# PHLCRSH-V2 Project Summary

PHLCRSH-V2 transforms the original spatial correlation viewer into a comprehensive, client-side **Spatial Safety Diagnostic Engine** and integrates a **Grounded AI Safety Assistant**.

---

## 1. Key Upgrades in V2

### 📊 Safety Exposure & Risk Index (Phase 1)
*   **From Counts to Rates:** Shifted map metrics from absolute crash counts to normalized risk rates. 
*   **Formula:** Mapped local Average Daily Traffic (ADT) and Roadway Management System (RMS) volumes to calculate crashes per million Daily Volume-Feet (VMT/mile equivalent).
*   **KSI Focus:** Added a toggle to isolate high-severity Fatal and Severe Injury (KSI) crashes.

### 🚲 Right-of-Way & Infrastructure Snapping (Phase 2)
*   **Bike Network:** Snapped the City of Philadelphia's bike network to segment midpoints, categorizing streets by Protected, Painted, or Shared lanes.
*   **Intersections:** Mapped intersection control tiers (Signalized, Stop-controlled, Uncontrolled) and added visual icons at intersection vertices.

### ☀️ Temporal & Environmental Slices (Phase 3)
*   **Day/Night & Wet/Dry Slices:** Added active temporal slices to compute risk dynamically based on crash conditions.
*   **Streetlight Illumination Proxy:** Buffers street pole locations (50ft) to compute local streetlight density.
*   **Sun-Glare Predictor:** Calculates road segment bearing azimuths to flag East-West running corridors prone to sun glare ($75^\circ\text{–}105^\circ$ and $255^\circ\text{–}285^\circ$).

### 🌡️ Equity & Climate Overlays (Phase 4)
*   **Urban Heat Index:** Joined CDC-aligned Heat Vulnerability Index (HVI) census tracts to identify high climate risk zones (HVI $\ge 4$).
*   **School Zones:** Generated 500ft buffers around public school facilities to flag adjacent corridors.

### 💬 Grounded AI Safety Assistant (Phase 5)
*   **Text-to-SQL Execution:** Built a client-side AI chat bubble grounded on the database schema. It takes natural language, gets SQL from an LLM, executes it locally on DuckDB-WASM, and presents synthesized insights.
*   **Interactive Map Highlights:** Dynamically updates a custom neon-cyan line layer (`segments-ai-highlight`) and auto-zooms viewport bounds to fit segment coordinates returned by the AI queries.
*   **Settings Panel:** Enables secure storage of local LLM API credentials (Gemini, OpenAI, Anthropic, Groq, Grok, OpenRouter) in `localStorage`.

---

## 2. Interface Reorganization

*   **Header Clean-up:** Simplified left-sidebar header title to "PHLCRSH Engine" and moved sub-items into a spacious grid layout.
*   **Action Toolbar:** Added a dedicated secondary action bar hosting utility links (`Notebook`, `NotebookLM`, `About`).

---

## 3. GitHub Pages Deployment Architecture

To host this serverless dashboard on GitHub Pages, the following network configuration was implemented:
*   **Same-Origin Parquet Caching:** Moved database fetch links from an external Cloudflare R2 bucket to same-origin paths (`/PHLCRSH-V2/data/...`). This completely resolved all cross-origin resource sharing (CORS) blocks.
*   **Relative Service Worker Routing:** Configured the `coi-serviceworker.js` script tag in [index.html](file:///Users/toshonjennings/PHLCRSH/app/index.html) to load relatively. This ensures the service worker starts up correctly inside the subfolder path to inject the necessary COOP/COEP HTTP headers for multithreaded WASM.
