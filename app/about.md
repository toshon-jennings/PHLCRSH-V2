# About PHLCRSH

PHLCRSH is an exploratory map of Philadelphia street segments, crash history, tree canopy, street width, grade, and block group context. The project asks where street geometry and environmental context line up with crash risk, and where the public data itself needs skepticism.

The map is not a causal model. It is a browser-based analytical viewer for comparing patterns: crash counts by street segment, canopy coverage, calculated grade, cartway width, and demographic context. The strongest use case is inspection: turn layers on, compare similar streets, and click examples to see the live DuckDB queries behind the story panels.

## What the App Shows

- Crash density by street segment.
- Tree canopy coverage along street segments.
- Elevation-grade estimates from sampled elevation data.
- Cartway width and speed context.
- Block group population and median household income.
- Bivariate interaction layers for canopy x width and grade x speed.

## Data Sources

OpenDataPhilly is the main catalog for the Philadelphia-specific public datasets used here.

- Crash records: [OpenDataPhilly Crashes data](https://opendataphilly.org/datasets/crashes/), a Philadelphia subset of PennDOT annual crash data.
- Street geometry: [OpenDataPhilly Street Centerlines](https://opendataphilly.org/datasets/street-centerlines/) and [OpenDataPhilly Curbs](https://opendataphilly.org/datasets/curbs/).
- State-road attributes: [PASDA PennDOT State Roads](https://mapservices.pasda.psu.edu/server/rest/services/pasda/PennDOT/MapServer/4), extracted from PennDOT Roadway Management System data.
- Traffic-count context: [DVRPC Traffic Counts ArcGIS service](https://arcgis.dvrpc.org/portal/rest/services/Transportation/TrafficCounts/FeatureServer).
- Street trees: [OpenDataPhilly Philadelphia Tree Inventory](https://opendataphilly.org/datasets/philadelphia-tree-inventory/).
- Tree canopy and land cover: [OpenDataPhilly Philadelphia Land Cover Raster](https://opendataphilly.org/datasets/philadelphia-land-cover-raster/).
- Elevation and grade inputs: [OpenDataPhilly Digital Elevation Model](https://opendataphilly.org/datasets/digital-elevation-model-dem/).
- Census demographics: [Census 2024 ACS 5-year API](https://api.census.gov/data/2024/acs/acs5.html), including population and median household income estimates.
- Census block-group geometry: [Census TIGER/Line shapefiles](https://www.census.gov/geographies/mapping-files/time-series/geo/tiger-line-file.html).
- Basemap: [CARTO basemaps](https://carto.com/basemaps) with [OpenStreetMap](https://www.openstreetmap.org/copyright) data attribution.

## Methods Overview

Crash records were joined to street segments so segment-level crash counts could be mapped and compared. The app keeps the segment as the main unit of analysis because that is the level where street width, canopy, grade, and speed context can be inspected together.

Street widths are based on available cartway and roadway geometry, with state-road attributes used where available as a comparison point. These fields are useful for pattern-finding but still reflect public data gaps, joins, and measurement choices.

Tree canopy is summarized at the segment level so the map can compare low-canopy and higher-canopy streets. The story examples query comparable narrow streets directly in the browser rather than relying on fixed screenshots.

Grade is estimated from elevation samples along each segment. This is useful for seeing hilly corridors, but it can produce artifacts on bridges, ramps, overpasses, and very short segments. The grade outlier story is intentionally a data-quality check.

Census block groups provide context layers and peer comparisons. The app keeps all Philadelphia block group geometries in the block-group parquet so the city boundary remains complete even where segment-derived values are missing.

DuckDB-WASM runs in the browser. The app downloads GeoParquet files, registers them with DuckDB, and queries them locally for map features, peer comparisons, story examples, and the Philadelphia boundary.

## Limitations

- The analysis is correlational, not causal proof.
- Crash records, street geometry, canopy data, and Census fields each have timing and join limitations.
- Grade estimates can be wrong on ramps, bridges, overpasses, and short fragments.
- Segment-level aggregation can hide intersection effects and corridor-level behavior.
- Public data gaps can create null values or misleading comparisons.

## Links

- [Notebook source](https://github.com/benpolinsky/PHLCRSH/blob/main/scratchpad.ipynb)
- Notebook PDF: pending export in the notebook cleanup slice
- [GitHub repository](https://github.com/benpolinsky/PHLCRSH)
- [Deployed map](https://benpolinsky.github.io/PHLCRSH/)
