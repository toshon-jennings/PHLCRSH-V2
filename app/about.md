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

- Pennsylvania crash data from PennDOT.
- Philadelphia street centerline, cartway, curb, and related street geometry sources from public city data.
- Philadelphia tree and canopy inputs from public city and land-cover sources.
- Elevation inputs derived from public terrain or LiDAR-derived elevation data.
- Census block group geometry and demographic context from public Census/ACS sources.
- OpenStreetMap and CARTO basemap data in the interactive map.

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
