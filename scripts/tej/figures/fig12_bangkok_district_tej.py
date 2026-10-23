"""
Fig 14 — Bangkok 50-khet district PAI choropleth + priority zones
=================================================================
District-scale demonstration (RQ4). Two panels:
  (a) District PAI choropleth (continuous)
  (b) K-means priority zones (5 classes)
Notable energy-poor / high-yield khet labelled.
Output: Figures/supplementary/FigS12_Bangkok_District.png (600 dpi)
"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import matplotlib.patches as mpatches
import matplotlib.patheffects as pe
import geopandas as gpd
import fiona
import pandas as pd
from pathlib import Path
import os
from PIL import Image

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from _paths import SRC, out_path
from _figures import figout, save_tiff   # single figure registry (Figures/main, Figures/supplementary)
BASE = SRC                                    # inputs, read-only
GADM = BASE / "Data" / "01_Admin_Boundaries" / "gadm41_THA.gpkg"
CSV  = BASE / "Data" / "14_Processed_Bangkok" / "bangkok_district_PAI_vuln.csv"
OUT  = out_path("Figures", "_").parent      # DER_TEJ\Figures

ZONE_COLORS = {1: "#d73027", 2: "#fc8d59", 3: "#fee090", 4: "#91bfdb", 5: "#4575b4"}

# GADM NAME_2 -> standard romanisation used in the manuscript text (consistency)
NAME_STD = {
    "Din Dang": "Din Daeng", "Wattana": "Watthana", "Bang Su": "Bang Sue",
    "Bang Plad": "Bang Phlat", "Bangkhuntien": "Bang Khun Thian",
    "Pom Pram Sattru": "Pom Prap Sattru Phai", "Bung Kum": "Bueng Kum",
    "Samphantawong": "Samphanthawong",
}

# ── Load geometries + results ──────────────────────────────────────────────────
adm2 = next(l for l in fiona.listlayers(str(GADM)) if l.endswith("_2"))
khet = gpd.read_file(str(GADM), layer=adm2)
khet = khet[khet["NAME_1"] == "Bangkok Metropolis"][["NAME_2", "geometry"]].to_crs("EPSG:4326")
df = pd.read_csv(CSV).rename(columns={"PAI_vuln": "PAI", "zone_vuln": "zone", "rank_vuln": "rank"})
khet = khet.merge(df, on="NAME_2", how="left")
print(f"Merged {khet['PAI'].notna().sum()}/50 khet")

XLIM = (100.31, 100.95)
YLIM = (13.48, 13.96)

def add_scalebar(ax, x, y, length_deg=0.09, label="10 km"):
    ax.plot([x, x + length_deg], [y, y], color="black", lw=1.6, solid_capstyle="butt")
    ax.text(x + length_deg / 2, y + 0.006, label, ha="center", va="bottom", fontsize=6)

def add_north(ax, x, y, size=0.03):
    ax.annotate("N", xy=(x, y + size), xytext=(x, y), fontsize=8, ha="center",
                va="bottom", fontweight="bold",
                arrowprops=dict(arrowstyle="-|>", color="black", lw=1.0, mutation_scale=8))

fig, (axA, axB) = plt.subplots(1, 2, figsize=(13, 6.5), dpi=600, facecolor="white")

# ── Panel A: PAI choropleth ────────────────────────────────────────────────────
cmap = plt.cm.YlOrRd
norm = mcolors.Normalize(vmin=khet["PAI"].min(), vmax=khet["PAI"].max())
khet.plot(ax=axA, column="PAI", cmap=cmap, norm=norm,
          linewidth=0.4, edgecolor="#888888")
axA.set_xlim(*XLIM); axA.set_ylim(*YLIM); axA.set_aspect("equal")
axA.set_xlabel("Longitude (°E)", fontsize=8); axA.set_ylabel("Latitude (°N)", fontsize=8)
axA.tick_params(labelsize=6.5)
sm = plt.cm.ScalarMappable(cmap=cmap, norm=norm); sm.set_array([])
cbar = plt.colorbar(sm, ax=axA, fraction=0.04, pad=0.02, shrink=0.7)
cbar.set_label("District PAI", fontsize=7.5); cbar.ax.tick_params(labelsize=6.5)

# label top-3 and bottom-3 khet
lab = pd.concat([khet.nlargest(3, "PAI"), khet.nsmallest(3, "PAI")])
for _, r in lab.iterrows():
    c = r.geometry.centroid
    col = "#7f0000" if r["PAI"] >= khet["PAI"].median() else "#08306b"
    axA.annotate(NAME_STD.get(r["NAME_2"], r["NAME_2"]), xy=(c.x, c.y), fontsize=5.0, ha="center", color=col,
                 fontweight="bold",
                 path_effects=[pe.withStroke(linewidth=1.4, foreground="white")])
add_scalebar(axA, 100.34, 13.50); add_north(axA, 100.91, 13.90)
axA.set_title("a", fontsize=10, fontweight="bold", pad=5)
axA.spines[["top", "right"]].set_visible(False)

# ── Panel B: zone map ──────────────────────────────────────────────────────────
for z in [1, 2, 3, 4, 5]:
    sub = khet[khet["zone"] == z]
    if len(sub):
        sub.plot(ax=axB, color=ZONE_COLORS[z], linewidth=0.4, edgecolor="#888888")
axB.set_xlim(*XLIM); axB.set_ylim(*YLIM); axB.set_aspect("equal")
axB.set_xlabel("Longitude (°E)", fontsize=8); axB.set_ylabel("Latitude (°N)", fontsize=8)
axB.tick_params(labelsize=6.5)
zone_n = khet["zone"].value_counts().to_dict()
patches = [mpatches.Patch(color=ZONE_COLORS[z],
           label=f"Zone {z}  (n={int(zone_n.get(z,0))})") for z in [1, 2, 3, 4, 5]]
axB.legend(handles=patches, fontsize=6.5, loc="lower right", framealpha=0.9,
           edgecolor="#cccccc", title="Priority zone", title_fontsize=7)
add_scalebar(axB, 100.34, 13.50); add_north(axB, 100.91, 13.90)
axB.set_title("b", fontsize=10, fontweight="bold", pad=5)
axB.spines[["top", "right"]].set_visible(False)

plt.tight_layout()
png = figout("S-district")
fig.savefig(str(png), dpi=600, bbox_inches="tight")
save_tiff(fig, "S-district", bbox_inches="tight")   # 1000 dpi TIFF
plt.close(fig)
print(f"Saved: {png}")

print("=== Fig 14 COMPLETE ===")
