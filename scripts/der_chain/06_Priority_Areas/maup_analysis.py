# -*- coding: utf-8 -*-
"""
Modifiable Areal Unit Problem (MAUP) analysis — reviewer appendix.

Re-runs the EXACT province pipeline (log1p C3 -> [0,1] 2nd-98th clip -> EWM
float64 -> bounded-ideal TOPSIS) at three nested administrative scales:

    Region  (6, NESDB grouping — conventional, see note)   coarser
    Province(77, the paper's unit of analysis)              baseline
    Amphoe  (928, GADM ADM-2)                               finer

and reports how the entropy weights and the priority ordering change with the
unit of aggregation. Amphoe is the clean, uncontestable finer level (it nests
exactly inside provinces); the 6-region grouping is a conventional coarse
illustration and its exact province assignment is noted as such.

Purpose: quantify the MAUP the paper flags in Section 6.2, and test whether the
central weighting result (equity is the dominant, or near-dominant, criterion)
and the efficiency-equity tension are scale-robust — which would strengthen,
not undermine, the scale-dependence finding.

Output: Data/14_Processed_90m/maup_results.json
"""
import json
import numpy as np
import pandas as pd
import geopandas as gpd
import fiona
import rasterio
from rasterstats import zonal_stats
from scipy import stats
from pathlib import Path
import os
import warnings
warnings.filterwarnings("ignore")

BASE = Path(os.environ.get("ENERGY_DATA_ROOT", r"D:\Clude Code GIS\Energy"))  # raw data (Tier-2), override via env
PROC = BASE / "DER" / "Data" / "14_Processed_90m"
GADM = BASE / "DER" / "Data" / "01_Admin_Boundaries" / "gadm41_THA.gpkg"

LAYERS = {  # paper label -> raster (same as compute_pai_province_level.py)
    "C1_Resource": "C1_PVOUT_90m.tif",
    "C2_Equity":   "C2_poverty_90m.tif",
    "C3_Demand":   "C3_popdens_90m.tif",
    "C4_Infra":    "C5_grid_dist_90m.tif",
    "C5_Physical": "C6_land_suitability_90m.tif",
}
NAMES = list(LAYERS)
LOG_CRIT = "C3_Demand"

# NESDB 6-region grouping (conventional; used only for the coarse illustration)
REGION = {
    "North": ["Chiang Mai", "Chiang Rai", "Lampang", "Lamphun", "Mae Hong Son",
              "Nan", "Phayao", "Phrae", "Uttaradit"],
    "Northeast": ["Amnat Charoen", "Bueng Kan", "Buri Ram", "Chaiyaphum", "Kalasin",
                  "Khon Kaen", "Loei", "Maha Sarakham", "Mukdahan", "Nakhon Phanom",
                  "Nakhon Ratchasima", "Nong Bua Lam Phu", "Nong Khai", "Roi Et",
                  "Sakon Nakhon", "Si Sa Ket", "Surin", "Ubon Ratchathani",
                  "Udon Thani", "Yasothon"],
    "Central": ["Ang Thong", "Bangkok Metropolis", "Chai Nat", "Kamphaeng Phet",
                "Lop Buri", "Nakhon Nayok", "Nakhon Pathom", "Nakhon Sawan",
                "Nonthaburi", "Pathum Thani", "Phetchabun", "Phichit", "Phitsanulok",
                "Phra Nakhon Si Ayutthaya", "Samut Prakan", "Samut Sakhon",
                "Samut Songkhram", "Saraburi", "Sing Buri", "Sukhothai",
                "Suphan Buri", "Uthai Thani"],
    "East": ["Chachoengsao", "Chanthaburi", "Chon Buri", "Prachin Buri", "Rayong",
             "Sa Kaeo", "Trat"],
    "West": ["Kanchanaburi", "Phetchaburi", "Prachuap Khiri Khan", "Ratchaburi", "Tak"],
    "South": ["Chumphon", "Krabi", "Nakhon Si Thammarat", "Narathiwat", "Pattani",
              "Phangnga", "Phatthalung", "Phuket", "Ranong", "Satun", "Songkhla",
              "Surat Thani", "Trang", "Yala"],
}
PROV2REG = {p: r for r, ps in REGION.items() for p in ps}
assert sum(len(v) for v in REGION.values()) == 77, "region map must cover 77 provinces"


def norm01(v):
    lo, hi = np.nanpercentile(v, 2), np.nanpercentile(v, 98)
    return np.clip((v - lo) / (hi - lo + 1e-12), 0.0, 1.0)


def ewm_topsis(raw_by_crit):
    """raw_by_crit: dict criterion -> raw mean array. Returns weights, PAI, X."""
    rm = dict(raw_by_crit)
    rm[LOG_CRIT] = np.log1p(raw_by_crit[LOG_CRIT] * 100.0)
    X = np.column_stack([norm01(rm[k]) for k in NAMES]).astype(np.float64)
    n = X.shape[0]
    Xp = X - X.min(0) + 1e-12
    P = Xp / Xp.sum(0, keepdims=True)
    e = np.clip(-(1 / np.log(n)) * (P * np.where(P > 0, np.log(P), 0)).sum(0), 0, 1)
    w = (1 - e) / (1 - e).sum()
    Xw = X * w
    PAI = np.sqrt((Xw ** 2).sum(1)) / (np.sqrt(((Xw - w) ** 2).sum(1))
                                       + np.sqrt((Xw ** 2).sum(1)) + 1e-12)
    return w, PAI, X


def eff_equity_rho(X):
    eff = [0, 2, 3, 4]
    Xe = X[:, eff]
    Pe = Xe - Xe.min(0) + 1e-12
    Pp = Pe / Pe.sum(0, keepdims=True)
    ee = np.clip(-(1 / np.log(len(Xe))) * (Pp * np.where(Pp > 0, np.log(Pp), 0)).sum(0), 0, 1)
    we = (1 - ee) / (1 - ee).sum()
    Xew = Xe * we
    paie = np.sqrt((Xew ** 2).sum(1)) / (np.sqrt(((Xew - we) ** 2).sum(1))
                                         + np.sqrt((Xew ** 2).sum(1)) + 1e-12)
    r, p = stats.spearmanr(X[:, 1], paie)
    return round(float(r), 3), float(f"{p:.4g}")


def summarise(scale, w, PAI, X, names_units, note=""):
    top = names_units[int(np.argmax(PAI))]
    order = {n: (NAMES[i], round(float(w[i]), 4)) for i, n in enumerate(NAMES)}
    dom = NAMES[int(np.argmax(w))]
    r_ee, p_ee = eff_equity_rho(X)
    print(f"\n[{scale}]  n = {len(PAI)}   {note}")
    print("  EWM weights: " + "  ".join(f"{k.split('_')[0]}={w[i]:.3f}" for i, k in enumerate(NAMES)))
    print(f"  dominant criterion: {dom}   |   equity vs efficiency-only: "
          f"rho={r_ee:+.3f} (p={p_ee})   |   top unit: {top}")
    return {"n": int(len(PAI)),
            "weights": {NAMES[i]: round(float(w[i]), 4) for i in range(len(NAMES))},
            "dominant_criterion": dom,
            "equity_vs_efficiency_rho": r_ee, "equity_vs_efficiency_p": p_ee,
            "top_unit": top, "note": note}


results = {}

# ── PROVINCE (baseline) — read the raw means already stored ───────────────────
s = pd.read_csv(PROC / "province_PAI_summary.csv")
raw_prov = {"C1_Resource": s.C1.values, "C2_Equity": s.C2.values,
            "C3_Demand": s.C3.values, "C4_Infra": s.C5.values,
            "C5_Physical": s.C6.values}
raw_prov = {k: np.asarray(v, float) for k, v in raw_prov.items()}
wP, paiP, XP = ewm_topsis(raw_prov)
results["province"] = summarise("PROVINCE", wP, paiP, XP, s.NAME_1.tolist(),
                                "baseline — paper unit")
prov_pai = pd.Series(paiP, index=s.NAME_1.values)

# ── REGION (coarse) — area-weighted aggregate of province raw means ───────────
adm1 = next(l for l in fiona.listlayers(str(GADM)) if l.endswith("_1"))
g1 = gpd.read_file(str(GADM), layer=adm1)[["NAME_1", "geometry"]].to_crs("EPSG:32647")
g1["area"] = g1.geometry.area
areas = dict(zip(g1.NAME_1, g1.area))
sr = s.copy()
sr["region"] = sr.NAME_1.map(PROV2REG)
sr["area"] = sr.NAME_1.map(areas)
raw_reg = {}
reg_order = list(REGION)
for lbl, col in [("C1_Resource", "C1"), ("C2_Equity", "C2"), ("C3_Demand", "C3"),
                 ("C4_Infra", "C5"), ("C5_Physical", "C6")]:
    raw_reg[lbl] = np.array([np.average(sr[sr.region == r][col], weights=sr[sr.region == r]["area"])
                             for r in reg_order])
wR, paiR, XR = ewm_topsis(raw_reg)
results["region"] = summarise("REGION", wR, paiR, XR, reg_order,
                              "NESDB 6-region grouping (conventional); n=6 -> weights fragile")

# ── AMPHOE (fine) — zonal stats over the rasters, 928 units ───────────────────
adm2 = next(l for l in fiona.listlayers(str(GADM)) if l.endswith("_2"))
g2 = gpd.read_file(str(GADM), layer=adm2)[["NAME_1", "NAME_2", "geometry"]].to_crs("EPSG:4326")
print(f"\nAmphoe zonal stats over {len(g2)} units (this takes a few minutes)...")
raw_amp = {}
for k, f in LAYERS.items():
    with rasterio.open(PROC / f) as src:
        nod = src.nodata
    vals = np.array([z["mean"] for z in
                     zonal_stats(g2, str(PROC / f), stats=["mean"], nodata=nod, all_touched=True)],
                    float)
    raw_amp[k] = vals
    print(f"  {k:12s} done  ({np.isfinite(vals).sum()}/{len(vals)} with data)")
# drop amphoe with any missing criterion (coastal slivers etc.)
mask = np.all([np.isfinite(raw_amp[k]) for k in NAMES], axis=0)
g2v = g2[mask].reset_index(drop=True)
raw_amp = {k: raw_amp[k][mask] for k in NAMES}
wA, paiA, XA = ewm_topsis(raw_amp)
results["amphoe"] = summarise("AMPHOE", wA, paiA, XA, g2v.NAME_2.tolist(),
                              f"GADM ADM-2; {int(mask.sum())}/{len(mask)} amphoe with full data")

# ── cross-scale consistency: province rank from amphoe means vs direct ────────
amp_df = pd.DataFrame({"NAME_1": g2v.NAME_1.values, "PAI_amp": paiA})
prov_from_amp = amp_df.groupby("NAME_1").PAI_amp.mean()
common = prov_from_amp.index.intersection(prov_pai.index)
rho_pa, p_pa = stats.spearmanr(prov_pai.loc[common], prov_from_amp.loc[common])
results["province_vs_amphoe_mean"] = {
    "spearman": round(float(rho_pa), 3), "p": float(f"{p_pa:.4g}"), "n": int(len(common))}
print(f"\nProvince PAI vs (mean of its amphoe PAI): rho={rho_pa:+.3f} "
      f"(p={p_pa:.3g}, n={len(common)})")

# equity dominance across scales — the headline MAUP robustness statement
eq_rank = {sc: sorted(results[sc]["weights"], key=results[sc]["weights"].get,
                      reverse=True).index("C2_Equity") + 1
           for sc in ["region", "province", "amphoe"]}
results["equity_weight_rank_by_scale"] = eq_rank
print(f"\nEquity's rank among the 5 EWM weights — "
      f"Region {eq_rank['region']}, Province {eq_rank['province']}, Amphoe {eq_rank['amphoe']} "
      f"(1 = largest weight)")

(PROC / "maup_results.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
print(f"\nSaved: {PROC / 'maup_results.json'}")
