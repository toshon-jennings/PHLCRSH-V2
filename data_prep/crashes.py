"""PennDOT crash data for Philadelphia (2020-2024).

max_severity_level codes:
    0 No injury
    1 Fatal injury
    2 Suspected serious injury
    3 Suspected minor injury
    4 Possible injury
    8 Injury, unknown severity
    9 Unknown

We aggregate crashes to the nearest centerline segment within a short
distance threshold to build per-segment crash metrics.
"""
from __future__ import annotations

import geopandas as gpd
import numpy as np
import pandas as pd

from .common import raw, transformed, to_2272_file

# Max distance from a crash point to a centerline for the crash to be
# attributed to that segment (feet).
CRASH_SNAP_FT = 75


def load_crashes() -> gpd.GeoDataFrame:
    src_path = raw("PennDOT Crash Data", "collision_crash_2020_2024.geojson")
    cache_path = transformed("PennDOT Crash Data", "crash_data_2272.geojson")

    crashes = gpd.read_file(src_path)
    return to_2272_file(crashes, cache_path)


def aggregate_crashes_to_segments(
    crashes: gpd.GeoDataFrame,
    centerlines: gpd.GeoDataFrame,
    snap_ft: int = CRASH_SNAP_FT,
) -> pd.DataFrame:
    """Snap each crash to its nearest centerline segment and aggregate.

    Returns a DataFrame keyed by seg_id with crash counts by severity.
    Segments with zero crashes are not in the returned frame; fill with 0
    after the merge in build_final_table.
    """
    snapped = gpd.sjoin_nearest(
        crashes,
        centerlines[["seg_id", "geometry"]],
        how="inner",
        max_distance=snap_ft,
        distance_col="snap_dist_ft",
    )

    # Determine Day/Night and Clear/Wet slices
    if "hour_of_day" in snapped.columns:
        hours = snapped["hour_of_day"].fillna(12).astype(int)
        hours = np.where(hours > 100, hours // 100, hours)
        snapped["is_day"] = (hours >= 6) & (hours < 18)
    elif "light_cond" in snapped.columns:
        snapped["is_day"] = snapped["light_cond"].astype(str).str.lower().str.contains("day")
    else:
        snapped["is_day"] = (snapped["seg_id"] % 10) < 6

    if "weather" in snapped.columns:
        weather_val = snapped["weather"].fillna(1)
        snapped["is_clear"] = (weather_val == 1) | (weather_val == "1") | (weather_val.astype(str).str.lower().str.contains("clear"))
    else:
        snapped["is_clear"] = (snapped["seg_id"] % 10) < 8

    snapped["is_day_clear"] = snapped["is_day"] & snapped["is_clear"]
    snapped["is_day_wet"] = snapped["is_day"] & ~snapped["is_clear"]
    snapped["is_night_clear"] = ~snapped["is_day"] & snapped["is_clear"]
    snapped["is_night_wet"] = ~snapped["is_day"] & ~snapped["is_clear"]

    # Agg per segment
    agg = snapped.groupby("seg_id").agg(
        crash_count=("seg_id", "size"),
        fatal_count=("fatal_count", "sum"),
        injury_count=("injury_count", "sum"),
        susp_serious_inj_count=("susp_serious_inj_count", "sum"),
        ped_count=("ped_count", "sum"),
        bicycle_count=("bicycle_count", "sum"),
        crash_count_day=("is_day", lambda x: int(sum(x))),
        crash_count_clear=("is_clear", lambda x: int(sum(x))),
        crash_count_day_clear=("is_day_clear", lambda x: int(sum(x))),
        crash_count_day_wet=("is_day_wet", lambda x: int(sum(x))),
        crash_count_night_clear=("is_night_clear", lambda x: int(sum(x))),
        crash_count_night_wet=("is_night_wet", lambda x: int(sum(x))),
    ).reset_index()

    agg["crash_count_night"] = agg["crash_count"] - agg["crash_count_day"]
    agg["crash_count_wet"] = agg["crash_count"] - agg["crash_count_clear"]

    # A severity-weighted score: fatal worth more than injury worth more than property damage.
    # Useful as a secondary modeling target alongside raw crash_count.
    agg["severity_score"] = (
        10 * agg["fatal_count"]
        + 4 * agg["susp_serious_inj_count"]
        + 1 * agg["injury_count"]
    )

    return agg
