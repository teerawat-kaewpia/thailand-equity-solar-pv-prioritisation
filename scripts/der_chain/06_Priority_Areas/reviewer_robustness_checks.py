# -*- coding: utf-8 -*-
"""Reviewer robustness checks for the final province-level EWM-TOPSIS model.

This script deliberately reads the final 77 x 5 normalised criterion matrix
instead of re-running raster preprocessing. It does not overwrite baseline PAI,
weights, zones, or LISA files. Outputs are separate reviewer-appendix files.

Checks:
  1. Conditional bootstrap uncertainty for EWM weights (B=4,999).
  2. Dirichlet perturbation of final weights (N=4,999, kappa=50), reporting
     rank IQR and probability of retaining each baseline k=5 priority zone.
  3. K-means sensitivity over k=2..8, including silhouette and overlap with
     the baseline Zone 1.
  4. Benjamini-Hochberg FDR correction of existing Local Moran p-values.
"""

from __future__ import annotations

import json
from pathlib import Path
import os

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score


BASE = Path(os.environ.get("DER_PROJECT_ROOT", Path(__file__).resolve().parents[2]))
PROC = BASE / "Data" / "14_Processed_90m"
RNG = np.random.default_rng(20260904)
B = 4_999
N_DIRICHLET = 4_999
KAPPA = 50.0
K_VALUES = range(2, 9)


def ewm_weights(x: np.ndarray) -> np.ndarray:
    """Shannon-entropy weights for a non-negative normalised criterion matrix."""
    positive = x - x.min(axis=0) + 1e-12
    probabilities = positive / positive.sum(axis=0, keepdims=True)
    entropy = -(probabilities * np.log(probabilities)).sum(axis=0) / np.log(len(x))
    divergence = 1.0 - np.clip(entropy, 0.0, 1.0)
    return divergence / divergence.sum()


def topsis(x: np.ndarray, weights: np.ndarray) -> np.ndarray:
    weighted = x * weights
    d_best = np.sqrt(((weighted - weights) ** 2).sum(axis=1))
    d_worst = np.sqrt((weighted ** 2).sum(axis=1))
    return d_worst / (d_best + d_worst + 1e-12)


def priority_zones(pai: np.ndarray, k: int, n_init: int = 100) -> np.ndarray:
    """Map k-means labels to 1=highest through k=lowest priority."""
    labels = KMeans(n_clusters=k, random_state=42, n_init=n_init).fit_predict(pai.reshape(-1, 1))
    means = np.array([pai[labels == label].mean() for label in range(k)])
    order = np.argsort(means)[::-1]
    remap = {old: new + 1 for new, old in enumerate(order)}
    return np.array([remap[label] for label in labels], dtype=int)


def bh_fdr(p_values: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Return Benjamini-Hochberg adjusted p-values and alpha=.05 rejections."""
    n = len(p_values)
    order = np.argsort(p_values)
    ranked = p_values[order]
    adjusted_ranked = np.minimum.accumulate((ranked * n / np.arange(1, n + 1))[::-1])[::-1]
    adjusted = np.empty(n)
    adjusted[order] = np.minimum(adjusted_ranked, 1.0)
    return adjusted, adjusted <= 0.05


def main() -> None:
    norm = pd.read_csv(PROC / "province_criteria_normalised.csv")
    weights = pd.read_csv(PROC / "EWM_weights.csv")
    summary = pd.read_csv(PROC / "province_PAI_summary.csv")
    lisa = pd.read_csv(PROC / "province_LISA.csv")

    criteria = weights["criterion"].tolist()
    x = norm[criteria].to_numpy(float)
    baseline_w = weights["weight"].to_numpy(float)
    names = norm["NAME_1"].to_numpy()
    n = len(x)
    assert n == 77 and x.shape[1] == 5

    baseline_pai = topsis(x, baseline_w)
    baseline_zones = summary.set_index("NAME_1").loc[names, "dominant_zone"].to_numpy(int)
    max_pai_error = float(np.abs(baseline_pai - norm["PAI"].to_numpy(float)).max())

    # 1. Conditional bootstrap: matrix is already transformed and normalised.
    boot_weights = np.empty((B, len(criteria)))
    for b in range(B):
        boot_weights[b] = ewm_weights(x[RNG.integers(0, n, n)])
    weight_out = pd.DataFrame({
        "criterion": criteria,
        "baseline_weight": baseline_w,
        "bootstrap_mean": boot_weights.mean(axis=0),
        "bootstrap_sd": boot_weights.std(axis=0, ddof=1),
        "bootstrap_ci95_low": np.quantile(boot_weights, 0.025, axis=0),
        "bootstrap_ci95_high": np.quantile(boot_weights, 0.975, axis=0),
    })
    weight_out.to_csv(PROC / "reviewer_weight_uncertainty.csv", index=False, encoding="utf-8-sig")

    # 2. Weight-only uncertainty. Criterion measurements themselves are held fixed.
    dirichlet_pai = np.empty((N_DIRICHLET, n))
    dirichlet_zones = np.empty((N_DIRICHLET, n), dtype=np.int8)
    for draw in range(N_DIRICHLET):
        draw_w = RNG.dirichlet(baseline_w * KAPPA)
        draw_pai = topsis(x, draw_w)
        dirichlet_pai[draw] = draw_pai
        dirichlet_zones[draw] = priority_zones(draw_pai, 5, n_init=10)
    draw_ranks = pd.DataFrame(-dirichlet_pai).rank(axis=1, method="average").to_numpy()
    stability = pd.DataFrame({
        "NAME_1": names,
        "baseline_zone": baseline_zones,
        "baseline_rank": pd.Series(-baseline_pai).rank(method="average").astype(int).to_numpy(),
        "dirichlet_rank_median": np.median(draw_ranks, axis=0),
        "dirichlet_rank_iqr": np.quantile(draw_ranks, 0.75, axis=0) - np.quantile(draw_ranks, 0.25, axis=0),
        "dirichlet_pai_ci95_low": np.quantile(dirichlet_pai, 0.025, axis=0),
        "dirichlet_pai_ci95_high": np.quantile(dirichlet_pai, 0.975, axis=0),
        "probability_baseline_zone": (dirichlet_zones == baseline_zones[None, :]).mean(axis=0),
        "probability_zone1": (dirichlet_zones == 1).mean(axis=0),
    }).sort_values("baseline_rank")
    stability.to_csv(PROC / "reviewer_dirichlet_stability.csv", index=False, encoding="utf-8-sig")

    # 3. K sensitivity uses the fixed baseline PAI; this isolates the policy tier choice.
    base_zone1 = set(names[baseline_zones == 1])
    cluster_rows = []
    for k in K_VALUES:
        zones = priority_zones(baseline_pai, k)
        zone1 = set(names[zones == 1])
        cluster_rows.append({
            "k": k,
            "silhouette": float(silhouette_score(baseline_pai.reshape(-1, 1), zones)),
            "top_tier_n": int((zones == 1).sum()),
            "top_tier_members": "; ".join(sorted(zone1)),
            "overlap_with_k5_zone1_n": len(base_zone1 & zone1),
            "overlap_with_k5_zone1_pct": len(base_zone1 & zone1) / len(base_zone1) * 100,
        })
    cluster_out = pd.DataFrame(cluster_rows)
    cluster_out.to_csv(PROC / "reviewer_cluster_sensitivity.csv", index=False, encoding="utf-8-sig")

    # 4. FDR correction applied to the original LISA permutation p-values.
    lisa_fdr = lisa.copy()
    lisa_fdr["LISA_p_fdr"], significant = bh_fdr(lisa_fdr["LISA_p"].to_numpy(float))
    lisa_fdr["LISA_type_fdr"] = np.where(significant, lisa_fdr["LISA_type"].replace({"ns": "unclassified"}), "ns")
    lisa_fdr.to_csv(PROC / "province_LISA_fdr.csv", index=False, encoding="utf-8-sig")

    report = {
        "input": {
            "n_provinces": int(n),
            "criteria": criteria,
            "baseline_pai_max_abs_error_vs_input": max_pai_error,
        },
        "bootstrap": {
            "draws": B,
            "conditioning": "Final transformed and normalised province matrix held fixed; provinces resampled with replacement.",
            "weights": weight_out.round(6).to_dict(orient="records"),
        },
        "dirichlet": {
            "draws": N_DIRICHLET,
            "kappa": KAPPA,
            "conditioning": "Final criterion matrix held fixed; EWM baseline weights perturbed.",
            "zone1_membership_probability": stability[stability["baseline_zone"] == 1][["NAME_1", "probability_zone1"]].round(4).to_dict(orient="records"),
        },
        "cluster_sensitivity": cluster_out.round(4).to_dict(orient="records"),
        "lisa_fdr": {
            "n_unadjusted_significant": int((lisa_fdr["LISA_p"] < 0.05).sum()),
            "n_fdr_significant": int(significant.sum()),
            "fdr_significant_units": lisa_fdr.loc[significant, "NAME_1"].tolist(),
        },
    }
    with open(PROC / "reviewer_robustness_summary.json", "w", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2)

    print("Reviewer robustness checks complete")
    print(f"  Baseline PAI reconstruction max error: {max_pai_error:.3e}")
    print(weight_out.round(4).to_string(index=False))
    print("\nK sensitivity")
    print(cluster_out[["k", "silhouette", "top_tier_n", "overlap_with_k5_zone1_n"]].to_string(index=False))
    print(f"\nLISA: {report['lisa_fdr']['n_unadjusted_significant']} unadjusted; "
          f"{report['lisa_fdr']['n_fdr_significant']} FDR-significant")


if __name__ == "__main__":
    main()
