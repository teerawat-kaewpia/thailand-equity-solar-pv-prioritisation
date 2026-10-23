# -*- coding: utf-8 -*-
"""
Province-level (n=77) weight sensitivity + OSM validation for the corrected
EWM-TOPSIS pipeline. Writes the same CSV schemas the table/figure scripts use.
"""
import numpy as np, pandas as pd, geopandas as gpd, fiona, json
from shapely.geometry import shape, Point
from scipy import stats
from scipy.stats import chi2_contingency
from pathlib import Path
import os
import warnings; warnings.filterwarnings("ignore")

BASE = Path(os.environ.get("ENERGY_DATA_ROOT", r"D:\Clude Code GIS\Energy"))  # raw data (Tier-2), override via env
PROC = BASE / "DER" / "Data" / "14_Processed_90m"
GADM = BASE / "DER" / "Data" / "01_Admin_Boundaries" / "gadm41_THA.gpkg"
PLANTS = BASE / "Energy map" / "GridNetwork_OSM" / "plants.geojson"

norm = pd.read_csv(PROC / "province_criteria_normalised.csv")
summ = pd.read_csv(PROC / "province_PAI_summary.csv")
W = pd.read_csv(PROC / "EWM_weights.csv")
CRIT = W["criterion"].tolist()
w_ewm = W["weight"].to_numpy(float)
X = norm[CRIT].to_numpy(float)
n = len(norm)

def topsis(X, w):
    Xw = X * w
    dp = np.sqrt(((Xw - w) ** 2).sum(1)); dn = np.sqrt((Xw ** 2).sum(1))
    return dn / (dp + dn + 1e-12)

# scenarios
w_equal  = np.full(5, 0.2)
w_expert = w_ewm.copy(); w_expert[1] = 0.30
w_expert[[0, 2, 3, 4]] = w_ewm[[0, 2, 3, 4]] / w_ewm[[0, 2, 3, 4]].sum() * 0.70
SC = {"EWM": w_ewm, "Equal": w_equal, "Expert": w_expert}
print("scenario weights:")
for k, v in SC.items():
    print(f"  {k:7s} " + " ".join(f"{c.split('_')[0]}:{x:.3f}" for c, x in zip(CRIT, v)) + f"  sum={v.sum():.3f}")

df = pd.DataFrame({"NAME_1": norm["NAME_1"]})
for k, v in SC.items():
    df[f"PAI_{k}"] = topsis(X, v)
    df[f"rank_{k}"] = df[f"PAI_{k}"].rank(ascending=False).astype(int)
for s in ["Equal", "Expert"]:
    df[f"rank_diff_{s}"] = (df[f"rank_{s}"] - df["rank_EWM"]).abs()
df.to_csv(PROC / "sensitivity_analysis.csv", index=False, encoding="utf-8-sig")

print("\n=== Sensitivity vs EWM baseline ===")
rows = []
for s in ["Equal", "Expert"]:
    rho, prho = stats.spearmanr(df["PAI_EWM"], df[f"PAI_{s}"])
    tau, ptau = stats.kendalltau(df["rank_EWM"], df[f"rank_{s}"])
    dif = df[f"rank_diff_{s}"]
    rows.append({"Comparison": f"EWM vs {'Equal Weights (1/5 each)' if s=='Equal' else 'Expert Weights (equity-first)'}",
                 "Spearman ρ": round(rho, 4), "Spearman p": "<0.001" if prho < 1e-3 else round(prho, 4),
                 "Kendall τ": round(tau, 4), "Kendall p": "<0.001" if ptau < 1e-3 else round(ptau, 4),
                 "RMSE (rank units)": round(float(np.sqrt((dif ** 2).mean())), 3),
                 "MAE (rank units)": round(float(dif.mean()), 3),
                 "Max |Δrank|": int(dif.max()),
                 "N provinces |Δrank| > 10": int((dif > 10).sum()),
                 "N provinces |Δrank| > 5": int((dif > 5).sum())})
    print(f"  {s:7s} rho={rho:.3f} tau={tau:.3f} RMSE={rows[-1]['RMSE (rank units)']} max={int(dif.max())}")
pd.DataFrame(rows).to_csv(PROC / "sensitivity_summary.csv", index=False, encoding="utf-8-sig")

# ── OSM validation (province level) ──────────────────────────────────────────
adm1 = next(l for l in fiona.listlayers(str(GADM)) if l.endswith("_1"))
prov = gpd.read_file(str(GADM), layer=adm1)[["NAME_1", "geometry"]].to_crs("EPSG:4326")
with open(PLANTS, encoding="utf-8") as fh:
    data = json.load(fh)
pts = []
for ft in data["features"]:
    pr = ft.get("properties", {})
    src = (pr.get("generator:source") or pr.get("plant:source") or pr.get("power_source") or "")
    if src.lower() != "solar":
        continue
    g = ft.get("geometry")
    if not g: continue
    s = shape(g); p = s.centroid if s.geom_type != "Point" else s
    if p.is_empty or p.x == 0.0: continue
    pts.append(Point(p.x, p.y))
sg = gpd.GeoDataFrame(geometry=pts, crs="EPSG:4326").cx[97.5:106.0, 5.0:21.0]
cnt = gpd.sjoin(sg, prov, predicate="within").groupby("NAME_1").size()

v = summ[["NAME_1", "rank", "PAI", "dominant_zone"]].copy()
v["solar_count"] = v["NAME_1"].map(cnt).fillna(0).astype(int)
v.sort_values("rank").to_csv(PROC / "validation_solar_osm.csv", index=False, encoding="utf-8-sig")

rho, p = stats.spearmanr(v["PAI"], v["solar_count"])
prov_a = prov.to_crs("EPSG:32647"); prov_a["area"] = prov_a.geometry.area
v = v.merge(prov_a[["NAME_1", "area"]], on="NAME_1")
tot_a, tot_p = v["area"].sum(), v["solar_count"].sum()
print(f"\n=== OSM validation (n={tot_p} plants, province level) ===")
print(f"  Spearman PAI vs plant count: rho={rho:.3f} (p={p:.3f})")
obs, exp = [], []
for z in range(1, 6):
    s = v[v["dominant_zone"] == z]
    o_, e_ = s["solar_count"].sum(), tot_p * s["area"].sum() / tot_a
    obs.append(o_); exp.append(max(e_, 1e-9))
    print(f"  Zone {z}: obs {o_:>3} ({o_/tot_p*100:4.1f}%)  area {s['area'].sum()/tot_a*100:4.1f}%  "
          f"enrich {(o_/tot_p)/(s['area'].sum()/tot_a):.2f}x")
chi2, pchi, dof, _ = chi2_contingency(np.array([obs, [max(1, int(x)) for x in exp]]))
print(f"  chi2={chi2:.1f} df={dof} p={pchi:.4g}")
print("\nSaved: sensitivity_analysis.csv, sensitivity_summary.csv, validation_solar_osm.csv")
