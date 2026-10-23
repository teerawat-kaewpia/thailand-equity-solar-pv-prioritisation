"""
Fig N12 — Criterion Profiles Radar Chart (Zone 1-5)
Fig N13 — Policy Recommendation Framework
=========================================================
Output: Fig13_Radar.png, Fig14_Policy.png  (600 dpi)
"""

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch
import numpy as np
import pandas as pd
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from _paths import SRC, BASE as TEJ, out_path
from _figures import figout, save_tiff   # single figure registry (Figures/main, Figures/supplementary)
BASE = SRC                       # inputs: shared DER data, read-only
PROC = BASE / "Data" / "14_Processed_90m"
OUT  = out_path("Figures", "_").parent   # outputs: DER_TEJ\Figures

import json
MR = json.loads((BASE / "Data" / "master_results.json").read_text(encoding="utf-8"))

# radar/policy panels describe the MODEL criteria, so read the normalised matrix
pai_df = pd.read_csv(PROC / "province_criteria_normalised.csv").merge(
    pd.read_csv(PROC / "province_PAI_summary.csv")[["NAME_1", "dominant_zone"]],
    on="NAME_1")

ZONE_COLORS  = {1:"#d73027",2:"#fc8d59",3:"#fee090",4:"#91bfdb",5:"#4575b4"}
ZONE_LABELS  = {1:"Zone 1\n(Highest)",2:"Zone 2\n(High)",
                3:"Zone 3\n(Medium)",4:"Zone 4\n(Low)",5:"Zone 5\n(Lowest)"}

CRIT_COLS  = ["C1_Resource","C2_Equity","C3_Demand","C4_Infra","C5_Physical"]
CRIT_NAMES = ["C1\nResource","C2\nEquity","C3\nDemand","C4\nInfra","C5\nPhysical"]
CRIT_FULL  = ["C1 Solar Potential","C2 Equity (poverty incidence)",
              "C3 Population Density","C4 Grid Accessibility","C5 Land Suitability"]

# Zone-level criterion means
zone_means = pai_df.groupby("dominant_zone")[CRIT_COLS + ["PAI"]].mean()

# ─────────────────────────────────────────────────────────────────────────────
# FIG N12 — Radar Chart
# ─────────────────────────────────────────────────────────────────────────────
print("Rendering Fig N12 — Radar chart...")

# Normalize to [0,1] range across all zones
vals_raw = zone_means[CRIT_COLS].values  # shape (5, 5)
vmin = pai_df[CRIT_COLS].min().values
vmax = pai_df[CRIT_COLS].max().values
vals_norm = (vals_raw - vmin) / (vmax - vmin)
vals_norm = np.clip(vals_norm, 0, 1)

N = len(CRIT_COLS)
angles = [n / float(N) * 2 * np.pi for n in range(N)]
angles += angles[:1]

fig12, ax = plt.subplots(figsize=(7, 6), dpi=600,
                          subplot_kw=dict(polar=True), facecolor="white")
fig12.subplots_adjust(top=0.88)

for zone_idx in [1, 2, 3, 4, 5]:
    row = vals_norm[zone_idx - 1, :].tolist()
    row += row[:1]
    ax.plot(angles, row, "o-", lw=1.8, color=ZONE_COLORS[zone_idx],
            markersize=4, zorder=3 + zone_idx,
            label=f"Zone {zone_idx} ({['Highest','High','Medium','Low','Lowest'][zone_idx-1]})")
    ax.fill(angles, row, alpha=0.08, color=ZONE_COLORS[zone_idx])

# Axis labels
ax.set_xticks(angles[:-1])
ax.set_xticklabels(CRIT_NAMES, fontsize=8.5, fontweight="bold")
ax.set_ylim(0, 1)
ax.set_yticks([0.25, 0.5, 0.75])
ax.set_yticklabels(["0.25","0.50","0.75"], fontsize=6, color="#888888")
ax.set_rlabel_position(20)
ax.grid(color="#cccccc", linestyle="--", linewidth=0.6)

ax.legend(loc="lower right", bbox_to_anchor=(1.35, 0.0),
          fontsize=7.5, framealpha=0.90, edgecolor="#cccccc")


fig12.savefig(str(figout("radar")), dpi=600, bbox_inches="tight")
save_tiff(fig12, "radar", bbox_inches="tight")   # 1000 dpi TIFF
print(f"  Saved: {figout('radar')}")
plt.close(fig12)

# ─────────────────────────────────────────────────────────────────────────────
# FIG N13 — Zone-to-Policy Framework (Discussion figure)
# ─────────────────────────────────────────────────────────────────────────────
print("Rendering Fig N13 — Zone-to-Policy framework...")

zone_counts = pai_df["dominant_zone"].value_counts().sort_index().to_dict()

_ZW = {1: "Highest", 2: "High", 3: "Medium", 4: "Low", 5: "Lowest"}
ZONE_LABEL = {
    z: (f"Zone {z}: {_ZW[z]} Priority",
        f"PAI {MR['zones'][str(z)]['pai_min']:.3f}–{MR['zones'][str(z)]['pai_max']:.3f}",
        f"{MR['zones'][str(z)]['land_pct']:.1f}% of land")
    for z in (1, 2, 3, 4, 5)
}

# Policy pathways follow the CURRENT zone composition. Zone 1 is no longer the
# metropolitan belt (as under the superseded night-light equity proxy) but a
# small set of high-poverty provinces plus two central agricultural ones, so the
# instrument attached to it is subsidised community solar, not urban rooftop.
POLICY_MAP = {
    1: ("Subsidised Community Solar",
        ["Capital subsidy / concessional finance",
         "Community & cooperative ownership models",
         "Distribution-connected, sized to feeder capacity"],
        "0–3 years"),
    2: ("Community Solar & Agrivoltaics",
        ["Shared solar farms and energy cooperatives",
         "Agrivoltaic dual land use on farmland",
         "Grid reinforcement & demand-side management"],
        "3–5 years"),
    3: ("Hybrid Solar",
        ["Grid-tied rooftop and ground-mount solar",
         "Feasibility studies & pilot projects",
         "Capacity building & stakeholder engagement"],
        "5–10 years"),
    4: ("Small Distributed Solar",
        ["Small systems sized to local feeder capacity",
         "Distribution-connected community solar",
         "Infrastructure investment & environmental screening"],
        "10–15 years"),
    5: ("Efficiency-First",
        ["Energy efficiency measures as first response",
         "Targeted rooftop solar on public facilities",
         "Conservation constraints and long-term monitoring"],
        "Ongoing"),
}

fig13 = plt.figure(figsize=(15, 10), dpi=600, facecolor="white")
ax13  = fig13.add_axes([0, 0, 1, 1], facecolor="white")
ax13.axis("off")
ax13.set_xlim(0, 15)
ax13.set_ylim(0, 10)

# Column headers
ax13.text(2.90, 8.88, "DER Priority Zone",
          ha="center", va="center", fontsize=10.5, fontweight="bold", color="#333333",
          bbox=dict(boxstyle="round,pad=0.28", facecolor="#f0f0f0",
                    edgecolor="#cccccc", lw=0.6))
ax13.text(11.05, 8.88, "Recommended Deployment Strategy",
          ha="center", va="center", fontsize=10.5, fontweight="bold", color="#333333",
          bbox=dict(boxstyle="round,pad=0.28", facecolor="#f0f0f0",
                    edgecolor="#cccccc", lw=0.6))

# Layout constants
ROW_Y  = [8.05, 6.60, 5.15, 3.70, 2.25]
BOX_H  = 1.18
ZBX_X  = 0.25
ZBX_W  = 5.30
ZBX_CX = ZBX_X + ZBX_W / 2          # 2.90
ARR_X0 = ZBX_X + ZBX_W + 0.08       # 5.63
ARR_X1 = 7.18
PBX_X  = ARR_X1 + 0.10              # 7.28
PBX_W  = 7.47
WHITE  = "#ffffff"

for zone, y in zip([1, 2, 3, 4, 5], ROW_Y):
    zc   = ZONE_COLORS[zone]
    name, pai, land = ZONE_LABEL[zone]
    ptype, actions, timeline = POLICY_MAP[zone]
    n    = zone_counts.get(zone, 0)
    tcol = WHITE if zone in [1, 5] else "#111111"

    # Zone box
    zbox = FancyBboxPatch((ZBX_X, y - BOX_H / 2), ZBX_W, BOX_H,
                           boxstyle="round,pad=0.06,rounding_size=0.10",
                           linewidth=0, facecolor=zc, alpha=0.92, zorder=3)
    ax13.add_patch(zbox)
    ax13.text(ZBX_CX, y + 0.30, name,
              ha="center", va="center", fontsize=10, fontweight="bold",
              color=tcol, zorder=4)
    ax13.text(ZBX_CX, y + 0.02, pai,
              ha="center", va="center", fontsize=8.5, color=tcol, zorder=4)
    ax13.text(ZBX_CX, y - 0.26, f"{land}  |  {n} provinces",
              ha="center", va="center", fontsize=7.8, color=tcol, zorder=4)

    # Arrow
    ax13.annotate("", xy=(ARR_X1, y), xytext=(ARR_X0, y),
                  arrowprops=dict(arrowstyle="-|>", color=zc,
                                  lw=2.4, mutation_scale=16),
                  zorder=3)

    # Policy box
    pbox = FancyBboxPatch((PBX_X, y - BOX_H / 2), PBX_W, BOX_H,
                           boxstyle="round,pad=0.06,rounding_size=0.10",
                           linewidth=1.4, edgecolor=zc,
                           facecolor=WHITE, zorder=3)
    ax13.add_patch(pbox)

    # Policy type title (left-aligned)
    ax13.text(PBX_X + 0.28, y + 0.30, ptype,
              ha="left", va="center", fontsize=11, fontweight="bold",
              color=zc, zorder=4)

    # Timeline badge (right side, same row as title)
    TL_W = 1.55
    tl_x = PBX_X + PBX_W - TL_W - 0.12
    tl_box = FancyBboxPatch((tl_x, y + 0.13), TL_W, 0.32,
                              boxstyle="round,pad=0.04,rounding_size=0.06",
                              linewidth=0, facecolor=zc, alpha=0.18, zorder=4)
    ax13.add_patch(tl_box)
    ax13.text(tl_x + TL_W / 2, y + 0.29, timeline,
              ha="center", va="center", fontsize=7.5, color=zc,
              fontweight="bold", zorder=5)

    # Action bullets
    for k, action in enumerate(actions):
        ax13.text(PBX_X + 0.28, y + 0.02 - k * 0.27, f"• {action}",
                  ha="left", va="center", fontsize=7.8, color="#444444", zorder=4)

# Descriptive notes under the figure removed per request (zone labels already
# convey the priority ordering; the indicative-pathways caveat lives in the text).

pass   # Fig14_Policy retired 2026-10-15: superseded by Table 15, last copy in Figures/archive
print("  Fig14_Policy not saved (retired)")
plt.close(fig13)

print("=== Fig N12 + N13 COMPLETE ===")
