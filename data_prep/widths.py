"""Cartway width per centerline segment via perpendicular transects.

Approach: build perpendicular transects along each centerline at fixed
spacing, intersect them with cartway polygons, and take the median of the
resulting widths as the segment's width. Yields a paved_median_ft and a
span_median_ft plus a confidence flag.

Curbs FCODE values used:
    1000,1001   cartway (paved travelway)
    1010-1012   concrete islands (divider indicator)
    1020-1022   shoulders
    1030-1032   grass islands (divider indicator)
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import geopandas as gpd
import shapely
from shapely import make_valid
from shapely.geometry import LineString, Point
from shapely.ops import unary_union

from .common import raw, transformed, stash, EPSG, to_2272_file

ROADWAY_FCODES = [1000, 1001]
ISLAND_FCODES = [1010, 1011, 1012, 1030, 1031, 1032]


# ---- Curb loading ----

def load_curbs_2272() -> gpd.GeoDataFrame:
    src_path = raw("Curbs and Cartways", "Curbs.geojson")
    cache_path = transformed("Curbs and Cartways", "Curbs.geojson")
    curbs = gpd.read_file(src_path)
    return to_2272_file(curbs, cache_path)


def split_curbs(curbs: gpd.GeoDataFrame) -> tuple[gpd.GeoDataFrame, gpd.GeoDataFrame]:
    roadways = curbs[curbs["fcode"].isin(ROADWAY_FCODES)].copy()
    islands = curbs[curbs["fcode"].isin(ISLAND_FCODES)].copy()
    return roadways, islands


# ---- Geometry helpers ----

def _prep_gdf(gdf: gpd.GeoDataFrame, epsg: int = EPSG) -> gpd.GeoDataFrame:
    if gdf.crs is None:
        raise ValueError("Input GeoDataFrame has no CRS.")
    out = gdf.to_crs(epsg).copy()
    out = out[out.geometry.notna() & ~out.geometry.is_empty].copy()
    out["geometry"] = out.geometry.map(lambda g: make_valid(g) if not g.is_valid else g)
    out = out[out.geometry.notna() & ~out.geometry.is_empty].copy()
    return out


def _line_parts(g) -> list:
    """Extract only line pieces from a geometry (ignore points that add no width)."""
    if g is None or g.is_empty:
        return []
    if g.geom_type == "LineString":
        return [g] if g.length > 0 else []
    if g.geom_type == "MultiLineString":
        return [p for p in g.geoms if p.length > 0]
    if g.geom_type == "GeometryCollection":
        parts = []
        for p in g.geoms:
            parts.extend(_line_parts(p))
        return parts
    return []


# ---- Transect construction ----

def make_perpendicular_transects(
    centerlines: gpd.GeoDataFrame,
    id_col: str = "cl_id",
    spacing_ft: float = 75,
    trim_ft: float = 50,
    half_len_ft: float = 125,
    tangent_delta_ft: float = 5,
) -> gpd.GeoDataFrame:
    """Build perpendicular cross-sections every spacing_ft along each centerline."""
    rows = []
    for _, row in centerlines.iterrows():
        line = row.geometry
        if line is None or line.is_empty or line.length <= 0:
            continue

        L = float(line.length)
        trim = min(float(trim_ft), max(0.0, (L - 1.0) / 2.0))

        if L - 2 * trim < max(1.0, spacing_ft):
            stations = np.array([L / 2.0])
        else:
            stations = np.arange(trim, L - trim + 1e-9, float(spacing_ft))
            if len(stations) == 0:
                stations = np.array([L / 2.0])

        for j, s in enumerate(stations):
            p = line.interpolate(float(s))
            s0 = max(0.0, float(s) - float(tangent_delta_ft))
            s1 = min(L, float(s) + float(tangent_delta_ft))
            if s1 <= s0:
                continue

            a = line.interpolate(s0)
            b = line.interpolate(s1)
            dx, dy = b.x - a.x, b.y - a.y
            d = np.hypot(dx, dy)
            if d == 0:
                continue

            # perpendicular unit vector
            nx, ny = -dy / d, dx / d
            transect = LineString([
                (p.x - half_len_ft * nx, p.y - half_len_ft * ny),
                (p.x + half_len_ft * nx, p.y + half_len_ft * ny),
            ])
            rows.append({
                id_col: row[id_col],
                "transect_no": j,
                "station_ft": float(s),
                "geometry": transect,
            })

    return gpd.GeoDataFrame(rows, geometry="geometry", crs=centerlines.crs)


# ---- Transect measurement ----

def measure_transect_widths(
    transects: gpd.GeoDataFrame,
    surfaces: gpd.GeoDataFrame,
    id_col: str = "cl_id",
    grid_size_ft: float | None = None,
) -> gpd.GeoDataFrame:
    """Intersect each transect with cartway polygons and measure width.

    paved_width_ft = total length of line pieces that fall inside the cartway
    span_width_ft  = outermost-to-outermost extent across the transect
    """
    if transects.empty:
        return gpd.GeoDataFrame(columns=[id_col, "paved_width_ft", "span_width_ft"],
                                geometry="geometry", crs=transects.crs)

    surfaces = surfaces.to_crs(transects.crs)
    pairs = surfaces.sindex.query(transects.geometry, predicate="intersects")

    groups: dict[int, np.ndarray] = {}
    if pairs.size:
        pair_df = pd.DataFrame({"tx_pos": pairs[0], "surf_pos": pairs[1]})
        for tx_pos, g in pair_df.groupby("tx_pos", sort=False):
            groups[int(np.asarray(tx_pos).item())] = g["surf_pos"].to_numpy(dtype=np.int64)

    records = []
    tx_geoms = transects.geometry.to_numpy()
    surface_geoms = surfaces.geometry.reset_index(drop=True)

    for tx_pos, t in enumerate(tx_geoms):
        surf_pos = groups.get(tx_pos)
        if surf_pos is None or len(surf_pos) == 0:
            paved_width = np.nan
            span_width = np.nan
            n_parts = 0
            center_covered = False
        else:
            surf = unary_union(list(surface_geoms.iloc[surf_pos].values))
            if grid_size_ft:
                inter = shapely.intersection(t, surf, grid_size=grid_size_ft)
            else:
                inter = t.intersection(surf)
            parts = _line_parts(inter)
            paved_width = float(sum(p.length for p in parts)) if parts else np.nan
            n_parts = len(parts)
            if parts:
                projected_ends = []
                for p in parts:
                    projected_ends.append(t.project(Point(p.coords[0])))
                    projected_ends.append(t.project(Point(p.coords[-1])))
                span_width = float(max(projected_ends) - min(projected_ends))
            else:
                span_width = np.nan
            center_covered = bool(surf.covers(t.interpolate(t.length / 2.0)))

        records.append({
            id_col: transects.iloc[tx_pos][id_col],
            "transect_no": transects.iloc[tx_pos]["transect_no"],
            "station_ft": transects.iloc[tx_pos]["station_ft"],
            "paved_width_ft": paved_width,
            "span_width_ft": span_width,
            "n_parts": n_parts,
            "center_covered": center_covered,
            "geometry": t,
        })

    return gpd.GeoDataFrame(records, geometry="geometry", crs=transects.crs)


def summarize_widths(
    raw_transects: gpd.GeoDataFrame,
    id_col: str = "cl_id",
    prefix: str = "cartway",
    min_width_ft: float = 4,
    max_width_ft: float = 250,
) -> pd.DataFrame:
    """Per-segment summary of the transect width measurements."""
    x = raw_transects.copy()
    x["valid_width"] = (
        x["span_width_ft"].notna()
        & x["span_width_ft"].between(min_width_ft, max_width_ft)
    )
    good = x[x["valid_width"]].copy()

    all_counts = x.groupby(id_col).size().rename(f"{prefix}_n_transects")
    valid_counts = good.groupby(id_col).size().rename(f"{prefix}_n_valid")

    stats = good.groupby(id_col).agg(
        span_median_ft=("span_width_ft", "median"),
        paved_median_ft=("paved_width_ft", "median"),
        parts_median=("n_parts", "median"),
        center_covered_share=("center_covered", "mean"),
    ).add_prefix(prefix + "_")

    summary = all_counts.to_frame().join(valid_counts).join(stats)
    summary[f"{prefix}_valid_share"] = (
        summary[f"{prefix}_n_valid"] / summary[f"{prefix}_n_transects"]
    )
    return summary.reset_index()


def widths_by_centerline(
    centerlines: gpd.GeoDataFrame,
    surfaces: gpd.GeoDataFrame,
    id_col: str = "cl_id",
    spacing_ft: float = 75,
    trim_ft: float = 50,
    half_len_ft: float = 125,
) -> tuple[gpd.GeoDataFrame, gpd.GeoDataFrame, gpd.GeoDataFrame]:
    """End-to-end: prep, transect, measure, summarize. Returns (summary_on_cl, raw, transects)."""
    cl = centerlines.copy()
    if id_col not in cl.columns:
        cl = cl.reset_index(drop=True)
        cl[id_col] = cl.index

    cl = _prep_gdf(cl)
    surfaces = _prep_gdf(surfaces)

    cl_parts = cl.explode(index_parts=False).reset_index(drop=True)
    cl_parts = cl_parts[
        cl_parts.geometry.geom_type.isin(["LineString", "MultiLineString"])
    ].copy()

    transects = make_perpendicular_transects(
        cl_parts, id_col=id_col,
        spacing_ft=spacing_ft, trim_ft=trim_ft, half_len_ft=half_len_ft,
    )
    raw_t = measure_transect_widths(transects, surfaces, id_col=id_col)
    summary = summarize_widths(raw_t, id_col=id_col)
    out = cl.merge(summary, on=id_col, how="left")
    return out, raw_t, transects


# ---- Entry point used by build_final_table ----

def compute_segment_widths(centerlines: gpd.GeoDataFrame) -> pd.DataFrame:
    """Return per-segment width data, loading from cache if available.

    Width computation takes ~30 min on the full network. We cache to GPKG.
    """
    cache_path = stash("philly_centerlines_cartway_widths.gpkg")

    import os
    if os.path.exists(cache_path):
        full_out = gpd.read_file(cache_path, layer="widths")
    else:
        curbs = load_curbs_2272()
        roadways, _islands = split_curbs(curbs)
        cl_for_widths = centerlines.copy()
        cl_for_widths = cl_for_widths.reset_index(drop=True)
        cl_for_widths["cl_id"] = cl_for_widths.index
        full_out, _raw, _tx = widths_by_centerline(cl_for_widths, roadways)
        os.makedirs(os.path.dirname(cache_path), exist_ok=True)
        full_out.to_file(cache_path, layer="widths", driver="GPKG")

    full_out["cartway_width_ft"] = full_out["cartway_paved_median_ft"]
    full_out["width_confidence"] = np.select(
        [
            full_out["cartway_n_valid"].fillna(0) >= 3,
            full_out["cartway_n_valid"].fillna(0) == 2,
            full_out["cartway_n_valid"].fillna(0) == 1,
        ],
        ["good", "okay", "low_one_or_two_transects"],
        default="missing",
    )

    return full_out[[
        "seg_id",
        "cartway_width_ft",
        "cartway_paved_median_ft",
        "cartway_span_median_ft",
        "cartway_valid_share",
        "cartway_n_valid",
        "width_confidence",
    ]].copy()
