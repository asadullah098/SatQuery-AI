import numpy as np
from fastapi.testclient import TestClient
from rasterio.io import MemoryFile
from rasterio.transform import from_origin
from satquery_api.main import app

client = TestClient(app)


def test_liveness_exposes_default_deterministic_mode() -> None:
    response = client.get("/health/live")
    assert response.status_code == 200
    assert response.json()["inference_mode"] == "deterministic"


def test_registry_exposes_primary_model_contract() -> None:
    response = client.get("/api/v1/models")
    assert response.status_code == 200
    assert response.json()[0]["id"] == "rs-internvl-s1-s2"


def test_run_never_misrepresents_mock_as_real_inference() -> None:
    response = client.post("/api/v1/runs", json={"asset_ids": ["s1", "s2"], "query": "Where is water?"})
    assert response.status_code == 200
    assert response.json()["inference_mode"] == "mock"
    assert response.json()["confidence"]["calibrated"] is False


def test_asset_upload_validates_signature_and_detects_sar() -> None:
    response = client.post("/api/v1/assets", files={"file": ("S1_scene.tif", b"II*\x00demo-raster", "image/tiff")})
    assert response.status_code == 201
    assert response.json()["modality"] == "S1_SAR"
    assert len(response.json()["checksum_sha256"]) == 64


def test_pair_validation_requires_s1_and_s2() -> None:
    valid = client.post("/api/v1/asset-pairs/validate", json={"modalities": ["S1_SAR", "S2_MULTISPECTRAL"]})
    invalid = client.post("/api/v1/asset-pairs/validate", json={"modalities": ["S1_SAR", "S1_SAR"]})
    assert valid.json()["compatible"] is True
    assert invalid.json()["compatible"] is False


def test_real_geotiff_metadata_is_extracted() -> None:
    profile = {"driver": "GTiff", "height": 4, "width": 5, "count": 2, "dtype": "uint16", "crs": "EPSG:32643", "transform": from_origin(77.0, 24.0, 10.0, 10.0)}
    with MemoryFile() as memory_file:
        with memory_file.open(**profile) as dataset:
            dataset.write(np.ones((2, 4, 5), dtype="uint16"))
        payload = memory_file.read()
    response = client.post("/api/v1/assets", files={"file": ("S2_scene.tif", payload, "image/tiff")})
    assert response.status_code == 201
    assert response.json()["metadata"]["crs"] == "EPSG:32643"
    assert response.json()["metadata"]["band_count"] == 2
    assert response.json()["metadata"]["resolution"] == [10.0, 10.0]


def _upload_geotiff(name: str, crs: str = "EPSG:32643", west: float = 77.0) -> dict:
    profile = {"driver": "GTiff", "height": 8, "width": 8, "count": 1, "dtype": "uint16", "crs": crs, "transform": from_origin(west, 24.0, 10.0, 10.0)}
    with MemoryFile() as memory_file:
        with memory_file.open(**profile) as dataset:
            dataset.write(np.arange(64, dtype="uint16").reshape(1, 8, 8))
        payload = memory_file.read()
    return client.post("/api/v1/assets", files={"file": (name, payload, "image/tiff")}).json()


def _upload_rgb_geotiff(name: str) -> dict:
    profile = {"driver": "GTiff", "height": 12, "width": 12, "count": 3, "dtype": "uint16", "crs": "EPSG:32643", "transform": from_origin(77.0, 24.0, 10.0, 10.0)}
    data = np.full((3, 12, 12), 50, dtype="uint16")
    data[0, 2:9, 1:7] = 25
    data[1, 2:9, 1:7] = 210
    data[2, 2:9, 1:7] = 35
    with MemoryFile() as memory_file:
        with memory_file.open(**profile) as dataset:
            dataset.write(data)
        payload = memory_file.read()
    return client.post("/api/v1/assets", files={"file": (name, payload, "image/tiff")}).json()


def test_asset_preview_and_retrieval() -> None:
    asset = _upload_geotiff("S1_preview.tif")
    assert client.get(f"/api/v1/assets/{asset['id']}").status_code == 200
    preview = client.get(f"/api/v1/assets/{asset['id']}/preview")
    assert preview.status_code == 200
    assert preview.headers["content-type"] == "image/png"
    assert preview.content.startswith(b"\x89PNG")


def test_pair_validation_checks_actual_asset_metadata() -> None:
    s1 = _upload_geotiff("S1_pair.tif", "EPSG:32643")
    s2 = _upload_geotiff("S2_pair.tif", "EPSG:4326")
    response = client.post("/api/v1/asset-pairs/validate", json={"asset_ids": [s1["id"], s2["id"]]})
    assert response.json()["compatible"] is False
    assert any("CRS mismatch" in issue for issue in response.json()["issues"])


def test_pair_preparation_aligns_source_to_reference_grid() -> None:
    source = _upload_geotiff("S1_align.tif", "EPSG:32643")
    reference = _upload_geotiff("S2_align.tif", "EPSG:32643")
    response = client.post("/api/v1/asset-pairs/prepare", json={"source_asset_id": source["id"], "reference_asset_id": reference["id"]})
    assert response.status_code == 200
    assert response.json()["grid"]["width"] == 8
    assert response.json()["grid"]["resampling"] == "bilinear"


def test_uploaded_pair_uses_real_cpu_evidence_engine() -> None:
    s1 = _upload_geotiff("S1_cpu.tif")
    s2 = _upload_geotiff("S2_cpu.tif")
    response = client.post("/api/v1/runs", json={"asset_ids": [s1["id"], s2["id"]], "query": "Where are the water regions?"})
    assert response.status_code == 200
    result = response.json()
    assert result["inference_mode"] == "deterministic"
    assert result["model"]["id"] == "deterministic-eo-s1-s2"
    assert "water_coverage_percent" in result["metrics"]
    evidence = client.get(f"/api/v1/runs/{result['run_id']}/evidence.png")
    assert evidence.status_code == 200
    assert evidence.content.startswith(b"\x89PNG")


def test_green_land_query_routes_to_vegetation_evidence() -> None:
    s1 = _upload_geotiff("S1_vegetation.tif")
    s2 = _upload_rgb_geotiff("S2_MULTISPECTRAL_vegetation.tif")
    response = client.post("/api/v1/runs", json={"asset_ids": [s1["id"], s2["id"]], "query": "Identify the greenland area"})
    assert response.status_code == 200
    result = response.json()
    assert result["task"] == "grounding"
    assert "vegetation_coverage_percent" in result["metrics"]
    assert "vegetated land" in result["answer"]
    assert "water_coverage_percent" not in result["metrics"]


def test_persisted_assets_are_restored_for_analysis_after_process_restart() -> None:
    from satquery_api import main

    s1 = _upload_geotiff("S1_persisted.tif")
    s2 = _upload_rgb_geotiff("S2_MULTISPECTRAL_persisted.tif")
    main.ASSETS.clear()
    main.ASSET_PATHS.clear()
    response = client.post("/api/v1/runs", json={"asset_ids": [s1["id"], s2["id"]], "query": "Identify the green land area"})
    assert response.status_code == 200
    assert "vegetation_coverage_percent" in response.json()["metrics"]


def test_unsupported_cpu_query_is_rejected_instead_of_returning_water() -> None:
    s1 = _upload_geotiff("S1_unsupported.tif")
    s2 = _upload_rgb_geotiff("S2_MULTISPECTRAL_unsupported.tif")
    response = client.post("/api/v1/runs", json={"asset_ids": [s1["id"], s2["id"]], "query": "Count all buildings in this scene"})
    assert response.status_code == 422
    assert "vision-language model" in response.json()["detail"]


def test_run_can_be_retrieved_streamed_and_reported() -> None:
    created = client.post("/api/v1/runs", json={"asset_ids": ["s1", "s2"], "query": "Where is water?"}).json()
    run_id = created["run_id"]
    assert client.get(f"/api/v1/runs/{run_id}").json()["run_id"] == run_id
    assert "event: complete" in client.get(f"/api/v1/runs/{run_id}/events").text
    report = client.get(f"/api/v1/runs/{run_id}/report")
    assert report.status_code == 200
    assert "attachment" in report.headers["content-disposition"]
    listing = client.get("/api/v1/runs")
    assert any(item["run_id"] == run_id for item in listing.json())
    assert client.post(f"/api/v1/runs/{run_id}/cancel").json()["status"] == "cancelled"
