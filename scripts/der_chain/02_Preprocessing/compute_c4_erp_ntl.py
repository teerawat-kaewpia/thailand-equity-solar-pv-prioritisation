"""
C4: Emission Reduction Potential from VIIRS NTL (pixel-level)
==============================================================
Formula: C4_i = NTL_i  (normalized to [0,1] at 2nd-98th percentile)

Since EFEC is constant nationally (0.4682 tCO2/MWh, TGO 2022),
ERP ∝ electricity consumption ∝ NTL radiance.

High NTL pixel = high electricity use = high current emissions
             = high potential for DER to displace grid emissions (Benefit ↑)

Sources:
  - VIIRS DNB annual composite 2022 (90m, EPSG:4326)
  - TGO EFEC 2022 = 0.4682 tCO2/MWh (constant — does not affect normalization)

Reference: Ou et al. (2019) Applied Energy; Zhao et al. (2019) RSE
Output: DER/Data/14_Processed_90m/C4_ERP_proxy_NTL_90m.tif
"""

import numpy as np
import rasterio
from pathlib import Path
import os

BASE       = Path(os.environ.get("ENERGY_DATA_ROOT", r"D:\Clude Code GIS\Energy"))
NTL_TIF    = BASE / "Energy map" / "Thailand_NTL_2022_90m.tif"
REF_GRID   = BASE / "Energy map" / "Thailand_DEM_90m.tif"
OUTPUT_TIF = BASE / "DER" / "Data" / "14_Processed_90m" / "C4_ERP_proxy_NTL_90m.tif"

NODATA_OUT = -9999.0
PCTL_LO    = 2
PCTL_HI    = 98

# ── Reference grid ─────────────────────────────────────────────────────────────
print("Reading reference grid...")
with rasterio.open(REF_GRID) as ref:
    ref_transform = ref.transform
    ref_crs       = ref.crs
    ref_width     = ref.width
    ref_height    = ref.height

# ── Load NTL ───────────────────────────────────────────────────────────────────
print("Loading NTL 2022...")
with rasterio.open(NTL_TIF) as src:
    ntl = src.read(1).astype("float32")

ntl = np.where(np.isnan(ntl), 0.0, ntl)
ntl = np.where(ntl < 0, 0.0, ntl)

valid_mask = ntl > 0
print(f"  NTL range: 0 – {ntl.max():.2f} nW/cm2/sr")
print(f"  Lit pixels (NTL>0): {valid_mask.sum():,}")

# ── Normalize to [0,1] at 2nd-98th percentile ─────────────────────────────────
print("Normalizing...")
valid_vals = ntl[valid_mask]
lo = np.percentile(valid_vals, PCTL_LO)
hi = np.percentile(valid_vals, PCTL_HI)
print(f"  Normalization range: [{lo:.4f}, {hi:.4f}] nW/cm2/sr")

# Lit pixels: normalize [0,1]; dark pixels within Thailand: 0.0; outside Thailand: NODATA
c4_norm = np.where(valid_mask, np.clip((ntl - lo) / (hi - lo), 0.0, 1.0), 0.0)

# Apply GADM land mask (C2 raster as reference)
C2_TIF = BASE / "DER" / "Data" / "14_Processed_90m" / "C2_energy_poverty_90m.tif"
with rasterio.open(C2_TIF) as src:
    c2 = src.read(1).astype("float32")
    c2_nd = src.nodata if src.nodata is not None else -9999.0
land_mask = c2 != np.float32(c2_nd)

c4 = np.where(land_mask, c4_norm, NODATA_OUT)
c4 = c4.astype("float32")
print(f"  Thailand land pixels: {land_mask.sum():,} | C4 lit: {valid_mask[land_mask].sum():,}")

# ── Write output ───────────────────────────────────────────────────────────────
print(f"Writing: {OUTPUT_TIF}")
profile = {
    "driver": "GTiff", "dtype": "float32",
    "width": ref_width, "height": ref_height, "count": 1,
    "crs": ref_crs, "transform": ref_transform,
    "nodata": NODATA_OUT, "compress": "lzw",
    "tiled": True, "blockxsize": 512, "blockysize": 512,
}
with rasterio.open(OUTPUT_TIF, "w", **profile) as dst:
    dst.write(c4, 1)
    dst.update_tags(
        description="C4 Emission Reduction Potential proxy (NTL-based)",
        formula="normalize(NTL_pixel, 2nd-98th pctl)",
        ntl_source="VIIRS DNB annual composite 2022",
        EFEC_note="constant nationally (0.4682 tCO2/MWh, TGO 2022) — absorbed in normalization",
        normalization=f"2nd-98th pctl: [{lo:.4f}, {hi:.4f}] nW/cm2/sr",
        created="2026-07-07",
    )

print("\nDone.")
print(f"  Output: {OUTPUT_TIF}")
print(f"  Valid pixels: {(c4 != NODATA_OUT).sum():,}")
