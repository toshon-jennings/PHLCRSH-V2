"""Traffic calming devices - speed cushions, bump-outs, etc.

The source dataset includes future/planned installs through 2026; we filter
to devices installed by end of 2024 to match the crash window.
"""
from __future__ import annotations

import geopandas as gpd
import pandas as pd

from .common import raw, transformed, to_2272_file

CUTOFF_DATE = "2025-01-01"


def load_calming_devices() -> gpd.GeoDataFrame:
    src_path = raw("Traffic Calming Devices", "traffic_calming_devices.geojson")
    cache_path = transformed("Traffic Calming Devices", "traffic_calming_devices_2272.geojson")
    devices = gpd.read_file(src_path)
    devices = to_2272_file(devices, cache_path)
    devices = devices[devices["install_dt"] < CUTOFF_DATE].copy()
    devices["seg_id"] = devices["seg_id"].astype("Int64")
    return devices


def aggregate_calming_to_segments(devices: gpd.GeoDataFrame) -> pd.DataFrame:
    """Count calming devices per seg_id. The source already has seg_id so no spatial join needed."""
    counts = (
        devices.groupby("seg_id")
        .size()
        .rename("calming_device_count")
        .reset_index()
    )
    counts["has_calming"] = counts["calming_device_count"] > 0
    return counts
