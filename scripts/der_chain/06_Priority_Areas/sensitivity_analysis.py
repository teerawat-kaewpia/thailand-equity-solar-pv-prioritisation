"""
Sensitivity analysis: EWM weights vs alternative weighting schemes
====================================================================
Final model S2 (C1–C5): compares PAI rankings under 3 weighting scenarios:
  EWM:    Entropy Weight Method (data-driven, our model)
  Equal:  Equal weights (1/5 each = 0.200)
  Expert: Expert-adjusted — boost social need (C2) and solar (C1),
          reduce pop density (C3); reflects DER equity-first literature

Metrics: Spearman rank correlation between province rankings,
         provinces shifting >5 ranks, PAI difference maps.
"""

import numpy as np
import pandas as pd
import rasterio
from scipy.stats import spearmanr
from pathlib import Path
import os
import fiona
import geopandas as gpd
from rasterstats import zonal_stats
import warnings
warnings.filterwarnings("ignore")

BASE     = Path(os.environ.get("ENERGY_DATA_ROOT", r"D:\Clude Code GIS\Energy"))
PROC     = BASE / "DER" / "Data" / "14_Processed_90m"
GADM     = BASE / "DER" / "Data" / "01_Admin_Boundaries" / "gadm41_THA.gpkg"
NODATA   = -9999.0

CRIT_NAMES = ["C1_Solar", "C2_Poverty", "C3_PopDens", "C4_GridDist", "C5_LandSuit"]
CRIT_FILES = {
    "C1_Solar":    PROC / "C1_PVOUT_90m.tif",
    "C2_Poverty":  PROC / "C2_poverty_90m.tif",
    "C3_PopDens":  PROC / "C3_popdens_90m.tif",
    "C4_GridDist": PROC / "C5_grid_dist_90m.tif",       # distance-based; source file = C5
    "C5_LandSuit": PROC / "C6_land_suitability_90m.tif", # source file = C6
}

# EWM weights from final S2 pipeline
W_EWM   = np.array([0.247, 0.191, 0.126, 0.189, 0.247])  # poverty-C2 rerun weights
# Equal weights (1/5 each)
W_EQUAL = np.ones(5) / 5
# Expert-adjusted: boost C1 (solar) and C2 (poverty); reduce C3 (pop density)
# Rationale: DER equity-first framing — solar resource + social need drive site selection
W_EXPERT = np.array([0.28, 0.30, 0.10, 0.20, 0.12])
W_EXPERT = W_EXPERT / W_EXPERT.sum()   # renormalize to sum=1

SCENARIOS = {
    "EWM":    W_EWM,
    "Equal":  W_EQUAL,
    "Expert": W_EXPERT,
}
print("Weight scenarios:")
for name, w in SCENARIOS.items():
    print(f"  {name}: " + " | ".join(f"{c}={v:.3f}" for c,v in zip(CRIT_NAMES, w)))

# ── Load criteria arrays ───────────────────────────────────────────────────────
print("\nLoading criteria...")
arrays = {}
nodata_vals = {}
for name, path in CRIT_FILES.items():
    with rasterio.open(path) as src:
        arr = src.read(1).astype("float32")
        nd  = np.float32(src.nodata if src.nodata is not None else -9999.0)
    arrays[name] = arr
    nodata_vals[name] = nd
# A5: C2 raster is raw percent; scale it explicitly for pixel-level TOPSIS
from _c2_scale import scale_c2_pixels
arrays["C2_Poverty"] = scale_c2_pixels(arrays["C2_Poverty"], nodata_vals["C2_Poverty"], PROC)

# Land mask
land_mask = np.ones(arrays["C1_Solar"].shape, dtype=bool)
for name, arr in arrays.items():
    land_mask &= (arr != nodata_vals[name])
n_pix = land_mask.sum()
print(f"  Land pixels: {n_pix:,}")

X = np.zeros((n_pix, 5), dtype="float32")
for j, name in enumerate(CRIT_NAMES):
    X[:, j] = arrays[name][land_mask]

# ── TOPSIS function ────────────────────────────────────────────────────────────
def run_topsis(X, w):
    Xw = X * w[np.newaxis, :]
    Ap = w.copy()          # theoretical max: criterion at 1.0 → weighted = w
    An = np.zeros(len(w))  # theoretical min: criterion at 0.0
    Dp = np.sqrt(((Xw - Ap) ** 2).sum(axis=1))
    Dn = np.sqrt(((Xw - An) ** 2).sum(axis=1))
    return (Dn / (Dp + Dn + 1e-12)).astype("float32")

# ── Run all scenarios ──────────────────────────────────────────────────────────
print("\nRunning TOPSIS for each scenario...")
PAI_results = {}
ref_grid_info = {}
with rasterio.open(CRIT_FILES["C1_Solar"]) as src:
    ref_grid_info = {"transform": src.transform, "crs": src.crs,
                     "width": src.width, "height": src.height}

for scenario, w in SCENARIOS.items():
    pai = run_topsis(X, w)
    PAI_results[scenario] = pai
    print(f"  {scenario}: PAI range [{pai.min():.4f}, {pai.max():.4f}] | mean={pai.mean():.4f}")

# ── Province-level comparison ──────────────────────────────────────────────────
print("\nComputing province-level PAI for each scenario...")
layers = fiona.listlayers(str(GADM))
adm1   = next((l for l in layers if l.endswith("_1")), layers[1])
prov   = gpd.read_file(str(GADM), layer=adm1)
prov   = prov[["GID_1", "NAME_1", "geometry"]].copy()
if prov.crs.to_epsg() != 4326:
    prov = prov.to_crs("EPSG:4326")

results = {"GID_1": prov["GID_1"], "NAME_1": prov["NAME_1"]}

for scenario, pai_vals in PAI_results.items():
    pai_grid = np.full(land_mask.shape, NODATA, dtype="float32")
    pai_grid[land_mask] = pai_vals
    tfm = ref_grid_info["transform"]
    stats = zonal_stats(prov, pai_grid, affine=tfm, stats=["mean"], nodata=NODATA)
    results[f"PAI_{scenario}"] = [s["mean"] if s["mean"] is not None else np.nan for s in stats]

df = pd.DataFrame(results)

# ── Spearman rank correlations ─────────────────────────────────────────────────
print("\n=== Spearman rank correlations between scenarios ===")
pairs = [("EWM","Equal"), ("EWM","Expert"), ("Equal","Expert")]
for a, b in pairs:
    rho, p = spearmanr(df[f"PAI_{a}"], df[f"PAI_{b}"])
    print(f"  {a} vs {b}: ρ = {rho:.4f}  (p={p:.4f})")

# ── Rank change analysis ───────────────────────────────────────────────────────
df["rank_EWM"] = df["PAI_EWM"].rank(ascending=False).astype(int)
for scenario in ["Equal", "Expert"]:
    df[f"rank_{scenario}"] = df[f"PAI_{scenario}"].rank(ascending=False).astype(int)
    df[f"rank_diff_{scenario}"] = (df[f"rank_{scenario}"] - df["rank_EWM"]).abs()
    large_shift = (df[f"rank_diff_{scenario}"] > 5).sum()
    print(f"\n  Provinces shifting >5 ranks (EWM vs {scenario}): {large_shift}")
    top_shifts = df.nlargest(5, f"rank_diff_{scenario}")[
        ["NAME_1", "rank_EWM", f"rank_{scenario}", f"rank_diff_{scenario}"]
    ]
    print(top_shifts.to_string(index=False))

# Save
out = PROC / "sensitivity_analysis.csv"
df.to_csv(out, index=False, encoding="utf-8-sig")
print(f"\nSaved: {out}")

# ── Save S2 equal-weight PAI raster ───────────────────────────────────────────
pai_eq_grid = np.full(land_mask.shape, NODATA, dtype="float32")
pai_eq_grid[land_mask] = PAI_results["Equal"]
eq_out = PROC / "PAI_equal_weights_90m.tif"
profile = {
    "driver": "GTiff", "dtype": "float32",
    "width": ref_grid_info["width"], "height": ref_grid_info["height"], "count": 1,
    "crs": ref_grid_info["crs"], "transform": ref_grid_info["transform"],
    "nodata": NODATA, "compress": "lzw",
    "tiled": True, "blockxsize": 512, "blockysize": 512,
}
with rasterio.open(eq_out, "w", **profile) as dst:
    dst.write(pai_eq_grid, 1)
    dst.update_tags(description="PAI equal weights sensitivity test (C1-C5, 0.2 each)")
print(f"Equal-weight raster saved: {eq_out}")
