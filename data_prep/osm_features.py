"""OSM-sourced speed limits and lane counts.

Coverage is best on major roads and thin on residential streets. We fall
back to state-road data (authoritative) and then to class-based inference
in the final table assembly.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import geopandas as gpd
import osmnx as ox

from .common import EPSG, get_midpoint

OSM_MATCH_FT = 25  # midpoint-to-midpoint tolerance for assigning OSM attrs to a centerline


def load_osm_edges() -> gpd.GeoDataFrame:
    g = ox.graph_from_place("Philadelphia, Pennsylvania, USA", network_type="drive")
    edges = ox.graph_to_gdfs(g, nodes=False)
    return edges


def _parse_lanes(val) -> float:
    if isinstance(val, list):
        return max(int(x) for x in val)
    if pd.isna(val):
        return np.nan
    return int(val)


def _parse_speed(val) -> float:
    if isinstance(val, list):
        return max(int(s.split()[0]) for s in val)
    if pd.isna(val):
        return np.nan
    return int(val.split()[0])


def join_osm_to_centerlines(
    edges: gpd.GeoDataFrame,
    centerlines: gpd.GeoDataFrame,
    max_dist_ft: float = OSM_MATCH_FT,
) -> pd.DataFrame:
    """Midpoint-nearest join of OSM edges to centerlines. Returns seg_id, osm_lanes, osm_maxspeed."""
    cl_pts = centerlines[["seg_id", "geometry"]].copy()
    cl_pts.geometry = get_midpoint(centerlines)

    edge_pts = edges.copy()
    edge_pts = edge_pts.to_crs(EPSG)
    edge_pts["geometry"] = get_midpoint(edges)

    matched = gpd.sjoin_nearest(
        cl_pts,
        edge_pts[["lanes", "maxspeed", "highway", "geometry"]],
        how="left",
        max_distance=max_dist_ft,
        distance_col="osm_distance_ft",
    )
    matched = (
        matched.sort_values("osm_distance_ft")
        .drop_duplicates(subset="seg_id", keep="first")
    )
    matched["osm_lanes"] = matched["lanes"].apply(_parse_lanes)
    matched["osm_maxspeed"] = matched["maxspeed"].apply(_parse_speed)

    return matched[["seg_id", "osm_lanes", "osm_maxspeed", "highway"]].rename(
        columns={"highway": "osm_highway"}
    )
