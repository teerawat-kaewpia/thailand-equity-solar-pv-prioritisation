"""
Fig N04 — Criterion Correlation Matrix
Fig N05 — EWM Weight Comparison
========================================================
Output: Fig04_Correlation.png, Fig05_EWM_Weights.png  (600 dpi)
"""

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np
import pandas as pd
from scipy import stats
from pathlib import Path
import os

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from _paths import SRC, out_path
from _figures import figout, save_tiff   # single figure registry (Figures/main, Figures/supplementary)
BASE = SRC                                    # inputs, read-only
PROC = BASE / "Data" / "14_Processed_90m"
OUT  = out_path("Figures", "_").parent      # DER_TEJ\Figures

# Correlations must be computed on the MODEL matrix (C3 log-transformed, all
# criteria normalised to [0,1]) — the same matrix EWM and TOPSIS consume.
# Using the raw provincial means here previously produced a different Pearson r
# for C3 (0.272 vs 0.361) than the model the paper actually reports.
import json
MR = json.loads((BASE / "Data" / "master_results.json").read_text(encoding="utf-8"))
pai_df = pd.read_csv(PROC / "province_criteria_normalised.csv")

COLS  = ["C1_Resource","C2_Equity","C3_Demand","C4_Infra","C5_Physical","PAI"]
NAMES = ["C1\nResource","C2\nEquity","C3\nDemand","C4\nInfra","C5\nPhysical","PAI"]
N = len(COLS)

# ─────────────────────────────────────────────────────────────────────────────
# FIG N04 — Correlation Matrix
# ─────────────────────────────────────────────────────────────────────────────
print("Rendering Fig N04 — Correlation matrix...")

data = pai_df[COLS].values
corr_mat = np.zeros((N, N))
pval_mat = np.zeros((N, N))
for i in range(N):
    for j in range(N):
        r, p = stats.pearsonr(data[:, i], data[:, j])
        corr_mat[i, j] = r
        pval_mat[i, j] = p

fig4, ax = plt.subplots(figsize=(6.5, 5.5), dpi=600, facecolor="white")

# Color map: blue-white-red
cmap = plt.cm.RdBu_r
norm = plt.Normalize(vmin=-1, vmax=1)
im = ax.imshow(corr_mat, cmap=cmap, norm=norm, aspect="auto")

# Annotate cells
for i in range(N):
    for j in range(N):
        r = corr_mat[i, j]
        p = pval_mat[i, j]
        stars = "***" if p < 0.001 else ("**" if p < 0.01 else ("*" if p < 0.05 else ""))
        text_color = "white" if abs(r) > 0.65 else "black"
        ax.text(j, i, f"{r:.2f}{stars}",
                ha="center", va="center",
                fontsize=7, color=text_color, fontweight="bold")

ax.set_xticks(range(N)); ax.set_xticklabels(NAMES, fontsize=7.5)
ax.set_yticks(range(N)); ax.set_yticklabels(NAMES, fontsize=7.5)
ax.tick_params(length=0)

cbar = fig4.colorbar(im, ax=ax, fraction=0.036, pad=0.03)
cbar.set_label("Pearson r", fontsize=7.5)
cbar.ax.tick_params(labelsize=7)

# Significance key moved to the manuscript figure caption (kept out of the image).


# Highlight PAI row/col with border
for spine in ax.spines.values():
    spine.set_edgecolor("#cccccc")

fig4.tight_layout(rect=[0, 0.05, 1, 1])
fig4.savefig(str(figout("corr")), dpi=600, bbox_inches="tight")
save_tiff(fig4, "corr", bbox_inches="tight")   # 1000 dpi TIFF
print(f"  Saved: {figout('corr')}")
plt.close(fig4)

# ─────────────────────────────────────────────────────────────────────────────
# FIG N05 — EWM Weight Bar Chart
# ─────────────────────────────────────────────────────────────────────────────
print("Rendering Fig N05 — EWM weights...")

CRIT_NAMES  = ["C1\nResource", "C2\nEquity", "C3\nDemand", "C4\nInfra", "C5\nPhysical"]
_CK = ["C1_Resource", "C2_Equity", "C3_Demand", "C4_Infra", "C5_Physical"]
EWM_WEIGHTS = [MR["weights_full"][c] for c in _CK]
ENTROPY     = [MR["entropy_full"][c] for c in _CK]
CRIT_COLORS = ["#e6a817","#cc3333","#3377bb","#33aa55","#8855cc"]

fig5, ax = plt.subplots(figsize=(7, 4.5), dpi=600, facecolor="white")

x = np.arange(5)
bars = ax.bar(x, EWM_WEIGHTS, color=CRIT_COLORS, edgecolor="black",
              linewidth=0.6, width=0.55, zorder=3, alpha=0.88)

# Equal weights baseline
ax.axhline(0.20, color="#555555", lw=1.3, linestyle="--", zorder=2,
           label="Equal weight baseline (20%)")

# Weight labels on bars
for bar, w in zip(bars, EWM_WEIGHTS):
    ax.text(bar.get_x() + bar.get_width()/2, w + 0.003,
            f"{w*100:.1f}%", ha="center", va="bottom",
            fontsize=8.5, fontweight="bold")

# Entropy labels inside bars
for bar, e in zip(bars, ENTROPY):
    h = bar.get_height()
    ax.text(bar.get_x() + bar.get_width()/2, h * 0.45,
            f"e = {e:.3f}", ha="center", va="center",
            fontsize=6.5, color="white", fontweight="bold")

ax.set_xticks(x)
ax.set_xticklabels(CRIT_NAMES, fontsize=9)
ax.set_ylabel("EWM Criterion Weight", fontsize=9)
ax.set_ylim(0, max(EWM_WEIGHTS) * 1.18)
ax.yaxis.set_major_formatter(mticker.PercentFormatter(xmax=1, decimals=0))
ax.legend(fontsize=8, loc="upper right", framealpha=0.85)
ax.spines[["top","right"]].set_visible(False)
ax.tick_params(labelsize=8)
ax.grid(axis="y", linestyle=":", alpha=0.5, zorder=0)


fig5.tight_layout()
fig5.savefig(str(figout("weights")), dpi=600, bbox_inches="tight")
save_tiff(fig5, "weights", bbox_inches="tight")   # 1000 dpi TIFF
print(f"  Saved: {figout('weights')}")
plt.close(fig5)

print("=== Fig N04 + N05 COMPLETE ===")
