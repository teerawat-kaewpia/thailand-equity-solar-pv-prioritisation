"""
C5 v2: Grid Accessibility — distance-based (OSM power lines)
=============================================================
Replaces GridFinder LV direct-value approach (93.6% zeros → EWM weight inflation).

Formula: C5_dist_i = exp(-dist_km_i / D_REF)
  dist_km_i = Euclidean distance (km) from pixel i to nearest OSM power line
  D_REF     = 5.0 km reference decay distance (5 km ≈ half-score)

Result: smooth continuous [0,1] surface over all Thailand land pixels.
  On/near grid (dist=0):  C5 = 1.000
  5 km away:              C5 = 0.368
  10 km away:             C5 = 0.135
  25 km away:             C5 = 0.007

Sources: OSM Overpass API power_lines.geojson + power_cables.geojson (downloaded 2026-06-22)
Output : DER/Data/14_Processed_90m/C5_grid_dist_90m.tif
"""

import numpy as np
import pandas as pd
import geopandas as gpd
import rasterio
from rasterio.features import rasterize
import scipy.ndimage as ndi
from pathlib import Path
import os

BASE     = Path(os.environ.get("ENERGY_DATA_ROOT", r"D:\Clude Code GIS\Energy"))
OSM_DIR  = BASE / "Energy map" / "GridNetwork_OSM"
REF_GRID = BASE / "Energy map" / "Thailand_DEM_90m.tif"
C2_TIF   = BASE / "DER" / "Data" / "14_Processed_90m" / "C2_energy_poverty_90m.tif"
OUT_TIF  = BASE / "DER" / "Data" / "14_Processed_90m" / "C5_grid_dist_90m.tif"

D_REF    = 5.0     # km — exponential decay reference distance
PX_KM    = 0.09    # 90m pixel → 0.09 km
NODATA   = -9999.0

# ── Reference grid ─────────────────────────────────────────────────────────────
print("Reading reference grid...")
with rasterio.open(REF_GRID) as ref:
    tfm        = ref.transform
    crs        = ref.crs
    width      = ref.width
    height     = ref.height
print(f"  {width}x{height}  CRS={crs}")

# ── GADM land mask (from C2) ───────────────────────────────────────────────────
with rasterio.open(C2_TIF) as src:
    c2 = src.read(1).astype("float32")
    c2_nd = np.float32(src.nodata if src.nodata else -9999)
land_mask = c2 != c2_nd
print(f"  Land pixels: {land_mask.sum():,}")

# ── Load OSM power lines + cables ─────────────────────────────────────────────
print("Loading OSM power infrastructure...")
lines  = gpd.read_file(OSM_DIR / "power_lines.geojson")
cables = gpd.read_file(OSM_DIR / "power_cables.geojson")
grid   = gpd.GeoDataFrame(
    pd.concat([lines, cables], ignore_index=True),
    crs=lines.crs
)
grid = grid[grid.geometry.notna() & ~grid.geometry.is_empty]
print(f"  Total features: {len(grid):,}  (lines={len(lines)}, cables={len(cables)})")

# ── Rasterize lines → binary presence grid ────────────────────────────────────
print("Rasterizing power lines to 90m grid (all_touched=True)...")
shapes = [(geom.__geo_interface__, 1) for geom in grid.geometry]
lines_mask = rasterize(
    shapes,
    out_shape=(height, width),
    transform=tfm,
    fill=0,
    dtype="uint8",
    all_touched=True,
)
print(f"  Grid pixels with power line: {lines_mask.sum():,}")

# ── Euclidean distance transform ───────────────────────────────────────────────
print("Computing Euclidean distance transform (this may take ~30s)...")
# distance_transform_edt: for each background (0=no-line) pixel,
#   compute distance to nearest foreground (1=line) pixel
dist_px  = ndi.distance_transform_edt(1 - lines_mask)
dist_km  = dist_px * PX_KM
print(f"  Distance range: 0.0 – {dist_km[land_mask].max():.1f} km")
print(f"  Pixels within 1km of grid: {(dist_km[land_mask] < 1.0).sum():,} ({(dist_km[land_mask] < 1.0).mean()*100:.1f}%)")
print(f"  Pixels within 5km of grid: {(dist_km[land_mask] < 5.0).sum():,} ({(dist_km[land_mask] < 5.0).mean()*100:.1f}%)")
print(f"  Pixels >20km from grid:    {(dist_km[land_mask] > 20.0).sum():,} ({(dist_km[land_mask] > 20.0).mean()*100:.1f}%)")

# ── Exponential decay → C5 ────────────────────────────────────────────────────
print(f"Applying exponential decay (D_ref={D_REF} km)...")
c5_dist = np.exp(-dist_km / D_REF).astype("float32")
# Apply land mask
c5_out = np.where(land_mask, c5_dist, NODATA)
c5_out = c5_out.astype("float32")

valid = c5_out[land_mask]
print(f"  C5_dist range: {valid.min():.4f} – {valid.max():.4f}")
print(f"  C5_dist mean:  {valid.mean():.4f}")
print(f"  Zeros (C5<0.001): {(valid < 0.001).sum():,} ({(valid < 0.001).mean()*100:.1f}%) ← vs 93.6% in GridFinder version")

# EWM entropy preview
from numpy import histogram, log
def ewm_entropy(x, n_bins=1000):
    counts, _ = histogram(x[x >= 0], bins=n_bins)
    p = counts / counts.sum()
    p = p[p > 0]
    return -np.sum(p * log(p)) / log(n_bins)
e = ewm_entropy(valid)
div = 1 - e
print(f"\n  EWM entropy preview: {e:.6f}  (GridFinder was 0.094)")
print(f"  EWM divergence:      {div:.6f}  (lower = less weight inflation)")

# ── Write ──────────────────────────────────────────────────────────────────────
print(f"\nWriting: {OUT_TIF}")
profile = {
    "driver": "GTiff", "dtype": "float32",
    "width": width, "height": height, "count": 1,
    "crs": crs, "transform": tfm,
    "nodata": NODATA, "compress": "lzw",
    "tiled": True, "blockxsize": 512, "blockysize": 512,
}
with rasterio.open(OUT_TIF, "w", **profile) as dst:
    dst.write(c5_out, 1)
    dst.update_tags(
        description="C5 Grid Accessibility (distance-based, exp decay)",
        formula=f"exp(-dist_km / {D_REF})",
        source="OSM power_lines + power_cables (2026-06-22)",
        d_ref_km=str(D_REF),
        created="2026-07-07",
    )

print("Done.")
print(f"  Valid pixels: {(c5_out != NODATA).sum():,}")
