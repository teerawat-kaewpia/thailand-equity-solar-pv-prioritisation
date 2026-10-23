# -*- coding: utf-8 -*-
"""
PAI-MV sensitivity (reviewer request).

The baseline C4 Infrastructure criterion is transmission-line proximity
(C5_grid_dist_90m.tif). Medium-voltage (MV) distribution proximity, from the
GridFinder model (C5_grid_access_90m.tif, already 2nd-98th-pctl normalised),
gives a spatially opposite ordering: high-poverty peripheral provinces are far
from transmission yet often close to MV distribution.

This script swaps C4 -> MV proximity, re-derives province-level EWM weights and a
bounded-ideal TOPSIS PAI, and reports (i) new weights, (ii) rank agreement with
the published PAI, (iii) province rank shifts, (iv) Zone-1 retention, and (v) the
efficiency-equity association under the MV specification. Province-level (n=77),
matching the paper's inferential unit.

Output: DER/Data/14_Processed_90m/sensitivity_pai_mv.csv  (+ .json summary)
"""
import numpy as np, pandas as pd, geopandas as gpd, rasterio, fiona, json
from rasterio.mask import mask
from scipy import stats
from sklearn.cluster import KMeans
from pathlib import Path
import os

BASE = Path(os.environ.get("ENERGY_DATA_ROOT", r"D:\Clude Code GIS\Energy"))  # raw data (Tier-2), override via env
PROC = BASE / "DER" / "Data" / "14_Processed_90m"
GADM = BASE / "DER" / "Data" / "01_Admin_Boundaries" / "gadm41_THA.gpkg"
MV_TIF = PROC / "C5_grid_access_90m.tif"      # GridFinder MV/distribution proximity, [0,1]

CR = ["C1_Resource", "C2_Equity", "C3_Demand", "C4_Infra", "C5_Physical"]

# ── baseline (published) province criteria + PAI ──────────────────────────────
norm = pd.read_csv(PROC / "province_criteria_normalised.csv")
summ = pd.read_csv(PROC / "province_PAI_summary.csv")[["NAME_1", "rank", "dominant_zone"]]
norm = norm.merge(summ, on="NAME_1", validate="one_to_one")
assert len(norm) == 77, len(norm)

# ── province-mean MV proximity (zonal mean of the normalised GridFinder layer) ─
adm1 = next(l for l in fiona.listlayers(str(GADM)) if l.endswith("_1"))
prov = gpd.read_file(str(GADM), layer=adm1)[["NAME_1", "geometry"]]
with rasterio.open(MV_TIF) as src:
    nd = src.nodata
    prov = prov.to_crs(src.crs)
    mv = {}
    for _, r in prov.iterrows():
        try:
            out, _ = mask(src, [r.geometry.__geo_interface__], crop=True)
            a = out[0].astype("float64")
            a = a[(a != nd) & np.isfinite(a)] if nd is not None else a[np.isfinite(a)]
            mv[r["NAME_1"]] = float(a.mean()) if a.size else np.nan
        except Exception:
            mv[r["NAME_1"]] = np.nan
norm["C4_MV"] = norm["NAME_1"].map(mv)
assert norm["C4_MV"].notna().all(), norm.loc[norm.C4_MV.isna(), "NAME_1"].tolist()

# ── EWM + bounded-ideal TOPSIS (province level, identical to build_master) ─────
def ewm(Mx):
    n = Mx.shape[0]; Mp = Mx - Mx.min(0) + 1e-12
    P = Mp / Mp.sum(0, keepdims=True)
    e = np.clip(-(1/np.log(n))*(P*np.where(P > 0, np.log(P), 0)).sum(0), 0, 1)
    d = 1 - e; return d/d.sum()
def topsis(Mx, w):
    Mw = Mx*w
    return np.sqrt((Mw**2).sum(1))/(np.sqrt(((Mw-w)**2).sum(1))+np.sqrt((Mw**2).sum(1))+1e-12)

# baseline province-level PAI (recomputed the same way, for a like-for-like ref)
Xb = norm[CR].to_numpy(float)
wb = ewm(Xb); PAI_b = topsis(Xb, wb)

# MV variant: replace C4_Infra column with C4_MV
Xm = norm[["C1_Resource", "C2_Equity", "C3_Demand", "C4_MV", "C5_Physical"]].to_numpy(float)
wm = ewm(Xm); PAI_m = topsis(Xm, wm)
norm["PAI_MV"] = PAI_m

# ── 1. weights ────────────────────────────────────────────────────────────────
wbase = pd.read_csv(PROC / "EWM_weights.csv").set_index("criterion")["weight"]
print("=== EWM weights: baseline (published, C4=transmission) vs MV ===")
for i, c in enumerate(CR):
    lbl = "C4_MV" if c == "C4_Infra" else c
    print(f"  {lbl:12s} published={wbase[c]:.3f}   MV={wm[i]:.3f}")

# ── 2. rank agreement PAI-MV vs published PAI ─────────────────────────────────
rho_pub, p_pub = stats.spearmanr(norm["PAI_MV"], norm["PAI"])
rho_b,   _     = stats.spearmanr(PAI_b, norm["PAI"])          # sanity: prov-EWM ~ published
print(f"\nSpearman(PAI-MV, published PAI) = {rho_pub:.3f} (p = {p_pub:.2g})")
print(f"[sanity] Spearman(province-EWM baseline, published PAI) = {rho_b:.3f}")
# also confirm the criterion itself is oppositely ordered
rho_c4, p_c4 = stats.spearmanr(norm["C4_Infra"], norm["C4_MV"])
print(f"Spearman(C4 transmission, C4 MV) = {rho_c4:.3f} (p = {p_c4:.2g})  [reviewer's premise]")

# ── 3. province rank shifts ───────────────────────────────────────────────────
rk_pub = norm["PAI"].rank(ascending=False)
rk_mv  = norm["PAI_MV"].rank(ascending=False)
shift  = (rk_pub - rk_mv).abs()
print(f"\nRank shift: max = {int(shift.max())}, median = {shift.median():.1f}, "
      f"n>10 = {int((shift>10).sum())} of 77")

# ── 4. Zone-1 retention ───────────────────────────────────────────────────────
km = KMeans(n_clusters=5, random_state=42, n_init=10).fit(norm[["PAI_MV"]])
order = np.argsort([norm.loc[km.labels_ == k, "PAI_MV"].mean() for k in range(5)])[::-1]
remap = {old: new+1 for new, old in enumerate(order)}
norm["zone_MV"] = [remap[k] for k in km.labels_]
base_z1 = set(norm.loc[norm.dominant_zone == 1, "NAME_1"])
mv_z1   = set(norm.loc[norm.zone_MV == 1, "NAME_1"])
print(f"\nZone-1 baseline (n={len(base_z1)}): {sorted(base_z1)}")
print(f"Zone-1 MV       (n={len(mv_z1)}): {sorted(mv_z1)}")
print(f"Zone-1 retained: {len(base_z1 & mv_z1)}/{len(base_z1)}")

# ── 5. efficiency-equity association under MV ─────────────────────────────────
eff_cols = ["C1_Resource", "C3_Demand", "C4_MV", "C5_Physical"]
Xe = norm[eff_cols].to_numpy(float)
PAI_eff_mv = topsis(Xe, ewm(Xe))
rho_ee, p_ee = stats.spearmanr(norm["C2_Equity"], PAI_eff_mv)
print(f"\nEfficiency-equity (C2 vs efficiency-only, MV) = {rho_ee:.3f} (p = {p_ee:.2g})")
print("  [baseline published equity_vs_efficiency_only = -0.391]")

# ── save ──────────────────────────────────────────────────────────────────────
norm[["NAME_1", "PAI", "PAI_MV", "C4_Infra", "C4_MV", "dominant_zone", "zone_MV"]] \
    .to_csv(PROC / "sensitivity_pai_mv.csv", index=False, encoding="utf-8-sig")
summary = {
    "weights_mv": {("C4_MV" if c == "C4_Infra" else c): round(float(wm[i]), 4)
                   for i, c in enumerate(CR)},
    "weights_published": {c: round(float(wbase[c]), 4) for c in CR},
    "spearman_paiMV_vs_published": round(float(rho_pub), 3), "p": float(f"{p_pub:.3g}"),
    "spearman_C4trans_vs_C4mv": round(float(rho_c4), 3),
    "rank_shift_max": int(shift.max()), "rank_shift_n_gt10": int((shift > 10).sum()),
    "zone1_baseline_n": len(base_z1), "zone1_mv_n": len(mv_z1),
    "zone1_retained": len(base_z1 & mv_z1),
    "efficiency_equity_mv": round(float(rho_ee), 3), "efficiency_equity_mv_p": float(f"{p_ee:.3g}"),
    "efficiency_equity_published": -0.391,
    "c4mv_skew": round(float(norm["C4_MV"].skew()), 2),
    "c4trans_skew": round(float(norm["C4_Infra"].skew()), 2),
    "c4mv_weight": round(float(wm[CR.index("C4_Infra")]), 3),
    "zone1_mv_members": sorted(mv_z1),
}
(PROC / "sensitivity_pai_mv.json").write_text(json.dumps(summary, indent=1), encoding="utf-8")
print("\nSaved: sensitivity_pai_mv.csv + .json")
print(json.dumps(summary, indent=1))
