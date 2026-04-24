"""Tree canopy coverage per centerline segment.

Uses the Philadelphia Parks & Rec 2018 Land Cover raster (6-inch resolution).
Class 1 = tree canopy. We buffer each segment and compute the percentage
of pixels within the buffer that are canopy.

Zonal stats takes long enough that we cache the intermediate result.
"""
from __future__ import annotations

import os

import geopandas as gpd
import pandas as pd
from rasterstats import zonal_stats

from .common import raw, transformed

CANOPY_RASTER = "Phila Land Cover Raster/PPR_LandCover_2018.gdb"
CANOPY_CACHE = "Phila Land Cover Raster/canopy_stats.parquet"
BUFFER_FT = 5  # small buffer to stay on the road and capture adjacent canopy


def compute_canopy_pct(centerlines: gpd.GeoDataFrame) -> pd.DataFrame:
    """Return seg_id + canopy_pct. Cached to parquet after first compute."""
    cache_path = transformed(CANOPY_CACHE)

    if os.path.exists(cache_path):
        stats_df = pd.read_parquet(cache_path)
    else:
        buffered = centerlines.copy()
        buffered.geometry = centerlines.geometry.buffer(BUFFER_FT)
        raster_path = raw(CANOPY_RASTER)

        stats = zonal_stats(
            buffered.geometry,
            raster_path,
            categorical=True,
            nodata=None,
        )
        stats_df = pd.DataFrame(stats)
        os.makedirs(os.path.dirname(cache_path), exist_ok=True)
        stats_df.to_parquet(cache_path)

    stats_df = stats_df.fillna(0)

    # Parquet converts int column names to strings - handle both
    class_cols = [c for c in ["1", "2", "3", "5", "6", "7", 1, 2, 3, 5, 6, 7]
                  if c in stats_df.columns]
    canopy_col = "1" if "1" in stats_df.columns else 1

    stats_df["total_pixels"] = stats_df[class_cols].sum(axis=1)
    stats_df["canopy_pct"] = stats_df[canopy_col] / stats_df["total_pixels"]

    out = centerlines[["seg_id"]].reset_index(drop=True).copy()
    out["canopy_pct"] = stats_df["canopy_pct"].values
    out["has_canopy"] = out["canopy_pct"] > 0
    return out
