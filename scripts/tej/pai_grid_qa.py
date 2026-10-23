"""QA record for the PAI analysis grid: the count of cells valid in the PAI raster.

The manuscript reads the PAI-grid cell count from this file, never as a typed
literal. Reads DER rasters read-only and writes Data\\qa\\pai_grid_qa.json.
"""
import sys, json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from _paths import SRC, out_path
from _lineage import sha256
import numpy as np, rasterio

PROC = SRC / "Data" / "14_Processed_90m"
out = {}
for name in ("PAI_90m.tif", "DER_zones_90m.tif"):
    with rasterio.open(PROC / name) as r:
        n = 0
        for _, w in r.block_windows(1):
            a = r.read(1, window=w).astype("float64")
            n += int(((r.read_masks(1, window=w) > 0) & np.isfinite(a)).sum())
        out[name] = {"valid_cells": n, "crs": r.crs.to_string(), "res_deg": list(r.res),
                     "shape": list(r.shape), "sha256": sha256(PROC / name)}
assert out["PAI_90m.tif"]["valid_cells"] == out["DER_zones_90m.tif"]["valid_cells"]
qa = {"pai_grid_valid_cells": out["PAI_90m.tif"]["valid_cells"], "crs": out["PAI_90m.tif"]["crs"],
      "definition": "cells of the EPSG:4326 0.000833 deg grid valid in PAI_90m.tif (all criteria present)",
      "rasters": out}
json.dump(qa, open(out_path("Data", "qa", "pai_grid_qa.json"), "w"), indent=1)
print(json.dumps({k: qa[k] for k in ("pai_grid_valid_cells", "crs")}))
