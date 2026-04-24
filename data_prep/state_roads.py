"""PennDOT State Roads - authoritative source for lane count, posted speed,
AADT, divider type, and bike lane presence on state-maintained roads.

PennDOT TOTAL_WIDT was NOT used to calibrate our transect-derived widths
because the two measures showed near-zero correlation, likely due to
definition mismatch and route inventory conflation.

DIVSR_TYPE > 1 indicates a physical divider (see PennDOT HPMS field manual).
"""
from __future__ import annotations

import geopandas as gpd
import pandas as pd

from .common import raw, EPSG, get_midpoint


def load_state_roads() -> gpd.GeoDataFrame:
    """Load Philly state roads (pre-downloaded via PASDA)."""
    sr = gpd.read_file(raw("PA State Roads", "state_roads_philly.geojson"))
    sr = sr.to_crs(EPSG)
    sr["is_divided"] = sr["DIVSR_TYPE"].fillna(0).astype(int) > 1
    return sr


def join_state_roads_to_centerlines(
    state_roads: gpd.GeoDataFrame,
    centerlines: gpd.GeoDataFrame,
    max_dist_ft: float = 100,
) -> pd.DataFrame:
    """Nearest-midpoint join. Returns per-seg_id attributes from PennDOT."""
    centerlines_pts = centerlines[["seg_id", "geometry"]].copy()
    centerlines_pts.geometry = get_midpoint(centerlines)

    state_pts = state_roads.copy()
    state_pts.geometry = get_midpoint(state_roads)

    cols = ["LANE_CNT", "TOTAL_WIDT", "CUR_AADT", "DIVSR_TYPE", "BIKE_LANE",
            "is_divided", "geometry"]
    matched = gpd.sjoin_nearest(
        centerlines_pts,
        state_pts[cols],
        how="left",
        max_distance=max_dist_ft,
        distance_col="state_road_distance",
    )
    matched = (
        matched.sort_values("state_road_distance")
        .drop_duplicates(subset="seg_id", keep="first")
    )

    return matched[[
        "seg_id", "LANE_CNT", "TOTAL_WIDT", "CUR_AADT",
        "DIVSR_TYPE", "BIKE_LANE", "is_divided", "state_road_distance",
    ]].rename(columns={
        "LANE_CNT": "state_lane_cnt",
        "TOTAL_WIDT": "state_total_width_ft",
        "CUR_AADT": "state_aadt",
        "DIVSR_TYPE": "state_divisor_type",
        "BIKE_LANE": "bike_lane",
    })
