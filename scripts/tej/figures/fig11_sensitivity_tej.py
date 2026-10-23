"""
Fig N09 — Province PAI Ranking (all 77)
Fig N10 — Sensitivity Analysis (EWM vs Equal vs Expert)
========================================================
Output: Fig09_Province_Ranking.png, Fig11_Sensitivity.png  (600 dpi)
"""

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
import pandas as pd
from pathlib import Path
import os

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from _paths import SRC, out_path
from _sens import SENS_RHO   # full-precision rho (no double rounding)
from _figures import figout, save_tiff   # single figure registry (Figures/main, Figures/supplementary)
BASE = SRC                                    # inputs, read-only
PROC = BASE / "Data" / "14_Processed_90m"
OUT  = out_path("Figures", "_").parent      # DER_TEJ\Figures

pai_df  = pd.read_csv(PROC / "province_PAI_summary.csv")
pai_df["PAI"] = pai_df.NAME_1.map(pd.read_csv(PROC / "province_criteria_normalised.csv").set_index("NAME_1").PAI)   # full precision, summary PAI is 4 dp
sens_df = pd.read_csv(PROC / "sensitivity_analysis.csv")

import json
MR = json.loads((BASE / "Data" / "master_results.json").read_text(encoding="utf-8"))

ZONE_COLORS = {1:"#d73027", 2:"#fc8d59", 3:"#fee090", 4:"#91bfdb", 5:"#4575b4"}
ZONE_LABELS = {1:"Zone 1 (Highest)", 2:"Zone 2 (High)",
               3:"Zone 3 (Medium)", 4:"Zone 4 (Low)", 5:"Zone 5 (Lowest)"}

# ─────────────────────────────────────────────────────────────────────────────
# FIG N09 — Province Ranking
# ─────────────────────────────────────────────────────────────────────────────
print("Rendering Fig N09 — Province ranking...")

ranked = pai_df.sort_values("rank").reset_index(drop=True)

# Two side-by-side columns rather than one 77-row column: a single column has an
# aspect ratio of ~2.5:1, which the page-height cap shrinks to ~8.8 cm wide and
# renders the province labels illegible. Split at the midpoint so the panel is
# roughly square and can be placed at full text width.
half  = (len(ranked) + 1) // 2
parts = [ranked.iloc[:half].reset_index(drop=True),
         ranked.iloc[half:].reset_index(drop=True)]

fig9, axes = plt.subplots(1, 2, figsize=(7.4, 6.4), dpi=600, facecolor="white")
fig9.subplots_adjust(left=0.155, right=0.985, top=0.965, bottom=0.075, wspace=0.42)

PAI_MIN, PAI_MAX = 0.15, 0.78

for ax, part in zip(axes, parts):
    y_pos  = np.arange(len(part))
    colors = [ZONE_COLORS[z] for z in part["dominant_zone"]]
    ax.barh(y_pos, part["PAI"], height=0.74,
            color=colors, edgecolor="white", linewidth=0.25, zorder=3)

    # rank number prefixed to the province name so the two columns read in order
    ax.set_yticks(y_pos)
    ax.set_yticklabels([f"{r}. {n}" for r, n in zip(part["rank"], part["NAME_1"])],
                       fontsize=5.4)
    ax.invert_yaxis()

    for i, val in enumerate(part["PAI"]):
        ax.text(val + 0.008, i, f"{val:.3f}",
                va="center", fontsize=4.6, color="#333333")

    # dashed rule wherever the zone changes within this column
    zc = part["dominant_zone"].to_numpy()
    for i in range(1, len(zc)):
        if zc[i] != zc[i - 1]:
            ax.axhline(i - 0.5, color="#666666", lw=0.6, linestyle="--", zorder=2)
            # label sits just below the rule at the right margin, on a white
            # patch, so it never overprints the rule or the province labels
            ax.text(PAI_MAX - 0.008, i - 0.35, ZONE_LABELS[zc[i]],
                    fontsize=4.8, color="#666666", ha="right", va="top", zorder=4,
                    bbox=dict(boxstyle="square,pad=0.15", fc="white",
                              ec="none", alpha=0.85))

    ax.set_xlabel("PAI Score", fontsize=7.5)
    ax.set_xlim(PAI_MIN, PAI_MAX)
    ax.spines[["top", "right", "left"]].set_visible(False)
    ax.tick_params(axis="x", labelsize=6.5)
    ax.tick_params(axis="y", length=0)
    ax.grid(axis="x", linestyle=":", alpha=0.5, zorder=0)

patches = [mpatches.Patch(color=ZONE_COLORS[z], label=ZONE_LABELS[z])
           for z in [1, 2, 3, 4, 5]]
axes[1].legend(handles=patches, fontsize=5.4, loc="lower right",
               framealpha=0.90, edgecolor="#cccccc")

fig9.savefig(str(figout("ranking")), dpi=600, bbox_inches="tight")
save_tiff(fig9, "ranking", bbox_inches="tight")   # 1000 dpi TIFF
print(f"  Saved: {figout('ranking')}")
plt.close(fig9)

# ─────────────────────────────────────────────────────────────────────────────
# FIG N10 — Sensitivity Analysis (scatter rank comparison)
# ─────────────────────────────────────────────────────────────────────────────
print("Rendering Fig N10 — Sensitivity analysis...")

# Merge zone colors into sensitivity df
sens_df = sens_df.merge(pai_df[["NAME_1","dominant_zone"]], on="NAME_1", how="left")
colors_s = [ZONE_COLORS[z] for z in sens_df["dominant_zone"]]
sizes    = np.abs(sens_df["rank_diff_Equal"].fillna(0)) * 4 + 15

fig10, axes = plt.subplots(1, 2, figsize=(11, 5), dpi=600, facecolor="white")
fig10.subplots_adjust(wspace=0.32, top=0.96, bottom=0.12)

# rho values read from the single source of truth, not hand-typed
scenarios = [
    ("rank_Equal",  "rank_diff_Equal",  "Equal Weights (1/5 each)",
     f"ρ = {SENS_RHO['equal']:.3f}"),
    ("rank_Expert", "rank_diff_Expert", "Expert Weights (equity-first)",
     f"ρ = {SENS_RHO['expert']:.3f}"),
]

for ax, (rank_col, diff_col, label, rho) in zip(axes, scenarios):
    sc = ax.scatter(sens_df["rank_EWM"], sens_df[rank_col],
                    c=colors_s, s=sizes, alpha=0.80,
                    edgecolors="black", linewidths=0.3, zorder=3)

    # Diagonal line
    ax.plot([1, 77], [1, 77], color="#888888", lw=0.9,
            linestyle="--", zorder=2, label="No change")

    # Highlight large shifters (|diff| > 10)
    large = sens_df[np.abs(sens_df[diff_col].fillna(0)) > 10]
    placed = []
    for _, row in large.sort_values(["rank_EWM", rank_col]).iterrows():
        x0, y0 = row["rank_EWM"], row[rank_col]
        tx, ty = x0 + 0.8, y0 + 0.8
        wid = 0.55 * len(row["NAME_1"])            # label width in rank units at fontsize 4.5
        while any(abs(ty - py) < 1.6 and tx < px + pw and px < tx + wid for px, py, pw in placed):
            ty += 1.6
        placed.append((tx, ty, wid))
        ax.annotate(row["NAME_1"],
                    xy=(x0, y0), xytext=(tx, ty), textcoords="data",
                    fontsize=4.5, color="#333333", va="bottom",
                    arrowprops=dict(arrowstyle="-", lw=0.3, color="#aaaaaa"))

    ax.set_xlabel("EWM Rank", fontsize=8)
    ax.set_ylabel(f"{label} Rank", fontsize=8)
    ax.set_xlim(0, 78); ax.set_ylim(0, 78)
    ax.spines[["top","right"]].set_visible(False)
    ax.tick_params(labelsize=7)
    ax.grid(linestyle=":", alpha=0.4, zorder=0)

    # Stat box
    ax.text(0.97, 0.05, f"Spearman {rho}\nn = 77 provinces",
            transform=ax.transAxes, ha="right", va="bottom",
            fontsize=7.5, color="#333333",
            bbox=dict(boxstyle="round,pad=0.3", facecolor="white",
                      edgecolor="#cccccc", lw=0.7))

    ax.set_title("ab"[list(axes).index(ax)], fontsize=10, pad=4, fontweight="bold")   # panel label, not a title
    ax.legend(fontsize=7, loc="upper left")

# Zone legend
patches = [mpatches.Patch(color=ZONE_COLORS[z], label=ZONE_LABELS[z])
           for z in [1,2,3,4,5]]
fig10.legend(handles=patches, fontsize=6.5, loc="lower center",
             ncol=5, framealpha=0.90, edgecolor="#cccccc",
             bbox_to_anchor=(0.5, -0.01))


fig10.savefig(str(figout("sens")), dpi=600, bbox_inches="tight")
save_tiff(fig10, "sens", bbox_inches="tight")   # 1000 dpi TIFF
print(f"  Saved: {figout('sens')}")
plt.close(fig10)

print("=== Fig N09 + N10 COMPLETE ===")
