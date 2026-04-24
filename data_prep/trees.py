"""Philadelphia Parks & Rec street tree inventory (2024).

Provides tree_count per centerline segment via a buffer spatial join.
Complements the canopy raster - raw tree counts are a count-based feature,
canopy_pct is an area-based feature. Either or both may be useful.
"""
from __future__ import annotations

import geopandas as gpd
import pandas as pd

from .common import raw, transformed, to_2272_file

TREE_BUFFER_FT = 30


def load_trees() -> gpd.GeoDataFrame:
    src_path = raw("Phila Street Trees", "ppr_tree_inventory_2024.geojson")
    cache_path = transformed("Phila Street Trees", "ppr_tree_inventory_2024.geojson")
    trees = gpd.read_file(src_path)
    return to_2272_file(trees, cache_path)


def count_trees_per_segment(
    trees: gpd.GeoDataFrame,
    centerlines: gpd.GeoDataFrame,
    buffer_ft: float = TREE_BUFFER_FT,
) -> pd.DataFrame:
    buffered = centerlines[["seg_id", "geometry"]].copy()
    buffered.geometry = buffered.geometry.buffer(buffer_ft)

    joined = gpd.sjoin(
        trees, buffered, how="inner", predicate="intersects",
    )
    counts = (
        joined.groupby("seg_id").size().reset_index(name="tree_count")
    )
    return counts
