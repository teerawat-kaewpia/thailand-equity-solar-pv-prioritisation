"""
DER Paper v2 — Generalized EWM-TOPSIS Framework (Group A+B revision)
=====================================================================
Revision per "A Generalized EWM.docx" feedback, provincial demonstration only:
 - Generalized five-slot criterion framing (Resource/Equity/Demand/Infra/Physical)
 - Restructured: Sec 2 Generalized Framework -> Sec 3 Demonstration (Thailand)
 - New Sec 2.7 qualitative cost/grid-capacity screen (+ Table {T:grid})
 - New Sec 2.8 criterion transferability (+ Table {T:transfer})
 - Revised Sec 4.7 OSM validation limitations language
 - Tables renumbered sequentially T1-T12; Figs 10/11 swapped to citation order
 - District-scale (Bangkok) analysis NOT included (Group C -> future work)
Output: D:\\Clude Code GIS\\Energy\\DER\\DER_Paper_Manuscript_FULL_v2.docx
"""
from pathlib import Path
import re
import pandas as pd
from docx import Document
from docx.shared import Pt, Cm, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_TAB_ALIGNMENT
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
from PIL import Image as PILImage
from lxml import etree

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
from _paths import SRC, BASE, out_path, fig, data
from _figures import figin   # single figure registry, no fallback to the DER mirror
from _sens import SENS_RHO   # full-precision sensitivity rho (no double rounding)
TABLES = SRC / "Tables" / "DER_Paper_Tables.xlsx"   # shared, read-only
OUT    = out_path("Manuscript", "DER_TEJ_Manuscript.docx")

# ── MASTER RESULTS: single source of truth for every quoted number ────────────
# Built by build_master_results.py directly from the analysis outputs. Numbers
# below are interpolated from it so text, tables and captions cannot drift apart.
import json
MR = json.loads(data("master_results.json").read_text(encoding="utf-8"))
# TEJ: grid distances come ONLY from the TEJ pipeline (zone_distances.py, which reads
# mv_distance.py outputs through _lineage.load_mv). The v2 keys MR["gridfinder"] and
# MR["zone_grid_km"] are legacy, unauditable, not reused in the TEJ manuscript.
import sys as _sys
_sys.path.insert(0, str(Path(__file__).resolve().parent))
from _lineage import sha256 as _sha256
ZD = json.loads((BASE / "Data" / "zone_distances" / "zone_distances_tej.json").read_text(encoding="utf-8"))
assert ZD["mv_lineage"]["qa_sha256"] == _sha256(BASE / "Data" / "mv_distance" / "mv_distance_QA.json"), \
    "zone_distances_tej.json is stale relative to mv_distance.py output"
ZK = ZD["zones"]

# ERP post hoc diagnostic (Scripts/erp_posthoc_diagnostic.py), author decision 2026-10-10
ERPD = json.loads((BASE / "Data" / "erp_diagnostic" / "erp_diagnostic.json").read_text(encoding="utf-8"))
assert ERPD["status"].startswith("post hoc diagnostic")
assert ZD["rank_line_km"][0] == "3" and set(ZD["rank_line_km"][-2:]) == {"4", "5"} and ZD["rank_mv_km"][0] == "1"
# Counterfactual allocation scenarios (scenarios.py, protocol + amendments A2, A3)
SC = pd.read_csv(BASE / "Data" / "scenarios" / "scenario_tradeoff.csv").set_index("scenario")
SM = json.loads((BASE / "Data" / "scenarios" / "scenario_members.json").read_text(encoding="utf-8"))["meta"]
def sc(k, col, fmt="{:.2f}"):
    return fmt.format(SC.loc[k, col])
# Grid cell counts come from each pipeline's own QA record, never typed literals.
PAIQA = json.loads((BASE / "Data" / "qa" / "pai_grid_qa.json").read_text(encoding="utf-8"))
AWC = json.loads((BASE / "Data" / "area_weight_check" / "area_weight_check.json").read_text(encoding="utf-8"))   # review item 4
assert AWC["unweighted_reproduces_run4"]["zones_agree"] == 77 and AWC["zones_agree_77"] == 77 and AWC["S2_same"] and AWC["S3_same"]
assert PAIQA["crs"] == "EPSG:4326"
# Use FULL-precision weights/entropy for text so 3-dp rounding matches the
# tables and figures (which also round from full precision). Reading the
# already-4-dp-rounded values double-rounds and diverged for C2 and C5
# (0.333 vs 0.332, 0.171 vs 0.170).
Wt, En = MR["weights_full"], MR["entropy_full"]
def wt(c): return f"{Wt[c]:.3f}"
def en(c): return f"{En[c]:.3f}"

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


# protocol amendments, counted from the deposited protocol (review item 8, 2026-10-16: the text said three)
_AMEND = __import__("re").findall(r"^### A(\d+) ", (BASE / "Docs" / "SCENARIO_PROTOCOL.md").read_text(encoding="utf-8"),
                                  __import__("re").M)
assert _AMEND == ["1", "2", "3", "4", "5"], ("amendment text in Section 3.5 describes A1 to A5", _AMEND)
def names(xs): return xs[0] if len(xs) == 1 else ", ".join(xs[:-1]) + " and " + xs[-1]
def pai(p): return f"{_PAI[p]:.3f}"
_SBK = MR["bootstrap"]["stability_by_k"]
assert all(_SBK[k]["top_cluster_size"] >= len(_Z1) for k in ("2", "3", "4", "5"))   # contiguous 1-D bands


def D(crit, stat):
    """Descriptive statistic, formatted as the paper quotes it."""
    v = MR["descriptives"][crit][stat]
    if stat == "cv_pct":
        return f"{v:.2f}"
    if stat == "skew":
        return f"{v:+.2f}"
    return f"{v:.4f}" if stat in ("mean", "sd") else f"{v:.3f}"

# ── REFERENCES: built by build_references.py, every DOI verified against the
#    CrossRef registry (title-match guarded). CITEMAP renumbers the in-text
#    citations, which were written against the earlier 29-entry list, onto the
#    expanded list without having to retype them.
REFS = json.loads((BASE / "Data" / "references.json").read_text(encoding="utf-8"))
REF_ENTRIES = REFS["entries"]

CITEMAP = {
    1: 38,   # UNFCCC Paris Agreement
    2: 39,   # IEA Southeast Asia Outlook
    3: 1,    # Pepermans, distributed generation
    4: 2,    # Sovacool, energy decisions as justice
    5: 20,   # Charabi, PV site suitability fuzzy MCE
    6: 24,   # Ali, Songkhla Thailand
    7: 40,   # AEDP 2018
    8: 11,   # Ahlborg, rural electrification
    9: 12,   # Bhattacharyya & Palit, mini-grid
    10: 47,  # Saaty, AHP
    11: 37,  # Shannon
    12: 32,  # Haklay & Weber, OpenStreetMap
    13: 48,  # Hwang & Yoon, TOPSIS
    14: 15,  # Chen, effects of entropy weight on TOPSIS
    15: 25,  # Anselin, LISA
    16: 16,  # Shao, MCDM review (replaces unregistered Li et al.)
    17: 29,  # Arderne, global power system
    18: 30,  # Kruitwagen, PV inventory
    19: 42,  # EPPO statistics
    20: 43,  # DEDE statistics
    21: 44,  # World Bank Tracking SDG7
    22: 22,  # Majumdar, agrivoltaics Phoenix
    23: 14,  # Behzadian, TOPSIS survey
    24: 4,   # Heffron & McCauley, energy justice
    25: 13,  # Bhattacharyya, energy access programmes
    26: 23,  # Noorollahi, FAHP land suitability
    27: 36,  # Lave, solar variability
    28: 45,  # NESDC index
    29: 46,  # BMA index
}


def cite(*old):
    """Render an in-text citation, renumbering from the original scheme."""
    numbers = sorted(CITEMAP[o] for o in old)
    return "[" + ",".join(str(n) for n in numbers) + "]"

# ── Load all Excel sheets ──────────────────────────────────────────────────────
XL = pd.ExcelFile(TABLES)
T  = {sh: pd.read_excel(XL, sheet_name=sh) for sh in XL.sheet_names}

# ── Generalized criterion renaming (applied to table headers and cells) ───────
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
        # Apply the terminology map by value type so the generated manuscript
        # is invariant to the pandas version used for the build.
        df[col] = df[col].map(lambda v: _ren(v) if isinstance(v, str) else v)
    return df

# ── Figure paths (paper order; 10 = validation, 11 = sensitivity) ─────────────
FIGS = {
    "framework": figin("framework"),
    "study-region": figin("study-region"),
    "criteria-maps": figin("criteria-maps"),
    "pai-map": figin("pai-map"),
    "zones": figin("zones"),
    "deployment": figin("deployment"),
}

FIG_CAPTIONS = {
    # review 2026-10-24: poverty is a province statistic, not a 90 m raster criterion
    "framework": ("Fig. {F:framework}.", "Workflow for constructing and evaluating the Priority Area Index. "
         "Raster criteria were harmonised on a common 90 m grid and summarised by province, while official "
         "poverty incidence was assigned at province level. The five provincial criteria were weighted by "
         "the entropy weight method and ranked using bounded-ideal TOPSIS. The resulting index was "
         "evaluated for spatial structure and robustness, compared with recorded deployment, and applied "
         "to the counterfactual allocation rules and the policy screen. A candidate emission-reduction "
         "proxy (ERP) was removed before weighting because it overlapped with demand density C3 "
         f"(Spearman ρ = {ERPD['rho_erp_c3']:.3f})."),
    "study-region": ("Fig. {F:study-region}.", "Demonstration study region: Thailand's 77 provinces with six "
         "administrative regions. Map lines delineate study areas and do not necessarily depict accepted national boundaries. Geographic coordinates, WGS 84 (EPSG:4326)."),
    "criteria-maps": ("Fig. {F:criteria-maps}.", "Spatial distributions of the five criterion slots across "
         "Thailand's 77 provinces (criterion surfaces harmonised on a common 90 m working "
         "grid, with all analysis at the province level): (a) C1 Resource Potential (solar "
         "PVOUT), (b) C2 Equity (poverty incidence), (c) C3 Demand Density (population), "
         "(d) C4 Infrastructure Access (grid proximity) and (e) C5 Physical Suitability. "
         "Colours show province means of the 90 m criterion surfaces before the province-level "
         "rescaling used in the index: C2 as poverty incidence (%), the other panels as their "
         "pixel-level or formula scores (0–1), and C3 without its log transform. Map lines delineate study areas and do not necessarily depict accepted national boundaries. Geographic coordinates, WGS 84 (EPSG:4326)."),
    "pai-map": ("Fig. {F:pai-map}.", "Province-level Priority Area Index (PAI) on a continuous colour scale spanning "
         f"the observed range ({MR['pai']['min']:.3f}–{MR['pai']['max']:.3f}). Labels mark the three highest- and three lowest-ranked "
         "provinces. Map lines delineate study areas and do not necessarily depict accepted national boundaries. Geographic coordinates, WGS 84 (EPSG:4326)."),
    "zones": (f"Fig. {{F:zones}}.", f"K-means zone map (Zone 1 = highest priority, Zone 5 = lowest). "
         f"Zone 1 comprises {MR['zones']['1']['n']} provinces on "
         f"{MR['zones']['1']['land_pct']:.1f}% of national land, entered through high poverty, "
         f"high irradiance with flat land, or both. Map lines delineate study areas and do not necessarily depict accepted national boundaries. Geographic coordinates, WGS 84 (EPSG:4326)."),
    "deployment": (f"Fig. {{F:deployment}}.", f"Comparison with existing deployment. (a) Province PAI against OSM-mapped "
         f"OSM solar installations (n = {MR['validation']['n_plants']}, 77 provinces). (b) Installation "
         f"counts by priority zone. The "
         f"full PAI is uncorrelated with installation counts "
         f"(ρ = {MR['validation']['pai_vs_count_spearman']:.3f}, p = "
         f"{MR['validation']['p']:.2f}) because two opposing "
         f"signals cancel: the efficiency-only composite is positively associated "
         f"(ρ = +{MR['validation']['efficiency_only_vs_count_spearman']:.3f}) and equity "
         f"negatively (ρ = {MR['validation']['equity_vs_count_spearman']:.3f}). Zone 1 "
         f"holds {MR['zone_validation']['zone1_hit_rate']*100:.1f}% of installations on "
         f"{MR['zone_validation']['zone1_land_share']*100:.1f}% of national land."),
}

# ── Document and page setup ────────────────────────────────────────────────────
doc = Document()
sec = doc.sections[0]
sec.page_width   = Cm(21.0)
sec.page_height  = Cm(29.7)
sec.left_margin  = sec.right_margin  = Cm(2.54)
sec.top_margin   = sec.bottom_margin = Cm(2.54)

PAGE_W = Cm(15.5)   # usable text width

# ── Global font: Times New Roman throughout ────────────────────────────────────
TNR = "Times New Roman"

def _set_style_font(style_name, size_pt, bold=False, color=None):
    s = doc.styles[style_name]
    s.font.name  = TNR
    s.font.size  = Pt(size_pt)
    s.font.bold  = bold
    if color:
        s.font.color.rgb = RGBColor(*color)
    rPr = s.font._element
    rFonts = rPr.find(qn("w:rFonts"))
    if rFonts is None:
        rFonts = OxmlElement("w:rFonts")
        rPr.insert(0, rFonts)
    rFonts.set(qn("w:ascii"), TNR)
    rFonts.set(qn("w:hAnsi"), TNR)
    rFonts.set(qn("w:cs"),    TNR)

_set_style_font("Normal",    12)
_set_style_font("Heading 1", 13, bold=True)
_set_style_font("Heading 2", 12, bold=True)
_set_style_font("Heading 3", 11, bold=True)
try:
    _set_style_font("List Bullet", 12)
except Exception:
    pass

ns = doc.styles["Normal"]
ns.paragraph_format.alignment  = WD_ALIGN_PARAGRAPH.JUSTIFY
ns.paragraph_format.space_after = Pt(0)

# ── Style helpers ──────────────────────────────────────────────────────────────
def h1(text):
    doc.add_heading(text, level=1)

def h2(text):
    doc.add_heading(text, level=2)

def _apply_tnr(run, size_pt=12, italic=False, bold=False):
    run.font.name  = TNR
    run.font.size  = Pt(size_pt)
    run.font.italic = italic
    run.font.bold   = bold

def para(text, size=12, space_after=6, indent=True, align=WD_ALIGN_PARAGRAPH.JUSTIFY):
    p = doc.add_paragraph()
    p.alignment = align
    p.paragraph_format.space_after  = Pt(space_after)
    p.paragraph_format.space_before = Pt(0)
    if indent:
        p.paragraph_format.first_line_indent = Cm(0.5)
    r = p.add_run(text)
    _apply_tnr(r, size)
    return p

_MML_NS = "http://www.w3.org/1998/Math/MathML"
_MML2OMML = etree.XSLT(etree.parse(
    r"C:\Program Files\Microsoft Office\root\Office16\MML2OMML.XSL"
))

_EQUATION_MATHML = {
    1: """<math xmlns="http://www.w3.org/1998/Math/MathML"><mrow>
      <msub><mi>r</mi><mrow><mi>i</mi><mi>j</mi></mrow></msub><mo>=</mo>
      <mfrac><mrow><msub><mi>x</mi><mrow><mi>i</mi><mi>j</mi></mrow></msub><mo>-</mo><msub><mi>x</mi><mrow><mi>min</mi><mo>,</mo><mi>j</mi></mrow></msub></mrow>
      <mrow><msub><mi>x</mi><mrow><mi>max</mi><mo>,</mo><mi>j</mi></mrow></msub><mo>-</mo><msub><mi>x</mi><mrow><mi>min</mi><mo>,</mo><mi>j</mi></mrow></msub></mrow></mfrac>
    </mrow></math>""",
    2: """<math xmlns="http://www.w3.org/1998/Math/MathML"><mrow>
      <msub><mi>p</mi><mrow><mi>i</mi><mi>j</mi></mrow></msub><mo>=</mo>
      <mfrac><msub><mi>r</mi><mrow><mi>i</mi><mi>j</mi></mrow></msub>
      <mrow><munder><mo largeop="true">&#x2211;</mo><mi>i</mi></munder><msub><mi>r</mi><mrow><mi>i</mi><mi>j</mi></mrow></msub></mrow></mfrac>
    </mrow></math>""",
    3: """<math xmlns="http://www.w3.org/1998/Math/MathML"><mrow>
      <msub><mi>e</mi><mi>j</mi></msub><mo>=</mo><mo>-</mo>
      <mfrac><mn>1</mn><mrow><mi>ln</mi><mo>(</mo><mi>m</mi><mo>)</mo></mrow></mfrac><mo>&#x22c5;</mo>
      <munder><mo largeop="true">&#x2211;</mo><mi>i</mi></munder>
      <mrow><mo>(</mo><msub><mi>p</mi><mrow><mi>i</mi><mi>j</mi></mrow></msub><mo>&#x22c5;</mo><mi>ln</mi><msub><mi>p</mi><mrow><mi>i</mi><mi>j</mi></mrow></msub><mo>)</mo></mrow>
      <mo>,</mo><mspace width="0.5em"/><mtext>with </mtext><msub><mi>p</mi><mrow><mi>i</mi><mi>j</mi></mrow></msub><mi>ln</mi><msub><mi>p</mi><mrow><mi>i</mi><mi>j</mi></mrow></msub><mo>=</mo><mn>0</mn><mtext> when </mtext><msub><mi>p</mi><mrow><mi>i</mi><mi>j</mi></mrow></msub><mo>=</mo><mn>0</mn>
    </mrow></math>""",
    4: """<math xmlns="http://www.w3.org/1998/Math/MathML"><mrow><msub><mi>d</mi><mi>j</mi></msub><mo>=</mo><mn>1</mn><mo>-</mo><msub><mi>e</mi><mi>j</mi></msub></mrow></math>""",
    5: """<math xmlns="http://www.w3.org/1998/Math/MathML"><mrow>
      <msub><mi>w</mi><mi>j</mi></msub><mo>=</mo><mfrac><msub><mi>d</mi><mi>j</mi></msub><mrow><munder><mo largeop="true">&#x2211;</mo><mi>j</mi></munder><msub><mi>d</mi><mi>j</mi></msub></mrow></mfrac>
      <mo>,</mo><mspace width="0.8em"/><munder><mo largeop="true">&#x2211;</mo><mi>j</mi></munder><msub><mi>w</mi><mi>j</mi></msub><mo>=</mo><mn>1</mn>
    </mrow></math>""",
    6: """<math xmlns="http://www.w3.org/1998/Math/MathML"><mrow>
      <msup><mi>A</mi><mo>+</mo></msup><mo>=</mo><mo>{</mo><msubsup><mi>v</mi><mi>j</mi><mo>+</mo></msubsup><mo>=</mo><msub><mi>w</mi><mi>j</mi></msub><mo>&#x22c5;</mo><msubsup><mi>r</mi><mi>j</mi><mo>+</mo></msubsup><mo>=</mo><msub><mi>w</mi><mi>j</mi></msub><mo>&#x22c5;</mo><mn>1</mn><mo>=</mo><msub><mi>w</mi><mi>j</mi></msub><mo>|</mo><mi>j</mi><mo>&#x2208;</mo><mtext>benefit</mtext><mo>}</mo>
    </mrow></math>""",
    7: """<math xmlns="http://www.w3.org/1998/Math/MathML"><mrow>
      <msup><mi>A</mi><mo>-</mo></msup><mo>=</mo><mo>{</mo><msubsup><mi>v</mi><mi>j</mi><mo>-</mo></msubsup><mo>=</mo><msub><mi>w</mi><mi>j</mi></msub><mo>&#x22c5;</mo><msubsup><mi>r</mi><mi>j</mi><mo>-</mo></msubsup><mo>=</mo><msub><mi>w</mi><mi>j</mi></msub><mo>&#x22c5;</mo><mn>0</mn><mo>=</mo><mn>0</mn><mo>|</mo><mi>j</mi><mo>&#x2208;</mo><mtext>benefit</mtext><mo>}</mo>
    </mrow></math>""",
    8: """<math xmlns="http://www.w3.org/1998/Math/MathML"><mrow>
      <msubsup><mi>d</mi><mi>i</mi><mo>+</mo></msubsup><mo>=</mo><msqrt><mrow><munder><mo largeop="true">&#x2211;</mo><mi>j</mi></munder><msup><mrow><mo>(</mo><msub><mi>v</mi><mrow><mi>i</mi><mi>j</mi></mrow></msub><mo>-</mo><msubsup><mi>v</mi><mi>j</mi><mo>+</mo></msubsup><mo>)</mo></mrow><mn>2</mn></msup></mrow></msqrt>
    </mrow></math>""",
    9: """<math xmlns="http://www.w3.org/1998/Math/MathML"><mrow>
      <msubsup><mi>d</mi><mi>i</mi><mo>-</mo></msubsup><mo>=</mo><msqrt><mrow><munder><mo largeop="true">&#x2211;</mo><mi>j</mi></munder><msup><mrow><mo>(</mo><msub><mi>v</mi><mrow><mi>i</mi><mi>j</mi></mrow></msub><mo>-</mo><msubsup><mi>v</mi><mi>j</mi><mo>-</mo></msubsup><mo>)</mo></mrow><mn>2</mn></msup></mrow></msqrt>
    </mrow></math>""",
    10: """<math xmlns="http://www.w3.org/1998/Math/MathML"><mrow>
      <msub><mi>PAI</mi><mi>i</mi></msub><mo>=</mo><mfrac><msubsup><mi>d</mi><mi>i</mi><mo>-</mo></msubsup><mrow><msubsup><mi>d</mi><mi>i</mi><mo>+</mo></msubsup><mo>+</mo><msubsup><mi>d</mi><mi>i</mi><mo>-</mo></msubsup></mrow></mfrac><mo>,</mo><mspace width="0.8em"/><mi>PAI</mi><mo>&#x2208;</mo><mo>[</mo><mn>0</mn><mo>,</mo><mn>1</mn><mo>]</mo>
    </mrow></math>""",
    11: """<math xmlns="http://www.w3.org/1998/Math/MathML"><mrow>
      <mi>I</mi><mo>=</mo><mfrac><mi>n</mi><msub><mi>S</mi><mn>0</mn></msub></mfrac><mo>&#x22c5;</mo>
      <mfrac><mrow><munder><mo largeop="true">&#x2211;</mo><mi>i</mi></munder><munder><mo largeop="true">&#x2211;</mo><mi>j</mi></munder><msub><mi>w</mi><mrow><mi>i</mi><mi>j</mi></mrow></msub><msub><mi>z</mi><mi>i</mi></msub><msub><mi>z</mi><mi>j</mi></msub></mrow>
      <mrow><munder><mo largeop="true">&#x2211;</mo><mi>i</mi></munder><msup><msub><mi>z</mi><mi>i</mi></msub><mn>2</mn></msup></mrow></mfrac>
    </mrow></math>""",
}


def eq(text):
    """Insert an editable, professionally built-up Word equation (OMML)."""
    match = re.search(r"\((\d+)\)\s*$", text)
    if not match:
        raise ValueError(f"Equation number missing from: {text}")
    number = int(match.group(1))
    mathml = etree.fromstring(_EQUATION_MATHML[number].encode("utf-8"))
    omml = _MML2OMML(mathml).getroot()

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.LEFT
    p.paragraph_format.left_indent       = Cm(0)
    p.paragraph_format.space_before      = Pt(3)
    p.paragraph_format.space_after       = Pt(3)
    p.paragraph_format.first_line_indent = Cm(0)
    tabs = p.paragraph_format.tab_stops
    tabs.add_tab_stop(Cm(7.96), WD_TAB_ALIGNMENT.CENTER)
    tabs.add_tab_stop(Cm(15.92), WD_TAB_ALIGNMENT.RIGHT)
    p.add_run("\t")
    p._p.append(omml)
    p.add_run("\t")
    r = p.add_run(f"({number})")
    _apply_tnr(r, 10.5)
    return p

def bullet(text):
    p = doc.add_paragraph(style="List Bullet")
    p.paragraph_format.space_after = Pt(3)
    r = p.add_run(text)
    _apply_tnr(r, 12)
    return p

def spacer():
    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(4)

# Usable text height = A4 (29.7 cm) minus top+bottom margins (2 x 2.54 cm) = 24.62 cm.
# Reserve ~3 cm for the caption and paragraph spacing so a tall figure plus its
# caption still fits on one page.
MAX_FIG_H_CM = 21.5

def insert_fig(n, width_cm=14.5):
    path = FIGS[n]
    if not path.exists():
        p = doc.add_paragraph(f"[Figure {n}: file not found: {path.name}]")
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        return
    # Scale by width normally, but fall back to height-limited scaling for tall
    # figures (e.g. the 77-province ranking chart) so they do not overflow the page.
    with PILImage.open(str(path)) as im:
        px_w, px_h = im.size
    if width_cm * (px_h / px_w) > MAX_FIG_H_CM:
        size_kwargs = {"height": Cm(MAX_FIG_H_CM)}
    else:
        size_kwargs = {"width": Cm(width_cm)}
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(6)
    p.add_run().add_picture(str(path), **size_kwargs)
    cap = doc.add_paragraph()
    cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
    cap.paragraph_format.space_after = Pt(12)
    cap.paragraph_format.first_line_indent = Cm(0)
    label, rest = FIG_CAPTIONS[n]
    r_bold = cap.add_run(label + " ")
    _apply_tnr(r_bold, size_pt=9, bold=True)
    r_rest = cap.add_run(rest)
    _apply_tnr(r_rest, size_pt=9, italic=True)

def set_col_widths(table, widths_cm):
    # fixed layout: Word otherwise autofits and ignores the cell widths (review 2026-10-18, split ranges)
    table.autofit = False
    for gc, w in zip(table._tbl.tblGrid.findall(qn("w:gridCol")), widths_cm):
        gc.set(qn("w:w"), str(int(Cm(w).twips)))
    for row in table.rows:
        for i, cell in enumerate(row.cells):
            if i < len(widths_cm):
                cell.width = Cm(widths_cm[i])

from _tablestyle import apply_rules, fit_widths

def make_table(df, col_widths=None, font_size=9, header_shade="#1F4E79"):
    n_cols = len(df.columns)
    tbl = doc.add_table(rows=1, cols=n_cols)
    tbl.style = "Table Grid"
    hdr = tbl.rows[0].cells
    for i, col in enumerate(df.columns):
        hdr[i].text = ""
        run = hdr[i].paragraphs[0].add_run(str(col))
        hdr[i].paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.LEFT
        _apply_tnr(run, size_pt=font_size, bold=True)
        tc   = hdr[i]._tc
        tcPr = tc.get_or_add_tcPr()
        shd  = OxmlElement("w:shd")
        shd.set(qn("w:val"), "clear")
        shd.set(qn("w:color"), "auto")
        shd.set(qn("w:fill"), header_shade.lstrip("#"))
        tcPr.append(shd)
    for _, row in df.iterrows():
        cells = tbl.add_row().cells
        for i, val in enumerate(row):
            cells[i].text = ""
            run = cells[i].paragraphs[0].add_run(
                "" if pd.isna(val) else str(val)
            )
            cells[i].paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.LEFT   # no justified spacing in cells
            _apply_tnr(run, size_pt=font_size)
    if col_widths:
        set_col_widths(tbl, fit_widths(df, col_widths, font_size))   # no split numbers or words
    apply_rules(tbl)   # TEJ guide: no vertical rules, no shading
    spacer()
    return tbl

def tbl_caption(text):
    p = doc.add_paragraph()
    p.paragraph_format.space_after       = Pt(3)
    p.paragraph_format.space_before      = Pt(10)
    p.paragraph_format.first_line_indent = Cm(0)
    label, rest = text.split(".", 1)
    rb = p.add_run(label + ". ")
    _apply_tnr(rb, size_pt=9, bold=True)
    rr = p.add_run(rest.strip())
    _apply_tnr(rr, size_pt=9)

# ══════════════════════════════════════════════════════════════════════════════
# TITLE PAGE
# ══════════════════════════════════════════════════════════════════════════════
# Title, authors and journal line are written as SEPARATE paragraphs rather than
# one run with embedded newlines: a manual line break inside a run is dropped by
# some text extractors, which silently concatenates words ("SpatialPrioritization").
# One paragraph per line is unambiguous and lets the publisher reflow the title.
def _front(text, size_pt, bold=False, italic=False, space_after=0):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.first_line_indent = Cm(0)
    p.paragraph_format.space_after = Pt(space_after)
    _apply_tnr(p.add_run(text), size_pt=size_pt, bold=bold, italic=italic)
    return p

from _meta import TITLE, REPO_URL, RELEASE, DOI, credit_statement   # one source for all documents
_front(TITLE, size_pt=15, bold=True, space_after=18)

# Authors and affiliations: DER_paper_repo\Doc Edited\Title_page.docx (authors' own)
_pa = _front("", size_pt=12, space_after=6)
for txt, sup in [("Thanapon Saengsuwan", "a"), (", Teerawat Kaewpia", "b,*")]:
    _apply_tnr(_pa.add_run(txt), size_pt=12)
    _r = _pa.add_run(sup)
    _apply_tnr(_r, size_pt=12)
    _r.font.superscript = True
for sup, aff in [
    ("a", "Program in Energy Engineering and Electrical Technology, Faculty of Industrial "
          "Technology, Chiang Rai Rajabhat University, Chiang Rai, 57100, Thailand"),
    ("b", "Program in Logistics Engineering and Management, Faculty of Industrial Technology, "
          "Chiang Rai Rajabhat University, Chiang Rai, 57100, Thailand"),
]:
    _p = _front("", size_pt=10, italic=True)
    _r = _p.add_run(sup)
    _apply_tnr(_r, size_pt=10, italic=True)
    _r.font.superscript = True
    _apply_tnr(_p.add_run(" " + aff), size_pt=10, italic=True)
_front("*Corresponding author. E-mail: teerawat.kae@crru.ac.th", size_pt=10, space_after=12)


doc.add_page_break()

# ══════════════════════════════════════════════════════════════════════════════
# HIGHLIGHTS
# ══════════════════════════════════════════════════════════════════════════════
h1("Highlights")
HIGHLIGHTS = [
    "Counterfactual allocation rules for distributed solar compared under one budget",
    # review item 5: the poverty gain is partly by construction (poverty enters the index that selects S2)
    f"By design, equity targeting raised poverty exposure from {sc('S1','mean_poverty_pct','{:.1f}')}% to {sc('S2','mean_poverty_pct','{:.1f}')}%",
    # review formatting item: shortened from 85 characters (the TEJ limit) to leave a margin
    f"Median line distance was {SC.loc['S2','median_dist_line_km'] / SC.loc['S3','median_dist_line_km']:.1f} "
    "times that of the resource-and-infrastructure rule",
    "No spatial or poverty-targeting rule found among the solar instruments examined",
    "Utility feeder and transformer checks gate every candidate policy response",
]
for hl in HIGHLIGHTS:
    assert len(hl) <= 80, (len(hl), hl)   # TEJ limit 85, kept 5 below
    bullet(hl)
spacer()

# ══════════════════════════════════════════════════════════════════════════════
# ABSTRACT
# ══════════════════════════════════════════════════════════════════════════════
h1("Abstract")
para(
    "Distributed solar photovoltaics (PV) can lower household energy costs, but who benefits "
    "depends on how support is allocated and on what local distribution networks can absorb. "
    "This paper asks how alternative allocation rules for distributed solar support would "
    "differ in poverty exposure and network access across Thailand's provinces, and how they "
    "compare with the instruments currently in force. An equity-aware Priority Area Index, "
    "built with the entropy weight method and a bounded-ideal variant of the technique for order "
    "preference by similarity to ideal solution (TOPSIS), ranks the 77 provinces. "
    f"Equity, measured by official poverty incidence, received the largest weight "
    f"(w = {wt('C2_Equity')}) and ran counter to an efficiency-only composite "
    f"(ρ = {MR['equity_vs_efficiency_only']['spearman']:.3f}). Three counterfactual allocation "
    "rules then distribute one hypothetical budget across the 74 provinces served by the "
    "Provincial Electricity Authority: a population-proportional baseline, an equity-targeted "
    "rule and a resource-and-infrastructure comparator. By construction, the equity-targeted rule "
    f"raised the allocation-weighted poverty incidence from {sc('S1','mean_poverty_pct')}% to "
    f"{sc('S2','mean_poverty_pct')}% ({sc('S3','mean_poverty_pct')}% under the comparator). "
    "The trade-off was in network access: the allocation-weighted median distance to mapped "
    f"power lines was {sc('S2','median_dist_line_km','{:.1f}')} km against "
    f"{sc('S3','median_dist_line_km','{:.1f}')} km, "
    "and the median distance to modelled medium-voltage lines differed less "
    f"({sc('S2','median_dist_mv_km')} against {sc('S3','median_dist_mv_km')} km). Among the "
    "instruments examined, including the 2026 residential net-billing round and the community "
    "solar regulation, no spatial or poverty-targeting allocation rule was identified, and "
    "connection depends on utility feeder and transformer checks. The scenarios are screening "
    "counterfactuals, not evaluations of implemented policy, and do not replace "
    "hosting-capacity assessment."
)
para(
    "Keywords: distributed solar PV, distribution planning, net billing, equity, "
    "allocation scenarios, entropy weight method, Thailand"
)
spacer()

# ══════════════════════════════════════════════════════════════════════════════
# 1. INTRODUCTION
# ══════════════════════════════════════════════════════════════════════════════
h1("1. Introduction")
# concise pass 2026-10-24: policy terms are given once, in Section 5.4
para(
    "Distributed solar photovoltaics (PV), here rooftop and small ground-mounted systems "
    "connected to the distribution network, are now part of routine distribution planning: "
    "households and communities generate on the low- and medium-voltage network, and "
    "utilities decide whether each connection can be absorbed [1]. Storage, wind and demand "
    "response are outside the scope. Where support goes, and who receives it, has "
    "distributional consequences. In the United States, Black- and Hispanic-majority census "
    "tracts installed less rooftop PV after accounting for income and home ownership [7], "
    "adoption inequity also appears at the census-tract level [9] and persists across policy "
    "regimes and business models [8], and a systematic review finds such disparities to be a "
    "general feature of household solar [10]. Energy-justice scholarship frames these outcomes "
    "as distributional questions [3,4], and energy poverty is itself spatially clustered [5,6]."
)
para(
    "Thailand offers a concrete setting. Its 2026 instruments, a residential net-billing round "
    "of the Energy Regulatory Commission (ERC) [49,51], a community solar regulation [50] and transformer-level connection limits of the "
    "Provincial Electricity Authority (PEA) [51], define how much distributed solar can be bought and under which "
    "network conditions, but not where support should go (Section 5.4). The Power Development "
    "Plan 2018 Revision 1 (PDP2018 Rev.1) remains the adopted plan [39], and the draft Power "
    "Development Plan 2026 (PDP2026), under consultation since 8 September 2026, is "
    "treated as planning context, not as an instrument in force [40]."
)
para(
    "Spatial multi-criteria studies of solar siting typically rank places by resource, land "
    "and infrastructure criteria [20,24] and stop at the ranking. A ranking does not show what "
    "a programme would gain or give up by allocating support one way rather than another, nor "
    "how the result relates to the instruments in force and the network checks that gate "
    "every connection. This paper pairs an equity-aware provincial index with counterfactual "
    "allocation rules evaluated under one hypothetical budget and relates both to the "
    "instruments examined."
)
para(
    "Three research questions guide the analysis. (RQ1) Where does an equity-aware index "
    "place priority across Thailand's 77 provinces, and how does its equity criterion relate "
    "to the efficiency criteria? (RQ2) Under one hypothetical budget, how do counterfactual "
    "allocation rules differ in poverty exposure, solar resource, and distance to mapped "
    "power lines and to the modelled medium-voltage (MV) network? (RQ3) How do the "
    "instruments currently in force compare with these rules, and which utility checks gate "
    "implementation? An urban application in the service area of the Metropolitan Electricity "
    "Authority (MEA) is reported in Supplementary Section S12."
)
spacer()

# ══════════════════════════════════════════════════════════════════════════════
# 2. GENERALIZED FRAMEWORK
# ══════════════════════════════════════════════════════════════════════════════
h1("2. Equity-Aware Priority Index")

h2("2.1 Index Architecture")
para(
    "The index moves from spatial data to a ranked set of provinces in five steps (Fig. {F:framework}). "
    "Candidate criteria are screened for multicollinearity, normalised to a common scale "
    "and weighted by the entropy weight method (EWM). A bounded-ideal TOPSIS ranking then "
    "gives each unit a Priority Area Index (PAI). The units are grouped into priority zones "
    "and tested for spatial clustering. The allocation scenarios and the network-distance "
    "screen of Section 3.5 are applied to this output."
)
insert_fig("framework", width_cm=15.9)

h2("2.2 Criterion Slots and Multicollinearity Screening")
para(
    "The framework is expressed in five interchangeable criterion slots (Table {T:criteria}): "
    "C1 Resource Potential, C2 Equity, C3 Demand Density, C4 Infrastructure Access, and "
    "C5 Physical Suitability. Each slot defines a planning dimension, not a fixed dataset. "
    "Alternative indicators for other contexts are listed in Supplementary Table {T:transfer}. "
    "Retained criteria are checked for multicollinearity with the variance inflation factor (VIF), "
    "against a threshold of 10.0."
)
tbl_caption(
    "Table {T:criteria}. Generalised criterion slots, demonstration indicators (Thailand), and "
    "normalisation method."
)
t1_slots = pd.DataFrame({
    "Slot": ["C1", "C2", "C3", "C4", "C5"],
    "Generalised Dimension": [
        "Resource Potential", "Equity", "Demand Density",
        "Infrastructure Access", "Physical Suitability",
    ],
    "Demonstration Indicator (Thailand)": [
        "Solar PVOUT (kWh/kWp/year), Global Solar Atlas v2 LTAy [46]",
        "Poverty incidence (%), NESDC/NSO household socio-economic survey",
        "Population density (WorldPop 2020)",
        "Grid proximity exp(−d/5 km), OSM power lines and cables",
        "Hansen forest exclusion [30] × slope < 15° × non-built (GHSL)",
    ],
    "Type": ["Benefit"] * 5,
    "Normalisation": ["Pixel: 2nd–98th pct clip. Province: linear [0, 1], 2nd–98th pct clip",
                      "Raw %. Province: linear [0, 1], 2nd–98th pct clip",
                      "Pixel: 2nd–98th pct clip. Province: log(1 + 100x), then linear [0, 1], 2nd–98th pct clip"]
                     + ["Formula score. Province: linear [0, 1], 2nd–98th pct clip"] * 2,
})
make_table(t1_slots, col_widths=[0.9, 2.9, 6.0, 1.4, 3.3], font_size=8)

h2("2.3 Weighting and Ranking")
para(
    "Scaling works at two levels. C1 and C3 are continuous 90 m surfaces with pixel-level "
    "outliers, so each is scaled linearly to [0, 1] at the pixel level after clipping at its "
    "2nd and 98th percentiles, before provincial aggregation. C4 and C5 are formula scores "
    "already in [0, 1]. Poverty (C2) is kept as the original province-level percentage when "
    "rasterised. For the province-level PAI, demand density (C3) is log-transformed, "
    "log(1 + 100x), to reduce its right skew, and all five aggregated criteria are then "
    "clipped at the 2nd and 98th percentiles and scaled linearly to [0, 1] once. Weights follow from the Shannon entropy of each criterion's distribution "
    "across units, so a criterion that separates units more sharply receives more weight "
    "[15,35]. Entropy weights therefore measure how strongly a criterion differentiates the "
    "units, not its normative or policy importance. The weighted matrix is ranked by TOPSIS [45,14] with the ideal and nadir fixed "
    "at the bounds of the normalised scale (1 and 0) rather than at the observed extrema. "
    "The PAI is the closeness coefficient, ⟪pai-def⟫, where ⟪d-plus⟫ and ⟪d-minus⟫ are the "
    "Euclidean distances to the ideal and the nadir, so PAI lies in [0, 1]. Recomputing "
    "with observed-extrema ideals reproduced the ranking exactly (Spearman ρ = 1.000). The "
    "full equations are given in Supplementary Section S13."
)

h2("2.4 Zoning, Spatial Structure and Robustness")
para(
    "K-means clustering (k = 5) groups the PAI scores into priority zones. Five tiers is a "
    "planning convention, not a data-driven optimum (Section 4.4). Global and local Moran's "
    "I with queen contiguity and conditional permutations test whether priority clusters "
    "in space [25]. Ranking robustness is assessed under equal and expert weights, by "
    "bootstrap resampling of the entropy weights and by varying the number of clusters."
)

h2("2.5 Network-Distance Screen")
para(
    "Zones are screened by the mean distance of their provinces to the power-line network "
    "mapped in OpenStreetMap (OSM) and to a modelled medium-voltage network (Section 3.5). Distance indicates "
    "connection convenience. It is not hosting capacity."
)

spacer()

# ══════════════════════════════════════════════════════════════════════════════
# 3. DEMONSTRATION: THAILAND'S 77 PROVINCES
# ══════════════════════════════════════════════════════════════════════════════
h1("3. Demonstration: Thailand's 77 Provinces")

h2("3.1 Study Region")
para(
    "Thailand has 77 provinces in six regions (Fig. {F:study-region}). Poverty is highest in the "
    "western border provinces of Mae Hong Son and Tak, the deep south and parts of the "
    "north-eastern plateau, while population and the transmission backbone are densest in the "
    "Central region. MEA serves Bangkok, Nonthaburi and Samut Prakan, and PEA the remaining 74 "
    "provinces [54,61]. Household electrification is effectively universal [37], so the "
    "relevant spatial disparity is network geography rather than connection."
)
# Fig. 2 directly after Section 3.1 (layout 2026-10-24, after the Fig. 1 redesign moved the page breaks:
# placed after the Section 3.2 paragraph it left page 6 at 16%)
insert_fig("study-region", width_cm=14.0)
h2("3.2 Data and Preprocessing")
para(
    "The five criteria were populated with the datasets in Table {T:data}. Raster layers were "
    f"resampled to a common grid of 0.000833° (WGS 84, EPSG:4326), approximately 90 m "
    f"({AWC['grid']['ns_m']:.0f} m north–south and {AWC['grid']['ew_m_at_20N']:.0f}–"
    f"{AWC['grid']['ew_m_at_6N']:.0f} m east–west across Thailand), and the PAI is defined on the "
    f"{PAIQA['pai_grid_valid_cells']:,} cells valid in every criterion layer. The grid serves "
    "harmonisation only: province values are unweighted means of their cells, and every "
    "statistic is computed on the 77 provinces. Weighting cells by their latitude-dependent area "
    f"(at most {AWC['within_province_area_weight_spread_max_pct']:.1f}% spread within a province) "
    "changed no province mean by more than "
    f"{100 * max(AWC['max_relative_change_of_province_means'].values()):.1f}% and no PAI by more "
    f"than {AWC['max_abs_PAI_change']:.4f}, and left the zones and scenario memberships unchanged "
    "(Supplementary Section S6). Poverty incidence is one official value per province, so no "
    "poverty information is implied below province resolution. A sixth candidate criterion, an "
    "emission-reduction proxy (ERP) from night-time light and a national emission factor, was "
    "excluded because it overlapped with the demand-density criterion C3 "
    f"(Spearman ρ = {ERPD['rho_erp_c3']:.3f}). A VIF of 24.98 reported for ERP in an earlier "
    "version of this analysis could not be reproduced after the correction of C2 and is not "
    "used as a basis for exclusion. Adding ERP back would shift the index toward urban "
    "provinces and double-count demand (Supplementary Section S13.11). The retained criteria "
    f"have VIF ≤ {MR['vif_max']:.2f}."
)
tbl_caption(
    "Table {T:data}. Data sources for the five criteria, the network-distance screen and the "
    "deployment comparison."
)
t3_data = {
    "Dataset": [
        "Global Solar Atlas v2, LTAy PVOUT",
        "NESDC/NSO provincial poverty incidence [55]",
        "WorldPop, unconstrained UN-adjusted population [56]",
        "OSM power lines and cables (Overpass) [57]",
        "Hansen Global Forest Change v1.11, tree cover",
        "Copernicus DEM GLO-30 (slope) [58]",
        "GHSL GHS-BUILT-H ANBH R2023A [59]",
        "GridFinder modelled MV lines [29]",
        "GADM administrative boundaries [60]",
        "OSM solar plants (Overpass) [57]",
    ],
    "Use": ["C1 Resource", "C2 Equity", "C3 Demand", "C4 Infrastructure", "C5 Physical",
            "C5 Physical", "C5 Physical", "Network screen", "Province boundaries",
            "Deployment comparison"],
    "Native resolution": ["1 km", "Province", "100 m", "Vector", "30 m", "30 m",
                          "3 arc-seconds", "Vector", "Vector", "Point"],
    "Version or date": ["Long-term average", "2022", "2020", "OSM state 22 June 2026",
                        "Year 2000 layer", "GLO-30", "Epoch 2018", "Clipped June 2026",
                        "v4.1", "OSM state 22 June 2026"],
}
make_table(pd.DataFrame(t3_data), col_widths=[5.6, 3.0, 2.4, 3.6], font_size=8.5)

h2("3.3 Deployment Comparison Data")
para(
    "Province counts of 332 solar plants were extracted from OSM (power=plant, "
    "plant:source=solar, OSM database state 22 June 2026 [57]). They are compared with the PAI, the "
    "efficiency-only composite and the equity criterion, and with a land-area null model by "
    "zone (chi-square, all expected counts above five). Existing plants are not ground "
    "truth for where deployment ought to occur (Section 4.7)."
)

h2("3.4 Robustness Checks")
para(
    "Ranking robustness was assessed through pre-specified checks: equal weights, "
    "equity-first expert weights, "
    f"{MR['bootstrap']['B']} bootstrap resamples of the entropy weights and alternative "
    "cluster counts. Full results are reported in Supplementary Section S13."
)

h2("3.5 Counterfactual Allocation Scenarios and Network Screening")
para(
    "The allocation scenarios distribute one hypothetical programme budget of "
    f"{SM['B']:,} support units. They are counterfactual allocation rules, not "
    "evaluations of implemented policy, and their outputs are allocation-weighted "
    "exposures, not counts of people who would receive support. The rules, metrics and "
    "class definitions were fixed in a written protocol and hash-recorded before any "
    f"scenario was computed. {nw(len(_AMEND)).capitalize()} amendments are disclosed with the "
    "deposited protocol. "
    "The first changed the counting unit of the PEA substation linkage after its first run, "
    "with the thresholds unchanged. The second, made after an initial run in which one "
    "metropolitan province absorbed most of the equity-targeted budget, restricted the "
    "analysis set to the PEA service area, which is the decision context of this paper and "
    "the area covered by PEA's network data. The third redefined the MV variable before any "
    "MV result was computed. The fourth corrected the provincial poverty input, after a join "
    "on a wrong Thai province name in the boundary data had given two provinces another "
    "province's value, and was written before any corrected result was computed. The fifth "
    "removed a duplicated percentile clip so that the poverty criterion is scaled once, as "
    "stated in Section 2.3, and was written after a diagnostic of the single-clip variant had "
    "been seen. Each of the last two was followed by a full re-run of the analysis."
)
para(
    f"The analysis set is the {SM['analysis_set'].split(' (')[0]}, with a combined "
    f"population of {SM['pea_area_population']/1e6:.1f} million (WorldPop 2020, the C3 input). "
    "Bangkok, Nonthaburi and Samut Prakan, served by MEA, are excluded. S1, a "
    "population-proportional baseline, allocates the budget to all 74 provinces in "
    "proportion to population. S2, an equity-targeted rule, allocates it in proportion to "
    "population among the 15 provinces with the highest PAI. S3, a "
    "resource-and-infrastructure comparator, does the same for the 15 provinces with the "
    f"highest efficiency-only composite (Section 4.2). K = 15 corresponds to {SM['K']} of "
    "the analysis units. S3 represents allocation by resource and infrastructure. It is not a "
    "representation of market behaviour."
)
para(
    "Each rule is described by allocation-weighted metrics: mean poverty incidence, a "
    "poverty-weighted beneficiary equivalent (budget share times poverty incidence), mean "
    "PVOUT, and the weighted median province distance to the OSM-mapped power-line network "
    "(the C4 distance) and to the GridFinder modelled MV network. The MV distance was "
    "computed on a separate 90 m grid in UTM zone 47N as the Euclidean distance from each "
    "cell inside a province to the nearest modelled MV line, averaged by province. Provinces "
    "were grouped into nearer, intermediate and farther MV classes by Jenks natural breaks "
    f"(k = 3, upper bounds {SM['mv_jenks_k3_upper_bounds_km'][0]:.2f}, "
    f"{SM['mv_jenks_k3_upper_bounds_km'][1]:.2f} and {SM['mv_jenks_k3_upper_bounds_km'][2]:.2f} km). "
    "In every class, hosting capacity and connection feasibility are not assessable from "
    "the available data and require utility feeder-level verification."
)
spacer()

# ══════════════════════════════════════════════════════════════════════════════
# 4. RESULTS
# ══════════════════════════════════════════════════════════════════════════════
h1("4. Results")

h2("4.1 Criterion Patterns")
para(
    f"The criterion maps are shown in Fig. {{F:criteria-maps}}, and descriptive statistics are given "
    f"in Supplementary Table {{T:desc}}. Equity has the largest relative dispersion of the five "
    f"criteria (CV = {D('C2_Equity','cv_pct')}%). The PAI ranges from {D('PAI','min')} to "
    f"{D('PAI','max')} and varies less than any of its inputs (CV = {D('PAI','cv_pct')}%), "
    "so small differences between neighbouring provinces should not be over-interpreted."
)
insert_fig("criteria-maps")

h2("4.2 Equity and the Efficiency Criteria")
para(
    "Correlating equity with the full PAI would be circular, because equity is its most "
    "heavily weighted component. The test therefore uses an efficiency-only composite of "
    "C1, C3, C4 and C5, re-weighted by EWM on that set. Against it, equity is negatively "
    f"associated (Spearman ρ = {MR['equity_vs_efficiency_only']['spearman']:.3f}, "
    f"p = {MR['equity_vs_efficiency_only']['p']:.4f}, and p = "
    f"{MR['p_spatial']['C2 Equity vs efficiency-only composite']:.4f} against "
    f"{MR['spatial_permutation']['province'][0]['n_sim']} spatially restricted surrogates). "
    "Poverty is unrelated to solar resource "
    f"(ρ = {MR['equity_vs_each_efficiency']['C1_Resource']['spearman']:.3f}) but negatively "
    "related to infrastructure access "
    f"(ρ = {MR['equity_vs_each_efficiency']['C4_Infra']['spearman']:.3f}), physical suitability "
    f"(ρ = {MR['equity_vs_each_efficiency']['C5_Physical']['spearman']:.3f}) and demand "
    f"density (ρ = {MR['equity_vs_each_efficiency']['C3_Demand']['spearman']:.3f}). Poorer "
    "provinces are, on average, those where deployment is least convenient. Including "
    f"equity moves {MR['equity_removal']['n_shift_gt10']} of 77 provinces by more than ten "
    f"ranks (maximum shift {MR['equity_removal']['max_rank_shift']}). Correlations with the "
    "PAI and variance inflation factors are in Supplementary Table {T:corr}."
)

h2("4.3 Entropy Weights")
para(
    f"Equity received the largest weight (w = {wt('C2_Equity')}), about twice that of any other "
    f"criterion. Infrastructure access (w = {wt('C4_Infra')}), physical suitability "
    f"(w = {wt('C5_Physical')}) and demand density (w = {wt('C3_Demand')}) were close, and "
    f"solar resource was lowest (w = {wt('C1_Resource')}) (Table {{T:weights}}), because poverty "
    "varies far more between Thai provinces than solar resource does (Section 2.3)."
)
tbl_caption("Table {T:weights}. EWM criterion weights and Shannon entropy (n = 77 provinces).")
t6w = T["T2_Criterion_Def"][["Criterion", "Full Name", "Shannon Entropy (e)", "EWM Weight"]].copy()
t6w.columns = ["Criterion", "Dimension", "Shannon Entropy (e)", "EWM Weight (w)"]
_CK = ["C1_Resource", "C2_Equity", "C3_Demand", "C4_Infra", "C5_Physical"]
assert list(t6w["Criterion"]) == ["C1", "C2", "C3", "C4", "C5"]
t6w["Shannon Entropy (e)"] = [en(c) for c in _CK]          # full precision, rounded once
t6w["EWM Weight (w)"] = [wt(c) for c in _CK]
make_table(rename_crit(t6w), col_widths=[1.8, 4.5, 3.0, 3.0], font_size=8.5)

h2("4.4 Priority Zones and Network Distances")
para(
    f"K-means clustering of the PAI (Fig. {{F:pai-map}}) gave five zones (Table {{T:zones}}, Fig. {{F:zones}}). Zone 1 holds "
    f"{MR['zones']['1']['n']} provinces (PAI {MR['zones']['1']['pai_min']:.3f}–"
    f"{MR['zones']['1']['pai_max']:.3f}): {names(_Z1)}. They reach the top tier through high poverty, high irradiance with flat land, "
    "or both (Section 4.6), and Zone 5 "
    "combines low poverty with forested or mountainous terrain. The silhouette coefficient "
    f"is nearly flat across k = 2–6, and k = 5 is within "
    f"{MR['cluster_stability']['silhouette_max'] - MR['cluster_stability']['silhouette_k5']:.3f} of "
    "the best value, so the zones are a planning typology on a gradient, and the province ordering "
    "carries the information."
)
tbl_caption(
    "Table {T:zones}. Zone statistics: PAI distribution and criterion mean values for each "
    "deployment priority zone. K-means (k = 5) was applied to the 77 province-level PAI "
    "scores, so each province belongs to exactly one zone and the zone PAI ranges do not "
    "overlap. Land Area (%) is the share of national land area occupied by the provinces "
    "in each zone."
)
t8_sel = T["T7_Zone_Stats"][[
    "Zone", "PAI Range", "N Provinces", "Land Area (%)",
    "PAI Mean", "PAI SD", "C1 Solar Mean", "C2 Poverty Mean",
    "C3 PopDens Mean", "C4 GridDist Mean", "C5 LandSuit Mean"
]].copy()
make_table(rename_crit(t8_sel),
           # 11 columns: total kept under the 15.92 cm usable text width
           col_widths=[0.9, 1.7, 1.2, 1.2, 1.1, 1.0, 1.45, 1.45, 1.45, 1.45, 1.45],
           font_size=7.5)

para(
    f"Distances to the two networks behave differently (Table {{T:grid}}). Zone means span "
    f"{ZK['3']['line_km_mean']:.1f}–{ZK['5']['line_km_mean']:.1f} km to the OSM-mapped power lines, "
    f"with Zone 3 nearest and Zones 4 and 5 farthest. Within Zone 1 the province means range "
    f"from {ZK['1']['line_km_min']:.1f} to {ZK['1']['line_km_max']:.1f} km. Distances to the "
    "GridFinder modelled MV network [29] are "
    f"shorter ({ZK['1']['mv_km_mean']:.2f}–{ZK['5']['mv_km_mean']:.2f} km), and Zone 1 has the "
    "lowest zone mean. Across the 77 provinces PAI is negatively associated with distance to "
    f"the modelled MV lines (Spearman ρ = {ZD['spearman_PAI_vs_mv_mean_77']['rho']:.3f}, "
    f"p {'< 0.001' if ZD['spearman_PAI_vs_mv_mean_77']['p'] < 0.001 else '= ' + format(ZD['spearman_PAI_vs_mv_mean_77']['p'], '.3f')}) "
    "but not significantly associated with distance to the power lines "
    f"(ρ = {ZD['spearman_PAI_vs_line_mean_77']['rho']:.3f}, p = {ZD['spearman_PAI_vs_line_mean_77']['p']:.2f}). "
    "Neither distance measures hosting capacity, which depends on impedance, voltage regulation "
    "and protection settings [27,28]. Replacing the power-line criterion with a GridFinder "
    "low-voltage density surface kept the provincial ranking close to the published one "
    f"(ρ = {MR['pai_mv']['spearman_paiMV_vs_published']:.3f}) and the "
    f"equity association negative (ρ = {MR['pai_mv']['efficiency_equity_mv']:.3f}), although it "
    "changed the zone boundaries (Supplementary Table {T:S-lv})."
)
tbl_caption(
    "Table {T:grid}. Grid-distance screen by deployment priority zone. Distance to the "
    "OSM-mapped power-line network is the zone mean of province mean cell distances "
    "recovered from the C4 raster (⟪c4-dist⟫, approximate to within a few percent). "
    "Distance to the GridFinder modelled MV network is the zone mean of province mean "
    "distances computed on a 90 m UTM 47N grid. Both are distance measures of connection "
    "convenience, not feeder hosting capacity or connection feasibility, which require "
    "utility network data (Section 5.3). Zone statistics use the national 77-province "
    "analytical base, whereas policy-allocation scenarios are restricted to the 74 provinces "
    "in the PEA service area."
)
_zc = MR["zone_criterion_means"]
t9_screen = pd.DataFrame({
    "Zone": [1, 2, 3, 4, 5],
    "Provinces": [ZK[str(z)]["n"] for z in range(1, 6)],
    "Power lines, mean km (range)": [
        f"{ZK[str(z)]['line_km_mean']:.1f} ({ZK[str(z)]['line_km_min']:.1f}–{ZK[str(z)]['line_km_max']:.1f})"
        for z in range(1, 6)],
    "Modelled MV, mean km (range)": [
        f"{ZK[str(z)]['mv_km_mean']:.2f} ({ZK[str(z)]['mv_km_min']:.2f}–{ZK[str(z)]['mv_km_max']:.2f})"
        for z in range(1, 6)],
    "Grid-access index (C4)": [f"{_zc[str(z)]['C4_Infra']:.3f}" for z in range(1, 6)],
})
make_table(t9_screen, col_widths=[1.0, 1.6, 4.2, 4.2, 2.6], font_size=8.5)
# layout 2026-10-24 (after the Fig. 1 redesign): Fig. 2 after Section 3.1 and Figs. 4 and 5 after
# Table 5 leave no half-empty page apart from the title page
insert_fig("pai-map")
insert_fig("zones")

h2("4.5 Spatial Structure")
para(
    f"Priority is moderately clustered in space (global Moran's I = {MR['morans_I']['I']:.3f}, "
    f"permutation p = {MR['morans_I']['p']:.3f}). No local cluster remains significant after "
    f"false-discovery-rate correction across {MR['lisa_fdr']['n_tests']} tests, so priority "
    "forms several separated pockets rather than one target region (Supplementary Section S13)."
)

h2("4.6 Province Ranking")
para(
    f"Pattani ranked first (PAI = {pai('Pattani')}), with the second-highest poverty incidence "
    f"in the country after Mae Hong Son. Of the other Zone 1 provinces, {names(_POVONLY)} rank "
    f"in the national top fifth for poverty only, {names(_IRRONLY)} for irradiance only, and "
    f"{names(_BOTH)} for both. The lowest-ranked provinces "
    f"combine relative affluence with constrained terrain, led by Loei ({pai('Loei')}) "
    f"and Chiang Mai ({pai('Chiang Mai')}). Bangkok does not enter the top tier "
    "because intra-urban disadvantage is invisible at province level (Supplementary Section "
    "S12). The full ranking is in Supplementary Table {T:S-ranking}."
)

h2("4.7 Comparison with Existing Deployment")
_z1 = MR["zone_validation"]["zone_table"][0]
para(
    f"Across the {MR['validation']['n_plants']} OSM-mapped solar power plants, the full PAI was "
    f"uncorrelated with plant counts (ρ = {MR['validation']['pai_vs_count_spearman']:.3f}) because "
    "two associations offset each other. The efficiency-only composite was positively "
    f"associated with plants (ρ = +{MR['validation']['efficiency_only_vs_count_spearman']:.3f}, "
    f"p = {MR['validation']['efficiency_only_p']:.4f}) and equity negatively "
    f"(ρ = {MR['validation']['equity_vs_count_spearman']:.3f}, p = {MR['validation']['equity_p']:.4f}). "
    f"Zone 1 holds {_z1['land_pct']:.1f}% of national land but {_z1['solar_obs_pct']:.1f}% of "
    "OSM-mapped plants (Fig. {F:deployment}, Supplementary Table {T:osmzones}). Existing plants "
    "record where deployment has been profitable, not where it ought to occur. OpenStreetMap "
    "coverage is not universal and its quality is not systematically measured [31]. The comparison is therefore "
    "descriptive, not a validation of the index: the land-area null model does not control for "
    "developable land or grid access, so it shows divergence, not a measured deployment deficit."
)
insert_fig("deployment")

h2("4.8 Robustness")
para(
    "The ranking was stable under equity-first expert weights "
    f"(Spearman ρ = {SENS_RHO['expert']:.3f}) and less so under equal weights "
    f"(ρ = {SENS_RHO['equal']:.3f}). The bootstrap interval of the equity weight "
    f"({MR['bootstrap']['weight_ci']['C2_Equity'][0]:.3f}–{MR['bootstrap']['weight_ci']['C2_Equity'][1]:.3f}) "
    f"lies above the intervals of all other criteria, and the {nw(len(_Z1))} Zone 1 provinces stayed in "
    "the highest cluster for k = 2–5. Details are in Supplementary Section S13."
)

h2("4.9 Allocation Scenarios: Poverty Exposure and Network Access")
para(
    f"The three rules differ most in poverty exposure (Table {{T:allocation}}). The equity-targeted rule S2 "
    f"raised the allocation-weighted mean poverty incidence to {sc('S2','mean_poverty_pct')}%, "
    f"against {sc('S1','mean_poverty_pct')}% under the baseline and "
    f"{sc('S3','mean_poverty_pct')}% under the comparator S3. This difference arises partly by "
    "construction, because poverty enters the PAI that selects the S2 provinces. "
    f"S2 reached {int(SC.loc['S2','regions'])} "
    f"regions and the baseline {int(SC.loc['S1','regions'])}, while S3 reached "
    f"{int(SC.loc['S3','regions'])}. Mean PVOUT differed little "
    f"({sc('S2','mean_pvout_kwh_kwp','{:,.0f}')} against {sc('S3','mean_pvout_kwh_kwp','{:,.0f}')} "
    "kWh/kWp/yr), consistent with Thailand's even solar resource."
)
para(
    "Network access is where the rules part. The weighted median distance to mapped power "
    f"lines was {sc('S2','median_dist_line_km','{:.1f}')} km under S2 against "
    f"{sc('S3','median_dist_line_km','{:.1f}')} km under S3 and "
    f"{sc('S1','median_dist_line_km','{:.1f}')} km under the baseline. Distances to the "
    f"modelled MV network were shorter and closer together ({sc('S2','median_dist_mv_km')}, "
    f"{sc('S3','median_dist_mv_km')} and {sc('S1','median_dist_mv_km')} km), so equity "
    f"targeting changed MV access far less than line access. S2 placed "
    f"{sc('S2','share_B_farther_pct','{:.1f}')}% of the budget in the farther MV class, "
    f"against {sc('S3','share_B_farther_pct','{:.1f}')}% under S3. No province received more "
    f"than {SC['max_province_share_pct'].max():.1f}% of the budget under any rule."
)
para(
    "No rule is ranked as best: preferring one requires a normative weighting of poverty "
    "exposure against network access that the analysis does not supply, and the metrics "
    "describe where support would go, not how much capacity would be installed or connected."
)
tbl_caption(
    "Table {T:allocation}. Counterfactual allocation rules under one hypothetical budget (74 PEA-served "
    "provinces). Means and medians are weighted by budget share. Distances are province "
    "means to the OSM-mapped power-line network (C4) and to the GridFinder modelled MV "
    "network. MV classes are Jenks classes (k = 3) of the MV distance. The rules are "
    "counterfactuals, not evaluations of implemented policy."
)
_t14 = SC.reset_index()[["scenario", "label", "provinces", "regions", "mean_poverty_pct",
                         "mean_pvout_kwh_kwp", "median_dist_line_km", "median_dist_mv_km",
                         "share_B_farther_pct"]].copy()
_t14["scenario"] = _t14["scenario"] + " " + _t14["label"]
_t14 = _t14.drop(columns="label")
_t14.columns = ["Rule", "Provinces", "Regions", "Mean poverty (%)", "Mean PVOUT (kWh/kWp/yr)",
                "Median km to power lines", "Median km to modelled MV", "Budget in farther MV class (%)"]
_t14["Mean PVOUT (kWh/kWp/yr)"] = _t14["Mean PVOUT (kWh/kWp/yr)"].map(lambda v: f"{v:,.0f}")
# fixed decimals per column (review 2026-10-18: 1.70 printed as "1.7" beside 1.77 and 1.16)
for _c, _d in (("Mean poverty (%)", 2), ("Median km to power lines", 1), ("Median km to modelled MV", 2),
               ("Budget in farther MV class (%)", 1)):
    _t14[_c] = _t14[_c].map(lambda v, d=_d: f"{v:.{d}f}")
make_table(_t14, col_widths=[4.2, 1.4, 1.3, 1.6, 1.9, 1.8, 1.9, 1.8], font_size=7.5)
spacer()

# ══════════════════════════════════════════════════════════════════════════════
# 5. DISCUSSION
# ══════════════════════════════════════════════════════════════════════════════
h1("5. Discussion")

h2("5.1 Why Equity Dominates the Weights")
para(
    "Entropy weighting, applied without normative input, made equity the dominant criterion "
    "and solar resource the weakest (Section 4.3), whereas regional siting studies usually "
    "treat irradiance and land as the primary determinants [20,23,24]. The difference is "
    "methodological: irradiance varies modestly across Thailand while poverty varies a great "
    "deal. Where insolation varies more, the ordering would likely reverse, so the weights "
    "should be re-derived in each context rather than transported. Unlike expert elicitation "
    "such as the analytic hierarchy process [44], the procedure needs no elicitation while "
    "keeping the dependence on weights visible (Section 4.8). Within Thailand the consequence "
    "is substantive: priority shifts toward north-eastern and deep-south provinces rather than "
    "the most bankable locations, which treats siting as a question of who benefits as well as "
    "where generation is cheapest [2]."
)
h2("5.2 Need-Based Priority and Recorded Deployment")
para(
    "Recorded deployment is consistent with efficiency-oriented siting, and the provinces that "
    "equity-aware assessment identifies are largely those with the least recorded deployment "
    "(Section 4.7). The two orderings disagree about much of the country, so an "
    "equity-weighted index does not merely relabel what technical assessment already finds. "
    "Because priority forms separated pockets (Section 4.5) reached by different routes "
    "(Section 4.6), a single target region would misdirect effort."
)
h2("5.3 Network Screen and Robustness")
para(
    "The network screen tempers the ranking rather than displacing it. Several high-priority "
    "provinces combine acute need with long distances to the mapped power lines yet lie close "
    "to the modelled MV network (Section 4.4). That argues for sizing deployment to the "
    "distribution network, not for demoting those provinces, and for a utility "
    "hosting-capacity study before a programme is scaled up. The ranking is robust to the "
    "equity weight but sensitive to equal weighting, which discards the dispersion information "
    "that entropy weighting uses (Section 4.8). Equal weighting is therefore not a neutral "
    "default, and a planner who prefers an investment-return view should use the "
    "efficiency-only composite explicitly."
)
h2("5.4 Policy Implications")
para(
    "The scenarios answer what a programme gains and gives up under different allocation "
    "rules, not which provinces rank highest. Directing support by the equity-aware index "
    "raises poverty exposure by construction, and the informative result is what accompanies "
    "it: longer distances to mapped power lines, with distances to the modelled MV network "
    "changing much less (Section 4.9). Implementing a need-based allocation rule through "
    "rooftop or community projects would still require feeder- and transformer-level "
    "verification by the utility, which a province-level screen cannot provide."
)
para(
    "Table {T:policy} sets the zones against the instruments in force at the policy cutoff of "
    "16 October 2026 (full legal basis in Supplementary Table {T:S-policy-full}). Under the ERC "
    "invitation of June 2026, household rooftop solar is purchased under net billing at "
    "2.20 THB/kWh for up to 5 kW per meter over ten years, within a combined MEA and PEA target "
    "of 500 MW, and applications are accepted first come first served [49,51]. The community "
    "solar regulation, effective 23 September 2026, buys up to 1,500 MW from projects of at "
    "most 10 MW at a feed-in tariff of 2.1679 THB/kWh, and the distribution utility sizes each "
    "project to the grid capacity at its feeder connection point and the local load, with no "
    "reverse flow to the transmission system [50]. In the PEA service area, the combined "
    "contracted sale capacity of programme connections on one distribution transformer may not "
    "exceed 25% of its kVA rating, and PEA may limit inverter size [51]. Among the instruments "
    "examined, no spatial or poverty-targeting allocation rule was identified. The Energy "
    "Conservation Promotion Fund [52] appears in Table {T:policy} only as a conditional "
    "candidate, because the Act does not establish whether its criteria cover distributed "
    "solar, and the progressive residential tariff applied from the September 2026 bill [53] "
    "bears on affordability but deploys no capacity. Every candidate response remains subject "
    "to the utility's connection verification (Section 5.3). A rule that reserved part of an "
    "instrument for high-priority provinces would be a new design and is not evaluated here."
)
para(
    "The observed gap should be read narrowly. It concerns the allocation rules of the "
    "instruments examined (Supplementary Table {T:S-policy-docs}), not Thai energy policy as a "
    "whole, and other measures may reach low-income households in ways this screen does not "
    "capture. Nor does it imply that the instruments are poorly designed for their own "
    "objectives, which include buying capacity within network limits. The scenarios show what "
    "a targeting rule would change if policymakers chose to introduce one."
)
tbl_caption(
    "Table {T:policy}. Zone-to-policy screen. Spatial conditions summarise Tables {T:zones} and {T:grid}. MV classes "
    "(nearer, intermediate, farther) are Jenks classes (k = 3) of province mean distance to the "
    "GridFinder modelled MV lines, computed for the 74 PEA-served provinces only. The three MEA "
    "provinces, all in Zone 2, are outside that classification. The observed policy gap is a "
    "study inference limited to the instruments examined (Supplementary Section S11) and is not "
    "a statement about all Thai policy. Instruments: I1 household rooftop net billing [49], "
    "I2 community solar farm [50], I3 progressive residential tariff [53], I4 Energy "
    "Conservation Promotion Fund [52]. Connection gates follow the PEA requirements [51]."
)
_t15 = pd.read_csv(BASE / "Tables" / "zone_policy_table_main.csv")
make_table(_t15, col_widths=[1.0, 3.0, 4.0, 5.0, 2.9], font_size=7.5)

h2("5.5 Limitations")
para(
    "Several limitations bound these results. The entropy weights reflect Thailand's "
    "dispersion structure. Aggregating to provinces exposes the results to the modifiable "
    "areal unit problem [26], although re-running the pipeline at region and amphoe scales "
    + ("kept equity the largest weight, by a narrow margin at those two scales, "
       if all(v == 1 for v in MR["maup"]["equity_weight_rank_by_scale"].values())
       else "kept equity among the two largest weights ")
    + "and the efficiency–equity association "
    "negative (Supplementary Table {T:S-maup}). The raster inputs have native resolutions "
    "from 30 m to 1 km and poverty is one value per province, so resampling to the 90 m working "
    "grid adds no detail to the coarser layers and province means hide intra-provincial "
    "variation. The gridded population input and the night-light data behind the modelled MV "
    "network have known accuracy limits [32,33], the power-line distance is approximate to "
    "within a few percent, and the physical-suitability criterion omits statutory land-use "
    "zoning, so its scores are an upper bound. The analysis includes no feeder-level hosting "
    "capacity, time-resolved load or existing distributed generation, and the allocation rules "
    "do not model uptake, affordability or installation cost. PEA's published remaining "
    "generation capacity is recorded per substation and could not be linked reliably to "
    "provinces, so it informs the implementation gate but not the scenarios."
)
para(
    "The policy screen covers only the instruments examined, with a 16 October 2026 cutoff. Draft PDP2026 and the "
    "10,000 MW residential rooftop target that the Minister of Energy presented for it on "
    "9 September 2026 were planning targets, not instruments in force: no implementing ERC or "
    "utility instrument for that expansion was located by the cutoff [40,47]. The OSM "
    "installation record carries ascertainment bias. Future work should replace distances with "
    "feeder-level hosting capacity in collaboration with the utilities, use an official "
    "installation registry with capacities, and test targeting rules within an actual "
    "instrument design."
)
spacer()

# ══════════════════════════════════════════════════════════════════════════════
# 6. CONCLUSION
# ══════════════════════════════════════════════════════════════════════════════
h1("6. Conclusion")
para(
    "This paper paired an equity-aware provincial index for distributed solar PV with "
    "counterfactual allocation rules and a screen of the instruments in force in Thailand. "
    "Criterion surfaces were aggregated to the 77 provinces before analysis, and the key "
    "correlations were also tested against spatially restricted permutation nulls, which "
    "left the conclusions unchanged."
)
para(
    f"RQ1: Entropy weighting gave the largest weight to equity (w = {wt('C2_Equity')}) and "
    f"the smallest to solar resource (w = {wt('C1_Resource')}), because poverty varies far "
    "more between Thai provinces than the solar resource does. Equity ran counter to the "
    f"efficiency criteria (ρ = {MR['equity_vs_efficiency_only']['spearman']:.3f} against an "
    f"efficiency-only composite), and including it moved {MR['equity_removal']['n_shift_gt10']} "
    f"of 77 provinces by more than ten ranks. The {nw(len(_Z1))} Zone 1 provinces "
    f"(PAI {MR['zones']['1']['pai_min']:.3f}–{MR['zones']['1']['pai_max']:.3f}) have the "
    f"lowest mean distance to the modelled MV network of any zone ({ZK['1']['mv_km_mean']:.2f} km). "
    "The ranking was stable under equity-first expert weights and less so under equal "
    "weights (Section 4.8)."
)
para(
    f"RQ2: Under one hypothetical budget, the equity-targeted rule raised allocation-weighted "
    f"poverty incidence to {sc('S2','mean_poverty_pct')}%, against {sc('S1','mean_poverty_pct')}% "
    f"under the population-proportional baseline and {sc('S3','mean_poverty_pct')}% under the "
    "resource-and-infrastructure comparator, partly by construction because poverty enters "
    "the index that selects its provinces. The accompanying change was in access to "
    f"mapped power lines ({sc('S2','median_dist_line_km','{:.1f}')} against "
    f"{sc('S3','median_dist_line_km','{:.1f}')} km), while access to the modelled MV network "
    f"differed less ({sc('S2','median_dist_mv_km')} against {sc('S3','median_dist_mv_km')} km). "
    "The rules are counterfactuals and none is ranked as best."
)
para(
    "RQ3: Among the instruments examined, the 2026 residential net-billing round allocates "
    "first come first served, the community solar regulation sizes each project to feeder "
    "grid capacity and load, and for programme connections PEA caps combined contracted sale capacity at 25% "
    "of each distribution transformer's rating. No spatial or poverty-targeting allocation rule was "
    "identified among them. Every candidate response in Table {T:policy} therefore passes through "
    "the utility's connection checks, which a provincial screen cannot replace."
)

para(
    "The paper contributes an equity-aware provincial index with a reproducible "
    "network-distance screen, a comparison of counterfactual allocation rules under one "
    "budget that quantifies the trade-off between the poverty exposure of support and "
    "access to the network, and a zone-to-policy screen that relates this trade-off to the "
    "instruments in force and to the utility checks that gate them, with every "
    "institutional and regulatory statement traced to a primary document (Supplementary "
    "Section S11). How support is allocated shapes which places and populations the programme reaches."
)
spacer()

# ══════════════════════════════════════════════════════════════════════════════
# DECLARATIONS
# ══════════════════════════════════════════════════════════════════════════════
h1("Declaration of Generative AI and AI-assisted Technologies in the Manuscript Preparation Process")
para(
    # Codex added 2026-10-23 (authors: review only)
    "During the preparation of this work the authors used two large-language-model tools. "
    "Claude (Anthropic), accessed through Claude Code, was used for four bounded purposes: "
    "checking the language accuracy of manuscript text, writing and debugging the "
    "data-processing and analysis code, generating figures from author-specified "
    "specifications, and locating and reading potentially relevant sources, including policy "
    "documents. Codex (OpenAI) was used only to review the manuscript, tables and figures for "
    "consistency with the analysis outputs and the cited sources. The tools had no role in "
    "the study's decision-making and did not generate or alter the source data. All research questions, study design, criteria and data choices, "
    "analytical decisions, interpretation of results and substantive claims were conceived, "
    "checked and validated by the authors, who verified all numerical outputs against the "
    "analysis code, checked every citation against its source, reviewed and edited all "
    "AI-assisted text and code, and take full responsibility for the content of the "
    "publication.",
    indent=False,
)

# TEJ guide, Author contributions (CRediT): roles in _meta.CREDIT (approved 2026-10-23)
h1("CRediT authorship contribution statement")
para(credit_statement(), indent=False)

h1("Declaration of Competing Interest")
para(
    "The author(s) declare that they have no known competing financial interests or personal "
    "relationships that could have appeared to influence the work reported in this paper.",
    indent=False,
)

# TEJ guide, Funding sources: no funding (authors, 2026-10-09), standard Elsevier sentence
h1("Funding")
para(
    "This research did not receive any specific grant from funding agencies in the public, "
    "commercial, or not-for-profit sectors.",
    indent=False,
)

h1("Data Availability")
para(
    "The source datasets used in this study, namely provincial poverty statistics (NESDC/NSO), "
    "gross provincial product and household survey data (NESDC/NSO), BMA district "
    "administrative statistics, WorldPop, VIIRS, Global Solar Atlas, Hansen Global Forest "
    "Change, Copernicus DEM, GHSL, GridFinder, Google Open Buildings, OpenStreetMap and GADM, "
    "are publicly available from the sources cited. The policy documents used for the "
    "zone-to-policy screen are listed in Supplementary Table {T:S-policy-docs}. The two composite "
    "socioeconomic indices used for the district equity criterion and the construct check "
    "(Supplementary Section S13.8, Table {T:construct}) are author-constructed research "
    "prototypes, not official products. Their construction is documented in Supplementary "
    "Section S8 (Tables {T:S-index-a} and {T:S-index-b}), and their per-unit scores are deposited "
    "with the analysis data. Supplementary Sections S1 to S13 provide the criterion "
    "correlation matrices (S1, S2), the full ranking (S3), rank displacements (S4), "
    "spatially restricted significance tests (S5), the aggregation-scale recomputation (S6), "
    "the false-discovery-rate corrected local cluster tests (S7), the composite indices (S8), "
    "the power-line versus LV-density sensitivity (S9), data provenance (S10), the full "
    "zone-to-policy screen (S11), the urban application under the MEA context (S12), and the "
    "equations and extended results moved from the main text (S13). The analysis code, the "
    "province-level results, the allocation-scenario protocol with its "
    f"{nw(len(_AMEND))} disclosed amendments and run log, the scenario inputs and outputs, the "
    "composite-index scores, the figures and a data-provenance table are publicly available "
    f"at {REPO_URL} (release {RELEASE})"
    + (f" and archived at https://doi.org/{DOI}. " if DOI else
       ". A DOI-versioned archive of this release will be cited at acceptance. ")
    + "The 90 m criterion rasters are not redistributed, because they derive from third-party "
    "datasets with their own terms, and can be rebuilt from the cited sources with the deposited "
    "scripts. All reported quantities are computed by the deposited scripts from the cited data.",
    indent=False,
)

# ══════════════════════════════════════════════════════════════════════════════
# REFERENCES
# ══════════════════════════════════════════════════════════════════════════════
_REF_GROUP = re.compile(r"\[([0-9]+(?:\s*[,–-]\s*[0-9]+)*)\]")


def _reference_numbers(match, text):
    """Return reference numbers, or None for numeric mathematical brackets."""
    raw = match.group(1)
    numbers = []
    for part in [p.strip() for p in raw.split(",")]:
        range_match = re.fullmatch(r"(\d+)\s*[–-]\s*(\d+)", part)
        if range_match:
            start, end = map(int, range_match.groups())
            numbers.extend(range(start, end + 1))
        else:
            numbers.append(int(part))
    if not numbers or any(n < 1 or n > len(REF_ENTRIES) for n in numbers):
        return None
    # Do not treat expressions such as A+ = [1] as citations.
    if len(numbers) == 1 and "=" in text[max(0, match.start() - 5):match.start()]:
        return None
    return numbers


def _body_text_nodes():
    for child in doc.element.body.iterchildren():
        for node in child.xpath(".//w:t[not(ancestor::m:oMath)]"):
            yield node


# Number references by first appearance, as required by numbered citation style.
# ── Float labels: check, then resolve {T:..}/{F:..} tokens (see _floats.py) ────
from _floats import check_and_resolve, resolve_text
_items = [(q.text, bool(re.match(r"^(Table|Fig\.) \{[TF]:[A-Za-z0-9\-]+\}\.", q.text))) for q in doc.paragraphs]
_items += [(c.text, False) for _t in doc.tables for _r in _t.rows for c in _r.cells]
_float_problems = check_and_resolve(_items, is_main=True)
import os as _os
if _os.environ.get("FLOATS_ALLOW_UNCITED") == "1":  # stage-1 identity check only
    for _w in [x for x in _float_problems if "never cited" in x]: print("WARNING:", _w)
    _float_problems = [x for x in _float_problems if "never cited" not in x]
assert not _float_problems, chr(10).join(_float_problems)
for _node in doc.element.body.iter(qn("w:t")):
    if _node.text and "{" in _node.text:
        _node.text = resolve_text(_node.text)
assert not any("{T:" in (q.text) or "{F:" in q.text for q in doc.paragraphs), "unresolved float token"
# a string that lost its f prefix prints its fields literally (concise pass 2026-10-24: "{MR['pai_mv'][...]:.3f}")
_raw = [t for t in [q.text for q in doc.paragraphs] + [c.text for _t in doc.tables for _r in _t.rows for c in _r.cells]
        if re.search(r"\{[A-Za-z_][A-Za-z0-9_]*(?:\[|\(|:|\}|\.)|\{\{|\}\}", t)]
assert not _raw, "unformatted f-string field in the document: " + _raw[0][:160]

_citation_order = []
for _node in _body_text_nodes():
    _text = _node.text or ""
    for _match in _REF_GROUP.finditer(_text):
        for _number in _reference_numbers(_match, _text) or []:
            if _number not in _citation_order:
                _citation_order.append(_number)
# TEJ: entries no longer cited in the text are dropped from the list, not appended.
_uncited = [n for n in range(1, len(REF_ENTRIES) + 1) if n not in _citation_order]
if _uncited:
    print("Uncited references dropped:",
          "; ".join(REF_ENTRIES[n - 1][:45] for n in _uncited))
_reference_renumber = {
    old: new for new, old in enumerate(_citation_order, 1)
}
json.dump({str(k): v for k, v in _reference_renumber.items()},
          open(out_path("Data", "qa", "ref_renumber.json"), "w"), indent=0)  # read by the supplementary

for _node in _body_text_nodes():
    _text = _node.text or ""

    def _renumber_match(match):
        numbers = _reference_numbers(match, _text)
        if numbers is None:
            return match.group(0)
        mapped = sorted({_reference_renumber[number] for number in numbers})
        return "[" + ",".join(str(number) for number in mapped) + "]"

    _node.text = _REF_GROUP.sub(_renumber_match, _text)

h1("References")
refs = [
    f"[{new}] {REF_ENTRIES[old - 1]}"
    for new, old in enumerate(_citation_order, 1)
]
for ref in refs:
    p = doc.add_paragraph()
    p.paragraph_format.space_after       = Pt(3)
    p.paragraph_format.first_line_indent = Cm(0)
    p.paragraph_format.left_indent       = Cm(0.8)
    r = p.add_run(ref)
    _apply_tnr(r, size_pt=9)

# ══════════════════════════════════════════════════════════════════════════════
# SAVE
# ══════════════════════════════════════════════════════════════════════════════
_CITATION_GROUP = re.compile(r"\[([0-9]+(?:\s*[,–-]\s*[0-9]+)+)\]")


def _sort_citation_group(match):
    parts = [part.strip() for part in match.group(1).split(",")]
    parts.sort(key=lambda part: int(re.match(r"\d+", part).group()))
    return "[" + ",".join(parts) + "]"


def _clean_manuscript_text(text):
    # Avoid decorative em dashes in prose while preserving scientific notation.
    if text.strip() == "—":
        return "Not applicable"
    text = text.replace(" — ", ", ")
    return _CITATION_GROUP.sub(_sort_citation_group, text)


def _clean_text_nodes(container):
    for node in container.xpath(".//w:t[not(ancestor::m:oMath)]"):
        node.text = _clean_manuscript_text(node.text or "")


# Apply manuscript prose style before the numbered reference list. Bibliographic
# titles remain verbatim, while tables and captions receive the same citation rule.
for paragraph in doc.paragraphs:
    if paragraph.text.strip() == "References":
        break
    _clean_text_nodes(paragraph._p)
for table in doc.tables:
    _clean_text_nodes(table._tbl)

from _textfix import inline_math, typography   # audit 2026-10-09: M12, m1, m2
_n_inline = inline_math(doc)
_typo = typography(doc)
print(f"Inline eq: {_n_inline} | typography: {_typo}")

doc.save(str(OUT))
sz = OUT.stat().st_size / 1024

# Highlights as a separate submission file (TEJ guide: file name must contain "highlights")
_hd = Document()
_hd.styles["Normal"].font.name = "Times New Roman"
_hd.styles["Normal"].font.size = Pt(12)
_hd.add_paragraph().add_run("Highlights").bold = True
for hl in HIGHLIGHTS:
    _hd.add_paragraph(hl, style="List Bullet")
HL_OUT = OUT.parent / "DER_TEJ_Highlights.docx"
_hd.save(str(HL_OUT))
print(f"Saved  : {HL_OUT}")
print(f"Saved  : {OUT}")
print(f"Size   : {sz:,.0f} KB")
print(f"Figures: {sum(1 for f in FIGS.values() if f.exists())}/{len(FIGS)} embedded")
