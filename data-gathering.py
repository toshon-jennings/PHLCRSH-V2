# %%
import pandas as pd
import geopandas as gpd
import numpy as np
import rasterio
import osmnx as ox

from rasterio.plot import show
import matplotlib.pyplot as plt
import seaborn as sns

import pygris
import census

import requests

import os



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

def mrr_width(poly):
    mrr = poly.minimum_rotated_rectangle
    xs, ys = mrr.exterior.coords.xy
    edges = [((xs[i+1]-xs[i])**2 + (ys[i+1]-ys[i])**2)**0.5 for i in range(4)]
    return min(edges[0], edges[1])
roadways["width_ft"] = roadways.geometry.apply(mrr_width)
print(roadways["width_ft"].describe())

print(roadways.geometry.type.value_counts())
print(roadways[roadways.geometry.type == "MultiPolygon"].shape)

top = roadways.sort_values("width_ft", ascending=False).head(10)
print(top[["fcode", "width_ft"]])
top.plot(figsize=(10,10), color="red")
plt.show()

roadways["width_ft"] = 2 * roadways.geometry.area / roadways.geometry.length
print(roadways["width_ft"].describe())

# the below map actually makes some sense relatively - blvd is the darkest road, makes sense... We can see henry a bit
# What I think is probably important rather than just isDivided is number of lanes per divider.
# 74 feet max - that's blvd - 12 lanes 12x6
# also need to be specific about the lanes are we including the divider or no.
# the min, however, makes no sense, unless we have some weird roads. 0.5 feet... nah
# mean of 14... one road two ways... that makes sense to me.

# %%
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


center_line_master_speeds['midpoint'] = center_line_master_speeds.geometry.interpolate(0.5, normalized=True)
edges['midpoint'] = edges.geometry.interpolate(0.5, normalized=True)

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


# %%
# TODO: Fill state road data
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
state_roads_pts.geometry = state_roads.geometry.interpolate(0.5, normalized=True)

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
     
    # downsample in out_shape
    data = src.read(1, out_shape=(src.height // 25, src.width // 25))

    # mask to canopy only
    canopy = np.where(data == 1, 1, 0) # why no y?

    plt.figure(figsize=(10,10))
    plt.imshow(canopy, cmap="Greens")
    plt.title("2018 TC PH")
    plt.axis("off")
    
    plt.show()

    


# %%


# %%
print("Elevation: \n")
with rasterio.open("raw-data/Phila Elevation Raster/Philadelphia_dem_3ft_2022.tif") as src:
    data = src.read(1, out_shape=(src.height // 10, src.width // 10))
    nodata = src.nodata

data_masked = np.ma.masked_equal(data, nodata)

plt.figure(figsize=(10,10))
im = plt.imshow(data_masked, cmap="terrain")
plt.colorbar(im, label="Elevation (ft)")
plt.axis("off")
plt.show()
# TODO NEED TO CLIP!
    

# %%


# %%
print("PPD Street Trees ")
tree_data = gpd.read_file("raw-data/Phila Street Trees/ppr_tree_inventory_2024.geojson")
print(tree_data.crs) # 4326
tree_data.plot(cmap="Greens", ax=None, figsize=(20,20))



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

cen = census.Census("854998ba461ae3716c5c85301a31988051bea13e")

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
    year=2024
)

blockgroup_data_frame = pd.DataFrame(blockgroup_data)
print("Blockgfroup: \n")

print(blockgroup_data_frame.head(10))




# %%
print("Land usage")

land_usage = gpd.read_file("raw-data/Philly Land Use/Land_Use.geojson")
print(land_usage.crs) # 4326


