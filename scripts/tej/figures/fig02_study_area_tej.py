"""
Fig N02 — Study Area: Thailand with SE Asia context
====================================================
Output: Fig02_Study_Area.png  (600 dpi)
"""

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.patheffects as pe
import geopandas as gpd
import fiona
import pandas as pd
import numpy as np
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from _paths import SRC, BASE as TEJ, out_path
from _figures import figout, save_tiff   # single figure registry (Figures/main, Figures/supplementary)
BASE = SRC                       # inputs: shared DER data, read-only
GADM = BASE / "Data" / "01_Admin_Boundaries" / "gadm41_THA.gpkg"
NE   = BASE / "Data" / "01_Admin_Boundaries" / "ne_10m_admin0_countries.zip"
OUT  = out_path("Figures", "_").parent   # outputs: DER_TEJ\Figures

# ── Load data ─────────────────────────────────────────────────────────────────
print("Loading province boundaries...")
layers = fiona.listlayers(str(GADM))
adm1   = next(l for l in layers if l.endswith("_1"))
adm0   = next(l for l in layers if l.endswith("_0"))
prov   = gpd.read_file(str(GADM), layer=adm1)[["NAME_1", "geometry"]].copy()
thai   = gpd.read_file(str(GADM), layer=adm0)[["geometry"]].copy()
if prov.crs.to_epsg() != 4326:
    prov  = prov.to_crs("EPSG:4326")
    thai  = thai.to_crs("EPSG:4326")

# Load world countries
print("Loading world countries...")
world = gpd.read_file(str(NE))
if world.crs.to_epsg() != 4326:
    world = world.to_crs("EPSG:4326")

# SE Asia extent
XLIM = (97.0, 106.0)   # Thailand bbox 97.35-105.64 E plus a small margin (TEJ map policy)
YLIM = (5.3,  20.8)    # Thailand bbox 5.62-20.46 N plus a small margin
sea = world.cx[XLIM[0]:XLIM[1], YLIM[0]:YLIM[1]].copy()

# ── Thailand region classification ────────────────────────────────────────────
# Six regions, the same map the scenarios use (DER maup_analysis.py REGION). The earlier
# five-region list here misspelt "Chonburi" (GADM: "Chon Buri") and had no West (audit M3).
import ast
_src = (SRC / "Scripts" / "06_Priority_Areas" / "maup_analysis.py").read_text(encoding="utf-8")
_node = next(n for n in ast.parse(_src).body
             if isinstance(n, ast.Assign) and getattr(n.targets[0], "id", "") == "REGION")
P2R = {p: r for r, ps in ast.literal_eval(_node.value).items() for p in ps}


def get_region(name):
    return P2R[name]

prov["region"] = prov["NAME_1"].map(get_region)
assert prov["region"].nunique() == 6 and len(prov) == 77

REGION_COLORS = {
    "North":     "#4393c3",
    "Northeast": "#d6604d",
    "Central":   "#74c476",
    "East":      "#fdae61",
    "West":      "#d9c27a",
    "South":     "#9970ab",
}
prov["color"] = prov["region"].map(REGION_COLORS)

# ── Figure ────────────────────────────────────────────────────────────────────
fig, ax = plt.subplots(figsize=(8, 9), dpi=600, facecolor="white")
ax.set_aspect("equal")

# Background sea color
fig.patch.set_facecolor("#d6eaf8")
ax.set_facecolor("#d6eaf8")

# Surrounding countries
# exclude Thailand by name: the earlier "does not intersect Thailand" test also dropped every
# bordering country (Myanmar, Laos, Cambodia, Malaysia), so their land was drawn as sea (check 2026-10-15)
sea_no_thai = sea[sea["ADMIN"] != "Thailand"]
assert {"Myanmar", "Laos", "Cambodia", "Malaysia"} <= set(sea_no_thai["ADMIN"])
sea_no_thai.plot(ax=ax, color="#e8e8e8", edgecolor="#bbbbbb", linewidth=0.4)

# Thailand provinces by region
for region, color in REGION_COLORS.items():
    sub = prov[prov["region"] == region]
    if len(sub):
        sub.plot(ax=ax, color=color, edgecolor="#ffffff", linewidth=0.25, alpha=0.85)

# Thailand outer boundary
thai.boundary.plot(ax=ax, color="#333333", linewidth=0.8)

# Country name labels (neighboring countries)
COUNTRY_LABELS = {          # only labels that fall inside the cropped extent
    "Myanmar":   (97.5,  19.5),
    "Laos":      (103.5, 18.5),
    "Cambodia":  (104.5, 12.5),
    "Malaysia":  (101.9,  5.55),
}
for name, (lx, ly) in COUNTRY_LABELS.items():
    ax.text(lx, ly, name, ha="center", va="center",
            fontsize=6.5, color="#555555", style="italic",
            path_effects=[pe.withStroke(linewidth=1.5, foreground="#e8e8e8")])

# Water body labels
ax.text(100.8,  9.5, "Gulf of\nThailand", ha="center", va="center",
        fontsize=6, color="#2980b9", style="italic")
ax.text(97.8,  10.5, "Andaman\nSea", ha="center", va="center",
        fontsize=6, color="#2980b9", style="italic")

# Key city markers
CITIES = {
    "Bangkok★":       (100.50, 13.75),
    "Chiang Mai":     (98.99,  18.79),
    "Khon Kaen":      (102.83, 16.43),
    "Nakhon\nRatchasima": (102.10, 14.98),
    "Phuket":         (98.39,   7.88),
    "Hat Yai":        (100.47,  7.00),
}
for city, (cx, cy) in CITIES.items():
    marker = "*" if "★" in city else "o"
    ms = 5 if "★" in city else 3
    clabel = city.replace("★","")
    ax.plot(cx, cy, marker, ms=ms, color="#111111",
            zorder=6, markeredgecolor="white", markeredgewidth=0.4)
    ax.annotate(clabel, xy=(cx, cy), xytext=(4, 4),
                textcoords="offset points", fontsize=5.5, color="#111111",
                path_effects=[pe.withStroke(linewidth=1.2, foreground="white")])

ax.set_xlim(*XLIM)
ax.set_ylim(*YLIM)
ax.set_xlabel("Longitude (°E)", fontsize=8)
ax.set_ylabel("Latitude (°N)", fontsize=8)
ax.tick_params(labelsize=7)

# Region legend
patches = [mpatches.Patch(color=REGION_COLORS[r], label=r)
           for r in ["North","Northeast","Central","East","West","South"]]
ax.legend(handles=patches, fontsize=6.5, loc="lower right",
          framealpha=0.90, edgecolor="#cccccc",
          title="Administrative Region", title_fontsize=7)

# Scale bar
import math
_sb_lat = 6.3
_sb_len = 200.0 / (111.32 * math.cos(math.radians(_sb_lat)))   # degrees of longitude for 200 km
ax.plot([97.3, 97.3 + _sb_len], [_sb_lat, _sb_lat], color="black", lw=2.0, solid_capstyle="butt")
ax.text(97.3 + _sb_len / 2, _sb_lat + 0.25, "200 km", ha="center", fontsize=7)

# North arrow
ax.annotate("N", xy=(105.5, 20.55), xytext=(105.5, 20.0),
            fontsize=9, ha="center", va="bottom", fontweight="bold",
            arrowprops=dict(arrowstyle="-|>", color="black",
                            lw=1.2, mutation_scale=10))

ax.spines[["top","right"]].set_visible(False)

plt.tight_layout()
fig.savefig(str(figout("study-region")), dpi=600, bbox_inches="tight")
save_tiff(fig, "study-region", bbox_inches="tight")   # 1000 dpi TIFF
print(f"Saved: {figout('study-region')}")
plt.close()
print("=== Fig N02 COMPLETE ===")
