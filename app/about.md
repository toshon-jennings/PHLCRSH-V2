# About PHLCRSH

PHLCRSH is an exploratory map of Philadelphia street segments, crash history, tree canopy, street width, grade, and block group context. The project asks where street geometry and environmental context line up with crash risk, and where the public data itself needs skepticism.

The map is not a causal model. It is a browser-based analytical viewer for comparing patterns: crash counts by street segment, canopy coverage, calculated grade, cartway width, and demographic context. The strongest use case is inspection: turn layers on, compare similar streets, and click examples to see the live DuckDB queries behind the story panels.

## What the App Shows

- Dynamic crash risk index by street segment.
- Tree canopy coverage along street segments.
- Elevation-grade estimates from sampled elevation data.
- Cartway width and speed context.
- Block group population and median household income.
- Bivariate interaction layers for canopy x width and grade x speed.
- Infrastructure layers (Bike Network, Signal Locations).
- Context & Equity overlays (Urban Heat Index, School Zones).

## Diagnostic Engine & Feature Expansion (Phases 1–4)

In July 2026, the application was upgraded from a static count viewer into a dynamic, risk-exposure, and multi-modal safety diagnostic engine:

- **Phase 1: Exposure & Severity Baselining**: Shifted metrics from flat crash counts to true risk rates. The app computes a normalized Risk Index per segment representing crashes per million Daily Volume-Feet (using state or DVRPC AADT with class-based fallbacks, multiplied by segment length in miles). It also exposes binary flags for segments with high-severity outcomes (`has_fatality` and `has_severe_injury`), allowing users to isolate Fatal & Severe Only (KSI) corridors.
- **Phase 2: Micro-Infrastructure & Right-of-Way**: Integrated the City of Philadelphia's Bike Network, snapping bike facilities to centerline midpoints and classifying them into Protected, Painted, or Sharrow tiers. Also categorized intersections into Signalized, Stop-Controlled, or Uncontrolled types.
- **Phase 3: Temporal & Environmental Dynamics**: Implemented dynamic day/night and clear/wet crash slices. Streetlight density (Street Poles counts within a 50ft buffer) is mapped as a proxy for nighttime illumination. Sun-glare prone corridors are flagged automatically using geometric bearing calculations for segments running directly East-West (azimuth $75^\circ\text{–}105^\circ$ or $255^\circ\text{–}285^\circ$).
- **Phase 4: Equity & Climate Vulnerability Overlays**: Joined census block group geometry to School District of Philadelphia facility points and the CDC-aligned Heat Vulnerability Index (HVI) tracts. Segments intersecting school zones (500ft buffer) or high heat vulnerability tracts (HVI $\ge 4$) are flagged for equity overlay analysis.

## Credits & Contributions

- **Original Application**: Created and developed by [Ben Polinsky](https://github.com/ben-polinsky) as an exploratory analysis tool linking spatial geometry and PennDOT crashes. View the original [PHLCRSH GitHub repository](https://github.com/benpolinsky/PHLCRSH).
- **V2 Diagnostic Engine**: Extended collaboratively by [Toshon Jennings](https://github.com/toschon-jennings) and **Antigravity** (Google DeepMind's AI coding assistant). This upgrade built out the multi-dimensional exposure engine, snapped infrastructure indexes, daylight/weather slices, solar-glare vectors, school/heat overlays, and the visible viewport high-risk corridor leaderboard.

## Data Sources

OpenDataPhilly is the main catalog for the Philadelphia-specific public datasets used here.

- Crash records: [OpenDataPhilly Crashes data](https://opendataphilly.org/datasets/crashes/), a Philadelphia subset of PennDOT annual crash data.
- Street geometry: [OpenDataPhilly Street Centerlines](https://opendataphilly.org/datasets/street-centerlines/) and [OpenDataPhilly Curbs](https://opendataphilly.org/datasets/curbs/).
- State-road attributes: [PASDA PennDOT State Roads](https://mapservices.pasda.psu.edu/server/rest/services/pasda/PennDOT/MapServer/4), extracted from PennDOT Roadway Management System data.
- Traffic-count context: [DVRPC Traffic Counts ArcGIS service](https://arcgis.dvrpc.org/portal/rest/services/Transportation/TrafficCounts/FeatureServer).
- Street trees: [OpenDataPhilly Philadelphia Tree Inventory](https://opendataphilly.org/datasets/philadelphia-tree-inventory/).
- Tree canopy and land cover: [OpenDataPhilly Philadelphia Land Cover Raster](https://opendataphilly.org/datasets/philadelphia-land-cover-raster/).
- Elevation and grade inputs: [OpenDataPhilly Digital Elevation Model](https://opendataphilly.org/datasets/digital-elevation-model-dem/).
- Bike network: [OpenDataPhilly Bike Network ArcGIS service](https://services.arcgis.com/fLeGjb7u4uXqeF9q/arcgis/rest/services/Bike_Network/FeatureServer/0).
- Streetlight poles: [OpenDataPhilly Street Poles ArcGIS service](https://services.arcgis.com/fLeGjb7u4uXqeF9q/arcgis/rest/services/Street_Poles/FeatureServer/0).
- Public schools: [School District of Philadelphia Schools ArcGIS service](https://services.arcgis.com/fLeGjb7u4uXqeF9q/arcgis/rest/services/Schools/FeatureServer/0).
- Heat vulnerability: [Philadelphia Department of Public Health HVI ArcGIS service](https://services.arcgis.com/fLeGjb7u4uXqeF9q/arcgis/rest/services/heat_vulnerability_ct/FeatureServer/0).
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

- [NotebookLM Workspace](https://notebooklm.google.com/notebook/d7006b6e-266a-4a95-bce0-c2e9f170e34b)
- [Notebook source](https://github.com/benpolinsky/PHLCRSH/blob/main/crash_notebook.ipynb)
- [Notebook PDF](https://github.com/benpolinsky/PHLCRSH/blob/main/crash_notebook.pdf)
- [GitHub repository](https://github.com/benpolinsky/PHLCRSH)
- [Deployed map](https://benpolinsky.github.io/PHLCRSH/)

## Technical Postscript

DuckDB? OPFS? Why?

Because it was fun and surprisingly easy. Also, it enables powerful data analysis and processing in the browser without a backend. Was that necessary here? No, of course not. The data here is small enough to be processed completely in memory. But we do have some live aggregation that I'd certainly like to benchmark before moving forward beyond a proof of concept.
