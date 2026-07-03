"""Philadelphia street poles/streetlights data prep module.

Downloads the Street Poles inventory from the City of Philadelphia's ArcGIS REST API,
projects it to EPSG:2272, and aggregates pole counts within a buffer around each street centerline segment.
"""
from __future__ import annotations

import os
import geopandas as gpd
import pandas as pd
import requests

from .common import raw, transformed, to_2272_file

LIGHT_BUFFER_FT = 50  # Buffer distance around centerline to count streetlights


def load_streetlights() -> gpd.GeoDataFrame:
    """Load Philly street poles (downloading from ArcGIS REST if not cached)."""
    cached_raw = raw("Street Lights", "street_poles_raw.geojson")
    cached_2272 = transformed("Street Lights", "street_poles_2272.geojson")

    if not os.path.exists(cached_raw):
        print("Downloading Street Poles dataset from ArcGIS REST API...")
        url = "https://services.arcgis.com/fLeGjb7u4uXqeF9q/arcgis/rest/services/Street_Poles/FeatureServer/0/query"
        params = {
            "where": "1=1",
            "outSR": 4326,
            "outFields": "objectid",
            "f": "geojson",
        }
        r = requests.get(url, params=params)
        r.raise_for_status()
        os.makedirs(os.path.dirname(cached_raw), exist_ok=True)
        with open(cached_raw, "w") as f:
            f.write(r.text)
        lights = gpd.read_file(cached_raw)
    else:
        lights = gpd.read_file(cached_raw)

    return to_2272_file(lights, cached_2272)


def aggregate_streetlights_to_segments(
    lights: gpd.GeoDataFrame,
    centerlines: gpd.GeoDataFrame,
    buffer_ft: float = LIGHT_BUFFER_FT,
) -> pd.DataFrame:
    """Count the number of streetlights within buffer_ft of each segment."""
    buffered = centerlines[["seg_id", "geometry"]].copy()
    buffered.geometry = buffered.geometry.buffer(buffer_ft)

    joined = gpd.sjoin(
        lights,
        buffered,
        how="inner",
        predicate="intersects"
    )

    counts = (
        joined.groupby("seg_id")
        .size()
        .reset_index(name="nighttime_illumination")
    )
    return counts
