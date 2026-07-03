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
