# -*- coding: utf-8 -*-
"""
Supplementary material for the DER manuscript.

Contains the material the main text points to but does not have room for:
the full criterion correlation matrices (S1, S2), the complete 77-province
ranking of which only the top 20 is tabulated in the paper (S3), and the
province-by-province rank shifts under the alternative weighting scenarios (S4).

Numbers come from the same analysis outputs as the manuscript, via
master_results.json and the generated tables workbook, so the supplementary
cannot drift from the paper.
"""
import json
import pandas as pd
from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml.ns import qn
from docx.shared import Pt, Cm, RGBColor
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
from _paths import SRC, BASE, out_path, data
from _figures import figin   # single figure registry, no fallback to the DER mirror
from _sens import SENS, SENS_RHO   # full-precision sensitivity statistics (no double rounding)
from _paths import fig as _figpath
OUT  = out_path("Manuscript", "DER_TEJ_Supplementary.docx")
MR   = json.loads(data("master_results.json").read_text(encoding="utf-8"))
T    = pd.read_excel(SRC / "Tables" / "DER_Paper_Tables.xlsx", sheet_name=None)
PROC = SRC / "Data" / "14_Processed_90m"

# ERP post hoc diagnostic (Scripts/erp_posthoc_diagnostic.py), author decision 2026-10-10
ERPD = json.loads((BASE / "Data" / "erp_diagnostic" / "erp_diagnostic.json").read_text(encoding="utf-8"))
assert ERPD["status"].startswith("post hoc diagnostic")

# ── A4 (2026-10-09): narrative facts read from the data, never typed ──────────
_PS = pd.read_csv(SRC / "Data" / "14_Processed_90m" / "province_PAI_summary.csv")
_NM = pd.read_csv(SRC / "Data" / "14_Processed_90m" / "province_criteria_normalised.csv").set_index("NAME_1")
_POVT = pd.read_csv(SRC / "Data" / "14_Processed_90m" / "C2_poverty_province.csv").sort_values("poverty_pct", ascending=False)
_PAI = _NM["PAI"].to_dict()   # full precision: the summary PAI is rounded to 4 dp and double-rounds at 3 dp
_RANK = dict(zip(_PS.NAME_1, _PS["rank"]))
_Z1 = _PS[_PS.dominant_zone == 1].sort_values("rank").NAME_1.tolist()
# Zone 1 entry routes from national ranks (A5): scale-free, so normalisation cannot move them.
# A province enters on a criterion when it is in the national top fifth (rank 15 or better of 77).
_TOPQ = 15
_RPOV = pd.read_csv(SRC / "Data" / "14_Processed_90m" / "C2_poverty_province.csv").set_index("NAME_1").poverty_pct.rank(ascending=False, method="min")
_RC1 = _PS.set_index("NAME_1").C1.rank(ascending=False, method="min")
_Z1R = _Z1[1:]
_BOTH = [p for p in _Z1R if _RPOV[p] <= _TOPQ and _RC1[p] <= _TOPQ]
_POVONLY = [p for p in _Z1R if _RPOV[p] <= _TOPQ < _RC1[p]]
_IRRONLY = [p for p in _Z1R if _RC1[p] <= _TOPQ < _RPOV[p]]
assert _Z1[0] == "Pattani" and sorted(_BOTH + _POVONLY + _IRRONLY) == sorted(_Z1R), (_Z1, _BOTH, _POVONLY, _IRRONLY)
assert (_POVONLY, _IRRONLY, _BOTH) == (["Nong Bua Lam Phu", "Kalasin"], ["Ang Thong"], ["Chai Nat", "Si Sa Ket"]), (_POVONLY, _IRRONLY, _BOTH)
_POVORD = _POVT.NAME_1.tolist()
assert _POVORD[:3] == ["Mae Hong Son", "Pattani", "Tak"], _POVORD[:3]
_BOT = _PS.sort_values("rank", ascending=False).NAME_1.tolist()
assert _BOT[:5] == ["Loei", "Chiang Mai", "Surat Thani", "Trat", "Chanthaburi"], _BOT[:5]
_NUMW = {2: "two", 3: "three", 4: "four", 5: "five", 6: "six", 7: "seven", 8: "eight", 9: "nine", 10: "ten",
         11: "eleven", 12: "twelve", 13: "thirteen", 14: "fourteen", 15: "fifteen"}
def nw(n): return _NUMW[n]
def names(xs): return xs[0] if len(xs) == 1 else ", ".join(xs[:-1]) + " and " + xs[-1]
def pai(p): return f"{_PAI[p]:.3f}"
_SBK = MR["bootstrap"]["stability_by_k"]
assert all(_SBK[k]["top_cluster_size"] >= len(_Z1) for k in ("2", "3", "4", "5"))   # contiguous 1-D bands
_MI = MR["morans_I"]
_LS = pd.read_csv(PROC / "province_LISA.csv")
_LS = _LS[_LS.LISA_p < 0.05]
_LT = {t: _LS[_LS.LISA_type == t].sort_values("LISA_p").NAME_1.tolist() for t in ("HH", "LL", "HL", "LH")}
assert sum(len(v) for v in _LT.values()) == MR["lisa_fdr"]["n_raw_sig"]
_FDR0 = MR["lisa_fdr"]["n_fdr_sig"] == 0
def moran(): return f"{_MI['I']:.3f}, permutation p = {_MI['p']:.3f}, {_MI['permutations']} permutations"

CRIT = ["C1 Solar", "C2 Poverty", "C3 PopDens", "C4 GridDist", "C5 LandSuit"]
NICE = ["C1 Resource", "C2 Equity", "C3 Demand", "C4 Infrastructure", "C5 Physical"]

doc = Document()
sec = doc.sections[0]
sec.page_width, sec.page_height = Cm(21.0), Cm(29.7)
for m in ("left_margin", "right_margin"):
    setattr(sec, m, Cm(2.54))
sec.top_margin = sec.bottom_margin = Cm(2.54)
USABLE = 15.92  # cm


def _tnr(run, size_pt=11, bold=False, italic=False):
    run.font.name = "Times New Roman"
    run.font.size = Pt(size_pt)
    run.bold, run.italic = bold, italic
    run._element.rPr.rFonts.set(qn("w:eastAsia"), "Times New Roman")


def head(text, size_pt=13, space_before=14, space_after=6):
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(space_before)
    p.paragraph_format.space_after = Pt(space_after)
    _tnr(p.add_run(text), size_pt=size_pt, bold=True)
    p.paragraph_format.keep_with_next = True   # never strand a heading at a page foot
    return p


def para(text, size_pt=11, italic=False, size_after=8):
    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(size_after)
    p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    _tnr(p.add_run(text), size_pt=size_pt, italic=italic)
    return p


def caption(text):
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(10)
    p.paragraph_format.space_after = Pt(4)
    p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    _tnr(p.add_run(text), size_pt=9.5)
    p.paragraph_format.keep_with_next = True   # table captions stay with their table
    return p


from _tablestyle import apply_rules, fit_widths

def table(df, col_widths, font_size=9, shade_diag=False, index_col=False):
    """Render df; col_widths in cm, must sum to <= USABLE."""
    assert sum(col_widths) <= USABLE + 0.01, f"width {sum(col_widths):.2f} > {USABLE}"
    col_widths = fit_widths(df, col_widths, font_size)   # no split numbers or words (review 2026-10-18)
    t = doc.add_table(rows=1, cols=len(df.columns))
    t.style = "Table Grid"
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    t.autofit = False
    for j, (c, w) in enumerate(zip(df.columns, col_widths)):
        cell = t.rows[0].cells[j]
        cell.width = Cm(w)
        cell.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
        _tnr(cell.paragraphs[0].add_run(str(c)), size_pt=font_size, bold=True)
    for _, row in df.iterrows():
        cells = t.add_row().cells
        for j, (v, w) in enumerate(zip(row, col_widths)):
            cells[j].width = Cm(w)
            p = cells[j].paragraphs[0]
            p.alignment = (WD_ALIGN_PARAGRAPH.LEFT if (index_col and j == 0)
                           or isinstance(v, str) and not _numeric(v)
                           else WD_ALIGN_PARAGRAPH.CENTER)
            r = p.add_run("" if pd.isna(v) else str(v))
            on_diag = shade_diag and j > 0 and str(v) == "1.000"
            _tnr(r, size_pt=font_size, bold=on_diag)
            if on_diag:
                r.font.color.rgb = RGBColor(0x88, 0x88, 0x88)
    apply_rules(t)   # TEJ guide: no vertical rules, no shading
    return t


def _numeric(s):
    try:
        float(str(s).replace("−", "-")); return True
    except ValueError:
        return False


def fmt_matrix(sheet):
    m = T[sheet].copy()
    m = m.rename(columns={"Unnamed: 0": "Criterion"})
    m["Criterion"] = NICE
    m.columns = ["Criterion"] + NICE
    for c in NICE:
        m[c] = m[c].map(lambda v: f"{v:.3f}".replace("-", "−"))
    return m


# ══════════════════════════════════════════════════════════════════════════════
# TITLE
# ══════════════════════════════════════════════════════════════════════════════
t = doc.add_paragraph(); t.alignment = WD_ALIGN_PARAGRAPH.CENTER
t.paragraph_format.space_after = Pt(4)
_tnr(t.add_run("Supplementary Material"), size_pt=15, bold=True)

st = doc.add_paragraph(); st.alignment = WD_ALIGN_PARAGRAPH.CENTER
st.paragraph_format.space_after = Pt(18)
from _meta import TITLE   # same title as the manuscript (was the withdrawn SCS title)
_tnr(st.add_run(TITLE), size_pt=11, italic=True)

para("This document contains the full criterion correlation matrices referenced in "
     "Section 4.2 of the main text (Tables {T:S-pearson} and {T:S-spearman}), the complete ranking of "
     "all 77 provinces (Table {T:S-ranking}), the province-level rank displacements underlying the sensitivity "
     "analysis of Section 4.8 (Table {T:S-rankshift}), the spatially restricted significance tests "
     "(Table {T:S-spatialp}), and the sensitivity of the results to the unit of aggregation, the "
     "modifiable areal unit problem, recomputed at region, province and amphoe scales "
     "(Table {T:S-maup}), the multiple-comparison–corrected local spatial-cluster tests "
     "(Table {T:S-lisa}), and the construction of the two author-constructed composite "
     "socioeconomic indices used for the district equity criterion and the Table {T:construct} "
     "construct check (Section S8, Tables {T:S-index-a}–{T:S-index-b}), and a sensitivity of the results to the "
     "grid criterion in which C4 is replaced by a GridFinder LV-density surface (Section S9, "
     "Table {T:S-lv}). A data-source provenance inventory, including source version, native "
     "scale, temporal coverage, processing path and access route, is provided in Section "
     "S10 (Table {T:S-sources}). All values are computed on the normalised model "
     "matrix, C3 Demand Density log-transformed, every aggregated criterion clipped at the "
     "2nd and 98th percentiles and linearly rescaled to [0, 1] once at province level, which "
     "is the matrix consumed by the "
     "entropy weighting and TOPSIS steps.")

# ══════════════════════════════════════════════════════════════════════════════
# S1 / S2 — correlation matrices
# ══════════════════════════════════════════════════════════════════════════════
head("S1. Pearson correlation matrix")
caption("Table {T:S-pearson}. Pearson product-moment correlations among the five normalised "
        "criteria (n = 77 provinces). Values on the diagonal are unity by construction "
        "and are greyed. With n = 77, |r| > 0.224 is significant at p < 0.05 and "
        "|r| > 0.291 at p < 0.01 (two-tailed).")
table(fmt_matrix("T4b_Pearson_Matrix"),
      col_widths=[3.4, 2.5, 2.5, 2.5, 2.5, 2.5], index_col=True, shade_diag=True)

head("S2. Spearman rank correlation matrix")
caption("Table {T:S-spearman}. Spearman rank correlations among the five normalised criteria "
        "(n = 77 provinces). Reported alongside Table {T:S-pearson} because several criteria are "
        "not symmetrically distributed. Agreement between the two matrices indicates "
        "the reported associations are not artefacts of distributional shape.")
table(fmt_matrix("T4c_Spearman_Matrix"),
      col_widths=[3.4, 2.5, 2.5, 2.5, 2.5, 2.5], index_col=True, shade_diag=True)

_ee = MR["equity_vs_each_efficiency"]
para("Two features of these matrices support the argument in Section 4.2. First, "
     "C2 Equity is negatively correlated with every efficiency criterion except "
     f"C1 Resource Potential, with which it is effectively unrelated "
     f"(ρ = {_ee['C1_Resource']['spearman']:+.3f}, p = {_ee['C1_Resource']['p']:.3f}). "
     f"The strongest opposition is with C4 Infrastructure Access "
     f"(ρ = {_ee['C4_Infra']['spearman']:+.3f}). Poverty in Thailand is thus not "
     "associated with poor solar resource, but with distance from the grid, low "
     "settlement density and constrained terrain. Second, the positive association "
     "between C3 Demand Density and C4 Infrastructure Access is the strongest in the "
     "matrix, reflecting the shared urban–rural gradient that also produces the mildly "
     f"elevated variance inflation factors reported in Table {{T:corr}} (maximum "
     f"{MR['vif_max']:.2f}, well below the 10.0 exclusion threshold).",
     size_after=10)

# (forced page break removed 2026-10-18: it left half-empty pages, headings now keep with next)

# ══════════════════════════════════════════════════════════════════════════════
# S3 — full ranking
# ══════════════════════════════════════════════════════════════════════════════
head("S3. Complete province ranking")
caption("Table {T:S-ranking}. All 77 provinces ranked by Priority Area Index (PAI), with priority "
        "zone and normalised criterion values. Zone boundaries follow the K-means partition of "
        "Section 4.4.")

norm = pd.read_csv(PROC / "province_criteria_normalised.csv")
summ = pd.read_csv(PROC / "province_PAI_summary.csv")[["NAME_1", "rank", "dominant_zone"]]
MC = ["C1_Resource", "C2_Equity", "C3_Demand", "C4_Infra", "C5_Physical"]
s3 = norm.merge(summ, on="NAME_1").sort_values("rank")
s3 = s3[["rank", "NAME_1", "PAI", "dominant_zone"] + MC]
s3.columns = ["Rank", "Province", "PAI", "Zone"] + NICE
s3["PAI"] = s3["PAI"].map(lambda v: f"{v:.4f}")
for c in NICE:
    s3[c] = s3[c].map(lambda v: f"{v:.3f}")
table(s3, col_widths=[1.1, 3.5, 1.5, 0.9, 1.7, 1.7, 1.7, 1.75, 1.7], font_size=7.5)

# (forced page break removed 2026-10-18: it left half-empty pages, headings now keep with next)

# ══════════════════════════════════════════════════════════════════════════════
# S4 — rank shifts
# ══════════════════════════════════════════════════════════════════════════════
head("S4. Province rank displacement under alternative weighting scenarios")
_sr = SENS_RHO   # full precision, see _sens.py
caption(f"Table {{T:S-rankshift}}. Rank of each province under the EWM baseline, under equal weighting "
        f"(1/5 per criterion) and under equity-first expert weights, with signed "
        f"displacement Δ relative to the baseline. Positive Δ denotes a fall in priority. "
        f"Rank agreement with the baseline is ρ = {_sr['equal']:.3f} for equal weighting "
        f"and ρ = {_sr['expert']:.3f} for expert weighting (Table {{T:sens}}).")

s4 = T["T9b_Rank_Detail"].copy().sort_values("Rank_EWM")
s4.columns = ["Province", "Rank (EWM)", "Rank (equal)", "Δ equal",
              "Rank (expert)", "Δ expert"]
# External check 2026-10-23: the workbook shift columns hold |Δ|, so provinces that rose (Ang Thong 4 -> 1)
# showed +3 against a caption that defines a signed Δ. Δ is now alternative rank minus baseline rank, and
# the workbook column must equal its absolute value (any other difference stops the build).
for alt, c in (("Rank (equal)", "Δ equal"), ("Rank (expert)", "Δ expert")):
    signed = s4[alt].astype(int) - s4["Rank (EWM)"].astype(int)
    assert (signed.abs() == s4[c].astype(int)).all(), f"{c}: workbook shift is not |rank difference|"
    s4[c] = signed.map(lambda v: "0" if v == 0 else f"{int(v):+d}".replace("-", "−"))
table(s4, col_widths=[4.2, 2.3, 2.3, 2.0, 2.3, 2.0], font_size=8, index_col=True)

head("S5. Spatially restricted significance tests")
_sp = MR["spatial_permutation"]
_ns = _sp["province"][0]["n_sim"]
caption(f"Table {{T:S-spatialp}}. Classical and spatially restricted p-values for the correlations on "
        f"which the paper's argument rests. Because both the province and district units "
        f"are spatially autocorrelated, classical p-values treat as independent "
        f"observations that are not. Each correlation was therefore re-tested against "
        f"{_ns} Moran-spectral surrogates generated on the Queen contiguity graph, which "
        f"preserve the observed spatial structure while breaking the association with the "
        f"covariate. Conclusions are unchanged in every case.")
rows = []
for scale, items in _sp.items():
    for r in items:
        rows.append({"Scale": scale.capitalize(), "Comparison": r["label"],
                     "Spearman ρ": f"{r['rho']:+.3f}".replace("-", "−"),
                     "p (classical)": f"{r['p_classical']:.4f}",
                     "p (spatial)": f"{r['p_spatial']:.4f}"})
s5 = pd.DataFrame(rows)
s5["Comparison"] = s5["Comparison"].str.replace(" (district)", "", regex=False)
table(s5, col_widths=[1.9, 6.6, 2.2, 2.6, 2.4], font_size=8, index_col=True)

_er = MR["equity_removal"]
para("The asymmetry between the two scenarios is discussed in main text Section 5.3: the ranking "
     "is comparatively insensitive to the precise equity weight, because objective "
     "entropy weighting and equity-first expert judgement broadly agree, but it is "
     "sensitive to the decision to weight all criteria uniformly. For reference, removing "
     "the equity criterion altogether, rather than reweighting it, displaces the "
     f"ranking further still (ρ = {_er['spearman_full_vs_eff']:.3f} against the "
     f"efficiency-only composite, maximum shift {_er['max_rank_shift']} places, "
     f"{_er['n_shift_gt10']} of 77 provinces moving by more than ten ranks).",
     size_after=10)

# (forced page break removed 2026-10-18: it left half-empty pages, headings now keep with next)
head("S6. Sensitivity to the unit of aggregation (MAUP)")
_mp = MR["maup"]
para("Any zonal index inherits the modifiable areal unit problem: the values, and the "
     "weights derived from their dispersion, depend on the areal units chosen. To bound "
     "this, the entire province pipeline, log-transform of demand, linear [0, 1] "
     "normalisation with 2nd–98th percentile clipping, float64 entropy weighting, "
     "bounded-ideal TOPSIS, was re-run unchanged at three nested scales: a coarser region "
     f"level (n = {_mp['region']['n']}, the NESDB six-region grouping, whose exact province "
     f"assignment is conventional), the province level used in the paper "
     f"(n = {_mp['province']['n']}), and a finer amphoe level (n = {_mp['amphoe']['n']}, "
     "GADM ADM-2 districts) that nests exactly inside provinces (Table {T:S-maup}).")
# weight order per scale, read from the same numbers Table S6 prints (review 2026-10-15: the text had
# hard-coded "demand at region scale, infrastructure at amphoe scale", which Run 4 no longer shows)
_CN = {"C1_Resource": "resource potential", "C2_Equity": "equity", "C3_Demand": "demand density",
       "C4_Infra": "infrastructure access", "C5_Physical": "physical suitability"}
_ord = {k: sorted(_mp[k]["weights"].items(), key=lambda kv: -kv[1]) for _, k in (("", "region"), ("", "province"), ("", "amphoe"))}
_eq_rank = {k: [c for c, _ in v].index("C2_Equity") + 1 for k, v in _ord.items()}
assert _eq_rank == {k: _mp["equity_weight_rank_by_scale"][k] for k in _eq_rank}, (_eq_rank, _mp["equity_weight_rank_by_scale"])
_eq_all_first = all(r == 1 for r in _eq_rank.values())
_lead = {k: (v[1][0], v[0][1] - v[1][1]) for k, v in _ord.items()}   # runner-up criterion and equity's margin over it
caption("Table {T:S-maup}. Entropy weights and the equity–efficiency relationship recomputed at "
        "three nested aggregation scales. Weights are MAUP-sensitive, "
        + ("but equity carries the largest weight at every scale "
           if _eq_all_first else "and equity is not the largest weight at every scale ")
        + "and the equity–efficiency association is negative throughout the sub-national hierarchy.")
_sc = [("Region", "region"), ("Province", "province"), ("Amphoe", "amphoe")]
s6 = pd.DataFrame({
    "Scale (n)": [f"{lbl} ({_mp[k]['n']})" for lbl, k in _sc],
    "C1": [f"{_mp[k]['weights']['C1_Resource']:.3f}" for _, k in _sc],
    "C2 (equity)": [f"{_mp[k]['weights']['C2_Equity']:.3f}" for _, k in _sc],
    "C3": [f"{_mp[k]['weights']['C3_Demand']:.3f}" for _, k in _sc],
    "C4": [f"{_mp[k]['weights']['C4_Infra']:.3f}" for _, k in _sc],
    "C5": [f"{_mp[k]['weights']['C5_Physical']:.3f}" for _, k in _sc],
    "equity wt. rank": [str(_mp["equity_weight_rank_by_scale"][k]) for _, k in _sc],
    "equity–eff ρ": [f"{_mp[k]['equity_vs_efficiency_rho']:+.3f}".replace("-", "−")
                     for _, k in _sc],
})
table(s6, col_widths=[2.5, 1.4, 1.9, 1.4, 1.4, 1.4, 1.8, 2.1], font_size=8.5, index_col=True)
assert _eq_all_first, "the S6 narrative below assumes equity ranks first at every scale; rewrite it if not"
para(f"Three points follow. First, the weight ordering below equity is MAUP-sensitive, as "
     f"expected, since entropy weight depends on inter-unit dispersion, which changes with the "
     f"units. Equity carries the largest weight at all three scales, but the runner-up changes "
     f"and the margin narrows away from the province level: {_CN[_lead['region'][0]]} follows "
     f"at region scale (margin {_lead['region'][1]:.3f}), {_CN[_lead['province'][0]]} at "
     f"province scale (margin {_lead['province'][1]:.3f}) and {_CN[_lead['amphoe'][0]]} at "
     f"amphoe scale (margin {_lead['amphoe'][1]:.3f}). Second, the paper's substantive claim, "
     f"that entropy weighting gives equity the largest weight in Thailand because poverty "
     f"differentiates the units most strongly, therefore "
     f"does not depend on the choice of province as the unit, although at region and amphoe "
     f"scale equity leads by a narrow margin. Third, the efficiency–equity "
     f"tension stays negative across the entire sub-national hierarchy "
     f"(region {_mp['region']['equity_vs_efficiency_rho']:+.3f}, province "
     f"{_mp['province']['equity_vs_efficiency_rho']:+.3f}, amphoe "
     f"{_mp['amphoe']['equity_vs_efficiency_rho']:+.3f}, p < 0.001 at amphoe scale, "   # 3 dp as stored, no double rounding
     f"n = {_mp['amphoe']['n']}). That it appears at every level from region to amphoe, "
     f"and vanishes only within a single city (Section S12.2), is direct evidence "
     f"that the scale-dependence is a property of the geography, not an artefact of the "
     f"province grid. Finally, aggregating the amphoe PAI back to provinces reproduces the "
     f"direct province ranking closely (Spearman ρ = "
     f"{_mp['province_vs_amphoe_mean']['spearman']:.3f}, "
     f"n = {_mp['province_vs_amphoe_mean']['n']}), confirming the province ordering is not "
     f"itself a MAUP artefact.", size_after=10)
# cell-area check (review item 4, 2026-10-16): the 0.000833 deg grid is in EPSG:4326, so cell area varies
# with latitude. Post hoc check by Scripts/area_weight_check.py, numbers read from its output.
_AW = json.loads((BASE / "Data" / "area_weight_check" / "area_weight_check.json").read_text(encoding="utf-8"))
assert _AW["zones_agree_77"] == 77 and _AW["S2_same"] and _AW["S3_same"]
para("Cell-area weighting. The criterion rasters share a 0.000833° grid in geographic coordinates "
     f"(WGS 84, EPSG:4326), about {_AW['grid']['ns_m']:.0f} m north–south and "
     f"{_AW['grid']['ew_m_at_20N']:.0f}–{_AW['grid']['ew_m_at_6N']:.0f} m east–west across Thailand, so a "
     "cell's ground area falls with latitude. Province values are unweighted cell means. As a post "
     "hoc check, every province mean was recomputed with each cell weighted by the cosine of its "
     "latitude and the province pipeline was rerun unchanged. Within a province the cell area varies "
     f"by at most {_AW['within_province_area_weight_spread_max_pct']:.1f}%, the largest change in a "
     f"province mean was {100 * max(_AW['max_relative_change_of_province_means'].values()):.1f}%, the "
     f"equity weight moved from {_AW['weights_unweighted']['C2_Equity']:.4f} to "
     f"{_AW['weights_area_weighted']['C2_Equity']:.4f}, no PAI changed by more than "
     f"{_AW['max_abs_PAI_change']:.4f} (Spearman ρ = {_AW['spearman_rank']:.5f}, at most "
     f"{_AW['max_rank_change']} rank), and all {_AW['zones_agree_77']} zone assignments and the S2 and "
     "S3 memberships were unchanged.", size_after=10)

# (forced page break removed 2026-10-18: it left half-empty pages, headings now keep with next)
head("S7. Local spatial clusters (LISA) with multiple-comparison correction")
_lf = MR["lisa_fdr"]
caption(f"Table {{T:S-lisa}}. The {_lf['n_raw_sig']} provinces reaching the unadjusted α = 0.05 in "
        f"the local Moran (LISA) analysis, with Benjamini–Hochberg false-discovery-rate "
        f"adjusted p-values across all {_lf['n_tests']} province tests. "
        + ("None survives " if _FDR0 else f"{_lf['n_fdr_sig']} survive ") +
        f"correction (smallest adjusted p = {_lf['min_p_bh']:.3f}). The local clusters in "
        f"Section S13.6 and Fig. {{F:lisa}} are therefore exploratory. The global Moran's I "
        f"({moran()}) is a single test and is "
        f"unaffected.")
_lisa = pd.read_csv(PROC / "province_LISA_fdr.csv")
if "p_bh" not in _lisa.columns:                       # repo script names the BH column LISA_p_fdr
    _lisa["p_bh"] = _lisa["LISA_p_fdr"]
if "dominant_zone" not in _lisa.columns:
    _lisa = _lisa.merge(pd.read_csv(PROC / "province_PAI_summary.csv")[["NAME_1", "dominant_zone"]], on="NAME_1")
_lisa = _lisa[_lisa.LISA_p < 0.05].sort_values("LISA_p")
s7 = pd.DataFrame({
    "Province": _lisa.NAME_1.values,
    "Zone": _lisa.dominant_zone.astype(int).values,
    "Cluster type": _lisa.LISA_type.values,
    "p (unadjusted)": [f"{v:.3f}" for v in _lisa.LISA_p],
    "p (BH-FDR)": [f"{v:.3f}" for v in _lisa.p_bh],
    "Significant after FDR": ["yes" if v < 0.05 else "no" for v in _lisa.p_bh],
})
table(s7, col_widths=[3.6, 1.3, 2.2, 2.6, 2.4, 3.0], font_size=8.5, index_col=True)

# (forced page break removed 2026-10-18: it left half-empty pages, headings now keep with next)
head("S8. Construction of the author-built composite socioeconomic indices")
para("The equity criterion at district scale (Section S12.1) and the construct "
     "check at province scale (Section S13.8, Table {T:construct}) use two composite indices built by "
     "the authors from official source data. Neither is an official published product. Both "
     "are research prototypes, documented here for transparency. Each raw indicator is "
     "converted to a percentile rank (0–100) within its unit set (50 khet, 77 provinces), "
     "so all components share a common bounded scale and no external normalisation is "
     "needed. Right-skewed monetary inputs are Winsorised at the 95th percentile before "
     "ranking. There are no missing values in either unit set. Only the vulnerability "
     "sub-index (FV) of each index enters this paper, as the district equity slot, and as "
     "the comparison variable in Table {T:construct}. The per-unit scores are deposited with the "
     "analysis data (BKK_District_Index_2567_GIS_v1.csv, "
     "Thailand_Provincial_Index_2566_2567_GIS_v1.csv), so the comparisons are reproducible "
     "from the deposited scores.")
para("Bangkok district vulnerability index FV (base year 2024, equal-weight baseline "
     "model v1.0). The overall resilience score is SER = 0.50·EC + 0.50·(100 − FV). This "
     "paper uses only FV, an equal-weight mean of the four components in Table {T:S-index-a}. Source "
     "for all inputs: Bangkok Metropolitan Administration district administrative "
     "statistics, base year 2024.")
caption("Table {T:S-index-a}. Components of the Bangkok district vulnerability sub-index FV "
        "(equal weights, each raw value percentile-ranked 0–100 within the 50 khet, "
        "higher = more vulnerable).")
s8a = pd.DataFrame({
    "Component": ["V1 Slum share", "V2 Crowding", "V3 Green deficit", "V4 Disaster"],
    "Formula (raw)": ["slum communities / total communities × 100",
                      "registered population / houses",
                      "100 − pctile(green area / population)",
                      "disaster events / 10,000 houses"],
    "Direction": ["higher = worse", "higher = worse",
                  "reverse-signed", "higher = worse"],
    "Weight": ["0.25", "0.25", "0.25", "0.25"],
})
table(s8a, col_widths=[2.5, 6.4, 2.6, 1.6], font_size=8.5, index_col=True)
para("Provincial vulnerability index FV (reference period 2566–2567). The overall "
     "resilience score is SER = 0.50·EC + 0.50·(100 − FV). This paper compares against FV "
     "and the overall resilience score in Table {T:construct}. Source for all inputs: official "
     "NESDC/NSO provincial statistics (gross provincial product, household income and "
     "expenditure, debt, employment), reference year 2566.")
caption("Table {T:S-index-b}. Components of the provincial vulnerability sub-index FV (each raw "
        "value percentile-ranked 0–100 within the 77 provinces, higher = more "
        "vulnerable).")
s8b = pd.DataFrame({
    "Component": ["V1 Poverty burden (proxy)", "V2 Expenditure-to-income",
                  "V3 Debt-to-income", "V4 Population change"],
    "Formula (raw)": ["estimated poor headcount / registered population × 100",
                      "mean monthly household expenditure / income",
                      "mean household debt / annual income",
                      "annual population-change rate"],
    "Direction": ["higher = worse", "higher = worse", "higher = worse",
                  "lower growth / decline = worse (reverse-ranked)"],
    "Weight": ["0.35", "0.25", "0.25", "0.15"],
})
table(s8b, col_widths=[3.0, 5.6, 2.4, 1.6], font_size=8.5, index_col=True)
para("The V1 poverty-burden term is a proxy (estimated poor headcount over registered "
     "population, from different data systems) and shares the poverty construct of the "
     "paper's C2 criterion. The convergent rows of Table {T:construct} are therefore not independent "
     "of C2 and are reported as internal consistency. Where an official provincial poverty "
     "rate is available it should replace this proxy. The economic sub-index EC (not used "
     "as an equity slot in this paper) weights GPP per capita (0.25), household income "
     "(0.20), Social Security Article-33 insured share (0.20) and further components. Its "
     "full specification is in the deposited methodology file.", size_after=10)

# ── S9. PAI-MV grid-criterion sensitivity ─────────────────────────────────────
head("S9. Sensitivity to the grid criterion: power-line proximity versus LV density")
_mv = MR["pai_mv"]
caption("Table {T:S-lv}. Province-level EWM weights under the baseline C4 (proximity to "
        "OSM-mapped power lines) and under a variant in which C4 is replaced by the "
        "province mean of a GridFinder low-voltage (LV) density surface "
        "(C5_grid_access_90m.tif, a normalised index built from gridfinder_lv_thailand.tif, "
        "not a distance and not a medium-voltage layer). Both runs use the same float64 "
        "entropy weighting and bounded-ideal TOPSIS on the 77 provinces.")
_wp, _wm = _mv["weights_published"], _mv["weights_mv"]
s9 = pd.DataFrame({
    "Criterion": ["C1 Resource", "C2 Equity", "C3 Demand", "C4 Infrastructure", "C5 Physical"],
    "Baseline w (C4 = power-line proximity)": [f"{_wp['C1_Resource']:.3f}", f"{_wp['C2_Equity']:.3f}",
        f"{_wp['C3_Demand']:.3f}", f"{_wp['C4_Infra']:.3f}", f"{_wp['C5_Physical']:.3f}"],
    "Variant w (C4 = LV density)": [f"{_wm['C1_Resource']:.3f}", f"{_wm['C2_Equity']:.3f}",
        f"{_wm['C3_Demand']:.3f}", f"{_wm['C4_MV']:.3f}", f"{_wm['C5_Physical']:.3f}"],
})
table(s9, col_widths=[3.2, 3.4, 3.4], font_size=8.5, index_col=True)
para(
    f"The LV-density surface is strongly right-skewed (skewness {_mv['c4mv_skew']:.2f} "
    f"versus {_mv['c4trans_skew']:.2f} for the power-line criterion) because LV density is "
    f"concentrated in the Bangkok metropolitan cluster. Entropy weighting therefore inflates "
    f"its weight to {_mv['c4mv_weight']:.2f}. Despite this, the variant PAI ranks the 77 "
    f"provinces almost identically to the published PAI (Spearman ρ = "
    f"{_mv['spearman_paiMV_vs_published']:.3f}, p < 0.001, maximum rank shift "
    f"{_mv['rank_shift_max']}, {_mv['rank_shift_n_gt10']} of 77 provinces moving more than "
    f"ten ranks), and the two surfaces are positively correlated across provinces "
    f"(ρ = {_mv['spearman_C4trans_vs_C4mv']:.3f}). K-means zoning is more sensitive: the "
    f"inflated LV-density weight isolates a Bangkok-only top cluster, so "
    f"{_mv['zone1_retained']} of the {_mv['zone1_baseline_n']} baseline Zone-1 provinces are "
    f"retained, which is the reason the better-distributed power-line criterion is used in the "
    f"baseline. The efficiency–equity association is essentially unchanged (ρ = "
    f"{_mv['efficiency_equity_mv']:.3f}, p = {_mv['efficiency_equity_mv_p']:.3f}, versus "
    f"{MR['equity_vs_efficiency_only']['spearman']:.3f} at baseline), so the paper's central result "   # baseline from MR (sensitivity_pai_mv.json stores a typed -0.391)
    f"does not depend on the grid-criterion specification.", size_after=10)

# (forced page break removed 2026-10-18: it left half-empty pages, headings now keep with next)
head("S10. Data sources and provenance")
caption("Table {T:S-sources}. Data sources, provenance and processing routes for the spatial and "
        "administrative inputs used in the study. Native scale is the scale supplied by the "
        "provider. It is distinct from the 90 m working grid used for the province analysis. "
        "Items identified as screening or sensitivity inputs do not enter the baseline PAI.")
para("The table records the authoritative access route and the analysis script that implements "
     "each processing step. Resampling to the working grid harmonises spatial support but "
     "does not create finer socioeconomic information than the native provincial statistic. "
     "The OpenStreetMap layers were retrieved with the Overpass queries in "
     "scripts/data_download/download_grid_osm.py of the code repository (way features tagged "
     "power=line and power=cable, and way and node features tagged power=plant, within the "
     "bounding box 5.5–20.5° N, 97.5–105.7° E), database state 22 June 2026.",
     size_after=6)
s10 = pd.DataFrame([
    {"Role": "C1 Resource", "Dataset and provider": "Global Solar Atlas v2, PVOUT long-term annual yield", "Version / native scale": "v2, 1 km raster", "Period / access": "Long-term average, files dated 2026-06-17", "Use and processing": "Annual PV output resampled to 90 m by bilinear interpolation, 2nd-98th percentile normalisation at pixel level, then province mean rescaled once at province level.", "Access route / script": "globalsolaratlas.info, Scripts/02_Preprocessing/compute_c1_pvout_90m.py"},
    {"Role": "C2 Equity", "Dataset and provider": "NESDC Poverty and Income Distribution, Table 1.5, NSO socioeconomic survey", "Version / native scale": "Province statistic", "Period / access": "2022 (B.E. 2565), workbook dated 2026-07-12", "Use and processing": "Provincial poverty incidence (%) rasterised to 90 m as the raw percentage, constant within each province, benefit direction. Clipped at the 2nd and 98th percentiles and scaled to [0, 1] once, at province level.", "Access route / script": "nesdc.go.th, Scripts/02_Preprocessing/rasterize_c2_poverty.py"},
    {"Role": "C3 Demand", "Dataset and provider": "WorldPop unconstrained population", "Version / native scale": "2020 UN-adjusted, 100 m raster", "Period / access": "2020, downloaded 2026-06-15 (download log)", "Use and processing": "Population density resampled to 90 m and 2nd-98th percentile normalised at pixel level. The province mean is log-transformed, log(1 + 100x), then rescaled once at province level.", "Access route / script": "hub.worldpop.org, Scripts/02_Preprocessing/compute_c3_popdens_90m.py"},
    {"Role": "C4 Infrastructure", "Dataset and provider": "OpenStreetMap power lines and cables (power=line, power=cable)", "Version / native scale": "Vector network", "Period / access": "OSM database state 2026-06-22 (Overpass timestamp)", "Use and processing": "Distance to the mapped power lines converted to an exponential proximity score with a 5 km scale, then zonally aggregated.", "Access route / script": "openstreetmap.org, Overpass API, preprocessing scripts in Scripts/02_Preprocessing"},
    {"Role": "C5 Physical: forest", "Dataset and provider": "Hansen Global Forest Change, University of Maryland", "Version / native scale": "v1.11 treecover2000, 30 m raster", "Period / access": "Dataset release 2023, processed in GEE", "Use and processing": "Tree-cover constraint exported at 90 m and combined with terrain and built-environment components.", "Access route / script": "Earth Engine dataset catalog, Scripts/GEE/04_hansen_forest.py"},
    {"Role": "C5 Physical: terrain", "Dataset and provider": "Copernicus DEM GLO-30", "Version / native scale": "GLO-30, 30 m raster", "Period / access": "Tiles dated 2026-06-17 to 2026-06-21", "Use and processing": "Slope derived from the DEM and represented as a terrain-suitability constraint on the 90 m grid.", "Access route / script": "copernicus.eu/dem, Scripts/GEE/05_copernicus_dem.py"},
    {"Role": "C5 Physical: built environment", "Dataset and provider": "JRC GHSL GHS-BUILT-H ANBH", "Version / native scale": "E2018 R2023A v1.0, 3 arc-second raster (about 90 m)", "Period / access": "Reference epoch 2018, tiles dated 2026-07-03", "Use and processing": "Built-environment constraint aligned to the 90 m analysis grid and combined into C5.", "Access route / script": "ghsl.jrc.ec.europa.eu, Scripts/02_Preprocessing/download_ghsl_building_height.py"},
    {"Role": "Administrative aggregation", "Dataset and provider": "GADM administrative boundaries, Thailand", "Version / native scale": "v4.1, province and district polygons", "Period / access": "Downloaded 2026-06-15 (download log)", "Use and processing": "Province, amphoe and Bangkok district masks for zonal statistics, rankings and scale-sensitivity checks.", "Access route / script": "gadm.org, Data/01_Raw_Vector/gadm41_THA.gpkg"},
    {"Role": "Solar deployment comparison", "Dataset and provider": "OpenStreetMap solar power plants", "Version / native scale": "Point and polygon vector features", "Period / access": "OSM database state 2026-06-22 (Overpass timestamp)", "Use and processing": "Overpass query for power=plant and plant:source=solar, used only for descriptive deployment comparison.", "Access route / script": "openstreetmap.org, Overpass API"},
    {"Role": "Bangkok rooftop yield", "Dataset and provider": "Google Open Buildings footprint coverage", "Version / native scale": "v3 polygons (Earth Engine asset GOOGLE/Research/open-buildings/v3/polygons)", "Period / access": "Exported raster dated 2026-07-11 (GoogleOB_v3_density_30m_Bangkok.tif)", "Use and processing": "Footprint coverage rasterised and aggregated to the 50 khet, used for the district rooftop opportunity measure.", "Access route / script": "developers.google.com/open-buildings, Scripts/GEE/run_bangkok_density_export.py"},
    {"Role": "Bangkok district equity", "Dataset and provider": "Bangkok Metropolitan Administration district administrative statistics", "Version / native scale": "District statistics, 50 khet", "Period / access": "Base year 2024", "Use and processing": "Author-built vulnerability index from slum share, crowding, green deficit and disaster indicators, full construction in Section S8.", "Access route / script": "BMA administrative statistics, supplementary Section S8"},
    {"Role": "Provincial construct check", "Dataset and provider": "Author-built Thailand Provincial Socioeconomic and Financial Resilience Index (vulnerability FV and overall score SER) from NESDC/NSO provincial statistics", "Version / native scale": "v1.0 weighted baseline model, 77 provinces (Thailand_Provincial_Index_2566_2567_GIS_v1.csv)", "Period / access": "Reference period 2566–2567 (2023–2024), files dated 2026-07-12", "Use and processing": "External comparison only (Table {T:construct}), full construction in Section S8. It does not enter the PAI.", "Access route / script": "Supplementary Section S8, Scripts/06_Priority_Areas/validate_ser_external.py"},
    {"Role": "Map base layer (main-text Fig. {F:study-region} only)", "Dataset and provider": "Natural Earth Admin 0 countries", "Version / native scale": "v5.1.1, 1:10m vector", "Period / access": "Downloaded 2026-06-15", "Use and processing": "Neighbouring countries drawn as context in the study-region map. No analytical use.", "Access route / script": "naturalearthdata.com, DER_TEJ/Scripts/figures/fig02_study_area_tej.py"},
    {"Role": "LV-density sensitivity only", "Dataset and provider": "GridFinder modelled low-voltage density (Arderne et al.)", "Version / native scale": "gridfinder_lv_thailand.tif, 250 m raster (ESRI:54009)", "Period / access": "Used for the Table {T:S-lv} sensitivity", "Use and processing": "Normalised to [0,1] (2nd-98th percentile of non-zero cells) on the 90 m grid, province mean replaces C4 only in Table {T:S-lv}. Not a distance and not an MV layer.", "Access route / script": "GridFinder, Scripts/02_Preprocessing/compute_c5_grid_access_90m.py"},
    {"Role": "Modelled MV distance (TEJ screen)", "Dataset and provider": "GridFinder modelled medium-voltage lines (Arderne et al.)", "Version / native scale": "gridfinder_mv_lines_thailand.gpkg, 36,027 line features", "Period / access": "Clipped 2026-06-23", "Use and processing": "Euclidean distance from 90 m cells (EPSG:32647, cell centre inside the GADM 4.1 province union) to the nearest modelled MV line, province mean. A modelled network, not the utility network.", "Access route / script": "DER_TEJ/Scripts/mv_distance.py"},
    {"Role": "Step 1 screen, excluded", "Dataset and provider": "VIIRS DNB annual night-time radiance, Thailand TGO grid emission factor", "Version / native scale": "2022 annual composite, raster", "Period / access": "2022", "Use and processing": "Exploratory energy-related proxy, excluded because it overlaps with C3 demand density. It does not enter the PAI. Post hoc diagnostic in Section S13.11.", "Access route / script": "Earth Engine VIIRS catalog, TGO EFEC 2022, preprocessing records"},
])
table(s10, col_widths=[1.35, 2.85, 1.85, 1.55, 4.30, 4.00], font_size=7.0, index_col=True)

# ── S11. Zone-to-policy screen: full version and primary sources (TEJ) ─────────
# (forced page break removed 2026-10-18: it left half-empty pages, headings now keep with next)
head("S11. Zone-to-policy screen: full legal basis and primary sources")
para("Table {T:S-policy-full} gives the full version of main-text Table {T:policy}. Instruments, institutions and "
     "regulatory bases are taken only from primary documents read by the authors (Table {T:S-policy-docs}). "
     "The column 'Observed policy gap (study inference)' is limited to the instruments examined "
     "and is not a statement about all Thai policy. The progressive residential tariff (I3) is "
     "listed as equity context and a consumer-protection instrument, not as a deployment "
     "instrument. The Energy Conservation Promotion Fund (I4) is a conditional candidate, because "
     "its eligibility for distributed solar investment was not established from the Act text. "
     "Institutions are named only where a primary document assigns them a role.", size_after=8)
_s11 = pd.read_csv(BASE / "Tables" / "zone_policy_table_full_supp.csv")
_s11 = _s11[["Zone", "Observed policy gap (study inference)", "Candidate policy response",
             "Implementation gate", "Responsible institution", "Regulatory basis", "Official citation"]]
_s11["Official citation"] = _s11["Official citation"].str.replace(" (D5_POLICY_REGISTER.md)", "", regex=False)
_s11 = _s11.replace({r";\s*": ", "}, regex=True)  # no semicolons in rendered cells, source data untouched
caption("Table {T:S-policy-full}. Zone-to-policy screen, full version. Citation IDs refer to Table {T:S-policy-docs}.")
table(_s11, col_widths=[0.9, 2.6, 2.4, 2.6, 2.6, 3.1, 1.7], font_size=6.5)
_src = pd.read_json(BASE / "Data" / "policy" / "source_index.json")
caption("Table {T:S-policy-docs}. Primary documents used for the zone-to-policy screen.")
table(_src, col_widths=[0.9, 1.3, 5.2, 3.0, 2.6, 2.9], font_size=6.5)

# ── S12. Urban application under the MEA context (moved from the main text, TEJ) ─
# (forced page break removed 2026-10-18: it left half-empty pages, headings now keep with next)
head("S12. Urban application under the MEA context")
para("This section reports the application of the framework within the 50 districts (khet) of "
     "Bangkok, which are served by the Metropolitan Electricity Authority (MEA). It is kept out of "
     "the main text because its spatial unit, utility, data construction and policy instruments "
     "differ from those of the 74 PEA-served provinces. A district-level screen cannot replace "
     "MEA feeder data, which this application did not have. The text below is the district "
     "analysis of the earlier version of this study, with cross-references renumbered.", size_after=8)
S12_FIGCAP = 'District-scale demonstration, Bangkok Metropolitan Administration (50 khet): (a) district Priority Area Index (PAI) choropleth. (b) K-means priority zones (k = 5). Four-criterion intra-city model, rooftop-solar yield, equity (author-built district vulnerability index from BMA data), demand density, and infrastructure access. Within the city the equity criterion is effectively independent of the efficiency criteria (ρ = +0.064, p = 0.66), in contrast to the negative association found between provinces (ρ = ' + f"{MR['equity_vs_efficiency_only']['spearman']:.3f}".replace("-", "−") + ').'
head("S12.1 Methods: Bangkok's 50 khet", size_pt=12)
para(
    "The same framework was re-applied within a single "
    "metropolitan area, the 50 districts (khet) of the Bangkok Metropolitan Administration "
    "(BMA, GADM level-2 boundaries). Steps 1 to 4 of the workflow (main-text Fig. {F:framework}) were "
    "reproduced. The decision comparison of Step 5 and the "
    "installation-based deployment comparisons were not repeated, as comparable district-level "
    "records were unavailable. Applying the framework at this scale required two "
    "adaptations of the criterion set, each of which is itself an informative result about "
    "how the framework's criterion dimensions behave within a city."
)
para(
    "First, the resource and physical slots merge. Solar potential is physically "
    "near-uniform within a single city: across the 50 khet, PVOUT spans only about "
    "1,424–1,522 kWh kWp⁻¹ yr⁻¹ (≈ 7%). Re-normalising so small a range to [0, 1] "
    "manufactures a dominant entropy weight from a gradient no planner would act on. The "
    "resource and physical slots were therefore combined into a single rooftop-solar-yield "
    "criterion, the product of solar potential and building-footprint coverage density "
    "(sunlight × available roof), the latter derived from Google Open Buildings v3 "
    "(paint-rasterised at 5 m and areal-averaged to 30 m). Building density discriminated "
    "strongly between khet (CV = 30.6%), unlike the province forest/slope suitability "
    "raster, which is near-constant within the built metropolis (CV = 0.4%)."
)
para(
    "Second, the equity slot requires a scale-appropriate indicator. Provincial poverty "
    "incidence is published only at provincial resolution, and a remote-sensing substitute "
    "first tested, inverted night-time light per capita, proved invalid within a city, "
    "reflecting commercial land use rather than household affordability (Section S12.2). The "
    "equity slot was therefore populated at the correct granularity by an author-constructed "
    "composite vulnerability index built from official Bangkok Metropolitan Administration "
    "(BMA) source data (its construction is documented in Section S8), a research-prototype index (not an official BMA product) "
    "combining slum-community share, residential crowding, green-space deficit and disaster "
    "incidence. Its construction, component weights and per-district scores are given in the "
    "supplementary material. This yields a "
    "four-criterion district model, rooftop-solar yield, equity, demand density and "
    "infrastructure access, mirroring the provincial slots after the resource–physical "
    "merge. Drawing the equity slot from a different, scale-appropriate source is itself an "
    "instance of the framework's criterion transferability (Section S13.2). EWM weighting, TOPSIS "
    "scoring, K-means zoning "
    "(k = 5), and Global Moran's I were otherwise computed exactly as for the provincial run."
)
para(
    "The construct measured at district scale is therefore social vulnerability, not "
    "household poverty, and the distinction is deliberate rather than a compromise. For "
    "the specific question of DER equity, the components of the vulnerability index are "
    "the energy-relevant ones: overcrowded and slum housing is associated with higher "
    "energy burden and with the least capacity to finance private rooftop photovoltaics, "
    "and it is registered communities of this kind, not high-income low-density districts, "
    "that a municipal DER-equity programme would target. A direct validation of this "
    "slot against household income or electricity expenditure per khet would be preferable "
    "but is not possible with public data: neither BMA nor the National Statistical Office "
    "releases income or metered-consumption microdata at sub-district resolution, which is "
    "the reason a purpose-built vulnerability index is used here and why the provincial and "
    "district equity slots are populated from different official sources. Two implications "
    "follow and are carried through the paper: the district results are stated in terms of "
    "vulnerability rather than poverty (Sections S12.2 and S12.3), and the cross-scale claim is "
    "about the efficiency–equity relationship under a construct-valid, scale-appropriate "
    "equity indicator at each scale, not about a single identical variable measured twice."
)
head("S12.2 Results", size_pt=12)
para(
    "The four-criterion district model ran cleanly across the 50 khet (Fig. {F:S-district}). EWM "
    "assigned the largest weight to infrastructure access and the smallest to demand "
    "density. District PAI ranged from 0.317 to 0.827 (mean = 0.586, Table {T:S-district}). The "
    "highest-priority khet combine strong "
    "efficiency and high social vulnerability, Samphanthawong (the dense historic "
    "commercial core), Bang Rak, Rat Burana, Bang Sue, Din Daeng, and Chom Thong, while "
    "the lowest-priority khet are the sparsely built, low-vulnerability outer fringe (Khan "
    "Na Yao, Nong Chok, Bang Khen). Global Moran's I for the district PAI was 0.274 "
    f"(permutation p = 0.002, 999 permutations), close to the provincial value ({_MI['I']:.3f}): at "
    "both scales "
    "priority is moderately clustered, forming several distinct pockets rather than one "
    "contiguous frontier."
)
caption(
    "Table {T:S-district}. District-scale EWM weights and Spearman correlation of each criterion with "
    "the district PAI (n = 50 Bangkok khet, four-criterion intra-city model)."
)
t13 = pd.DataFrame({
    "Criterion": ["C1 Rooftop-solar yield", "C2 Equity (social vulnerability)",
                  "C3 Demand density", "C4 Infrastructure access"],
    "EWM weight": [0.276, 0.263, 0.115, 0.346],
    "Spearman ρ vs PAI": [0.398, 0.444, 0.257, 0.721],
    "p": ["0.004", "0.001", "0.071", "<0.001"],
})
table(t13, col_widths=[5.5, 2.3, 3.2, 2.0], font_size=8.5)
doc.add_picture(str(figin("S-district")), width=Cm(15.5))   # TEJ copy (panel labels a/b)
caption('Fig. {F:S-district}. ' + S12_FIGCAP + ' Map lines delineate study areas and do not necessarily depict accepted national boundaries. Geographic coordinates, WGS 84 (EPSG:4326).')
para(
    "The central result concerns how the equity criterion relates to the efficiency "
    "criteria once it is measured validly at each scale, and here the two scales diverge. "
    f"Within Bangkok, the association between equity and the efficiency-only composite "
    f"(rooftop yield, demand, infrastructure) is not statistically distinguishable from "
    f"zero (ρ = +0.064, p = 0.66, p = "
    f"{MR['p_spatial']['C2 Equity vs efficiency-only composite (district)']:.3f} under "
    f"spatially restricted permutation), and its pairwise correlations with those criteria "
    f"are likewise small and non-significant (rooftop yield −0.124, p = 0.39, demand "
    f"−0.088, p = 0.54, infrastructure +0.125, p = 0.39). Between provinces the same "
    f"relationship is clearly negative "
    f"(ρ = {MR['equity_vs_efficiency_only']['spearman']:.3f}, p < 0.001, main text Section 4.2). The "
    f"evidence is therefore consistent with a real trade-off between provinces and with "
    f"no detectable trade-off within the city, a scale-conditioned association rather "
    f"than a fixed property of the framework. The district result is an absence of "
    f"evidence at n = 50, not evidence of exact independence: the interval around "
    f"ρ = +0.064 remains wide enough to admit a weak association in either direction."
)
para(
    "The divergence has a straightforward geographic explanation and a substantive planning "
    "consequence. Between provinces, poverty is confounded with peripherality: Thailand's "
    "poorest provinces are also its farthest from the mapped power-line network, its least "
    "densely settled and its most topographically constrained, so serving need and serving "
    "convenience genuinely conflict. Within a single city those confounds largely dissolve, "
    "every khet sits inside the same metropolitan grid, at comparable latitude, on "
    "comparably buildable land, leaving social vulnerability free to vary independently of "
    "deployment convenience (interpreted further in Section S12.3). With the invalid "
    "night-light proxy of Section S12.1 in the equity slot the term had instead appeared "
    "strongly correlated with the composite (ρ = 0.733), an artefact of urban built form. "
    "The valid BMA measure reduces this to a level not distinguishable from zero. Two "
    "changes nonetheless coincide between the scales, the geography (peripherality "
    "confounded with poverty nationally, but constant within the city) and the equity "
    "construct itself (poverty incidence between provinces versus multidimensional "
    "vulnerability within the city), so the difference is best read as scale-conditioned "
    "under scale-appropriate measures, not attributed to geography alone."
)
# review item 6 (2026-10-16): the earlier text named ranks 1, 3 and 6 as "the ranking is led by" and
# claimed targeting "at little cost in technical yield" through municipal mandates and subsidies, neither
# of which this analysis measured. Top three now read in rank order, policy reading made conditional.
_tk = sorted(MR["district"]["top_khet"], key=lambda r: r["rank"])
assert [r["rank"] for r in _tk[:3]] == [1, 2, 3], _tk[:3]
para(
    "For a city administration the reading is narrower. Within Bangkok, need and the technical "
    "criteria used here do not pull apart at district scale: the ranking is led by "
    f"{_tk[0]['name']} (vulnerability {_tk[0]['vuln']:.2f}), {_tk[1]['name']} "
    f"({_tk[1]['vuln']:.2f}) and {_tk[2]['name']} ({_tk[2]['vuln']:.2f}), and vulnerability is "
    f"positively associated with the composite (ρ = {MR['district']['vuln_vs_pai_spearman']:.3f}), "
    "the opposite sign to the provincial relationship. This suggests that a municipal rooftop- "
    "or community-solar programme could direct support to its most vulnerable districts without "
    "trading off the resource, demand and infrastructure criteria of the index. Whether it could "
    "do so at low cost, and through which instruments, could be investigated but is not shown "
    "here: the analysis has no data on energy yield, programme cost, feeder capacity, household "
    "uptake or the legal powers of the metropolitan authority."
)
head("S12.3 Scale-conditioned relationships and proxy validity", size_pt=12)
para(
    "The two-scale demonstration surfaces a finding neither scale alone could have "
    "produced (Section S12.2). What is common to both scales is not the sign of the "
    "efficiency–equity relationship but the fact that the equity criterion carries "
    "information the resource, demand and infrastructure criteria do not, so a purely "
    "technical index would overlook the disadvantaged at either scale, though for different "
    "reasons and at different cost."
)
para(
    "The direction of the scale-dependence, however, is specific to the Thai context and "
    "should not be read as a general law. The between-province tension arises because, in "
    "Thailand, poverty is strongly confounded with peripherality: the poorest provinces are "
    "also the farthest from the mapped power-line network, the least densely settled and the most "
    "topographically constrained, a pattern rooted in the country's marked regional "
    "inequality between the metropolitan Central region and the north-eastern and "
    "southern-border peripheries. Its disappearance within Bangkok arises because that "
    "confound dissolves inside a single metropolitan grid, though the equity construct "
    "also changes with scale (poverty incidence between provinces, multidimensional "
    "vulnerability within the city), so the scale and construct effects are not fully "
    "separable and the change is reported as scale-conditioned rather than purely "
    "geographic. In a country whose poverty is "
    "not geographically confounded with grid access, or in a polycentric or more spatially "
    "equal city, the relationship could be weaker, absent, or of the opposite sign at "
    "either scale. The claim we draw is therefore not that DER equity is costly "
    "nationally and free locally, but the conditional one: the efficiency cost of pursuing "
    "equity depends on how far the chosen equity dimension is spatially entangled with the "
    "efficiency criteria at the scale of the decision, and that entanglement must be "
    "measured in each new context rather than assumed. The present results establish that "
    "such scale-dependence can be large enough to reverse a policy conclusion, which is "
    "the general lesson, while leaving its direction an empirical question elsewhere."
)
para(
    "Two methodological lessons follow, both generalising beyond DER siting. First, studies "
    "reporting that equity-aware siting entails an efficiency penalty and those reporting it "
    "does not may both be correct at the scale each examined. Generalising either is unsafe. "
    "Second, the finding was recoverable only because equity was measured with a "
    "construct-appropriate indicator at each scale, official provincial poverty incidence, "
    "and an author-constructed district vulnerability index built from BMA source data. The "
    "convenient night-light proxy tested first agreed with official "
    "poverty only weakly (ρ = 0.15, non-significant) and, forced into the intra-city model, "
    "manufactured a spurious efficiency–equity alignment (ρ = 0.733) that dissolved under "
    "scrutiny into a built-form artefact (Section S12.2). In any entropy- or variance-weighted "
    "spatial index, an equity criterion must be validated as measuring the construct it "
    "names before its behaviour across scales is interpreted, the choice of indicator "
    "determines what the method can find."
)

# ── S13. Method details and extended results (moved from the main text in F, TEJ) ─
# (forced page break removed 2026-10-18: it left half-empty pages, headings now keep with next)
from _equations import init_eq, eq
init_eq(doc, lambda r, size: _tnr(r, size_pt=size), prefix="S13.")
CRIT_RENAME = {
    "C1 Solar":     "C1 Resource",
    "C2 Poverty":   "C2 Equity",
    "C3 PopDens":   "C3 Demand",
    "C4 GridDist":  "C4 Infra",
    "C5 LandSuit":  "C5 Physical",
    "Solar Potential":    "Resource Potential (solar)",
    "Energy Poverty":     "Equity (poverty incidence)",
    "Population Density": "Demand Density (population)",
    "Grid Accessibility": "Infrastructure Access (grid)",
    "Land Suitability":   "Physical Suitability (land)",
}

def _ren(s):
    for k in sorted(CRIT_RENAME, key=len, reverse=True):
        s = s.replace(k, CRIT_RENAME[k])
    return s

def rename_crit(df):
    df = df.copy()
    df.columns = [_ren(str(c)) for c in df.columns]
    for col in df.columns:
        # Pandas 3 may infer text columns as StringDtype instead of object.
        # Apply the terminology map by value type so the generated supplement
        # is invariant to the pandas version used for the build.
        df[col] = df[col].map(lambda v: _ren(v) if isinstance(v, str) else v)
    return df

Wt, En = MR["weights_full"], MR["entropy_full"]
def wt(c): return f"{Wt[c]:.3f}"
def en(c): return f"{En[c]:.3f}"


def D(crit, stat):
    """Descriptive statistic, formatted as the paper quotes it."""
    v = MR["descriptives"][crit][stat]
    if stat == "cv_pct":
        return f"{v:.2f}"
    if stat == "skew":
        return f"{v:+.2f}"
    return f"{v:.4f}" if stat in ("mean", "sd") else f"{v:.3f}"


from PIL import Image as _PILImage
from _paths import fig as _figpath
S13_FIGCAPS = {
    "corr": ("Fig. {F:corr}.", "Criterion inter-correlation matrix (Pearson r, symmetric), with each "
         "criterion's correlation with the PAI in the last row and column, computed on the "
         "normalised model matrix (C3 log-transformed). Spearman ρ is given in Table {T:S-spearman}. "
         "Significance: *** p < 0.001, ** p < 0.01, * p < 0.05 (n = 77 provinces). "
         "C2 Equity is negatively associated with the efficiency criteria, most strongly "
         "with C4 Infrastructure Access."),
    "weights": (f"Fig. {{F:weights}}.", f"EWM criterion weights and Shannon entropy values. Lower entropy = "
         f"higher inter-provincial dispersion = higher weight. C2 Equity carries the "
         f"largest weight (w = {Wt['C2_Equity']:.3f}) and C1 Resource Potential the "
         f"smallest (w = {Wt['C1_Resource']:.3f})."),
    "lisa": ("Fig. {F:lisa}.", "LISA cluster map of province-level PAI (queen contiguity, 999 "
         "permutations). Local clusters are shown at the unadjusted α = 0.05 and are "
         + ("exploratory: none survives" if _FDR0 else "exploratory: few survive") +
         " Benjamini–Hochberg FDR correction across the 77 tests "
         "(main text Section 4.5, Table {T:S-lisa}). HH = High-High. LL = Low-Low. HL = High-Low outlier. "
         "LH = Low-High outlier. "
         f"Global Moran's I = {_MI['I']:.3f}, permutation p = {_MI['p']:.3f} ({_MI['permutations']} permutations). Map lines delineate study areas and do not necessarily depict accepted national boundaries. Geographic coordinates, WGS 84 (EPSG:4326)."),
    "ranking": ("Fig. {F:ranking}.", "Province PAI ranking (n = 77), shown in two columns and coloured by "
         "priority zone. High-poverty provinces are lifted into the top tier by the equity "
         "criterion. Affluent low-poverty provinces rank low despite adequate solar "
         "resource."),
    "sens": (f"Fig. {{F:sens}}.", f"Sensitivity analysis: (a) EWM vs equal weights "
         f"(ρ = {SENS_RHO['equal']:.3f}) and (b) EWM vs expert equity-first weights "
         f"(ρ = {SENS_RHO['expert']:.3f}). Points on the 1:1 diagonal "
         f"indicate rank agreement. Marker size is proportional to the absolute rank change "
         f"under equal weights. Provinces displaced by more than ten ranks are named."),
    "radar": ("Fig. {F:radar}.", "Zone-level criterion profiles (radar chart), on the normalised "
         "model scale. Zone 1 leads on C2 Equity, C1 Resource Potential and C5 Physical "
         "Suitability, but not on C4 Infrastructure Access, where Zone 2 scores highest, "
         "the efficiency–equity tension of main text Section 4.2 read at zone level."),
}
_ZC = MR["zone_criterion_means"]
assert all(_ZC["1"][c] == max(_ZC[z][c] for z in _ZC) for c in ("C2_Equity", "C1_Resource", "C5_Physical"))
assert max(_ZC, key=lambda z: _ZC[z]["C4_Infra"]) == "2"
S13_FIGS = ['corr', 'weights', 'lisa', 'ranking', 'sens', 'radar']   # files via _figures.figin
def supp_fig(label, width_cm=15.0, max_h_cm=21.0):
    path = figin(label)
    with _PILImage.open(str(path)) as im:
        w, h = im.size
    kw = {"height": Cm(max_h_cm)} if width_cm * h / w > max_h_cm else {"width": Cm(width_cm)}
    doc.add_paragraph().add_run().add_picture(str(path), **kw)
    lab, txt = S13_FIGCAPS[label]
    caption(lab + " " + txt)
head("S13. Method details and extended results")
para("This section holds the equations, method detail and extended results that were moved "
     "out of the main text to keep it focused on the allocation scenarios and the policy "
     "screen. Numbers are read from the same analysis outputs as the main text.", size_after=8)
head("S13.1 Normalisation, entropy weighting and bounded-ideal TOPSIS", size_pt=12)

para(
    "C1 and C3 are first scaled at the pixel level (2nd–98th percentile clip, linear [0, 1]) "
    "before provincial aggregation, C2 enters as the raw provincial percentage, and C4 and C5 "
    "are formula scores in [0, 1]. At province level, each of the five aggregated criteria is "
    "then normalised once using the positive linear transformation, with 2nd–98th percentile "
    "clipping applied to reduce the influence of extreme outliers:"
)
eq("r_{ij} = (x_{ij} - x_min,j) / (x_max,j - x_min,j)      (1)")
para(
    "Proximity-type criteria, such as infrastructure access, are treated as benefit "
    "criteria once expressed in exponential-decay form. Any cost-type criterion would "
    "instead be normalised using the negative transformation. All normalised values are "
    "clipped to [0, 1]."
)


para(
    "Weights are derived from the Shannon entropy of the normalised score distribution "
    "across all m spatial units, for each criterion j [15,35]:"
)
eq("p_{ij} = r_{ij} / Σ_i r_{ij}      (2)")
# review 2026-10-24: the zero convention is stated in the text, not run into the display equation
eq("e_j = -(1/ln m) · Σ_i (p_{ij} · ln p_{ij})      (3)")
para("The convention ⟪plnp-zero⟫ is used when ⟪pij-zero⟫.")
eq("d_j = 1 - e_j      (4)")
eq("w_j = d_j / Σ_j d_j,   Σ_j w_j = 1      (5)")
para(
    "A lower entropy value indicates greater inter-unit differentiation and therefore "
    "greater informational contribution to the ranking, yielding a higher weight."
)


para(
    "A weighted normalised matrix ⟪V-def⟫ is constructed as ⟪v-def⟫. "
    "This study uses a bounded-ideal variant of TOPSIS [45,14]: because every criterion is "
    "normalised to [0, 1] (Section S13.1), the ideal-best (A⁺) and ideal-worst (A⁻) profiles "
    "are defined at the theoretical bounds of that scale rather than, as in conventional "
    "TOPSIS, at the observed per-criterion extrema:"
)
eq("A^+ = {v_j^+ = w_j · r_j^+ = w_j · 1 = w_j | j ∈ benefit}      (6)")
eq("A^- = {v_j^- = w_j · r_j^- = w_j · 0 = 0   | j ∈ benefit}      (7)")
para(
    "Two scales are in play and are kept distinct throughout. On the UNWEIGHTED "
    "normalised scale the ideal and nadir are ⟪r-plus⟫ and ⟪r-minus⟫ for every criterion, "
    "since normalisation maps each criterion onto [0, 1]. On the WEIGHTED scale entering "
    "the distance calculation they become ⟪v-plus⟫ and ⟪v-minus⟫. Table {T:bounds} reports both: "
    # 2026-10-24: Fig. 1 no longer carries equations, and the table has one weight column (no
    # separate weighted-ideal columns), so the sentence describes the table as it is
    "the columns headed A⁺ and A⁻ are the unweighted ideals (1 and 0), and the column headed w "
    "gives the weighted ideal ⟪w-j⟫, with a weighted nadir of 0 for every criterion. The two "
    "are equivalent statements of the same bound."
)
para(
    "Using the theoretical rather than the observed maximum is deliberate: a criterion "
    "whose observed maximum falls well short of 1 would, under empirical-max "
    "normalisation, "
    "have its narrow spread re-inflated to the full [0, 1] range and so exert influence "
    "disproportionate to its information content. Anchoring A⁺ at ⟪w-j⟫ preserves each "
    "criterion's contribution in proportion to its EWM weight. Euclidean separation "
    "distances from each profile are then computed for spatial unit i:"
)
eq("d_i^+ = √[ Σ_j (v_{ij} - v_j^+)^2 ]      (8)")
eq("d_i^- = √[ Σ_j (v_{ij} - v_j^-)^2 ]      (9)")
para("The Priority Area Index is defined as the TOPSIS closeness coefficient:")
eq("PAI_i = d_i^- / (d_i^+ + d_i^-),   PAI ∈ [0, 1]      (10)")
para(
    "PAI = 1 denotes a unit at the theoretical ideal on every criterion. "
    "PAI = 0 denotes identity with the ideal-worst profile. Units are ranked in "
    "descending PAI order."
)
para(
    "Because this departs from standard TOPSIS practice, the two formulations were "
    "compared directly. Recomputing the index with conventional observed-extrema ideals "
    "reproduced the bounded-ideal ranking exactly (Spearman ρ = 1.000, no province shifted "
    "position, identical Zone 1 membership). The choice is therefore consequential for the "
    "interpretability of the PAI scale, bounded ideals make scores comparable across "
    "applications and over time, since they do not move when the sample changes, but not "
    "for the ordering reported here."
)


para(
    "K-means clustering (k = 5) is applied to unit-level PAI scores to yield discrete "
    "deployment-priority zones. The choice of five zones is a policy convention, a "
    "five-tier deployment-priority ordering of the kind used in planning, rather than a "
    "data-driven optimum, and this is stated explicitly because the PAI distribution does "
    "not favour any particular number of clusters (main text Section 4.4). Global and local Moran's "
    "I statistics are computed with a queen "
    "contiguity weight matrix and conditional random permutations to test whether high- "
    "and low-priority units cluster spatially [25]:"
)
eq("I = (n / S_0) · (Σ_i Σ_j w_{ij} z_i z_j) / (Σ_i z_i^2)      (11)")
para(
    # review 2026-10-24: the double sum is a display equation, not inline (it broke the line spacing)
    "where ⟪n⟫ is the number of units, ⟪z-def⟫, ⟪w-ij⟫ are spatial weights, and ⟪S0⟫ is the sum "
    "of all spatial weights:"
)
eq("S_0 = Σ_i Σ_j w_{ij}      (12)")
para(
    "A sensitivity analysis is then conducted under an equal-weight scenario and an "
    "expert-elicited scenario, with Spearman's ρ, Kendall's τ, and maximum rank "
    "displacement used to evaluate ranking stability."
)

caption(
    "Table {T:bounds}. Bounded-ideal TOPSIS reference points by criterion. A⁺ and A⁻ are the "
    "ideal and nadir on the unweighted normalised scale (1 and 0 by construction). The "
    "weighted values entering the distance calculation are ⟪w-j⟫ and 0 respectively "
    "(Eqs. (S13.6)–(S13.7)). Observed minima and maxima are on the same unweighted normalised scale. "
    "All criteria are benefit type (higher = better)."
)
t7_sel = T["T6_TOPSIS_Bounds"][[
    "Criterion", "EWM Weight (w)",
    "Ideal solution A⁺ (theory)", "Nadir solution A⁻ (theory)",
    "Obs. min (normalised)", "Obs. max (normalised)"
]].copy()
t7_sel.columns = ["Criterion", "w", "Ideal A+", "Nadir A-", "Obs. min", "Obs. max"]
table(rename_crit(t7_sel), col_widths=[2.2, 1.2, 2.0, 2.0, 2.2, 2.2], font_size=8.5)


head("S13.2 Criterion transferability", size_pt=12)

para(
    "To support re-application of the framework in cities and regions lacking the "
    "demonstration-case datasets, Table {T:transfer} maps each criterion slot to alternative data "
    "sources with comparable spatial coverage. Openly available global products, "
    "including predictive open grid-network maps [29], allow every slot to be populated, "
    "at varying resolution, in most national and municipal contexts."
)
caption(
    "Table {T:transfer}. Criterion transferability: alternative data sources by which each "
    "generalised criterion slot can be populated in other national or municipal contexts."
)
t2_transfer = pd.DataFrame({
    "Slot": ["C1 Resource Potential", "C2 Equity", "C3 Demand Density",
             "C4 Infrastructure Access", "C5 Physical Suitability", "Deployment comparison"],
    "Demonstration Indicator (Thailand)": [
        "Global Solar Atlas v2 LTAy PVOUT (1 km)",
        "Official poverty incidence (province) / author-built vulnerability index (district)",
        "WorldPop 2020 gridded population",
        "Exponential-decay distance to OSM power lines and cables",
        "Hansen forest cover + Copernicus DEM GLO-30 slope + GHSL built-up",
        "OSM solar plant point records",
    ],
    "Alternative Sources (other contexts)": [
        "NREL NSRDB, PVGIS, national solar/wind atlases where the DER mix differs",
        "Census income or poverty rates, multidimensional poverty indices, "
        "energy-burden datasets, household expenditure surveys",
        "National census grids, GHS-POP, LandScan, utility customer-meter counts",
        "Utility GIS feeder/substation maps, GridFinder modelled MV network [29], "
        "OpenInfraMap",
        "Local land-use zoning, building-footprint rooftop masks (Google/Microsoft "
        "Open Buildings), WDPA protected areas, cadastral land price tiers",
        "Utility interconnection registries, FiT/PPA contract lists, official plant "
        "registries",
    ],
})
table(t2_transfer, col_widths=[3.0, 5.0, 6.5], font_size=8)

head("S13.3 Descriptive statistics", size_pt=12)
para(
    f"Descriptive statistics for the five retained criteria and the PAI are reported in "
    f"Table {{T:desc}} and mapped in main-text Fig. {{F:criteria-maps}}. All values are on the normalised model scale "
    f"(Section S13.1), so each criterion spans [0, 1] by construction and the means and "
    f"coefficients of variation describe relative position within Thailand rather than "
    f"absolute physical magnitude. C5 Physical Suitability recorded the highest mean "
    f"(x̅ = {D('C5_Physical','mean')}, SD = {D('C5_Physical','sd')}, "
    f"CV = {D('C5_Physical','cv_pct')}%), followed by C1 Resource Potential "
    f"(x̅ = {D('C1_Resource','mean')}, SD = {D('C1_Resource','sd')}, "
    f"CV = {D('C1_Resource','cv_pct')}%). Both are left-skewed "
    f"(skewness {D('C1_Resource','skew')} and {D('C5_Physical','skew')}), meaning most "
    f"provinces score comparatively well and relatively few are poorly endowed. That "
    f"pattern is what later gives these criteria their low entropy weights: a criterion "
    f"on which most units resemble one another discriminates weakly (main text Section 4.3)."
)
para(
    f"C2 Equity showed the greatest relative dispersion of any criterion "
    f"(CV = {D('C2_Equity','cv_pct')}%, x̅ = {D('C2_Equity','mean')}, "
    f"SD = {D('C2_Equity','sd')}) and is right-skewed "
    f"(skewness {D('C2_Equity','skew')}), ranging from the least poor provinces of the "
    f"industrial Eastern seaboard to the highest poverty incidence in the far-southern "
    f"border and northern-highland provinces. C4 Infrastructure Access "
    f"(x̅ = {D('C4_Infra','mean')}, CV = {D('C4_Infra','cv_pct')}%) and C3 Demand "
    f"Density (x̅ = {D('C3_Demand','mean')}, CV = {D('C3_Demand','cv_pct')}%) occupy an "
    f"intermediate position. C3 retains mild right-skew "
    f"({D('C3_Demand','skew')}) even after the logarithmic transformation of "
    f"Section S13.1, reflecting the exceptional concentration of population in the Bangkok "
    f"metropolitan region. The composite PAI is markedly less variable than any of its "
    f"inputs (CV = {D('PAI','cv_pct')}%, x̅ = {D('PAI','mean')}, SD = {D('PAI','sd')}, "
    f"range {D('PAI','min')}–{D('PAI','max')}) and close to symmetric "
    f"(skewness {D('PAI','skew')}), which is the expected aggregating effect of "
    f"multi-criteria weighting and a reason that small PAI differences between adjacent "
    f"provinces should not be over-interpreted."
)
caption(
    "Table {T:desc}. Descriptive statistics for the five normalised criteria and the composite PAI "
    "(n = 77 provinces)."
)
table(rename_crit(T["T3_Descriptive_Stats"]), col_widths=[2.2, 0.8, 1.3, 1.3, 1.3, 1.1, 1.1, 1.3, 1.5, 2.4], font_size=8.5)

head("S13.4 Correlations with the PAI and multicollinearity", size_pt=12)
para(
    f"Pearson and Spearman correlations with PAI are reported in Table {{T:corr}}. Full matrices "
    f"are provided as Tables {{T:S-pearson}}–{{T:S-spearman}}. C2 Equity was the criterion most strongly "
    f"associated with the composite (Pearson r = {MR['corr_vs_pai']['C2_Equity']['pearson']:.3f}, "
    f"p < 0.001, Spearman ρ = {MR['corr_vs_pai']['C2_Equity']['spearman']:.3f}), as expected "
    f"given its dominant weight, followed by C1 Resource Potential "
    f"(ρ = {MR['corr_vs_pai']['C1_Resource']['spearman']:.3f}), C5 Physical Suitability "
    f"(ρ = {MR['corr_vs_pai']['C5_Physical']['spearman']:.3f}) and C3 Demand Density "
    f"(ρ = {MR['corr_vs_pai']['C3_Demand']['spearman']:.3f}). C4 Infrastructure Access was "
    f"only weakly related to PAI (ρ = {MR['corr_vs_pai']['C4_Infra']['spearman']:.3f}, "
    f"p = {MR['corr_vs_pai']['C4_Infra']['spearman_p']:.3f})."
)
para(
    f"Multicollinearity was checked on the normalised province-level design matrix. Six "
    f"candidate criteria entered the screening of Step 1 (main-text Fig. {{F:framework}}). Exactly one, Emission Reduction "
    f"Potential (ERP), was excluded, because it substantially overlapped with C3 Demand "
    f"Density (Spearman ρ = {ERPD['rho_erp_c3']:.3f}, main text Section 3.2). A VIF of 24.98 "
    f"reported for ERP in an earlier version could not be reproduced after the C2 correction "
    f"(VIF {ERPD['variants']['linear']['vif_erp']:.2f} with a linear and "
    f"{ERPD['variants']['log']['vif_erp']:.2f} with a log transform of ERP) and is not used "
    f"as a basis for exclusion. Section S13.11 reports a post hoc diagnostic with ERP added. "
    f"No further candidate was dropped at any later stage. "
    f"Among the five retained criteria, variance inflation factors ranged from "
    f"{min(MR['vif'].values()):.2f} (C2 Equity) to {MR['vif_max']:.2f} (C5 Physical "
    f"Suitability), with C3 Demand Density at {MR['vif']['C3_Demand']:.2f} and C4 "
    f"Infrastructure Access at {MR['vif']['C4_Infra']:.2f}, all well below the "
    f"conventional 10.0 exclusion threshold and below the stricter 5.0 threshold "
    f"sometimes applied. The criterion set is therefore not redundant [15], though the "
    f"mild elevation for C5, C3 and C4 reflects the shared urban–rural gradient noted "
    f"above."
)
caption(
    "Table {T:corr}. Pearson r, Spearman ρ, and VIF for each criterion versus the "
    "composite PAI (n = 77 provinces). *** p < 0.001. ** p < 0.01. * p < 0.05."
)
table(rename_crit(T["T4_Corr_VIF"]), col_widths=[2.2, 2.0, 1.5, 1.5, 2.0, 1.5, 1.5, 1.2, 1.8], font_size=8.5)
para("The full criterion inter-correlation matrix is shown in Fig. {F:corr}.")
supp_fig("corr")

head("S13.5 Entropy weights", size_pt=12)
para("The entropy value and EWM weight of each criterion are shown in Fig. {F:weights}.")
supp_fig("weights")

head("S13.6 Spatial autocorrelation", size_pt=12)
para(
    f"Global Moran's I for province-level PAI was {_MI['I']:.3f} (z = {_MI['z']:.2f}, permutation p = "
    f"{_MI['p']:.3f}, {_MI['permutations']} permutations), indicating moderate but statistically clear positive spatial "
    "autocorrelation (Fig. {F:lisa}): priority is neither randomly scattered nor organised into "
    "one dominant block. This global test is a single hypothesis and is unaffected by "
    "multiple comparisons. The local LISA statistics, by contrast, involve one test per "
    f"province and must be corrected accordingly. At the unadjusted level "
    f"{MR['lisa_fdr']['n_raw_sig']} provinces reach p < 0.05 ({nw(len(_LT['HH']))} High-High: "
    f"{names(_LT['HH'])}. {nw(len(_LT['LL'])).capitalize()} Low-Low, {nw(len(_LT['HL']))} High-Low "
    f"and {('one' if len(_LT['LH']) == 1 else nw(len(_LT['LH'])))} Low-High outliers), but "
    f"after Benjamini–Hochberg control of the false discovery rate across the "
    f"{MR['lisa_fdr']['n_tests']} tests "
    + ("none remains significant" if _FDR0 else f"{MR['lisa_fdr']['n_fdr_sig']} remain significant") +
    f" (smallest adjusted "
    f"p = {MR['lisa_fdr']['min_p_bh']:.3f}, Table {{T:S-lisa}}). The local clusters are therefore "
    "reported as exploratory and uncorrected, and no claim of individually significant "
    "hot- or cold-spots is made. What the analysis does support, the moderate global "
    "statistic together with the absence of any dominant local cluster, is that priority, "
    "being driven by regionally patterned but not smoothly graded poverty, forms several "
    "separated pockets rather than a single contiguous frontier. Deployment programmes "
    "designed around one large target region would miss much of the eligible population."
)
supp_fig("lisa")

head("S13.7 Province ranking", size_pt=12)
para(
    f"The complete province ranking by PAI is presented in Table {{T:S-ranking}} (Section S3) and "
    f"Fig. {{F:ranking}}. Pattani ranked first (PAI = {pai('Pattani')}), a deep-South "
    f"province with the second-highest poverty incidence in the country (after Mae Hong Son) "
    f"and modest solar resource. Ranked nationally, with the top fifth taken as rank 15 or "
    f"better of 77, {names([f'{p} ({pai(p)})' for p in _POVONLY])} enter Zone 1 on poverty "
    f"alone, {names([f'{p} ({pai(p)})' for p in _IRRONLY])} on irradiance and flat land "
    f"alone, and {names([f'{p} ({pai(p)})' for p in _BOTH])} on both. That the ranking is headed by "
    "provinces which no purely resource-driven assessment would select is the direct, "
    "intended consequence of data-driven weighting having found poverty to be Thailand's "
    "most spatially discriminating criterion (main text Section 4.3)."
)
para(
    f"The lowest-ranked provinces are correspondingly those combining relative affluence "
    f"with constrained terrain: Loei ({pai('Loei')}), Chiang Mai "
    f"({pai('Chiang Mai')}), Surat Thani ({pai('Surat Thani')}), Trat "
    f"and Chanthaburi. Bangkok Metropolis, despite the highest demand density in the "
    "country, does not enter the top tier at province scale, because its poverty incidence "
    "is low and its land availability minimal. This is a scale artefact rather than a "
    "substantive finding, intra-urban disadvantage is invisible to a province-level unit, "
    "and is why an urban application is reported in Supplementary Section S12."
)
# Top-20 table removed (review item 3, 2026-10-15): it repeated the first twenty rows of Table S3
supp_fig("ranking")

head("S13.8 Comparison with existing deployment and construct check", size_pt=12)
para(
    "The framework was compared against 332 OSM-mapped solar power plants "
    "recorded in OpenStreetMap. What such a comparison can establish requires care. "
    "Existing plants were sited by commercial developers optimising for irradiance, land "
    "cost and grid access. They record where deployment has been profitable, not where it "
    "ought to occur on equity grounds. High agreement between the PAI and the existing "
    "fleet would therefore not validate the index, it would show the index had reproduced "
    "the status quo, the outcome an equity-aware instrument is designed to avoid. The "
    "comparison is used for a narrower purpose: to test whether the efficiency component "
    "is realistic, and to quantify the gap between market-led siting and need-based "
    "priority."
)
_ZT = MR["zone_validation"]
_Z = {r["zone"]: r for r in _ZT["zone_table"]}
assert _ZT["p"] < 0.001 and set(sorted(_Z, key=lambda z: -_Z[z]["enrichment"])[:2]) == {2, 3} and _Z[1]["enrichment"] < 1
para(
    "The zone distribution states the same finding in allocative terms (Table {T:osmzones}, "
    "main-text Fig. {F:deployment}). The five zones depart very highly significantly from a null model of "
    f"installations distributed in proportion to land area (χ² = {_ZT['chi2']}, df = {_ZT['df']}, p < 0.001), "
    "but the deviation runs against the priority ordering at the top. Zone 1 provinces "
    f"hold {_Z[1]['land_pct']}% of national land and just {_Z[1]['solar_obs_pct']}% of OSM-mapped plants ({nw(_Z[1]['solar_obs'])} plants "
    f"against {_Z[1]['expected']} expected, enrichment {_Z[1]['enrichment']:.2f}). Existing installations concentrate instead in "
    f"Zones 2 and 3 (enrichment {_Z[2]['enrichment']:.2f} and {_Z[3]['enrichment']:.2f}), the broad agricultural middle band where "
    "land is cheap and grid access adequate but poverty is not acute. The highest-priority "
    "provinces under equity-aware assessment are those with the fewest recorded "
    "installations relative to land area in the OSM data."
)
caption(
    "Table {T:osmzones}. Distribution of 332 OSM-mapped solar power plants across the five "
    "priority zones, against a null model proportional to land area. Enrichment is the "
    "ratio of observed installation share to land-area share. Values below 1.0 indicate "
    "under-representation."
)
_zv = json.loads(data("14_Processed_90m", "validation_zone_stats.json")
                 .read_text(encoding="utf-8"))
t11_zone = pd.DataFrame([{
    "Zone": r["zone"], "Provinces (n)": r["n_provinces"],
    "Land area (%)": f"{r['land_pct']:.1f}",
    "Installations (n)": r["solar_obs"],
    "Installations (%)": f"{r['solar_obs_pct']:.1f}",
    "Expected (n)": f"{r['expected']:.1f}",
    "Enrichment": f"{r['enrichment']:.2f}",
} for r in _zv["zone_table"]])
table(t11_zone, col_widths=[1.0, 1.8, 1.8, 2.0, 2.0, 1.8, 1.6], font_size=8.5)
para(
    f"χ² = {_zv['chi2']} (df = {_zv['df']}, p < 0.001) against the land-area null model.",
)
import json as _json
para(
    "As a further construct check, not an external validation, the criteria were compared "
    "with an author-constructed composite index built from official NESDC/NSO source data "
    "(gross provincial product, household income, employment, debt and expenditure, "
    "2566–2567), a research prototype whose formula and per-province scores are given in "
    "Section S8. This comparison is not independent of C2: the index's "
    f"vulnerability sub-index itself contains a provincial poverty-burden proxy, so the "
    f"strong correlation of C2 with that sub-index "
    f"(ρ = {MR['ser_check']['c2_vs_vuln']['rho']:.3f}) and with the poverty-burden component "
    f"(ρ = {MR['ser_check']['c2_vs_poverty']['rho']:.3f}) is expected largely by "
    f"construction and should be read as an internal consistency check, confirming the two "
    f"poverty measures agree, rather than as external corroboration. More informative is "
    f"the discriminant pattern: the composite PAI is only moderately associated with the "
    f"index's resilience (ρ = {MR['ser_check']['pai_vs_resilience']['rho']:.3f}) and "
    f"vulnerability (ρ = {MR['ser_check']['pai_vs_vuln']['rho']:.3f}) scores (Table {{T:construct}}), "
    f"about {MR['ser_check']['pai_vs_resilience']['rho']**2*100:.0f}% and "
    f"{MR['ser_check']['pai_vs_vuln']['rho']**2*100:.0f}% shared rank variance, so the "
    f"PAI is not a socioeconomic ranking in disguise. The biophysical and infrastructural "
    f"criteria still discriminate substantially between provinces of similar poverty."
)
caption(
    "Table {T:construct}. Construct and sensitivity check of the criteria against an author-constructed "
    "composite index built from official NESDC/NSO source data (research prototype, all "
    "n = 77 provinces, matched via an explicit corrected Thai–English crosswalk). This is "
    "not an independent external validation: the index's vulnerability sub-index reuses a "
    "provincial poverty proxy, so the convergent rows are partly circular and are reported "
    "as internal consistency. Spearman rank correlations."
)
_sc = MR["ser_check"]
def _p(x): return "<0.001" if x < 0.001 else f"{x:.3f}"
t_ser = pd.DataFrame({
    "Comparison": [
        "C2 equity (poverty incidence) vs Index vulnerability score",
        "C2 equity (poverty incidence) vs Index poverty-burden proxy",
        "Composite PAI vs Index resilience score",
        "Composite PAI vs Index vulnerability score",
    ],
    "Spearman ρ": [_sc['c2_vs_vuln']['rho'], _sc['c2_vs_poverty']['rho'],
                   _sc['pai_vs_resilience']['rho'], _sc['pai_vs_vuln']['rho']],
    "p": [_p(_sc['c2_vs_vuln']['p']), _p(_sc['c2_vs_poverty']['p']),
          _p(_sc['pai_vs_resilience']['p']), _p(_sc['pai_vs_vuln']['p'])],
    "Interpretation": [
        "internal consistency (index reuses a poverty proxy)",
        "internal consistency: same construct (poverty)",
        f"discriminant, ~{_sc['pai_vs_resilience']['rho']**2*100:.0f}% shared variance, not redundant",
        f"discriminant, ~{_sc['pai_vs_vuln']['rho']**2*100:.0f}% shared variance, not redundant",
    ],
})
table(t_ser, col_widths=[6.2, 1.6, 1.2, 4.5], font_size=8)

head("S13.9 Sensitivity and uncertainty", size_pt=12)
_SE, _SX = MR["sensitivity"][0], MR["sensitivity"][1]
assert "Equal" in _SE["Comparison"] and "Expert" in _SX["Comparison"]
assert _SX["N provinces |Δrank| > 10"] < _SE["N provinces |Δrank| > 10"]
para(
    "Two alternative weighting scenarios were compared against the EWM baseline "
    "(Table {T:sens}, Fig. {F:sens}). Under equity-first expert weights the ranking was highly stable "
    f"(Spearman ρ = {SENS['expert']['rho']:.3f}, Kendall τ = {SENS['expert']['tau']:.3f}, RMSE = {SENS['expert']['rmse']:.1f} rank units, only "
    f"{_SX['N provinces |Δrank| > 10']} of 77 provinces "
    "moved more than ten places), which follows directly from the fact that EWM had itself "
    "already selected equity as the dominant criterion: the data-driven and the expert "
    "judgements substantially agree. Equal weighting displaced the ranking far more "
    f"(ρ = {SENS['equal']['rho']:.3f}, τ = {SENS['equal']['tau']:.3f}, RMSE = {SENS['equal']['rmse']:.1f}, "
    f"{_SE['N provinces |Δrank| > 10']} provinces moved more than ten places, maximum "
    f"shift {_SE['Max |Δrank|']}). The asymmetry is informative. It is not the equity weight that is the "
    "fragile assumption in this application but the decision to weight all five criteria "
    "alike, which implicitly down-weights the single criterion carrying the most spatial "
    "information. Reporting both scenarios lets planners see how much of the priority "
    "ordering rests on that choice."
)
para(
    f"The entropy weights themselves are well constrained. Across "
    f"{MR['bootstrap']['B']} bootstrap resamples of the 77 provinces, the equity weight had "
    f"a 95% percentile interval of "
    f"{MR['bootstrap']['weight_ci']['C2_Equity'][0]:.3f}–"
    f"{MR['bootstrap']['weight_ci']['C2_Equity'][1]:.3f}, its lower bound "
    f"({MR['bootstrap']['weight_ci']['C2_Equity'][0]:.3f}) still exceeds the upper bound of "
    f"every other criterion (for example C4 Infrastructure Access, "
    f"{MR['bootstrap']['weight_ci']['C4_Infra'][0]:.3f}–"
    f"{MR['bootstrap']['weight_ci']['C4_Infra'][1]:.3f}), so equity's status as the single "
    f"dominant criterion is not an artefact of the particular province sample. Zone "
    f"membership is more sensitive to the cluster count: all {nw(len(_Z1))} baseline Zone 1 provinces "
    f"were contained in the highest-PAI cluster for k = 2–5, but that cluster expanded to "
    f"{MR['bootstrap']['stability_by_k']['2']['top_cluster_size']} provinces at k = 2 and "
    f"{MR['bootstrap']['stability_by_k']['3']['top_cluster_size']} at k = 3, so this shows "
    f"the {nw(len(_Z1))} are consistently among the highest-priority provinces, not that Zone 1 has a "
    "fixed membership (consistent with the quasi-continuous PAI of main text Section 4.4). The "
    "bootstrap interval is conditional on the processed province matrix and does not "
    "include raster or source-data uncertainty, so total uncertainty may be understated. "
    "The k-sensitivity analysis is a separate structural robustness check that re-clusters "
    "the same PAI values rather than resampling provinces."
)
caption(
    "Table {T:sens}. Sensitivity analysis: rank agreement between EWM baseline and two "
    "alternative weight scenarios (n = 77 provinces). Province-level rank displacements "
    "for both scenarios are given as supplementary Table {T:S-rankshift}."
)
t12_sel = T["T9_Sensitivity"][[
    "Comparison", "Spearman ρ", "Spearman p",
    "Kendall τ", "Kendall p",
    "RMSE (rank units)", "MAE (rank units)", "Max |Δrank|"
]].copy()
table(t12_sel, col_widths=[4.3, 1.7, 1.4, 1.7, 1.4, 1.7, 1.7, 1.7], font_size=8.5)
supp_fig("sens")

head("S13.10 Zone criterion profiles", size_pt=12)
para("Fig. {F:radar} compares the mean criterion profile of each priority zone on the normalised model scale.")
supp_fig("radar")

head("S13.11 Post hoc diagnostic: ERP added as a sixth criterion", size_pt=12)
_lv, _gv = ERPD["variants"]["linear"], ERPD["variants"]["log"]
para(
    "This is a post hoc diagnostic, not a pre-specified sensitivity analysis. The excluded "
    "candidate ERP (province mean of night-time light multiplied by the national emission "
    "factor) was added to the five retained criteria and the index was recomputed with the "
    "same normalisation, entropy weighting, bounded-ideal TOPSIS and K-means steps (Table {T:erp}). "
    f"ERP overlaps strongly with C3 Demand Density (Spearman ρ = {ERPD['rho_erp_c3']:.3f}) and "
    f"is negatively related to C2 Equity (ρ = {ERPD['rho_erp_c2']:.3f}). Its province "
    "distribution is strongly right-skewed, so its entropy weight depends on the transform: "
    f"{_lv['weights']['ERP']:.3f} on a linear scale and {_gv['weights']['ERP']:.3f} after a log "
    "transform. In both cases the demand-related dimension enters twice, through C3 and ERP, "
    "and the index moves toward urban provinces. The equity criterion stays negatively "
    f"associated with the efficiency-only composite (ρ = {_lv['rho_equity_vs_efficiency']:.3f} "
    f"and {_gv['rho_equity_vs_efficiency']:.3f}). ERP is therefore kept out of the final "
    "criterion set because of its overlap with C3, as stated in main text Section 3.2."
)
caption(
    "Table {T:erp}. Post hoc diagnostic (not a pre-specified sensitivity analysis): the final "
    "five-criterion index compared with indices that add ERP under a linear and a log transform. "
    "S2 is recomputed as the 15 highest-ranked of the 74 PEA-served provinces under each index."
)
_b = ERPD["baseline"]
_w = MR["weights"]
t_erp = pd.DataFrame({
    "Quantity": ["ERP weight", "C2 Equity weight", "VIF of ERP", "ρ equity vs efficiency-only composite",
                 "ρ with the final PAI", "Zone sizes (1 to 5)", "Zone 1",
                 "S2 provinces changed (out / in)", "S2 mean poverty (%)", "S2 median km to power lines"],
    "Final index (5 criteria)": ["not included", f"{_w['C2_Equity']:.3f}", "–",
                                 f"{MR['equity_vs_efficiency_only']['spearman']:.3f}", "1.000",
                                 "/".join(str(MR['zones'][z]['n']) for z in "12345"),
                                 ", ".join(_b["zone1"]), "–", f"{_b['s2_mean_poverty_pct']:.2f}",
                                 f"{_b['s2_median_line_km']:.1f}"],
    "With ERP, linear": [f"{_lv['weights']['ERP']:.3f}", f"{_lv['weights']['C2_Equity']:.3f}", f"{_lv['vif_erp']:.2f}",
                         f"{_lv['rho_equity_vs_efficiency']:.3f}", f"{_lv['rho_pai6_vs_pai']:.3f}",
                         "/".join(map(str, _lv["zone_sizes"])), ", ".join(_lv["zone1"]),
                         f"{len(_lv['s2_out'])} / {len(_lv['s2_in'])}", f"{_lv['s2_mean_poverty_pct']:.2f}",
                         f"{_lv['s2_median_line_km']:.1f}"],
    "With ERP, log": [f"{_gv['weights']['ERP']:.3f}", f"{_gv['weights']['C2_Equity']:.3f}", f"{_gv['vif_erp']:.2f}",
                      f"{_gv['rho_equity_vs_efficiency']:.3f}", f"{_gv['rho_pai6_vs_pai']:.3f}",
                      "/".join(map(str, _gv["zone_sizes"])), ", ".join(_gv["zone1"]),
                      f"{len(_gv['s2_out'])} / {len(_gv['s2_in'])}", f"{_gv['s2_mean_poverty_pct']:.2f}",
                      f"{_gv['s2_median_line_km']:.1f}"],
})
table(t_erp, col_widths=[4.0, 3.6, 3.6, 3.6], font_size=8)

# ── Float labels: check, then resolve {T:..}/{F:..} tokens (see _floats.py) ────
import re as _re
from docx.oxml.ns import qn as _qn
from _floats import check_and_resolve, resolve_text
_items = [(q.text, bool(_re.match(r"^(Table|Fig\.) \{[TF]:[A-Za-z0-9\-]+\}\.", q.text))) for q in doc.paragraphs]
_items += [(c.text, False) for _t in doc.tables for _r in _t.rows for c in _r.cells]
_float_problems = check_and_resolve(_items, is_main=False)
assert not _float_problems, chr(10).join(_float_problems)
for _node in doc.element.body.iter(_qn("w:t")):
    if _node.text and "{" in _node.text:
        _node.text = resolve_text(_node.text)
assert not any("{T:" in q.text or "{F:" in q.text for q in doc.paragraphs), "unresolved float token"

# ── Citations: map reference-list indices to the main text's final numbers ────
# Text moved from the main text cites references by their index in references.json.
# The main build writes the renumbering it applied. Every reference cited here must
# also be cited in the main text, so the main reference list stays complete.
_REFN = {int(k): v for k, v in json.loads((BASE / "Data" / "qa" / "ref_renumber.json").read_text()).items()}
_NREF = len(json.loads((BASE / "Data" / "references.json").read_text(encoding="utf-8"))["entries"])
_RG = _re.compile(r"\[([0-9]+(?:\s*[,–-]\s*[0-9]+)*)\]")
_missing = set()
def _cite_sub(mm, text):
    nums = []
    for part in [x.strip() for x in mm.group(1).split(",")]:
        r = _re.fullmatch(r"(\d+)\s*[–-]\s*(\d+)", part)
        nums.extend(range(int(r.group(1)), int(r.group(2)) + 1) if r else [int(part)])
    if not nums or any(n < 1 or n > _NREF for n in nums):
        return mm.group(0)
    if len(nums) == 1 and "=" in text[max(0, mm.start() - 5):mm.start()]:
        return mm.group(0)
    for n in nums:
        if n not in _REFN:
            _missing.add(n)
    return "[" + ",".join(str(x) for x in sorted({_REFN.get(n, n) for n in nums})) + "]"
for _node in doc.element.body.iter(_qn("w:t")):
    if _node.text and "[" in _node.text and not any(a.tag.endswith("oMath") for a in _node.iterancestors()):
        _t0 = _node.text
        _node.text = _RG.sub(lambda mm: _cite_sub(mm, _t0), _t0)
assert not _missing, f"supplementary cites references not cited in the main text: {sorted(_missing)}"

from _textfix import inline_math, typography   # audit 2026-10-09: M12, m1, m2
print(f"Inline eq: {inline_math(doc)} | typography: {typography(doc)}")

doc.save(str(OUT))
print(f"Saved  : {OUT}")
print(f"Size   : {OUT.stat().st_size / 1024:,.0f} KB")
print(f"Tables : S1 (5x5), S2 (5x5), S3 ({len(s3)} rows), S4 ({len(s4)} rows), "
      f"S5, S6 (MAUP), S7 (LISA FDR); S8 index construction note; S9 LV-density grid-criterion sensitivity; "
      f"S10 data sources and provenance")
