"""Shared utilities and path constants used across data prep modules."""
from __future__ import annotations

import os
import geopandas as gpd

# ---- Paths (all relative to project root) ----

RAW = "raw-data"
TRANSFORMED = "transformed-data"
STASH = f"{TRANSFORMED}/Stash or final"

EPSG = 2272  # PA State Plane South (feet)


# ---- Path helpers ----

def raw(*parts: str) -> str:
    return os.path.join(RAW, *parts)


def transformed(*parts: str) -> str:
    return os.path.join(TRANSFORMED, *parts)


def stash(*parts: str) -> str:
    return os.path.join(STASH, *parts)


# ---- Geo helpers ----

def to_2272_file(df: gpd.GeoDataFrame, filepath: str) -> gpd.GeoDataFrame:
    """Reproject to EPSG:2272 and cache to disk. Reads from cache if present."""
    if os.path.exists(filepath):
        return gpd.read_file(filepath)
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    df_2272 = df.to_crs(EPSG)
    df_2272.to_file(filepath, driver="GeoJSON")
    return df_2272


def get_midpoint(gdf: gpd.GeoDataFrame) -> gpd.GeoSeries:
    """Return midpoint of each line geometry as a GeoSeries."""
    return gdf.geometry.interpolate(0.5, normalized=True)
