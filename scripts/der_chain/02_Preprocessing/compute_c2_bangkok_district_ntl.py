"""
C2 Energy Poverty at DISTRICT scale — Bangkok's 50 khet
========================================================
District-scale twin of compute_c2_energy_poverty_ntl.py.

WHY THIS EXISTS
  The province-level C2 raster (C2_energy_poverty_90m.tif) stores ONE value
  per province, rasterised uniformly across every pixel. So all 50 Bangkok
  khet share the single Bangkok-province value (0.3662) -> district CV = 0.0%,
  useless for a within-Bangkok analysis (feasibility probe confirmed this).

  Fix: recompute NTL-per-capita PER DISTRICT from the same raw rasters, using
  the BANGKOK-metro mean as the reference (a within-city relative energy-poverty
  measure, analogous to the province run's use of the national mean).

  No GEE needed: VIIRS native ~500 m, and the local NTL raster is already 90 m
  (upsampled), so a finer re-download would add no real information. The
  smallest khet (~1.8 km^2) still holds ~213 pixels at 90 m -> enough for a
  stable zonal mean.

FORMULA (per district d)
  NTL_per_capita_d = sum(NTL px in d) / sum(WorldPop px in d)
  C2_d = clip(1 - NTL_per_capita_d / bangkok_mean, 0, 1)
  Low NTL/capita -> high C2 -> high energy poverty -> high DER priority (Benefit)

Sources: VIIRS DNB annual composite 2022 (90 m) + WorldPop 2020 100 m + GADM 4.1 ADM2
Output: DER/Data/14_Processed_Bangkok/C2_bangkok_district.csv
"""

import numpy as np
import pandas as pd
import geopandas as gpd
import rasterio
from rasterio.warp import reproject, Resampling
from rasterstats import zonal_stats
from pathlib import Path
import os
import fiona

BASE       = Path(os.environ.get("ENERGY_DATA_ROOT", r"D:\Clude Code GIS\Energy"))
NTL_TIF    = BASE / "Energy map" / "Thailand_NTL_2022_90m.tif"
WORLDPOP   = BASE / "DER" / "Data" / "05_Population" / "worldpop_THA_2020_100m.tif"
GADM_GPKG  = BASE / "DER" / "Data" / "01_Admin_Boundaries" / "gadm41_THA.gpkg"
REF_GRID   = BASE / "Energy map" / "Thailand_DEM_90m.tif"
OUT_DIR    = BASE / "DER" / "Data" / "14_Processed_Bangkok"
OUT_CSV    = OUT_DIR / "C2_bangkok_district.csv"

OUT_DIR.mkdir(parents=True, exist_ok=True)

# ── Reference grid (90 m) ──────────────────────────────────────────────────────
print("Reading reference grid...")
with rasterio.open(REF_GRID) as ref:
    ref_transform = ref.transform
    ref_crs       = ref.crs
    ref_width     = ref.width
    ref_height    = ref.height
print(f"  Grid: {ref_width}x{ref_height}, CRS={ref_crs}")

# ── Load NTL (already on 90 m reference grid) ──────────────────────────────────
print("Loading NTL 2022...")
with rasterio.open(NTL_TIF) as src:
    ntl = src.read(1).astype("float32")
    ntl = np.where(np.isnan(ntl), 0.0, ntl)
    ntl = np.where(ntl < 0, 0.0, ntl)
print(f"  NTL range: 0 - {ntl.max():.2f} nW/cm2/sr")

# ── Resample WorldPop to 90 m reference grid ───────────────────────────────────
print("Resampling WorldPop to 90 m...")
pop_90m = np.zeros((ref_height, ref_width), dtype="float32")
with rasterio.open(WORLDPOP) as src:
    wp_nodata = src.nodata if src.nodata is not None else -9999
    reproject(
        source=rasterio.band(src, 1),
        destination=pop_90m,
        src_transform=src.transform,
        src_crs=src.crs,
        dst_transform=ref_transform,
        dst_crs=ref_crs,
        resampling=Resampling.bilinear,
        src_nodata=wp_nodata,
        dst_nodata=0.0,
    )
pop_90m = np.where(pop_90m < 0, 0.0, pop_90m)

# ── Load Bangkok's 50 districts (GADM ADM2) ────────────────────────────────────
print("Loading GADM ADM2 (Bangkok khet)...")
layers = fiona.listlayers(str(GADM_GPKG))
adm2_layer = next(l for l in layers if l.endswith("_2"))
khet = gpd.read_file(str(GADM_GPKG), layer=adm2_layer)
khet = khet[khet["NAME_1"] == "Bangkok Metropolis"][["NAME_2", "geometry"]].copy()
if khet.crs != ref_crs:
    khet = khet.to_crs(ref_crs)
print(f"  Districts: {len(khet)}")

# ── Zonal stats: NTL sum + population sum per district ─────────────────────────
print("Computing zonal stats (NTL + population per khet)...")
ntl_stats = zonal_stats(khet, ntl, affine=ref_transform,
                        stats=["sum"], nodata=0.0, all_touched=False)
pop_stats = zonal_stats(khet, pop_90m, affine=ref_transform,
                        stats=["sum"], nodata=0.0, all_touched=False)

khet["ntl_sum"] = [s["sum"] or 0.0 for s in ntl_stats]
khet["pop_sum"] = [s["sum"] or 0.0 for s in pop_stats]
khet["ntl_per_capita"] = np.where(
    khet["pop_sum"] > 0, khet["ntl_sum"] / khet["pop_sum"], 0.0)

# ── Reference = Bangkok-metro mean (within-city relative poverty) ──────────────
bkk_ntl  = khet["ntl_sum"].sum()
bkk_pop  = khet["pop_sum"].sum()
bkk_mean = bkk_ntl / bkk_pop if bkk_pop > 0 else 1.0
print(f"  Bangkok NTL sum : {bkk_ntl:.2f}")
print(f"  Bangkok pop     : {bkk_pop:,.0f}")
print(f"  Bangkok NTL/cap : {bkk_mean:.6f}")
print(f"  District NTL/cap range: {khet['ntl_per_capita'].min():.6f} - {khet['ntl_per_capita'].max():.6f}")

khet["C2"] = np.clip(1.0 - khet["ntl_per_capita"] / bkk_mean, 0.0, 1.0)

# ── Discrimination check (the whole point) ─────────────────────────────────────
def cv(x):
    x = np.asarray(x, float); x = x[np.isfinite(x)]
    return 100 * x.std() / x.mean() if x.mean() else float("nan")

print("\n=== District discrimination (target: >> province raster's 0.0%) ===")
print(f"  NTL_per_capita  CV = {cv(khet['ntl_per_capita']):.1f}%")
print(f"  C2 (clipped)    CV = {cv(khet['C2']):.1f}%  "
      f"[range {khet['C2'].min():.4f} - {khet['C2'].max():.4f}]")

print("\n--- 5 most energy-poor khet (highest C2) ---")
print(khet.nlargest(5, "C2")[["NAME_2", "ntl_per_capita", "C2"]].to_string(index=False))
print("--- 5 least energy-poor khet (lowest C2) ---")
print(khet.nsmallest(5, "C2")[["NAME_2", "ntl_per_capita", "C2"]].to_string(index=False))

# ── Write district CSV ─────────────────────────────────────────────────────────
out = khet.drop(columns="geometry").copy()
out.to_csv(OUT_CSV, index=False, encoding="utf-8-sig")
print(f"\nDone. Wrote {len(out)} districts -> {OUT_CSV}")
