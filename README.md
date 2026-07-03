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

The notebook expects the source data folders used during analysis. Census API access should be provided through `CENSUS_API_KEY`; the notebook does not hardcode an API key.

To create a local Python environment:

```sh
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m ipykernel install --user --name phlcrsh --display-name "PHLCRSH"
```

---

## Interactive AI Grounded Chat Safety Assistant

PHLCRSH-V2 includes a client-side **Grounded AI Safety Assistant** (accessible via the floating chat bubble in the bottom right corner). It operates as a local Text-to-SQL grounded safety assistant:

1. **Text-to-SQL Translation (Pass 1):** Takes your natural language query (e.g., *"Find the top 5 highest risk streets with no bike lanes in South Philly"*) and performs a client-side fetch to the selected LLM provider. The system prompt is grounded with the database schemas for both `segments` and `block_groups` (from `data_dictionary.md`) to guide the LLM to write a valid DuckDB SQL query.
2. **Local browser-side execution:** The generated SQL query is executed directly in the browser against the local DuckDB-WASM databases.
3. **Interactive Map Highlights:** If the SQL query returns a set of street segment IDs (`seg_id`), the assistant:
    * Updates a dedicated neon cyan MapLibre line highlight layer (`segments-ai-highlight`).
    * Triggers a visual flash animation (opacity pulse) to draw attention to the segments.
    * Dynamically calculates bounds and zooms the map to fit the returned features.
4. **Insight Synthesis (Pass 2):** The query results are converted to a clean JSON array (safely converting any `BigInt` types to prevent serialization errors) and fed back to the LLM in a second-pass call, which summarizes the findings into a human-readable safety insight.

### Supported Providers & Setup

Click the **Gear** icon in the chat header to open the settings pane:
*   **LLM Providers:** Select from Gemini, OpenAI, Anthropic, Groq, Grok, or OpenRouter.
*   **Model Selection:** Model names are auto-populated with sensible defaults (e.g., `gemini-2.5-flash`, `gpt-4o-mini`) but can be customized to use any model supported by your selected provider.
*   **API Key Management:** Input your API key, which is saved securely in the browser's `localStorage` and sent directly to the vendor's API endpoint (no third-party servers).

> [!NOTE]
> For the best client-side experience, **Gemini** or **OpenRouter** are recommended because they natively support browser fetch requests. Direct calls to Anthropic's endpoints from a web browser will result in CORS restrictions.

