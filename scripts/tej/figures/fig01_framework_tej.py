"""
Fig 1 -- Workflow for constructing and evaluating the Priority Area Index
=========================================================================
Redesign 2026-10-24 (review: the seven-phase infographic was too tall, its text and equations too small
at page size). Five steps in one row, one colour plus grey, no equations (they are in Section 2.3 and
Supplementary S13). Drawn at 159 mm wide, the full text width of the manuscript, so the type prints at
its stated size (body 7.5 pt, headings 8.5 pt, Arial). A fit check stops the build if any text leaves
its box.
Output: Fig01_Framework.png (600 dpi), TIFF (1000 dpi) and vector PDF with embedded fonts.
"""
import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, Rectangle

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from _paths import BASE as TEJ
from _figures import figout, save_tiff   # single figure registry (Figures/main, Figures/supplementary)

# the one number drawn in the figure is read from the analysis output, never typed
ERPD = json.loads((TEJ / "Data" / "erp_diagnostic" / "erp_diagnostic.json").read_text(encoding="utf-8"))
RHO = ERPD["rho_erp_c3"]

plt.rcParams.update({"font.family": "Arial", "pdf.fonttype": 42, "ps.fonttype": 42})
MM = 1 / 25.4
W, H = 159.0, 60.0                        # mm (H is reset from the content below)
BODY, HEAD = 7.5, 8.5                     # pt, at print size
NAVY, GREY, INK, RED = "#1f3b73", "#8a8a8a", "#1a1a1a", "#b03a2e"

fig = plt.figure(figsize=(W * MM, H * MM), facecolor="white")
ax = fig.add_axes([0, 0, 1, 1])
ax.set_xlim(0, W); ax.set_ylim(0, H); ax.axis("off")

# Content follows Sections 2 and 3 of the manuscript.
STEPS = [
    ("1", "Input criteria",
     ["C1 Solar resource", "C2 Poverty (equity),\nprovince statistic", "C3 Demand density",
      "C4 Grid access", "C5 Physical\nsuitability"]),
    # C2 is one official value per province: only the raster criteria are harmonised on the grid
    ("2", "Harmonise and\naggregate",
     ["Raster criteria\n(C1, C3–C5) on a\ncommon 90 m grid", "Province means\n(77 provinces)", "C3 log transform",
      "Clip and scale\nto [0, 1] at\nprovince level"]),
    ("3", "Weight and rank",
     ["Entropy weights\n(EWM)", "Bounded-ideal\nTOPSIS", "Priority Area\nIndex (PAI)"]),
    ("4", "Spatial and\nrobustness checks",
     ["K-means zones\n(k = 5)", "Moran's I and LISA", "Weight sensitivity\nand bootstrap",
      "Comparison with\nOSM-mapped\nsolar plants"]),
    ("5", "Decision\ncomparison",
     ["Three allocation\nrules (S1–S3),\none budget", "Network-distance\nscreen",
      "Instruments and\nutility connection\ngates"]),
]

GAP = 4.0                                  # mm between boxes (arrow space)
BW = (W - 1.0 - 4 * GAP) / 5               # box width
HEAD_H = 10.0                              # heading band height
PAD = 1.8
LINE, ITEM_GAP, FIRST = 3.15, 1.6, 2.6     # mm per text line, between items, heading to first item
# box height from the longest column, so no box carries empty space
_content = max(sum((it.count("\n") + 1) * LINE + ITEM_GAP for it in items) for _, _, items in STEPS)
NOTE_H, NOTE_GAP = 11.0, 4.0               # excluded-candidate note under step 1
BOX_H = HEAD_H + FIRST + _content + 0.6
H = 1.0 + BOX_H + NOTE_GAP + NOTE_H + 1.0
fig.set_size_inches(W * MM, H * MM)
ax.set_ylim(0, H)
TOP, BOT = H - 1.0, H - 1.0 - BOX_H

texts = []                                 # (text artist, box extent in data units) for the fit check
for k, (num, title, items) in enumerate(STEPS):
    x0 = 0.5 + k * (BW + GAP)
    ax.add_patch(Rectangle((x0, BOT), BW, TOP - BOT, facecolor="white", edgecolor=NAVY, lw=0.7, zorder=2))
    ax.add_patch(Rectangle((x0, TOP - HEAD_H), BW, HEAD_H, facecolor=NAVY, edgecolor=NAVY, lw=0.7, zorder=3))
    t = ax.text(x0 + BW / 2, TOP - HEAD_H / 2, f"{num}  {title}" if "\n" not in title else f"{num}  {title}",
                ha="center", va="center", fontsize=HEAD, fontweight="bold", color="white", zorder=4,
                linespacing=1.1)
    texts.append((t, (x0, TOP - HEAD_H, x0 + BW, TOP)))
    y = TOP - HEAD_H - FIRST
    for it in items:
        n_lines = it.count("\n") + 1
        b = ax.text(x0 + PAD, y, "•", ha="left", va="top", fontsize=BODY, color=NAVY, zorder=4)
        t = ax.text(x0 + PAD + 2.6, y, it, ha="left", va="top", fontsize=BODY, color=INK, zorder=4,
                    linespacing=1.15)
        texts.append((t, (x0, BOT, x0 + BW, TOP - HEAD_H)))
        y -= n_lines * LINE + ITEM_GAP
    if k < 4:                               # arrow to the next step, centred on the box height
        ym = (TOP + BOT) / 2
        ax.add_patch(FancyArrowPatch((x0 + BW + 0.5, ym), (x0 + BW + GAP - 0.5, ym), arrowstyle="-|>",
                                     mutation_scale=8, lw=0.9, color=INK, zorder=5))

# excluded candidate: a small dashed grey note under step 1, red used only for "removed"
nx0, nx1, ny0, ny1 = 0.5, 0.5 + 2.6 * BW + 2 * GAP, 1.0, 1.0 + NOTE_H
ax.add_patch(Rectangle((nx0, ny0), nx1 - nx0, ny1 - ny0, facecolor="white", edgecolor=GREY, lw=0.6,
                       ls=(0, (3, 2)), zorder=2))
ax.add_patch(FancyArrowPatch((0.5 + BW / 2, BOT), (0.5 + BW / 2, ny1), arrowstyle="-", lw=0.6, color=GREY,
                             ls=(0, (3, 2)), zorder=2))
t1 = ax.text(nx0 + PAD, ny1 - 2.2, "Candidate ERP (night-light emission proxy)", ha="left", va="top",
             fontsize=BODY, color=INK, zorder=4)
t2 = ax.text(nx0 + PAD, ny1 - 6.0, f"removed before weighting: overlaps C3, ρ = {RHO:.3f}", ha="left",
             va="top", fontsize=BODY, color=RED, zorder=4)
texts += [(t1, (nx0, ny0, nx1, ny1)), (t2, (nx0, ny0, nx1, ny1))]

# fit check: every text inside its box with at least 0.6 mm clear on each side
fig.canvas.draw()
inv = ax.transData.inverted()
for t, (bx0, by0, bx1, by1) in texts:
    (tx0, ty0), (tx1, ty1) = inv.transform(t.get_window_extent())
    assert tx0 >= bx0 + 0.6 and tx1 <= bx1 - 0.6 and ty0 >= by0 + 0.6 and ty1 <= by1 - 0.6, \
        f"text leaves its box: {t.get_text()!r} x {tx0:.1f}-{tx1:.1f} / {bx0:.1f}-{bx1:.1f}, " \
        f"y {ty0:.1f}-{ty1:.1f} / {by0:.1f}-{by1:.1f}"

# saved at the drawn size (no tight crop), so 1 mm in the file is 1 mm on the page
fig.savefig(str(figout("framework")), dpi=600)
save_tiff(fig, "framework")                                   # 1000 dpi TIFF
fig.savefig(str(figout("framework", "pdf")))                  # vector, fonts embedded (TrueType)
plt.close(fig)
print(f"Saved: Fig01_Framework.png, {W:.0f} x {H:.0f} mm, body {BODY} pt, headings {HEAD} pt")
print("=== Fig 1 COMPLETE ===")
