"""Policy scenarios S1-S3 and MV-proximity screening classes.

SCENARIO_PROTOCOL.md Section 1-2 as amended by A2 (74 PEA-served provinces,
S1 = population-proportional baseline) and A3 (MV = province mean distance to
GridFinder modelled MV lines, km). Weighted median = lower weighted median: the
smallest value at which the cumulative allocation weight reaches 0.5. Jenks =
mapclassify FisherJenks (exact optimal natural breaks), k = 3, on 74 provinces.
"""
import ast, sys, json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from _paths import SRC, BASE, out_path
import numpy as np, pandas as pd
import mapclassify

B, K = 1_000_000, 15
MEA = {"Bangkok Metropolis", "Nonthaburi", "Samut Prakan"}
CAVEAT = ("Hosting capacity and connection feasibility are not assessable from the available "
          "data and require utility feeder-level verification.")

d = pd.read_csv(BASE / "Data" / "scenarios" / "province_inputs.csv")
from _lineage import load_mv
mv, MV_LINEAGE = load_mv()
d = d.merge(mv[["NAME_1", "mv_dist_mean_km", "mv_dist_median_km"]], on="NAME_1", how="left")
assert len(d) == 77 and d.mv_dist_mean_km.notna().all()
src = (SRC / "Scripts" / "06_Priority_Areas" / "maup_analysis.py").read_text(encoding="utf-8")
node = next(n for n in ast.parse(src).body if isinstance(n, ast.Assign) and getattr(n.targets[0], "id", "") == "REGION")
P2R = {p: r for r, ps in ast.literal_eval(node.value).items() for p in ps}
d["region"] = d.NAME_1.map(P2R)
assert d.region.notna().all()

# A2: PEA service area only
assert MEA <= set(d.NAME_1)
d = d[~d.NAME_1.isin(MEA)].reset_index(drop=True)
assert len(d) == 74

# Section 2 + A2.5 + A3: MV-proximity classes on 74 provinces
fj = mapclassify.FisherJenks(d.mv_dist_mean_km.to_numpy(), k=3)
labels = np.array(["nearer", "intermediate", "farther"])
d["mv_class"] = labels[fj.yb]
breaks = [round(float(b), 3) for b in fj.bins]


def wmedian(x, w):
    o = np.argsort(np.asarray(x)); x, w = np.asarray(x)[o], np.asarray(w)[o]
    return float(x[np.searchsorted(np.cumsum(w) / w.sum(), 0.5)])


def eligible(rule):
    if rule == "S1":
        return d.index
    col = {"S2": "PAI", "S3": "PAI_eff"}[rule]
    cut = d[col].nlargest(K).min()
    sel = d.index[d[col] >= cut]
    assert len(sel) == K, f"tie at rank {K} for {rule}"
    return sel


rows, members = [], {}
for s, label in [("S1", "Population-proportional baseline"), ("S2", "Equity-targeted support"),
                 ("S3", "Resource-and-infrastructure-oriented comparator")]:
    e = d.loc[eligible(s)]
    b = B * e.population / e.population.sum()
    w = b / B
    row = {"scenario": s, "label": label, "provinces": len(e), "regions": e.region.nunique(),
           "poverty_weighted_beneficiary_equiv": round(float((b * e.poverty_pct / 100).sum())),
           "mean_poverty_pct": round(float((w * e.poverty_pct).sum()), 2),
           "mean_pvout_kwh_kwp": round(float((w * e.pvout_kwh_kwp).sum()), 1),
           "median_dist_line_km": round(wmedian(e.dist_line_km, w), 1),
           "median_dist_mv_km": round(wmedian(e.mv_dist_mean_km, w), 2),
           "max_province_share_pct": round(float(w.max() * 100), 1)}
    for c in labels:
        row[f"share_B_{c}_pct"] = round(float(w[e.mv_class == c].sum() * 100), 1)
    rows.append(row)
    members[s] = sorted(e.NAME_1)

t = pd.DataFrame(rows)
meta = {"analysis_set": "74 PEA-served provinces (A2)", "K": f"{K} of 74 ({K/74*100:.1f}%)",
        "pea_area_population": round(float(d.population.sum())), "B": B,
        "mv_variable": "province mean distance to GridFinder modelled MV lines, km (A3)",
        "mv_lineage": MV_LINEAGE,
        "mv_jenks_k3_upper_bounds_km": breaks,
        "mv_class_counts": d.mv_class.value_counts().to_dict(),
        "caveat_all_classes": CAVEAT,
        "overlap_S2_S3": sorted(set(members["S2"]) & set(members["S3"]))}
pd.set_option("display.width", 250)
print(t.to_string(index=False))
print(json.dumps(meta, ensure_ascii=False, indent=1))
t.to_csv(out_path("Data", "scenarios", "scenario_tradeoff.csv"), index=False, encoding="utf-8-sig")
d[["NAME_1", "region", "population", "poverty_pct", "pvout_kwh_kwp", "dist_line_km", "mv_dist_mean_km",
   "mv_dist_median_km", "mv_class", "PAI", "PAI_eff"]].to_csv(
    out_path("Data", "scenarios", "province_scenario_table_74.csv"), index=False, encoding="utf-8-sig")
json.dump({"members": members, "meta": meta}, open(out_path("Data", "scenarios", "scenario_members.json"), "w",
          encoding="utf-8"), ensure_ascii=False, indent=1)
