from pathlib import Path

import numpy as np
import rasterio
from rasterio.warp import Resampling, reproject


def align_pair(source_path: Path, reference_path: Path, output_path: Path) -> dict[str, object]:
    """Reproject the source raster onto the exact grid of the reference raster."""
    with rasterio.open(reference_path) as reference, rasterio.open(source_path) as source:
        if not reference.crs or not source.crs:
            raise ValueError("Both rasters require a CRS for alignment.")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        profile = source.profile.copy()
        profile.update(crs=reference.crs, transform=reference.transform, width=reference.width, height=reference.height)
        with rasterio.open(output_path, "w", **profile) as aligned:
            for band in range(1, source.count + 1):
                destination = np.empty((reference.height, reference.width), dtype=source.dtypes[band - 1])
                reproject(source=rasterio.band(source, band), destination=destination, src_transform=source.transform, src_crs=source.crs, dst_transform=reference.transform, dst_crs=reference.crs, resampling=Resampling.bilinear, src_nodata=source.nodata, dst_nodata=source.nodata)
                aligned.write(destination, band)
        return {"crs": reference.crs.to_string(), "width": reference.width, "height": reference.height, "resolution": [abs(reference.res[0]), abs(reference.res[1])], "transform": list(reference.transform)[:6], "resampling": "bilinear"}
