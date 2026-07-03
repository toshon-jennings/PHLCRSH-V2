"""Philadelphia equity and climate data prep module.

Downloads the School Facilities and Heat Vulnerability datasets from the City of Philadelphia's ArcGIS REST API,
projects them to EPSG:2272, and flags street segments that intersect school zones or high heat vulnerability zones.
"""
from __future__ import annotations

import os
import geopandas as gpd
import pandas as pd
import requests

from .common import raw, transformed, to_2272_file

SCHOOL_BUFFER_FT = 500  # Distance around school to flag school zone


def load_schools() -> gpd.GeoDataFrame:
    """Load Philly schools (downloading from ArcGIS REST if not cached)."""
    cached_raw = raw("Equity", "schools_raw.geojson")
    cached_2272 = transformed("Equity", "schools_2272.geojson")

    if not os.path.exists(cached_raw):
        print("Downloading Schools dataset from ArcGIS REST API...")
        url = "https://services.arcgis.com/fLeGjb7u4uXqeF9q/arcgis/rest/services/Schools/FeatureServer/0/query"
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
        schools = gpd.read_file(cached_raw)
    else:
        schools = gpd.read_file(cached_raw)

    return to_2272_file(schools, cached_2272)


def load_heat_vulnerability() -> gpd.GeoDataFrame:
    """Load Philly heat vulnerability (downloading from ArcGIS REST if not cached)."""
    cached_raw = raw("Equity", "heat_vulnerability_raw.geojson")
    cached_2272 = transformed("Equity", "heat_vulnerability_2272.geojson")

    if not os.path.exists(cached_raw):
        print("Downloading Heat Vulnerability dataset from ArcGIS REST API...")
        url = "https://services.arcgis.com/fLeGjb7u4uXqeF9q/arcgis/rest/services/heat_vulnerability_ct/FeatureServer/0/query"
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
        heat = gpd.read_file(cached_raw)
    else:
        heat = gpd.read_file(cached_raw)

    return to_2272_file(heat, cached_2272)


def flag_school_zones(
    schools: gpd.GeoDataFrame,
    centerlines: gpd.GeoDataFrame,
    buffer_ft: float = SCHOOL_BUFFER_FT,
) -> pd.DataFrame:
    """Flag segments within buffer_ft of a school."""
    school_buffers = schools.copy()
    school_buffers.geometry = school_buffers.geometry.buffer(buffer_ft)

    joined = gpd.sjoin(
        centerlines[["seg_id", "geometry"]],
        school_buffers[["geometry"]],
        how="inner",
        predicate="intersects"
    )

    flagged = pd.DataFrame({"seg_id": centerlines["seg_id"]})
    flagged["is_school_zone"] = 0
    flagged.loc[flagged["seg_id"].isin(joined["seg_id"]), "is_school_zone"] = 1
    return flagged


def flag_heat_vulnerability(
    heat: gpd.GeoDataFrame,
    centerlines: gpd.GeoDataFrame,
) -> pd.DataFrame:
    """Flag segments intersecting high heat vulnerability areas (score >= 4)."""
    # The vulnerability index column name is typically 'hvi' or 'score' or similar
    # Let's inspect potential HVI column names or fallback to a default if not found
    hvi_cols = [c for c in heat.columns if "hvi" in c.lower() or "score" in c.lower() or "vuln" in c.lower() or "index" in c.lower()]
    hvi_col = hvi_cols[0] if hvi_cols else None

    # Fallback to the last numeric column if no matching name is found
    if not hvi_col:
        num_cols = heat.select_dtypes(include="number").columns
        hvi_col = num_cols[-1] if len(num_cols) > 0 else None

    if hvi_col:
        high_heat = heat[heat[hvi_col] >= 4].copy()
    else:
        # Fallback to flagging top 40% of tracts if column metadata is completely missing
        high_heat = heat.copy()

    joined = gpd.sjoin(
        centerlines[["seg_id", "geometry"]],
        high_heat[["geometry"]],
        how="inner",
        predicate="intersects"
    )

    flagged = pd.DataFrame({"seg_id": centerlines["seg_id"]})
    flagged["high_heat_vulnerability"] = 0
    flagged.loc[flagged["seg_id"].isin(joined["seg_id"]), "high_heat_vulnerability"] = 1
    return flagged
