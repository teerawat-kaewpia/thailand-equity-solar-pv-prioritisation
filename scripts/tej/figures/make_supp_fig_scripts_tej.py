"""Create TEJ copies of three supplementary figure scripts from DER_paper_repo (audit 2026-10-09, 07):
  fig08_lisa_map_tej.py        S13c: true 200 km bar, north arrow letter below, no ';' in legend, the
                               FDR sentence read from lisa_fdr, no fixed 'Bangkok Metro Cluster' label
  fig11_sensitivity_tej.py     S13e: panel labels a/b instead of titles (marker size explained in caption)
  fig12_bangkok_district_tej.py S12: panel labels a/b instead of titles, legend title 'Priority zone'
Inputs come from SRC (read-only), outputs go to DER_TEJ/Figures.
"""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tiff1000_patch import add_tiff   # 2026-10-15: 1000 dpi TIFF next to every PNG

REPO = Path(r"D:\Clude Code GIS\Energy\DER_paper_repo\Scripts\07_Figures")
HERE = Path(__file__).resolve().parent
HDR = ('import sys\nsys.path.insert(0, str(Path(__file__).resolve().parents[1]))\n'
       'from _paths import SRC, out_path\n'
       'from _figures import figout   # single figure registry (Figures/main, Figures/supplementary)\n')


def rep(s, a, b, n=1):
    assert s.count(a) == n, (s.count(a), a[:80])
    return s.replace(a, b)


def outs(s, mapping):
    """2026-10-15: write each figure through the registry instead of a flat Figures/ folder."""
    for name, key in mapping.items():
        s = rep(s, f'str(OUT / "{name}")', f'str(figout("{key}"))')
        s = rep(s, "{OUT / '" + name + "'}", "{figout('" + key + "')}")
    return s


def roots(s):
    s = rep(s, 'BASE = Path(os.environ.get("DER_PROJECT_ROOT", Path(__file__).resolve().parents[2]))',
            HDR + 'BASE = SRC                                    # inputs, read-only')
    s = rep(s, 'OUT  = BASE / "Figures"', 'OUT  = out_path("Figures", "_").parent      # DER_TEJ\\Figures')
    return s


# ── S13c LISA ──
s = roots((REPO / "fig04_lisa_map.py").read_text(encoding="utf-8"))
s = rep(s, '''# Group label for the Bangkok Metropolitan HH cluster
ax.text(100.55, 13.95, "Bangkok\\nMetro\\nCluster",
        ha="center", va="center", fontsize=4.5,
        color="#111111", fontweight="bold",
        path_effects=[pe.withStroke(linewidth=2.0, foreground="white")])
''', '')
s = rep(s, '''          title="LISA cluster type (unadjusted p < 0.05;\\nexploratory, none survives FDR)",''',
        '''          title=("LISA cluster type (unadjusted p < 0.05)\\n"
                 + (f"Exploratory. None survives FDR correction" if MR["lisa_fdr"]["n_fdr_sig"] == 0
                    else f"{MR['lisa_fdr']['n_fdr_sig']} survive FDR correction")),''')
s = rep(s, '''ax.plot([98.0, 100.0], [5.9, 5.9], color="black", lw=1.8,
        solid_capstyle="butt")
ax.text(99.0, 6.10, "200 km", ha="center", fontsize=7)''',
        '''import math
_dlon = 200.0 / (111.32 * math.cos(math.radians(5.9)))     # 200 km at 5.9 N
ax.plot([98.0, 98.0 + _dlon], [5.9, 5.9], color="black", lw=1.8, solid_capstyle="butt")
ax.text(98.0 + _dlon / 2, 6.10, "200 km", ha="center", fontsize=7)''')
s = rep(s, '''ax.annotate("N", xy=(104.8, 18.9), xytext=(104.8, 18.5),
            fontsize=9, ha="center", va="bottom", fontweight="bold",''',
        '''ax.annotate("N", xy=(104.8, 19.1), xytext=(104.8, 18.5),
            fontsize=9, ha="center", va="top", fontweight="bold",''')
# 2026-10-15 (user check): label every shaded province (HH, LL, HL, LH), not only HH and LL, and do not
# skip small central provinces, so each coloured polygon carries its name
s = rep(s, 'sig = prov[prov["LISA_type"].isin(["HH", "LL"])]', 'sig = prov[prov["LISA_type"].isin(["HH", "LL", "HL", "LH"])]')
s = rep(s, '''    if row.geometry.area < 0.25 and 13.0 < cy < 14.8 and 99.5 < cx < 101.5:
        continue
''', '')
s = outs(s, {"Fig08_LISA_Map.png": "lisa"})
s, _n = add_tiff(s)
assert _n >= 1
(HERE / "fig08_lisa_map_tej.py").write_text(s, encoding="utf-8")

# ── S13e sensitivity (+ ranking, unchanged) ──
s = roots((REPO / "figN09_10_ranking_sensitivity.py").read_text(encoding="utf-8"))
s = rep(s, '''    ax.set_title(f"EWM vs {label}", fontsize=8, pad=4, fontweight="bold")''',
        '''    ax.set_title("ab"[list(axes).index(ax)], fontsize=10, pad=4, fontweight="bold")   # panel label, not a title''')
# 2026-10-15: rho at full precision; master_results holds 4-dp values, which double-round at 3 dp (0.9605 -> 0.961)
s = rep(s, 'pai_df  = pd.read_csv(PROC / "province_PAI_summary.csv")\n',
        'pai_df  = pd.read_csv(PROC / "province_PAI_summary.csv")\n'
        'pai_df["PAI"] = pai_df.NAME_1.map(pd.read_csv(PROC / "province_criteria_normalised.csv").set_index("NAME_1").PAI)   # full precision, summary PAI is 4 dp\n')
s = rep(s, "MR['sensitivity_rho']['equal']", "SENS_RHO['equal']")
s = rep(s, "MR['sensitivity_rho']['expert']", "SENS_RHO['expert']")
s = rep(s, "from _paths import SRC, out_path\n", "from _paths import SRC, out_path\nfrom _sens import SENS_RHO   # full-precision rho (no double rounding)\n")
# 2026-10-15: labels of large shifters overlapped (Bangkok cluster, Chaiyaphum/Kamphaeng Phet). Deterministic
# placement: each label starts at the default offset and moves up in steps until it clears the labels placed before.
s = rep(s, '''    for _, row in large.iterrows():
        ax.annotate(row["NAME_1"],
                    xy=(row["rank_EWM"], row[rank_col]),
                    xytext=(4, 4), textcoords="offset points",
                    fontsize=4.5, color="#333333",
                    arrowprops=dict(arrowstyle="-", lw=0.3, color="#aaaaaa"))''',
        '''    placed = []
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
                    arrowprops=dict(arrowstyle="-", lw=0.3, color="#aaaaaa"))''')
s = outs(s, {"Fig09_Province_Ranking.png": "ranking", "Fig11_Sensitivity.png": "sens"})
s, _n = add_tiff(s)
assert _n >= 1
(HERE / "fig11_sensitivity_tej.py").write_text(s, encoding="utf-8")

# ── S12 Bangkok districts ──
s = (REPO / "fig14_bangkok_district.py").read_text(encoding="utf-8")
s = rep(s, 'BASE = Path(os.environ.get("DER_PROJECT_ROOT", Path(__file__).resolve().parents[2]))',
        HDR + 'BASE = SRC                                    # inputs, read-only')
s = rep(s, 'OUT  = BASE / "Figures"', 'OUT  = out_path("Figures", "_").parent      # DER_TEJ\\Figures')
s = rep(s, '''axA.set_title("(a) District PAI (4 criteria incl. equity)", fontsize=9, fontweight="bold", pad=5)''',
        '''axA.set_title("a", fontsize=10, fontweight="bold", pad=5)''')
s = rep(s, '''axB.set_title("(b) K-means priority zones (k=5)", fontsize=9, fontweight="bold", pad=5)''',
        '''axB.set_title("b", fontsize=10, fontweight="bold", pad=5)''')
s = rep(s, '''title="DER Priority Zone"''', '''title="Priority zone"''')
# 2026-10-15: registry output, and no 900 dpi TIFF copy (never used by either document)
s = rep(s, 'png = OUT / "Fig12_Bangkok_District.png"', 'png = figout("S-district")')
s = rep(s, 'Output: Fig12_Bangkok_District.png (600 dpi) + TIFF/Fig12_Bangkok_District.tif (900 dpi)',
        'Output: Figures/supplementary/FigS12_Bangkok_District.png (600 dpi)')
s = rep(s, 'TIF  = OUT / "TIFF"\nTIF.mkdir(parents=True, exist_ok=True)\n', '')
_i = s.index("# ── 900 dpi TIFF")
_j = s.index("\n", s.index("Saved TIFF 900dpi")) + 1
s = s[:_i] + s[_j:]
assert "TIF" not in s.replace("TIFF", "")
s = rep(s, 'fig.savefig(str(png), dpi=600, bbox_inches="tight")\n',
        'fig.savefig(str(png), dpi=600, bbox_inches="tight")\n'
        'save_tiff(fig, "S-district", bbox_inches="tight")   # 1000 dpi TIFF\n')
s = s.replace("from _figures import figout ", "from _figures import figout, save_tiff ", 1)
(HERE / "fig12_bangkok_district_tej.py").write_text(s, encoding="utf-8")

# ── S13a correlation matrix + S13b EWM weights (TEJ port, 2026-10-15) ──
# Previously read from the DER mirror's Figures folder. Ported so every supplementary figure is built here.
s = roots((REPO / "figN04_05_corr_weights.py").read_text(encoding="utf-8"))
s = outs(s, {"Fig04_Correlation.png": "corr", "Fig05_EWM_Weights.png": "weights"})
s, _n = add_tiff(s)
assert _n >= 1
(HERE / "fig_s13ab_corr_weights_tej.py").write_text(s, encoding="utf-8")
print("written: fig08_lisa_map_tej.py, fig11_sensitivity_tej.py, fig12_bangkok_district_tej.py, fig_s13ab_corr_weights_tej.py")
