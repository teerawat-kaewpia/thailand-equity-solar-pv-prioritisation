# -*- coding: utf-8 -*-
"""
Province-level EWM-TOPSIS PAI  (n = 77 provinces)  — CORRECTED PIPELINE
=======================================================================
Replaces the pixel-level EWM, which was numerically invalid: at n = 60.5M
pixels the Shannon entropy saturates (e -> 1) and a float32 accumulation over
60.5M terms produced a spurious weight vector. Two corrections:

  (1) EWM is computed at the UNIT OF ANALYSIS (77 provinces) in float64.
      All inferential statistics in the paper are province-level, so the
      weights must be derived from the same 77 x 5 matrix.
  (2) C3 (population density) is log-transformed before normalisation.
      Its province distribution is strongly right-skewed (skew = +2.51);
      on raw values a single outlier (Bangkok) dominates the entropy weight
      (w rises to 0.411 and C3 becomes the top criterion purely from skew).

Pipeline: province means -> log1p(C3) -> linear [0,1] with 2nd-98th pct clip
          -> EWM (float64) -> TOPSIS (theoretical ideal A+ = w, A- = 0)
          -> K-means (k = 5) zones.

Outputs (schema-compatible with the previous pixel pipeline so the figure and
table scripts keep working):
  province_PAI_summary.csv   EWM_weights.csv   province_criteria_normalised.csv
"""
import numpy as np
import pandas as pd
import geopandas as gpd
import fiona
import rasterio
from rasterstats import zonal_stats
from sklearn.cluster import KMeans
from scipy import stats
from pathlib import Path
import os
import warnings
warnings.filterwarnings("ignore")

BASE = Path(os.environ.get("ENERGY_DATA_ROOT", r"D:\Clude Code GIS\Energy"))  # raw data (Tier-2), override via env
PROC = BASE / "DER" / "Data" / "14_Processed_90m"
GADM = BASE / "DER" / "Data" / "01_Admin_Boundaries" / "gadm41_THA.gpkg"
N_ZONES = 5

# model criteria (paper labels) -> raster actually used
LAYERS = {
    "C1_Resource": "C1_PVOUT_90m.tif",          # solar PVOUT
    "C2_Equity":   "C2_poverty_90m.tif",        # NESDC poverty incidence
    "C3_Demand":   "C3_popdens_90m.tif",        # population density  (log-transformed)
    "C4_Infra":    "C5_grid_dist_90m.tif",      # grid accessibility exp(-d/5km)
    "C5_Physical": "C6_land_suitability_90m.tif",
}
NAMES = list(LAYERS)
LOG_CRIT = "C3_Demand"

# ── province means ─────────────────────────────────────────────────────────────
adm1 = next(l for l in fiona.listlayers(str(GADM)) if l.endswith("_1"))
prov = gpd.read_file(str(GADM), layer=adm1)[["GID_1", "NAME_1", "geometry"]].to_crs("EPSG:4326")
print(f"Provinces: {len(prov)}")

raw = {}
for k, f in LAYERS.items():
    with rasterio.open(PROC / f) as s:
        nod = s.nodata
    raw[k] = np.array([z["mean"] for z in
                       zonal_stats(prov, str(PROC / f), stats=["mean"], nodata=nod)], float)
    print(f"  {k:12s} province means [{raw[k].min():.4f}, {raw[k].max():.4f}]")

# ── (2) de-skew the demand criterion ──────────────────────────────────────────
sk_before = stats.skew(raw[LOG_CRIT])
raw_model = dict(raw)
raw_model[LOG_CRIT] = np.log1p(raw[LOG_CRIT] * 100.0)
sk_after = stats.skew(raw_model[LOG_CRIT])
print(f"\n{LOG_CRIT}: skew {sk_before:+.2f} -> {sk_after:+.2f} after log1p(100x)")

# ── normalisation: linear [0,1], 2nd-98th percentile clip (framework §2.3) ────
# ── A5 scaling guard: each criterion is clipped and scaled to [0,1] once, at province level ──
with rasterio.open(PROC / LAYERS["C2_Equity"]) as _s:
    _t2 = _s.tags()
assert _t2.get("scaling") == "none", "C2 raster must hold raw poverty percent, unscaled (A5)"
_pov = pd.read_csv(PROC / "C2_poverty_province.csv").set_index("NAME_1")["poverty_pct"]
assert np.allclose(raw["C2_Equity"], _pov.loc[prov["NAME_1"]].to_numpy(float), atol=1e-4), \
    "C2 province means must equal the raw poverty table (no pre-scaling)"
_PIX = {}
for _k in ("C1_Resource", "C3_Demand"):
    with rasterio.open(PROC / LAYERS[_k]) as _s:
        _t = _s.tags()
    assert "2nd-98th" in _t.get("formula", "") and "2nd-98th" in _t.get("normalization", ""), \
        f"{_k}: the documented pixel-level preprocessing tag is missing"
    assert 0.0 <= np.nanmin(raw[_k]) and np.nanmax(raw[_k]) <= 1.0, f"{_k}: pixel-scaled means outside [0,1]"
    _PIX[_k] = {"formula": _t["formula"], "normalization": _t["normalization"]}
for _k in ("C4_Infra", "C5_Physical"):
    assert 0.0 <= np.nanmin(raw[_k]) and np.nanmax(raw[_k]) <= 1.0, f"{_k}: formula score outside [0,1]"
_NORM_DONE = []


def norm01(v):
    lo, hi = np.nanpercentile(v, 2), np.nanpercentile(v, 98)
    _NORM_DONE.append((NAMES[len(_NORM_DONE)], (float(lo), float(hi))))
    return np.clip((v - lo) / (hi - lo + 1e-12), 0.0, 1.0)

X = np.column_stack([norm01(raw_model[k]) for k in NAMES]).astype(np.float64)
assert len(_NORM_DONE) == len(NAMES) == 5, "each criterion must be scaled exactly once at province level"
import json as _json
(PROC / "criterion_scaling.json").write_text(_json.dumps({
    "amendment": "A5 2026-10-10",
    "pixel_level": {"C1_Resource": _PIX["C1_Resource"], "C3_Demand": _PIX["C3_Demand"],
                    "C2_Equity": "none (raw percent, province-constant raster)",
                    "C4_Infra": "formula score exp(-d/5 km) in [0,1]", "C5_Physical": "formula score in [0,1]"},
    "province_level": {k: {"transform": ("log1p(100x), then " if k == LOG_CRIT else "") + "2nd-98th pct clip, linear [0,1]",
                           "times": 1, "lo": lo_hi[0], "hi": lo_hi[1]} for k, lo_hi in _NORM_DONE},
}, indent=1), encoding="utf-8")

# ── EWM (float64) ─────────────────────────────────────────────────────────────
n = X.shape[0]
Xp = X - X.min(axis=0) + 1e-12                  # strictly positive; 0·ln0 := 0
P = Xp / Xp.sum(axis=0, keepdims=True)
lnP = np.where(P > 0, np.log(P), 0.0)
e = np.clip(-(1.0 / np.log(n)) * (P * lnP).sum(axis=0), 0.0, 1.0)
d = 1.0 - e
w = d / d.sum()
print("\n=== EWM weights (province level, n=77, float64) ===")
for k, ei, wi in zip(NAMES, e, w):
    print(f"  {k:12s} entropy={ei:.4f}  weight={wi:.4f}")
print(f"  SUM = {w.sum():.6f}")
pd.DataFrame({"criterion": NAMES, "entropy": e, "weight": w}).to_csv(
    PROC / "EWM_weights.csv", index=False)

# ── TOPSIS (theoretical ideal A+ = w, A- = 0) ─────────────────────────────────
Xw = X * w
d_pos = np.sqrt(((Xw - w) ** 2).sum(axis=1))
d_neg = np.sqrt((Xw ** 2).sum(axis=1))
PAI = d_neg / (d_pos + d_neg + 1e-12)
print(f"\nPAI: [{PAI.min():.4f}, {PAI.max():.4f}] mean={PAI.mean():.4f} median={np.median(PAI):.4f}")

# ── K-means zones (k=5) on province PAI ───────────────────────────────────────
lab = KMeans(n_clusters=N_ZONES, random_state=42, n_init=10).fit_predict(PAI.reshape(-1, 1))
zmean = [PAI[lab == z].mean() for z in range(N_ZONES)]
remap = {o: r + 1 for r, o in enumerate(np.argsort(zmean)[::-1])}
zone = np.array([remap[z] for z in lab], int)

out = prov.drop(columns="geometry").copy()
out["PAI"] = PAI.round(4)
# schema-compatible criterion columns (C1..C6); C4 slot keeps the dropped-ERP
# placeholder so downstream scripts that expect 6 columns still work.
out["C1"] = raw["C1_Resource"].round(4)
out["C2"] = raw["C2_Equity"].round(4)
out["C3"] = raw["C3_Demand"].round(4)
out["C4"] = np.nan                       # C4_ERP candidate dropped at screening
out["C5"] = raw["C4_Infra"].round(4)     # paper C4 Infrastructure
out["C6"] = raw["C5_Physical"].round(4)  # paper C5 Physical
for z in range(1, N_ZONES + 1):
    out[f"zone{z}_pct"] = np.where(zone == z, 100.0, 0.0)
out["dominant_zone"] = zone
out = out.sort_values("PAI", ascending=False).reset_index(drop=True)
out["rank"] = out.index + 1
out.to_csv(PROC / "province_PAI_summary.csv", index=False, encoding="utf-8-sig")

# normalised matrix (for correlation figure / audit)
norm_df = pd.DataFrame(X, columns=NAMES)
norm_df.insert(0, "NAME_1", prov["NAME_1"].values)
norm_df["PAI"] = PAI
norm_df.to_csv(PROC / "province_criteria_normalised.csv", index=False, encoding="utf-8-sig")

print("\n=== Zones ===")
for z in range(1, N_ZONES + 1):
    m = out["dominant_zone"] == z
    print(f"  Zone {z}: n={m.sum():2d}  PAI mean={out.loc[m,'PAI'].mean():.4f}  "
          f"[{out.loc[m,'PAI'].min():.3f}-{out.loc[m,'PAI'].max():.3f}]")

print("\n=== Top 10 ===")
print(out.head(10)[["rank", "NAME_1", "PAI", "dominant_zone"]].to_string(index=False))
print("\n=== Bottom 5 ===")
print(out.tail(5)[["rank", "NAME_1", "PAI", "dominant_zone"]].to_string(index=False))

# ── criterion vs PAI + equity orthogonality/tension ───────────────────────────
print("\n=== Criterion vs PAI (Spearman) ===")
for j, k in enumerate(NAMES):
    r, p = stats.spearmanr(X[:, j], PAI)
    print(f"  {k:12s} rho={r:+.3f} (p={p:.3f})")

eff = [0, 2, 3, 4]
Xe = X[:, eff]
Pe = Xe - Xe.min(0) + 1e-12
Pp = Pe / Pe.sum(0, keepdims=True)
ee = np.clip(-(1/np.log(n)) * (Pp * np.where(Pp > 0, np.log(Pp), 0)).sum(0), 0, 1)
we = (1 - ee) / (1 - ee).sum()
Xew = Xe * we
PAI_eff = np.sqrt((Xew**2).sum(1)) / (np.sqrt(((Xew - we)**2).sum(1)) + np.sqrt((Xew**2).sum(1)) + 1e-12)
r_eff, p_eff = stats.spearmanr(X[:, 1], PAI_eff)
print(f"\n=== Equity vs EFFICIENCY-only PAI: rho={r_eff:+.3f} (p={p_eff:.4f}) ===")
for j, k in zip(eff, [NAMES[i] for i in eff]):
    r, p = stats.spearmanr(X[:, 1], X[:, j])
    print(f"  C2 vs {k:12s} rho={r:+.3f} (p={p:.3f})")

print("\nSaved: province_PAI_summary.csv, EWM_weights.csv, province_criteria_normalised.csv")
