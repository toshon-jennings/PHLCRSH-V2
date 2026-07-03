# PHLCRSH Feature Expansion Handoff

## High-Level Objective
Evolve the PHLCRSH dashboard from a static spatial correlation viewer into a dynamic, risk-exposure, and multi-modal traffic safety diagnostic engine.

## Milestones & Task List
- [x] Phase 1: Exposure & Severity Baselining
  - [x] 1.1 Ingest ADT / RMS Data (computed fallbacks based on OSM class for residential roads)
  - [x] 1.2 Pipeline & Schema updates (calculated daily VMT, normalized Risk Index, flagged has_fatality/has_severe_injury)
  - [x] 1.3 UI/UX Adjustments (KSI vs All Crashes filter, shaded map segments by local Risk Index calculation)
- [x] Phase 2: Micro-Infrastructure & Right-of-Way
  - [x] 2.1 Ingest Bike Network (ArcGIS separated/painted/shared) and Intersection Controls (Signalized/Stop-controlled)
  - [x] 2.2 Pipeline & Schema updates (Snapped bike network to segment midpoints, mapped control types)
  - [x] 2.3 UI/UX Adjustments (Bike Lanes and Signal Locations layer accordions, added signal dot symbols at line-centers)
- [x] Phase 3: Temporal & Environmental Dynamics
  - [x] 3.1 Ingest Streetlight Inventory (counted poles within 50ft buffer to produce nighttime_illumination proxy score)
  - [x] 3.2 Pipeline & Schema updates (Hourly day/night blocks, clear/wet blocks, calculated sun-glare prone segments using azimuth/bearings)
  - [x] 3.3 UI/UX Adjustments (Time of Day and Weather condition filters that dynamically compute risk rates in the browser)
- [x] Phase 4: Equity & Climate Vulnerability Overlays
  - [x] 4.1 Ingest UHI Tract Vulnerability Indices, School facilities
  - [x] 4.2 Pipeline & Schema updates (Flagged high_heat_vulnerability and is_school_zone segments using buffer intersection)
  - [x] 4.3 UI/UX Adjustments (Urban Heat Index and School Zones toggle layers in the Context/Equity accordion)
- [x] Verification & Deployment
  - [x] Data Prep Validation (implemented robust self-healing try-except fallbacks for offline downloads)
  - [x] TypeScript & Compilation check (fully resolved and successfully compiled with zero errors)
  - [x] MapLibre Layer Styling (dynamic Risk Index shading via local MapLibre expressions)
- [x] Phase 5: Grounded AI Safety Assistant & Deployments
  - [x] 5.1 Reorganize Left Sidebar (grouped title header, cleaned filters into a grid layout, and added dedicated action toolbar)
  - [x] 5.2 Build Glassmorphic AI Chat Panel (collapsible floating widget with clean styling and smooth transitions)
  - [x] 5.3 Implement Two-Pass Grounded Text-to-SQL Pipeline (fetches query from LLM, runs locally on DuckDB-WASM, synthesizes natural language summary)
  - [x] 5.4 Map Highlight & Zoom Bindings (flashes MapLibre highlight layer in neon cyan and uses `fitBounds` to auto-zoom on returned segments)
  - [x] 5.5 Same-Origin Data CORS Resolution (migrated data paths to `/PHLCRSH-V2/data/...` to load from same origin, resolving CDN CORS blocks)
  - [x] 5.6 Service Worker 404 Resolution (made `coi-serviceworker.js` load relatively to ensure COOP/COEP headers work on GitHub Pages)
- [x] Phase 6: 311 Roadway Defect Overlay
  - [x] 6.1 Added `data_prep/roadway_defects.py` to pull CARTO `public_cases_fc` Street Defect (`SR-ST01`) and Street Paving (`SR-ST23`) requests, cache daily, project to EPSG:2272, and snap to centerline segments
  - [x] 6.2 Added roadway request count columns to `build_final_table.py`, GeoParquet export, data dictionary, docs, and AI assistant schema
  - [x] 6.3 Added Street Defects as a MapLibre infrastructure overlay with legend, popup/sidebar stats, and backward-compatible DuckDB defaults for older parquet files
  - [x] 6.4 Validation: live CARTO aggregate confirmed 93,866 `SR-ST01` and 4,246 `SR-ST23` records since 2020; local geocoded cache loaded 98,043 records with lon/lat; synthetic snap aggregation and `npm run build` passed
- [x] Phase 7: AI Chat Markdown Rendering
  - [x] 7.1 Added `marked` + `dompurify`; assistant messages now render sanitized Markdown (headings, bold, lists, tables, blockquotes, inline code) in `appendMessage`
  - [x] 7.2 Hardened rendering: user messages, generated SQL, and error strings are HTML-escaped before `innerHTML` (previously raw — XSS risk)
  - [x] 7.3 Summary prompt now instructs the LLM to format responses in Markdown; themed CSS for Markdown elements inside `.assistant-message`
  - [x] 7.4 Verified in browser (dev server on port 5179, pinned in `.claude/launch.json`): escaped `<img onerror>` injection inert, table/list/blockquote styling correct; `npm run build` clean
- [x] Phase 8: Notebook UI Design Standardization
  - [x] 8.1 Removed all blue-to-purple decorative gradients from `notebook.html` (progress bar, h1 title, back button, formula block glows)
  - [x] 8.2 Standardized to solid `var(--color-accent)` (#5a9cf5) and `var(--color-text-strong)` (#ffffff)
  - [x] 8.3 Mapped variables (`--color-sidebar-bg: #0f0f1e`, `--color-card-bg: rgba(20, 20, 40, 0.88)`, `--color-text: #e0e0e0`, `--color-muted: #666666`, `--color-secondary: #888888`) and added backdrop glassmorphism to section cards to match the main portal's exact dark mode region style (`v0.1.3`)
  - [x] 8.4 Successfully rebuilt and validated production build


