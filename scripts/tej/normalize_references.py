"""Normalise the reference list format (external review, formatting item, 2026-10-18).

1. Journal names: CrossRef's short-container-title gave abbreviations for some journals and full names
   for others. Every journal is now given by its full name (the CrossRef container-title).
2. A source with a DOI is cited by its DOI only (IEA entry carried both a web URL and the DOI).
3. DOI-backed journal-article titles are normalised to sentence case. Proper nouns and technical
   abbreviations (for example GIS, TOPSIS, LISA, OpenStreetMap and WorldPop) retain their case.
4. The EPPO PDP2026 news item: the percent-encoded Thai URL (about 300 characters) is replaced by the
   EPPO news page plus the access date. The full URL is kept in Docs/PROVENANCE.csv (row P13).
Idempotent: running it twice changes nothing. Edits Data/references.json in place.
"""
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _paths import BASE

F = BASE / "Data" / "references.json"
R = json.loads(F.read_text(encoding="utf-8"))
E = R["entries"]

FULL = {                                    # abbreviation -> CrossRef container-title
    "Nat Energy": "Nature Energy",
    "Nat Sustain": "Nature Sustainability",
    "Environ. Res. Lett": "Environmental Research Letters",
    "Environ Sci Pollut Res": "Environmental Science and Pollution Research",
    "IET Generation Trans & Dist": "IET Generation, Transmission & Distribution",
    "Sci Data": "Scientific Data",
    "IEEE Pervasive Comput": "IEEE Pervasive Computing",
}
EPPO_LONG = re.compile(r"https://www\.eppo\.go\.th/information-services/advertise/news-eppo/%E0[^\s]*")
# External check 2026-10-23: the news listing page was not specific enough. The item URL is written in its
# decoded (IRI) form, 89 characters, which resolves to the same page (HTTP 200, checked 2026-10-23).
EPPO_SHORT = ("https://www.eppo.go.th/information-services/advertise/news-eppo/"
              "สนพ-เปิดรับฟัง"
              "ความคิดเ-4/ (accessed 16 October 2026).")
EPPO_LISTING = "https://www.eppo.go.th/information-services/advertise/news-eppo/ (accessed 16 October 2026)."
IEA_WEB = "https://www.iea.org/reports/southeast-asia-energy-outlook-2022. "

# CrossRef preserves publisher-supplied capitalisation, so otherwise identical
# Vancouver-style entries can mix sentence case and title case. These explicit
# replacements cover the DOI-backed article titles that require normalisation.
# They are deliberately not applied to reports, books, plans, laws or agency pages.
ARTICLE_TITLE_SENTENCE_CASE = {
    "Energy justice: A conceptual review":
        "Energy justice: a conceptual review",
    "Double energy vulnerability: Spatial intersections of domestic and transport energy poverty in England":
        "Double energy vulnerability: spatial intersections of domestic and transport energy poverty in England",
    "The geography of energy poverty in Canada: Spatial clustering and inequalities at the municipal level":
        "The geography of energy poverty in Canada: spatial clustering and inequalities at the municipal level",
    "The energy injustice of household solar energy: A systematic review of distributional disparities in residential rooftop solar adoption":
        "The energy injustice of household solar energy: a systematic review of distributional disparities in residential rooftop solar adoption",
    "Drivers and barriers to rural electrification in Tanzania and Mozambique – Grid-extension, off-grid, and renewable energy technologies":
        "Drivers and barriers to rural electrification in Tanzania and Mozambique – grid-extension, off-grid, and renewable energy technologies",
    "Mini-grid based off-grid electrification to enhance electricity access in developing countries: What policies may be required?":
        "Mini-grid based off-grid electrification to enhance electricity access in developing countries: what policies may be required?",
    "Energy access programmes and sustainable development: A critical review and analysis":
        "Energy access programmes and sustainable development: a critical review and analysis",
    "A GIS-based Multiple Criteria Decision Analysis approach for wind power plant site selection":
        "A GIS-based multiple criteria decision analysis approach for wind power plant site selection",
    "Multi-criteria decision making for solar power - Wind power plant site selection using a GIS-intuitionistic fuzzy-based approach with an application in the Netherlands":
        "Multi-criteria decision making for solar power - wind power plant site selection using a GIS-intuitionistic fuzzy-based approach with an application in the Netherlands",
    "Combining solar photovoltaic panels and food crops for optimising land use: Towards new agrivoltaic schemes":
        "Combining solar photovoltaic panels and food crops for optimising land use: towards new agrivoltaic schemes",
    "Dual use of agricultural land: Introducing ‘agrivoltaics’ in Phoenix Metropolitan Statistical Area, USA":
        "Dual use of agricultural land: introducing ‘agrivoltaics’ in Phoenix Metropolitan Statistical Area, USA",
    "Land Suitability Analysis for Solar Farms Exploitation Using GIS and Fuzzy Analytic Hierarchy Process (FAHP)—A Case Study of Iran":
        "Land suitability analysis for solar farms exploitation using GIS and fuzzy analytic hierarchy process (FAHP)—a case study of Iran",
    "Local Indicators of Spatial Association—LISA":
        "Local indicators of spatial association—LISA",
    "Maximization of Distribution Network Hosting Capacity through Optimal Grid Reconfiguration and Distributed Generation Capacity Allocation/Control":
        "Maximization of distribution network hosting capacity through optimal grid reconfiguration and distributed generation capacity allocation/control",
    "High-Resolution Global Maps of 21st-Century Forest Cover Change":
        "High-resolution global maps of 21st-century forest cover change",
    "OpenStreetMap: User-Generated Street Maps":
        "OpenStreetMap: user-generated street maps",
    "How accurate are WorldPop-Global-Unconstrained gridded population data at the cell-level?: A simulation analysis in urban Namibia":
        "How accurate are WorldPop-Global-Unconstrained gridded population data at the cell-level?: a simulation analysis in urban Namibia",
    "Nighttime Lights and County-Level Economic Activity in the United States: 2001 to 2019":
        "Nighttime lights and county-level economic activity in the United States: 2001 to 2019",
    "A Mathematical Theory of Communication":
        "A mathematical theory of communication",
}

# GHSL (external check 2026-10-23): name the layer used. Authors stay as registered for the DOI
# (DataCite lists Pesaresi M only, checked 2026-10-23).
GHSL_OLD = "Sentinel2 composite (2018). European Commission"
GHSL_NEW = "Sentinel2 composite (2018), average net building height (ANBH) layer. European Commission"

# Thai ภาคประชาชน means the general public (households), not the "public sector" (government), check 2026-10-24
PUBLIC = [("rooftop solar projects for the public sector, residential type",
           "rooftop solar projects for the general public, residential type"),
          ("under the public-sector rooftop solar programme",
           "under the rooftop solar programme for the general public")]

changed = 0
for i, s in enumerate(E):
    t = s
    for a, b in PUBLIC:
        t = t.replace(a, b)
    if GHSL_NEW not in t:
        t = t.replace(GHSL_OLD, GHSL_NEW)
    for a, full in FULL.items():
        t = t.replace(f". {a}. ", f". {full}. ")
    if "https://doi.org/" in t:
        for source_title, sentence_title in ARTICLE_TITLE_SENTENCE_CASE.items():
            t = t.replace(source_title, sentence_title)
    t = EPPO_LONG.sub(lambda m: EPPO_SHORT, t)
    t = t.replace(EPPO_LISTING, EPPO_SHORT)
    if "https://doi.org/" in t:
        t = t.replace(IEA_WEB, "")
    if t != s:
        E[i] = t
        changed += 1

# checks: no abbreviation left, every DOI written as https://doi.org/, no entry carries two links,
# no URL longer than 90 characters
for s in E:
    assert "public sector" not in s and "public-sector" not in s, s[:90]
    for a in FULL:
        assert f". {a}. " not in s, s[:80]
    assert "dx.doi.org" not in s and "doi:" not in s.lower(), s[:80]
    links = re.findall(r"https?://\S+", s)
    assert len(links) <= 1, s[:80]
    assert all(len(u) <= 90 for u in links), s[:80]
    if "https://doi.org/" in s:
        for source_title in ARTICLE_TITLE_SENTENCE_CASE:
            assert source_title not in s, s[:120]
for s, p in zip(E, R["provenance"]):
    if p["doi"]:
        assert s.endswith(f"https://doi.org/{p['doi']}"), s[:80]

F.write_text(json.dumps(R, indent=2, ensure_ascii=False), encoding="utf-8")
print(f"references normalised: {changed} entries changed, {len(E)} entries checked")
