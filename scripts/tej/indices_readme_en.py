"""English guide to the two author-built indices in data/indices/ (2026-10-24).

The two methodology files are in Thai (the authors' working language) and are kept unchanged. This
script writes Docs/indices_README_EN.md, which the release places at data/indices/README_EN.md: an English
summary of each method (indicators, weights, scaling, formula, classes and sources, taken from the Thai
methodology files and from Supplementary Tables S8a and S8b), a column dictionary with an English
glossary of the Thai values, and Thai to English name crosswalks built from the data and checked to be
complete (77 provinces, 50 districts).
"""
import sys
import unicodedata
from pathlib import Path

import fiona
import geopandas as gpd
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _paths import BASE, RAW, SRC

EM = RAW / "Energy map"
PROV_CSV = EM / "Thailand_Provincial_Socioeconomic_Resilience_Index_2566_2567" / "Thailand_Provincial_Index_2566_2567_GIS_v1.csv"
BKK_CSV = EM / "Bangkok District Socioeconomic Resilience Index" / "BKK_District_Index_2567_GIS_v1.csv"
C2 = SRC / "Data" / "14_Processed_90m" / "C2_poverty_province.csv"          # corrected Thai to English pairs (A4)
GADM = SRC / "Data" / "01_Admin_Boundaries" / "gadm41_THA.gpkg"

prov = pd.read_csv(PROV_CSV, encoding="utf-8-sig")
bkk = pd.read_csv(BKK_CSV, encoding="utf-8-sig")
c2 = pd.read_csv(C2, encoding="utf-8-sig")

# ── glossaries of the Thai values that occur in the files ────────────────────────
CLASS = {"สูงมาก": "Very high (80–100)", "สูง": "High (60 to below 80)", "ปานกลาง": "Medium (40 to below 60)",
         "ต่ำ": "Low (20 to below 40)", "ต่ำมาก": "Very low (below 20)"}
REGION = {"กรุงเทพมหานคร": "Bangkok", "ภาคกลาง": "Central", "ภาคตะวันออกเฉียงเหนือ": "Northeast",
          "ภาคเหนือ": "North", "ภาคใต้": "South"}
assert set(prov["class_baseline"]) | set(bkk["class_baseline"]) <= set(CLASS), "class label without translation"
assert set(prov["region_nso"]) <= set(REGION), "region label without translation"

# ── province crosswalk (Thai name in the index -> GADM English name used in the paper) ──
th2en = dict(zip(c2["prov_th"], c2["NAME_1"]))
missing = [t for t in prov["province_join_name"] if t not in th2en]
assert not missing and len(prov) == 77, f"provinces without an English name: {missing}"

# ── district crosswalk, same rule as build_c2_vulnerability_district.py ─────────
def norm(s):
    s = unicodedata.normalize("NFC", str(s)).strip()
    for p in ("เขต", "อำเภอ"):
        if s.startswith(p):
            s = s[len(p):].strip()
    return s
OVERRIDE = {"ทวีวัฒนา": "Thawi Wattana", "ธนบุรี": "Thon Buri", "บางกะปิ": "Bang Kapi", "หลักสี่": "Lak Si"}
adm2 = next(l for l in fiona.listlayers(str(GADM)) if l.endswith("_2"))
gd = gpd.read_file(str(GADM), layer=adm2)
gd = gd[gd["NAME_1"] == "Bangkok Metropolis"]
d_th2en = {norm(t): e for t, e in zip(gd["NL_NAME_2"], gd["NAME_2"])}
d_th2en.update(OVERRIDE)
bkk_en = [d_th2en.get(norm(t)) for t in bkk["district_th"]]
assert all(bkk_en) and len(bkk) == 50, [t for t, e in zip(bkk["district_th"], bkk_en) if not e]
used = set(pd.read_csv(SRC / "Data" / "14_Processed_Bangkok" / "C2_vulnerability_district.csv",
                       encoding="utf-8-sig")["NAME_2"])
assert set(bkk_en) == used, "district names differ from data/bangkok/C2_vulnerability_district.csv"

L = []
w = L.append
w("# Author-built indices: English guide")
w("")
w("This folder holds two composite indices built by the authors from official statistics. Neither is an "
  "official published product. Both are research prototypes. Their full methodology files are in Thai, "
  "the authors' working language, and are kept unchanged. This guide summarises them in English and "
  "explains the Thai names and values in the data files. The summary follows the Thai methodology files "
  "and Supplementary Section S8 (Tables S8a and S8b).")
w("")
w("| File | Language | Content |")
w("|---|---|---|")
w("| `Thailand_Provincial_Index_2566_2567_GIS_v1.csv` | Thai names, English column headers | Provincial index, 77 provinces |")
w("| `Thailand_Provincial_Socioeconomic_Resilience_Index_2566_2567_Methodology.md` | Thai | Full provincial method |")
w("| `BKK_District_Index_2567_GIS_v1.csv` | Thai names, English column headers | Bangkok district index, 50 khet |")
w("| `BKK_District_Socioeconomic_Resilience_Index_2567_v1.xlsx` | Thai | Bangkok workbook (raw data, weights, scores) |")
w("| `BKK_District_Socioeconomic_Resilience_Index_2567_Methodology.md` | Thai | Full Bangkok method |")
w("")
w("Thai years are Buddhist Era (B.E.): B.E. 2566 = 2023, 2567 = 2024.")
w("")
w("## How the paper uses them")
w("")
w("- **Bangkok district index:** only the vulnerability sub-index FV is used, as the equity criterion of "
  "the district demonstration (Supplementary Section S12). It is matched to districts by the English "
  "names in `data/bangkok/C2_vulnerability_district.csv`.")
w("- **Provincial index:** FV and the overall score SER are compared with the paper's index as an external "
  "construct check (Supplementary Table S13f). Neither enters the Priority Area Index.")
w("")
w("## Method summary (both indices)")
w("")
w("- Two dimensions: economic capacity EC and vulnerability FV, each 0–100.")
w("- Overall score: SER = 0.50·EC + 0.50·(100 − FV), so lower vulnerability raises the score.")
w("- Each raw indicator is converted to a percentile rank within its unit set, "
  "S = (rank − 1) / (N − 1) × 100, with N = 77 provinces or 50 districts. Indicators where a lower value "
  "means more vulnerability are reverse-ranked.")
w("- Right-skewed monetary inputs (registered capital) are Winsorised at the 95th percentile before ranking.")
w("- Classes are fixed score bands: very high 80–100, high 60 to below 80, medium 40 to below 60, low 20 to "
  "below 40, very low below 20.")
w("")
w("### Provincial index (reference period 2566–2567, v1.0 weighted baseline model)")
w("")
w("| Code | Indicator | Weight within dimension |")
w("|---|---|---|")
for c, t, wt in [("E1", "Gross provincial product per capita (NESDC, 2567)", "0.25"),
                 ("E2", "Mean monthly household income (NSO, 2566)", "0.20"),
                 ("E3", "Section 33 insured persons per 1,000 population (Social Security Office, 2567)", "0.20"),
                 ("E4", "Newly registered juristic persons per 10,000 population (Department of Business Development, 2567)", "0.15"),
                 ("E5", "Registered capital of new businesses per person, Winsorised at P95 (DBD, 2567)", "0.10"),
                 ("E6", "Diversity of new businesses, normalised Shannon entropy of business categories (DBD, 2567)", "0.10"),
                 ("V1", "Poverty burden proxy: estimated poor headcount / registered population × 100 (NESDC/NSO, DOPA, 2566)", "0.35"),
                 ("V2", "Household expenditure / income × 100 (NSO, 2566)", "0.25"),
                 ("V3", "Household debt / annual income (NSO, 2566)", "0.25"),
                 ("V4", "Registered population change 2566–2567, reverse-ranked (DOPA)", "0.15")]:
    w(f"| {c} | {t} | {wt} |")
w("")
w("V1 is a proxy, not the official poverty rate. The paper's equity criterion C2 uses the official NESDC "
  "poverty incidence instead (Table 2 of the manuscript).")
w("")
w("### Bangkok district index (base year 2567, v1.0 equal-weight baseline model)")
w("")
w("| Code | Indicator | Weight within dimension |")
w("|---|---|---|")
for c, t, wt in [("E1", "Newly registered juristic persons per 1,000 houses (DBD, 2567)", "0.25"),
                 ("E2", "Registered capital per house, Winsorised at P95 (DBD, 2567)", "0.25"),
                 ("E3", "Diversity of new businesses, normalised Shannon entropy (DBD, 2567)", "0.25"),
                 ("E4", "Houses per km² (BMA, 2567)", "0.25"),
                 ("V1", "Slum communities / all communities × 100 (BMA, 2567)", "0.25"),
                 ("V2", "Registered population per house (BMA, 2567)", "0.25"),
                 ("V3", "Green area per person, reverse-ranked (BMA, 2567)", "0.25"),
                 ("V4", "Disaster incidents per 10,000 houses (BMA, 2567)", "0.25")]:
    w(f"| {c} | {t} | {wt} |")
w("")
w("Sources: BMA = Bangkok Metropolitan Administration, Bangkok Statistics 2567. DBD = Department of "
  "Business Development, newly registered juristic persons open data, January to December 2567. "
  "NESDC = Office of the National Economic and Social Development Council. NSO = National Statistical "
  "Office. DOPA = Department of Provincial Administration (registered population).")
w("")
w("## Column dictionary")
w("")
w("`Thailand_Provincial_Index_2566_2567_GIS_v1.csv`")
w("")
w("| Column | Meaning |")
w("|---|---|")
for c, m in [("province_th", "Province name in Thai"), ("province_join_name", "Thai name used to join to boundaries (English names in the crosswalk below)"),
             ("region_nso", "NSO region, Thai label (glossary below)"), ("rank_baseline", "Rank by overall score SER, 1 = highest"),
             ("resilience_score_baseline", "Overall score SER, 0–100"), ("economic_score_baseline", "Economic capacity EC, 0–100"),
             ("vulnerability_score_baseline", "Vulnerability FV, 0–100"), ("class_baseline", "SER class, Thai label (glossary below)"),
             ("gpp_per_capita_2567", "Gross provincial product per capita, THB, 2567"),
             ("household_income_monthly_2566", "Mean monthly household income, THB, 2566"),
             ("poverty_burden_proxy_pct_2566", "Indicator V1, %, 2566")]:
    w(f"| `{c}` | {m} |")
w("")
w("`BKK_District_Index_2567_GIS_v1.csv`")
w("")
w("| Column | Meaning |")
w("|---|---|")
for c, m in [("district_th", "District (khet) name in Thai"), ("district_join_name", "Thai name with the prefix เขต (khet), used to join to boundaries"),
             ("rank_baseline", "Rank by overall score SER, 1 = highest"), ("resilience_score_baseline", "Overall score SER, 0–100"),
             ("economic_score_baseline", "Economic capacity EC, 0–100"), ("vulnerability_score_baseline", "Vulnerability FV, 0–100 (the value the paper uses)"),
             ("class_baseline", "SER class, Thai label (glossary below)")]:
    w(f"| `{c}` | {m} |")
w("")
w("## Glossary of Thai values")
w("")
w("| Thai | English |")
w("|---|---|")
for k, v in list(CLASS.items()) + list(REGION.items()):
    w(f"| {k} | {v} |")
w("")
w("## Crosswalk: provinces (77)")
w("")
w("English names are the GADM 4.1 names used throughout the paper and in `data/province/`. Pairs are taken "
  "from the corrected poverty table (amendment A4).")
w("")
w("| Thai | English |")
w("|---|---|")
for t in prov.sort_values("province_join_name")["province_join_name"]:
    w(f"| {t} | {th2en[t]} |")
w("")
w("## Crosswalk: Bangkok districts (50)")
w("")
w("English names are the GADM 4.1 level-2 names used in `data/bangkok/`. Four Thai names are matched by a "
  "fixed rule because GADM spells them differently (ทวีวัฒนา, ธนบุรี, บางกะปิ, หลักสี่).")
w("")
w("| Thai | English |")
w("|---|---|")
for t, e in sorted(zip(bkk["district_th"], bkk_en)):
    w(f"| {t} | {e} |")

text = "\n".join(L) + "\n"
assert "—" not in text and ";" not in text, "house style: no em dash, no semicolon"
out = BASE / "Docs" / "indices_README_EN.md"
out.write_text(text, encoding="utf-8")
print(f"{out.name}: {len(L)} lines, 77 provinces and 50 districts cross-walked")
