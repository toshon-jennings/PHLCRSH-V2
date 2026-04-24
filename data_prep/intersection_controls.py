"""Intersection controls: stop signs and traffic signals.

stoptype values:
    Conventional - single-direction stop
    All Way      - four-way stop
    Signalized   - traffic signal

We can't tell from the data which leg of the intersection has the control,
so we treat each centerline segment as having a control if any control
point is within a small buffer of the segment.
"""
from __future__ import annotations

import geopandas as gpd
import pandas as pd

from .common import raw, transformed, to_2272_file

# Buffer around control points for spatial match (feet).
CONTROL_BUFFER_FT = 5


def load_intersection_controls() -> gpd.GeoDataFrame:
    src_path = raw("Intersection Controls", "Intersection_Controls.geojson")
    cache_path = transformed("Intersection Controls", "Intersection_Controls_2272.geojson")
    controls = gpd.read_file(src_path)
    return to_2272_file(controls, cache_path)


def aggregate_controls_to_segments(
    controls: gpd.GeoDataFrame,
    centerlines: gpd.GeoDataFrame,
    buffer_ft: float = CONTROL_BUFFER_FT,
) -> pd.DataFrame:
    """Return per-seg_id control flags (any control, signalized, all-way, conventional)."""
    buffered = controls.copy()
    buffered.geometry = buffered.geometry.buffer(buffer_ft)

    joined = gpd.sjoin(
        centerlines[["seg_id", "geometry"]],
        buffered[["stoptype", "geometry"]],
        how="left",
        predicate="intersects",
    )

    # Pivot by stoptype - one row per seg_id with binary flags
    joined = joined.dropna(subset=["stoptype"])
    flags = (
        joined.assign(val=1)
        .pivot_table(
            index="seg_id",
            columns="stoptype",
            values="val",
            aggfunc="max",
            fill_value=0,
        )
        .reset_index()
    )

    # Normalize column names
    rename_map = {
        "Conventional": "has_conventional_stop",
        "All Way": "has_all_way_stop",
        "Signalized": "has_signal",
    }
    flags = flags.rename(columns=rename_map)

    for col in rename_map.values():
        if col not in flags.columns:
            flags[col] = 0

    flags["has_any_control"] = (
        flags["has_conventional_stop"]
        | flags["has_all_way_stop"]
        | flags["has_signal"]
    ).astype(int)

    return flags[[
        "seg_id",
        "has_any_control",
        "has_conventional_stop",
        "has_all_way_stop",
        "has_signal",
    ]]
