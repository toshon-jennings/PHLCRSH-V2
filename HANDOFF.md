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
- [x] Phase 9: AI Assistant Hardening & UX (built on top of the existing streaming pipeline)
  - [x] 9.1 SQL Guard: added `validateReadOnlySQL()` in `executeSQL` — rejects any generated SQL not starting with `SELECT`/`WITH` (after stripping comments/whitespace) and any multi-statement input; throws into the existing attempt/retry loop
  - [x] 9.2 Anthropic Fixes: added `anthropic-dangerous-direct-browser-access: true` header (coexists with `stream: true` on both the streaming and non-streaming paths), removed the "may be blocked by CORS" suffix from the error message, replaced the CORS warning in `updateProviderNote()` with a neutral note, and bumped `DEFAULT_MODELS.anthropic` to `claude-haiku-4-5-20251001`
  - [x] 9.3 Custom Provider: added "Custom (OpenAI-compatible)" to `#ai-provider` for local servers (LM Studio/Ollama); added a Base URL field (`phlcrsh_ai_base_url`) mirroring the provider/model/key load/save/refresh pattern; `callLLM` now takes an optional `baseUrl` param and routes it through the existing OpenAI-compatible branch as `${baseUrl}/chat/completions`; empty API key allowed for this provider
  - [x] 9.4 Results Table: `Message.rows` carries `cleanQueryResults` output through to render time; `renderMessageExtras` adds a collapsible "View Data (N rows)" block (headers from first row, `geometry` skipped, capped at 20 rows, every cell escaped) that composes for free through both `appendMessage` and the streaming `finish()` path
  - [x] 9.5 Starter Chips: 4 clickable example prompts under the welcome bubble in `#ai-chat-messages`; click fills `#ai-chat-input`, calls `form.requestSubmit()`, and removes the chips for the session
  - [x] 9.6 Persisted History: `chatHistory: Message[]` saved to `localStorage` (`phlcrsh_ai_history`, JSON, last 50, try/catch) and replayed through `appendMessage` on init after the welcome bubble — restoring never auto-triggers map zoom since `appendMessage` itself never calls `highlightAndZoomToSegments`; added a "Clear chat" button in `ai-panel-actions` styled like `.ai-panel-action-btn`
  - [x] 9.7 All six sub-tasks verified individually and together with `npm run build` (`tsc && vite build`) — zero TypeScript errors
- [x] Phase 10: Streaming Hardening & Multi-Turn Memory (review of Phase 9 + new capability, `v0.1.4`)
  - [x] 10.1 Review fixes to the streaming pipeline: `consumeSSE` now flushes the final buffered event when a stream ends without a trailing newline; streaming updates only auto-scroll when the reader is already near the bottom (`isNearBottom`); mid-stream errors keep the partially streamed text (finished with the error block attached) instead of discarding it; SQL-toggle listener binds by `[data-sql-id]` instead of the shared `.sql-details-btn` class
  - [x] 10.2 Multi-Turn Memory: `callLLM` now accepts an ordered `ChatTurn[]` conversation (mapped per provider: Gemini `contents`, Anthropic `messages`, OpenAI-compatible `messages`); the submit handler builds capped history from persisted `chatHistory` (last 3 user→assistant pairs from turns that produced real SQL) — the SQL pass sees prior SQL (so follow-ups modify it, per new schema rule 8), the summary pass sees prior prose (truncated)
  - [x] 10.3 End-to-end verification against a local OpenAI-compatible SSE mock (custom provider, port 5199): streamed Markdown rendered incrementally; "View Data (5 rows)" table came from a real DuckDB execution of the generated SQL; follow-up question's requests carried `[system, user, assistant, user]` with the prior SQL in the assistant turn on both passes; history + tables + zoom buttons restored after reload with no auto-zoom; `npm run build` clean
  - [x] 10.4 Incident note: a concurrent Hermes deploy loop (gh-pages stash/reset/clean cycles in this same checkout) twice destroyed uncommitted work during this phase; recovered via `git stash` + scratchpad patch backups. Lesson: don't run deploy agents and coding agents in one working tree — give deploys their own clone/worktree
- [x] Phase 11: AADT Data Quality Guard
  - [x] 11.1 Investigated implausible High-Risk Corridor rows, including Limekiln Pike segments where raw DVRPC values of 6 and 117 were being treated as valid ADT and inflating risk.
  - [x] 11.2 Added a browser-side DuckDB view guard: `adt < 500` falls back to the functional-class estimate, `has_aadt` becomes false, and `risk_index`/`vmt` are recomputed from cleaned exposure.
  - [x] 11.3 Updated `build_final_table.py` so future data rebuilds apply the same 500-vehicle validity floor, support numeric class fallbacks, and keep `length` in feet while deriving VMT from miles.
  - [x] 11.4 Updated AI assistant/data dictionary/About wording to clarify cleaned AADT and feet-based Risk Index; verified `npm run build`, local DuckDB view syntax, and dev server on port 5179.

