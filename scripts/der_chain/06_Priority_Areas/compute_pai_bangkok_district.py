"""
DER Priority Area Index — Bangkok 50-khet DISTRICT scale (EWM + TOPSIS + K-means)
=================================================================================
District-scale twin of compute_pai_topsis.py. Unit = khet (50), not pixel.
Answers RQ4 (scale-consistency of the equity finding) for the SCS demonstration.

Pipeline (mirrors province logic, at district granularity):
  0  district-mean of each criterion raster over the 50 khet (GADM ADM2)
  1  linear [0,1] normalisation across the 50 districts (2nd-98th pct clip)
     - C2 Equity uses INVERTED NTL/capita (low light per capita = high poverty)
  2  EWM weights from the 50x5 normalised matrix
  3  TOPSIS -> district PAI (theoretical A+ = w, A- = 0, same as province run)
  4  K-means (k=5) -> priority zones
  5  Queen-contiguity Global Moran's I on district PAI (if libpysal/esda present)
  6  Pearson/Spearman of each criterion vs PAI

INTRA-CITY CRITERION ADAPTATION (RQ4 finding):
  Solar PVOUT is near-uniform within one city (Bangkok spread ~1424-1522
  kWh/kWp/yr = ~7%), so re-normalising it to [0,1] across 50 khet manufactures
  a dominant EWM weight (0.42) from a 7% physical gradient and inverts the
  index (agricultural fringe > urban core). Fix: the Resource and Physical
  slots MERGE at intra-city scale into a single "Rooftop Solar Yield" =
  PVOUT x building-footprint density (sun x how much roof exists). This yields
  a 4-criterion district model.

Criteria (all benefit, higher = higher DER priority):
  C1 RooftopYield PVOUT x building density        (merged Resource x Physical)
  C2 Equity       C2_bangkok_district.csv         (inverted NTL/capita, recomputed)
  C3 Demand       C3_popdens_90m.tif              (population)
  C4 Infra        C5_grid_dist_90m.tif            (exp-decay grid accessibility)
  (component layers C1_PVOUT and C5 building density are kept for transparency)

Output: DER/Data/14_Processed_Bangkok/
  bangkok_district_PAI.csv        (per-khet criteria, PAI, rank, zone)
  bangkok_EWM_weights.csv
  bangkok_criterion_correlations.csv
"""

import numpy as np
import pandas as pd
import geopandas as gpd
import rasterio
from rasterstats import zonal_stats
from sklearn.cluster import KMeans
from scipy import stats
from pathlib import Path
import os
import fiona

BASE   = Path(os.environ.get("ENERGY_DATA_ROOT", r"D:\Clude Code GIS\Energy"))
PROC   = BASE / "DER" / "Data" / "14_Processed_90m"
BKKDIR = BASE / "DER" / "Data" / "14_Processed_Bangkok"
GADM   = BASE / "DER" / "Data" / "01_Admin_Boundaries" / "gadm41_THA.gpkg"
BLD    = BASE / "Energy map" / "DER_Bangkok_Buildings"
C2_CSV = BKKDIR / "C2_bangkok_district.csv"

N_ZONES = 5
BKKDIR.mkdir(parents=True, exist_ok=True)

# raster layers read by district-mean zonal stats (C2 comes from CSV).
# C1_PVOUT and C5_density are COMPONENTS -> merged into C1_RooftopYield below.
RASTER_CRIT = {
    "C1_PVOUT":    PROC / "C1_PVOUT_90m.tif",
    "C3_Demand":   PROC / "C3_popdens_90m.tif",
    "C4_Infra":    PROC / "C5_grid_dist_90m.tif",
    "C5_density":  BLD  / "GoogleOB_v3_density_30m_Bangkok.tif",
}
# 4-criterion intra-city model (Resource x Physical merged into RooftopYield)
CRIT_ORDER = ["C1_RooftopYield", "C2_Equity", "C3_Demand", "C4_Infra"]

# ── Load 50 khet ───────────────────────────────────────────────────────────────
print("Loading Bangkok 50 khet (GADM ADM2)...")
adm2 = next(l for l in fiona.listlayers(str(GADM)) if l.endswith("_2"))
khet = gpd.read_file(str(GADM), layer=adm2)
khet = khet[khet["NAME_1"] == "Bangkok Metropolis"][["NAME_2", "geometry"]].copy()
khet = khet.to_crs("EPSG:4326").reset_index(drop=True)
print(f"  {len(khet)} districts")

# ── Stage 0: district-mean of each raster criterion ───────────────────────────
print("\nStage 0 — district-mean zonal stats...")
for cname, rpath in RASTER_CRIT.items():
    with rasterio.open(rpath) as src:
        nod = src.nodata
    zs = zonal_stats(khet, str(rpath), stats=["mean"], nodata=nod)
    khet[cname] = [s["mean"] for s in zs]
    print(f"  {cname:12s} from {rpath.name}: "
          f"[{khet[cname].min():.4f}, {khet[cname].max():.4f}]")

# ── C1 Rooftop Solar Yield = PVOUT x building density (merged slot) ────────────
# Sun is near-uniform within the city; roof area is what varies. Their product
# = deployable rooftop solar potential per district.
khet["C1_RooftopYield"] = khet["C1_PVOUT"] * khet["C5_density"]
print(f"C1_RooftopYield (PVOUT x density): "
      f"[{khet['C1_RooftopYield'].min():.4f}, {khet['C1_RooftopYield'].max():.4f}]")

# ── C2 Equity from recomputed district NTL/capita (inverted) ──────────────────
print("Merging C2 (inverted NTL/capita)...")
c2 = pd.read_csv(C2_CSV)[["NAME_2", "ntl_per_capita"]]
khet = khet.merge(c2, on="NAME_2", how="left")
# energy poverty = inverse of light per capita; store raw signal, normalise below
khet["C2_Equity"] = -khet["ntl_per_capita"]        # higher = poorer (benefit)
print(f"  C2 raw signal (-NTL/cap): [{khet['C2_Equity'].min():.4f}, {khet['C2_Equity'].max():.4f}]")

# ── Stage 1: linear [0,1] normalisation across districts (2nd-98th pct clip) ───
print("\nStage 1 — [0,1] normalisation (benefit, per framework)...")
Xn = np.zeros((len(khet), len(CRIT_ORDER)), dtype="float64")
for j, c in enumerate(CRIT_ORDER):
    v = khet[c].astype("float64").values
    lo, hi = np.nanpercentile(v, 2), np.nanpercentile(v, 98)
    if hi <= lo:
        lo, hi = np.nanmin(v), np.nanmax(v)
    vn = np.clip((v - lo) / (hi - lo + 1e-12), 0.0, 1.0)
    Xn[:, j] = vn
    khet[c + "_norm"] = vn
    print(f"  {c:12s} normalised  mean={vn.mean():.3f}  CV={100*vn.std()/vn.mean():.1f}%")

# ── Stage 2: Entropy Weight Method ────────────────────────────────────────────
print("\nStage 2 — EWM weights...")
n = Xn.shape[0]
Xp = Xn - Xn.min(axis=0) + 1e-6
P = Xp / Xp.sum(axis=0, keepdims=True)
with np.errstate(divide="ignore", invalid="ignore"):
    lnP = np.where(P > 0, np.log(P), 0.0)
e = np.clip(-(1.0 / np.log(n)) * (P * lnP).sum(axis=0), 0.0, 1.0)
d = 1.0 - e
w = d / d.sum()
wdf = pd.DataFrame({"criterion": CRIT_ORDER, "entropy": e, "divergence": d, "weight": w})
print(wdf.to_string(index=False))
wdf.to_csv(BKKDIR / "bangkok_EWM_weights.csv", index=False)

# ── Stage 3: TOPSIS ────────────────────────────────────────────────────────────
print("\nStage 3 — TOPSIS...")
Xw = Xn * w[np.newaxis, :]
A_pos = w.copy()               # theoretical ideal (each criterion at 1.0)
A_neg = np.zeros(len(w))       # theoretical nadir
D_pos = np.sqrt(((Xw - A_pos) ** 2).sum(axis=1))
D_neg = np.sqrt(((Xw - A_neg) ** 2).sum(axis=1))
PAI = D_neg / (D_pos + D_neg + 1e-12)
khet["PAI"] = PAI
khet["rank"] = pd.Series(PAI).rank(ascending=False).astype(int)
print(f"  PAI range: {PAI.min():.4f} - {PAI.max():.4f} | mean {PAI.mean():.4f}")

# ── Stage 4: K-means zones ─────────────────────────────────────────────────────
print(f"\nStage 4 — K-means (k={N_ZONES})...")
km = KMeans(n_clusters=N_ZONES, random_state=42, n_init=10)
lab = km.fit_predict(PAI.reshape(-1, 1))
zmeans = [PAI[lab == z].mean() for z in range(N_ZONES)]
remap = {orig: r + 1 for r, orig in enumerate(np.argsort(zmeans)[::-1])}
khet["zone"] = [remap[z] for z in lab]
for z in range(1, N_ZONES + 1):
    m = khet["zone"] == z
    print(f"  Zone {z}: n={m.sum():2d}  PAI mean={PAI[m.values].mean():.4f}")

# ── Stage 5: Global Moran's I (queen contiguity) ──────────────────────────────
print("\nStage 5 — Global Moran's I on district PAI...")
try:
    from libpysal.weights import Queen
    from esda.moran import Moran
    W = Queen.from_dataframe(khet, use_index=False)
    W.transform = "r"
    mi = Moran(khet["PAI"].values, W, permutations=999)
    print(f"  Moran's I = {mi.I:.4f}  (p = {mi.p_sim:.4f}, z = {mi.z_sim:.3f}, 999 perms)")
    moran_line = f"{mi.I:.4f},{mi.p_sim:.4f},{mi.z_sim:.3f}"
except Exception as ex:
    print(f"  [skipped — libpysal/esda unavailable: {ex}]")
    moran_line = "NA,NA,NA"

# ── Stage 6: criterion vs PAI correlations ────────────────────────────────────
print("\nStage 6 — criterion correlations vs PAI...")
corr_rows = []
for c in CRIT_ORDER:
    r_p, p_p = stats.pearsonr(khet[c + "_norm"], khet["PAI"])
    r_s, p_s = stats.spearmanr(khet[c + "_norm"], khet["PAI"])
    corr_rows.append({"criterion": c, "pearson_r": r_p, "pearson_p": p_p,
                      "spearman_rho": r_s, "spearman_p": p_s,
                      "EWM_weight": w[CRIT_ORDER.index(c)]})
    print(f"  {c:12s} Pearson r={r_p:+.3f} (p={p_p:.3f})  "
          f"Spearman rho={r_s:+.3f} (p={p_s:.3f})  w={w[CRIT_ORDER.index(c)]:.3f}")
cdf = pd.DataFrame(corr_rows)
cdf.to_csv(BKKDIR / "bangkok_criterion_correlations.csv", index=False)

# ── Save per-district table ────────────────────────────────────────────────────
cols = (["NAME_2"] + CRIT_ORDER + [c + "_norm" for c in CRIT_ORDER]
        + ["C1_PVOUT", "C5_density", "ntl_per_capita", "PAI", "rank", "zone"])
out = khet[cols].sort_values("rank").reset_index(drop=True)
out.to_csv(BKKDIR / "bangkok_district_PAI.csv", index=False, encoding="utf-8-sig")

print("\n=== Top 8 khet by PAI ===")
print(out.head(8)[["NAME_2", "PAI", "rank", "zone", "C1_RooftopYield_norm", "C2_Equity_norm"]].to_string(index=False))
print("\n=== Bottom 5 khet ===")
print(out.tail(5)[["NAME_2", "PAI", "rank", "zone"]].to_string(index=False))

# ── Key RQ4 check: does equity stay high-weight / low-correlation at district? ─
c2w = w[CRIT_ORDER.index("C2_Equity")]
c2r = cdf.loc[cdf.criterion == "C2_Equity", "spearman_rho"].values[0]
print(f"\n=== RQ4 scale-consistency check ===")
print(f"  C2 Equity: EWM weight = {c2w:.3f} (rank {int(pd.Series(w).rank(ascending=False)[CRIT_ORDER.index('C2_Equity')])}/5), "
      f"Spearman vs PAI = {c2r:+.3f}")
print(f"  Province pattern was: high weight (0.223, 2nd) + weak corr (rho=0.322).")
print(f"  District reproduces it? weight-high & corr-weak -> {'YES' if c2w>0.18 and abs(c2r)<0.55 else 'CHECK'}")

print(f"\nDone. Outputs -> {BKKDIR}")
