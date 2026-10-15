"""Province-level inputs for the policy scenarios (SCENARIO_PROTOCOL.md Section 1).

Computes, for the 77 GADM 4.1 provinces:
  population (WorldPop 2020, the same raster as C3), raw PVOUT (kWh/kWp/yr,
  Global Solar Atlas v2, the same raster as C1 before normalisation), mean
  distance to the OSM power-line network (km, recovered per pixel from the C4
  raster C = exp(-d/5)), poverty incidence (%, the C2 source), PAI and the
  efficiency-only composite (re-derived exactly as in build_master_results.py).

Reproduction checks against v2 are run before anything is written. The MV
variable is NOT computed here (its definition is pending, see Docs).
"""
import sys, json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from _paths import RAW, SRC, out_path
import numpy as np, pandas as pd, geopandas as gpd
from rasterstats import zonal_stats
from scipy import stats

ENERGY = RAW
PROC = SRC / "Data" / "14_Processed_90m"
GADM = SRC / "Data" / "01_Admin_Boundaries" / "gadm41_THA.gpkg"
WORLDPOP = SRC / "Data" / "05_Population" / "worldpop_THA_2020_100m.tif"   # = C3 input
PVOUT = (ENERGY / "Energy map" / "Thailand_GISdata_LTAym_YearlyMonthlyTotals_GlobalSolarAtlas-v2_GEOTIFF"
         / "Thailand_GISdata_LTAy_YearlyMonthlyTotals_GlobalSolarAtlas-v2_GEOTIFF" / "PVOUT.tif")  # = C1 input
C4 = PROC / "C5_grid_dist_90m.tif"                                            # exp(-d/5), d in km

prov = gpd.read_file(GADM, layer="ADM_ADM_1")[["NAME_1", "geometry"]].to_crs(4326)


def dist_km(x):
    v = x.compressed() if np.ma.isMaskedArray(x) else x.ravel()
    v = v[(v > 0) & (v <= 1)]
    return float(np.mean(-5.0 * np.log(v))) if v.size else np.nan


print("zonal: population ...")
pop = zonal_stats(prov, str(WORLDPOP), stats=["sum"], nodata=-99999.0, all_touched=False)
print("zonal: PVOUT ...")
pv = zonal_stats(prov, str(PVOUT), stats=["mean"], all_touched=False)
print("zonal: transmission distance ...")
tr = zonal_stats(prov, str(C4), stats=[], add_stats={"d": dist_km}, nodata=-9999.0, all_touched=False)

df = pd.DataFrame({"NAME_1": prov.NAME_1,
                   "population": [z["sum"] for z in pop],
                   "pvout_kwh_kwp": [z["mean"] for z in pv],
                   "dist_line_km": [z["d"] for z in tr]})

pov = pd.read_csv(PROC / "C2_poverty_province.csv")[["NAME_1", "poverty_pct"]]
summ = pd.read_csv(PROC / "province_PAI_summary.csv")[["NAME_1", "PAI", "rank", "dominant_zone"]]
norm = pd.read_csv(PROC / "province_criteria_normalised.csv")
df = df.merge(pov, on="NAME_1", how="left").merge(summ, on="NAME_1", how="left")

# ── efficiency-only composite, identical to build_master_results.py ──────────
W = pd.read_csv(PROC / "EWM_weights.csv")
CR = list(W.criterion)
X = norm[CR].to_numpy(float)
eff = [0, 2, 3, 4]
def ewm(Mx):
    n = Mx.shape[0]; Mp = Mx - Mx.min(0) + 1e-12
    P = Mp / Mp.sum(0, keepdims=True)
    e = np.clip(-(1/np.log(n))*(P*np.where(P > 0, np.log(P), 0)).sum(0), 0, 1)
    d = 1 - e; return d/d.sum()
def topsis(Mx, w):
    Mw = Mx*w
    return np.sqrt((Mw**2).sum(1))/(np.sqrt(((Mw-w)**2).sum(1))+np.sqrt((Mw**2).sum(1))+1e-12)
norm["PAI_eff"] = topsis(X[:, eff], ewm(X[:, eff]))
df = df.merge(norm[["NAME_1", "PAI_eff"]], on="NAME_1", how="left")

# ── reproduction checks (abort on failure) ───────────────────────────────────
MR = json.loads((SRC / "Data" / "master_results.json").read_text(encoding="utf-8"))
chk = {}
assert len(df) == 77 and df[["poverty_pct", "PAI", "PAI_eff"]].notna().all().all(), "join incomplete"
r = stats.spearmanr(norm[CR[1]], norm["PAI_eff"])[0]
chk["equity_vs_eff_rho"] = (round(r, 3), MR["equity_vs_efficiency_only"]["spearman"])
assert round(r, 3) == MR["equity_vs_efficiency_only"]["spearman"], chk
zm = df.groupby("dominant_zone").dist_line_km.mean().round(1)
chk["zone_line_km"] = {int(z): float(zm[z]) for z in zm.index}   # v2 Table 9 values are legacy, not compared here
chk["pop_total_million"] = round(df.population.sum() / 1e6, 2)
chk["pvout_range"] = (round(df.pvout_kwh_kwp.min(), 0), round(df.pvout_kwh_kwp.max(), 0))
print(json.dumps(chk, indent=1))

df.to_csv(out_path("Data", "scenarios", "province_inputs.csv"), index=False, encoding="utf-8-sig")
json.dump(chk, open(out_path("Data", "scenarios", "province_inputs_checks.json"), "w"), indent=1)
print("written")
