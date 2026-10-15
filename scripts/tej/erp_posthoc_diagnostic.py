"""Post hoc diagnostic (not a pre-specified sensitivity analysis): the excluded candidate ERP
(night-time light x national emission factor, C4_ERP_proxy_NTL_90m.tif) added back as a sixth criterion,
with the same pipeline as compute_pai_province_level.py on the corrected (A4) data.

ERP is excluded from the final criterion set because it overlaps with C3 demand density. The VIF of
24.98 printed in earlier drafts could not be reproduced after the C2 correction and is not used.
This script records the overlap, the reproducible VIF values and what adding ERP would do.

Reads SRC (read-only). Writes DER_TEJ/Data/erp_diagnostic/erp_diagnostic.json.
"""
import json
import sys
import warnings
from pathlib import Path

import fiona
import geopandas as gpd
import numpy as np
import pandas as pd
from rasterstats import zonal_stats
from scipy import stats
from sklearn.cluster import KMeans

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _paths import SRC, BASE, out_path

warnings.filterwarnings("ignore")
PROC = SRC / "Data" / "14_Processed_90m"
GADM = SRC / "Data" / "01_Admin_Boundaries" / "gadm41_THA.gpkg"
CR = ["C1_Resource", "C2_Equity", "C3_Demand", "C4_Infra", "C5_Physical"]
ERP_RASTER = PROC / "C4_ERP_proxy_NTL_90m.tif"

prov = gpd.read_file(GADM, layer=next(l for l in fiona.listlayers(str(GADM)) if l.endswith("_1")))[["NAME_1", "geometry"]].to_crs("EPSG:4326")
erp = np.array([z["mean"] for z in zonal_stats(prov, str(ERP_RASTER), stats=["mean"], nodata=-9999.0)], float)
N = pd.read_csv(PROC / "province_criteria_normalised.csv").set_index("NAME_1").loc[prov.NAME_1]
S = pd.read_csv(PROC / "province_PAI_summary.csv").set_index("NAME_1").loc[prov.NAME_1]
P74 = pd.read_csv(BASE / "Data" / "scenarios" / "province_scenario_table_74.csv")
X5 = N[CR].to_numpy(float)


def norm01(v):
    lo, hi = np.nanpercentile(v, 2), np.nanpercentile(v, 98)
    return np.clip((v - lo) / (hi - lo + 1e-12), 0, 1)


def ewm(X):
    Xp = X - X.min(0) + 1e-12
    P = Xp / Xp.sum(0)
    e = np.clip(-(1 / np.log(len(X))) * (P * np.where(P > 0, np.log(P), 0)).sum(0), 0, 1)
    return (1 - e) / (1 - e).sum()


def topsis(X, w):
    V = X * w
    return np.sqrt((V ** 2).sum(1)) / (np.sqrt(((V - w) ** 2).sum(1)) + np.sqrt((V ** 2).sum(1)) + 1e-12)


def vif_last(X):
    y, A = X[:, -1], np.column_stack([np.ones(len(X)), X[:, :-1]])
    r = y - A @ np.linalg.lstsq(A, y, rcond=None)[0]
    return float(1 / (r.var() / y.var()))


def zones(pai):
    lab = KMeans(5, random_state=42, n_init=10).fit_predict(pai.reshape(-1, 1))
    zm = [pai[lab == z].mean() for z in range(5)]
    rm = {o: r + 1 for r, o in enumerate(np.argsort(zm)[::-1])}
    return np.array([rm[z] for z in lab])


def wmedian(x, w):
    o = np.argsort(x)
    return float(np.asarray(x)[o][np.searchsorted(np.cumsum(np.asarray(w)[o]) / np.sum(w), 0.5)])


out = {"status": "post hoc diagnostic, not a pre-specified sensitivity analysis",
       "erp_raster": ERP_RASTER.name,
       "rho_erp_c3": round(float(stats.spearmanr(erp, X5[:, 2])[0]), 3),
       "rho_erp_c2": round(float(stats.spearmanr(erp, X5[:, 1])[0]), 3),
       "baseline": {"zone1": sorted(S[S.dominant_zone == 1].index.tolist()),
                    "s2_mean_poverty_pct": None, "s2_median_line_km": None},
       "variants": {}}
base_s2 = P74.nlargest(15, "PAI")
sh0 = base_s2.population / base_s2.population.sum()
out["baseline"]["s2_mean_poverty_pct"] = round(float((sh0 * base_s2.poverty_pct).sum()), 2)
out["baseline"]["s2_median_line_km"] = round(wmedian(base_s2.dist_line_km.values, sh0.values), 1)
for key, e in (("linear", norm01(erp)), ("log", norm01(np.log1p(erp * 100)))):
    X6 = np.column_stack([X5, e])
    w = ewm(X6)
    pai = topsis(X6, w)
    eff = topsis(X6[:, [0, 2, 3, 4, 5]], ewm(X6[:, [0, 2, 3, 4, 5]]))
    rho, p = stats.spearmanr(X6[:, 1], eff)
    z = zones(pai)
    df = pd.DataFrame({"NAME_1": prov.NAME_1.values, "PAI6": pai, "zone6": z})
    s = P74.merge(df, on="NAME_1").nlargest(15, "PAI6")
    sh = s.population / s.population.sum()
    out["variants"][key] = {
        "transform": "linear [0,1], 2nd-98th clip" if key == "linear" else "log(1 + 100x), then linear [0,1], 2nd-98th clip",
        "vif_erp": round(vif_last(X6), 2),
        "weights": dict(zip(CR + ["ERP"], [round(float(x), 3) for x in w])),
        "rho_equity_vs_efficiency": round(float(rho), 3), "p": float(f"{p:.2g}"),
        "rho_pai6_vs_pai": round(float(stats.spearmanr(pai, S.PAI)[0]), 3),
        "zone_sizes": [int(x) for x in np.bincount(z)[1:]],
        "zone1": sorted(df[df.zone6 == 1].NAME_1.tolist()),
        "s2_out": sorted(set(base_s2.NAME_1) - set(s.NAME_1)),
        "s2_in": sorted(set(s.NAME_1) - set(base_s2.NAME_1)),
        "s2_mean_poverty_pct": round(float((sh * s.poverty_pct).sum()), 2),
        "s2_median_line_km": round(wmedian(s.dist_line_km.values, sh.values), 1),
    }
p = out_path("Data", "erp_diagnostic", "erp_diagnostic.json")
p.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
print(json.dumps(out, ensure_ascii=False, indent=1))
