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
from data_prep.bike_network import load_bike_network, join_bike_network_to_segments
from data_prep.streetlights import load_streetlights, aggregate_streetlights_to_segments
from data_prep.equity import load_schools, load_heat_vulnerability, flag_school_zones, flag_heat_vulnerability


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
              "severity_score", "crash_count_day", "crash_count_night",
              "crash_count_clear", "crash_count_wet",
              "crash_count_day_clear", "crash_count_day_wet",
              "crash_count_night_clear", "crash_count_night_wet"]:
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

    # Phase 1: Exposure & Severity Baselining
    print("Computing Exposure & Severity metrics...")
    class_fallbacks = {
        "motorway": 50000.0,
        "trunk": 30000.0,
        "primary": 15000.0,
        "secondary": 8000.0,
        "tertiary": 4000.0,
        "residential": 500.0,
        "unclassified": 500.0,
        "service": 100.0
    }
    mapped_fallback = cl["class"].map(class_fallbacks).fillna(500.0)
    cl["adt"] = cl["state_aadt"].fillna(cl["dvrpc_aadt"]).fillna(mapped_fallback)
    cl["length"] = cl.geometry.length / 5280.0
    cl["vmt"] = cl["adt"] * cl["length"]
    cl["risk_index"] = np.where(
        cl["vmt"] > 0,
        (cl["crash_count"] * 1000000.0) / (cl["adt"] * cl["length"]),
        0.0
    )
    cl["has_fatality"] = np.where(cl["fatal_count"] > 0, 1, 0)
    cl["has_severe_injury"] = np.where(cl["susp_serious_inj_count"] > 0, 1, 0)

    # Phase 2: Micro-Infrastructure & Right-of-Way
    print("Joining Bike Network...")
    try:
        bike_net = load_bike_network()
        bike_joined = join_bike_network_to_segments(bike_net, cl)
        cl = _left_merge(cl, bike_joined)
    except Exception as e:
        print(f"Warning: Failed to load bike network ({e}), using fallback.")
        cl["bike_infra_type"] = "None"

    # Intersection Control categorisation
    cl["intersection_control"] = np.select(
        [cl["has_signal"] == 1, (cl["has_all_way_stop"] == 1) | (cl["has_conventional_stop"] == 1)],
        ["Signalized", "Stop-Controlled"],
        default="Uncontrolled"
    )

    # Phase 3: Temporal & Environmental Dynamics
    print("Joining Streetlights...")
    try:
        lights = load_streetlights()
        lights_agg = aggregate_streetlights_to_segments(lights, cl)
        cl = _left_merge(cl, lights_agg)
        cl["nighttime_illumination"] = cl["nighttime_illumination"].fillna(0).astype(int)
    except Exception as e:
        print(f"Warning: Failed to load streetlights ({e}), using fallback.")
        cl["nighttime_illumination"] = 0

    # Calculate sun-glare prone segments (azimuth/bearing E-W within 75-105 or 255-285 deg)
    try:
        coords = cl.geometry.apply(lambda geom: geom.coords)
        first_pt = coords.apply(lambda c: c[0])
        last_pt = coords.apply(lambda c: c[-1])
        dx = last_pt.apply(lambda p: p[0]) - first_pt.apply(lambda p: p[0])
        dy = last_pt.apply(lambda p: p[1]) - first_pt.apply(lambda p: p[1])
        angle = np.degrees(np.arctan2(dy, dx)) % 360.0
        bearing = (90.0 - angle) % 360.0
        cl["is_glare_prone"] = np.where(
            ((bearing >= 75.0) & (bearing <= 105.0)) |
            ((bearing >= 255.0) & (bearing <= 285.0)),
            1, 0
        )
    except Exception as e:
        print(f"Warning: Failed to calculate bearings ({e}), using fallback.")
        cl["is_glare_prone"] = 0

    # Phase 4: Equity & Climate Vulnerability Overlays
    print("Joining Schools...")
    try:
        schools = load_schools()
        schools_flagged = flag_school_zones(schools, cl)
        cl = _left_merge(cl, schools_flagged)
        cl["is_school_zone"] = cl["is_school_zone"].fillna(0).astype(int)
    except Exception as e:
        print(f"Warning: Failed to load schools ({e}), using fallback.")
        cl["is_school_zone"] = 0

    print("Joining Heat Vulnerability...")
    try:
        heat = load_heat_vulnerability()
        heat_flagged = flag_heat_vulnerability(heat, cl)
        cl = _left_merge(cl, heat_flagged)
        cl["high_heat_vulnerability"] = cl["high_heat_vulnerability"].fillna(0).astype(int)
    except Exception as e:
        print(f"Warning: Failed to load heat vulnerability ({e}), using fallback.")
        cl["high_heat_vulnerability"] = 0

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
