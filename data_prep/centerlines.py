"""Street centerlines - the master table everything else joins onto.

Centerline CLASS codes (Philly Streets Dept):
    1  Expressway
    2  Major Arterial
    3  Minor Arterial
    4  Collector
    5  Local
    6  Driveway
    9  Low Speed Ramp
    10 High Speed Ramp
    12 Non-travelable
    13 (undocumented, inconsistent)
    14 City Boundary
    15 Walking Connector
    18 Traffic Controlled Crosswalk

We exclude 6, 12, 13, 14, 15, 18 as non-driveable / not relevant to crash analysis.
"""
from __future__ import annotations

import geopandas as gpd

from .common import raw, transformed, to_2272_file

EXCLUDE_CLASSES = [6, 12, 13, 14, 15, 18]

# Inferred speed limits by centerline class, used when no OSM/state-road override exists.
SPEED_BY_CLASS = {
    1: 55,   # Expressway
    2: 35,   # Major Arterial
    3: 30,   # Minor Arterial
    4: 30,   # Collector
    5: 25,   # Local
    9: 25,   # Low Speed Ramp
    10: 45,  # High Speed Ramp
}


def load_centerlines() -> gpd.GeoDataFrame:
    """Load Philly street centerlines in EPSG:2272, filtered to driveable classes."""
    src_path = raw("Street Centerline Data", "Street_Centerline.geojson")
    cache_path = transformed("Street Centerline Data", "2272_centerlines.geojson")

    cl = gpd.read_file(src_path)
    cl_2272 = to_2272_file(cl, cache_path)

    master = cl_2272[~cl_2272["class"].isin(EXCLUDE_CLASSES)].copy()

    # Normalize seg_id dtype for downstream joins
    master["seg_id"] = master["seg_id"].astype("Int64")

    # Inferred speed from class (overridden later where better data exists)
    master["maxspeed_inferred"] = master["class"].map(SPEED_BY_CLASS)

    return master
