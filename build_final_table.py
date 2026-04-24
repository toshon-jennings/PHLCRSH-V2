"""Assemble the final per-segment analytical table.

Runs each data prep module, joins every result onto the master centerline
table by seg_id, and writes one GeoPackage to disk.

Final schema (one row per driveable centerline segment):

    Identity & geometry
        seg_id, geometry, length, st_name, st_type, class, oneway

    Crashes (target variables)
        crash_count, fatal_count, injury_count,
        susp_serious_inj_count, ped_count, bicycle_count,
        severity_score

    Physical road design
        cartway_width_ft, width_confidence, cartway_n_valid
        state_lane_cnt, state_total_width_ft, state_divisor_type,
        is_divided, bike_lane
        osm_lanes, osm_maxspeed, osm_highway
        maxspeed_inferred (from class), maxspeed_final (merged)

    Traffic
        dvrpc_aadt, has_aadt, aadt_distance_ft
        state_aadt

    Intersection & calming
        has_any_control, has_signal, has_all_way_stop,
        has_conventional_stop, calming_device_count, has_calming

    Natural environment
        canopy_pct, has_canopy, tree_count
        grade_range_smooth, grade_smooth_median,
        grade_smooth_p90, grade_smooth_max

    Context / confounders
        GEOID, median_income, population, median_rent, median_age,
        white_alone, vacant_units, commute_* fields
"""
from __future__ import annotations

import os

import geopandas as gpd
import numpy as np
import pandas as pd

from data_prep.common import stash
from data_prep.centerlines import load_centerlines
from data_prep.crashes import load_crashes, aggregate_crashes_to_segments
from data_prep.widths import compute_segment_widths
from data_prep.state_roads import load_state_roads, join_state_roads_to_centerlines
from data_prep.traffic_calming import load_calming_devices, aggregate_calming_to_segments
from data_prep.intersection_controls import (
    load_intersection_controls, aggregate_controls_to_segments,
)
from data_prep.traffic_counts import load_traffic_counts, join_aadt_to_segments
from data_prep.osm_features import load_osm_edges, join_osm_to_centerlines
from data_prep.census import build_block_groups_with_acs, join_bg_to_segments
from data_prep.canopy import compute_canopy_pct
from data_prep.elevation import compute_grade
from data_prep.trees import load_trees, count_trees_per_segment


OUTPUT_PATH = stash("philly_final_analytical_table.gpkg")


def _left_merge(master: gpd.GeoDataFrame, df: pd.DataFrame, on: str = "seg_id") -> gpd.GeoDataFrame:
    master["seg_id"] = master["seg_id"].astype("Int64")
    df[on] = df[on].astype("Int64")
    return master.merge(df, on=on, how="left")


def build() -> gpd.GeoDataFrame:
    print("Loading centerlines...")
    cl = load_centerlines()

    print("Crashes...")
    crashes = load_crashes()
    crash_agg = aggregate_crashes_to_segments(crashes, cl)
    cl = _left_merge(cl, crash_agg)
    for c in ["crash_count", "fatal_count", "injury_count",
              "susp_serious_inj_count", "ped_count", "bicycle_count",
              "severity_score"]:
        cl[c] = cl[c].fillna(0).astype(int)

    print("Cartway widths...")
    widths = compute_segment_widths(cl)
    cl = _left_merge(cl, widths)

    print("State roads...")
    sr = load_state_roads()
    sr_joined = join_state_roads_to_centerlines(sr, cl)
    cl = _left_merge(cl, sr_joined)

    print("OSM speed/lanes...")
    edges = load_osm_edges()
    osm_joined = join_osm_to_centerlines(edges, cl)
    cl = _left_merge(cl, osm_joined)

    print("DVRPC traffic counts...")
    counts = load_traffic_counts()
    aadt = join_aadt_to_segments(counts, cl)
    cl = _left_merge(cl, aadt)

    print("Traffic calming...")
    devices = load_calming_devices()
    calming = aggregate_calming_to_segments(devices)
    cl = _left_merge(cl, calming)
    cl["calming_device_count"] = cl["calming_device_count"].fillna(0).astype(int)
    cl["has_calming"] = cl["has_calming"].fillna(False)

    print("Intersection controls...")
    controls = load_intersection_controls()
    controls_agg = aggregate_controls_to_segments(controls, cl)
    cl = _left_merge(cl, controls_agg)
    for c in ["has_any_control", "has_signal", "has_all_way_stop", "has_conventional_stop"]:
        cl[c] = cl[c].fillna(0).astype(int)

    print("Census block groups...")
    bg = build_block_groups_with_acs()
    bg_joined = join_bg_to_segments(bg, cl)
    cl = _left_merge(cl, bg_joined)

    print("Canopy...")
    canopy = compute_canopy_pct(cl)
    cl = _left_merge(cl, canopy)

    print("Trees...")
    trees = load_trees()
    tree_counts = count_trees_per_segment(trees, cl)
    cl = _left_merge(cl, tree_counts)
    cl["tree_count"] = cl["tree_count"].fillna(0).astype(int)

    print("Elevation / grade...")
    grade = compute_grade(cl)
    cl = _left_merge(cl, grade)

    # Final maxspeed: prefer state road (authoritative), then OSM, then class-inferred.
    cl["maxspeed_final"] = (
        cl["osm_maxspeed"]
        .fillna(cl["maxspeed_inferred"])
    )

    # Final lane count: prefer state road, then OSM.
    cl["lanes_final"] = cl["state_lane_cnt"].fillna(cl["osm_lanes"])

    return cl


def save(final_table: gpd.GeoDataFrame, path: str = OUTPUT_PATH) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    final_table.to_file(path, layer="segments", driver="GPKG")
    print(f"Wrote {len(final_table):,} segments to {path}")


if __name__ == "__main__":
    final = build()
    save(final)
    print("\nColumn summary:")
    for col in final.columns:
        nulls = final[col].isna().sum()
        print(f"  {col:40s}  {str(final[col].dtype):15s}  nulls={nulls:,}")
