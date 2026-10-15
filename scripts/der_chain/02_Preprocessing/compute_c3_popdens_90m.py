"""
C3: Population Density — resampled to 90m reference grid
==========================================================
Source : WorldPop 2020 UN-adjusted 100m (persons/pixel)
Formula: C3_i = normalize(pop_density_i, 2nd-98th pctl)  [0,1]
         High density → many people benefit from DER → Benefit ↑
Output : DER/Data/14_Processed_90m/C3_popdens_90m.tif
"""

import numpy as np
import rasterio
from rasterio.warp import reproject, Resampling
from pathlib import Path
import os

BASE       = Path(os.environ.get("ENERGY_DATA_ROOT", r"D:\Clude Code GIS\Energy"))
WORLDPOP   = BASE / "DER" / "Data" / "05_Population" / "worldpop_THA_2020_100m.tif"
REF_GRID   = BASE / "Energy map" / "Thailand_DEM_90m.tif"
OUTPUT_TIF = BASE / "DER" / "Data" / "14_Processed_90m" / "C3_popdens_90m.tif"

NODATA_OUT = -9999.0
PCTL_LO    = 2
PCTL_HI    = 98

print("Reading reference grid...")
with rasterio.open(REF_GRID) as ref:
    ref_transform = ref.transform
    ref_crs       = ref.crs
    ref_width     = ref.width
    ref_height    = ref.height
print(f"  Grid: {ref_width}x{ref_height}")

print("Resampling WorldPop 100m → 90m (bilinear)...")
with rasterio.open(WORLDPOP) as src:
    wp_nodata = src.nodata if src.nodata is not None else -99999.0
    print(f"  WorldPop nodata: {wp_nodata}")

pop_90m = np.zeros((ref_height, ref_width), dtype="float32")
with rasterio.open(WORLDPOP) as src:
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

# Clamp negatives (artefacts from bilinear near nodata boundaries)
pop_90m = np.where(pop_90m < 0, 0.0, pop_90m)
land_mask = pop_90m > 0
print(f"  Populated pixels: {land_mask.sum():,} | max: {pop_90m.max():.1f} persons/pixel")

print("Normalizing to [0,1]...")
vals = pop_90m[land_mask]
lo = np.percentile(vals, PCTL_LO)
hi = np.percentile(vals, PCTL_HI)
print(f"  Normalization range [{PCTL_LO}–{PCTL_HI}th pctl]: {lo:.4f} – {hi:.4f} persons/pixel")

c3 = np.where(land_mask, np.clip((pop_90m - lo) / (hi - lo), 0.0, 1.0), NODATA_OUT)
c3 = c3.astype("float32")

print(f"Writing: {OUTPUT_TIF}")
profile = {
    "driver": "GTiff", "dtype": "float32",
    "width": ref_width, "height": ref_height, "count": 1,
    "crs": ref_crs, "transform": ref_transform,
    "nodata": NODATA_OUT, "compress": "lzw",
    "tiled": True, "blockxsize": 512, "blockysize": 512,
}
with rasterio.open(OUTPUT_TIF, "w", **profile) as dst:
    dst.write(c3, 1)
    dst.update_tags(
        description="C3 Population Density, normalized",
        source="WorldPop 2020 100m UN-adjusted",
        formula="normalize(pop_density, 2nd-98th pctl)",
        normalization=f"2nd-98th pctl: [{lo:.4f}, {hi:.4f}] persons/pixel",
        resampling="bilinear",
        created="2026-07-07",
    )

print("\nDone.")
print(f"  Output: {OUTPUT_TIF}")
print(f"  Valid pixels: {(c3 != NODATA_OUT).sum():,}")
print(f"  C3 range: {c3[c3 != NODATA_OUT].min():.4f} – {c3[c3 != NODATA_OUT].max():.4f}")
