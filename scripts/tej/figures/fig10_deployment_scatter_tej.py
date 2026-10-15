"""
Fig N11 — External Validation Scatter: PAI vs OSM Solar Plants
==============================================================
Output: Fig10_Validation_Scatter.png  (600 dpi)
"""

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patheffects as pe
import numpy as np
import pandas as pd
from scipy import stats
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from _paths import SRC, BASE as TEJ, out_path
from _figures import figout, save_tiff   # single figure registry (Figures/main, Figures/supplementary)
BASE = SRC                       # inputs: shared DER data, read-only
PROC = BASE / "Data" / "14_Processed_90m"
OUT  = out_path("Figures", "_").parent   # outputs: DER_TEJ\Figures

osm = pd.read_csv(PROC / "validation_solar_osm.csv")

ZONE_COLORS = {1:"#d73027", 2:"#fc8d59", 3:"#fee090", 4:"#91bfdb", 5:"#4575b4"}

fig, axes = plt.subplots(1, 2, figsize=(11, 5), dpi=600, facecolor="white")
fig.subplots_adjust(wspace=0.32, top=0.96, bottom=0.12)

# ── Panel A: PAI vs solar count (all 77) ─────────────────────────────────────
ax = axes[0]
colors = [ZONE_COLORS[z] for z in osm["dominant_zone"]]

# Jitter zero counts slightly for visibility
jitter_y = osm["solar_count"].copy().astype(float)
zero_mask = jitter_y == 0
jitter_y[zero_mask] += np.random.default_rng(42).uniform(0, 0.25, zero_mask.sum())

sc = ax.scatter(osm["PAI"], jitter_y,
                c=colors, s=40, alpha=0.80,
                edgecolors="black", linewidths=0.35, zorder=3)

# Spearman
rho, pval = stats.spearmanr(osm["PAI"], osm["solar_count"])
ax.text(0.03, 0.97,
        f"Spearman ρ = {rho:.3f}\np = {pval:.3f}\nn = 77".replace("-", "−"),   # typographic minus, as on the axes
        transform=ax.transAxes, ha="left", va="top", fontsize=7.5,
        bbox=dict(boxstyle="round,pad=0.3", facecolor="white",
                  edgecolor="#cccccc", lw=0.7, alpha=0.95))

# Label only the most notable provinces (top count threshold)
_lab = osm[osm["solar_count"] >= 13].sort_values(["solar_count", "PAI"])
_rank = _lab.groupby("solar_count").cumcount()
for (_, row), k in zip(_lab.iterrows(), _rank):
    ax.annotate(row["NAME_1"],
                xy=(row["PAI"], row["solar_count"]),
                xytext=(6, 4 + 10 * k), textcoords="offset points", fontsize=6,
                arrowprops=dict(arrowstyle="-", lw=0.4, color="#555555") if k else None,
                path_effects=[pe.withStroke(linewidth=1.5, foreground="white")])

ax.set_xlabel("Province-level PAI Score", fontsize=8.5)
ax.set_ylabel("OSM Solar Plant Count", fontsize=8.5)
ax.set_title("a", fontsize=10, pad=4, fontweight="bold", loc="center")
ax.spines[["top","right"]].set_visible(False)
ax.tick_params(labelsize=7.5)
ax.grid(linestyle=":", alpha=0.4, zorder=0)

# ── Panel B: Box plot by zone ─────────────────────────────────────────────────
ax = axes[1]
zone_data = [osm[osm["dominant_zone"] == z]["solar_count"].values for z in [1,2,3,4,5]]
bp = ax.boxplot(zone_data, patch_artist=True, widths=0.55,
                medianprops=dict(color="black", lw=1.5),
                whiskerprops=dict(lw=0.8), capprops=dict(lw=0.8),
                flierprops=dict(marker="o", markersize=3, alpha=0.6))

for patch, zone in zip(bp["boxes"], [1,2,3,4,5]):
    patch.set_facecolor(ZONE_COLORS[zone])
    patch.set_alpha(0.75)

# Overlay jittered points
np.random.seed(42)
for i, (zone, d) in enumerate(zip([1,2,3,4,5], zone_data), start=1):
    jx = np.random.uniform(i - 0.18, i + 0.18, len(d))
    ax.scatter(jx, d, color=ZONE_COLORS[zone], s=14, alpha=0.7,
               edgecolors="#333333", linewidths=0.3, zorder=4)

ax.set_xticklabels(["Zone 1\n(Highest)","Zone 2\n(High)","Zone 3\n(Medium)",
                     "Zone 4\n(Low)","Zone 5\n(Lowest)"], fontsize=7.5)
ax.set_ylabel("OSM Solar Plant Count", fontsize=8.5)
ax.set_title("b", fontsize=10, pad=4, fontweight="bold", loc="center")
ax.spines[["top","right"]].set_visible(False)
ax.tick_params(axis="y", labelsize=7.5)
ax.grid(axis="y", linestyle=":", alpha=0.4, zorder=0)


fig.savefig(str(figout("deployment")), dpi=600, bbox_inches="tight")
save_tiff(fig, "deployment", bbox_inches="tight")   # 1000 dpi TIFF
fig.savefig(str(figout("deployment", "pdf")), bbox_inches="tight")   # vector (TEJ artwork)
print(f"Saved: {figout('deployment')}")
plt.close()
print("=== Fig N11 COMPLETE ===")
