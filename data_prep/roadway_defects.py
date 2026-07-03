"""Philadelphia 311 roadway defect request data prep module.

Pulls Street Defect and Street Paving requests from the City of Philadelphia
CARTO SQL API, builds point geometry from the published lon/lat fields, and
snaps each request to its nearest street centerline segment.
"""
from __future__ import annotations

import os
from datetime import date, timedelta

import geopandas as gpd
import pandas as pd
import requests

from .common import EPSG, raw, transformed

CARTO_SQL_URL = "https://phl.carto.com/api/v2/sql"
START_YEAR = 2020
ROADWAY_DEFECT_SNAP_FT = 100
CACHE_MAX_AGE = timedelta(days=1)
SERVICE_CODES = ("SR-ST01", "SR-ST23")


def _cache_is_fresh(path: str) -> bool:
    if not os.path.exists(path):
        return False
    modified = date.fromtimestamp(os.path.getmtime(path))
    return date.today() - modified < CACHE_MAX_AGE


def _year_ranges(start_year: int = START_YEAR) -> list[tuple[str, str]]:
    current_year = date.today().year
    return [
        (f"{year}-01-01", f"{year + 1}-01-01")
        for year in range(start_year, current_year + 1)
    ]


def _fetch_rows(start_date: str, end_date: str) -> list[dict]:
    codes = ", ".join(f"'{code}'" for code in SERVICE_CODES)
    sql = f"""
        SELECT
            cartodb_id,
            service_request_id,
            requested_datetime,
            updated_datetime,
            status,
            service_name,
            service_code,
            address,
            lon,
            lat
        FROM public_cases_fc
        WHERE requested_datetime >= '{start_date}'
          AND requested_datetime < '{end_date}'
          AND service_code IN ({codes})
          AND lon IS NOT NULL
          AND lat IS NOT NULL
        ORDER BY requested_datetime
    """
    response = requests.get(CARTO_SQL_URL, params={"q": sql}, timeout=120)
    response.raise_for_status()
    payload = response.json()
    if payload.get("error"):
        raise RuntimeError(f"CARTO SQL API error for {start_date} to {end_date}: {payload['error']}")
    return payload.get("rows", [])


def _download_roadway_requests() -> pd.DataFrame:
    rows: list[dict] = []
    for start_date, end_date in _year_ranges():
        print(f"Downloading 311 roadway requests {start_date} to {end_date}...")
        rows.extend(_fetch_rows(start_date, end_date))

    df = pd.DataFrame(rows)
    if df.empty:
        return pd.DataFrame(columns=[
            "cartodb_id",
            "service_request_id",
            "requested_datetime",
            "updated_datetime",
            "status",
            "service_name",
            "service_code",
            "address",
            "lon",
            "lat",
        ])

    df["lon"] = pd.to_numeric(df["lon"], errors="coerce")
    df["lat"] = pd.to_numeric(df["lat"], errors="coerce")
    df = df.dropna(subset=["lon", "lat"])
    df = df[df["service_code"].isin(SERVICE_CODES)]
    return df


def load_roadway_defects() -> gpd.GeoDataFrame:
    """Load 311 Street Defect and Street Paving points, refreshing daily."""
    cached_raw = raw("311 Service Requests", "roadway_defects_2020_present.csv")
    cached_2272 = transformed("311 Service Requests", "roadway_defects_2272.geojson")

    if _cache_is_fresh(cached_2272):
        return gpd.read_file(cached_2272)

    if _cache_is_fresh(cached_raw):
        df = pd.read_csv(cached_raw)
    else:
        df = _download_roadway_requests()
        os.makedirs(os.path.dirname(cached_raw), exist_ok=True)
        df.to_csv(cached_raw, index=False)

    if df.empty:
        gdf = gpd.GeoDataFrame(df, geometry=[], crs="EPSG:4326")
    else:
        gdf = gpd.GeoDataFrame(
            df,
            geometry=gpd.points_from_xy(df["lon"], df["lat"]),
            crs="EPSG:4326",
        )

    os.makedirs(os.path.dirname(cached_2272), exist_ok=True)
    gdf_2272 = gdf.to_crs(EPSG)
    gdf_2272.to_file(cached_2272, driver="GeoJSON")
    return gdf_2272


def aggregate_roadway_defects_to_segments(
    requests_gdf: gpd.GeoDataFrame,
    centerlines: gpd.GeoDataFrame,
    snap_ft: float = ROADWAY_DEFECT_SNAP_FT,
) -> pd.DataFrame:
    """Snap 311 roadway requests to centerlines and count requests per segment."""
    columns = [
        "seg_id",
        "roadway_request_count",
        "roadway_defect_count",
        "roadway_paving_request_count",
        "roadway_open_request_count",
    ]
    if requests_gdf.empty:
        return pd.DataFrame(columns=columns)

    snapped = gpd.sjoin_nearest(
        requests_gdf,
        centerlines[["seg_id", "geometry"]],
        how="inner",
        max_distance=snap_ft,
        distance_col="roadway_request_dist_ft",
    )
    if snapped.empty:
        return pd.DataFrame(columns=columns)

    request_id_col = "service_request_id" if "service_request_id" in snapped.columns else "cartodb_id"
    snapped = (
        snapped.sort_values("roadway_request_dist_ft")
        .drop_duplicates(subset=request_id_col, keep="first")
    )

    by_code = (
        snapped.groupby(["seg_id", "service_code"])
        .size()
        .unstack(fill_value=0)
    )
    out = pd.DataFrame(index=by_code.index)
    out["roadway_defect_count"] = by_code.get("SR-ST01", 0)
    out["roadway_paving_request_count"] = by_code.get("SR-ST23", 0)
    out["roadway_request_count"] = out["roadway_defect_count"] + out["roadway_paving_request_count"]

    status = snapped["status"].fillna("").astype(str).str.lower()
    open_mask = ~status.isin({"closed", "canceled", "cancelled"})
    open_counts = snapped.loc[open_mask].groupby("seg_id").size()
    out["roadway_open_request_count"] = open_counts.reindex(out.index, fill_value=0)

    return out.reset_index()[columns]
