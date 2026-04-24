"""DVRPC traffic counts (AADT).

Coverage is solid on major arterials but sparse on residential streets.
We attribute the AADT of the nearest count station within 500 ft to a
segment, and flag segments that got a match.
"""
from __future__ import annotations

import os

import geopandas as gpd
import pandas as pd
import requests

from .common import raw, transformed, to_2272_file

AADT_SNAP_FT = 500


def load_traffic_counts(year: int = 2024) -> gpd.GeoDataFrame:
    cached_raw = raw("DVRPC Traffic Count", f"dvrpc_{year}_philly_traffic_counts.geojson")
    cached_2272 = transformed("DVRPC Traffic Count", f"dvrpc_{year}_philly_traffic_counts_2272.geojson")

    if not os.path.exists(cached_raw):
        url = "https://arcgis.dvrpc.org/portal/rest/services/transportation/trafficcounts/FeatureServer/0/query"
        params = {
            "where": f"setyear={year} AND co_name LIKE 'Phil%'",
            "outsr": 4326,
            "outfields": "*",
            "f": "geojson",
        }
        r = requests.get(url, params=params)
        counts = gpd.read_file(r.text)
        os.makedirs(os.path.dirname(cached_raw), exist_ok=True)
        counts.to_file(cached_raw, driver="GeoJSON")
    else:
        counts = gpd.read_file(cached_raw)

    return to_2272_file(counts, cached_2272)


def join_aadt_to_segments(
    counts: gpd.GeoDataFrame,
    centerlines: gpd.GeoDataFrame,
    max_dist_ft: float = AADT_SNAP_FT,
) -> pd.DataFrame:
    """Nearest count station per segment within max_dist_ft. Returns seg_id + AADT."""
    matched = gpd.sjoin_nearest(
        centerlines[["seg_id", "geometry"]],
        counts[["volume", "geometry"]],
        how="left",
        max_distance=max_dist_ft,
        distance_col="aadt_distance_ft",
    )
    matched = (
        matched.sort_values("aadt_distance_ft")
        .drop_duplicates(subset="seg_id", keep="first")
    )
    matched = matched.rename(columns={"volume": "dvrpc_aadt"})
    matched["has_aadt"] = matched["dvrpc_aadt"].notna()
    return matched[["seg_id", "dvrpc_aadt", "aadt_distance_ft", "has_aadt"]]
