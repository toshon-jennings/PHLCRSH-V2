# PHLCRSH

PHLCRSH is an exploratory map of Philadelphia street segments, crash history, tree canopy, street width, grade, and block group context. The project asks where street geometry and environmental context line up with crash risk, and where the public data itself needs skepticism.

The map is not a causal model. It is a browser-based analytical viewer for comparing patterns across street segments. DuckDB-WASM runs locally in the browser, reads GeoParquet outputs, and powers the map layers, peer comparisons, and story examples.

## Links

- [Deployed map](https://benpolinsky.github.io/PHLCRSH/)
- [Notebook source](crash_notebook.ipynb)
- [Notebook PDF](crash_notebook.pdf)
- [Frontend app](app/)

## Data Sources

- Crash records: [OpenDataPhilly Crashes data](https://opendataphilly.org/datasets/crashes/), a Philadelphia subset of PennDOT annual crash data.
- Street geometry: [OpenDataPhilly Street Centerlines](https://opendataphilly.org/datasets/street-centerlines/) and [OpenDataPhilly Curbs](https://opendataphilly.org/datasets/curbs/).
- State-road attributes: [PASDA PennDOT State Roads](https://mapservices.pasda.psu.edu/server/rest/services/pasda/PennDOT/MapServer/4), extracted from PennDOT Roadway Management System data.
- Traffic-count context: [DVRPC Traffic Counts ArcGIS service](https://arcgis.dvrpc.org/portal/rest/services/Transportation/TrafficCounts/FeatureServer).
- Street trees: [OpenDataPhilly Philadelphia Tree Inventory](https://opendataphilly.org/datasets/philadelphia-tree-inventory/).
- Tree canopy and land cover: [OpenDataPhilly Philadelphia Land Cover Raster](https://opendataphilly.org/datasets/philadelphia-land-cover-raster/).
- Elevation and grade inputs: [OpenDataPhilly Digital Elevation Model](https://opendataphilly.org/datasets/digital-elevation-model-dem/).
- Census demographics: [Census 2024 ACS 5-year API](https://api.census.gov/data/2024/acs/acs5.html).
- Census block-group geometry: [Census TIGER/Line shapefiles](https://www.census.gov/geographies/mapping-files/time-series/geo/tiger-line-file.html).
- Basemap: [CARTO basemaps](https://carto.com/basemaps) with [OpenStreetMap](https://www.openstreetmap.org/copyright) data attribution.

## Running the App

```sh
cd app
npm install
npm run dev -- --host localhost --port 5173
```

Open `http://localhost:5173/PHLCRSH/`.

To build:

```sh
cd app
npm run build
```

## Notebook

The notebook expects the local `roads` Python environment and the source data folders used during analysis. Census API access should be provided through `CENSUS_API_KEY`; the notebook does not hardcode an API key.
