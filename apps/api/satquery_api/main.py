import io
import json
from pathlib import Path
from typing import Annotated
from uuid import uuid4

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response, StreamingResponse
from pydantic import BaseModel, Field
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

from satquery_api.adapters import ModelRequest, configured_adapter
from satquery_api.assets import MAX_UPLOAD_BYTES, create_preview, inspect_asset
from satquery_api.deterministic import (
    UnsupportedQueryError,
    analyze_pair,
    classify_query,
)
from satquery_api.preprocessing import align_pair
from satquery_api.storage import STORE

app = FastAPI(title="SatQuery AI API", version="0.1.0")
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:3000"], allow_methods=["*"], allow_headers=["*"])

@app.middleware("http")
async def security_headers(request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    return response


class HealthResponse(BaseModel):
    status: str
    inference_mode: str
    primary_model: str


class ModelCapability(BaseModel):
    id: str
    display_name: str
    status: str
    modalities: list[list[str]]
    tasks: list[str]
    temporal: bool
    output_types: list[str]
    version: str


class AnalysisRequest(BaseModel):
    asset_ids: list[str] = Field(min_length=2, max_length=4)
    query: str = Field(min_length=8, max_length=2000)
    requested_task: str = "auto"


class AnalysisResult(BaseModel):
    run_id: str
    inference_mode: str
    answer: str
    task: str
    model: dict[str, str]
    confidence: dict[str, str | float | bool]
    warnings: list[str]
    trace: list[dict[str, str]]
    metrics: dict[str, float] = Field(default_factory=dict)


class AssetResponse(BaseModel):
    id: str
    filename: str
    size_bytes: int
    checksum_sha256: str
    media_type: str
    modality: str
    metadata: dict[str, object] | None
    storage_state: str
    warnings: list[str]


class PairValidationRequest(BaseModel):
    modalities: list[str] | None = Field(default=None, min_length=2, max_length=2)
    asset_ids: list[str] | None = Field(default=None, min_length=2, max_length=2)


class PairValidationResponse(BaseModel):
    compatible: bool
    model_id: str | None
    issues: list[str]


class PairPreparationRequest(BaseModel):
    source_asset_id: str
    reference_asset_id: str


PRIMARY_MODEL = ModelCapability(
    id="rs-internvl-s1-s2",
    display_name="RS-InternVL",
    status="mock",
    modalities=[["S1_SAR", "S2_MULTISPECTRAL"]],
    tasks=["vqa", "caption", "grounding"],
    temporal=False,
    output_types=["text", "bbox"],
    version="unverified-mock",
)
CPU_MODEL = ModelCapability(
    id="deterministic-eo-s1-s2", display_name="Deterministic EO Engine", status="available",
    modalities=[["S1_SAR", "S2_MULTISPECTRAL"]], tasks=["vqa", "grounding"], temporal=False,
    output_types=["text", "mask"], version="1.1.0",
)
MODEL_ADAPTER, INFERENCE_MODE = configured_adapter()
ASSETS: dict[str, AssetResponse] = {}
ASSET_PATHS: dict[str, Path] = {}
RUNS: dict[str, AnalysisResult] = {}
RUN_MASKS: dict[str, bytes] = {}


@app.get("/health/live", response_model=HealthResponse)
def liveness() -> HealthResponse:
    primary = CPU_MODEL.id if INFERENCE_MODE == "deterministic" else PRIMARY_MODEL.id
    return HealthResponse(status="ok", inference_mode=INFERENCE_MODE, primary_model=primary)


@app.get("/health/ready", response_model=HealthResponse)
def readiness() -> HealthResponse:
    status = "ready" if INFERENCE_MODE in {"remote", "deterministic"} else "degraded"
    primary = CPU_MODEL.id if INFERENCE_MODE == "deterministic" else PRIMARY_MODEL.id
    return HealthResponse(status=status, inference_mode=INFERENCE_MODE, primary_model=primary)


@app.get("/api/v1/models", response_model=list[ModelCapability])
def model_registry() -> list[ModelCapability]:
    return [PRIMARY_MODEL, CPU_MODEL]


@app.post("/api/v1/assets", response_model=AssetResponse, status_code=201)
async def upload_asset(file: Annotated[UploadFile, File()]) -> AssetResponse:
    try:
        content = await file.read(MAX_UPLOAD_BYTES + 1)
        inspected = inspect_asset(file.filename or "unnamed", content)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    upload_root = Path("uploads").resolve()
    upload_root.mkdir(parents=True, exist_ok=True)
    target = upload_root / f"{inspected.id}{Path(inspected.filename).suffix.lower()}"
    target.write_bytes(content)
    response = AssetResponse(**inspected.__dict__, storage_state="stored")
    ASSETS[inspected.id] = response
    ASSET_PATHS[inspected.id] = target
    STORE.put_asset(inspected.id, response.model_dump(), target)
    return response


@app.get("/api/v1/assets/{asset_id}", response_model=AssetResponse)
def get_asset(asset_id: str) -> AssetResponse:
    if asset_id in ASSETS:
        return ASSETS[asset_id]
    stored = STORE.get_asset(asset_id)
    if not stored:
        raise HTTPException(status_code=404, detail="Asset not found")
    asset = AssetResponse.model_validate(stored[0])
    ASSETS[asset_id], ASSET_PATHS[asset_id] = asset, stored[1]
    return asset


@app.get("/api/v1/assets", response_model=list[AssetResponse])
def list_assets() -> list[AssetResponse]:
    return [AssetResponse.model_validate(item) for item in STORE.list_assets()]


@app.delete("/api/v1/assets/{asset_id}", status_code=204)
def delete_asset(asset_id: str) -> Response:
    path = STORE.delete_asset(asset_id)
    if path is None:
        raise HTTPException(status_code=404, detail="Asset not found")
    path.unlink(missing_ok=True)
    ASSETS.pop(asset_id, None); ASSET_PATHS.pop(asset_id, None)
    return Response(status_code=204)


@app.get("/api/v1/assets/{asset_id}/preview")
def preview_asset(asset_id: str) -> Response:
    asset = get_asset(asset_id)
    path = ASSET_PATHS[asset_id]
    try:
        preview = create_preview(path.read_bytes(), asset.media_type)
    except Exception as error:
        raise HTTPException(status_code=422, detail="Preview could not be generated") from error
    return Response(preview, media_type="image/png", headers={"Cache-Control": "private, max-age=3600"})


@app.post("/api/v1/asset-pairs/validate", response_model=PairValidationResponse)
def validate_asset_pair(request: PairValidationRequest) -> PairValidationResponse:
    records = []
    for item in request.asset_ids or []:
        try:
            records.append(get_asset(item))
        except HTTPException:
            pass
    if request.asset_ids and len(records) != 2:
        return PairValidationResponse(compatible=False, model_id=None, issues=["One or more assets were not found."])
    observed = set(request.modalities or [asset.modality for asset in records])
    required = {"S1_SAR", "S2_MULTISPECTRAL"}
    issues: list[str] = []
    if observed != required:
        issues.extend(f"Missing required modality: {item}" for item in sorted(required - observed))
    if len(records) == 2:
        metadata = [asset.metadata or {} for asset in records]
        crs = [item.get("crs") for item in metadata]
        if all(crs) and crs[0] != crs[1]:
            issues.append(f"CRS mismatch: {crs[0]} versus {crs[1]}.")
        bounds = [item.get("bounds") for item in metadata]
        if all(bounds):
            a, b = bounds
            if a[2] <= b[0] or b[2] <= a[0] or a[3] <= b[1] or b[3] <= a[1]:
                issues.append("Raster footprints do not overlap.")
    if not issues:
        return PairValidationResponse(compatible=True, model_id=PRIMARY_MODEL.id, issues=[])
    return PairValidationResponse(compatible=False, model_id=None, issues=issues)


@app.post("/api/v1/asset-pairs/prepare")
def prepare_asset_pair(request: PairPreparationRequest) -> dict[str, object]:
    source, reference = get_asset(request.source_asset_id), get_asset(request.reference_asset_id)
    if source.media_type != "image/tiff" or reference.media_type != "image/tiff":
        raise HTTPException(status_code=422, detail="Alignment requires two GeoTIFF assets")
    output = Path("data/aligned") / f"{source.id}-to-{reference.id}.tif"
    try:
        grid = align_pair(ASSET_PATHS[source.id], ASSET_PATHS[reference.id], output)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    return {"status": "prepared", "source_asset_id": source.id, "reference_asset_id": reference.id, "aligned_path": str(output), "grid": grid}


@app.post("/api/v1/runs", response_model=AnalysisResult)
def create_run(request: AnalysisRequest) -> AnalysisResult:
    records: list[AssetResponse] = []
    missing: list[str] = []
    for asset_id in request.asset_ids:
        try:
            records.append(get_asset(asset_id))
        except HTTPException:
            missing.append(asset_id)
    built_in_demo = set(request.asset_ids) <= {"s1", "s2", "s1-demo", "s2-demo"}
    if missing and not built_in_demo:
        raise HTTPException(status_code=422, detail="One or more assets were not found; reload or upload the observations again")
    task = "grounding" if any(word in request.query.lower() for word in ("highlight", "where", "locate", "identify", "map", "region", "area")) else "vqa"
    metrics: dict[str, float] = {}
    outcome = None
    run_mode = INFERENCE_MODE
    if INFERENCE_MODE == "deterministic" and len(records) == 2:
        by_modality = {asset.modality: asset for asset in records}
        if {"S1_SAR", "S2_MULTISPECTRAL"} - set(by_modality):
            raise HTTPException(status_code=422, detail="Deterministic analysis requires one S1 and one S2 asset")
        try:
            query_intent = classify_query(request.query)
            outcome = analyze_pair(ASSET_PATHS[by_modality["S1_SAR"].id], ASSET_PATHS[by_modality["S2_MULTISPECTRAL"].id], request.query)
        except UnsupportedQueryError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error
        prediction = type("Prediction", (), {"answer": outcome.answer, "confidence": outcome.confidence, "warning": outcome.warning})()
        confidence_method, metrics = outcome.method, outcome.metrics
    else:
        try: prediction = MODEL_ADAPTER.predict(ModelRequest(asset_ids=request.asset_ids, query=request.query, task=task))
        except RuntimeError as error: raise HTTPException(status_code=503, detail=str(error)) from error
        confidence_method = "simulated demo score" if INFERENCE_MODE == "mock" else "remote uncalibrated score"
        if INFERENCE_MODE == "deterministic":
            run_mode = "mock"
            confidence_method = "simulated demo score"
    active_model = CPU_MODEL if run_mode == "deterministic" else PRIMARY_MODEL
    result = AnalysisResult(
        run_id=str(uuid4()),
        inference_mode=run_mode,
        answer=prediction.answer,
        task=task,
        model={"id": active_model.id, "version": active_model.version},
        confidence={"value": prediction.confidence, "method": confidence_method, "calibrated": False},
        warnings=[prediction.warning],
        trace=[
            {"stage": "validation", "status": "complete", "detail": "S1/S2 contract accepted"},
            {"stage": "routing", "status": "complete", "detail": f"{active_model.display_name} selected"},
            {"stage": "analysis", "status": "complete", "detail": f"CPU {query_intent} evidence engine executed" if run_mode == "deterministic" else f"{run_mode} adapter executed"},
        ],
        metrics=metrics,
    )
    RUNS[result.run_id] = result
    if outcome is not None:
        RUN_MASKS[result.run_id] = outcome.mask_png
    STORE.put_run(result.run_id, result.model_dump())
    return result


@app.get("/api/v1/runs/{run_id}/evidence.png")
def run_evidence(run_id: str) -> Response:
    if run_id not in RUN_MASKS:
        raise HTTPException(status_code=404, detail="No raster evidence is available for this run")
    return Response(RUN_MASKS[run_id], media_type="image/png", headers={"Cache-Control": "private, max-age=3600"})


@app.get("/api/v1/runs/{run_id}", response_model=AnalysisResult)
def get_run(run_id: str) -> AnalysisResult:
    if run_id in RUNS:
        return RUNS[run_id]
    stored = STORE.get_run(run_id)
    if not stored:
        raise HTTPException(status_code=404, detail="Run not found")
    result = AnalysisResult.model_validate(stored[0]); RUNS[run_id] = result
    return result


@app.get("/api/v1/runs")
def list_runs() -> list[dict]:
    return STORE.list_runs()


@app.post("/api/v1/runs/{run_id}/cancel")
def cancel_run(run_id: str) -> dict[str, str]:
    if not STORE.set_run_status(run_id, "cancelled"):
        raise HTTPException(status_code=404, detail="Run not found")
    return {"run_id": run_id, "status": "cancelled"}


@app.get("/api/v1/runs/{run_id}/events")
def run_events(run_id: str) -> StreamingResponse:
    result = get_run(run_id)
    def stream():
        for index, event in enumerate(result.trace, 1):
            yield f"id: {index}\nevent: trace\ndata: {json.dumps(event)}\n\n"
        yield f"event: complete\ndata: {json.dumps({'run_id': result.run_id})}\n\n"
    return StreamingResponse(stream(), media_type="text/event-stream")


@app.get("/api/v1/runs/{run_id}/report")
def run_report(run_id: str) -> Response:
    result = get_run(run_id)
    payload = result.model_dump_json(indent=2)
    return Response(payload, media_type="application/json", headers={"Content-Disposition": f'attachment; filename="satquery-{run_id}.json"'})


@app.get("/api/v1/runs/{run_id}/report.pdf")
def run_pdf_report(run_id: str) -> Response:
    result = get_run(run_id); output = io.BytesIO(); document = canvas.Canvas(output, pagesize=A4)
    width, height = A4; document.setFillColorRGB(.03, .09, .14); document.rect(0, 0, width, height, fill=1, stroke=0)
    document.setFillColorRGB(.45, .9, 1); document.setFont("Helvetica-Bold", 11); document.drawString(42, height - 48, "SATQUERY AI · ANALYSIS REPORT")
    document.setFillColorRGB(1, 1, 1); document.setFont("Helvetica-Bold", 22); document.drawString(42, height - 82, result.task.upper())
    document.setFont("Helvetica", 9); document.setFillColorRGB(.7, .78, .84); document.drawString(42, height - 102, f"Run {result.run_id} · {result.model['id']} · {result.inference_mode}")
    text = document.beginText(42, height - 145); text.setFont("Helvetica", 11); text.setLeading(17); text.setFillColorRGB(.92, .96, 1)
    for line in [result.answer, "", f"Confidence: {result.confidence['value']} ({result.confidence['method']}; calibrated={result.confidence['calibrated']})", "", "Trace:"] + [f"• {item['stage']}: {item['detail']}" for item in result.trace] + ["", "Warnings:"] + [f"• {warning}" for warning in result.warnings]:
        for chunk in [line[i:i+88] for i in range(0, len(line), 88)] or [""]: text.textLine(chunk)
    document.drawText(text); document.showPage(); document.save()
    return Response(output.getvalue(), media_type="application/pdf", headers={"Content-Disposition": f'attachment; filename="satquery-{run_id}.pdf"'})
