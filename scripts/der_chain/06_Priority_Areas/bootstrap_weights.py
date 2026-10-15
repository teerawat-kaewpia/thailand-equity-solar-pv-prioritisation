# -*- coding: utf-8 -*-
"""
Canonical bootstrap of the EWM weights and cluster robustness (conditional
uncertainty). Resamples the 77 province-level observations with replacement and
recomputes the entropy weights on each replicate to give percentile confidence
intervals; also checks whether the six baseline Zone-1 provinces stay inside the
highest-PAI cluster as k varies.

This is a CONDITIONAL uncertainty: it resamples the province observations but
does NOT propagate error in the underlying raster or source data, so the true
intervals are wider. Fixed seed (42) so the output is reproducible — this is the
single canonical producer of bootstrap_uncertainty.json.

Output: DER/Data/14_Processed_90m/bootstrap_uncertainty.json
"""
import json
import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from pathlib import Path
import os
import warnings
warnings.filterwarnings("ignore")

PROC = Path(os.environ.get("DER_PROJECT_ROOT", Path(__file__).resolve().parents[2])) / "Data" / "14_Processed_90m"
CK = ["C1_Resource", "C2_Equity", "C3_Demand", "C4_Infra", "C5_Physical"]
B = 4999
SEED = 42


def ewm(M):
    Mp = M - M.min(0) + 1e-12
    P = Mp / Mp.sum(0, keepdims=True)
    e = np.clip(-(1 / np.log(len(M))) * (P * np.where(P > 0, np.log(P), 0)).sum(0), 0, 1)
    d = 1 - e
    return d / d.sum()


def topsis(M, w):
    Mw = M * w
    return np.sqrt((Mw ** 2).sum(1)) / (np.sqrt(((Mw - w) ** 2).sum(1))
                                        + np.sqrt((Mw ** 2).sum(1)) + 1e-12)


norm = pd.read_csv(PROC / "province_criteria_normalised.csv")
X = norm[CK].to_numpy(float)
n = len(X)
w0 = ewm(X)
PAI = topsis(X, w0)

# ── bootstrap weight CIs ──────────────────────────────────────────────────────
rng = np.random.default_rng(SEED)
wb = np.empty((B, 5))
for b in range(B):
    wb[b] = ewm(X[rng.integers(0, n, n)])
ci = {CK[i]: [round(float(np.percentile(wb[:, i], 2.5)), 3),
              round(float(np.percentile(wb[:, i], 97.5)), 3)] for i in range(5)}

# ── cluster robustness: do the 6 baseline Zone-1 provinces stay in the top
#    cluster as k varies, and how large is that cluster? ─────────────────────────
top6 = set(norm.iloc[np.argsort(-PAI)[:6]]["NAME_1"])
stability = {}
for k in range(2, 6):
    lab = KMeans(n_clusters=k, random_state=SEED, n_init=10).fit_predict(PAI.reshape(-1, 1))
    hi = max(range(k), key=lambda z: PAI[lab == z].mean())
    topk = set(norm[lab == hi]["NAME_1"])
    stability[str(k)] = {"top_cluster_size": int(len(topk)),
                         "baseline_zone1_inside": int(len(top6 & topk))}

out = {"B": B, "seed": SEED, "weights_baseline": {CK[i]: round(float(w0[i]), 4) for i in range(5)},
       "weight_ci": ci, "zone1_top6": sorted(top6), "stability_by_k": stability,
       "note": "conditional uncertainty: resamples 77 province observations only, "
               "does not propagate raster/source-data error"}
(PROC / "bootstrap_uncertainty.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
print(f"C2 weight 95% CI: {ci['C2_Equity']}")
for k, v in stability.items():
    print(f"  k={k}: top cluster {v['top_cluster_size']} provinces, "
          f"{v['baseline_zone1_inside']}/6 baseline Zone-1 inside")
print(f"Saved: {PROC / 'bootstrap_uncertainty.json'}")
