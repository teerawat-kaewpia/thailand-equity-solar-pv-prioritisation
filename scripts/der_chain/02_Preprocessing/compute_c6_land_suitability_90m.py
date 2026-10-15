"""
C6: Land Suitability for DER — Hansen forest + slope composite
===============================================================
Formula: C6_i = forest_score_i × slope_score_i
  forest_score = max(0, 1 - treecover2000 / 50)   — penalizes dense forest (>50% = score 0)
  slope_score  = max(0, 1 - slope_deg / 20)        — penalizes steep terrain (>20° = score 0)

High C6 → open, flat land → most suitable for ground-mount solar/wind DER (Benefit ↑)
Note: Urban areas (GHSL ANBH > 0) are set to C6 = 1.0 (rooftop DER eligible regardless of
      slope/forest) to avoid penalizing dense urban pixels.

Sources:
  - Hansen GFC v1.11 treecover2000 (90m, EPSG:4326, already at ref grid)
  - Copernicus DEM slope (90m, EPSG:4326, already at ref grid)
  - GHSL ANBH building height (90m, EPSG:4326, already at ref grid)

Output : DER/Data/14_Processed_90m/C6_land_suitability_90m.tif
"""

import numpy as np
import rasterio
from pathlib import Path
import os

BASE        = Path(os.environ.get("ENERGY_DATA_ROOT", r"D:\Clude Code GIS\Energy"))
FOREST_TIF  = BASE / "Energy map" / "Thailand_forest_treecover2000_90m.tif"
SLOPE_TIF   = BASE / "Energy map" / "Thailand_slope_90m.tif"
GHSL_TIF    = BASE / "Energy map" / "Thailand_building_height_GHSL_ANBH_90m.tif"
REF_GRID    = BASE / "Energy map" / "Thailand_DEM_90m.tif"
OUTPUT_TIF  = BASE / "DER" / "Data" / "14_Processed_90m" / "C6_land_suitability_90m.tif"

NODATA_OUT    = -9999.0
FOREST_THRESH = 50.0   # % treecover above which land is fully unsuitable
SLOPE_THRESH  = 20.0   # degrees above which land is fully unsuitable

print("Reading reference grid...")
with rasterio.open(REF_GRID) as ref:
    ref_transform = ref.transform
    ref_crs       = ref.crs
    ref_width     = ref.width
    ref_height    = ref.height
    ref_nd        = ref.nodata
print(f"  Grid: {ref_width}x{ref_height}")

# Build land mask from DEM (non-nodata pixels = land)
print("Building land mask from C2 (GADM province raster)...")
C2_TIF = BASE / "DER" / "Data" / "14_Processed_90m" / "C2_energy_poverty_90m.tif"
with rasterio.open(C2_TIF) as src:
    c2 = src.read(1).astype("float32")
    c2_nd = src.nodata if src.nodata is not None else -9999.0
land_mask = c2 != np.float32(c2_nd)
print(f"  Land pixels (GADM mask): {land_mask.sum():,}")

print("Loading Hansen treecover 2000...")
with rasterio.open(FOREST_TIF) as src:
    forest = src.read(1).astype("float32")
forest = np.where(np.isnan(forest), 0.0, forest)
forest = np.clip(forest, 0.0, 100.0)
print(f"  Forest treecover range: {forest[land_mask].min():.0f} – {forest[land_mask].max():.0f} %")

print("Loading slope...")
with rasterio.open(SLOPE_TIF) as src:
    slope = src.read(1).astype("float32")
slope = np.where(np.isnan(slope), 0.0, slope)
slope = np.where(slope < 0, 0.0, slope)
print(f"  Slope range: {slope[land_mask].min():.1f} – {slope[land_mask].max():.1f} deg")

print("Loading GHSL building height (urban override)...")
with rasterio.open(GHSL_TIF) as src:
    ghsl = src.read(1).astype("float32")
    ghsl_nd = src.nodata if src.nodata is not None else -9999.0
ghsl = np.where(ghsl == ghsl_nd, 0.0, ghsl)
ghsl = np.where(ghsl < 0, 0.0, ghsl)
urban_mask = ghsl > 0
print(f"  Urban pixels (GHSL>0): {urban_mask.sum():,}")

print("Computing C6...")
forest_score = np.clip(1.0 - forest / FOREST_THRESH, 0.0, 1.0)
slope_score  = np.clip(1.0 - slope  / SLOPE_THRESH,  0.0, 1.0)

c6 = forest_score * slope_score

# Urban override: rooftop DER — set suitability to 1.0
c6 = np.where(urban_mask & land_mask, 1.0, c6)

# Apply land mask
c6 = np.where(land_mask, c6, NODATA_OUT)
c6 = c6.astype("float32")

valid = c6[land_mask]
print(f"  C6 range: {valid.min():.4f} – {valid.max():.4f}")
print(f"  Fully suitable (C6=1.0): {(c6 == 1.0).sum():,} px")
print(f"  Fully unsuitable (C6=0): {(c6[land_mask] == 0.0).sum():,} px")

print(f"Writing: {OUTPUT_TIF}")
profile = {
    "driver": "GTiff", "dtype": "float32",
    "width": ref_width, "height": ref_height, "count": 1,
    "crs": ref_crs, "transform": ref_transform,
    "nodata": NODATA_OUT, "compress": "lzw",
    "tiled": True, "blockxsize": 512, "blockysize": 512,
}
with rasterio.open(OUTPUT_TIF, "w", **profile) as dst:
    dst.write(c6, 1)
    dst.update_tags(
        description="C6 Land Suitability for DER (composite)",
        formula="forest_score × slope_score; urban pixels → 1.0",
        forest_source="Hansen GFC v1.11 treecover2000 (90m)",
        forest_threshold=f">={FOREST_THRESH}% treecover = unsuitable",
        slope_source="Copernicus DEM GLO-30 slope (90m)",
        slope_threshold=f">={SLOPE_THRESH}deg = unsuitable",
        urban_override="GHSL ANBH>0 → C6=1.0 (rooftop DER)",
        created="2026-07-07",
    )

print("\nDone.")
print(f"  Output: {OUTPUT_TIF}")
print(f"  Valid pixels: {(c6 != NODATA_OUT).sum():,}")
