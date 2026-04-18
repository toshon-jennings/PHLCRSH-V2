# Data Gathering Checklist

## Base Crash Data

- [x] PennDOT Crash Data (2019–2024) — [OpenDataPhilly Crashes](https://opendataphilly.org/datasets/crashes/) — CSV, SHP, or GeoJSON
  - [x] Obtain
  - [x] Confirm `dec_latitude` / `dec_longitude` fields are populated and geocoding quality is decent
  - [x] Check `max_severity_level` values and distribution - TBD if usable. Probably as categorical.
  - [x] Verify `weather1`, `weather2`, `illumination`, `hour_of_day` fields are usable
  - [x] 2024

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
  - [x] Obtain (PPR_LandCover_2018 - not sure where i got it check work computer)
  - [x] Confirm CRS and resolution
- [ ] DEM / Elevation — USGS lidar-derived
  - [x] obtain https://noaa-nos-coastal-lidar-pds.s3.amazonaws.com/dem/PA_Phil_DEM_2022_9849/index.html
  - [ ] Plan slope computation per road segment 
- [ ] Parks Trees Planted.
  - [x] Obtain

### BONUS
- [ ] Sunlight? Direction? 
- [ ] Cloud cover - might be too difficutl but weould becrayz
- [ ] Anything else?

## Control / Confounder Data

- [ ] Census Demographics (ACS) — [Census TIGER/data.census.gov](https://data.census.gov) — block-group level
  - [x] - Border/blog groups
  - [x] Income, population density, commute mode — pick a few relevant variables
- [x] Zoning / Land Use — [OpenDataPhilly](https://opendataphilly.org) — residential vs commercial vs industrial
  - [ ] Join to road segments by spatial overlay

## Processing Prep

- [ ] Confirm common CRS: PA State Plane South (EPSG:2272)
  - [ ] Reproject all to 2272
  - [ ] Resave
- [ ] Set up project directory structure
- [ ] Plot everything in a map.
- [ ] Initial exploratory notebook — load crash data and centerlines, try the spatial join

## Next Steps

- [ ] Setup web app. Python -> TS Vite 