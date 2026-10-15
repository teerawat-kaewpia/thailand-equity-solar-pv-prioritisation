"""
Fig 4 — LISA Spatial Autocorrelation Cluster Map
=================================================
Province-level High-High / Low-Low / HL / LH / ns clusters.
Output: Fig08_LISA_Map.png  (600 dpi)
"""

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.patheffects as pe
import geopandas as gpd
import fiona
import pandas as pd
from pathlib import Path
import os

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from _paths import SRC, out_path
from _figures import figout, save_tiff   # single figure registry (Figures/main, Figures/supplementary)
BASE = SRC                                    # inputs, read-only
PROC = BASE / "Data" / "14_Processed_90m"
GADM = BASE / "Data" / "01_Admin_Boundaries" / "gadm41_THA.gpkg"
OUT  = out_path("Figures", "_").parent      # DER_TEJ\Figures

import json
MR = json.loads((BASE / "Data" / "master_results.json").read_text(encoding="utf-8"))
MI = MR["morans_I"]

# ── palette ───────────────────────────────────────────────────────────────────
LISA_COLORS = {
    "HH": "#d73027",      # High-High  (red)
    "LL": "#4575b4",      # Low-Low    (blue)
    "HL": "#f46d43",      # High-Low   (orange)
    "LH": "#abd9e9",      # Low-High   (light blue)
    "ns": "#e8e8e8",      # not significant (light grey)
}
LISA_LABELS = {
    "HH": "High-High cluster",
    "LL": "Low-Low cluster",
    "HL": "High-Low outlier",
    "LH": "Low-High outlier",
    "ns": "Not significant",
}

# ── Load ──────────────────────────────────────────────────────────────────────
print("Loading province boundaries...")
layers = fiona.listlayers(str(GADM))
adm1   = next(l for l in layers if l.endswith("_1"))
prov   = gpd.read_file(str(GADM), layer=adm1)[["GID_1", "NAME_1", "geometry"]].copy()
if prov.crs.to_epsg() != 4326:
    prov = prov.to_crs("EPSG:4326")

lisa_df = pd.read_csv(PROC / "province_LISA.csv")
prov    = prov.merge(lisa_df, on="NAME_1", how="left")
prov["LISA_type"] = prov["LISA_type"].fillna("ns")

counts = prov["LISA_type"].value_counts()
print("LISA type distribution:")
print(counts)

# ── Plot ──────────────────────────────────────────────────────────────────────
XLIM = (97.3, 105.7)
YLIM = (5.5, 20.6)

fig, ax = plt.subplots(figsize=(5.5, 8.5), dpi=600, facecolor="white")
ax.set_aspect("equal")

for lt in ["ns", "LH", "HL", "LL", "HH"]:   # draw significant on top
    sub = prov[prov["LISA_type"] == lt]
    if len(sub):
        sub.plot(ax=ax, color=LISA_COLORS[lt],
                 linewidth=0.3, edgecolor="#999999")

# Annotate province names for significant clusters
# Skip tiny central provinces (area < 0.25 sq-deg within the Bangkok metro band)
# to prevent label collision; replaced by a single cluster label below.
sig = prov[prov["LISA_type"].isin(["HH", "LL", "HL", "LH"])]
for _, row in sig.iterrows():
    cx = row.geometry.centroid.x
    cy = row.geometry.centroid.y
    ax.text(cx, cy, row["NAME_1"],
            ha="center", va="center", fontsize=3.8,
            color="#111111", fontweight="bold",
            path_effects=[pe.withStroke(linewidth=1.8, foreground="white")])


# Moran's I annotation
ax.text(0.97, 0.97,
        f"Global Moran's I = {MI['I']:.3f}\nz = {MI['z']:.2f},  "
        f"permutation p = {MI['p']:.3f}\n"
        f"({MI['permutations']} permutations, Queen contiguity)",
        transform=ax.transAxes, ha="right", va="top",
        fontsize=6.5, color="#333333",
        bbox=dict(boxstyle="round,pad=0.3", facecolor="white",
                  edgecolor="#cccccc", linewidth=0.7, alpha=0.9))

ax.set_xlim(*XLIM)
ax.set_ylim(*YLIM)
ax.set_xlabel("Longitude (°E)", fontsize=8)
ax.set_ylabel("Latitude (°N)", fontsize=8)
ax.tick_params(labelsize=7)

# Legend
patches = []
for lt in ["HH", "LL", "HL", "LH", "ns"]:
    n = counts.get(lt, 0)
    patches.append(mpatches.Patch(color=LISA_COLORS[lt],
                                  label=f"{LISA_LABELS[lt]}  (n={n})"))
ax.legend(handles=patches, fontsize=6.5, loc="lower right",
          bbox_to_anchor=(1.0, 0.18),
          framealpha=0.90, edgecolor="#cccccc",
          title=("LISA cluster type (unadjusted p < 0.05)\n"
                 + (f"Exploratory. None survives FDR correction" if MR["lisa_fdr"]["n_fdr_sig"] == 0
                    else f"{MR['lisa_fdr']['n_fdr_sig']} survive FDR correction")),
          title_fontsize=7)

# Scale bar
import math
_dlon = 200.0 / (111.32 * math.cos(math.radians(5.9)))     # 200 km at 5.9 N
ax.plot([98.0, 98.0 + _dlon], [5.9, 5.9], color="black", lw=1.8, solid_capstyle="butt")
ax.text(98.0 + _dlon / 2, 6.10, "200 km", ha="center", fontsize=7)

# North arrow
ax.annotate("N", xy=(104.8, 19.1), xytext=(104.8, 18.5),
            fontsize=9, ha="center", va="top", fontweight="bold",
            arrowprops=dict(arrowstyle="-|>", color="black",
                            lw=1.2, mutation_scale=10))

ax.spines[["top","right"]].set_visible(False)

plt.tight_layout()
fig.savefig(str(figout("lisa")), dpi=600, bbox_inches="tight")
save_tiff(fig, "lisa", bbox_inches="tight")   # 1000 dpi TIFF
print(f"Saved: {figout('lisa')}")
plt.close(fig)
print("=== Fig 4 COMPLETE ===")
