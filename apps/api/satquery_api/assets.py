import hashlib
import io
from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

import numpy as np
from PIL import Image
from rasterio.errors import RasterioIOError
from rasterio.io import MemoryFile

MAX_UPLOAD_BYTES = 256 * 1024 * 1024
ALLOWED_EXTENSIONS = {".tif", ".tiff", ".png", ".jpg", ".jpeg"}
MAX_RASTER_PIXELS = 120_000_000


@dataclass(frozen=True)
class InspectedAsset:
    id: str
    filename: str
    size_bytes: int
    checksum_sha256: str
    media_type: str
    modality: str
    metadata: dict[str, object] | None
    warnings: list[str]


def detect_media_type(filename: str, head: bytes) -> str:
    extension = Path(filename).suffix.lower()
    if extension not in ALLOWED_EXTENSIONS:
        raise ValueError("Unsupported extension. Use GeoTIFF, PNG, or JPEG.")
    if head.startswith((b"II*\x00", b"MM\x00*")):
        return "image/tiff"
    if head.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if head.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    raise ValueError("File signature does not match a supported raster format.")


def infer_modality(filename: str) -> tuple[str, list[str]]:
    normalized = filename.upper()
    if any(token in normalized for token in ("S1_", "SENTINEL-1", "SAR", "RISAT")):
        return "S1_SAR", []
    if any(token in normalized for token in ("S2_", "SENTINEL-2", "MULTISPECTRAL", "MS_")):
        return "S2_MULTISPECTRAL", []
    return "UNKNOWN", ["Modality could not be inferred from the filename; user confirmation is required."]


def inspect_asset(filename: str, content: bytes) -> InspectedAsset:
    if not content:
        raise ValueError("The uploaded file is empty.")
    if len(content) > MAX_UPLOAD_BYTES:
        raise ValueError("The uploaded file exceeds the 256 MB development limit.")
    media_type = detect_media_type(filename, content[:16])
    modality, warnings = infer_modality(filename)
    metadata: dict[str, object] | None = None
    if media_type == "image/tiff":
        try:
            with MemoryFile(content) as memory_file, memory_file.open() as dataset:
                metadata = {
                    "width": dataset.width,
                    "height": dataset.height,
                    "band_count": dataset.count,
                    "band_descriptions": [description or f"Band {index}" for index, description in enumerate(dataset.descriptions, 1)],
                    "dtypes": list(dataset.dtypes),
                    "crs": dataset.crs.to_string() if dataset.crs else None,
                    "bounds": [dataset.bounds.left, dataset.bounds.bottom, dataset.bounds.right, dataset.bounds.top],
                    "resolution": [abs(dataset.res[0]), abs(dataset.res[1])],
                    "nodata": dataset.nodata,
                }
                if dataset.width * dataset.height > MAX_RASTER_PIXELS:
                    raise ValueError("Raster dimensions exceed the 120 megapixel processing limit.")
                if dataset.crs is None:
                    warnings.append("GeoTIFF does not declare a coordinate reference system.")
        except RasterioIOError:
            warnings.append("GeoTIFF signature is valid, but raster metadata could not be opened.")
    return InspectedAsset(
        id=str(uuid4()),
        filename=Path(filename).name,
        size_bytes=len(content),
        checksum_sha256=hashlib.sha256(content).hexdigest(),
        media_type=media_type,
        modality=modality,
        metadata=metadata,
        warnings=warnings,
    )


def create_preview(content: bytes, media_type: str, max_size: int = 1200) -> bytes:
    """Create a bounded PNG preview without returning the original raster."""
    if media_type in {"image/png", "image/jpeg"}:
        image = Image.open(io.BytesIO(content)).convert("RGB")
        image.thumbnail((max_size, max_size))
    else:
        with MemoryFile(content) as memory_file, memory_file.open() as dataset:
            indexes = list(range(1, min(dataset.count, 3) + 1))
            data = dataset.read(indexes, out_shape=(len(indexes), min(dataset.height, max_size), min(dataset.width, max_size)))
            rendered: list[np.ndarray] = []
            for band in data:
                valid = band[np.isfinite(band)]
                low, high = np.percentile(valid, (2, 98)) if valid.size else (0, 1)
                scaled = np.clip((band.astype("float32") - low) / max(float(high - low), 1e-6), 0, 1)
                rendered.append((scaled * 255).astype("uint8"))
            if len(rendered) == 1:
                rgb = np.stack([rendered[0]] * 3, axis=-1)
            else:
                while len(rendered) < 3:
                    rendered.append(rendered[-1])
                rgb = np.stack(rendered[:3], axis=-1)
            image = Image.fromarray(rgb, "RGB")
    output = io.BytesIO()
    image.save(output, format="PNG", optimize=True)
    return output.getvalue()
