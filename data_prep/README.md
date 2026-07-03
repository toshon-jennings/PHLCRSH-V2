# Data Prep Pipeline

## Structure

```
data_prep/
  common.py                 Shared helpers, paths, CRS constant
  centerlines.py            Master table - Philly street centerlines
  crashes.py                PennDOT crash data + per-segment aggregation
  widths.py                 Cartway width via perpendicular transects
  state_roads.py            PennDOT state roads (lanes, width, AADT, dividers)
  traffic_calming.py        Calming devices per segment
  intersection_controls.py  Stop signs and signals per segment
  traffic_counts.py         DVRPC raw traffic-count context (nearest station within 500ft)
  osm_features.py           OSM speed limits and lane counts
  roadway_defects.py        311 Street Defect / Street Paving requests per segment
  census.py                 Block groups + ACS 5-year variables
  canopy.py                 Tree canopy % from 2018 land cover raster
  elevation.py              Grade per segment from 3ft DEM
  trees.py                  PPR tree inventory count per segment

build_final_table.py        Orchestrator - runs all modules and joins to master
```

## Running

```bash
python build_final_table.py
```

Requires:
- `CENSUS_API_KEY` environment variable for ACS data
- All raw data files in `raw-data/` (see individual module docstrings for paths)
- Several transformed/cached files will be written to `transformed-data/`

First run is slow (~30 min for width transects, ~10 min for canopy raster,
several minutes for elevation profile sampling). Subsequent runs use cached
intermediate results.

## Output

Single GeoPackage at `transformed-data/Stash or final/philly_final_analytical_table.gpkg`,
layer `segments`. One row per driveable centerline segment.

## Key decisions documented in modules

- Excluded centerline classes: 6 (driveway), 12 (non-travelable), 13
  (undocumented), 14 (boundary), 15 (walking connector), 18 (crosswalk)
- Speed limit priority: OSM posted > class-inferred default
- Lane count priority: state road > OSM
- Grade computed via 10-point smoothed sampling along each centerline,
  because full zonal-stats buffers picked up adjacent hillsides and
  endpoint-only sampling was noisy
- PennDOT `TOTAL_WIDT` was NOT used to calibrate transect-derived widths
  because of near-zero correlation (see `widths.py` docstring)
- Crash snap distance to nearest centerline: 75 ft
- DVRPC traffic-count snap distance: 500 ft (raw context only; not treated as AADT)
- 311 Street Defect and Street Paving requests are pulled from the City CARTO
  `public_cases_fc` table and snapped to the nearest centerline within 100 ft
- Canopy class `1` confirmed as tree canopy from PASDA metadata
