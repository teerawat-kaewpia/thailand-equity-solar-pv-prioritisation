"""Zone-level distances for the v2 priority zones, from the TEJ pipeline only.

Line distance: province mean of d = -5 ln C4 (province_inputs.csv; the C4 raster
was reproduced cell-exact by c4_provenance_check.py). MV distance: load_mv()
(mv_distance.py outputs, lineage-checked). Zone = v2 dominant_zone, 77 provinces.
Zone value = mean of the province means (the Table 9 definition).
"""
import sys, json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from _paths import BASE, out_path
from _lineage import load_mv, sha256
import pandas as pd
from scipy import stats

inp = pd.read_csv(BASE / "Data" / "scenarios" / "province_inputs.csv")
mv, lineage = load_mv()
d = inp.merge(mv[["NAME_1", "mv_dist_mean_km"]], on="NAME_1")
assert len(d) == 77

zones = {}
for z, g in d.groupby("dominant_zone"):
    zones[str(int(z))] = {"n": int(len(g)),
                          "line_km_mean": round(float(g.dist_line_km.mean()), 1),
                          "line_km_min": round(float(g.dist_line_km.min()), 1),
                          "line_km_max": round(float(g.dist_line_km.max()), 1),
                          "mv_km_mean": round(float(g.mv_dist_mean_km.mean()), 2),
                          "mv_km_min": round(float(g.mv_dist_mean_km.min()), 2),
                          "mv_km_max": round(float(g.mv_dist_mean_km.max()), 2)}
r77, p77 = stats.spearmanr(d.PAI, d.mv_dist_mean_km)
rl, pl = stats.spearmanr(d.PAI, d.dist_line_km)
out = {"zones": zones,
       "rank_line_km": sorted(zones, key=lambda z: zones[z]["line_km_mean"]),
       "rank_mv_km": sorted(zones, key=lambda z: zones[z]["mv_km_mean"]),
       "spearman_PAI_vs_mv_mean_77": {"rho": round(float(r77), 3), "p": float(f"{p77:.3g}")},
       "spearman_PAI_vs_line_mean_77": {"rho": round(float(rl), 3), "p": float(f"{pl:.3g}")},
       "inputs": {"province_inputs.csv_sha256": sha256(BASE / "Data" / "scenarios" / "province_inputs.csv")},
       "mv_lineage": lineage}
json.dump(out, open(out_path("Data", "zone_distances", "zone_distances_tej.json"), "w"), indent=1)
print(json.dumps({k: out[k] for k in ("zones", "rank_line_km", "rank_mv_km",
                                       "spearman_PAI_vs_mv_mean_77", "spearman_PAI_vs_line_mean_77")}, indent=1))
