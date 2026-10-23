"""Cell-area sensitivity of the province means (external review item 4, 2026-10-16).

The criterion rasters sit on a 0.000833 deg grid in EPSG:4326, so a cell's ground area scales with
cos(latitude). The pipeline takes unweighted cell means per province (rasterstats zonal_stats). This
script recomputes every province mean with cos(latitude) cell weights, reruns the province pipeline
unchanged (log1p(100x) for C3, one 2nd-98th percentile clip, EWM, bounded-ideal TOPSIS, K-means k = 5,
S2/S3 = top 15 of the 74 PEA provinces) and compares with Run 4.

C2 is constant within a province, so it is unaffected by construction. Reported as a post hoc check.
Output: Data/area_weight_check/area_weight_check.json
"""
import json
import sys
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import rasterio
from rasterio.features import rasterize
from scipy import stats
from sklearn.cluster import KMeans

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _paths import SRC, BASE, out_path

PROC = SRC / "Data" / "14_Processed_90m"
GADM = SRC / "Data" / "01_Admin_Boundaries" / "gadm41_THA.gpkg"
LAY = {"C1_Resource": "C1_PVOUT_90m.tif", "C2_Equity": "C2_poverty_90m.tif", "C3_Demand": "C3_popdens_90m.tif",
       "C4_Infra": "C5_grid_dist_90m.tif", "C5_Physical": "C6_land_suitability_90m.tif"}
NAMES = list(LAY)

prov = gpd.read_file(GADM, layer="ADM_ADM_1")[["NAME_1", "geometry"]].to_crs("EPSG:4326").reset_index(drop=True)
with rasterio.open(PROC / LAY["C1_Resource"]) as s0:
    shape, tr = s0.shape, s0.transform
ids = rasterize(((g, i + 1) for i, g in enumerate(prov.geometry)), out_shape=shape, transform=tr, fill=0, dtype="int16")
lat = tr.f + tr.e * (np.arange(shape[0]) + 0.5)                       # cell-centre latitude of each row
wrow = np.cos(np.radians(lat))                                        # relative ground area of a cell in that row

unw, wtd, spread = {}, {}, {}
for k, f in LAY.items():
    with rasterio.open(PROC / f) as s:
        a = s.read(1).astype("float64")
        nod = s.nodata
    ok = (ids > 0) & np.isfinite(a) & ((a != nod) if nod is not None else True)
    idx = ids[ok]
    w = np.broadcast_to(wrow[:, None], shape)[ok]
    n = len(prov) + 1
    unw[k] = (np.bincount(idx, a[ok], n) / np.bincount(idx, minlength=n))[1:]
    wtd[k] = (np.bincount(idx, a[ok] * w, n) / np.bincount(idx, w, n))[1:]
# within-province spread of the cell-area weight (max/min - 1)
rows_of = {}
r_idx = np.broadcast_to(np.arange(shape[0])[:, None], shape)
for i in range(1, len(prov) + 1):
    rr = r_idx[ids == i]
    spread[prov.NAME_1[i - 1]] = float(wrow[rr].max() / wrow[rr].min() - 1) if len(rr) else 0.0


def pipeline(raw):
    X = []
    for k in NAMES:
        v = np.log1p(raw[k] * 100.0) if k == "C3_Demand" else raw[k]
        lo, hi = np.nanpercentile(v, 2), np.nanpercentile(v, 98)
        X.append(np.clip((v - lo) / (hi - lo + 1e-12), 0, 1))
    X = np.column_stack(X)

    def ewm_topsis(M):
        Mp = M - M.min(0) + 1e-12
        P = Mp / Mp.sum(0)
        e = np.clip(-(1 / np.log(len(M))) * np.where(P > 0, P * np.log(P), 0).sum(0), 0, 1)
        w = (1 - e) / (1 - e).sum()
        V = M * w
        dp, dm = np.sqrt(((V - w) ** 2).sum(1)), np.sqrt((V ** 2).sum(1))
        return dm / (dp + dm + 1e-12), w

    pai, w = ewm_topsis(X)
    eff, _ = ewm_topsis(X[:, [0, 2, 3, 4]])
    lab = KMeans(n_clusters=5, random_state=42, n_init=10).fit_predict(pai.reshape(-1, 1))
    order = np.argsort([pai[lab == z].mean() for z in range(5)])[::-1]
    zone = np.array([int(np.where(order == l)[0][0]) + 1 for l in lab])
    return pd.DataFrame({"NAME_1": prov.NAME_1, "PAI": pai, "PAI_eff": eff, "zone": zone}), dict(zip(NAMES, w))


A, wA = pipeline(unw)
B, wB = pipeline(wtd)
SUMM = pd.read_csv(PROC / "province_PAI_summary.csv").set_index("NAME_1")
P74 = pd.read_csv(BASE / "Data" / "scenarios" / "province_scenario_table_74.csv")
MEM = json.loads((BASE / "Data" / "scenarios" / "scenario_members.json").read_text(encoding="utf-8"))["members"]


def members(D):
    d = D[D.NAME_1.isin(P74.NAME_1)]
    return set(d.nlargest(15, "PAI").NAME_1), set(d.nlargest(15, "PAI_eff").NAME_1)


s2A, s3A = members(A)
s2B, s3B = members(B)
rA, rB = A.PAI.rank(ascending=False), B.PAI.rank(ascending=False)
mean_shift = {k: float(np.max(np.abs(wtd[k] - unw[k]) / np.maximum(np.abs(unw[k]), 1e-12))) for k in NAMES}
res = {
    "grid": {"crs": "EPSG:4326", "cell_deg": 1 / 1200, "ns_m": round(1 / 1200 * 111320, 1),
             "ew_m_at_6N": round(1 / 1200 * 111320 * np.cos(np.radians(6)), 1),
             "ew_m_at_20N": round(1 / 1200 * 111320 * np.cos(np.radians(20)), 1)},
    "within_province_area_weight_spread_max_pct": round(100 * max(spread.values()), 2),
    "unweighted_reproduces_run4": {"max_abs_PAI_diff": round(float(np.abs(A.PAI.values - SUMM.PAI.loc[A.NAME_1].values).max()), 5),
                                   "zones_agree": int((A.zone.values == SUMM.dominant_zone.loc[A.NAME_1].values).sum()),
                                   "S2_same": s2A == set(MEM["S2"]), "S3_same": s3A == set(MEM["S3"])},
    "max_relative_change_of_province_means": {k: round(v, 6) for k, v in mean_shift.items()},
    "weights_unweighted": {k: round(v, 4) for k, v in wA.items()},
    "weights_area_weighted": {k: round(v, 4) for k, v in wB.items()},
    "max_abs_PAI_change": round(float(np.abs(B.PAI - A.PAI).max()), 5),
    "spearman_rank": round(float(stats.spearmanr(A.PAI, B.PAI)[0]), 5),
    "max_rank_change": int(np.abs(rA - rB).max()),
    "zones_agree_77": int((A.zone == B.zone).sum()),
    "zone_changes": A.assign(z2=B.zone)[A.zone != B.zone][["NAME_1", "zone", "z2"]].values.tolist(),
    "S2_same": s2A == s2B, "S3_same": s3A == s3B,
}
out = out_path("Data", "area_weight_check", "area_weight_check.json")
out.write_text(json.dumps(res, indent=1, default=str), encoding="utf-8")
print(json.dumps(res, indent=1, default=str))
