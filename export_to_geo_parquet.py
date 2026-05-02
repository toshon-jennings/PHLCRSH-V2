import geopandas as gpd
import os

# Load the final table
df = gpd.read_file(
    "transformed-data/Stash or final/philly_final_analytical_table.gpkg",
    layer="segments",
)

# --- Block groups parquet ---
bg_geom = gpd.read_file("raw-data/Census/phila_block_groups_2024_4269.geojson")[["GEOID", "geometry"]]
bg_vals = (
    df[["GEOID", "population", "median_income"]]
    .drop_duplicates("GEOID")
    .dropna(subset=["GEOID"])
)
bg_vals["median_income"] = bg_vals["median_income"].where(bg_vals["median_income"] >= 0, other=None)
bg_export = bg_geom.merge(bg_vals, on="GEOID", how="inner")
bg_export.to_parquet("philly_block_groups.parquet", compression="zstd")
print(f"Exported {len(bg_export):,} block groups")
print(f"Block groups file size: {os.path.getsize('philly_block_groups.parquet') / 1e6:.1f} MB")

# Reproject to 4326 for web mapping (MapLibre/Leaflet expect WGS84)
df_4326 = df.to_crs(4326)

keep_cols = [
    "seg_id",
    "st_name",
    "st_type",
    "class",
    "length",
    "crash_count",
    "fatal_count",
    "injury_count",
    "severity_score",
    "cartway_width_ft",
    "width_confidence",
    "lanes_final",
    "maxspeed_final",
    "is_divided",
    "has_signal",
    "calming_device_count",
    "dvrpc_aadt",
    "has_aadt",
    "canopy_pct",
    "tree_count",
    "grade_range_smooth",
    "grade_smooth_p90",
    "median_income",
    "population",
    "geometry",
]

df_export = df_4326[keep_cols].copy()
print(df_export["is_divided"].unique())

# Coerce types so parquet doesn't end up with weird object columns
df_export["is_divided"] = (df_export["is_divided"] == "True").astype(int)

# Write GeoParquet
df_export.to_parquet("philly_segments.parquet", compression="zstd")

print(f"Exported {len(df_export):,} segments")
print(f"File size: {os.path.getsize('philly_segments.parquet') / 1e6:.1f} MB")
