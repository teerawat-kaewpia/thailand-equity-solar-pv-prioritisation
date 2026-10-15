# -*- coding: utf-8 -*-
"""
Zone-level validation against documented utility-scale solar installations (OSM).

Reported honestly: solar plants are sited by developers optimising for resource,
land and grid access, NOT for equity. A high hit rate for Zone 1 is therefore
evidence that the EFFICIENCY component of the PAI is realistic, not that the
equity-weighted composite predicts where DER *should* go. See Section 4.7.
"""
import json, numpy as np, pandas as pd, geopandas as gpd, fiona
from scipy import stats
from pathlib import Path
import os
import warnings; warnings.filterwarnings("ignore")

BASE = Path(os.environ.get("DER_PROJECT_ROOT", Path(__file__).resolve().parents[2]))
PROC = BASE / "Data" / "14_Processed_90m"
GADM = BASE / "Data" / "01_Admin_Boundaries" / "gadm41_THA.gpkg"

v = pd.read_csv(PROC / "validation_solar_osm.csv")
adm1 = next(l for l in fiona.listlayers(str(GADM)) if l.endswith("_1"))
g = gpd.read_file(str(GADM), layer=adm1)[["NAME_1", "geometry"]].to_crs("EPSG:32647")
g["area"] = g.geometry.area
m = v.merge(g[["NAME_1", "area"]], on="NAME_1")

tot_area, tot_obs = m["area"].sum(), m["solar_count"].sum()
rows = []
for z in sorted(m.dominant_zone.unique()):
    sub = m[m.dominant_zone == z]
    land = sub["area"].sum() / tot_area * 100
    obs = int(sub.solar_count.sum())
    rows.append({"zone": int(z), "n_provinces": int(len(sub)), "land_pct": round(land, 1),
                 "solar_obs": obs, "solar_obs_pct": round(obs / tot_obs * 100, 1),
                 "expected": round(tot_obs * land / 100, 1),
                 "enrichment": round((obs / tot_obs) / (land / 100), 3)})
D = pd.DataFrame(rows)
D.to_csv(PROC / "validation_zone_distribution.csv", index=False, encoding="utf-8-sig")

chi2, p = stats.chisquare(D.solar_obs, D.expected)
z1 = D[D.zone == 1].iloc[0]
z12 = D[D.zone <= 2]
out = {
    "n_plants": int(tot_obs),
    "zone_table": rows,
    "chi2": round(float(chi2), 1), "df": int(len(D) - 1),
    "p": float(f"{p:.3g}"),
    "zone1_hit_rate": round(float(z1.solar_obs / tot_obs), 3),   # share of plants in Zone 1
    "zone1_land_share": round(float(z1.land_pct / 100), 3),
    "zone1_enrichment": float(z1.enrichment),
    "zone12_hit_rate": round(float(z12.solar_obs.sum() / tot_obs), 3),
    "zone12_land_share": round(float(z12.land_pct.sum() / 100), 3),
}
print(D.to_string(index=False))
print(json.dumps(out, indent=2))
(PROC / "validation_zone_stats.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
