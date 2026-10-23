"""A4 re-run: recompute the two DER files that have no producing script.

  cluster_stability.json  silhouette of 1-D K-means on province PAI for k = 2..8
                          (KMeans random_state = 42, n_init = 10, as compute_pai_province_level.py).
                          The gap statistic in the old file has no recoverable method and is not used
                          by the TEJ manuscript, so it is not recomputed and is marked as such.
  lisa_fdr.json           counts from province_LISA_fdr.csv (reviewer_robustness_checks.py output).

Usage: python rerun_c2fix_extras.py <PROC dir> [--check]   --check compares with the files already there.
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score

proc = Path(sys.argv[1])
check = "--check" in sys.argv
pai = pd.read_csv(proc / "province_PAI_summary.csv")["PAI"].to_numpy(float).reshape(-1, 1)
sil = {}
for k in range(2, 9):
    lab = KMeans(n_clusters=k, random_state=42, n_init=10).fit_predict(pai)
    sil[str(k)] = round(float(silhouette_score(pai, lab)), 3)
best = max(sil, key=sil.get)
cs = {"silhouette": sil, "silhouette_best_k": int(best), "k_chosen": 5, "silhouette_k5": sil["5"],
      "silhouette_max": sil[best],
      "gap": "not recomputed (no producing script for the original values, not used in the TEJ manuscript)",
      "produced_by": "DER_TEJ/Scripts/rerun_c2fix_extras.py"}
lf = pd.read_csv(proc / "province_LISA_fdr.csv")
pcol = "p_bh" if "p_bh" in lf.columns else "LISA_p_fdr"   # DER file uses p_bh, repo script writes LISA_p_fdr
lj = {"n_raw_sig": int((lf["LISA_p"] < 0.05).sum()), "n_fdr_sig": int((lf[pcol] < 0.05).sum()),
      "min_p_bh": round(float(lf[pcol].min()), 3), "method": "Benjamini-Hochberg", "n_tests": int(len(lf)),
      "produced_by": "DER_TEJ/Scripts/rerun_c2fix_extras.py"}
if check:
    old_cs = json.loads((proc / "cluster_stability.json").read_text(encoding="utf-8"))
    old_lf = json.loads((proc / "lisa_fdr.json").read_text(encoding="utf-8"))
    print("silhouette reproduced:", old_cs["silhouette"] == sil, "| old", old_cs["silhouette"], "| new", sil)
    print("lisa_fdr reproduced:", all(old_lf[k] == lj[k] for k in ("n_raw_sig", "n_fdr_sig", "min_p_bh", "n_tests")), old_lf, lj)
else:
    (proc / "cluster_stability.json").write_text(json.dumps(cs, indent=1), encoding="utf-8")
    (proc / "lisa_fdr.json").write_text(json.dumps(lj, indent=1), encoding="utf-8")
    print("written:", cs, lj)
