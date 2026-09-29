import io
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import rasterio
from PIL import Image
from rasterio.enums import Resampling

WATER_TERMS = ("water", "river", "lake", "pond", "flood", "inundat", "wetland")
VEGETATION_TERMS = (
    "vegetation", "vegetated", "green land", "greenland", "green area", "greenness",
    "crop", "cropland", "farm", "agricultur", "forest", "plantation",
)


class UnsupportedQueryError(ValueError):
    pass


@dataclass(frozen=True)
class DeterministicResult:
    answer: str
    confidence: float
    method: str
    mask_png: bytes
    metrics: dict[str, float]
    warning: str


def _read(path: Path, size: int = 512) -> np.ndarray:
    with rasterio.open(path) as dataset:
        return dataset.read(out_shape=(dataset.count, min(size, dataset.height), min(size, dataset.width)), resampling=Resampling.bilinear).astype("float32")


def _normalize(band: np.ndarray) -> np.ndarray:
    valid = band[np.isfinite(band)]
    low, high = np.percentile(valid, (2, 98)) if valid.size else (0, 1)
    return np.clip((band - low) / max(float(high - low), 1e-6), 0, 1)


def _normalize_stack(bands: np.ndarray) -> np.ndarray:
    valid = bands[np.isfinite(bands)]
    low, high = np.percentile(valid, (2, 98)) if valid.size else (0, 1)
    return np.clip((bands - low) / max(float(high - low), 1e-6), 0, 1)


def classify_query(query: str) -> str:
    normalized = " ".join(query.lower().replace("-", " ").split())
    if any(term in normalized for term in VEGETATION_TERMS):
        return "vegetation"
    if any(term in normalized for term in WATER_TERMS):
        return "water"
    raise UnsupportedQueryError(
        "The local CPU engine currently supports water/flood and vegetation/green-land mapping only. "
        "This question requires a vision-language model, which is not active in the no-GPU configuration."
    )


def _clean_mask(mask: np.ndarray) -> np.ndarray:
    neighbours = sum(
        np.roll(np.roll(mask, row, axis=0), column, axis=1)
        for row, column in ((-1, 0), (1, 0), (0, -1), (0, 1), (-1, -1), (-1, 1), (1, -1), (1, 1))
    )
    return mask & (neighbours >= 2)


def _outline_png(mask: np.ndarray, colour: tuple[int, int, int]) -> bytes:
    interior = mask & np.roll(mask, 1, 0) & np.roll(mask, -1, 0) & np.roll(mask, 1, 1) & np.roll(mask, -1, 1)
    boundary = mask & ~interior
    outline = boundary | np.roll(boundary, 1, 0) | np.roll(boundary, -1, 0) | np.roll(boundary, 1, 1) | np.roll(boundary, -1, 1)
    rgba = np.zeros((*mask.shape, 4), dtype="uint8")
    rgba[outline] = [*colour, 245]
    output = io.BytesIO()
    Image.fromarray(rgba, "RGBA").save(output, "PNG", optimize=True)
    return output.getvalue()


def _describe_distribution(mask: np.ndarray) -> str:
    if not mask.any():
        return "No spatially coherent region passed the current threshold."
    row_names, column_names = ("northern", "central", "southern"), ("western", "central", "eastern")
    row_edges = np.linspace(0, mask.shape[0], 4, dtype=int)
    column_edges = np.linspace(0, mask.shape[1], 4, dtype=int)
    cells: list[tuple[float, str]] = []
    for row in range(3):
        for column in range(3):
            density = float(mask[row_edges[row]:row_edges[row + 1], column_edges[column]:column_edges[column + 1]].mean())
            label = "central" if row == 1 and column == 1 else f"{row_names[row]}-{column_names[column]}"
            cells.append((density, label))
    peak = max(value for value, _ in cells)
    labels = [label for value, label in sorted(cells, reverse=True) if value >= max(0.02, peak * 0.62)][:3]
    return "The strongest evidence is in the " + ", ".join(labels) + " portion" + ("s" if len(labels) > 1 else "") + "."


def _analyze_vegetation(sar: np.ndarray, optical: np.ndarray) -> DeterministicResult:
    warnings: list[str] = []
    if optical.shape[0] >= 4:
        red, nir = optical[0], optical[3]
        vegetation_index = (nir - red) / (np.abs(nir) + np.abs(red) + 1e-6)
        optical_mask = vegetation_index > 0.24
        method = "NDVI vegetation screening with SAR backscatter support"
        warnings.append("The four-band route assumes R, G, B, NIR ordering; verify band metadata for scientific use.")
    elif optical.shape[0] >= 3:
        red, green, blue = _normalize_stack(optical[:3])
        excess_green = (2 * green) - red - blue
        green_advantage = green - np.maximum(red, blue)
        optical_mask = (excess_green > 0.08) & (green_advantage > 0.015) & (green > 0.16)
        method = "RGB excess-green vegetation screening with SAR backscatter support"
        warnings.append("RGB preview vegetation screening was used; NDVI requires a correctly ordered NIR band.")
    else:
        raise UnsupportedQueryError(
            "Vegetation mapping needs an RGB preview or a multispectral raster containing red and NIR bands."
        )

    optical_mask = _clean_mask(optical_mask)
    sar_intensity = np.mean([_normalize(band) for band in sar[: min(2, sar.shape[0])]], axis=0)
    sar_support = (sar_intensity > 0.20) & (sar_intensity < 0.92)
    supported = optical_mask & sar_support
    support_score = float(supported.sum() / max(optical_mask.sum(), 1))
    coverage = float(optical_mask.mean())
    confidence = min(0.82, 0.46 + support_score * 0.32)
    percent = coverage * 100
    distribution = _describe_distribution(optical_mask)
    answer = (
        f"The CPU vegetation analysis marks approximately {percent:.1f}% of the overlapping scene as "
        f"likely green or vegetated land. {distribution} "
        f"About {support_score * 100:.0f}% of that optical vegetation mask has non-water SAR backscatter support."
    )
    return DeterministicResult(
        answer,
        confidence,
        method,
        _outline_png(optical_mask, (167, 255, 112)),
        {"vegetation_coverage_percent": round(percent, 2), "sar_support_fraction": round(support_score, 4)},
        " ".join(warnings),
    )


def analyze_pair(sar_path: Path, optical_path: Path, query: str) -> DeterministicResult:
    sar, optical = _read(sar_path), _read(optical_path)
    height, width = min(sar.shape[1], optical.shape[1]), min(sar.shape[2], optical.shape[2])
    sar, optical = sar[:, :height, :width], optical[:, :height, :width]
    intent = classify_query(query)
    if intent == "vegetation":
        return _analyze_vegetation(sar, optical)

    warnings: list[str] = []
    shadow_fraction = 0.0
    if optical.shape[0] >= 4:
        green, nir = optical[1], optical[3]
        ndwi = (green - nir) / (np.abs(green) + np.abs(nir) + 1e-6)
        optical_mask = ndwi > 0.08
        method = "NDWI and SAR low-backscatter agreement"
    elif optical.shape[0] >= 3:
        red, green, blue = _normalize_stack(optical[:3])
        brightness = (red + green + blue) / 3
        water_colour_index = ((green + blue) / 2) - red
        optical_mask = (water_colour_index > 0.10) & (blue > 0.22)
        possible_shadows = (brightness < 0.22) & ~optical_mask
        shadow_fraction = float(possible_shadows.mean())
        warnings.append("RGB preview analysis was used; multispectral NDWI requires a four-or-more-band GeoTIFF.")
        method = "RGB water-colour index, SAR low-backscatter agreement, and shadow rejection"
    else:
        optical_mask = _normalize(optical[0]) < 0.30
        warnings.append("Single-band optical intensity screening was used; cloud-shadow separation is limited.")
        method = "Optical intensity and SAR low-backscatter agreement"
    sar_intensity = np.mean([_normalize(band) for band in sar[: min(2, sar.shape[0])]], axis=0)
    sar_mask = sar_intensity < 0.28
    agreement = _clean_mask(optical_mask & sar_mask)
    union = optical_mask | sar_mask
    agreement_score = float(agreement.sum() / max(union.sum(), 1))
    coverage = float(agreement.mean())
    confidence = min(.95, .55 + agreement_score * .4)
    percent = coverage * 100
    requested = "permanent water and likely inundation" if any(word in query.lower() for word in ("flood", "inundat")) else "surface water"
    shadow_note = f" Approximately {shadow_fraction * 100:.1f}% of dark optical pixels were rejected as possible shadow or non-water because they lacked the required water colour response." if optical.shape[0] >= 3 else ""
    distribution = _describe_distribution(agreement)
    answer = f"CPU-based S1/S2 analysis identifies approximately {percent:.1f}% of the overlapping scene as {requested} supported by both sensors. {distribution} Optical water response and low SAR backscatter agree with an IoU-style score of {agreement_score:.2f}.{shadow_note}"
    warning = " ".join(warnings) if warnings else "Deterministic EO result; no vision-language checkpoint was executed."
    return DeterministicResult(answer, confidence, method, _outline_png(agreement, (111, 255, 211)), {"water_coverage_percent": round(percent, 2), "cross_sensor_agreement": round(agreement_score, 4), "rejected_shadow_percent": round(shadow_fraction * 100, 2)}, warning)
