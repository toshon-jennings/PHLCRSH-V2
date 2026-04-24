"""Census block groups + ACS 5-year variables (2024).

Poverty (B17001_002E) was dropped because it's suppressed at the block
group level for much of Philly. Median income is our main SES proxy.

Variables pulled:
    B19013_001E  Median household income
    B01003_001E  Total population
    B08301_001E  Total commuters
    B08301_003E  Drove alone
    B08301_010E  Public transit
    B08301_019E  Walked
    B08301_021E  Worked from home
    B02001_002E  White alone
    B25002_003E  Vacant units
    B25058_001E  Median contract rent
    B01002_001E  Median age
"""
from __future__ import annotations

import os

import census
import geopandas as gpd
import pandas as pd
import pygris

from .common import raw, transformed, to_2272_file, EPSG

BG_VARS = (
    "NAME",
    "B19013_001E",
    "B01003_001E",
    "B08301_001E",
    "B08301_003E",
    "B08301_010E",
    "B08301_019E",
    "B08301_021E",
    "B02001_002E",
    "B25002_003E",
    "B25058_001E",
    "B01002_001E",
)

RENAME = {
    "B19013_001E": "median_income",
    "B01003_001E": "population",
    "B08301_001E": "commuters_total",
    "B08301_003E": "commute_drove_alone",
    "B08301_010E": "commute_transit",
    "B08301_019E": "commute_walked",
    "B08301_021E": "commute_wfh",
    "B02001_002E": "white_alone",
    "B25002_003E": "vacant_units",
    "B25058_001E": "median_rent",
    "B01002_001E": "median_age",
}


def load_block_groups(year: int = 2024) -> gpd.GeoDataFrame:
    cache_path = raw("Census", "phila_block_groups_2024_4269.geojson")
    if os.path.exists(cache_path):
        bg = gpd.read_file(cache_path)
    else:
        bg = pygris.block_groups(state="PA", county="Philadelphia", year=year)
        os.makedirs(os.path.dirname(cache_path), exist_ok=True)
        bg.to_file(cache_path, driver="GeoJSON")

    # Project to EPSG:2272
    cache_2272 = transformed("Census", "phila_block_groups_2272.geojson")
    return to_2272_file(bg, cache_2272)


def load_acs_blockgroup(year: int = 2024) -> pd.DataFrame:
    api_key = os.environ.get("CENSUS_API_KEY")
    if not api_key:
        raise RuntimeError("Set CENSUS_API_KEY environment variable.")

    cen = census.Census(api_key)
    raw_rows = cen.acs5.state_county_blockgroup(
        fields=BG_VARS,
        state_fips="42",
        county_fips="101",
        blockgroup="*",
        year=year,
    )
    df = pd.DataFrame(raw_rows)
    df = df.rename(columns=RENAME)
    df["GEOID"] = df["state"] + df["county"] + df["tract"] + df["block group"]
    return df


def build_block_groups_with_acs(year: int = 2024) -> gpd.GeoDataFrame:
    """Join ACS attributes to block group geometry."""
    bg = load_block_groups(year)
    acs = load_acs_blockgroup(year)
    return bg.merge(acs, on="GEOID", how="left")


def join_bg_to_segments(
    bg: gpd.GeoDataFrame,
    centerlines: gpd.GeoDataFrame,
) -> pd.DataFrame:
    """Assign each centerline to the block group containing its midpoint."""
    cl_pts = centerlines[["seg_id", "geometry"]].copy()
    cl_pts["geometry"] = cl_pts.geometry.interpolate(0.5, normalized=True)

    keep_cols = ["GEOID"] + list(RENAME.values())
    joined = gpd.sjoin(
        cl_pts,
        bg[keep_cols + ["geometry"]],
        how="left",
        predicate="within",
    )
    joined = joined.drop_duplicates(subset="seg_id", keep="first")
    return joined[["seg_id"] + keep_cols]
