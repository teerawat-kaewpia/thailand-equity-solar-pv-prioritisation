# -*- coding: utf-8 -*-
"""
Rasterize the VALID province equity criterion (NESDC poverty incidence) to the
90 m reference grid, replacing the NTL-based C2.

Amendment A5 (2026-10-10): the raster carries the RAW provincial poverty incidence (%),
with no clip and no scaling. The 2nd-98th percentile clip and the linear [0,1] scaling are
applied once, to the province means, in compute_pai_province_level.py (as for C1, C3, C4, C5).
Before A5 this script clipped and scaled C2 here as well, so C2 was clipped twice.
Pixel-level TOPSIS scripts scale C2 explicitly through 06_Priority_Areas/_c2_scale.py.

Input : C2_poverty_province.csv (77 provinces) + GADM ADM1 + DEM ref grid
Output: DER/Data/14_Processed_90m/C2_poverty_90m.tif   (float32, poverty %, unscaled)
"""
import numpy as np
import pandas as pd
import geopandas as gpd
import rasterio
from rasterio.features import rasterize
from pathlib import Path
import os
import fiona

BASE   = Path(os.environ.get("ENERGY_DATA_ROOT", r"D:\Clude Code GIS\Energy"))
PROC   = BASE / "DER" / "Data" / "14_Processed_90m"
GADM   = BASE / "DER" / "Data" / "01_Admin_Boundaries" / "gadm41_THA.gpkg"
REF    = BASE / "Energy map" / "Thailand_DEM_90m.tif"
POVCSV = PROC / "C2_poverty_province.csv"
OUT    = PROC / "C2_poverty_90m.tif"
NODATA = -9999.0

# ── reference grid ─────────────────────────────────────────────────────────────
with rasterio.open(REF) as ref:
    tr, crs, W, H = ref.transform, ref.crs, ref.width, ref.height
print(f"Ref grid: {W}x{H}, {crs}")

# ── province poverty, raw percent (A5: no clip, no scaling here) ──────────────
import hashlib
pov = pd.read_csv(POVCSV)
v = pov["poverty_pct"].to_numpy(float)
assert len(pov) == 77 and np.isfinite(v).all() and (v >= 0).all() and (v <= 100).all()
pov["C2"] = v
YEARS = pov["year_used"].value_counts().sort_index().to_dict()
FALLBACK = pov.loc[pov["year_used"] != 2565, ["NAME_1", "year_used"]].values.tolist()
print(f"poverty_pct [{v.min():.2f}, {v.max():.2f}] kept as raw percent; years used {YEARS}")

# ── join to geometry ───────────────────────────────────────────────────────────
adm1 = next(l for l in fiona.listlayers(str(GADM)) if l.endswith("_1"))
g = gpd.read_file(str(GADM), layer=adm1)[["NAME_1", "geometry"]]
if g.crs != crs:
    g = g.to_crs(crs)
g = g.merge(pov[["NAME_1", "C2"]], on="NAME_1", how="left")
print(f"Joined {g['C2'].notna().sum()}/77 provinces")

# ── rasterize ──────────────────────────────────────────────────────────────────
shapes = ((geom, val) for geom, val in zip(g.geometry, g["C2"])
          if geom is not None and not pd.isna(val))
c2 = rasterize(shapes, out_shape=(H, W), transform=tr, fill=NODATA,
               dtype="float32", all_touched=False)

profile = {"driver": "GTiff", "dtype": "float32", "width": W, "height": H,
           "count": 1, "crs": crs, "transform": tr, "nodata": NODATA,
           "compress": "lzw", "tiled": True, "blockxsize": 512, "blockysize": 512}
with rasterio.open(OUT, "w", **profile) as dst:
    dst.write(c2, 1)
    dst.update_tags(
        description="C2 Equity: provincial poverty incidence (NESDC), raw percent",
        unit="percent of population below the poverty line",
        scaling="none",
        scaled_in="compute_pai_province_level.py (province means, 2nd-98th pct clip, once); pixel TOPSIS via 06_Priority_Areas/_c2_scale.py",
        year_primary="2565",
        years_used=str({int(k): int(n) for k, n in YEARS.items()}),
        year_fallback=str([[a, int(b)] for a, b in FALLBACK]),
        input_table=POVCSV.name,
        input_sha256=hashlib.sha256(POVCSV.read_bytes()).hexdigest(),
        amendment="A5 2026-10-10: raw values, previously clipped and scaled here",
        source="NESDC Poverty & Income Distribution 2567, Table 1.5 (NSO SES)",
        replaces="C2_energy_poverty_90m.tif (inverted NTL/capita)",
    )
print(f"\nDone. Valid pixels: {(c2 != NODATA).sum():,}")
print(f"Saved: {OUT}")
