"""
C1: Solar Photovoltaic Output (PVOUT) — resampled to 90m reference grid
==========================================================================
Source : Global Solar Atlas v2 — LTAy YearlyTotals PVOUT.tif (1km, EPSG:4326)
         Valid range: ~1111–1592 kWh/kWp/year
         nodata: float32 sentinel (~1.175e-38)
Formula: C1_i = normalize(PVOUT_i, 2nd-98th pctl)  [0,1]
         High PVOUT → high solar irradiance → high DER solar potential (Benefit ↑)
Output : DER/Data/14_Processed_90m/C1_PVOUT_90m.tif
"""

import numpy as np
import rasterio
from rasterio.warp import reproject, Resampling
from pathlib import Path
import os

BASE       = Path(os.environ.get("ENERGY_DATA_ROOT", r"D:\Clude Code GIS\Energy"))
PVOUT_TIF  = (BASE / "Energy map"
              / "Thailand_GISdata_LTAym_YearlyMonthlyTotals_GlobalSolarAtlas-v2_GEOTIFF"
              / "Thailand_GISdata_LTAy_YearlyMonthlyTotals_GlobalSolarAtlas-v2_GEOTIFF"
              / "PVOUT.tif")
REF_GRID   = BASE / "Energy map" / "Thailand_DEM_90m.tif"
OUTPUT_TIF = BASE / "DER" / "Data" / "14_Processed_90m" / "C1_PVOUT_90m.tif"

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

print("Loading PVOUT...")
with rasterio.open(PVOUT_TIF) as src:
    pvout_nd = np.float32(src.nodata)
    pvout_raw = src.read(1).astype("float32")

# Mask nodata sentinel and NaN
valid_mask = (pvout_raw != pvout_nd) & ~np.isnan(pvout_raw) & (pvout_raw > 0)
pvout_clean = np.where(valid_mask, pvout_raw, np.nan)
valid_vals = pvout_raw[valid_mask]
print(f"  Source valid pixels: {valid_mask.sum():,} | range: {valid_vals.min():.1f} – {valid_vals.max():.1f} kWh/kWp/yr")

print("Resampling PVOUT → 90m reference grid (bilinear)...")
pvout_90m = np.full((ref_height, ref_width), np.nan, dtype="float32")
with rasterio.open(PVOUT_TIF) as src:
    reproject(
        source=rasterio.band(src, 1),
        destination=pvout_90m,
        src_transform=src.transform,
        src_crs=src.crs,
        dst_transform=ref_transform,
        dst_crs=ref_crs,
        resampling=Resampling.bilinear,
        src_nodata=float(pvout_nd),
        dst_nodata=np.nan,
    )

land_mask = ~np.isnan(pvout_90m) & (pvout_90m > 0)
print(f"  After resample: {land_mask.sum():,} valid pixels | range: {pvout_90m[land_mask].min():.1f} – {pvout_90m[land_mask].max():.1f}")

print("Normalizing to [0,1]...")
vals = pvout_90m[land_mask]
lo = np.percentile(vals, PCTL_LO)
hi = np.percentile(vals, PCTL_HI)
print(f"  Normalization range [{PCTL_LO}–{PCTL_HI}th pctl]: {lo:.2f} – {hi:.2f} kWh/kWp/yr")

c1 = np.where(land_mask, np.clip((pvout_90m - lo) / (hi - lo), 0.0, 1.0), NODATA_OUT)
c1 = c1.astype("float32")

print(f"Writing: {OUTPUT_TIF}")
profile = {
    "driver": "GTiff", "dtype": "float32",
    "width": ref_width, "height": ref_height, "count": 1,
    "crs": ref_crs, "transform": ref_transform,
    "nodata": NODATA_OUT, "compress": "lzw",
    "tiled": True, "blockxsize": 512, "blockysize": 512,
}
with rasterio.open(OUTPUT_TIF, "w", **profile) as dst:
    dst.write(c1, 1)
    dst.update_tags(
        description="C1 Solar PV Output (PVOUT), normalized",
        source="Global Solar Atlas v2 LTAy YearlyTotals",
        unit_source="kWh/kWp/year",
        normalization=f"2nd-98th pctl: [{lo:.2f}, {hi:.2f}] kWh/kWp/yr",
        formula="normalize(PVOUT, 2nd-98th pctl)",
        resampling="bilinear",
        created="2026-07-07",
    )

print("\nDone.")
print(f"  Output: {OUTPUT_TIF}")
print(f"  Valid pixels: {(c1 != NODATA_OUT).sum():,}")
print(f"  C1 range: {c1[c1 != NODATA_OUT].min():.4f} – {c1[c1 != NODATA_OUT].max():.4f}")
