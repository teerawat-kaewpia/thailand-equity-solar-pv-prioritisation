"""
Fig. 3 (TEJ): C1-C5 input criterion layers, province-level choropleth.

TEJ copy of DER\\Scripts\\07_Figures\\figN03_input_layers.py (audit 2026-10-09, M10/m3/m4):
  * no in-image titles. Panel names move to the caption, and centred panel labels a-e are
    drawn in the image (the caption already refers to (a)-(e));
  * scale bar and north arrow on panel a, colour bars labelled "Normalised score";
  * no em dashes in figure text.
Inputs are read from DER (read-only), output goes to DER_TEJ\\Figures.
Column mapping: CSV C1=Solar, C2=Poverty, C3=PopDens, C5=GridDist (paper C4), C6=LandSuit (paper C5).
"""
import math
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import geopandas as gpd
import fiona
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from _paths import SRC, out_path
from _figures import figout, save_tiff   # single figure registry (Figures/main, Figures/supplementary)

PROC = SRC / "Data" / "14_Processed_90m"
GADM = SRC / "Data" / "01_Admin_Boundaries" / "gadm41_THA.gpkg"
OUT = out_path("Figures", "_").parent

layers = fiona.listlayers(str(GADM))
adm1 = next(l for l in layers if l.endswith("_1"))
prov = gpd.read_file(str(GADM), layer=adm1)[["NAME_1", "geometry"]].copy()
if prov.crs.to_epsg() != 4326:
    prov = prov.to_crs("EPSG:4326")
prov = prov.merge(pd.read_csv(PROC / "province_PAI_summary.csv"), on="NAME_1", how="left")

CRIT = [("C1", "YlOrRd"), ("C2", "PuRd"), ("C3", "YlOrBr"), ("C5", "GnBu"), ("C6", "YlGn")]
XLIM = (97.3, 105.7)
YLIM = (5.5, 20.6)

fig, axes = plt.subplots(1, 5, figsize=(17, 6.5), dpi=600, facecolor="white")
fig.subplots_adjust(wspace=0.06, top=0.95, bottom=0.05, left=0.02, right=0.98)

for k, (ax, (col, cmap_name)) in enumerate(zip(axes, CRIT)):
    ax.set_aspect("equal")
    vmin, vmax = prov[col].quantile(0.02), prov[col].quantile(0.98)
    norm = mcolors.Normalize(vmin=vmin, vmax=vmax)
    cmap = plt.get_cmap(cmap_name)
    prov.plot(ax=ax, column=col, cmap=cmap_name, norm=norm, edgecolor="#cccccc", linewidth=0.15)
    ax.set_xlim(*XLIM)
    ax.set_ylim(*YLIM)
    ax.set_xticks([])
    ax.set_yticks([])
    ax.spines[:].set_visible(False)

    sm = plt.cm.ScalarMappable(cmap=cmap, norm=norm)
    sm.set_array([])
    cbar = fig.colorbar(sm, ax=ax, orientation="horizontal", fraction=0.06, pad=0.02, shrink=0.80)
    cbar.ax.tick_params(labelsize=5.5)
    cbar.set_ticks([vmin, (vmin + vmax) / 2, vmax])
    cbar.set_ticklabels([f"{vmin:.2f}", f"{(vmin + vmax) / 2:.2f}", f"{vmax:.2f}"])
    # A5: C2 is mapped as raw poverty incidence, the other layers as their pixel-level scores
    cbar.set_label("Poverty incidence (%)" if col == "C2" else "Normalised score", fontsize=6)

    # centred panel label (house rule: labels, not titles)
    ax.text(0.5, 1.01, "abcde"[k], transform=ax.transAxes, ha="center", va="bottom",
            fontsize=10, fontweight="bold")

# map furniture on panel a: 200 km scale bar at 6.3 N and a north arrow
ax = axes[0]
lat = 6.3
dlon = 200.0 / (111.32 * math.cos(math.radians(lat)))
ax.plot([97.6, 97.6 + dlon], [lat, lat], color="black", lw=1.6, solid_capstyle="butt")
ax.text(97.6 + dlon / 2, lat + 0.3, "200 km", ha="center", fontsize=6)
ax.annotate("N", xy=(105.1, 20.3), xytext=(105.1, 19.4), ha="center", va="center", fontsize=8,
            fontweight="bold", arrowprops=dict(arrowstyle="-|>", color="black", lw=1.0))

fig.savefig(str(figout("criteria-maps")), dpi=600, bbox_inches="tight")
save_tiff(fig, "criteria-maps", bbox_inches="tight")   # 1000 dpi TIFF
print(f"Saved: {figout('criteria-maps')}")
plt.close()
