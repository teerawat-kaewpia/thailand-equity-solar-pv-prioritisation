"""
TEJ Figs 4 and 5: province PAI map and priority-zone map.

TEJ copy of DER\\Scripts\\07_Figures\\fig02_03_pai_zone_maps.py (audit 2026-10-09):
  * B7  colour scale spans the observed PAI range (was fixed at 0.22-0.64, clipping both ends);
  * scale bar drawn as 200 km at its latitude (2.0 degrees of longitude is about 221 km at 5.9 N);
  * north arrow drawn with the letter below the arrow (the glyph overlapped the arrow);
  * no em dashes in figure text, colour-bar label "Province PAI".
Inputs are read from DER (read-only), outputs go to DER_TEJ\\Figures.
"""

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import matplotlib.patches as mpatches
import matplotlib.ticker as ticker
import geopandas as gpd
import fiona
import pandas as pd
import numpy as np
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from _paths import SRC, out_path
from _figures import figout, save_tiff   # single figure registry (Figures/main, Figures/supplementary)
BASE  = SRC                                   # inputs, read-only
PROC  = BASE / "Data" / "14_Processed_90m"
GADM  = BASE / "Data" / "01_Admin_Boundaries" / "gadm41_THA.gpkg"
OUT   = out_path("Figures", "_").parent      # DER_TEJ\\Figures

# ── Load data ─────────────────────────────────────────────────────────────────
print("Loading province boundaries...")
layers = fiona.listlayers(str(GADM))
adm1   = next(l for l in layers if l.endswith("_1"))
prov   = gpd.read_file(str(GADM), layer=adm1)[["GID_1", "NAME_1", "geometry"]].copy()
if prov.crs.to_epsg() != 4326:
    prov = prov.to_crs("EPSG:4326")

pai_df = pd.read_csv(PROC / "province_PAI_summary.csv")
prov   = prov.merge(pai_df, on="NAME_1", how="left")
print(f"  {len(prov)} provinces loaded")

# ── Shared map extent ─────────────────────────────────────────────────────────
XLIM = (97.3, 105.7)
YLIM = (5.5, 20.6)

ZONE_COLORS = {
    1: "#d73027",   # deepest red  = Highest
    2: "#fc8d59",   # orange
    3: "#fee090",   # yellow
    4: "#91bfdb",   # light blue
    5: "#4575b4",   # deep blue   = Lowest
}
# Zone counts and land shares come from the single source of truth so the map
# legend cannot drift from the analysis (they previously did: "29.0%" for a
# Zone 1 that now holds 6 provinces on 4.9% of national land).
import json
MR = json.loads((BASE / "Data" / "master_results.json").read_text(encoding="utf-8"))
_ZW = {1: "Highest", 2: "High", 3: "Medium", 4: "Low", 5: "Lowest"}
ZONE_LABELS = {
    z: f"Zone {z}: {_ZW[z]}  (n={MR['zones'][str(z)]['n']}, "
       f"{MR['zones'][str(z)]['land_pct']:.1f}% land)"
    for z in (1, 2, 3, 4, 5)
}

def add_scalebar(ax, x, y, km=200, label="200 km"):
    import math
    length_deg = km / (111.32 * math.cos(math.radians(y)))
    ax.plot([x, x + length_deg], [y, y], color="black", lw=1.8,
            transform=ax.transData, solid_capstyle="butt")
    ax.plot([x, x], [y, y + 0.08], color="black", lw=1.2, transform=ax.transData)
    ax.plot([x + length_deg, x + length_deg], [y, y + 0.08],
            color="black", lw=1.2, transform=ax.transData)
    ax.text(x + length_deg/2, y + 0.18, label, ha="center", va="bottom",
            fontsize=7, transform=ax.transData)

def add_north(ax, x, y, size=0.6):
    ax.annotate("N", xy=(x, y + size), xytext=(x, y),
                fontsize=9, ha="center", va="top", fontweight="bold",
                arrowprops=dict(arrowstyle="-|>", color="black",
                                lw=1.2, mutation_scale=10))

# ─────────────────────────────────────────────────────────────────────────────
# FIG 2 — PAI Choropleth
# ─────────────────────────────────────────────────────────────────────────────
print("Rendering Fig 2 — PAI map...")
fig2, ax2 = plt.subplots(figsize=(5.5, 8.5), dpi=600,
                          facecolor="white")
ax2.set_aspect("equal")

cmap = plt.cm.YlOrRd
norm = mcolors.Normalize(vmin=float(np.floor(pai_df["PAI"].min() * 100) / 100),
                        vmax=float(np.ceil(pai_df["PAI"].max() * 100) / 100))

prov.plot(ax=ax2, column="PAI", cmap=cmap, norm=norm,
          linewidth=0.25, edgecolor="#aaaaaa")
# Province borders (heavier for region boundaries – skip for simplicity)

ax2.set_xlim(*XLIM)
ax2.set_ylim(*YLIM)
ax2.set_xlabel("Longitude (°E)", fontsize=8)
ax2.set_ylabel("Latitude (°N)", fontsize=8)
ax2.tick_params(labelsize=7)

# Colorbar
sm = plt.cm.ScalarMappable(cmap=cmap, norm=norm)
sm.set_array([])
cbar = plt.colorbar(sm, ax=ax2, orientation="vertical",
                    fraction=0.035, pad=0.02, shrink=0.65)
cbar.set_label("Province PAI", fontsize=7.5)
cbar.ax.tick_params(labelsize=7)

# Highlight top-3 and bottom-3 provinces
top3 = pai_df.nlargest(3, "PAI")["NAME_1"].tolist()
bot3 = pai_df.nsmallest(3, "PAI")["NAME_1"].tolist()
# Per-province label offsets to avoid crowding in central Thailand
_offsets = {
    "Bangkok Metropolis": (18, -10),
    "Samut Sakhon":       (-22, -8),
    "Samut Prakan":       (20,  -6),
    "Nonthaburi":         (-20,  8),
    "Pathum Thani":       (18,  10),
}
for _, row in prov[prov["NAME_1"].isin(top3 + bot3)].iterrows():
    c = row.geometry.centroid
    color = "#cc0000" if row["NAME_1"] in top3 else "#0033aa"
    ax2.plot(c.x, c.y, "o", ms=2.5, color=color, zorder=5)
    ox, oy = _offsets.get(row["NAME_1"], (8, 6))
    ax2.annotate(row["NAME_1"],
                 xy=(c.x, c.y), xytext=(ox, oy),
                 textcoords="offset points",
                 fontsize=5.5, color=color, zorder=6,
                 # white halo: labels sat unreadable on dark fills (Kalasin) and across borders (Loei), check 2026-10-15
                 path_effects=[__import__("matplotlib.patheffects", fromlist=["withStroke"]).withStroke(linewidth=1.6, foreground="white")],
                 arrowprops=dict(arrowstyle="-", color=color,
                                 lw=0.4, relpos=(0, 0)))

# Legend for highlighted points
from matplotlib.lines import Line2D
legend_els = [
    Line2D([0],[0], marker="o", color="w", markerfacecolor="#cc0000",
           markersize=5, label="Top 3 provinces"),
    Line2D([0],[0], marker="o", color="w", markerfacecolor="#0033aa",
           markersize=5, label="Bottom 3 provinces"),
]
ax2.legend(handles=legend_els, fontsize=6.5, loc="lower right",
           framealpha=0.85, edgecolor="#cccccc")

add_scalebar(ax2, 98.0, 5.9)
add_north(ax2, 104.8, 18.5)

ax2.spines[["top","right"]].set_visible(False)

plt.tight_layout()
fig2.savefig(str(figout("pai-map")), dpi=600, bbox_inches="tight")
save_tiff(fig2, "pai-map", bbox_inches="tight")   # 1000 dpi TIFF
print(f"  Saved: {figout('pai-map')}")
plt.close(fig2)

# ─────────────────────────────────────────────────────────────────────────────
# FIG 3 — Zone map
# ─────────────────────────────────────────────────────────────────────────────
print("Rendering Fig 3 — Zone map...")
prov["zone_color"] = prov["dominant_zone"].map(ZONE_COLORS)

fig3, ax3 = plt.subplots(figsize=(5.5, 8.5), dpi=600,
                          facecolor="white")
ax3.set_aspect("equal")

for zone in [1, 2, 3, 4, 5]:
    sub = prov[prov["dominant_zone"] == zone]
    if len(sub):
        sub.plot(ax=ax3, color=ZONE_COLORS[zone],
                 linewidth=0.25, edgecolor="#aaaaaa")

ax3.set_xlim(*XLIM)
ax3.set_ylim(*YLIM)
ax3.set_xlabel("Longitude (°E)", fontsize=8)
ax3.set_ylabel("Latitude (°N)", fontsize=8)
ax3.tick_params(labelsize=7)

# Legend
patches = [mpatches.Patch(color=ZONE_COLORS[z], label=ZONE_LABELS[z])
           for z in [1, 2, 3, 4, 5]]
ax3.legend(handles=patches, fontsize=6.5, loc="lower right",
           bbox_to_anchor=(1.0, 0.16),
           framealpha=0.90, edgecolor="#cccccc",
           title="Priority zone", title_fontsize=7)

add_scalebar(ax3, 98.0, 5.9)
add_north(ax3, 104.8, 18.5)

ax3.spines[["top","right"]].set_visible(False)

plt.tight_layout()
fig3.savefig(str(figout("zones")), dpi=600, bbox_inches="tight")
save_tiff(fig3, "zones", bbox_inches="tight")   # 1000 dpi TIFF
print(f"  Saved: {figout('zones')}")
plt.close(fig3)

print("=== Fig 2 + 3 COMPLETE ===")
