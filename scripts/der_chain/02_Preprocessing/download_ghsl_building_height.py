# -*- coding: utf-8 -*-
"""
Download GHSL Building Height (GHS-BUILT-H ANBH, E2018, R2023A) for Thailand.
Source: JRC open FTP -- no authentication required.
Resolution: 3 arc-sec (90m), EPSG:4326 -- exact match for existing DEM grid.

ANBH = Average Net Building Height (mean height measured over building footprint
       pixels only, not averaged over the whole cell). More representative of
       actual building height than AGBH (which dilutes height over non-building areas).

6 tiles cover Thailand (R7-R9, C28-C29):
  Grid origin: left=-180, top=89.1, tile size=10deg x 10deg
  Tile coverage: 90-110E, -0.9 to 29.1N  (contains Thailand 97-106E, 5-21N)

Outputs (Energy map\):
  Thailand_building_height_GHSL_ANBH_90m.tif  -- clipped, aligned to DEM grid
"""

import io, zipfile, os, re
from pathlib import Path

import requests
import numpy as np
import rasterio
from rasterio.merge import merge
from rasterio.warp import reproject, Resampling
from rasterio.transform import from_bounds

DATA_DIR  = Path(r"D:\Clude Code GIS\Energy\Energy map")
CACHE_DIR = DATA_DIR / "_ghsl_tile_cache"
DEM_PATH  = DATA_DIR / "Thailand_DEM_90m.tif"
OUT_PATH  = DATA_DIR / "Thailand_building_height_GHSL_ANBH_90m.tif"

BASE_URL  = (
    "https://jeodpp.jrc.ec.europa.eu/ftp/jrc-opendata/GHSL/"
    "GHS_BUILT_H_GLOBE_R2023A/"
    "GHS_BUILT_H_ANBH_E2018_GLOBE_R2023A_4326_3ss/V1-0/tiles/"
)

TILES = [
    "GHS_BUILT_H_ANBH_E2018_GLOBE_R2023A_4326_3ss_V1_0_R7_C28.zip",
    "GHS_BUILT_H_ANBH_E2018_GLOBE_R2023A_4326_3ss_V1_0_R7_C29.zip",
    "GHS_BUILT_H_ANBH_E2018_GLOBE_R2023A_4326_3ss_V1_0_R8_C28.zip",
    "GHS_BUILT_H_ANBH_E2018_GLOBE_R2023A_4326_3ss_V1_0_R8_C29.zip",
    "GHS_BUILT_H_ANBH_E2018_GLOBE_R2023A_4326_3ss_V1_0_R9_C28.zip",
    "GHS_BUILT_H_ANBH_E2018_GLOBE_R2023A_4326_3ss_V1_0_R9_C29.zip",
]

NODATA = -200.0   # GHSL uses -200 for nodata in some versions; rasterio will expose it


def download_tile(zip_name, cache_dir):
    """Download zip, extract .tif, return path to cached .tif."""
    tif_name = zip_name.replace(".zip", ".tif")
    tif_path = cache_dir / tif_name
    if tif_path.exists():
        print(f"  [cache] {tif_name}")
        return tif_path

    url = BASE_URL + zip_name
    print(f"  Downloading {zip_name} ...", end="", flush=True)
    resp = requests.get(url, timeout=300, stream=True)
    resp.raise_for_status()
    raw = b"".join(resp.iter_content(chunk_size=1 << 20))
    print(f" {len(raw)/1e6:.1f} MB")

    with zipfile.ZipFile(io.BytesIO(raw)) as zf:
        names = [n for n in zf.namelist() if n.endswith(".tif")]
        if not names:
            raise RuntimeError(f"No .tif found in {zip_name}: {zf.namelist()}")
        tif_bytes = zf.read(names[0])

    tif_path.write_bytes(tif_bytes)
    return tif_path


def main():
    CACHE_DIR.mkdir(exist_ok=True)

    print("=== Step 1: Download 6 GHSL tiles ===")
    tile_paths = [download_tile(z, CACHE_DIR) for z in TILES]

    print("\n=== Step 2: Mosaic tiles ===")
    datasets = [rasterio.open(p) for p in tile_paths]
    mosaic_arr, mosaic_transform = merge(datasets, method="first")
    mosaic_crs = datasets[0].crs
    src_nodata = datasets[0].nodata
    for ds in datasets:
        ds.close()

    print(f"  Mosaic shape: {mosaic_arr.shape}  nodata={src_nodata}")

    print("\n=== Step 3: Align to DEM reference grid ===")
    with rasterio.open(DEM_PATH) as dem:
        ref_profile = dem.profile.copy()
        ref_h = dem.height
        ref_w = dem.width
        ref_transform = dem.transform
        ref_crs = dem.crs

    dst_arr = np.full((ref_h, ref_w), fill_value=-9999.0, dtype=np.float32)

    # Write mosaic to temp in-memory file for reproject source
    mem_profile = {
        "driver": "GTiff",
        "dtype": "float32",
        "width": mosaic_arr.shape[2],
        "height": mosaic_arr.shape[1],
        "count": 1,
        "crs": mosaic_crs,
        "transform": mosaic_transform,
        "nodata": src_nodata,
    }

    import tempfile
    with tempfile.NamedTemporaryFile(suffix=".tif", delete=False) as tmp:
        tmp_path = tmp.name
    try:
        with rasterio.open(tmp_path, "w", **mem_profile) as tmp_ds:
            tmp_ds.write(mosaic_arr[0].astype(np.float32), 1)

        with rasterio.open(tmp_path) as src:
            reproject(
                source=rasterio.band(src, 1),
                destination=dst_arr,
                src_transform=mosaic_transform,
                src_crs=mosaic_crs,
                dst_transform=ref_transform,
                dst_crs=ref_crs,
                resampling=Resampling.bilinear,
                src_nodata=src_nodata,
                dst_nodata=-9999.0,
            )
    finally:
        os.unlink(tmp_path)

    # Replace any remaining negative GHSL nodatas with 0 for clean output
    # (GHSL can use -200 as a secondary nodata; values <0 are not valid heights)
    valid = dst_arr != -9999.0
    dst_arr[valid & (dst_arr < 0)] = 0.0

    n_valid = valid.sum()
    n_nonzero = (valid & (dst_arr > 0)).sum()
    print(f"  Valid pixels: {n_valid:,}  with building height>0: {n_nonzero:,}")
    print(f"  Height stats: mean={dst_arr[valid & (dst_arr>0)].mean():.1f}m  "
          f"max={dst_arr[valid].max():.1f}m")

    print(f"\n=== Step 4: Save output ===")
    out_profile = ref_profile.copy()
    out_profile.update(
        dtype="float32",
        count=1,
        nodata=-9999.0,
        compress="lzw",
        predictor=2,
    )
    with rasterio.open(OUT_PATH, "w", **out_profile) as dst:
        dst.write(dst_arr, 1)
        dst.update_tags(
            source="JRC GHSL GHS-BUILT-H ANBH E2018 R2023A v1.0",
            description="Average Net Building Height (m) at 90m, clipped to Thailand, aligned to Copernicus DEM grid",
            year_reference="2018",
            tiles_used=", ".join(TILES),
            tree_cover_mask="none (pure GHSL, no Hansen mask applied)",
        )

    size_mb = OUT_PATH.stat().st_size / 1e6
    print(f"  Saved: {OUT_PATH.name}  ({size_mb:.1f} MB)")
    print("\nDone. Thailand_building_height_GHSL_ANBH_90m.tif ready for use.")
    print("  - Layer reference year: 2018")
    print("  - No vegetation mask needed (GHSL ANBH is already building-footprint-only)")
    print("  - Cross-validate against Google Open Buildings 2.5D (primary layer)")


if __name__ == "__main__":
    main()
