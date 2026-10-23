# -*- coding: utf-8 -*-
"""
MASTER RESULTS — single source of truth for every number quoted in the paper.
Collects values from the actual analysis outputs into master_results.json so
the manuscript, tables and figure captions all read the SAME numbers instead of
hand-typed copies (which previously drifted apart).
"""
import json, numpy as np, pandas as pd
from scipy import stats
from pathlib import Path
import os
import warnings; warnings.filterwarnings("ignore")

BASE = Path(os.environ.get("DER_PROJECT_ROOT", Path(__file__).resolve().parents[2]))
PROC = BASE / "Data" / "14_Processed_90m"
BKK  = BASE / "Data" / "14_Processed_Bangkok"
OUT  = BASE / "Data" / "master_results.json"

M = {}

# ── province EWM weights + entropy ────────────────────────────────────────────
W = pd.read_csv(PROC / "EWM_weights.csv")
LABEL = {"C1_Resource": "C1 Resource Potential", "C2_Equity": "C2 Equity",
         "C3_Demand": "C3 Demand Density", "C4_Infra": "C4 Infrastructure Access",
         "C5_Physical": "C5 Physical Suitability"}
M["weights"] = {r.criterion: round(float(r.weight), 4) for r in W.itertuples()}
M["entropy"] = {r.criterion: round(float(r.entropy), 4) for r in W.itertuples()}
# full precision retained separately: tables quote entropy to 6 dp
M["entropy_full"] = {r.criterion: float(r.entropy) for r in W.itertuples()}
M["weights_full"] = {r.criterion: float(r.weight) for r in W.itertuples()}
M["weights_sum"] = round(float(W.weight.sum()), 6)
M["labels"] = LABEL

# ── province PAI + zones ──────────────────────────────────────────────────────
s = pd.read_csv(PROC / "province_PAI_summary.csv")
M["n_provinces"] = int(len(s))
M["pai"] = {"min": round(float(s.PAI.min()), 4), "max": round(float(s.PAI.max()), 4),
            "mean": round(float(s.PAI.mean()), 4), "sd": round(float(s.PAI.std(ddof=1)), 4),
            "median": round(float(s.PAI.median()), 4)}
# zone land-area shares (projected areas, EPSG:32647)
import geopandas as gpd, fiona
_adm1 = next(l for l in fiona.listlayers(str(BASE / "Data" / "01_Admin_Boundaries" / "gadm41_THA.gpkg"))
             if l.endswith("_1"))
_g = gpd.read_file(str(BASE / "Data" / "01_Admin_Boundaries" / "gadm41_THA.gpkg"),
                   layer=_adm1)[["NAME_1", "geometry"]].to_crs("EPSG:32647")
_g["area"] = _g.geometry.area
_sa = s.merge(_g[["NAME_1", "area"]], on="NAME_1")
_tot_area = _sa["area"].sum()

M["zones"] = {}
for z in sorted(s.dominant_zone.unique()):
    sub = s[s.dominant_zone == z]
    sub_a = _sa[_sa.dominant_zone == z]
    M["zones"][int(z)] = {"n": int(len(sub)), "pai_mean": round(float(sub.PAI.mean()), 4),
                          "pai_min": round(float(sub.PAI.min()), 3),
                          "pai_max": round(float(sub.PAI.max()), 3),
                          "pai_sd": round(float(sub.PAI.std(ddof=1)), 4) if len(sub) > 1 else 0.0,
                          "land_pct": round(float(sub_a["area"].sum() / _tot_area * 100), 1)}
M["top10"] = s.nsmallest(10, "rank")[["rank", "NAME_1", "PAI"]].to_dict("records")
M["bottom5"] = s.nlargest(5, "rank")[["rank", "NAME_1", "PAI"]].to_dict("records")

# ── criterion correlations vs PAI + descriptive ───────────────────────────────
norm = pd.read_csv(PROC / "province_criteria_normalised.csv")
CR = list(W.criterion)
M["corr_vs_pai"] = {}
for c in CR:
    r, p = stats.spearmanr(norm[c], norm["PAI"])
    rp, pp = stats.pearsonr(norm[c], norm["PAI"])
    M["corr_vs_pai"][c] = {"spearman": round(float(r), 3), "spearman_p": round(float(p), 4),
                           "pearson": round(float(rp), 3), "pearson_p": round(float(pp), 4)}

# ── descriptive statistics on the normalised (model) matrix ───────────────────
# Section 4.1 quotes these; keeping them here stops the prose from drifting away
# from Table 4, which is generated from the same matrix.
M["descriptives"] = {}
for c in CR + ["PAI"]:
    v = norm[c].astype(float)
    M["descriptives"][c] = {
        "mean": round(float(v.mean()), 4), "sd": round(float(v.std(ddof=1)), 4),
        "median": round(float(v.median()), 4),
        "min": round(float(v.min()), 4), "max": round(float(v.max()), 4),
        "cv_pct": round(float(v.std(ddof=1) / v.mean() * 100), 2),
        "skew": round(float(stats.skew(v)), 3),
    }
# province names at the extremes of each criterion, for the narrative
M["criterion_extremes"] = {
    c: {"max": norm.loc[norm[c].idxmax(), "NAME_1"],
        "min": norm.loc[norm[c].idxmin(), "NAME_1"]} for c in CR
}

# ── VIF on the normalised (model) design matrix ───────────────────────────────
from statsmodels.stats.outliers_influence import variance_inflation_factor
_X = norm[CR].to_numpy(float)
_Xc = np.column_stack([np.ones(len(_X)), _X])
M["vif"] = {c: round(float(variance_inflation_factor(_Xc, i + 1)), 3)
            for i, c in enumerate(CR)}
M["vif_max"] = round(max(M["vif"].values()), 3)

# ── zone criterion means, on the SAME normalised matrix the model uses ────────
_nz = norm.merge(s[["NAME_1", "dominant_zone"]], on="NAME_1")
M["zone_criterion_means"] = {
    int(z): {c: round(float(g[c].mean()), 4) for c in CR}
    for z, g in _nz.groupby("dominant_zone")
}

# ── equity vs EFFICIENCY-ONLY composite (the defensible test) ─────────────────
X = norm[CR].to_numpy(float)
eff = [0, 2, 3, 4]
def ewm(Mx):
    n = Mx.shape[0]; Mp = Mx - Mx.min(0) + 1e-12
    P = Mp / Mp.sum(0, keepdims=True)
    e = np.clip(-(1/np.log(n))*(P*np.where(P > 0, np.log(P), 0)).sum(0), 0, 1)
    d = 1 - e; return d/d.sum()
def topsis(Mx, w):
    Mw = Mx*w
    return np.sqrt((Mw**2).sum(1))/(np.sqrt(((Mw-w)**2).sum(1))+np.sqrt((Mw**2).sum(1))+1e-12)
we = ewm(X[:, eff]); PAI_eff = topsis(X[:, eff], we)
r, p = stats.spearmanr(X[:, 1], PAI_eff)
M["equity_vs_efficiency_only"] = {"spearman": round(float(r), 3), "p": float(f"{p:.4g}")}
M["equity_vs_each_efficiency"] = {}
for j in eff:
    rr, pp = stats.spearmanr(X[:, 1], X[:, j])
    M["equity_vs_each_efficiency"][CR[j]] = {"spearman": round(float(rr), 3), "p": round(float(pp), 4)}
# rank change when C2 removed
rk_full = pd.Series(norm["PAI"]).rank(ascending=False)
rk_eff = pd.Series(PAI_eff).rank(ascending=False)
M["equity_removal"] = {"spearman_full_vs_eff": round(float(stats.spearmanr(norm["PAI"], PAI_eff)[0]), 3),
                       "max_rank_shift": int((rk_full - rk_eff).abs().max()),
                       "n_shift_gt10": int(((rk_full - rk_eff).abs() > 10).sum())}

# ── LISA / sensitivity / validation ───────────────────────────────────────────
# Global Moran's I recomputed here so the figures and text cannot diverge from it
L = pd.read_csv(PROC / "province_LISA.csv")
try:
    from libpysal.weights import Queen
    from esda.moran import Moran
    _gl = _g.merge(L[["NAME_1", "PAI"]], on="NAME_1")
    _w = Queen.from_dataframe(_gl, use_index=False); _w.transform = "r"
    np.random.seed(42)                      # fix permutation draw -> reproducible p_sim
    _mi = Moran(_gl["PAI"].to_numpy(float), _w, permutations=999)
    # report the analytic (normal-approximation) p as well; it does not depend on
    # the permutation draw, so the quoted "p < 0.001" is stable across runs
    M["morans_I"] = {"I": round(float(_mi.I), 4), "z": round(float(_mi.z_norm), 3),
                     "p": float(f"{_mi.p_sim:.4g}"),
                     "p_norm": float(f"{_mi.p_norm:.4g}"), "permutations": 999}
except Exception as e:                                   # keep the build usable
    M["morans_I"] = {"error": str(e)}
M["morans_I"].update({"n_HH": int((L.LISA_type == "HH").sum()),
                      "n_LL": int((L.LISA_type == "LL").sum()),
                      "n_HL": int((L.LISA_type == "HL").sum()),
                      "n_ns": int((L.LISA_type == "ns").sum())})
M["lisa_HH"] = L[L.LISA_type == "HH"].NAME_1.tolist()
M["lisa_LL"] = L[L.LISA_type == "LL"].NAME_1.tolist()

S = pd.read_csv(PROC / "sensitivity_summary.csv")
M["sensitivity"] = S.to_dict("records")
M["sensitivity_rho"] = {("equal" if "Equal" in r["Comparison"] else "expert"):
                        round(float(r["Spearman ρ"]), 4) for r in M["sensitivity"]}
v = pd.read_csv(PROC / "validation_solar_osm.csv")
r, p = stats.spearmanr(v.PAI, v.solar_count)
M["validation"] = {"n_plants": int(v.solar_count.sum()),
                   "pai_vs_count_spearman": round(float(r), 3), "p": round(float(p), 4)}
r2, p2 = stats.spearmanr(PAI_eff, v.sort_values("rank").reset_index(drop=True)["solar_count"]
                         if False else v.set_index("NAME_1").loc[norm["NAME_1"], "solar_count"].to_numpy())
M["validation"]["efficiency_only_vs_count_spearman"] = round(float(r2), 3)
M["validation"]["efficiency_only_p"] = float(f"{p2:.4g}")
r3, p3 = stats.spearmanr(X[:, 1], v.set_index("NAME_1").loc[norm["NAME_1"], "solar_count"].to_numpy())
M["validation"]["equity_vs_count_spearman"] = round(float(r3), 3)
M["validation"]["equity_p"] = float(f"{p3:.4g}")

# spatially restricted permutation tests (spatial_permutation_test.py)
try:
    _sp = json.loads((PROC / "spatial_permutation_results.json").read_text(encoding="utf-8"))
    M["spatial_permutation"] = _sp
    M["p_spatial"] = {r["label"]: r["p_spatial"]
                      for scale in _sp.values() for r in scale}
except Exception:
    pass

# zone-vs-installations distribution (written by validate_zones_province.py)
M["zone_validation"] = json.loads((PROC / "validation_zone_stats.json").read_text(encoding="utf-8"))

# MAUP across scales (maup_analysis.py) and per-zone grid distance (km)
try:
    M["maup"] = json.loads((PROC / "maup_results.json").read_text(encoding="utf-8"))
except Exception:
    pass
try:
    M["zone_grid_km"] = json.loads((PROC / "zone_grid_distance.json").read_text(encoding="utf-8"))
except Exception:
    pass
try:
    M["cluster_stability"] = json.loads((PROC / "cluster_stability.json").read_text(encoding="utf-8"))
except Exception:
    pass
try:
    M["gridfinder"] = json.loads((PROC / "gridfinder_distance.json").read_text(encoding="utf-8"))
except Exception:
    pass
try:
    M["pai_mv"] = json.loads((PROC / "sensitivity_pai_mv.json").read_text(encoding="utf-8"))
except Exception:
    pass
try:
    M["lisa_fdr"] = json.loads((PROC / "lisa_fdr.json").read_text(encoding="utf-8"))
except Exception:
    pass
try:
    M["bootstrap"] = json.loads((PROC / "bootstrap_uncertainty.json").read_text(encoding="utf-8"))
except Exception:
    pass
# SER construct check (validate_ser_external.py; corrected 77-province crosswalk)
try:
    _ser = pd.read_csv(PROC / "validation_ser_external.csv")
    _sk = {"our C2 (poverty) vs SER vulnerability": "c2_vs_vuln",
           "our C2 (poverty) vs SER poverty proxy": "c2_vs_poverty",
           "our PAI vs SER resilience": "pai_vs_resilience",
           "our PAI vs SER vulnerability": "pai_vs_vuln"}
    M["ser_check"] = {"n": 77}
    for r in _ser.itertuples():
        M["ser_check"][_sk[r.comparison]] = {"rho": round(float(r.spearman_rho), 3),
                                             "p": float(f"{r.p_value:.4g}")}
except Exception:
    pass

# ── district (Bangkok) ────────────────────────────────────────────────────────
# NOTE: the equity slot here is the BMA vulnerability index. Any weights file
# produced before that correction (bangkok_EWM_weights.csv) is superseded and
# must not be read: district weights are recomputed from the corrected model.
d = pd.read_csv(BKK / "bangkok_district_PAI_vuln.csv")
M["district"] = {"n": int(len(d)),
                 "pai_min": round(float(d.PAI_vuln.min()), 3),
                 "pai_max": round(float(d.PAI_vuln.max()), 3),
                 "pai_mean": round(float(d.PAI_vuln.mean()), 3),
                 "equity_vs_efficiency_only": round(float(stats.spearmanr(d.C2_Equity_norm, d.PAI3)[0]), 3)}
_DC = [c for c in ["C1_RooftopYield_norm", "C2_Equity_norm", "C3_Demand_norm", "C4_Infra_norm"]
       if c in d.columns]
if len(_DC) == 4:
    _Xd = d[_DC].to_numpy(float)
    _wd = ewm(_Xd)
    M["district"]["weights"] = {c.replace("_norm", ""): round(float(w), 4)
                                for c, w in zip(_DC, _wd)}
    M["district"]["corr_vs_pai"] = {
        c.replace("_norm", ""): round(float(stats.spearmanr(d[c], d.PAI_vuln)[0]), 3)
        for c in _DC}
# urban dimension: top-priority khet that are ALSO high-vulnerability, and the
# correlation of vulnerability with the composite (both positive -> targeting the
# disadvantaged does not cost priority within the city)
_dv = d.sort_values("rank_vuln")
M["district"]["top_khet"] = [
    {"name": r.NAME_2, "rank": int(r.rank_vuln), "pai": round(float(r.PAI_vuln), 3),
     "vuln": round(float(r.C2_Equity_norm), 3), "infra": round(float(r.C4_Infra_norm), 3)}
    for _, r in _dv.head(6).iterrows()]
M["district"]["vuln_vs_pai_spearman"] = round(
    float(stats.spearmanr(d.C2_Equity_norm, d.PAI_vuln)[0]), 3)
M["district"]["n_top10_highvuln"] = int(
    (_dv.head(10).C2_Equity_norm > 0.5).sum())  # how many of top-10 are above-median vuln

OUT.write_text(json.dumps(M, indent=2, ensure_ascii=False), encoding="utf-8")
print(json.dumps({k: M[k] for k in ["weights", "entropy", "weights_sum", "pai",
                                    "equity_vs_efficiency_only", "validation"]},
                 indent=2, ensure_ascii=False))
print(f"\nSaved: {OUT}")
