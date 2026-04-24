# Data Gathering Checklist

## Base Crash Data

- [x] PennDOT Crash Data (2019–2024) — [OpenDataPhilly Crashes](https://opendataphilly.org/datasets/crashes/) — CSV, SHP, or GeoJSON
  - [x] Obtain
  - [x] Confirm `dec_latitude` / `dec_longitude` fields are populated and geocoding quality is decent
  - [x] Check `max_severity_level` values and distribution - TBD if usable. Probably as categorical.
  - [x] Verify `weather1`, `weather2`, `illumination`, `hour_of_day` fields are usable
  - [x] 2024
  - [x] to 2272

## Physical Factor Data

- [x] Street Centerlines — [OpenDataPhilly](https://opendataphilly.org/datasets/street-centerlines/) — lane count, directionality, classification
  - [x] Obtain
  - [x] Check what attributes are actually on each segment
  - [x] No speed limit, no lane count.
  - [x] to 2272
    - [x] Compute segment lengths (already done)
- [-] Curbs / Cartway Edges — [OpenDataPhilly](https://opendataphilly.org/datasets/curbs/) — for deriving road width
  - [x] Obtain
  - [x] Which fcodes to use? We have the main streets, but we can use islands and such to determine if a roadway is divided. Do we have that? i don't think so.
  - [-] Lanes with separation (some)
  - [-] Figure out how to pair/join opposing curb edges to a centerline segment (some - in progress)
- [x] Traffic Calming Devices — [OpenDataPhilly](https://opendataphilly.org/categories/transportation/) — point locations
  - [x] Obtain
  - [!] Check what types are represented (speed bumps, bump-outs, etc.) - by id get that figured out...
    - We cannot determine. We can gather the types, but not filter by type unfortunately.
  - [x] ensure that the measure is completed as of 2024 Dec 31.
  - [x] join (non spatial have seg_id)
- [x] Intersection Controls — OpenDataPhilly — signalized vs stop-controlled
  - [x] Obtain
  - [x] May overlap with crash data fields — check for redundancy - some but we have em anyway
  - [x] What is led_status? - seemingly it's if there are leds installed.
  - [x] joined 
- [x] AADT Traffic Counts — [DVRPC Traffic Count Viewer](https://www.dvrpc.org/traffic/) — traffic volume
  - [x] Obtain
  - [x] Assess spatial coverage — how many Philly segments have a nearby station?
    - it's sparse, but we'll keep and perhaps we cna use it.
    - can use the type of street from centerline data as a proxy, or do a distance analysis
  - [x] Decide on join strategy (nearest station? interpolation? cutoff distance?)
    - cutoff 500 ft
- [ ] Find lane count and speed limit data
  - [-] lane count
  - [-] speed limit
    - [x] filled in by road class on centerline data
    - [x] can try to link up with state mph data
      - this isn't much, but at least it's some ground truth
  - [ ] bring it all togheter / fill in defaults

## Natural Factor Data

- [ ] Tree Canopy Raster — NLCD 30m or Philly-specific canopy assessment
  - [x] Obtain (PPR_LandCover_2018 - not sure where i got it check work computer)
  - [x] Confirm CRS and resolution
  - [ ] run zonal stats and add to centerline data
- [ ] DEM / Elevation — USGS lidar-derived
  - [x] obtain https://noaa-nos-coastal-lidar-pds.s3.amazonaws.com/dem/PA_Phil_DEM_2022_9849/index.html
  - [ ] Plan slope computation per centerline segment
    - [x] I think that if we take the max-min on the centerline thats a start
    - [x] grade
    - [ ] handle messy results
- [x] Parks Trees Planted.
  - [x] Obtain
  - [x] join to centerline

### BONUS
- [ ] Sunlight? Direction? 
- [ ] Cloud cover - might be too difficutl but weould becrayz
- [ ] add cross_median in crash data to severity?
- [ ] sanity check road width with OSM or other data source

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