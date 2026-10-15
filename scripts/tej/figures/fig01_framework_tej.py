"""
Fig N01 -- Methodological Framework Flowchart
=============================================
EWM-TOPSIS DER Priority Area Index (PAI) pipeline
Output: Fig01_Framework.png  (600 dpi)
"""

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from _paths import SRC, BASE as TEJ, out_path
from _figures import figout, save_tiff   # single figure registry (Figures/main, Figures/supplementary)
BASE = SRC                       # inputs: shared DER data, read-only
OUT  = out_path("Figures", "_").parent   # outputs: DER_TEJ\Figures

# Every quoted result in this diagram is read from the single source of truth,
# never hand-typed: a framework figure with stale numbers is invisible to a
# text-level check because the values are drawn into the image.
import json
MR = json.loads((BASE / "Data" / "master_results.json").read_text(encoding="utf-8"))
ZN = MR["zones"]; VAL = MR["validation"]; ZV = MR["zone_validation"]

# ── Palette ────────────────────────────────────────────────────────────────────
PH = {
    1: ("#d4e6f1", "#1a6fa8"),   # blue   — data
    2: ("#d5f5e3", "#1e8449"),   # green  — preprocessing
    3: ("#fdebd0", "#ca6f1e"),   # orange — EWM
    4: ("#fadbd8", "#b03a2e"),   # red    — TOPSIS
    5: ("#e8f4f8", "#1a5276"),   # teal   — spatial
    6: ("#e8daef", "#6c3483"),   # purple — validation
    7: ("#fef9e7", "#b7950b"),   # yellow — policy
}
ZONE_FC = ["#d73027","#fc8d59","#fee090","#91bfdb","#4575b4"]

# ── Helpers ────────────────────────────────────────────────────────────────────
def rbox(ax, x, y, w, h, fc, ec, lw=1.4, alpha=0.92, rounding=0.15):
    p = FancyBboxPatch((x, y), w, h,
                        boxstyle=f"round,pad=0.06,rounding_size={rounding}",
                        linewidth=lw, edgecolor=ec, facecolor=fc,
                        alpha=alpha, zorder=3)
    ax.add_patch(p)

def arr(ax, x1, y1, x2, y2, color, lw=1.8):
    ax.annotate("", xy=(x2, y2), xytext=(x1, y1),
                arrowprops=dict(arrowstyle="-|>", color=color,
                                lw=lw, mutation_scale=18,
                                shrinkA=0, shrinkB=0), zorder=5)

def txt(ax, x, y, s, fs=7.5, color="#333333", bold=False, style="normal", ha="center", va="center"):
    ax.text(x, y, s, ha=ha, va=va, fontsize=fs, color=color,
            fontweight="bold" if bold else "normal",
            style=style, zorder=4, linespacing=1.35)

# ── Figure ─────────────────────────────────────────────────────────────────────
fig = plt.figure(figsize=(11, 16), dpi=600, facecolor="white")
ax  = fig.add_axes([0, 0, 1, 1], facecolor="white")
ax.axis("off")
ax.set_xlim(0, 11); ax.set_ylim(0, 16)

CX, CW = 5.50, 8.80   # centre x, content width
LX = 0.30              # phase label x
BX = (CX - CW/2)      # box left x  = 1.10

# ── TITLE removed for journal submission ──────────────────────────────────────

# ═══════════════════════════════════════════════════════════════════════════════
# PHASE 1 — DATA ACQUISITION  (y: 13.4 – 14.7)
# ═══════════════════════════════════════════════════════════════════════════════
fc1, ec1 = PH[1]
P1_Y, P1_H = 13.40, 1.28

# Phase label
txt(ax, LX+0.30, P1_Y+P1_H-0.20, "Phase 1", fs=6.8, bold=True, color=ec1, ha="left")
txt(ax, LX+0.30, P1_Y+P1_H-0.52, "Data", fs=6.5, color=ec1, ha="left")
txt(ax, LX+0.30, P1_Y+P1_H-0.78, "Acquisition", fs=6.5, color=ec1, ha="left")

# 5 criterion mini-boxes
CRIT = [
    ("C1 Resource", "Global Solar Atlas v2\nLTAy PVOUT, 1 km"),
    ("C2 Equity",   "NESDC/NSO\npoverty incidence"),
    ("C3 Demand",   "WorldPop\n2020 100m"),
    ("C4 Infra",    "OSM power lines\n+ cables"),
    ("C5 Physical", "Hansen GFC\n+ GHSL + DEM"),
]
cbw, cbh = 1.40, 1.15
cgap = 0.08
cx0  = BX + 0.05

for i, (cname, csrc) in enumerate(CRIT):
    bx = cx0 + i * (cbw + cgap)
    rbox(ax, bx, P1_Y+0.06, cbw, cbh, fc1, ec1, lw=1.2)
    txt(ax, bx+cbw/2, P1_Y+cbh-0.15, cname, fs=7.8, bold=True, color=ec1)
    txt(ax, bx+cbw/2, P1_Y+0.38, csrc, fs=6.2, color="#444444")

# excluded candidate box (right, outside main content): ERP overlaps C3 (author decision 2026-10-10)
vrx = cx0 + 5*(cbw+cgap) + 0.08
rbox(ax, vrx, P1_Y+0.06, 1.18, cbh, "#fce4e4", "#c0392b", lw=1.2)
txt(ax, vrx+0.59, P1_Y+cbh-0.15, "ERP (C6 cand.)", fs=7.0, bold=True, color="#c0392b")
txt(ax, vrx+0.59, P1_Y+0.60, "Emission Reduction\nPotential (NTL proxy)",
    fs=5.6, color="#888888")
txt(ax, vrx+0.59, P1_Y+0.34, "overlaps C3", fs=6.5, bold=True, color="#c0392b")
txt(ax, vrx+0.59, P1_Y+0.14, "[EXCLUDED]", fs=6, bold=True, color="#c0392b")

# Cross mark on rejected box
txt(ax, vrx+0.98, P1_Y+cbh-0.05, "X", fs=11, bold=True, color="#c0392b")

# left bracket line
ax.plot([0.35, 0.35], [P1_Y, P1_Y+P1_H], color=ec1, lw=2.5, solid_capstyle="round", zorder=2, alpha=0.55)

# ═══════════════════════════════════════════════════════════════════════════════
# PHASE 2 — PREPROCESSING  (y: 11.55 – 12.65)
# ═══════════════════════════════════════════════════════════════════════════════
fc2, ec2 = PH[2]
P2_Y, P2_H = 11.55, 1.10

arr(ax, CX, P1_Y-0.04, CX, P2_Y+P2_H+0.04, ec2)

txt(ax, LX+0.30, P2_Y+P2_H*0.75, "Phase 2", fs=6.8, bold=True, color=ec2, ha="left")
txt(ax, LX+0.30, P2_Y+P2_H*0.45, "Pre-\nprocessing", fs=6.5, color=ec2, ha="left")

rbox(ax, BX, P2_Y, CW, P2_H, fc2, ec2)
txt(ax, CX, P2_Y+P2_H-0.25, "Preprocessing & Normalisation", fs=8.5, bold=True, color=ec2)
# A5 two-level scaling, as in Methods Section 2.3 (check 2026-10-15)
txt(ax, CX, P2_Y+0.62, "90 m resampling  |  C1, C3: pixel-level 2nd–98th percentile clip  |  C2: raw poverty %  |  Province-mean aggregation")
txt(ax, CX, P2_Y+0.32, "Province level: C3 log(1 + 100x), then each criterion clipped at 2nd–98th percentile and scaled to [0, 1] once  |  ERP excluded (overlap with C3)")

ax.plot([0.35, 0.35], [P2_Y, P2_Y+P2_H], color=ec2, lw=2.5, solid_capstyle="round", zorder=2, alpha=0.55)

# ═══════════════════════════════════════════════════════════════════════════════
# PHASE 3 — EWM WEIGHT DERIVATION  (y: 9.65 – 10.75)
# ═══════════════════════════════════════════════════════════════════════════════
fc3, ec3 = PH[3]
P3_Y, P3_H = 9.65, 1.10

arr(ax, CX, P2_Y-0.04, CX, P3_Y+P3_H+0.04, ec3)

txt(ax, LX+0.30, P3_Y+P3_H*0.75, "Phase 3", fs=6.8, bold=True, color=ec3, ha="left")
txt(ax, LX+0.30, P3_Y+P3_H*0.45, "EWM\nWeights", fs=6.5, color=ec3, ha="left")

rbox(ax, BX, P3_Y, CW, P3_H, fc3, ec3)
txt(ax, CX, P3_Y+P3_H-0.25, "Entropy Weight Method (EWM)", fs=8.5, bold=True, color=ec3)
txt(ax, CX, P3_Y+0.42,
    r"Entropy:  $e_j = -(\ln m)^{-1}\sum_{i} p_{ij}\,\ln p_{ij}$        "
    r"Divergence:  $d_j = 1 - e_j$        Weight:  $w_j = d_j\,/\,\sum_{k} d_k$")

ax.plot([0.35, 0.35], [P3_Y, P3_Y+P3_H], color=ec3, lw=2.5, solid_capstyle="round", zorder=2, alpha=0.55)

# ═══════════════════════════════════════════════════════════════════════════════
# PHASE 4 — TOPSIS SCORING  (y: 7.75 – 8.95)
# ═══════════════════════════════════════════════════════════════════════════════
fc4, ec4 = PH[4]
P4_Y, P4_H = 7.75, 1.20

arr(ax, CX, P3_Y-0.04, CX, P4_Y+P4_H+0.04, ec4)

txt(ax, LX+0.30, P4_Y+P4_H*0.75, "Phase 4", fs=6.8, bold=True, color=ec4, ha="left")
txt(ax, LX+0.30, P4_Y+P4_H*0.45, "TOPSIS\nScoring", fs=6.5, color=ec4, ha="left")

rbox(ax, BX, P4_Y, CW, P4_H, fc4, ec4)
txt(ax, CX, P4_Y+P4_H-0.25, "TOPSIS: Priority Area Index (PAI)", fs=8.5, bold=True, color=ec4)
txt(ax, CX, P4_Y+0.72,
    r"Bounded ideal (unweighted)  $A^{+}=[1,1,1,1,1]$   $A^{-}=[0,0,0,0,0]$"
    r"     |     weighted:  $v^{+}_{j}=w_j,\ \ v^{-}_{j}=0$")
txt(ax, CX, P4_Y+0.45,
    r"$d^{+}_{i}=\sqrt{\sum_{j} (v_{ij}-v^{+}_{j})^{2}}$        "
    r"$d^{-}_{i}=\sqrt{\sum_{j} (v_{ij}-v^{-}_{j})^{2}}$")
txt(ax, CX, P4_Y+0.20,
    r"$\mathrm{PAI}_{i}=d^{-}_{i}\,/\,(d^{+}_{i}+d^{-}_{i})\ \in\ [0, 1]$",
    bold=True, color=ec4, fs=7.8)

ax.plot([0.35, 0.35], [P4_Y, P4_Y+P4_H], color=ec4, lw=2.5, solid_capstyle="round", zorder=2, alpha=0.55)

# ═══════════════════════════════════════════════════════════════════════════════
# PHASE 5 — SPATIAL ANALYSIS  (y: 5.80 – 7.30, two branches)
# ═══════════════════════════════════════════════════════════════════════════════
fc5, ec5 = PH[5]
P5_Y, P5_H = 5.80, 1.50
ec5a = "#2980b9"   # K-means (blue)
ec5b = "#1abc9c"   # LISA (teal)

# Split arrows
arr(ax, CX, P4_Y-0.04, 3.10, P5_Y+P5_H+0.04, ec5a)
arr(ax, CX, P4_Y-0.04, 7.90, P5_Y+P5_H+0.04, ec5b)

txt(ax, LX+0.30, P5_Y+P5_H*0.75, "Phase 5", fs=6.8, bold=True, color=ec5, ha="left")
txt(ax, LX+0.30, P5_Y+P5_H*0.45, "Spatial\nAnalysis", fs=6.5, color=ec5, ha="left")

# K-means box (left)
bw5 = 4.15
rbox(ax, BX, P5_Y, bw5, P5_H, "#d6eaf8", ec5a)
txt(ax, BX+bw5/2, P5_Y+P5_H-0.28, "Spatial Zoning (K-means k=5)", fs=8, bold=True, color=ec5a)
txt(ax, BX+bw5/2, P5_Y+0.60, "K-means  k = 5  |  n_init = 10  |  Random seed fixed")
txt(ax, BX+bw5/2, P5_Y+0.32, "Five priority zones ranked by mean PAI  |  cluster stability across k")

# LISA box (right)
rx5 = BX + bw5 + 0.18
rw5 = CW - bw5 - 0.18
rbox(ax, rx5, P5_Y, rw5, P5_H, "#d1f2eb", ec5b)
txt(ax, rx5+rw5/2, P5_Y+P5_H-0.28, "LISA Autocorrelation", fs=8, bold=True, color=ec5b)
txt(ax, rx5+rw5/2, P5_Y+0.72, "Queen contiguity weight matrix")
txt(ax, rx5+rw5/2, P5_Y+0.47, "Global Moran's I  |  Local Moran's I (LISA)")
txt(ax, rx5+rw5/2, P5_Y+0.22, "999 permutations  |  HH  LL  HL  LH  ns clusters")

ax.plot([0.35, 0.35], [P5_Y, P5_Y+P5_H], color=ec5, lw=2.5, solid_capstyle="round", zorder=2, alpha=0.55)

# ═══════════════════════════════════════════════════════════════════════════════
# PHASE 6 — VALIDATION  (y: 3.90 – 5.10)
# ═══════════════════════════════════════════════════════════════════════════════
fc6, ec6 = PH[6]
P6_Y, P6_H = 3.90, 1.20

# Both spatial-analysis branches feed validation directly. Separate endpoints
# retain visible arrowheads and avoid a false merge node above the panel.
arr(ax, 3.10, P5_Y-0.04, 3.10, P6_Y+P6_H+0.04, ec6)
arr(ax, 7.90, P5_Y-0.04, 7.90, P6_Y+P6_H+0.04, ec6)

txt(ax, LX+0.30, P6_Y+P6_H*0.75, "Phase 6", fs=6.8, bold=True, color=ec6, ha="left")
txt(ax, LX+0.30, P6_Y+P6_H*0.45, "Comparison", fs=6.5, color=ec6, ha="left")

rbox(ax, BX, P6_Y, CW, P6_H, fc6, ec6)
txt(ax, CX, P6_Y+P6_H-0.25, "Deployment Comparison & Robustness", fs=8.5, bold=True, color=ec6)
txt(ax, CX, P6_Y+0.68,
    "Deployment comparison against documented OSM solar installations")
txt(ax, CX, P6_Y+0.40,
    "Zone-enrichment test (chi-square)   |   Weight sensitivity: equal and expert scenarios")
txt(ax, CX, P6_Y+0.16,
    "Bootstrap weight uncertainty   |   Spatially restricted permutation tests")

ax.plot([0.35, 0.35], [P6_Y, P6_Y+P6_H], color=ec6, lw=2.5, solid_capstyle="round", zorder=2, alpha=0.55)

# ═══════════════════════════════════════════════════════════════════════════════
# PHASE 7 — POLICY FRAMEWORK  (y: 1.90 – 3.25)
# ═══════════════════════════════════════════════════════════════════════════════
fc7, ec7 = PH[7]
P7_Y, P7_H = 1.90, 1.35

arr(ax, CX, P6_Y-0.04, CX, P7_Y+P7_H+0.04, ec7)

txt(ax, LX+0.30, P7_Y+P7_H*0.75, "Phase 7", fs=6.8, bold=True, color=ec7, ha="left")
txt(ax, LX+0.30, P7_Y+P7_H*0.45, "Policy\nScreen", fs=6.5, color=ec7, ha="left")

rbox(ax, BX, P7_Y, CW, P7_H, fc7, ec7)
txt(ax, CX, P7_Y+P7_H-0.24, "Counterfactual Allocation Rules + Zone-to-Policy Screen", fs=8.0, bold=True, color=ec7)

# three allocation rules under one budget, then the policy screen; no rule is ranked
RULES = [("S1", "Population-proportional\nbaseline"),
         ("S2", "Equity-targeted\n(top 15 by PAI)"),
         ("S3", "Resource-and-infrastructure\ncomparator"),
         ("Screen", "Instruments examined,\nutility connection gates")]
zgap = 0.12
zpw  = (CW - 2*0.20 - 3*zgap) / 4
zph  = 0.82
zpx0 = BX + 0.20
zpy  = P7_Y + 0.08
for i, (head, body) in enumerate(RULES):
    bx = zpx0 + i*(zpw+zgap)
    rbox(ax, bx, zpy, zpw, zph, "white", ec7, lw=1.0, alpha=0.9, rounding=0.10)
    txt(ax, bx+zpw/2, zpy+0.62, head, fs=7, bold=True, color=ec7)
    txt(ax, bx+zpw/2, zpy+0.30, body, fs=6, color="#111111")

ax.plot([0.35, 0.35], [P7_Y, P7_Y+P7_H], color=ec7, lw=2.5, solid_capstyle="round", zorder=2, alpha=0.55)

# ── Figures/Tables index note removed: framework shows method only, no results ──

# ── Legend ─────────────────────────────────────────────────────────────────────
# ── Save ───────────────────────────────────────────────────────────────────────
fig.savefig(str(figout("framework")), dpi=600, bbox_inches="tight", pad_inches=0.0)
save_tiff(fig, "framework", bbox_inches="tight", pad_inches=0.0)   # 1000 dpi TIFF
fig.savefig(str(figout("framework", "pdf")), bbox_inches="tight", pad_inches=0.0)   # vector (TEJ artwork)
print("Saved: Fig01_Framework.png")
plt.close()
print("=== Fig N01 COMPLETE ===")
