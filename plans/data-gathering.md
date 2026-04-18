# Data Gathering Checklist

## Base Crash Data

- [ ] PennDOT Crash Data (2019–2024) — [OpenDataPhilly Crashes](https://opendataphilly.org/datasets/crashes/) — CSV, SHP, or GeoJSON
  - [x] Obtain
  - [x] Confirm `dec_latitude` / `dec_longitude` fields are populated and geocoding quality is decent
  - [ ] Check `max_severity_level` values and distribution
  - [ ] Verify `weather1`, `weather2`, `illumination`, `hour_of_day` fields are usable
  - [ ] Check if 2025 data drops in time
  - [ ] Pick a year!

## Physical Factor Data

- [ ] Street Centerlines — [OpenDataPhilly](https://opendataphilly.org/datasets/street-centerlines/) — lane count, directionality, classification
  - [x] Obtain
  - [ ] Check what attributes are actually on each segment (speed limit? lane count?)
  - [ ] Compute segment lengths
- [ ] Curbs / Cartway Edges — [OpenDataPhilly](https://opendataphilly.org/datasets/curbs/) — for deriving road width
  - [x] Obtain
  - [ ] Figure out how to pair opposing curb edges to a centerline segment
- [ ] Traffic Calming Devices — [OpenDataPhilly](https://opendataphilly.org/categories/transportation/) — point locations
  - [x] Obtain
  - [ ] Check what types are represented (speed bumps, bump-outs, etc.) - by id get that figured out.,
- [ ] Intersection Controls — OpenDataPhilly — signalized vs stop-controlled
  - [x] Obtain
  - [ ] May overlap with crash data fields — check for redundancy
  - [ ] What is led_status?
- [ ] AADT Traffic Counts — [DVRPC Traffic Count Viewer](https://www.dvrpc.org/traffic/) — traffic volume
  - [x] Obtain
  - [ ] Download station locations and counts
  - [ ] Assess spatial coverage — how many Philly segments have a nearby station?
  - [ ] Decide on join strategy (nearest station? interpolation? cutoff distance?)

## Natural Factor Data

- [ ] Tree Canopy Raster — NLCD 30m or Philly-specific canopy assessment
  - [ ] Obtain
  - [ ] Check [OpenDataPhilly](https://opendataphilly.org) for a local canopy layer
  - [ ] Fallback: [NLCD Tree Canopy](https://www.mrlc.gov/data/nlcd-tree-canopy-cover-conus) 
  - [ ] Confirm CRS and resolution
- [ ] DEM / Elevation — USGS lidar-derived
  - [ ] Check [OpenDataPhilly](https://opendataphilly.org) for city DEM
  - [ ] Fallback: [USGS 3DEP](https://apps.nationalmap.gov/downloader/) — 1m or 3m resolution
  - [ ] Plan slope computation per road segment 
- [ ] Parks Trees Planted.
  - [ ] Obtain

## Control / Confounder Data

- [ ] Census Demographics (ACS) — [Census TIGER/data.census.gov](https://data.census.gov) — tract-level - wait.. not block level?
  - [ ] Income, population density, commute mode — pick a few relevant variables
- [ ] Zoning / Land Use — [OpenDataPhilly](https://opendataphilly.org) — residential vs commercial vs industrial
  - [ ] Join to road segments by spatial overlay

## Processing Prep

- [ ] Confirm common CRS: PA State Plane South (EPSG:2272)
- [ ] Resave
- [ ] Set up project directory structure
- [ ] Initial exploratory notebook — load crash data and centerlines, try the spatial join