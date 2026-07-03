"""Philadelphia bike network data prep module.

Downloads the bike network dataset from the City of Philadelphia's ArcGIS REST API,
projects it to EPSG:2272, snaps it to street centerlines using midpoint-nearest logic,
and classifies each segment's bike infrastructure into: Protected, Painted, Sharrow, None.
"""
from __future__ import annotations

import os
import geopandas as gpd
import pandas as pd
import requests

from .common import raw, transformed, to_2272_file, get_midpoint, EPSG

BIKE_MATCH_FT = 50  # Snapping distance (feet)


def load_bike_network() -> gpd.GeoDataFrame:
    """Load Philly bike network (downloading from ArcGIS REST if not cached)."""
    cached_raw = raw("Bike Network", "bike_network_raw.geojson")
    cached_2272 = transformed("Bike Network", "bike_network_2272.geojson")

    if not os.path.exists(cached_raw):
        print("Downloading Bike Network dataset from ArcGIS REST API...")
        url = "https://services.arcgis.com/fLeGjb7u4uXqeF9q/arcgis/rest/services/Bike_Network/FeatureServer/0/query"
        params = {
            "where": "1=1",
            "outSR": 4326,
            "outFields": "*",
            "f": "geojson",
        }
        r = requests.get(url, params=params)
        r.raise_for_status()
        os.makedirs(os.path.dirname(cached_raw), exist_ok=True)
        with open(cached_raw, "w") as f:
            f.write(r.text)
        bike = gpd.read_file(cached_raw)
    else:
        bike = gpd.read_file(cached_raw)

    return to_2272_file(bike, cached_2272)


def classify_infra(facityp: str | None, bikewaytyp: str | None) -> str:
    """Classify bike infrastructure tier based on type fields."""
    facityp_lower = str(facityp).lower() if pd.notna(facityp) else ""
    bikeway_lower = str(bikewaytyp).lower() if pd.notna(bikewaytyp) else ""

    if "separated" in facityp_lower or "separated" in bikeway_lower or "sidepath" in bikeway_lower:
        return "Protected"
    if "painted" in facityp_lower or "painted" in bikeway_lower or "bus/bike" in bikeway_lower:
        return "Painted"
    if "advisory" in facityp_lower or "shared" in facityp_lower or "sharrow" in bikeway_lower:
        return "Sharrow"
    return "None"


def join_bike_network_to_segments(
    bike_net: gpd.GeoDataFrame,
    centerlines: gpd.GeoDataFrame,
    max_dist_ft: float = BIKE_MATCH_FT,
) -> pd.DataFrame:
    """Nearest midpoint join. Returns a DataFrame keyed by seg_id with bike_infra_type."""
    cl_pts = centerlines[["seg_id", "geometry"]].copy()
    cl_pts.geometry = get_midpoint(centerlines)

    bike_pts = bike_net.copy()
    bike_pts.geometry = get_midpoint(bike_net)

    cols = ["facityp", "bikewaytyp", "geometry"]
    matched = gpd.sjoin_nearest(
        cl_pts,
        bike_pts[cols],
        how="left",
        max_distance=max_dist_ft,
        distance_col="bike_net_distance",
    )
    matched = (
        matched.sort_values("bike_net_distance")
        .drop_duplicates(subset="seg_id", keep="first")
    )

    # Classify each segment's infrastructure
    matched["bike_infra_type"] = matched.apply(
        lambda r: classify_infra(r["facityp"], r["bikewaytyp"]), axis=1
    )

    # If distance is too far or no match, it is "None"
    matched.loc[matched["bike_infra_type"].isna() | matched["bike_net_distance"].isna(), "bike_infra_type"] = "None"

    return matched[["seg_id", "bike_infra_type"]]
