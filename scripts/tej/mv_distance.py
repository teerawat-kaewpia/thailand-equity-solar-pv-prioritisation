"""Province mean distance to GridFinder modelled MV lines (km).

Implements SCENARIO_PROTOCOL.md Amendment A3 exactly:
  90 m grid in EPSG:32647 over the GADM 4.1 country extent; valid cell = cell
  centre inside the union of the 77 provinces (all_touched=False); MV lines
  reprojected and rasterised all_touched=True (lines outside Thailand kept);
  Euclidean distance transform x 90 m; province mean (scenario variable) and
  median (descriptive). Outputs to DER_TEJ\\Data\\mv_distance\\.
"""
import sys, json, hashlib
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from _paths import RAW, SRC, BASE, out_path
import numpy as np, pandas as pd, geopandas as gpd, rasterio
from rasterio.features import rasterize
from rasterio.transform import from_origin
from scipy import ndimage as ndi, stats
from pyproj import CRS, Transformer

MV = RAW / "Energy map" / "GridFinder_Thailand" / "gridfinder_mv_lines_thailand.gpkg"
GADM = SRC / "Data" / "01_Admin_Boundaries" / "gadm41_THA.gpkg"
EPSG, RES, ND = 32647, 90.0, -9999.0
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()

prov = gpd.read_file(GADM, layer="ADM_ADM_1")[["NAME_1", "geometry"]].to_crs(EPSG).reset_index(drop=True)
xmin, ymin, xmax, ymax = prov.total_bounds
xmin, ymin = np.floor(xmin / RES) * RES, np.floor(ymin / RES) * RES
xmax, ymax = np.ceil(xmax / RES) * RES, np.ceil(ymax / RES) * RES
W, H = int((xmax - xmin) / RES), int((ymax - ymin) / RES)
T = from_origin(xmin, ymax, RES, RES)
print(f"grid {W} x {H} = {W*H/1e6:.1f} M cells")

# province id raster (cell centre rule) -> valid mask
pid = rasterize([(g, i + 1) for i, g in enumerate(prov.geometry)], out_shape=(H, W), transform=T,
                fill=0, dtype="uint8", all_touched=False)
valid = pid > 0

mv = gpd.read_file(MV).to_crs(EPSG)
mv = mv[mv.geometry.notna() & ~mv.geometry.is_empty]
lines = rasterize([(g, 1) for g in mv.geometry], out_shape=(H, W), transform=T,
                  fill=0, dtype="uint8", all_touched=True)
print("line cells:", int(lines.sum()))
d_km = (ndi.distance_transform_edt(1 - lines) * RES / 1000.0).astype("float32")
del lines
d_km[~valid] = ND

out_dir = BASE / "Data" / "mv_distance"
with rasterio.open(out_path("Data", "mv_distance", "mv_distance_km_90m_utm47.tif"), "w", driver="GTiff",
                   height=H, width=W, count=1, dtype="float32", crs=f"EPSG:{EPSG}", transform=T,
                   nodata=ND, compress="deflate", tiled=True) as dst:
    dst.write(d_km, 1)

# province statistics
v = d_km[valid]; ids = pid[valid]
rows = []
for i, name in enumerate(prov.NAME_1):
    x = v[ids == i + 1]
    rows.append({"NAME_1": name, "mv_dist_mean_km": float(x.mean()), "mv_dist_median_km": float(np.median(x)),
                 "n_cells": int(x.size)})
tab = pd.DataFrame(rows)
tab.to_csv(out_path("Data", "mv_distance", "province_mv_distance.csv"), index=False, encoding="utf-8-sig")

# QA
inp = pd.read_csv(BASE / "Data" / "scenarios" / "province_inputs.csv")[["NAME_1", "dist_line_km"]]
m = tab.merge(inp, on="NAME_1")
from pyproj import Proj
# UTM 47N scale factor at the eastern extreme of the grid (zone-48 longitudes)
east = Transformer.from_crs(EPSG, 4326, always_xy=True).transform(xmax, (ymin + ymax) / 2)
k = Proj(CRS.from_epsg(EPSG)).get_factors(east[0], east[1]).meridional_scale
qa = {"source": str(MV), "source_sha256": sha(MV), "n_features": int(len(mv)),
      "gadm": str(GADM), "gadm_layer": "ADM_ADM_1", "crs": f"EPSG:{EPSG}", "res_m": RES,
      "grid_w_h": [W, H], "valid_cells": int(valid.sum()),
      "pct_within_1km": round(float((v <= 1).mean() * 100), 1),
      "pct_within_5km": round(float((v <= 5).mean() * 100), 1),
      "pct_within_10km": round(float((v <= 10).mean() * 100), 1),
      "max_km": round(float(v.max()), 1),
      "province_mean_km_range": [round(tab.mv_dist_mean_km.min(), 2), round(tab.mv_dist_mean_km.max(), 2)],
      "min_cells_per_province": int(tab.n_cells.min()),
      "spearman_vs_C4_line_distance": round(float(stats.spearmanr(m.mv_dist_mean_km, m.dist_line_km)[0]), 3),
      "utm47_scale_factor_at_east_edge": {"lon": round(east[0], 2), "k": round(float(k), 5)}}
json.dump(qa, open(out_path("Data", "mv_distance", "mv_distance_QA.json"), "w"), indent=1)
print(json.dumps(qa, indent=1))
