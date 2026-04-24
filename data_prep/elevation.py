"""Per-segment elevation and grade from the Philadelphia 3ft 2022 DEM.

Approach: sample elevation at N points along each centerline and compute
grade as (max - min) / length. This proved more robust than either
endpoint-only sampling or full zonal-stats buffer sampling. A smoothed
median filter knocks out bridge/overpass artifacts for a secondary grade
estimate.

Nodata value in the raster is float32 min (~-3.4e38). We treat anything
below -1e30 as nodata regardless of exact sentinel.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import geopandas as gpd
import rasterio
from shapely.geometry import LineString

from .common import raw

DEM_PATH = raw("Phila Elevation Raster", "Philadelphia_dem_3ft_2022.tif")
NODATA_THRESHOLD = -1e30
N_SAMPLES = 10
SMOOTH_WINDOW = 5


def _sample_profile_along_line(
    line: LineString, src, n: int = N_SAMPLES,
) -> list[dict]:
    rows = []
    for i in range(n):
        frac = i / (n - 1)
        station_ft = frac * line.length
        p = line.interpolate(frac, normalized=True)
        val = next(src.sample([(p.x, p.y)]))[0]
        if val > NODATA_THRESHOLD:
            rows.append({"station_ft": station_ft, "elev_ft": float(val)})
    return rows


def _get_grade_smoothed(
    line: LineString, src, n: int = N_SAMPLES, window: int = SMOOTH_WINDOW,
):
    """Return (grade_range_smooth, grade_median, grade_p90, grade_max)."""
    prof = _sample_profile_along_line(line, src, n=n)
    if len(prof) < 2 or line.length == 0:
        return np.nan, np.nan, np.nan, np.nan

    g = pd.DataFrame(prof).sort_values("station_ft")
    g["elev_smooth_ft"] = (
        g["elev_ft"]
        .rolling(window=window, center=True, min_periods=2)
        .median()
    ).fillna(g["elev_ft"])

    dx = g["station_ft"].diff()
    dz = g["elev_smooth_ft"].diff()
    interval_grades = (dz / dx).abs().replace([np.inf, -np.inf], np.nan).dropna()

    grade_range_smooth = (
        g["elev_smooth_ft"].max() - g["elev_smooth_ft"].min()
    ) / line.length

    if len(interval_grades) == 0:
        return grade_range_smooth, np.nan, np.nan, np.nan

    return (
        grade_range_smooth,
        interval_grades.median(),
        interval_grades.quantile(0.90),
        interval_grades.max(),
    )


def compute_grade(centerlines: gpd.GeoDataFrame) -> pd.DataFrame:
    """Return per-seg_id grade metrics."""
    with rasterio.open(DEM_PATH) as src:
        results = centerlines.geometry.apply(
            lambda line: _get_grade_smoothed(line, src, n=N_SAMPLES, window=SMOOTH_WINDOW)
        )

    out = centerlines[["seg_id"]].copy()
    out["grade_range_smooth"] = results.apply(lambda x: x[0])
    out["grade_smooth_median"] = results.apply(lambda x: x[1])
    out["grade_smooth_p90"] = results.apply(lambda x: x[2])
    out["grade_smooth_max"] = results.apply(lambda x: x[3])
    return out
