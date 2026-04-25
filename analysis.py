# Here's my goal.
# Visualize relationship between crashes and "all" - 1 map
# Correlation Table
# Some crash analytics:
# - crash rate (crash_count / length_ft)
# - crashes by road class
# - anything else that pops out in the correlation table
# %%
import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt
import seaborn as sns
import plotly as ptly
from mpl_toolkits.axes_grid1 import make_axes_locatable
import numpy as np
import statsmodels.api as sm
import statsmodels.formula.api as smf
from scipy.stats import chi2

# %%
crash_data = gpd.read_file(
    "transformed-data/Stash or final/philly_final_analytical_table.gpkg"
)

# %%
crash_data.head()
print(crash_data.columns.tolist())

# pick numeric cols
cols = [
    "maxspeed_inferred",
    "crash_count",
    "fatal_count",
    "injury_count",
    "susp_serious_inj_count",
    "ped_count",
    "bicycle_count",
    "severity_score",
    "cartway_width_ft",
    "cartway_paved_median_ft",
    "cartway_span_median_ft",
    "cartway_valid_share",
    "cartway_n_valid",
    # 'width_confidence',
    "state_lane_cnt",
    "state_total_width_ft",
    "state_aadt",
    # 'state_divisor_type',
    # 'bike_lane',
    # 'is_divided',
    "state_road_distance",
    # 'osm_lanes',
    # 'osm_maxspeed',
    # 'osm_highway',
    "dvrpc_aadt",
    "aadt_distance_ft",
    "has_aadt",
    "calming_device_count",
    # 'has_calming',
    "has_any_control",
    "has_conventional_stop",
    "has_all_way_stop",
    "has_signal",
    # 'GEOID',
    "median_income",
    "population",
    "commuters_total",
    "commute_drove_alone",
    "commute_transit",
    "commute_walked",
    "commute_wfh",
    "white_alone",
    "vacant_units",
    "median_rent",
    "median_age",
    "canopy_pct",
    "has_canopy",
    "tree_count",
    "grade_range_smooth",
    "grade_smooth_median",
    "grade_smooth_p90",
    "grade_smooth_max",
    "maxspeed_final",
    "lanes_final",
]

cols_min = [
    # Target
    "crash_count",
    # Road design (your primary framework)
    "cartway_width_ft",
    "lanes_final",
    "maxspeed_final",
    "is_divided",
    "has_signal",
    "has_calming",
    "calming_device_count",
    # Traffic exposure
    "dvrpc_aadt",
    # Environment (your hypothesis)
    "canopy_pct",
    "grade_range_smooth",
    # Context
    "median_income",
    "length",
    "class",
]


def string_to_bool_int(df, field):
    df[field] = df[field].map({"True": 1, "False": 0})


string_to_bool_int(crash_data, "is_divided")
string_to_bool_int(crash_data, "has_calming")

# crash_cor_data['is_divided'] = crash_cor_data['is_divided'].map({'True': 1, 'False': 0})

# %%

corr_cols = [
    "crash_count",
    # Road design (your primary framework)
    "cartway_width_ft",
    "lanes_final",
    "maxspeed_final",
    "has_signal",
    "has_calming",
    "dvrpc_aadt",
    # Environment (your hypothesis)
    "canopy_pct",
    "grade_range_smooth",
    # Context
    "median_income",
    "length",
    "class",
]

crash_cor_data = crash_data[corr_cols].copy()
corr = crash_cor_data.corr()

# %%

plt.figure(figsize=(25, 25))
sns.heatmap(
    corr,
    annot=True,
    fmt=".2f",
    cmap="RdBu_r",
    center=0,
    vmin=-1,
    vmax=1,
    square=True,
    cbar_kws={"shrink": 0.8},
)
plt.title("Correlation Matrix")
plt.tight_layout()
plt.tight_layout()
plt.savefig(
    "presentation_assets/correlat.png",
    dpi=200,
    bbox_inches="tight",
    facecolor="#0a0a0a",
)
plt.show()


# %%

# before we run regressions, we need to do some data prep

# non-na's
print(crash_data[cols_min].isna().sum().sort_values(ascending=False))
# lanes_final           39804
# is_divided            39804
# dvrpc_aadt            34267
# cartway_width_ft        387
# median_income           159
# canopy_pct               20

# our plan for lanes_final was to take state roads and then fallback to class:

# again, this isn't great and we'd love to find a better way, but for now.
lanes_by_class = {
    1: 4,  # Expressway
    2: 4,  # Major Arterial
    3: 2,  # Minor Arterial
    4: 2,  # Collector
    5: 2,  # Local
    9: 1,  # Low Speed Ramp
    10: 2,  # High Speed Ramp
}

crash_data["lanes_final"] = crash_data["lanes_final"].fillna(
    crash_data["class"].map(lanes_by_class)
)

# for non-divided, we also can see this is non-state roads (same count as lanes_final), so we'll fill na with 0s
# and we'll just say no, not divided. TODO: We will have to note this in our report
crash_data["is_divided"] = crash_data["is_divided"].fillna(0)

# For dvrpc_aadt - traffic counts - for now I'll keep it, even with the low coverage.
# I'll turn it into a flag (perhaps just the fact they're measuring says something?)
# and then we can maybe take the median just so we have numbers?
# TODO: Question this.
crash_data["has_aadt"] = crash_data["dvrpc_aadt"].notna().astype(int)
crash_data["dvrpc_aadt"] = crash_data["dvrpc_aadt"].fillna(
    crash_data["dvrpc_aadt"].median()
)


## Next, let's look at cartway width - we're pretty good here, let's fill with median for the missing roads.
## If we have time, we can scrutinize more.
crash_data["cartway_width_ft"] = crash_data["cartway_width_ft"].fillna(
    crash_data.groupby("class")["cartway_width_ft"].transform("median")
)

## and calming device count
crash_data["has_calming"] = (crash_data["calming_device_count"] > 0).astype(int)

# %%
# So, median income is a bit interesting. I would think we'd have for all
# could have cartways that fall outside of block groups:
nulls = crash_data[crash_data["median_income"].isna()]
print(len(nulls))
nulls.explore()

# aha! the cartways are either on a city boundary or over 95 in industrial zones.
# we can drop em
crash_data = crash_data.dropna(subset=["median_income"])

print(crash_data[cols_min].isna().sum().sort_values(ascending=False))


# alright NAs are preppedTODO: Go back and get the corrlation matrix with this fixed data.

# %%
cols_final = [
    # Target
    "crash_count",
    # Road design (your primary framework)
    "cartway_width_ft",
    "lanes_final",
    "maxspeed_final",
    "is_divided",
    "has_signal",
    "has_calming",
    # Traffic exposure
    "dvrpc_aadt",
    "has_aadt",
    # Environment (your hypothesis)
    "canopy_pct",
    "grade_range_smooth",
    # Context
    # "median_income", # dropping median income - we dont have trhe block level coverage and while there are ooptions, we'll add them if we have time
    "length",
    "class",
    "geometry",
]

# we still have some more prep to do. Let's get a subset of our data and then check out histograms
crash_data_prepping = crash_data[cols_final].copy()

crash_data_prepping.hist(figsize=(20, 15), bins=50)
plt.tight_layout()
plt.show()

# a few things here to adjust
# some log scaling to do frot he left skewed data (crash_count, dvrpc, length, grade_range_smooth (use log1p since it has 0s)
# - cartway width - we could cap outliers or leave it
# - median income I didn't clean! We have -7 - we'l;l drop for now
# nulls = crash_data[crash_data["median_income"] == -666666666]
# nulls.explore()

# TODO: Log scaling! anything else?
crash_data_prepping["log_aadt"] = np.log1p(crash_data_prepping["dvrpc_aadt"])
crash_data_prepping["log_length"] = np.log(crash_data_prepping["length"])
crash_data_prepping["log_grade"] = np.log1p(crash_data_prepping["grade_range_smooth"])

# %% [markdown]

# It's time to run some regression models.
# Since we're dealing with crash counts, and not continuous data, regular ol OLS isn't the best approach.
# Here I've done a bit of research and found that the two most common regressions for count distributions are
# Poisson and negative binomial regression. Poisson assumes constant variance and since crash data is sparse, certainly not spatially constantly (TODO: show or have map to show)
# we reach for negative binomial regression.


# %%
# m1 road design only
m1 = smf.glm(
    formula=(
        "crash_count ~ cartway_width_ft + lanes_final + maxspeed_final "
        "+ is_divided + has_signal + has_calming "
        "+ log_aadt + has_aadt"
    ),
    data=crash_data_prepping,
    family=sm.families.NegativeBinomial(),
    offset=crash_data_prepping[
        "log_length"
    ],  # we use log_length as the offset - the link - to transform the relationship to log/rate bsed
).fit()
print("=" * 60)
print("MODEL 1: Road design only")
print("=" * 60)
print(m1.summary())

# %% [markdown]
# ============================================================
# MODEL 1: Road design only
# ============================================================
#                  Generalized Linear Model Regression Results
# ==============================================================================
# Dep. Variable:            crash_count   No. Observations:                40331
# Model:                            GLM   Df Residuals:                    40322
# Model Family:        NegativeBinomial   Df Model:                            8
# Link Function:                    Log   Scale:                          1.0000
# Method:                          IRLS   Log-Likelihood:                -43879.
# Date:                Sat, 25 Apr 2026   Deviance:                       38759.
# Time:                        11:02:00   Pearson chi2:                 7.87e+04
# No. Iterations:                    29   Pseudo R-squ. (CS):             0.3193
# Covariance Type:            nonrobust
# ====================================================================================
#                        coef    std err          z      P>|z|      [0.025      0.975]
# ------------------------------------------------------------------------------------
# Intercept           -9.1781      0.111    -82.395      0.000      -9.396      -8.960
# cartway_width_ft     0.0072      0.000     19.245      0.000       0.006       0.008
# lanes_final          0.1855      0.014     13.529      0.000       0.159       0.212
# maxspeed_final       0.0513      0.002     23.072      0.000       0.047       0.056
# is_divided           0.0805      0.096      0.836      0.403      -0.108       0.269
# has_signal           1.4384      0.018     79.795      0.000       1.403       1.474
# has_calming          0.1350      0.050      2.682      0.007       0.036       0.234
# log_aadt             0.0303      0.013      2.397      0.017       0.006       0.055
# has_aadt            -0.0124      0.023     -0.531      0.595      -0.058       0.033


# Pseudo R-squ. (CS):             0.3193 <--- lots of room to do better! Can we?
# Interpretation:
# Some good significant variables
# The most interesting is has_calming is signifcant but it's positively correlated? Does that make any sense?
# WEll it does if you figure we're reacting to crashes
# - we place calming measures where crashes are.
# If we wanted to study their effectiveness, we could look at crash data for the same centerline segments before and after,
# or try to compare similar segments in terms of traffic and other road design, but without calming measures.

# %%
# m2 -> add environmental
m2 = smf.glm(
    formula=(
        "crash_count ~ cartway_width_ft + lanes_final + maxspeed_final "
        "+ is_divided + has_signal + has_calming "
        "+ log_aadt + has_aadt "
        "+ canopy_pct + log_grade"
    ),
    data=crash_data_prepping,
    family=sm.families.NegativeBinomial(),
    offset=crash_data_prepping["log_length"],
).fit()
print("=" * 60)
print("MODEL 2: Add environmental")
print("=" * 60)
print(m2.summary())


# %% [markdown]
# ============================================================
# MODEL 2: Add environmental
# ============================================================
#                  Generalized Linear Model Regression Results
# ==============================================================================
# Dep. Variable:            crash_count   No. Observations:                40331
# Model:                            GLM   Df Residuals:                    40320
# Model Family:        NegativeBinomial   Df Model:                           10
# Link Function:                    Log   Scale:                          1.0000
# Method:                          IRLS   Log-Likelihood:                -43806.
# Date:                Sat, 25 Apr 2026   Deviance:                       38612.
# Time:                        11:12:59   Pearson chi2:                 7.72e+04
# No. Iterations:                    29   Pseudo R-squ. (CS):             0.3218
# Covariance Type:            nonrobust
# ====================================================================================
#                        coef    std err          z      P>|z|      [0.025      0.975]
# ------------------------------------------------------------------------------------
# Intercept           -9.0353      0.112    -80.470      0.000      -9.255      -8.815
# cartway_width_ft     0.0068      0.000     18.116      0.000       0.006       0.008
# lanes_final          0.1890      0.014     13.770      0.000       0.162       0.216
# maxspeed_final       0.0505      0.002     22.683      0.000       0.046       0.055
# is_divided           0.0935      0.096      0.970      0.332      -0.095       0.282
# has_signal           1.4274      0.018     79.050      0.000       1.392       1.463
# has_calming          0.1420      0.050      2.818      0.005       0.043       0.241
# log_aadt             0.0270      0.013      2.142      0.032       0.002       0.052
# has_aadt            -0.0147      0.023     -0.628      0.530      -0.061       0.031
# canopy_pct          -0.7914      0.072    -10.917      0.000      -0.933      -0.649
# log_grade           -2.7630      0.712     -3.879      0.000      -4.159      -1.367
# ====================================================================================

# model does a bit better Pseudo R-squ. (CS):             0.3218
# we actually see that canopy_pct and log grade are both highly significant and negatively corrlated with crashes. Log grade extremely so!
# this is pretty fucking cool, but of course this is preliminary there could be explanations but pretty damn cool, I need to check for mistakes and a lot of other things.

# %%
# model 3 => let's check out interactions
m3 = smf.glm(
    formula=(
        "crash_count ~ cartway_width_ft + lanes_final + maxspeed_final "
        "+ is_divided + has_signal + has_calming "
        "+ log_aadt + has_aadt "
        "+ canopy_pct + log_grade "
        "+ canopy_pct:cartway_width_ft "
        "+ log_grade:maxspeed_final"
    ),
    data=crash_data_prepping,
    family=sm.families.NegativeBinomial(),
    offset=crash_data_prepping["log_length"],
).fit()
print("=" * 60)
print("MODEL 3: Add interactions")
print("=" * 60)
print(m3.summary())

# %% [markdown]
# ============================================================
# MODEL 3: Add interactions
# ============================================================
#                  Generalized Linear Model Regression Results
# ==============================================================================
# Dep. Variable:            crash_count   No. Observations:                40331
# Model:                            GLM   Df Residuals:                    40318
# Model Family:        NegativeBinomial   Df Model:                           12
# Link Function:                    Log   Scale:                          1.0000
# Method:                          IRLS   Log-Likelihood:                -43761.
# Date:                Sat, 25 Apr 2026   Deviance:                       38522.
# Time:                        11:23:09   Pearson chi2:                 7.72e+04
# No. Iterations:                    28   Pseudo R-squ. (CS):             0.3233
# Covariance Type:            nonrobust
# ===============================================================================================
#                                   coef    std err          z      P>|z|      [0.025      0.975]
# -----------------------------------------------------------------------------------------------
# Intercept                      -8.4234      0.121    -69.539      0.000      -8.661      -8.186
# cartway_width_ft                0.0066      0.000     16.956      0.000       0.006       0.007
# lanes_final                     0.1846      0.014     13.437      0.000       0.158       0.212
# maxspeed_final                  0.0314      0.003     11.876      0.000       0.026       0.037
# is_divided                      0.0928      0.096      0.965      0.335      -0.096       0.281
# has_signal                      1.4265      0.018     78.995      0.000       1.391       1.462
# has_calming                     0.1397      0.050      2.773      0.006       0.041       0.238
# log_aadt                        0.0255      0.013      2.015      0.044       0.001       0.050
# has_aadt                       -0.0091      0.023     -0.386      0.700      -0.055       0.037
# canopy_pct                     -1.4095      0.150     -9.366      0.000      -1.704      -1.115
# log_grade                     -51.2896      4.285    -11.969      0.000     -59.689     -42.891
# canopy_pct:cartway_width_ft     0.0166      0.003      4.939      0.000       0.010       0.023
# log_grade:maxspeed_final        1.5949      0.135     11.846      0.000       1.331       1.859
# ===============================================================================================

# %%
# Model comparison


# Model comparison
def lr_test(m_small, m_big, label):
    lr_stat = 2 * (m_big.llf - m_small.llf)
    df_diff = m_big.df_model - m_small.df_model
    p = 1 - chi2.cdf(lr_stat, df_diff)
    print(f"{label}: LR={lr_stat:.2f}, df={df_diff}, p={p:.4f}")


print("\n" + "=" * 60)
print("MODEL COMPARISON")
print("=" * 60)
comparison = pd.DataFrame(
    {
        "Model": ["M1: Road design", "M2: + Environment", "M3: + Interactions"],
        "AIC": [m1.aic, m2.aic, m3.aic],
        "Log-Likelihood": [m1.llf, m2.llf, m3.llf],
        "Pseudo-R²": [
            1 - m1.deviance / m1.null_deviance,
            1 - m2.deviance / m2.null_deviance,
            1 - m3.deviance / m3.null_deviance,
        ],
    }
)
print(comparison.to_string(index=False))

print()
lr_test(m1, m2, "M1 vs M2 (does environment add explanatory power?)")
lr_test(m2, m3, "M2 vs M3 (do interactions add explanatory power?)")
# %% [markdown]
# # MAPS!
# %%

# Map 1 -> Crash frequency by road segment

fig, ax = plt.subplots(figsize=(12, 12), facecolor="#0a0a0a")
ax.set_facecolor("#0a0a0a")
bg_geom_2272 = gpd.read_file("transformed-data/Census/just-geom.geojson")
# Background: city outline
bg_geom_2272.boundary.plot(ax=ax, color="#444", linewidth=0.5)


fig, ax = plt.subplots(figsize=(12, 12), facecolor="#0a0a0a")
ax.set_facecolor("#0a0a0a")

bg_geom_2272.boundary.plot(ax=ax, color="#444", linewidth=0.5)

divider = make_axes_locatable(ax)
cax = divider.append_axes("right", size="3%", pad=1.0)

crash_data.plot(
    ax=ax,
    column="crash_count",
    cmap="inferno",
    linewidth=0.5,
    vmin=0,
    vmax=crash_data["crash_count"].quantile(0.95),
    legend=True,
    cax=cax,
    legend_kwds={"label": "Crashes per segment"},
)

cax.tick_params(colors="white")
cax.yaxis.label.set_color("white")
cax.yaxis.labelpad = 15

ax.set_axis_off()
ax.set_title(
    "Crash Frequency by Road Segment, Philadelphia 2020-2024",
    color="white",
    fontsize=16,
    y=0.98,
)
plt.tight_layout()
plt.savefig(
    "presentation_assets/maps_crash_freq_road_segment.png",
    dpi=200,
    bbox_inches="tight",
    facecolor="#0a0a0a",
)
plt.show()


# %%
# What about a hexbin?
# Get crash points (not centerlines - we want the actual crash locations)
# This assumes you have crashes_2272 from earlier
crashes_2272 = gpd.read_file(
    "transformed-data/PennDOT Crash Data/crash_data_2272.geojson"
)


crash_points = crashes_2272.copy()
crash_points = crash_points[
    crash_points.geometry.notna() & ~crash_points.geometry.is_empty
]
crash_points["x"] = crash_points.geometry.x
crash_points["y"] = crash_points.geometry.y

fig, ax = plt.subplots(figsize=(12, 12), facecolor="#0a0a0a")
ax.set_facecolor("#0a0a0a")

# Set extent BEFORE plotting
xmin, ymin, xmax, ymax = bg_geom_2272.total_bounds
ax.set_xlim(xmin, xmax)
ax.set_ylim(ymin, ymax)

# # Hex bin - log scale initially, but we'll go linear.
hb = ax.hexbin(
    crash_points["x"],
    crash_points["y"],
    gridsize=120,
    cmap="inferno",
    mincnt=1,
    extent=(xmin, xmax, ymin, ymax),
    vmax=50,
)


# City outline on top, thinner
bg_geom_2272.boundary.plot(ax=ax, color="#666", linewidth=0.5, alpha=0.6)

cbar = plt.colorbar(hb, ax=ax, shrink=0.5, pad=0.04)
cbar.set_label("Crashes (log scale)", color="white")
cbar.ax.tick_params(colors="white")

ax.set_axis_off()
ax.set_aspect("equal")
ax.set_title(
    "Crash Density, Philadelphia 2020-2024", color="white", fontsize=16, y=0.98
)
plt.tight_layout()
plt.savefig(
    "presentation_assets/maps_crash_density_log_scale.png",
    dpi=200,
    bbox_inches="tight",
    facecolor="#0a0a0a",
)
plt.show()

# %%

## Tree canopy

fig, ax = plt.subplots(figsize=(20, 20), facecolor="#0a0a0a")
ax.set_facecolor("#0a0a0a")
bg_geom_2272.boundary.plot(ax=ax, color="#666", linewidth=0.5, alpha=0.6)

crash_data.plot(
    ax=ax,
    column="canopy_pct",
    cmap="Greens",
    linewidth=0.6,
    legend=True,
    legend_kwds={"label": "Tree canopy %", "shrink": 0.5, "pad": 0.04},
)

cbar = ax.get_figure().axes[-1]  # type: ignore
cbar.tick_params(colors="white")
cbar.yaxis.label.set_color("white")

ax.set_axis_off()
ax.set_title("Tree Canopy Coverage by Road Segment", color="white", fontsize=16, y=0.98)
plt.tight_layout()
plt.savefig(
    "presentation_assets/maps_tree_canopy_road_segment.png",
    dpi=200,
    bbox_inches="tight",
    facecolor="#0a0a0a",
)
plt.show()

# %%

# Elevation Grade
fig, ax = plt.subplots(figsize=(20, 20), facecolor="#0a0a0a")
ax.set_facecolor("#0a0a0a")
bg_geom_2272.boundary.plot(ax=ax, color="#666", linewidth=0.5, alpha=0.6)
crash_data.plot(
    ax=ax,
    column="grade_range_smooth",
    cmap="magma",
    linewidth=0.6,
    vmax=0.05,  # noticeable hill
    legend=True,
    legend_kwds={"label": "Elevation Grade %", "shrink": 0.5, "pad": 0.04},
)
cbar = ax.get_figure().axes[-1]  # type: ignore
cbar.tick_params(colors="white")
cbar.yaxis.label.set_color("white")

ax.set_axis_off()
ax.set_title("Elevation by Road Segment", color="white", fontsize=16, y=0.98)
plt.tight_layout()
plt.savefig(
    "presentation_assets/elevation_grade_road_segment.png",
    dpi=200,
    bbox_inches="tight",
    facecolor="#0a0a0a",
)
plt.show()

## add notes about grades: 0.03 -> noticeable hill; 0.05 -> Steep; 0.12 ->0.17 -> The Wall.
# %%
# Cartway width
fig, ax = plt.subplots(figsize=(20, 20), facecolor="#0a0a0a")
ax.set_facecolor("#0a0a0a")
bg_geom_2272.boundary.plot(ax=ax, color="#666", linewidth=0.5, alpha=0.6)
crash_data.plot(
    ax=ax,
    column="cartway_width_ft",
    cmap="viridis",
    linewidth=0.6,
    vmax=100,
    legend=True,
    legend_kwds={"label": "Cartway Width", "shrink": 0.5, "pad": 0.04},
)
cbar = ax.get_figure().axes[-1]  # type: ignore
cbar.tick_params(colors="white")
cbar.yaxis.label.set_color("white")

ax.set_axis_off()
ax.set_title("Cartway Width by Road Segment", color="white", fontsize=16, y=0.98)
plt.tight_layout()
plt.savefig(
    "presentation_assets/cartway_width_by_road_segment.png",
    dpi=200,
    bbox_inches="tight",
    facecolor="#0a0a0a",
)
plt.show()

# %%
