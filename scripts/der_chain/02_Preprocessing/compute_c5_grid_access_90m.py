"""
C5: Grid Accessibility — GridFinder LV raster → 90m reference grid
====================================================================
Source : GridFinder (Arderne et al. 2020) LV grid model for Thailand
         gridfinder_lv_thailand.tif  (ESRI:54009 World Mollweide)
         Values: continuous [0,1] — higher = greater LV grid density/accessibility
         nodata: 0.0

Formula: C5_i = normalize(gridfinder_lv_i, 2nd-98th pctl of non-zero pixels)
         High C5 → near/on LV grid → lower connection cost → Benefit ↑

Reference: Arderne C. et al. (2020). Predictive mapping of the global power system.
           Scientific Data, 7(1), 19. https://doi.org/10.1038/s41597-019-0347-4

Output : DER/Data/14_Processed_90m/C5_grid_access_90m.tif
"""

import numpy as np
import rasterio
from rasterio.warp import reproject, Resampling
from pathlib import Path
import os

BASE       = Path(os.environ.get("ENERGY_DATA_ROOT", r"D:\Clude Code GIS\Energy"))
GF_TIF     = BASE / "Energy map" / "GridFinder_Thailand" / "gridfinder_lv_thailand.tif"
REF_GRID   = BASE / "Energy map" / "Thailand_DEM_90m.tif"
OUTPUT_TIF = BASE / "DER" / "Data" / "14_Processed_90m" / "C5_grid_access_90m.tif"

NODATA_OUT = -9999.0
PCTL_HI    = 98   # normalize by 98th pctl of non-zero values; 0 (no grid) → C5=0

print("Reading reference grid...")
with rasterio.open(REF_GRID) as ref:
    ref_transform = ref.transform
    ref_crs       = ref.crs
    ref_width     = ref.width
    ref_height    = ref.height
print(f"  Grid: {ref_width}x{ref_height} | CRS: {ref_crs}")

print("Loading GridFinder LV...")
with rasterio.open(GF_TIF) as src:
    gf_crs = src.crs
    gf_nd  = src.nodata    # 0.0
    print(f"  Source CRS: {gf_crs} | nodata: {gf_nd}")
    print(f"  Source shape: {src.width}x{src.height}")
    raw = src.read(1).astype("float32")

nz_mask = (raw > 0) & ~np.isnan(raw)
print(f"  Non-zero pixels: {nz_mask.sum():,} | range: {raw[nz_mask].min():.4f} – {raw[nz_mask].max():.4f}")

print("Reprojecting + resampling → EPSG:4326 90m (bilinear)...")
gf_90m = np.zeros((ref_height, ref_width), dtype="float32")
with rasterio.open(GF_TIF) as src:
    reproject(
        source=rasterio.band(src, 1),
        destination=gf_90m,
        src_transform=src.transform,
        src_crs=src.crs,
        dst_transform=ref_transform,
        dst_crs=ref_crs,
        resampling=Resampling.bilinear,
        src_nodata=float(gf_nd),
        dst_nodata=0.0,
    )

gf_90m = np.where(gf_90m < 0, 0.0, gf_90m)
grid_mask = gf_90m > 0
print(f"  Grid-accessible pixels: {grid_mask.sum():,} | max: {gf_90m.max():.4f}")

# Land mask from C2 raster (rasterized from GADM province polygons = clean Thailand boundary)
C2_TIF = BASE / "DER" / "Data" / "14_Processed_90m" / "C2_energy_poverty_90m.tif"
with rasterio.open(C2_TIF) as src:
    c2 = src.read(1).astype("float32")
    c2_nd = src.nodata if src.nodata is not None else -9999.0
land_mask = c2 != np.float32(c2_nd)
print(f"  Total land pixels (GADM mask): {land_mask.sum():,}")

print("Normalizing to [0,1]...")
# hi = 98th pctl of grid-present pixels; 0 (no-grid) naturally maps to 0
vals_nz = gf_90m[grid_mask]
hi = np.percentile(vals_nz, PCTL_HI)
print(f"  Normalization hi ({PCTL_HI}th pctl of grid pixels): {hi:.6f}")

# All land pixels: clip(gf / hi, 0, 1) — no-grid areas → 0.0
c5 = np.where(land_mask, np.clip(gf_90m / hi, 0.0, 1.0), NODATA_OUT)
c5 = c5.astype("float32")

print(f"Writing: {OUTPUT_TIF}")
profile = {
    "driver": "GTiff", "dtype": "float32",
    "width": ref_width, "height": ref_height, "count": 1,
    "crs": ref_crs, "transform": ref_transform,
    "nodata": NODATA_OUT, "compress": "lzw",
    "tiled": True, "blockxsize": 512, "blockysize": 512,
}
with rasterio.open(OUTPUT_TIF, "w", **profile) as dst:
    dst.write(c5, 1)
    dst.update_tags(
        description="C5 Grid Accessibility (GridFinder LV), normalized",
        source="GridFinder Arderne et al. 2020 — LV grid model",
        source_crs="ESRI:54009 (World Mollweide)",
        formula="normalize(gridfinder_lv, 2nd-98th pctl of non-zero)",
        normalization=f"clip(gf/hi_98th, 0, 1); hi={hi:.6f}; no-grid → 0",
        resampling="bilinear with reprojection",
        created="2026-07-07",
    )

print("\nDone.")
print(f"  Output: {OUTPUT_TIF}")
print(f"  Valid pixels: {(c5 != NODATA_OUT).sum():,}")
print(f"  C5 range: {c5[c5 != NODATA_OUT].min():.4f} – {c5[c5 != NODATA_OUT].max():.4f}")
