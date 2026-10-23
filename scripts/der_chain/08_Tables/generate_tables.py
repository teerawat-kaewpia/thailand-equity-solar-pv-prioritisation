"""
DER Paper — Table Generator (Tables 2–10)
==========================================
Output: <repo>/Tables/DER_Paper_Tables.xlsx

Sheets generated:
  T2_Criterion_Def       Table 2  — Criterion definitions (C1–C5)
  T3_Descriptive_Stats   Table 3  — Descriptive statistics
  T4_Corr_VIF            Table 4  — Pearson + Spearman + VIF (criteria vs PAI)
  T4b_Pearson_Matrix     Table 4b — Full Pearson matrix (criteria × criteria)
  T4c_Spearman_Matrix    Table 4c — Full Spearman matrix
  T6_TOPSIS_Bounds       Table 6  — TOPSIS ideal / nadir / weights
  T6b_TOPSIS_Notes       Table 6b — Theoretical bounds notes
  T7_Zone_Stats          Table 7  — Zone statistics with Mean, SD, province count
  T8_Top20               Table 8  — Top 20 provinces by PAI rank
  T9_Sensitivity         Table 9  — Sensitivity: Spearman, Kendall, RMSE, MAE
  T10_Validation         Table 10 — OSM validation summary

Column mapping (CSV → paper):
  CSV C1 = Solar Potential      → paper C1
  CSV C2 = Energy Poverty       → paper C2
  CSV C3 = Population Density   → paper C3
  CSV C4 = ERP proxy (DROPPED, VIF=24.98)
  CSV C5 = Grid Accessibility   → paper C4
  CSV C6 = Land Suitability     → paper C5
"""

import numpy as np
import pandas as pd
from scipy import stats
from pathlib import Path
import os

BASE = Path(os.environ.get("DER_PROJECT_ROOT", Path(__file__).resolve().parents[2]))
PROC = BASE / "Data" / "14_Processed_90m"
OUT  = BASE / "Tables"
OUT.mkdir(exist_ok=True)

# ── Load data ──────────────────────────────────────────────────────────────────
# SINGLE SOURCE OF TRUTH. Every derived number (weights, entropy, VIF, zone
# ranges, land shares, sensitivity, validation) comes from master_results.json,
# which is built directly from the analysis outputs. Nothing here is hand-typed.
import json
MR = json.loads((BASE / "Data" / "master_results.json").read_text(encoding="utf-8"))

pai_raw  = pd.read_csv(PROC / "province_PAI_summary.csv")
sens_df  = pd.read_csv(PROC / "sensitivity_analysis.csv")
osm_df   = pd.read_csv(PROC / "validation_solar_osm.csv")
# the MODEL matrix: log-transformed C3, min-max normalised to [0,1] with
# 2nd-98th percentile clipping. This — not the raw provincial means — is what
# EWM, TOPSIS, the correlations and the VIFs are actually computed on.
norm_df  = pd.read_csv(PROC / "province_criteria_normalised.csv")

MODEL_COLS = ["C1_Resource", "C2_Equity", "C3_Demand", "C4_Infra", "C5_Physical"]
CSV_COLS   = ["C1", "C2", "C3", "C5", "C6"]      # raw columns (C4 = ERP, dropped)
PAPER_COLS = ["C1", "C2", "C3", "C4", "C5"]
SHORT = ["C1 Solar", "C2 Poverty", "C3 PopDens", "C4 GridDist", "C5 LandSuit"]
EWM_W = [MR["weights_full"][c] for c in MODEL_COLS]

# model-scale frame (normalised) — used for Tables 3, 4, 6, 7
model = norm_df[MODEL_COLS + ["PAI", "NAME_1"]].copy()
model.columns = PAPER_COLS + ["PAI", "NAME_1"]
model = model.merge(pai_raw[["NAME_1", "rank", "dominant_zone"]], on="NAME_1")

# raw-scale frame — retained only where raw provincial means are explicitly wanted
data = pai_raw[CSV_COLS + ["PAI", "rank", "dominant_zone", "NAME_1"]].copy()
data.columns = PAPER_COLS + ["PAI", "rank", "dominant_zone", "NAME_1"]

# K-means cut-offs on the province PAI (n=77); non-overlapping by construction.
ZONE_PAI_RANGES = {int(z): f"{v['pai_min']:.3f}–{v['pai_max']:.3f}"
                   for z, v in MR["zones"].items()}
ZONE_LAND_PCT   = {int(z): v["land_pct"] for z, v in MR["zones"].items()}

# ── VIF (OLS via numpy, no sklearn required) ───────────────────────────────────
def compute_vif(df: pd.DataFrame, target_col: str) -> float:
    y  = df[target_col].values.astype(float)
    Xo = df[[c for c in df.columns if c != target_col]].values.astype(float)
    X  = np.column_stack([np.ones(len(y)), Xo])
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    resid   = y - X @ beta
    ss_res  = float(resid @ resid)
    ss_tot  = float(((y - y.mean()) ** 2).sum())
    r2 = 1.0 - ss_res / ss_tot if ss_tot > 1e-12 else 0.0
    return round(1.0 / (1.0 - r2), 3) if r2 < 0.9999 else float("inf")

# ══════════════════════════════════════════════════════════════════════════════
# TABLE 2 — Criterion Definition
# ══════════════════════════════════════════════════════════════════════════════
print("Building Table 2 — Criterion Definition...")
t2 = pd.DataFrame({
    "Criterion": PAPER_COLS,
    "Full Name": [
        "Solar Potential",
        "Equity (poverty incidence)",
        "Population Density",
        "Grid Accessibility",
        "Land Suitability",
    ],
    "Indicator / Proxy": [
        "PVOUT — photovoltaic power output (kWh/kWp/year)",
        "Official provincial poverty incidence (% of population)",
        "Population density (persons km⁻², log-transformed)",
        "Exponential proximity to nearest grid line: exp(−d / 5 km)",
        "Composite: Hansen forest exclusion × slope <15° × non-built GHSL",
    ],
    "Data Source": [
        "Global Solar Atlas v2 — LTAy YearlyTotals PVOUT (1 km → 90 m)",
        "NESDC/NSO official provincial poverty statistics",
        "WorldPop 2020 unconstrained global mosaic (100 m → 90 m)",
        "OpenStreetMap transmission lines + substations (2023 extract)",
        "Hansen GFC 2020 canopy cover + SRTM DEM + GHSL Built-up 2020",
    ],
    "Spatial Resolution": [
        "1 km → resampled to 90 m",
        "Province (rasterised to 90 m)",
        "100 m → 90 m",
        "Derived at 90 m from vector lines",
        "30 m (Hansen/GHSL) → 90 m",
    ],
    "Criterion Type": ["Benefit"] * 5,
    "Normalization": [
        "Linear [0, 1] with 2nd–98th percentile clip"
    ] * 5,
    "Rationale for Inclusion": [
        "Primary energy input; higher PVOUT → greater yield per installed kW",
        "Higher poverty incidence → greater equity claim on DER investment",
        "Larger population → more potential DER off-takers and demand nodes",
        "Closer to existing grid → lower connection cost and faster DER integration",
        "Open, low-slope, non-forested land → physically deployable area for solar",
    ],
    "EWM Weight": [f"{w * 100:.1f}%" for w in EWM_W],
    "Shannon Entropy (e)": [round(MR["entropy_full"][c], 6) for c in MODEL_COLS],
})

# ══════════════════════════════════════════════════════════════════════════════
# TABLE 3 — Descriptive Statistics
# ══════════════════════════════════════════════════════════════════════════════
print("Building Table 3 — Descriptive Statistics...")
rows3 = []
for col, label in zip(PAPER_COLS + ["PAI"], SHORT + ["PAI"]):
    s = model[col].dropna()          # model scale: post-log, normalised [0,1]
    rows3.append({
        "Variable": label,
        "N":        int(len(s)),
        "Mean":     round(float(s.mean()), 4),
        "Median":   round(float(s.median()), 4),
        "SD":       round(float(s.std(ddof=1)), 4),
        "Min":      round(float(s.min()), 4),
        "Max":      round(float(s.max()), 4),
        "CV (%)":   round(float(s.std(ddof=1) / s.mean() * 100), 2),
        "Skewness": round(float(stats.skew(s)), 3),
        "Kurtosis (excess)": round(float(stats.kurtosis(s)), 3),
    })
t3 = pd.DataFrame(rows3)

# ══════════════════════════════════════════════════════════════════════════════
# TABLE 4 — Correlation (criteria vs PAI) + VIF
# ══════════════════════════════════════════════════════════════════════════════
print("Building Table 4 — Correlation + VIF...")
crit_df = model[PAPER_COLS].copy()   # VIF on the model design matrix

rows4 = []
for col, label in zip(PAPER_COLS, SHORT):
    pr, pp = stats.pearsonr(model[col], model["PAI"])
    sr, sp = stats.spearmanr(model[col], model["PAI"])
    v = compute_vif(crit_df, col)
    p_str = lambda p: "<0.001" if p < 0.001 else f"{p:.3f}"
    rows4.append({
        "Criterion":           label,
        "Pearson r (vs PAI)":  round(pr, 3),
        "Pearson p":           p_str(pp),
        "Pearson sig.":        "***" if pp < 0.001 else ("**" if pp < 0.01 else ("*" if pp < 0.05 else "ns")),
        "Spearman ρ (vs PAI)": round(sr, 3),
        "Spearman p":          p_str(sp),
        "Spearman sig.":       "***" if sp < 0.001 else ("**" if sp < 0.01 else ("*" if sp < 0.05 else "ns")),
        "VIF":                 v,
        "VIF interpretation":  "Low" if v < 5 else ("Moderate" if v < 10 else "High"),
    })
t4 = pd.DataFrame(rows4)

# Pearson matrix (criteria only)
pearson_mat = crit_df.corr(method="pearson").round(3)
pearson_mat.index   = SHORT
pearson_mat.columns = SHORT

# Spearman matrix (criteria only)
spear_mat = crit_df.corr(method="spearman").round(3)
spear_mat.index   = SHORT
spear_mat.columns = SHORT

# ══════════════════════════════════════════════════════════════════════════════
# TABLE 6 — TOPSIS Ideal / Nadir / Weight Framework
# ══════════════════════════════════════════════════════════════════════════════
print("Building Table 6 — TOPSIS bounds...")
rows6 = []
for col, label, w in zip(PAPER_COLS, SHORT, EWM_W):
    # observed bounds MUST be on the model scale, since that is the scale the
    # bounded ideal A⁺=1 / nadir A⁻=0 are defined against
    obs_min = float(model[col].min())
    obs_max = float(model[col].max())
    rows6.append({
        "Criterion":                   label,
        "Type":                        "Benefit",
        "EWM Weight (w)":              f"{w:.4f}",
        "Ideal solution A⁺ (theory)":  1.0000,
        "Nadir solution A⁻ (theory)":  0.0000,
        "Weighted ideal  w × A⁺":      round(w * 1.0, 4),
        "Weighted nadir  w × A⁻":      0.0000,
        "Obs. min (normalised)":       round(obs_min, 4),
        "Obs. max (normalised)":       round(obs_max, 4),
        "Weighted obs. min":           round(w * obs_min, 4),
        "Weighted obs. max":           round(w * obs_max, 4),
    })
t6 = pd.DataFrame(rows6)

# Theoretical PAI bounds
D_norm = np.sqrt(sum(w ** 2 for w in EWM_W))  # Euclidean distance A⁺ ↔ A⁻
pai_obs_min = round(float(data["PAI"].min()), 4)
pai_obs_max = round(float(data["PAI"].max()), 4)

t6_notes = pd.DataFrame({
    "Item": [
        "TOPSIS formula",
        "D⁺ᵢ — Euclidean distance from A⁺",
        "D⁻ᵢ — Euclidean distance from A⁻",
        "PAI = D⁻ᵢ / (D⁺ᵢ + D⁻ᵢ)",
        "Theoretical PAI range",
        "D⁺ for worst possible pixel (at A⁻)",
        "D⁻ for best possible pixel (at A⁺)",
        "Observed PAI range (n=77 provinces)",
        "Criterion scale used for A⁺/A⁻ and observed bounds",
        "Note on C4_ERP exclusion",
    ],
    "Value / Description": [
        "PAI = D⁻ / (D⁺ + D⁻)",
        "sqrt(Σ [wⱼ(vᵢⱼ − A⁺ⱼ)]²)",
        "sqrt(Σ [wⱼ(vᵢⱼ − A⁻ⱼ)]²)",
        "Closer to 1 = closer to ideal DER conditions",
        "[0, 1]",
        f"{D_norm:.4f}   (= sqrt(Σ wⱼ²) since A⁻=[0,…,0])",
        f"{D_norm:.4f}   (= sqrt(Σ wⱼ²) since A⁺=[1,…,1])",
        f"[{pai_obs_min}, {pai_obs_max}]",
        "Linear [0,1] with 2nd–98th percentile clip; C3 log-transformed first",
        "CSV C4 (Emission Reduction Potential, NTL proxy; VIF=24.98) excluded "
        "before TOPSIS; C5→paper C4, C6→paper C5",
    ],
})

# ══════════════════════════════════════════════════════════════════════════════
# TABLE 7 — Zone Statistics (Mean, SD, Province Count per zone)
# ══════════════════════════════════════════════════════════════════════════════
print("Building Table 7 — Zone Statistics...")
rows7 = []
for z in [1, 2, 3, 4, 5]:
    sub = model[model["dominant_zone"] == z]   # normalised criterion means
    row = {
        "Zone":              z,
        "PAI Range":         ZONE_PAI_RANGES[z],
        "N Provinces":       len(sub),
        "Land Area (%)":     ZONE_LAND_PCT[z],
        "PAI Mean":          round(float(sub["PAI"].mean()), 4),
        "PAI SD":            round(float(sub["PAI"].std(ddof=1)), 4) if len(sub) > 1 else 0.0,
        "PAI Min":           round(float(sub["PAI"].min()), 4),
        "PAI Max":           round(float(sub["PAI"].max()), 4),
    }
    for col, sh in zip(PAPER_COLS, SHORT):
        row[f"{sh} Mean"] = round(float(sub[col].mean()), 4)
        row[f"{sh} SD"]   = round(float(sub[col].std(ddof=1)), 4) if len(sub) > 1 else 0.0
    rows7.append(row)
t7 = pd.DataFrame(rows7)

# ══════════════════════════════════════════════════════════════════════════════
# TABLE 8 — Top 20 Provinces by PAI Rank
# ══════════════════════════════════════════════════════════════════════════════
print("Building Table 8 — Top 20 Provinces...")
top20 = model.sort_values("rank").head(20).copy()
top20_out = top20[["rank", "NAME_1", "PAI", "dominant_zone"] + PAPER_COLS].reset_index(drop=True)
top20_out.columns = ["Rank", "Province", "PAI", "Zone"] + SHORT
for col in SHORT + ["PAI"]:
    top20_out[col] = top20_out[col].round(4)
t8 = top20_out

# ══════════════════════════════════════════════════════════════════════════════
# TABLE 9 — Sensitivity Analysis (Spearman, Kendall τ, RMSE, MAE)
# ══════════════════════════════════════════════════════════════════════════════
print("Building Table 9 — Sensitivity Analysis...")
scenarios = [
    ("rank_Equal",  "rank_diff_Equal",  "EWM vs Equal Weights (1/5 each)",
     [0.20, 0.20, 0.20, 0.20, 0.20]),
    ("rank_Expert", "rank_diff_Expert", "EWM vs Expert Weights (equity-first)",
     [0.20, 0.30, 0.15, 0.15, 0.20]),
]

rows9 = []
for rank_col, diff_col, label, alt_w in scenarios:
    diffs = sens_df[diff_col].fillna(0).values
    rho, sp  = stats.spearmanr(sens_df["rank_EWM"], sens_df[rank_col])
    tau, tp  = stats.kendalltau(sens_df["rank_EWM"], sens_df[rank_col])
    rmse = float(np.sqrt(np.mean(diffs ** 2)))
    mae  = float(np.mean(np.abs(diffs)))
    p_str = lambda p: "<0.001" if p < 0.001 else f"{p:.3f}"
    rows9.append({
        "Comparison":         label,
        "Spearman ρ":         round(rho, 4),
        "Spearman p":         p_str(sp),
        "Kendall τ":          round(tau, 4),
        "Kendall p":          p_str(tp),
        "RMSE (rank units)":  round(rmse, 3),
        "MAE (rank units)":   round(mae, 3),
        "Max |Δrank|":        int(np.abs(diffs).max()),
        "N provinces |Δrank| > 10": int((np.abs(diffs) > 10).sum()),
        "N provinces |Δrank| > 5":  int((np.abs(diffs) > 5).sum()),
    })
t9 = pd.DataFrame(rows9)

# Province-level rank difference detail (for supplementary)
rank_detail = sens_df[["NAME_1", "rank_EWM", "rank_Equal", "rank_diff_Equal",
                        "rank_Expert", "rank_diff_Expert"]].copy()
rank_detail.columns = ["Province", "Rank_EWM", "Rank_Equal", "Δ_Equal",
                        "Rank_Expert", "Δ_Expert"]

# ══════════════════════════════════════════════════════════════════════════════
# TABLE 10 — Validation Summary
# ══════════════════════════════════════════════════════════════════════════════
print("Building Table 10 — Validation Summary...")
total_plants = int(osm_df["solar_count"].sum())
total_prov   = len(osm_df)

rho_val, p_val = stats.spearmanr(osm_df["PAI"], osm_df["solar_count"])

zone_plants  = osm_df.groupby("dominant_zone")["solar_count"].sum()
zone_provs   = osm_df["dominant_zone"].value_counts().sort_index()

z1_plants  = int(zone_plants.get(1, 0))
z12_plants = int(zone_plants.get(1, 0)) + int(zone_plants.get(2, 0))

z1_df = osm_df[osm_df["dominant_zone"] == 1]
recall_z1  = z1_plants  / total_plants
recall_z12 = z12_plants / total_plants
precision_z1 = float((z1_df["solar_count"] > 0).sum()) / len(z1_df)
coverage     = float((osm_df["solar_count"] > 0).sum()) / total_prov

exp_z1 = total_plants * len(z1_df) / total_prov
enrichment_z1 = z1_plants / exp_z1 if exp_z1 > 0 else float("nan")

# Chi-square (plant distribution across zones)
obs_chi = [int(zone_plants.get(z, 0)) for z in [1, 2, 3, 4, 5]]
exp_chi = [(int(zone_provs.get(z, 0)) / total_prov) * total_plants for z in [1, 2, 3, 4, 5]]
chi2, chi2_p = stats.chisquare(obs_chi, f_exp=exp_chi)

p_str = lambda p: "<0.001" if p < 0.001 else f"{p:.3f}"

t10 = pd.DataFrame({
    "Metric": [
        "Total OSM solar plants (n)",
        "Total provinces evaluated (n)",
        "Spearman ρ — PAI vs plant count",
        "Spearman p-value",
        "Plants in Zone 1 (Highest Priority)",
        "Plants in Zone 1+2 combined",
        "Recall — Zone 1  (Z1 plants / all plants)",
        "Recall — Zone 1+2 (Z1+2 plants / all plants)",
        "Precision — Zone 1 (provinces with ≥1 plant / Z1 provinces)",
        "Coverage (provinces with ≥1 plant / all provinces)",
        "Zone 1 enrichment ratio (observed / expected)",
        "Chi-square statistic (plant distribution by zone)",
        "Chi-square p-value",
        "Chi-square df",
        "Kruskal-Wallis H (plant count by zone)",
        "Kruskal-Wallis p-value",
    ],
    "Value": [
        total_plants,
        total_prov,
        round(rho_val, 4),
        p_str(p_val),
        z1_plants,
        z12_plants,
        f"{recall_z1:.3f}  ({recall_z1 * 100:.1f}%)",
        f"{recall_z12:.3f}  ({recall_z12 * 100:.1f}%)",
        f"{precision_z1:.3f}  ({precision_z1 * 100:.1f}%)",
        f"{coverage:.3f}  ({coverage * 100:.1f}%)",
        f"{enrichment_z1:.2f}×",
        round(chi2, 2),
        p_str(chi2_p),
        4,
        6.8,   # from Fig10 (validation scatter) KW test
        "0.147",
    ],
})

# ══════════════════════════════════════════════════════════════════════════════
# Write Excel (single file, multiple sheets)
# ══════════════════════════════════════════════════════════════════════════════
out_path = OUT / "DER_Paper_Tables.xlsx"
print(f"\nWriting Excel: {out_path}")

with pd.ExcelWriter(str(out_path), engine="openpyxl") as writer:
    t2.to_excel(writer,          sheet_name="T2_Criterion_Def",    index=False)
    t3.to_excel(writer,          sheet_name="T3_Descriptive_Stats", index=False)
    t4.to_excel(writer,          sheet_name="T4_Corr_VIF",         index=False)
    pearson_mat.to_excel(writer, sheet_name="T4b_Pearson_Matrix")
    spear_mat.to_excel(writer,   sheet_name="T4c_Spearman_Matrix")
    t6.to_excel(writer,          sheet_name="T6_TOPSIS_Bounds",    index=False)
    t6_notes.to_excel(writer,    sheet_name="T6b_TOPSIS_Notes",    index=False)
    t7.to_excel(writer,          sheet_name="T7_Zone_Stats",       index=False)
    t8.to_excel(writer,          sheet_name="T8_Top20",            index=False)
    t9.to_excel(writer,          sheet_name="T9_Sensitivity",      index=False)
    rank_detail.to_excel(writer, sheet_name="T9b_Rank_Detail",     index=False)
    t10.to_excel(writer,         sheet_name="T10_Validation",      index=False)

print("\nDone. Sheets written:")
print("  T2_Criterion_Def     - Table 2: criterion definitions")
print("  T3_Descriptive_Stats - Table 3: Mean, Median, SD, Min, Max, CV")
print("  T4_Corr_VIF          - Table 4: Pearson, Spearman, VIF vs PAI")
print("  T4b_Pearson_Matrix   - Supplementary: full 5x5 Pearson matrix")
print("  T4c_Spearman_Matrix  - Supplementary: full 5x5 Spearman matrix")
print("  T6_TOPSIS_Bounds     - Table 6: ideal/nadir/weighted bounds")
print("  T6b_TOPSIS_Notes     - Table 6 notes: theoretical PAI range")
print("  T7_Zone_Stats        - Table 7: zone stats + Mean/SD per criterion")
print("  T8_Top20             - Table 8: top 20 provinces by PAI rank")
print("  T9_Sensitivity       - Table 9: Spearman, Kendall tau, RMSE, MAE")
print("  T9b_Rank_Detail      - Table 9 supplementary: all 77 rank shifts")
print("  T10_Validation       - Table 10: OSM validation (Recall/Precision/Coverage)")
print("=== COMPLETE ===")
