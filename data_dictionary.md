# PHLCRSH Data Dictionary

This document defines the schemas, columns, data types, and descriptions for the datasets used in the PHLCRSH Safety Diagnostic Engine. The data is stored in GeoParquet format and queried in-browser via DuckDB-WASM.

---

## 1. Table: `segments`
This table represents individual street centerline segments in Philadelphia, enriched with crash statistics, road design metrics, tree canopy coverage, topographic grade, and equity context.

| Column Name | Data Type | Source / Calculation | Description |
| :--- | :--- | :--- | :--- |
| **`seg_id`** | `INTEGER` | City of Philadelphia | Unique street centerline segment identifier (Primary Key). |
| **`st_name`** | `VARCHAR` | City of Philadelphia | Name of the street (e.g., "Broad", "Market"). |
| **`st_type`** | `VARCHAR` | City of Philadelphia | Street suffix type (e.g., "St", "Ave", "Blvd"). |
| **`class`** | `INTEGER` | City of Philadelphia | Functional classification code (1: Expressway, 2: Major Arterial, 3: Minor Arterial, 4: Collector, 5: Local, 9: Ramp). |
| **`road_class`** | `VARCHAR` | City of Philadelphia | Human-readable functional classification corresponding to `class`. |
| **`length`** | `FLOAT` | Computed | Geometry length of the street segment in feet. |
| **`cartway_width_ft`** | `FLOAT` | Curbs/Centerlines Join | Estimated width of the roadway cartway (curb-to-curb) in feet, computed via perpendicular transects. |
| **`maxspeed_final`** | `FLOAT` | PennDOT / DMV | Final posted speed limit in miles per hour (MPH). |
| **`canopy_pct`** | `FLOAT` | Land Cover Raster | Percentage of tree canopy cover intersecting the segment buffer area (values: `0.0` to `1.0`). |
| **`grade_range_smooth`** | `FLOAT` | DEM Raster | Smoothed segment slope grade (values: `0.0` to `1.0` representing `0%` to `100%` slope). |
| **`state_total_width_ft`** | `FLOAT` | PennDOT RMS | Total roadway width from State Road attributes (where available). |
| **`state_lane_cnt`** | `INTEGER` | PennDOT RMS | Number of traffic lanes from State Road attributes. |
| **`state_divisor_type`** | `VARCHAR` | PennDOT RMS | Median separator category (e.g., "Divided", "Undivided", "Barrier"). |
| **`GEOID`** | `VARCHAR` | Census Bureau | FIPS census block group identifier containing the segment midpoint. |
| **`geometry`** | `GEOMETRY` | City of Philadelphia | LineString geometry of the centerline segment (EPSG:4326). |

### Phase 1: Exposure & Severity Metrics
| Column Name | Data Type | Source / Calculation | Description |
| :--- | :--- | :--- | :--- |
| **`adt`** | `FLOAT` | DVRPC / PennDOT / Fallbacks | Average Daily Traffic volume. Uses DVRPC telemetry if available, PennDOT State counts as secondary, and class-based volume approximations as fallback. |
| **`vmt`** | `FLOAT` | `adt * (length / 5280)` | Daily Vehicle Miles Traveled on this segment. |
| **`risk_index`** | `FLOAT` | `(crashes * 1M) / (adt * length)` | Normalized Risk Index representing crash frequency per million Daily Vehicle-Feet traveled. |
| **`crash_count`** | `INTEGER` | PennDOT Crashes snap | Total historical crash count snapped to this segment. |
| **`fatal_count`** | `INTEGER` | PennDOT Crashes snap | Number of fatalities recorded on this segment. |
| **`injury_count`** | `INTEGER` | PennDOT Crashes snap | Number of general injuries recorded on this segment. |
| **`susp_serious_inj_count`**| `INTEGER` | PennDOT Crashes snap | Number of suspected serious injuries recorded on this segment. |
| **`severity_score`** | `INTEGER` | `10*fatal + 4*serious + 1*injury` | Weighted severity score representing the overall hazard level of crashes on the segment. |
| **`has_fatality`** | `INTEGER` | `fatal_count > 0` | Binary indicator (1: segment has had one or more fatal crashes; 0: otherwise). |
| **`has_severe_injury`** | `INTEGER` | `susp_serious_inj_count > 0` | Binary indicator (1: segment has had one or more serious injuries; 0: otherwise). |
| **`ped_count`** | `INTEGER` | PennDOT Crashes snap | Number of crashes on this segment involving pedestrians. |
| **`bicycle_count`** | `INTEGER` | PennDOT Crashes snap | Number of crashes on this segment involving bicyclists. |

### Phase 2: Micro-Infrastructure
| Column Name | Data Type | Source / Calculation | Description |
| :--- | :--- | :--- | :--- |
| **`bike_infra_type`** | `VARCHAR` | Snapped Bike Network | Snapped bicycle facility category: `Protected` (barrier-separated), `Painted` (striped lanes), `Sharrow` (shared arrows), or `None`. |
| **`intersection_control`** | `VARCHAR` | Street Poles join | Estimated intersection control type at segment boundaries: `Signalized`, `Stop-Controlled` (stop signs), or `Uncontrolled`. |

### Phase 3: Temporal & Environmental Slices
| Column Name | Data Type | Source / Calculation | Description |
| :--- | :--- | :--- | :--- |
| **`nighttime_illumination`** | `FLOAT` | Street Poles buffer | Streetlight pole density proxy (number of streetlight poles counted within a 50ft buffer of the segment centerline). |
| **`is_glare_prone`** | `INTEGER` | Compass Bearing | Binary indicator (1: segment runs directly East-West (bearing azimuth $75^\circ\text{-}105^\circ$ or $255^\circ\text{-}285^\circ$), making drivers prone to sunrise/sunset sun glare; 0: otherwise). |
| **`crash_count_day`** | `INTEGER` | PennDOT (6 AM - 6 PM) | Crashes occurring during daylight hours. |
| **`crash_count_night`** | `INTEGER` | PennDOT (6 PM - 6 AM) | Crashes occurring during nighttime hours. |
| **`crash_count_clear`** | `INTEGER` | PennDOT Weather = 1 | Crashes occurring under clear, dry weather conditions. |
| **`crash_count_wet`** | `INTEGER` | PennDOT Weather &gt; 1 | Crashes occurring under wet, frozen, or adverse weather conditions. |
| **`crash_count_day_clear`** | `INTEGER` | Day & Clear intersection | Crashes occurring during daylight hours under clear weather. |
| **`crash_count_day_wet`** | `INTEGER` | Day & Wet intersection | Crashes occurring during daylight hours under wet/snow weather. |
| **`crash_count_night_clear`** | `INTEGER` | Night & Clear intersection | Crashes occurring during nighttime hours under clear weather. |
| **`crash_count_night_wet`** | `INTEGER` | Night & Wet intersection | Crashes occurring during nighttime hours under wet/snow weather. |

### Phase 4: Equity & Climate Context
| Column Name | Data Type | Source / Calculation | Description |
| :--- | :--- | :--- | :--- |
| **`is_school_zone`** | `INTEGER` | Public Schools buffer | Binary indicator (1: segment falls within a 500ft buffer of a School District of Philadelphia public school; 0: otherwise). |
| **`high_heat_vulnerability`** | `INTEGER` | PDPH HVI Census join | Binary indicator (1: segment intersects a Census Tract with a Heat Vulnerability Index (HVI) score of 4 or 5; 0: otherwise). |

### 311 Roadway Condition Requests
| Column Name | Data Type | Source / Calculation | Description |
| :--- | :--- | :--- | :--- |
| **`roadway_request_count`** | `INTEGER` | Philly311 CARTO snap | Total 311 roadway-condition requests snapped to the segment since 2020. |
| **`roadway_defect_count`** | `INTEGER` | Philly311 `SR-ST01` snap | Street Defect requests snapped to the segment since 2020, used as a pothole/surface-failure proxy. |
| **`roadway_paving_request_count`** | `INTEGER` | Philly311 `SR-ST23` snap | Street Paving requests snapped to the segment since 2020. |
| **`roadway_open_request_count`** | `INTEGER` | Philly311 status | Snapped roadway-condition requests whose status is not closed/canceled. |

---

## 2. Table: `block_groups`
This table contains census block groups in Philadelphia, providing socioeconomic and demographic context layers.

| Column Name | Data Type | Source / Calculation | Description |
| :--- | :--- | :--- | :--- |
| **`GEOID`** | `VARCHAR` | Census Bureau | FIPS block group unique identifier (Primary Key). |
| **`population`** | `INTEGER` | Census ACS 2024 (5-Yr) | Total population count. |
| **`median_income`** | `INTEGER` | Census ACS 2024 (5-Yr) | Median household income in USD (suppressed/null for tracts with low population density). |
| **`geometry`** | `GEOMETRY` | Census TIGER/Line | Polygon boundary geometry of the census block group (EPSG:4326). |
