# %%
import pandas as pd
import geopandas as gpd
import numpy as np

from shapely.geometry.point import Point
from shapely.geometry import LineString

import rasterio
from rasterio.mask import mask
from rasterstats import zonal_stats
import osmnx as ox

from rasterio.plot import show
import matplotlib.pyplot as plt
import seaborn as sns
import cmocean.cm as cmo

import pygris
import census

import requests

import os

#%%


# transforms df to 2272 and writes it to specified filepath
# if filepath exists, read it and return
def to_2272_file(df, filepath):
    df_2272 = None;
    
    if not os.path.exists(filepath):
        print("write file")
        df_2272 = df.to_crs(2272)
        df_2272.to_file(filepath, driver="geoJSON")
    else:
        print("read file")
        df_2272 = gpd.read_file(filepath)

    return df_2272


def get_midpoint(gdf: gpd.GeoDataFrame): 
    return gdf.geometry.interpolate(0.5, normalized=True)


# %%

crash_data = gpd.read_file("raw-data/PennDOT Crash Data/collision_crash_2020_2024.geojson")

# %% [markdown]
# ## Data Acquisition and Setup
# 
# ### 2024 PennDOT Crash Data for Philadelphia
# 
# The crash data blah blah blah
# 
# #### Data Quality
# 
# ##### What does max_severity_level mean?
# 
# 0 - No injury
# 
# 1 - Fatal injury
# 2 - Suspected serious injury - Obvious b/c they can't move/operate
# 3 - Suspected minor injury - Evident to others, but not serious as above - brusies/bleeding etc
# 4 - Possible injury - Not evident but reported - knocked out - internal injuries
# 
# 8 - Injury, unknown severity
# 9 - Unknown
# 
# We're going to need to finesse this a bit. We could shuffle "No Injury" to 5 and have a severity scale. That kind of works, though "Possible injury" gives me a bit of pause - it could seemingly be as server as 3 (perhaps 2?).
# We could try to scale, but I'm leaning more toward using these as a categorical rather than ordinal.
# 

# %%

# main crash data
# crash_data.head(10)
print(crash_data.columns)
print(crash_data.crs) # 4326

print(crash_data["max_severity_level"].describe())
print(crash_data["max_severity_level"].value_counts(dropna=False))



# count    36303.000000
# mean         3.481503
# std          2.900757
# min          0.000000
# 25%          1.000000
# 50%          3.000000
# 75%          4.000000
# max          9.000000

# max_severity_level
# 3    14104
# 0     8494
# 8     5215
# 4     3328
# 9     2763
# 2     1779
# 1      620


sns.countplot(x="max_severity_level", data=crash_data)
plt.show()
crash_data["tcd_type"]
crash_data["tcd_func_cd"]

# %% [markdown]
# Other fields of interest. 
# Weather1 and Weather2 have Lots of NAs, what are they?
# 
# Illumination - nothing there
# However Illumination Dark is interesting - 0 - NO or 1 - Yes - so I think 
# 
# Time of day and hour of day are not reliable enough. We'll have to drop.
# po-po arrival time perhaps more, but still not enough

# %%

# most do not have weather data. Are we to interpret that as fine conditions.
print(crash_data.describe())
print(crash_data["weather1"].value_counts(dropna=False))
print(crash_data["weather2"].value_counts(dropna=False))

crashes_no_weather = crash_data[["weather1", "weather2"]].notna().any(axis=1).sum()
print(f"crashes without weather1 or weather2 {crashes_no_weather}")

print(crash_data["illumination"].describe())
print(crash_data["illumination"].value_counts(dropna=False))
print(crash_data["illumination_dark"].value_counts(dropna=False))

# neither time_of_day nor hour_of_day are usable - too many NaNs
print(crash_data["hour_of_day"].value_counts(dropna=False))
print(crash_data["time_of_day"].value_counts(dropna=False))
print(crash_data["arrival_tm"].value_counts(dropna=False)) # maybe



# %%
# while we can whittle our data down a bit, and drop what we do not need, we want to be sure ot convert to 2272
print(crash_data.crs)
print(crash_data.centroid)

transformed_crash_path = "transformed-data/PennDOT Crash Data/crash_data_2272.geojson"
crash_data_2272 = to_2272_file(crash_data, transformed_crash_path)

print(crash_data_2272.crs)
print(crash_data_2272.centroid)

crash_data_2272.head()
    



# %% [markdown]
# ### Centerline street data
# 
# Lane count - **we'll have to look elsewhere for lanecount.** 
# Directionality - `oneway` - values are B - both; FT - direction of from->to (direction of digitization); TF - direction of to->from (oppo of digitization)
# Classification - `class` There's some cleaning to do here. Here are the classifications: 
# 
# ```
# 0-Navy Yard
# 1-Expressways
# 2-Major Arterial
# 3-Minor Arterial
# 4-Collector
# 5-Local
# 6-Driveway
# 9-Low Speed Ramps
# 10-High Speed Ramps
# 12-Non Travable
# 14-City Boundary
# 13-???
# 15-Walking Connector
# 18-Traffic Controlled Crosswalks 
# ```
# 
# We might not want to consider street types that aren't driveable or have a near-zero posibility of crashes like `Driveways`, `Non-Travable`, `City Boundary`, `Walking Connectors`, and `Traffic Controlled Crosswalks`. Since I can't find a great source, I'm going to plot and classify the data so I can see for myself, then I'll make a call one way or another. There's a chance that if these aren't actual streets, they could still be independent variables (distance from traffic controlled crosswalk, for instance).
# 
# 12 - Things like forbidden drive - walkways, perhaps maintenance vehicles can access.
# 
# However, I see a 13... and these roads don't seem to haev anything in common. A mixed bag. Legacy? At any rate, if we use this classifcation as a predictor, then we should probably exclude it.
# 
# What else?
# 
# Compare to: https://opendataphilly.org/datasets/street-centerlines-for-vision-zero-high-injury-network-2017/ at the end of your analysis
# 

# %%

# centerline

center_line_data = gpd.read_file("raw-data/Street Centerline Data/Street_Centerline.geojson")

print(center_line_data.crs) # 4326

center_line_data.columns

print("oneway")
print(center_line_data["oneway"].value_counts())

print("pre_dir")
print(center_line_data["pre_dir"].value_counts())

print("seg_id")
print(center_line_data["seg_id"])

print("st_type")
print(center_line_data["st_type"])

print("class")

print(center_line_data.columns)

center_line_data["class"].value_counts()

## What's up with thesse classes


# %%

thirteens = center_line_data[center_line_data["class"] == 13]
thirteens.explore()

# %% [markdown]
# Hi i am markdoinw

# %%
# these are all sorts of driveways, shopping centers, parks, universities. Again, I'm split on whether or not to include them.
driveways = center_line_data[center_line_data["class"] == 6]
driveways.explore()

## before we manipulate, let's transform so we don't have to do it multiple times
cl_2272_filepath = "transformed-data/Street Centerline Data/2272_centerlines.geojson"
center_line_2272 = to_2272_file(center_line_data, cl_2272_filepath)

exclude_classes = [6, 12, 13, 14, 15, 18]
# could show maps of others
center_line_subset = center_line_2272[~center_line_2272["class"].isin(exclude_classes)]
center_line_excluded = center_line_2272[center_line_2272["class"].isin(exclude_classes)]


center_line_master_2722 = center_line_subset.copy()
print(center_line_master_2722)
#center_line_excluded.explore(column="class", categorical=True, legend=True, cmap="tab10")
center_line_subset.explore(column="class", categorical=True, legend=True, cmap="tab10")

# %% [markdown]
# Indeed - we understand the centerline data better, but at the risk of not having speed limit or num of lanes. We'll definitely want speed limits.
# 

# %%
center_line_data.head()
# center_line_subset["length_ft"] = center_line_subset.geometry.length actually not necessary "legnth" is already in feet


# %% [markdown]
# ### Curbs with Cartways
# Curbs with cartways can tell us how wide streets are. metadata guidance
# 
# > Classification of a curb polygon and whether it consists of parcels, islands, medians etc; and also its visibility. Hidden FCODE = 1001
# 
# > Travelways Concrete Island: On State Route=1010; On Fam Route=1011; On City Street=1012
# > Shoulder: On State Route = 1020; On Fam Route = 1021; On City Street = 1022
# > Grass Island: On State Route = 1030; On Fam Route = 1031; On City Street = 1032 

# %%


# curbs with cartways - 

curbs_with_cartways = gpd.read_file("raw-data/Curbs and Cartways/Curbs.geojson")
curbs_with_cartways_2272 = to_2272_file(curbs_with_cartways, "transformed-data/Curbs and Cartways/Curbs.geojson")

print(curbs_with_cartways_2272.head(10))
print(curbs_with_cartways_2272.crs) # 4326

print(curbs_with_cartways_2272.columns.tolist())
print(curbs_with_cartways_2272.head())
print(curbs_with_cartways_2272['fcode'].value_counts())
# curbs_with_cartways_2272.explore(column="fcode", categorical=True, legend=True)

roadway_ids = [1000, 1001]
island_ids = [1010,1011,1012,1030,1031,1032]
    
roadways = curbs_with_cartways_2272[curbs_with_cartways_2272["fcode"].isin(roadway_ids)]
islands = curbs_with_cartways_2272[curbs_with_cartways_2272["fcode"].isin(island_ids)]

islands.plot(column="fcode", categorical=True, legend=True, figsize=(10,10))
plt.show() # this looks correct - rooselvelt expressway; 76 + 95; airport + cargo city area.


# %% [markdown]
# 

# %%

# so two spatial ops here.. one is to associate islands with roads
# and then the other is to associate the roads with our centerline data so we can get the width of the roads
# the first:
# any of the roads which intersect the islands, we'll associate - so it'll be a self join kinda thing. this is not the way. the better way is to use authoratative sources

rmsseg = gpd.read_file("raw-data/PennDOT State Roads/RMSSEG_(State_Roads).geojson")


# %%

rmsseg = rmsseg[rmsseg["CTY_CODE"].astype(str) == "67"].to_crs(2272)  # Philly county code
rmsseg.columns.to_list()
rmsseg["is_divided"] = (
    rmsseg["DIVSR_TYPE"].notna()
    & ~rmsseg["DIVSR_TYPE"].astype(str).str.strip().isin(["", "0", "00"])
) | (rmsseg["DIVSR_WIDTH"].fillna(0) > 0)

# bonus: keep the type for downstream modeling
rmsseg["median_type"] = rmsseg["DIVSR_TYPE"]
rmsseg.groupby("DIVSR_TYPE").size().plot()
rmsseg.plot(column="DIVSR_TYPE", categorical=True, legend=True, figsize=(25,25)) # 0 = not divided, this is state roads only of course
plt.show()
rmsseg["DIVSR_TYPE"].value_counts(dropna=False)
# first go is here, but we're seeing some false positives,. so we've gotta distinguish a bit more here
# https://gis.penndot.gov/BPR_PDF_FILES/Documents/Traffic/Highway_Statistics/HPMS/Field_Manual/2016_PA_Field_Manual.pdf has the keys 

rmsseg["is_divided"] =  rmsseg["DIVSR_TYPE"].astype(int) > 1 # still needs refinign I think... need to keep on
plt.show()
rmsseg.plot(column="is_divided", categorical=True, legend=True, cmap="flag", figsize=(25,25)) # 0 = not divided, this is state roads only of course



# %% [markdown]
# The above map looks better than our first attempts by joining... but market east and west arent really divided..
# Lots good, but some clean up to do.
# 
# Now part 2 to assocoaite back to cetnerlines.. 
# 

# %%
# hit = gpd.sjoin(center_line_subset, roadways, predicate="intersects") 


# %%

# FYI THIS WAS FIRST APPROACH TO JOIN BACK TO CENTERLINES - DIDNT GO WITH
# def mrr_width(poly):
#     mrr = poly.minimum_rotated_rectangle
#     xs, ys = mrr.exterior.coords.xy
#     edges = [((xs[i+1]-xs[i])**2 + (ys[i+1]-ys[i])**2)**0.5 for i in range(4)]
#     return min(edges[0], edges[1])
# roadways["width_ft"] = roadways.geometry.apply(mrr_width)
# print(roadways["width_ft"].describe())

# print(roadways.geometry.type.value_counts())
# print(roadways[roadways.geometry.type == "MultiPolygon"].shape)

# top = roadways.sort_values("width_ft", ascending=False).head(10)
# print(top[["fcode", "width_ft"]])
# top.plot(figsize=(10,10), color="red")
# plt.show()

# roadways["width_ft"] = 2 * roadways.geometry.area / roadways.geometry.length
# print(roadways["width_ft"].describe())

# the below map actually makes some sense relatively - blvd is the darkest road, makes sense... We can see henry a bit
# What I think is probably important rather than just isDivided is number of lanes per divider.
# 74 feet max - that's blvd - 12 lanes 12x6
# also need to be specific about the lanes are we including the divider or no.
# the min, however, makes no sense, unless we have some weird roads. 0.5 feet... nah
# mean of 14... one road two ways... that makes sense to me.

## %%
# roadways["width_ft"].describe()

# # or
# import geopandas as gpd
# import pandas as pd
# import numpy as np

# # 1) force clean projected CRS
# centerlines = center_line_subset.to_crs(2272).copy()
# roadways = roadways.to_crs(2272).copy()

# # give ids if needed
# centerlines = centerlines.reset_index(drop=True)
# centerlines["cl_id"] = centerlines.index
# centerlines.columns

# roadways = roadways.reset_index(drop=True)
# roadways["rw_id"] = roadways.index

# # 2) small buffer so boundary-touch cases still count
# roadways["geom_buf"] = roadways.geometry.buffer(5)   # 5 ft; tune as needed

# # 3) get candidate centerlines near each roadway polygon
# candidates = gpd.sjoin(
#     centerlines[["cl_id", "seg_id", "st_name", "geometry"]],
#     roadways[["rw_id", "geom_buf"]].set_geometry("geom_buf"),
#     predicate="intersects",
#     how="inner"
# ).rename(columns={"index_right": "rw_idx"})

# # 4) bring original geometries back
# candidates = candidates.merge(
#     roadways[["rw_id", "geometry"]].rename(columns={"geometry": "rw_geom"}),
#     on="rw_id",
#     how="left"
# )

# candidates = candidates.rename(columns={"geometry": "cl_geom"})
# candidates = gpd.GeoDataFrame(candidates, geometry="cl_geom", crs=2272)

# # 5) score each candidate
# candidates["dist_ft"] = candidates.apply(
#     lambda r: r.cl_geom.distance(r.rw_geom), axis=1
# )

# # line length inside roadway polygon
# candidates["inside_len"] = candidates.apply(
#     lambda r: r.cl_geom.intersection(r.rw_geom).length, axis=1
# )

# candidates["cl_len"] = candidates.cl_geom.length
# candidates["inside_ratio"] = candidates["inside_len"] / candidates["cl_len"].replace(0, np.nan)

# # 6) choose best centerline per roadway polygon
# # prefer high inside_ratio, then low distance
# best = (
#     candidates.sort_values(["rw_id", "inside_ratio", "dist_ft"], ascending=[True, False, True])
#     .groupby("rw_id")
#     .head(1)
#     .copy()
# )

# roadways_matched = roadways.merge(
#     best[["rw_id", "cl_id", "seg_id", "dist_ft", "inside_ratio"]],
#     on="rw_id",
#     how="left"
# )

# %%
# roadways_matched["dist_ft"].describe() # worse than the width feet.
# I'll come back to this, but when we do, we should be able to try to match the state roads with our calculations.
# and this is clearly wrong, the above is better.
## - try again -> THIS WORKS!

from shapely.ops import unary_union
from shapely import make_valid
import shapely


def _prep_gdf(gdf, epsg=2272):
    out = gdf.copy()

    if out.crs is None:
        raise ValueError("Input GeoDataFrame has no CRS. Set CRS before measuring widths.")

    out = out.to_crs(epsg)
    out = out[out.geometry.notna() & ~out.geometry.is_empty].copy()
    out["geometry"] = out.geometry.map(lambda g: make_valid(g) if not g.is_valid else g)
    out = out[out.geometry.notna() & ~out.geometry.is_empty].copy()

    return out


def _line_parts(g):
    """
    Extract line components from a Shapely intersection result.
    Ignores points because points have no cross-section width.
    """
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


def make_perpendicular_transects(
    centerlines,
    id_col="cl_id",
    spacing_ft=25,
    trim_ft=25,
    half_len_ft=175,
    tangent_delta_ft=5,
):
    """
    Build repeated perpendicular transects along each centerline.

    spacing_ft: distance between transects along centerline.
    trim_ft: avoids intersection flares near segment ends.
    half_len_ft: transect extends this far left and right from centerline.
    tangent_delta_ft: small distance used to estimate local tangent.
    """
    rows = []

    for _, row in centerlines.iterrows():
        line = row.geometry

        if line is None or line.is_empty or line.length <= 0:
            continue

        L = float(line.length)

        # Avoid over-trimming short segments.
        trim = min(float(trim_ft), max(0.0, (L - 1.0) / 2.0))

        if L - 2 * trim < max(1.0, spacing_ft):
            stations = np.array([L / 2.0]) 
        else:
            stations = np.arange(trim, L - trim + 1e-9, float(spacing_ft)) # a nudge to include stations at endpoints
            if len(stations) == 0:
                stations = np.array([L / 2.0]) # fallback to one station at the midpoint

        # loop through stations and make transects for each, j, s are index and value
        for j, s in enumerate(stations):
            p = line.interpolate(float(s)) # get the station point on the line

            # we need to determine the direction the centerline is going
            # at this particular station. We can't do that from one point
            # so we sample a couple on either end of the station
            s0 = max(0.0, float(s) - float(tangent_delta_ft))
            s1 = min(L, float(s) + float(tangent_delta_ft))

            # edge cases where our +delta is the same or less than -delta
            if s1 <= s0:
                continue
            
            # get each of the "sub-station" points on the centerline    
            a = line.interpolate(s0)
            b = line.interpolate(s1)

            # calcluate the change in x and the change in y
            # to get the cartesian distance between the two points
            dx, dy = b.x - a.x, b.y - a.y
            d = np.hypot(dx, dy)

            if d == 0:
                continue

            # Calculate the unit normal to the tangent. Normals are perpendicular to a line,
            # exactly what we want.
            # this works by:
            # rotating 90 deg (-dy)
            # and then normalizing to the unit vector (divide by the distance)
            nx, ny = -dy / d, dx / d
            
            # now build the transect by:
            # starting at the station point
            # and adding or subtracting our (estimated) half_len_ft offset
            # along the vector direction
            transect = LineString([
                (p.x - half_len_ft * nx, p.y - half_len_ft * ny),
                (p.x + half_len_ft * nx, p.y + half_len_ft * ny),
            ])
            
            # and let's just append the rows
            rows.append({
                id_col: row[id_col],
                "transect_no": j,
                "station_ft": float(s),
                "geometry": transect,
            })

    return gpd.GeoDataFrame(rows, geometry="geometry", crs=centerlines.crs)


def measure_transect_widths(
    transects,
    surfaces,
    id_col="cl_id",
    grid_size_ft=None,
):
    """
    Intersect transects with cartway/curb polygons.

    paved_width_ft = sum of all line pieces inside polygon.
    span_width_ft = outermost-to-outermost cross-section span.
    """
    if transects.empty:
        return gpd.GeoDataFrame(
            columns=[
                id_col,
                "transect_no",
                "station_ft",
                "paved_width_ft",
                "span_width_ft",
                "n_parts",
                "center_covered",
                "geometry",
            ],
            geometry="geometry",
            crs=transects.crs,
        )

    surfaces = surfaces.to_crs(transects.crs)

    # Bulk spatial-index query. pairs[0] = transect positions; pairs[1] = surface positions.
    pairs = surfaces.sindex.query(transects.geometry, predicate="intersects")

    groups = {}
    if pairs.size:
        pair_df = pd.DataFrame({
            "tx_pos": pairs[0],
            "surf_pos": pairs[1],
        })

        for tx_pos, g in pair_df.groupby("tx_pos", sort=False):
            tx_i = int(np.asarray(tx_pos).item())
            groups[tx_i] = g["surf_pos"].to_numpy(dtype=np.int64)
            
    records = []

    tx_geoms = transects.geometry.to_numpy()
    surface_geoms = surfaces.geometry.reset_index(drop=True)
    from time import perf_counter
    t0 = perf_counter()
    for tx_pos, t in enumerate(tx_geoms):
        # profiling
        if tx_pos % 5000 == 0 and tx_pos > 0:
            elapsed = perf_counter() - t0
            rate = tx_pos / elapsed
            remaining = (len(tx_geoms) - tx_pos) / rate

            print(
                f"{tx_pos:,}/{len(tx_geoms):,} transects | "
                f"{rate:,.1f}/sec | "
                f"{remaining/60:,.1f} min left"
            )
        surf_pos = groups.get(tx_pos)

        if surf_pos is None or len(surf_pos) == 0:
            paved_width = np.nan
            span_width = np.nan
            n_parts = 0
            center_covered = False

        else:
            # Union only nearby candidate polygons, not the whole city.
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
    raw,
    id_col="cl_id",
    prefix="cartway",
    min_width_ft=4,
    max_width_ft=250,
):
    """
    Summarize transect widths back to centerline segments.
    Median is preferred over mean because intersections/flares create outliers.
    """
    x = raw.copy()

    x["valid_width"] = (
        x["span_width_ft"].notna()
        & x["span_width_ft"].between(min_width_ft, max_width_ft)
    )

    good = x[x["valid_width"]].copy()

    all_counts = x.groupby(id_col).size().rename(f"{prefix}_n_transects")
    valid_counts = good.groupby(id_col).size().rename(f"{prefix}_n_valid")

    stats = good.groupby(id_col).agg(
        span_median_ft=("span_width_ft", "median"),
        span_p25_ft=("span_width_ft", lambda s: s.quantile(0.25)),
        span_p75_ft=("span_width_ft", lambda s: s.quantile(0.75)),
        paved_median_ft=("paved_width_ft", "median"),
        paved_p25_ft=("paved_width_ft", lambda s: s.quantile(0.25)),
        paved_p75_ft=("paved_width_ft", lambda s: s.quantile(0.75)),
        parts_median=("n_parts", "median"),
        center_covered_share=("center_covered", "mean"),
    ).add_prefix(prefix + "_")

    summary = all_counts.to_frame().join(valid_counts).join(stats)
    summary[f"{prefix}_valid_share"] = (
        summary[f"{prefix}_n_valid"] / summary[f"{prefix}_n_transects"]
    )

    return summary.reset_index()


def widths_by_centerline(
    centerlines,
    surfaces,
    prefix="cartway",
    id_col="cl_id",
    epsg=2272,
    spacing_ft=25,
    trim_ft=25,
    half_len_ft=175,
    tangent_delta_ft=5,
    min_width_ft=4,
    max_width_ft=250,
    grid_size_ft=None,
):
    """
    Main wrapper.

    centerlines: LineString centerline GeoDataFrame.
    surfaces: Polygon cartway/curb/roadway GeoDataFrame.
    """
    cl = centerlines.copy()

    if id_col not in cl.columns:
        cl = cl.reset_index(drop=True)
        cl[id_col] = cl.index

    cl = _prep_gdf(cl, epsg=epsg)
    surfaces = _prep_gdf(surfaces, epsg=epsg)

    # Explode multipart centerlines, but keep original cl_id for summarizing.
    cl_parts = cl.explode(index_parts=False).reset_index(drop=True)
    cl_parts = cl_parts[
        cl_parts.geometry.geom_type.isin(["LineString", "MultiLineString"])
    ].copy()

    transects = make_perpendicular_transects(
        cl_parts,
        id_col=id_col,
        spacing_ft=spacing_ft,
        trim_ft=trim_ft,
        half_len_ft=half_len_ft,
        tangent_delta_ft=tangent_delta_ft,
    )

    raw = measure_transect_widths(
        transects,
        surfaces,
        id_col=id_col,
        grid_size_ft=grid_size_ft,
    )

    summary = summarize_widths(
        raw,
        id_col=id_col,
        prefix=prefix,
        min_width_ft=min_width_ft,
        max_width_ft=max_width_ft,
    )

    out = cl.merge(summary, on=id_col, how="left")

    return out, raw, transects

#%%
# 
## NOTE _ KEEP THESE, JUST COMMENTED OUT FOR SPACE SAVE - THIS IS TESTING AND VALIDATION
### - RUNNING
centerlines = center_line_subset.copy()
roadway_polys = roadways.copy()

# this is taking FOREVER :) 
# MUCH MUCH Quicker with 2k and spacing ft at 75.
# test_centerlines = centerlines.sample(2000, random_state=1)
# test_out, test_raw, test_transects = widths_by_centerline(
#     centerlines=test_centerlines,
#     surfaces=roadway_polys,
#     prefix="cartway",
#     id_col="cl_id",
#     spacing_ft=75,
#     trim_ft=25,
#     half_len_ft=175,
# )

# centerlines_w_cartway, cartway_raw, cartway_transects = widths_by_centerline(
#     centerlines=centerlines,
#     surfaces=roadway_polys,
#     prefix="cartway",
#     id_col="cl_id",
#     epsg=2272,
#     spacing_ft=25,
#     trim_ft=25,
#     half_len_ft=175,
#     min_width_ft=4,
#     max_width_ft=250,
# )

#%%
# we'll need to QA the results before we move on and run the entire shit.
# test_raw[["paved_width_ft", "span_width_ft", "n_parts", "center_covered"]].describe()

# test_out[
#     ["cartway_span_median_ft", "cartway_paved_median_ft", "cartway_valid_share"]
# ].describe()

# test_out.sort_values("cartway_span_median_ft", ascending=False)[
#     ["cl_id", "cartway_span_median_ft", "cartway_paved_median_ft", "cartway_valid_share"]
# ].head(20)

# test_out.sort_values("cartway_span_median_ft", ascending=True)[
#     ["cl_id", "cartway_span_median_ft", "cartway_paved_median_ft", "cartway_valid_share"]
# ].head(20)


# ax = roadway_polys.to_crs(2272).plot(figsize=(12, 12), alpha=0.25)
# test_out.plot(
#     ax=ax,
#     column="cartway_span_median_ft",
#     legend=True,
#     linewidth=1,
# ) # looks pretty sane to me at first glance?

# wide_raw = test_raw[test_raw["span_width_ft"] > 120]

# ax = roadway_polys.to_crs(2272).plot(figsize=(10, 10), alpha=0.25)
# wide_raw.plot(ax=ax, color="red", linewidth=1) # hmmmm less enthusiasm.. lots of 120 wide streets.
# test_centerlines.to_crs(2272).plot(ax=ax, color="black", linewidth=0.5)

# wide_raw = test_raw[test_raw["span_width_ft"] > 120].copy()
# wide_raw[["span_width_ft", "paved_width_ft", "n_parts", "center_covered"]].describe()

# # compare span vs paved
# wide_raw["gap_ft"] = wide_raw["span_width_ft"] - wide_raw["paved_width_ft"]

# wide_raw[["span_width_ft", "paved_width_ft", "gap_ft", "n_parts"]].describe()

# top_wide = test_raw.sort_values("span_width_ft", ascending=False).head(20)

# ax = roadway_polys.to_crs(2272).plot(figsize=(10, 10), alpha=0.25)
# top_wide.plot(ax=ax, color="red", linewidth=2)
# test_centerlines.to_crs(2272).plot(ax=ax, color="black", linewidth=0.5)
# # So this looks a bit more promising... it seems like we're hitting mostly intersections or other weird outliers
# # Let's see if we can do better:
# #%%

# test_out2, test_raw2, test_transects2 = widths_by_centerline(
#     centerlines=test_centerlines,
#     surfaces=roadway_polys,
#     prefix="cartway",
#     id_col="cl_id",
#     spacing_ft=75,
#     trim_ft=50,
#     half_len_ft=125,
# )

#%%
# wide_raw_2 = test_raw2[test_raw2["span_width_ft"] > 120]

# ax = roadway_polys.to_crs(2272).plot(figsize=(10, 10), alpha=0.25)
# wide_raw_2.plot(ax=ax, color="red", linewidth=1) # This is much much better. At this point I need to really dig into what I'm dealing with

# test_raw2_c = test_raw2.copy()
# test_raw2_c["gap_ft"] = test_raw2["span_width_ft"] - test_raw2["paved_width_ft"]

import folium

def map_width_check(centerlines, roadways, transects, width_threshold=120):
    roadways_4326 = roadways.to_crs(4326)
    centerlines_4326 = centerlines.to_crs(4326)

    wide_tx = transects[transects["span_width_ft"] > width_threshold].copy()
    wide_tx_4326 = wide_tx.to_crs(4326)

    # Center map on Philly-ish centroid of your data
    c = roadways_4326.unary_union.centroid
    m = folium.Map(
        location=[c.y, c.x],
        zoom_start=12,
        tiles="CartoDB positron"
    )

    folium.GeoJson(
        roadways_4326[["geometry"]],
        name="Roadway polygons",
        style_function=lambda x: {
            "color": "#8ecae6",
            "weight": 1,
            "fillOpacity": 0.15,
        },
    ).add_to(m)

    folium.GeoJson(
        centerlines_4326[["geometry"]],
        name="Centerlines",
        style_function=lambda x: {
            "color": "black",
            "weight": 1,
            "opacity": 0.5,
        },
    ).add_to(m)

    folium.GeoJson(
        wide_tx_4326[["span_width_ft", "paved_width_ft", "gap_ft", "n_parts", "center_covered", "geometry"]],
        name=f"Transects > {width_threshold} ft",
        tooltip=folium.GeoJsonTooltip(
            fields=["span_width_ft", "paved_width_ft", "gap_ft", "n_parts", "center_covered"],
            aliases=["Span ft", "Paved ft", "Gap ft", "Parts", "Center covered"],
        ),
        style_function=lambda x: {
            "color": "red",
            "weight": 3,
            "opacity": 0.9,
        },
    ).add_to(m)

    folium.LayerControl().add_to(m)
    return m


# m2 = map_width_check(
#     centerlines=test_centerlines,
#     roadways=roadway_polys,
#     transects=test_raw2_c,
#     width_threshold=120,
# )

# m2

# AHAH we can see from the "Bad" examples that we're 
#%%
# wide_paved_2 = test_raw2[test_raw2["paved_width_ft"] > 120]

# ax = roadway_polys.to_crs(2272).plot(figsize=(10, 10), alpha=0.25)
# wide_paved_2.plot(ax=ax, color="red", linewidth=1)
# wide_paved_2["gap_ft"] = test_raw2["span_width_ft"] - test_raw2["paved_width_ft"]

# m3 = map_width_check(
#     centerlines=test_centerlines,
#     roadways=roadway_polys,
#     transects=wide_paved_2,
#     width_threshold=120,
# )

# test_out2.plot(
#     column="cartway_paved_median_ft",
#     legend=True,
#     figsize=(12, 12),
#     vmin=0,
#     vmax=100,
# )

# This distribution looks pretty sane to me.
# The max yeah some cause for concern, btu we're cleaning up well.
# count    1981.000000
# mean       38.478735
# std        23.620443
# min         5.129544
# 25%        25.539738
# 50%        33.405994
# 75%        42.793088
# max       250.000000
# Name: cartway_paved_median_ft, dtype: float64
#%%
# test_out2.sort_values("cartway_paved_median_ft", ascending=False)[
#     [
#         "cl_id",
#         "cartway_paved_median_ft",
#         "cartway_span_median_ft",
#         "cartway_valid_share",
#         "cartway_n_valid",
#         "cartway_parts_median",
#     ]
# ].head(20)

# ## ah we need labels to determine what is what

# top_ids = (
#     test_out2
#     .sort_values("cartway_paved_median_ft", ascending=False)
#     .head(20)["cl_id"]
#     .tolist()
# )

# top_segments = test_out2[test_out2["cl_id"].isin(top_ids)].copy()

# ax = roadway_polys.to_crs(2272).plot(figsize=(12, 12), alpha=0.2)
# test_out2.plot(ax=ax, color="lightgray", linewidth=0.5)
# top_segments.plot(ax=ax, color="red", linewidth=3)

# # label each red segment with cl_id
# for _, r in top_segments.iterrows():
#     p = r.geometry.representative_point()
#     ax.annotate(
#         str(r["cl_id"]),
#         xy=(p.x, p.y),
#         fontsize=9,
#         color="black",
#         bbox=dict(facecolor="white", alpha=0.7, edgecolor="none")
#     )
    
# top_segments_4326 = top_segments.to_crs(4326)

# m3 = folium.Map(
#     location=[
#         top_segments_4326.geometry.unary_union.centroid.y,
#         top_segments_4326.geometry.unary_union.centroid.x
#     ],
#     zoom_start=12,
#     tiles="CartoDB positron"
# )

# folium.GeoJson(
#     top_segments_4326[
#         ["cl_id", "cartway_paved_median_ft", "cartway_span_median_ft", "cartway_n_valid", "cartway_parts_median", "geometry"]
#     ],
#     tooltip=folium.GeoJsonTooltip(
#         fields=["cl_id", "cartway_paved_median_ft", "cartway_span_median_ft", "cartway_n_valid", "cartway_parts_median"],
#         aliases=["CL ID", "Paved median", "Span median", "N valid", "Parts median"],
#     ),
#     style_function=lambda x: {"color": "red", "weight": 5},
# ).add_to(m3)

# m3
# %%
# def add_segments_to_map(m, segments):
#     segments_4326 = segments.to_crs(4326)

#     folium.GeoJson(
#         segments_4326[
#             [
#                 "cl_id",
#                 "cartway_paved_median_ft",
#                 "cartway_span_median_ft",
#                 "cartway_n_valid",
#                 "cartway_parts_median",
#                 "geometry",
#             ]
#         ],
#         name="Highlighted segments",
#         tooltip=folium.GeoJsonTooltip(
#             fields=[
#                 "cl_id",
#                 "cartway_paved_median_ft",
#                 "cartway_span_median_ft",
#                 "cartway_n_valid",
#                 "cartway_parts_median",
#             ],
#             aliases=[
#                 "CL ID",
#                 "Paved median",
#                 "Span median",
#                 "N valid",
#                 "Parts median",
#             ],
#         ),
#         style_function=lambda x: {
#             "color": "purple",
#             "weight": 5,
#             "opacity": 0.9,
#         },
#     ).add_to(m)

#     return m

# top_segments = (
#     test_out2
#     .sort_values("cartway_paved_median_ft", ascending=False)
#     .head(20)
#     .copy()
# )

# m4 = map_width_check(
#     centerlines=test_centerlines,
#     roadways=roadway_polys,
#     transects=test_raw2_c,
#     width_threshold=120,
# )

# m4 = add_segments_to_map(m4, top_segments)

# m4

# %%
# top_segments = (
#     test_out2
#     .sort_values("cartway_paved_median_ft", ascending=False)
#     .head(20)
#     .copy()
# )

# roadways_4326 = roadway_polys.to_crs(4326)
# top_segments_4326 = top_segments.to_crs(4326)

# m_top = folium.Map(
#     location=[
#         top_segments_4326.geometry.unary_union.centroid.y,
#         top_segments_4326.geometry.unary_union.centroid.x,
#     ],
#     zoom_start=12,
#     tiles="CartoDB positron",
# )

# folium.GeoJson(
#     roadways_4326[["geometry"]],
#     name="Roadway polygons",
#     style_function=lambda x: {
#         "color": "#8ecae6",
#         "weight": 1,
#         "fillOpacity": 0.10,
#     },
# ).add_to(m_top)

# folium.GeoJson(
#     top_segments_4326[
#         [
#             "cl_id",
#             "cartway_paved_median_ft",
#             "cartway_span_median_ft",
#             "cartway_n_valid",
#             "cartway_parts_median",
#             "geometry",
#         ]
#     ],
#     name="Top 20 paved median segments",
#     tooltip=folium.GeoJsonTooltip(
#         fields=[
#             "cl_id",
#             "cartway_paved_median_ft",
#             "cartway_span_median_ft",
#             "cartway_n_valid",
#             "cartway_parts_median",
#         ],
#         aliases=[
#             "CL ID",
#             "Paved median",
#             "Span median",
#             "N valid",
#             "Parts median",
#         ],
#     ),
#     style_function=lambda x: {
#         "color": "red",
#         "weight": 6,
#         "opacity": 1,
#     },
# ).add_to(m_top)

# m_top.fit_bounds(m_top.get_bounds()) # type: ignore
# folium.LayerControl().add_to(m_top)

# m_top

## ALRIGHT! I think we have this cleaned enough - TODO: Get a summary of what you've done, lots of things here
#%%
%%time

# load from below before so we dont have to do this again
# full_out, full_raw, full_transects = widths_by_centerline(
#     centerlines=centerlines,
#     surfaces=roadway_polys,
#     prefix="cartway",
#     id_col="cl_id",
#     spacing_ft=75,
#     trim_ft=50,
#     half_len_ft=125,
# )

full_out = gpd.read_file("transformed-data/Stash or final/philly_centerlines_cartway_widths.gpkg", layer="widths")
full_raw = gpd.read_file("transformed-data/Stash or final/philly_cartway_width_transects_raw.gpkg", layer="raw_transects")
full_transects = gpd.read_file("transformed-data/Stash or final/philly_cartway_width_transects.gpkg", layer="transects")

full_out["cartway_width_ft"] = full_out["cartway_paved_median_ft"]

full_out["width_confidence"] = np.select(
    [
        full_out["cartway_n_valid"].fillna(0) >= 3,
        full_out["cartway_n_valid"].fillna(0) == 2,
        full_out["cartway_n_valid"].fillna(0) == 1,
    ],
    [
        "good",
        "okay",
        "low_one_or_two_transects",
    ],
    default="missing",
)


#%%

# great -let's save the data before we do anyting stupid (processing time is 31 mins)
# full_out["width_method"] = "perpendicular_transect_paved_median"
# full_out["width_spacing_ft"] = 75
# full_out["width_trim_ft"] = 50
# full_out["width_half_len_ft"] = 125
# full_out.to_file("transformed-data/Stash or final/philly_centerlines_cartway_widths.gpkg", layer="widths", driver="GPKG")
# full_raw.to_file("transformed-data/Stash or final/philly_cartway_width_transects_raw.gpkg", layer="raw_transects", driver="GPKG")
# full_transects.to_file("transformed-data/Stash or final/philly_cartway_width_transects.gpkg", layer="transects", driver="GPKG")
full_out["cartway_width_ft"].describe()
qa_confidence = full_out.groupby("width_confidence")["cartway_width_ft"].describe()

problem = full_out[full_out["width_confidence"].isin(["low_one_or_two_transects", "missing"])]

ax = full_out.plot(figsize=(12, 12), color="lightgray", linewidth=0.3)
problem.plot(ax=ax, color="red", linewidth=1)

good_or_okay_widths = full_out[full_out["width_confidence"].isin(["good", "okay"])].copy()
all_widths = all_widths = full_out.copy()
# so we've spent a lot of time on this, and I think we have a pretty good analysis - we've got confidence levels, which is a really big part
# of analysis. It's much better to say, hey we're pretty confident that these streets are very wide.

##KEY
# Widths were calculated from perpendicular transects every 75 ft, trimmed 50 ft from segment ends. 
# Primary width is median paved transect width. Confidence reflects number of valid transects per segment, so short blocks are more likely to be low-confidence.

#%%

# GREAT I Am fucking psyched we have the width data.
# Now to merge back to master
width_cols = [
    "seg_id",
    "cartway_width_ft",
    "cartway_paved_median_ft",
    "cartway_span_median_ft",
    "cartway_valid_share",
    "cartway_n_valid",
    "cartway_parts_median",
    "width_confidence",
    "width_method",
    "width_spacing_ft",
    "width_trim_ft",
    "width_half_len_ft",
]

centerlines_with_width = center_line_master_2722.merge(
    full_out[width_cols],
    on="seg_id",
    how="left",
)

centerlines_with_width.to_file(
    "transformed-data/Stash or final/philly_centerlines_with_cartway_widths.gpkg",
    layer="centerlines_widths",
    driver="GPKG",
)

### - end transect / centerline

#%%

# now let's compare to state road width
# RESULT -
# PennDOT TOTAL_WIDT comparison was attempted as an external validation check, 
# but matched state-road records showed near-zero correlation with the transect-derived cartway widths. 
# Because of likely definition mismatch and/or route inventory conflation issues, 
# PennDOT widths were not used to calibrate the derived width field.

# This is a good follow up investigation or one to incorporate if we have more timne.
state_roads = gpd.read_file("raw-data/PA State Roads/state_roads_philly.geojson")
print(state_roads.crs) # still good - obsessive checking :)
state_roads_cpy = state_roads.copy()
clw = centerlines_with_width.copy()
# state roads are linestrings so use join nearest
compare = gpd.sjoin_nearest(
    state_roads_cpy,
    clw[
        [
            "seg_id",
            "cartway_width_ft",
            "cartway_span_median_ft",
            "width_confidence",
            "cartway_n_valid",
            "geometry",
        ]
    ],
    how="left",
    max_distance=50,
    distance_col="match_dist_ft",
)

compare["width_diff_ft"] = (
    compare["cartway_width_ft"] - compare["TOTAL_WIDT"]
)

# hmm with all data, including bad, we're not doing great
# count    5302.000000
# mean       27.640088
# std        32.083978
# min         0.000341
# 25%         6.779268
# 50%        16.447861
# 75%        36.396950
# max       216.000000
compare["abs_width_diff_ft"] = compare["width_diff_ft"].abs()


compare_clean = compare[
    (compare["TOTAL_WIDT"].notna())
    & (compare["TOTAL_WIDT"] > 0)
    & (compare["cartway_width_ft"].notna())
    & (compare["width_confidence"].isin(["good", "okay"]))
    & (compare["match_dist_ft"] <= 25)
].copy()

compare_clean["width_diff_ft"] = (
    compare_clean["cartway_width_ft"] - compare_clean["TOTAL_WIDT"]
)

compare_clean["abs_width_diff_ft"] = compare_clean["width_diff_ft"].abs()

compare_clean["abs_width_diff_ft"].describe()




# still a tough go
# count    4485.000000
# mean       24.168872
# std        25.153998
# min         0.000341
# 25%         6.640863
# 50%        15.528496
# 75%        33.476255
# max       150.818152

# signed
# count    4485.000000
# mean       11.273550
# std        33.013134
# min       -71.257175
# 25%        -9.969765
# 50%         1.089338
# 75%        27.829236
# max       150.818152
# Name: width_diff_ft, dtype: float64

compare_clean.plot.scatter(
    x="TOTAL_WIDT",
    y="cartway_width_ft",
    figsize=(7, 7),
    alpha=0.3,
)

cmp2 = compare[
    (compare["width_confidence"].isin(["good", "okay"])) &
    (compare["match_dist_ft"] <= 10) &
    (compare["TOTAL_WIDT"] > 0)
].copy()

cmp2.plot.scatter(
    x="TOTAL_WIDT",
    y="cartway_width_ft",
    figsize=(7, 7),
    alpha=0.3,
)

compare["seg_id"].value_counts().describe()


# %% [markdown]
# ### Traffic Calming Devices
# 
# some words - theres. no need to buffer - it has the seg_id to join on centerlines

# %%

# calming devices

traffic_calming_devices = gpd.read_file("raw-data/Traffic Calming Devices/traffic_calming_devices.geojson")
traffic_calming_2272 = to_2272_file(traffic_calming_devices, "transformed-data/Traffic Calming Devices/traffic_calming_devices_2272.geojson")

print("Calming: \n")
print(traffic_calming_devices.columns)

print(traffic_calming_devices.head(10))

print(traffic_calming_devices.crs) # 4326
# TODO: get unique values and add readable map
print(traffic_calming_devices.id.unique())
print(traffic_calming_devices.seg_id)
print(traffic_calming_devices.install_dt.sort_values()) # we have up to 2026 so need to filter down

traffic_calming_devices_through_2024 = traffic_calming_devices[traffic_calming_devices["install_dt"] < "2025-01-01"]
print(traffic_calming_devices_through_2024.install_dt.sort_values())
# size

print(traffic_calming_devices_through_2024["seg_id"].size)
print(center_line_master_2722["seg_id"].dtype)
print(traffic_calming_devices_through_2024["seg_id"].dtype)

center_line_master_2722["seg_id"] = center_line_master_2722["seg_id"].astype("Int64")
traffic_calming_devices_through_2024["seg_id"] = traffic_calming_devices_through_2024["seg_id"].astype("Int64")

centerline_master_tc_test = center_line_master_2722.merge(
    traffic_calming_devices_through_2024[["seg_id", "id", "install_dt"]],
    on="seg_id",
    how="left",
       indicator=True,
)

# so something is going on here... only 1215 match but above we have 6140 calming devices - i see but 1228 segment ids above... so still to figure out whats going on
# will want to map
centerline_master_tc_test["_merge"].value_counts()
ax = centerline_master_tc_test.plot(column="id", figsize=(12,12))
ax.set_title("road segments with calming devices")


# %% [markdown]
# ### Intersection Controls 
# 
# Intersection controls are divided into three types: "Conventional", "All Way", and "Signalized". The first two are stop signs. All Way means all ways have a stop sign, at least we hope. Conventional means a non-all way stop, and signalized mean there's some sort of traffic signal. Unfortunately, for these last two controls we have no idea _which road_ gets the stop sign or signal, though we can imagine it's the "more main" or heavier trafficked. For this analysis, we'll have to treat each type as a binary indicator - present or not. But present at what? There's no way to tell intersections from our centerline data alone. For this analysis, we'll buffer the intersection controls by 5m, and then see which centerlines intersect.
# stoptype
# Conventional    32637
# All Way         14756
# Signalized      13105
# there is some redundancy with TCD_FUNC_CD + TCD_TYPE in the crash data from penndot
# crash_data["tcd_type"]
# crash_data["tcd_func_cd"]
# I think this is different - one tells us if a crash involved aa traffic signal, the other tells us locations of them.

# %%

intersection_controls = gpd.read_file("raw-data/Intersection Controls/Intersection_Controls.geojson")
intersection_controls_2272 = to_2272_file(intersection_controls, "transformed-data/Intersection Controls/Intersection_Controls_2272.geojson")
print("intersections: \n")
print(intersection_controls_2272.columns)
print(intersection_controls_2272.head(10))
print(intersection_controls_2272.crs)
print(intersection_controls_2272.describe())
print(intersection_controls_2272.stoptype.unique())

# need to join now to... centerlines is the mastre
# i will siphone them off until im sure i can build it all up i guess
ic_buffered = intersection_controls_2272.copy()
ic_buffered.geometry = ic_buffered.geometry.buffer(5) # i guess they're along the center line beause this doesnt seem to matter too much 
ic_buffered.head()

ic_buffered.explore()
# buf.head()

center_line_master_2722_ic_test = center_line_master_2722.sjoin(ic_buffered, "left", "intersects")
center_line_master_2722_ic_test.head(10)
center_line_master_2722_ic_test.stoptype.value_counts(dropna=False) # so we 

# ic_buffered.explore()


# %% [markdown]
### Traffic Counts
# interesting here - coverage is solid across the city, but im not sure exaclty how we shoujld use it. 
# I think we can do some exploratory analysis regarding hwo many crashes are within a certain distance of the survey itself (just for fnu)
# i think otherwise we need to group these into high traffic/med/low traffic and

# %%
# DVRPC Traffic counts

print("traffic counts: \n")

traffic_counts_path = "raw-data/DVRPC Traffic Count/dvrpc_2024_philly_traffic_counts.geojson"

if not os.path.exists("raw-data/DVRPC Traffic Count/dvrpc_2024_philly_traffic_counts.geojson"):
    url = "https://arcgis.dvrpc.org/portal/rest/services/transportation/trafficcounts/FeatureServer/0/query"
    params = {
        "where": "setyear=2024 AND co_name LIKE 'Phil%'",
        "outsr": 4326,
        "outfields": "*",
        "f": "geojson"
    }
    r = requests.get(url, params=params)
    counts = gpd.read_file(r.text)
    counts.to_file("raw-data/DVRPC Traffic Count/dvrpc_2024_philly_traffic_counts.geojson", driver="GeoJSON")
else: 
    counts = gpd.read_file(traffic_counts_path)
    
traffic_counts_2272 = to_2272_file(counts, "transformed-data/DVRPC Traffic Count/dvrpc_2024_philly_traffic_counts_2272.geojson")

print(traffic_counts_2272.head(10))
print(traffic_counts_2272.columns)
print(traffic_counts_2272.crs) 

traffic_counts_2272.explore()

tc_working = traffic_counts_2272.copy()
# Only keep segments within, say, 500 feet of an AADT station
aadt_joined = gpd.sjoin_nearest(
    center_line_master_2722,
    tc_working,
    how='left',
    max_distance=500,  # feet, since EPSG:2272
    distance_col='aadt_distance'
)

# Segments with a match have AADT; others don't
aadt_joined['has_aadt'] = aadt_joined['volume'].notna()
print(aadt_joined['has_aadt'].value_counts())

# %% [markdown]
# # lane counts and speed limits

# %%
# Grab data from osm
g = ox.graph_from_place("Philadelphia, Pennsylvania, USA", network_type="drive")
edges = ox.graph_to_gdfs(g, nodes=False)

# %%
print(edges.head(20))
# %%
# we can fill in na value with some known-defaults, this is quoted in 
# https://gis.penndot.pa.gov/BPR_PDF_FILES/Documents/Traffic/Highway_Statistics/HPMS/Field_Manual/2016_PA_Field_Manual.pdf

# though we're operating at the city level, same principle

speed_by_class = {
    1: 55,   # Expressway
    2: 35,   # Major Arterial
    3: 30,   # Minor Arterial
    4: 30,   # Collector
    5: 25,   # Local
    9: 25,   # Low Speed Ramp
    10: 45,  # High Speed Ramp
}
# %%
# add only if not filled from OSM
# this is unfortuntely not easy... attempt one
# Get midpoints of both line layers
center_line_master_speeds = center_line_master_2722.copy()


center_line_master_speeds['midpoint'] = get_midpoint(center_line_master_speeds)
edges['midpoint'] = get_midpoint(edges)

# Create point GeoDataFrames for the join
centerlines_pts = center_line_master_speeds.set_geometry('midpoint').drop(columns='geometry').rename_geometry('geometry')
edges_pts = edges.set_geometry('midpoint').drop(columns='geometry').rename_geometry('geometry')
edges_pts = edges_pts.to_crs(2272)

# Nearest join with distance threshold
matched = gpd.sjoin_nearest(
    centerlines_pts,
    edges_pts[['lanes', 'maxspeed', 'highway', 'geometry']],
    how='left',
    max_distance=25,  # feet 
    distance_col='osm_distance'
)

print(len(center_line_master_speeds)) # 40490
print(len(matched)) # 57544
# welp, we need to deuplicate
# whats happening is multiple osm edges are matching the same centerline midpoint
matched = matched.sort_values('osm_distance').drop_duplicates(subset='seg_id', keep='first')
print(len(matched)) # 40490
print(matched.lanes.value_counts(dropna=False))
print(matched.maxspeed.value_counts(dropna=False))

# now we need to handle cases where we have multiple values for each 
def parse_lanes(val):
    if isinstance(val, list):
        # Take max - represents the segment's peak capacity. 
        return max(int(x) for x in val)
    if pd.isna(val):
        return np.nan
    return int(val)

matched['lanes_clean'] = matched['lanes'].apply(parse_lanes)


def parse_speed(val):
    if isinstance(val, list):
        # Take max - represents the segment's peak capacity. 
        return max(int(s.split()[0]) for s in val) 
    if pd.isna(val):
        return np.nan
    return int(val.split()[0])

matched['maxspeed_clean'] = matched['maxspeed'].apply(parse_speed)

matched[matched["lanes_clean"].notna()][["lanes", "lanes_clean"]]
matched[matched["maxspeed_clean"].notna()][["maxspeed", "maxspeed_clean"]]


# %% [markdown]
# ### State Roads

# %%
url = "https://mapservices.pasda.psu.edu/server/rest/services/pasda/PennDOT/MapServer/4/query"
params = {
    "where": "CTY_CODE='67'",
    "outsr": 2272,
    "outfields": "*",
    "f": "geojson"
}
# %%

# state_roads = gpd.read_file(f"{url}?" + "&".join(f"{k}={v}" for k,v in params.items()))
# state_roads.to_file("raw-data/PA State Roads/state_roads_philly.geojson", driver="geoJSON")

state_roads = gpd.read_file("raw-data/PA State Roads/state_roads_philly.geojson")
print(state_roads.crs) 
print(state_roads.columns.tolist())
# ['OBJECTID', 'Shape_Length', 'GIS_UPDATE', 'GIS_GEOMET', 'GPID', 'ST_RT_NO', 'CTY_CODE', 
# # 'DISTRICT_N', 'JURIS', 'SEG_NO', 'SEG_LNGTH_', 'SEQ_NO', 'SUB_ROUTE', 'YR_BUILT', 'YR_RESURF', 
# # 'DIR_IND', 'FAC_TYPE', 'TOTAL_WIDT', 'SURF_TYPE', 'LANE_CNT', 'PARK_LANE', 'DIVSR_TYPE', 'DIVSR_WIDT', 
# # 'COND_DATE', 'PVMNT_COND', 'CUR_AADT', 'ACCESS_CTR', 'TOLL_CODE', 'STREET_NAM', 'TRAF_RT_NO', 'TRAF_RT__1', 
# # 'TRAF_RT__2', 'BGN_DESC', 'END_DESC', 'MAINT_RESP', 'URBAN_RURA', 'NHS_IND', 'TANDEM_TRL', 'ACCESS_TAN', 'INTERST_NE', 
# # 'NHPN_IND', 'NORM_ADMIN', 'NORM_TRAFF', 'NORM_SHLD_', 'MAPID', 'NLF_ID', 'SIDE_IND', 'NLF_CNTL_B', 'NLF_CNTL_E', 'CUM_OFFSET', 
# # 'CUM_OFFS_1', 'X_VALUE_BG', 'Y_VALUE_BG', 'X_VALUE_EN', 'Y_VALUE_EN', 'GRAPHIC_LE', 'KEY_UPDATE', 'ATTR_UPDAT', 'OVERALL_PV',
# # 'SEG_STATUS', 'PAVMT_CYCL', 'DRAIN_CYCL', 'GDRAIL_CYC', 'DISTRICT_S', 'TRT_TYPE_N', 'PA_BYWAY_I', 'STREET_N_1', 'TRAF_RT__3', 
# # 'TRAF_RT__4', 'TRAF_RT__5', 'STREET_N_2', 'TRAF_RT__6', 'TRAF_RT__7', 'TRAF_RT__8', 'TRXN_FLAG', 'ROUTE_DIR', 'BUS_PLAN_N', 
# # 'EXP_WAY_NE', 'HPMS_SAMP_', 'MILE_POINT', 'IS_STRUCTU', 'GOVT_LVL_C', 'HOV_TYPE', 'HOV_LANES', 'PAR_SEG_IN', 'HPMS_DIVSR',
# $ 'IRI_CUR_FL', 'DRAIN_SWT', 'GDRAIL_SWT', 'PAVMT_SWT', 'SHLD_COND_', 'FED_AID_PR', 'DRAIN_CNT', 'GDRAIL_CNT', 'PVMNT_TRTM',
# % 'PVMNT_IND', 'IRI_YEAR', 'OPI_YEAR', 'IRI_RATING', 'OPI_RATING', 'SURFACE_YE', 'SEGMENT_MI', 'LANE_MILES', 'CYCLE_MAIN', 'Shape_Leng', 'LEN', 'BIKE_LANE', 'geometry']

state_roads_pts = state_roads.copy()
state_roads_pts.geometry = get_midpoint(state_roads)

matched_state = gpd.sjoin_nearest(
    centerlines_pts,
    state_roads_pts[['LANE_CNT', 'TOTAL_WIDT', 'CUR_AADT', 'DIVSR_TYPE', 'BIKE_LANE', 'geometry']],
    how='left',
    max_distance=100,
    distance_col='state_road_distance'
)

print(len(centerlines_pts))
print(len(matched_state))
matched_state = matched_state.sort_values('state_road_distance').drop_duplicates(subset='seg_id', keep='first')
print(len(matched_state))

print(matched_state["LANE_CNT"].value_counts(dropna=False))
print(matched_state["TOTAL_WIDT"].value_counts(dropna=False))
print(matched_state["CUR_AADT"].value_counts(dropna=False))


# %%
# edges['maxspeed_filled'] = edges['maxspeed'].fillna(edges['highway'].map(speed_defaults))
center_line_master_2722.head()

center_line_master_speeds["maxspeed"] = center_line_master_speeds["class"].map(speed_by_class)
center_line_master_speeds.head()
center_line_master_speeds["maxspeed"].value_counts(dropna=False)

#%%
# %%
print("Census info: ")

block_groups_path = "raw-data/Census/phila_block_groups_2024_4269.geojson"

if not os.path.exists(block_groups_path):
    block_groups = pygris.block_groups(state="PA", county="Philadelphia", year=2024)
    block_groups.to_file(block_groups_path, driver="GeoJSON")
else:
    block_groups = gpd.read_file(block_groups_path)

print(len(block_groups))
block_groups.head(10)
print(block_groups.crs) # 4269

cen = census.Census(os.environ["CENSUS_API_KEY"])

tract_data = cen.acs5.state_county_tract(
    fields=("NAME",
    "B19013_001E",  # median income
    "B17001_002E",  # poverty - hmmm None...
    "B01003_001E",  # population
    "B08301_001E",  # total commuters
    "B08301_003E",  # drove alone
    "B08301_010E",  # transit
    "B08301_019E",  # walked
    "B08301_021E",  # WFH
    "B02001_002E",  # white alone
    "B25002_003E",  # vacant units
    "B25058_001E",  # median rent
    "B01002_001E"),  # median age
    state_fips='42',
    county_fips="101",
    tract="*",
    year=2024
)


tract_data_df = pd.DataFrame(tract_data)
print("Tract: \n")
print(tract_data_df.head(10))

blockgroup_data = cen.acs5.state_county_blockgroup(
    fields=("NAME",
    "B19013_001E",  # median income
    "B01003_001E",  # population
    "B08301_001E",  # total commuters
    "B08301_003E",  # drove alone
    "B08301_010E",  # transit
    "B08301_019E",  # walked
    "B08301_021E",  # WFH
    "B02001_002E",  # white alone
    "B25002_003E",  # vacant units
    "B25058_001E",  # median rent
    "B01002_001E"),  # median age
    state_fips='42',
    county_fips="101",
    blockgroup="*",
    year=2024,
)

blockgroup_data_frame = pd.DataFrame(blockgroup_data)
print("Blockgfroup: \n")

print(blockgroup_data_frame.head(10))

# %%
# now get the geom
bg_geom: gpd.GeoDataFrame = pygris.block_groups(state="PA", county="Philadelphia", year=2024)
bg_geom.plot()

# %%

bg_geom_2272 = to_2272_file(bg_geom, "transformed-data/Census/just-geom.geojson")


# %%
print("Land usage")

land_usage = gpd.read_file("raw-data/Philly Land Use/Land_Use.geojson")
print(land_usage.crs) # 4326



# %% [markdown]
# # Tree Canopy Data

# %%
# Tree canopy data - CRS = 2272
# according to the site - 1 is tree canopy
with rasterio.open("raw-data/Phila Land Cover Raster/PPR_LandCover_2018.gdb") as src:
    print(src.crs) # 2722
    print(src.bounds)
    print(src.res) # 0.5 x 0.5
    print(src.shape)
    print(src.transform)
    print(src.tags())
    print(src.nodata)
     
    # downsample in out_shape
    data = src.read(1, out_shape=(src.height // 25, src.width // 25))

    # mask to canopy only
    canopy = np.where(data == 1, 1, 0) # why no y?

    plt.figure(figsize=(10,10))
    plt.imshow(canopy, cmap="Greens")
    plt.title("2018 TC PH")
    plt.axis("off")
    
    plt.show()
    
#%%

# takes a while! we have stats written below
# tc_center_lines_buf = center_line_master_2722.copy()
# tc_center_lines_buf.geometry = center_line_master_2722.geometry.buffer(5)

# stats = zonal_stats(
#     tc_center_lines_buf.geometry,
#     "raw-data/Phila Land Cover Raster/PPR_LandCover_2018.gdb",
#     categorical=True,
#     stats=["mean", "min", "max", "range", "median", "std", "percentile_10", "percentile_90", "count"], # these stats are actually largely nonsense :) categorical
#     nodata=None,
# )

    


# %%
# print(stats)
# stats_df = pd.DataFrame(stats)
# stats_df.to_parquet("transformed-data/Phila Land Cover Raster/canopy_stats.parquet")
stats_df = pd.read_parquet("transformed-data/Phila Land Cover Raster/canopy_stats.parquet")
print(stats_df.columns.tolist())

#%%
stats_df = stats_df.fillna(0)
# DOUBLE CHECK!!! Some 1.0s
stats_df['total'] = stats_df[['1', '2', '3', '5', '6', '7']].sum(axis=1)
stats_df['canopy_pct'] = stats_df['1'] / stats_df['total']

center_line_master_2722['canopy_pct'] = stats_df['canopy_pct'].values

#%%
center_line_master_2722.plot(column="canopy_pct", legend=True, figsize=(20,20), cmap="Greens")
center_line_master_2722["canopy_pct"].describe()
center_line_master_2722["has_canopy"] = (center_line_master_2722["canopy_pct"] > 0)
# %%
print("Elevation: \n")
elevation_raster_path = "raw-data/Phila Elevation Raster/Philadelphia_dem_3ft_2022.tif"
#%%

boundary_2272 = bg_geom.to_crs("EPSG:2272")
boundary_union = boundary_2272.geometry.union_all()  # single polygon from all block groups


with rasterio.open(elevation_raster_path) as src:
    # Force CRS to just the horizontal 2272 
    # (TODO: Circle back and see if this is necessary, more likely the nodota float32 min is the culprit)
    out_image, out_transform = mask(
        src,
        [boundary_union],
        crop=True,
        nodata=src.nodata
    )
    out_meta = src.meta.copy()
    out_meta.update({
        "height": out_image.shape[1],
        "width": out_image.shape[2],
        "transform": out_transform,
        "crs": rasterio.CRS.from_epsg(2272)  # explicit 2D CRS
    })

# %%

# initially, clipping was returning white...

with rasterio.open(elevation_raster_path) as src:
    print(src.nodata) # -3.4028234663852886e+38

# we need to mask out that nodata value (float32's min value)
    

#%%
data = np.ma.masked_less(out_image[0, ::10, ::10], -1e30) 
print("doen")

plt.figure(figsize=(10, 10))
plt.imshow(data, cmap=cmo.deep) # type: ignore
plt.colorbar(label="Elevation (ft)")
plt.axis("off")
plt.show()

# now the clip looks good 

#%% [markdown]
# ### Time to associate raster elevation change to centerline segments

# a quick and naive first approach:
# get a point at the start end end of each segment and sample the elevation in the raster
#%%
raster_center_line = center_line_master_2722.copy()
raster_center_line.head()

raster_center_line["startpoint"] = raster_center_line.geometry.interpolate(0, normalized=True)
raster_center_line["midpoint"] = get_midpoint(raster_center_line)
raster_center_line["endpoint"] = raster_center_line.geometry.interpolate(1, normalized=True)

raster_center_line.head()


with rasterio.open(elevation_raster_path) as src:
    def sample_elevation(point):
        if point.is_empty:
            return None
        val = next(src.sample([(point.x, point.y)]))[0]
        return val if val > -1e30 else None
    
    raster_center_line['start_elev'] = raster_center_line.geometry.apply(
        lambda g: sample_elevation(Point(g.coords[0]))
    )
    raster_center_line['end_elev'] = raster_center_line.geometry.apply(
        lambda g: sample_elevation(Point(g.coords[-1]))
    )

#%% 

# since we're getting some crazy grade levels (> 59) we're clearly sampling some weird elevation
# we can probably handle with some zonal analysis, but for now, we can get rid of the short segments
# and see if that helps

raster_center_line_above_150 = raster_center_line[raster_center_line["length"] > 150]
   
raster_center_line_above_150["ele_diff"] = abs(raster_center_line_above_150["start_elev"] - raster_center_line_above_150["end_elev"])
raster_center_line_above_150["grade"] = raster_center_line_above_150["ele_diff"] / raster_center_line_above_150["length"]
 #%%

# this is actually not bad as a first attempt
# the data is in the ballpark with port royal and bells mills in the top 5
raster_center_line_above_150.head()
raster_center_line_above_150.sort_values("ele_diff", ascending=False).head()
raster_center_line_above_150.sort_values("grade", ascending=False).head()

#%%
# let's see how it plots
raster_center_line.plot(column="ele_diff",  cmap='viridis', legend=True,
    figsize=(12, 12),
    linewidth=0.5,
    vmin=0,
    vmax=raster_center_line['ele_diff'].quantile(0.95))

# and the grade

raster_center_line.plot(column="grade",  cmap='magma', legend=True,
    figsize=(12, 12),
    linewidth=0.5,
    vmin=0,
    vmax=raster_center_line['grade'].quantile(0.95))



# grades are a bit funky... upwards of 60%
# so onward to zonal

#%%
segments_buffered = center_line_master_2722.copy()
segments_buffered.geometry = center_line_master_2722.geometry.buffer(5)

stats = zonal_stats(
    segments_buffered.geometry,
    elevation_raster_path,
    stats=["mean", "min", "max", "range", "median", "std", "percentile_10", "percentile_90", "count"],
    nodata=-3.4028235e+38
)

#%%
stats_df = pd.DataFrame(stats)

#%%
center_line_master_2722['elev_mean'] = stats_df['mean']
center_line_master_2722['elev_min'] = stats_df['min']
center_line_master_2722['elev_max'] = stats_df['max']
center_line_master_2722['elev_std'] = stats_df['std']
center_line_master_2722['percentile_10'] = stats_df['percentile_10']
center_line_master_2722['percentile_90'] = stats_df['percentile_90']
center_line_master_2722['elev_range'] = center_line_master_2722['elev_max'] - center_line_master_2722['elev_min']
center_line_master_2722['grade_buffered'] = center_line_master_2722['elev_range'] / center_line_master_2722['length']
center_line_master_2722["percentile_90-10"] = center_line_master_2722['percentile_90'] - center_line_master_2722['percentile_10']
center_line_master_2722['grade_buffered_90_10'] = center_line_master_2722['percentile_90-10'] / center_line_master_2722['length']
center_line_master_2722.head(10)
center_line_master_2722["elev_range"].describe()
center_line_master_2722["elev_mean"].describe()
center_line_master_2722["elev_std"].describe() # for the most part this looks good - a std deviation 2.14 at 0.75
center_line_master_2722['grade_buffered'].describe()
center_line_master_2722.sort_values("percentile_90-10", ascending=False)


## we're not having great results this way..... in fact our naive approah was better... 
## funky ranges whether min max or inter-percentile... could tweak percentiles more,  but we also have tons of nans, and i dont htink we had that with the smaple by point.
## so let's try sampling a lot of points on the centerline.
## if that doesnt work.. its back to the drawing board

#%%
## Okay here's where we are picking up with our elevation data.
def sample_along_line(line: LineString, src, n: int = 10) -> list[float]:
    points = [line.interpolate(i / (n - 1), normalized=True) for i in range(n)]
    elevs = []
    for p in points:
        val = next(src.sample([(p.x, p.y)]))[0]
        if val > -1e30:
            elevs.append(float(val))
    return elevs


with rasterio.open(elevation_raster_path) as src:
    def get_grade(line):
        elevs = sample_along_line(line, src, n=10)
        if len(elevs) < 2:
            return np.nan, np.nan
        return max(elevs) - min(elevs), np.std(elevs)
    
    results = center_line_master_2722.geometry.apply(get_grade)

center_line_master_2722['elev_range_sampled'] = results.apply(lambda x: x[0])
center_line_master_2722['elev_std_sampled'] = results.apply(lambda x: x[1])
center_line_master_2722['grade_sampled'] = center_line_master_2722['elev_range_sampled'] / center_line_master_2722['length']

center_line_master_2722['grade_log'] = np.log1p(center_line_master_2722['grade_sampled'])
#%%
center_line_master_2722.plot(
    column='grade_sampled',
    cmap='magma',
    legend=True,
    figsize=(12, 12),
    linewidth=0.8,
    vmax=center_line_master_2722['grade_sampled'].quantile(0.95)
)

#%%

suspicious_ish = center_line_master_2722[center_line_master_2722["grade_sampled"] > 0.1]

fig, ax = plt.subplots(figsize=(12, 12))

# City boundary as background
bg_geom_2272.boundary.plot(ax=ax, color='lightgray', linewidth=1)

suspicious_ish.plot(
    ax=ax,
    column='grade_sampled',
    cmap='magma',
    legend=True,
    figsize=(12, 12),
    linewidth=1.8,
    vmax=suspicious_ish['grade_sampled'].quantile(0.95)
)

plt.show()

suspicious_ish.plot(

    column='grade_sampled',
    cmap='magma',
    legend=True,
    figsize=(12, 12),
    linewidth=0.8,
    vmax=suspicious_ish['grade_sampled'].quantile(0.95)
)
# i see a bunch of suspicious points... I need the city overlay though to tell more
# ahh the dashed line seems like vine st expresssway which makes sense.
# so two things - first ill check this out on the real map,
# and then I'll apply some smoothing to the elevation so hopefully it's not so jumpy
 #%%
import folium

def map_suspicious_grades(
    centerlines,
    grade_gdf,
    grade_col="grade_p90",
    threshold=0.10,
    tiles="CartoDB positron",
):
    cl_4326 = centerlines.to_crs(4326)
    sus = grade_gdf[grade_gdf[grade_col].abs() > threshold].copy().to_crs(4326)

    c = sus.geometry.unary_union.centroid if len(sus) else cl_4326.geometry.unary_union.centroid

    m = folium.Map(
        location=[c.y, c.x],
        zoom_start=12,
        tiles=tiles,
    )

    folium.GeoJson(
        cl_4326[["geometry"]],
        name="All centerlines",
        style_function=lambda x: {
            "color": "#bbbbbb",
            "weight": 1,
            "opacity": 0.5,
        },
    ).add_to(m)

    folium.GeoJson(
        sus[[grade_col, "geometry"]],
        name=f"{grade_col} > {threshold:.0%}",
        tooltip=folium.GeoJsonTooltip(
            fields=[grade_col],
            aliases=[grade_col],
            localize=True,
        ),
        style_function=lambda x: {
            "color": "red",
            "weight": 4,
            "opacity": 0.9,
        },
    ).add_to(m)
    
    folium.TileLayer(
        tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
        attr="Esri World Imagery",
        name="Satellite",
        overlay=False,
        control=True,
    ).add_to(m)

    folium.LayerControl().add_to(m)
    return m

m_grade = map_suspicious_grades(
    centerlines=center_line_master_2722,  # or your master centerlines
    grade_gdf=center_line_master_2722,    # whichever GeoDataFrame has the grade column
    grade_col="grade_sampled",              # replace with your actual grade column
    threshold=0.10,
)

m_grade.save("maps/grades.html")

#%%
# Alright! So, the above isn't the worst. We have clearly identified bridges and overpasses as
# as most of the suspicious areas. Now, we'll attempt to better handle those by smoothing over the
# raster data. At 3ft, it's very detailed and thus one wrong point could mess up our analysis. We don't
# want to eliminate the data, just smooth it over a bit.

# also, our current grade is based on “total elevation variation over segment length.”
# thats okay, but again, we can do better.

def smooth_and_calc_grade(group, elev_col="elev_ft", station_col="length", window=5):
    g = group.sort_values(station_col).copy()

    g["elev_smooth_ft"] = (
        g[elev_col]
        .rolling(window=window, center=True, min_periods=2)
        .median()
    )

    g["elev_smooth_ft"] = g["elev_smooth_ft"].fillna(g[elev_col])

    dx = g[station_col].diff()

    g["grade_raw"] = g[elev_col].diff() / dx
    g["grade_smooth"] = g["elev_smooth_ft"].diff() / dx
    g["abs_grade_smooth"] = g["grade_smooth"].abs()

    return g

def sample_profile_along_line(line: LineString, src, n: int = 10):
    rows = []

    for i in range(n):
        frac = i / (n - 1)
        station_ft = frac * line.length
        p = line.interpolate(frac, normalized=True)

        val = next(src.sample([(p.x, p.y)]))[0]

        if val > -1e30:
            rows.append({
                "station_ft": station_ft,
                "elev_ft": float(val),
            })

    return rows

def get_grade_smoothed(line, src, n=10, window=5):
    prof = sample_profile_along_line(line, src, n=n)

    if len(prof) < 2 or line.length == 0:
        return np.nan, np.nan, np.nan, np.nan

    g = pd.DataFrame(prof).sort_values("station_ft")

    g["elev_smooth_ft"] = (
        g["elev_ft"]
        .rolling(window=window, center=True, min_periods=2)
        .median()
    ).fillna(g["elev_ft"])

    dx = g["station_ft"].diff()
    dz = g["elev_smooth_ft"].diff()

    interval_grades = (dz / dx).abs().replace([np.inf, -np.inf], np.nan).dropna()

    grade_range_smooth = (
        g["elev_smooth_ft"].max() - g["elev_smooth_ft"].min()
    ) / line.length

    if len(interval_grades) == 0:
        return grade_range_smooth, np.nan, np.nan, np.nan

    return (
        grade_range_smooth,
        interval_grades.median(),
        interval_grades.quantile(0.90),
        interval_grades.max(),
    )
    
with rasterio.open(elevation_raster_path) as src:
    results = center_line_master_2722.geometry.apply(
        lambda line: get_grade_smoothed(line, src, n=10, window=5)
    )

center_line_master_2722["grade_range_smooth"] = results.apply(lambda x: x[0])
center_line_master_2722["grade_smooth_median"] = results.apply(lambda x: x[1])
center_line_master_2722["grade_smooth_p90"] = results.apply(lambda x: x[2])
center_line_master_2722["grade_smooth_max"] = results.apply(lambda x: x[3])

#%%
## Get more diverse readings
center_line_master_2722.plot(
    column="grade_range_smooth",
    legend=True,
    figsize=(12, 12),
    vmax=0.17
)


steep_smooth = center_line_master_2722[
    center_line_master_2722["grade_range_smooth"] > 0.10
]

ax = center_line_master_2722.plot(figsize=(12, 12), color="lightgray", linewidth=0.4)
steep_smooth.plot(ax=ax, color="red", linewidth=1.5)

#%%
with rasterio.open(elevation_raster_path) as src:
    print(src.crs)
    print(src.res)
    print(src.bounds)

# %%
print("PPD Street Trees ")
tree_data = gpd.read_file("raw-data/Phila Street Trees/ppr_tree_inventory_2024.geojson")
print(tree_data.crs) # 4326
tree_data.plot(cmap="Greens", ax=None, figsize=(20,20))

tree_data_2272 = to_2272_file(tree_data, "transformed-data/Phila Street Trees/ppr_tree_inventory_2024.geojson")

#%%
tree_data_2272.head(10)

tree_line = center_line_master_2722.copy()

tree_center_joined = tree_line.sjoin_nearest(tree_data_2272)

tree_center_joined.head(10)

print(len(tree_line))
print(len(tree_center_joined))


## again, naive approch... we'd rather have them within a certain range:
# Buffer segments to capture trees along them
segments_buffered = tree_line.copy()
segments_buffered.geometry = tree_line.geometry.buffer(30)  # ~30ft either side, seems to work well - can investigate further.

# Spatial join - each tree gets matched to all segments whose buffer contains it
joined = gpd.sjoin(tree_data_2272, segments_buffered[['seg_id', 'geometry']], how='inner', predicate='intersects')

# Count trees per segment
tree_counts = joined.groupby('seg_id').size().reset_index(name='tree_count')

# Merge back to centerlines
centerlines = tree_line.merge(tree_counts, on='seg_id', how='left')
centerlines['tree_count'] = centerlines['tree_count'].fillna(0).astype(int)

# %%
