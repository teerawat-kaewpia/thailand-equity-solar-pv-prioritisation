# -*- coding: utf-8 -*-
"""
Build the manuscript reference list from verified sources.

After any rebuild, run normalize_references.py (full journal names, one link per entry,
short EPPO URL). Data/references.json is the live list read by the assemblers.

Two classes of entry:

  DOI entries — the DOI is stated here, and every other field (authors, title,
  journal, volume, issue, pages, year) is FETCHED FROM CROSSREF and formatted
  from that metadata. Nothing is typed from memory, so a reference cannot claim
  a DOI that belongs to a different paper.

  Report entries — institutional publications (UNFCCC, IEA, ministries, World
  Bank, NESDC, BMA) that are not DOI-registered. These carry a publisher and URL
  instead. A DOI is NEVER invented for them.

Output: Data/references.json  (ordered list of formatted strings + provenance)
"""
import json, time, urllib.request
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
from _paths import SRC, BASE, out_path
OUT = out_path("Data", "references.json")
MAILTO = __import__("os").environ.get("CROSSREF_MAILTO", "")   # CrossRef polite-pool contact, set locally, never stored in code

# ── DOI-backed entries, in intended citation order ────────────────────────────
# (DOI, expected title fragment). The fragment is not decoration: the build
# ABORTS if the title CrossRef returns for a DOI does not contain it. Three
# DOIs typed from memory in an earlier revision resolved to entirely unrelated
# papers (a thermoelectric-generator study, a China CO2 paper, a potato-peel
# study) and were caught only by reading the fetched titles. This guard makes
# that failure mode impossible to miss.
DOIS = [
    # framing: DER, energy justice, energy poverty
    ("10.1016/j.enpol.2003.10.004",  "Distributed generation"),
    ("10.1038/nenergy.2016.24",      "Energy decisions reframed"),
    ("10.1016/j.erss.2015.10.004",   "Energy justice"),
    ("10.1016/j.enpol.2017.03.018",  "concept of energy justice"),
    ("10.1016/j.erss.2020.101699",   "Double energy vulnerability"),
    ("10.1016/j.enpol.2024.114298",  "geography of energy poverty"),
    # solar equity / distributional outcomes
    ("10.1038/s41893-018-0204-z",    "Disparities in rooftop photovoltaics"),
    ("10.1038/s41560-020-00724-2",   "income equity in rooftop solar"),
    ("10.1088/1748-9326/ac4fdc",     "rooftop solar adoption inequity"),
    ("10.1016/j.erss.2024.103473",   "energy injustice of household solar"),
    # access / electrification in developing contexts
    ("10.1016/j.renene.2012.09.057", "rural electrification in Tanzania"),
    ("10.1016/j.enpol.2016.04.010",  "Mini-grid based off-grid electrification"),
    ("10.1016/j.esd.2012.05.002",    "Energy access programmes"),
    # MCDM / TOPSIS / entropy
    ("10.1016/j.eswa.2012.05.056",   "survey of TOPSIS applications"),
    ("10.1016/j.eswa.2020.114186",   "entropy weight on TOPSIS"),
    ("10.1016/j.renene.2020.04.137", "multi-criteria decision making applications"),
    ("10.1016/j.jup.2015.06.001",    "Multiple Criteria Decision Analysis"),
    ("10.1007/s11356-023-26540-1",   "Solar PV power plant site selection"),
    ("10.1016/j.esr.2024.101307",    "Multi-criteria decision making for solar"),
    # GIS suitability for solar
    ("10.1016/j.renene.2010.10.037", "PV site suitability analysis"),
    ("10.1016/j.renene.2011.03.005", "Combining solar photovoltaic panels and food crops"),
    ("10.1016/j.landurbplan.2017.10.011", "Dual use of agricultural land"),
    ("10.3390/en9080643",            "Land Suitability Analysis for Solar Farms"),
    ("10.1016/j.renene.2018.09.035", "Songkh"),
    # spatial statistics / scale
    ("10.1111/j.1538-4632.1995.tb00338.x", "Local Indicators of Spatial Association"),
    ("10.1016/j.spasta.2022.100689", "modifiable areal unit problem"),
    # grid / hosting capacity
    ("10.1049/gtd2.12062",           "hosting capacity"),
    ("10.3390/en13205315",           "Hosting Capacity"),
    # data infrastructure
    ("10.1038/s41597-019-0347-4",    "global power system"),
    ("10.1126/science.1244693",      "Forest Cover Change"),
    ("10.1109/mprv.2008.80",         "OpenStreetMap"),
    ("10.1371/journal.pone.0271504", "WorldPop"),
    ("10.3390/rs13142741",           "Nighttime Lights"),
    # Thailand
    ("10.1016/j.rser.2015.04.042",   "solar photovoltaic rooftops in Thailand"),
    # foundational
    ("10.1002/j.1538-7305.1948.tb01338.x", "Mathematical Theory of Communication"),
]

# ── Non-DOI institutional sources ─────────────────────────────────────────────
REPORTS = [
    ("UNFCCC. Paris Agreement to the United Nations Framework Convention on Climate "
     "Change. New York: United Nations; 2015. "
     "https://unfccc.int/process-and-meetings/the-paris-agreement"),
    ("International Energy Agency. Southeast Asia Energy Outlook 2022. Paris: IEA; 2022. "
     "https://www.iea.org/reports/southeast-asia-energy-outlook-2022"),
    ("Ministry of Energy, Thailand. Alternative Energy Development Plan 2018–2037 "
     "(AEDP 2018). Bangkok: Ministry of Energy; 2019."),
    ("Energy Policy and Planning Office (EPPO). Power Development Plan 2018–2037, "
     "Revision 1 (PDP2018 Rev.1). Bangkok: Ministry of Energy; 2020. Approved by the "
     "National Energy Policy Council on 19 March 2020 and by the Cabinet on 20 October "
     "2020; Thailand's adopted power development plan at the time of writing. "
     "https://www.eppo.go.th/images/allimage/PDP_image/PDP2018REv1.pdf"),
    ("Energy Policy and Planning Office (EPPO). EPPO opens public consultation on the draft "
     "Power Development Plan 2026 to 2050 (PDP2026). Bangkok: Ministry of Energy; 10 September "
     "2026. Consultation held 8 September 2026. The draft includes an indicative target of "
     "more than 9,100 MW of distributed energy resources by 2050. "
     "https://www.eppo.go.th/information-services/advertise/news-eppo/"
     "%E0%B8%AA%E0%B8%99%E0%B8%9E-%E0%B9%80%E0%B8%9B%E0%B8%B4%E0%B8%94%E0%B8%A3%E0%B8%B1%E0%B8%9A%E0%B8%9F%E0%B8%B1%E0%B8%87%E0%B8%84%E0%B8%A7%E0%B8%B2%E0%B8%A1%E0%B8%84%E0%B8%B4%E0%B8%94%E0%B9%80-4/"),
    ("Energy Policy and Planning Office (EPPO). Thailand Energy Statistics 2022. "
     "Bangkok: Ministry of Energy; 2022. https://www.eppo.go.th/index.php/en/"),
    ("Department of Alternative Energy Development and Efficiency (DEDE). Thailand "
     "Renewable Energy Statistics 2022. Bangkok: Ministry of Energy; 2023."),
    ("World Bank. Tracking SDG7: The Energy Progress Report 2023. Washington, DC: "
     "World Bank; 2023. https://trackingsdg7.esmap.org/"),
    # NOTE: the two author-constructed composite indices (provincial and Bangkok district)
    # are NOT external publications and are therefore NOT listed as numbered references.
    # Their construction is documented in supplementary Section S8 and their per-unit
    # scores are deposited with the analysis data.
    ("Saaty TL. The Analytic Hierarchy Process: Planning, Priority Setting, Resource "
     "Allocation. New York: McGraw-Hill; 1980."),
    ("Hwang CL, Yoon K. Multiple Attribute Decision Making: Methods and Applications. "
     "Berlin: Springer-Verlag; 1981."),
    ("Solargis. Global Solar Atlas v2: photovoltaic power output (PVOUT) long-term "
     "yearly average. Bratislava: Solargis / World Bank Group; 2020. "
     "https://globalsolaratlas.info/"),
    # Official ministerial statement is context only. It is not an ERC or utility
    # implementing instrument and is not used to alter the June 2026 programme terms.
    ("Ministry of Energy, Thailand. Ministerial address on draft PDP2026 and proposed "
     "expansion of residential rooftop solar procurement. Bangkok: Ministry of Energy; "
     "9 September 2026. "
     "https://www.energy.go.th/th/minister-news/30502"),
    # regulator that actually sets feed-in / net-metering / rooftop-solar purchase terms.
    # Specific Royal-Gazette-published instrument (not a homepage) for peer-review rigour.
    ("Energy Regulatory Commission (ERC), Thailand. Regulation of the Energy Regulatory "
     "Commission on Power Purchase from Solar PV Rooftop, B.E. 2556 (2013). Issued under "
     "the Energy Industry Act B.E. 2550 (2007); announced 30 August 2013 and published in "
     "the Government Gazette on 6 September 2013. Bangkok: ERC. "
     "http://www.ratchakitcha.soc.go.th/DATA/PDF/2556/E/111/1.PDF"),
]


def fetch(doi):
    url = f"https://api.crossref.org/works/{urllib.request.quote(doi)}"
    req = urllib.request.Request(url, headers={"User-Agent": f"DER-refs (mailto:{MAILTO})"})
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=40) as fh:
                return json.load(fh)["message"]
        except Exception as e:
            if attempt == 2:
                raise RuntimeError(f"{doi}: {e}")
            time.sleep(2 * (attempt + 1))


def authors(msg, limit=6):
    a = msg.get("author") or []
    if not a:
        return msg.get("publisher", "Anon")
    out = []
    for x in a[:limit]:
        fam = x.get("family", "").strip()
        given = x.get("given", "").strip()
        ini = "".join(p[0] for p in given.replace(".", " ").split() if p)
        out.append(f"{fam} {ini}".strip() if fam else x.get("name", "").strip())
    s = ", ".join(out)
    if len(a) > limit:
        s += ", et al"
    return s


def fmt(msg):
    title = (msg.get("title") or [""])[0].rstrip(". ")
    # CrossRef stores some titles with HTML entities
    title = title.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
    jrnl = (msg.get("container-title") or msg.get("short-container-title") or [""])   # full journal names (review 2026-10-18)
    jrnl = jrnl[0] if jrnl else ""
    year = (msg.get("issued", {}).get("date-parts") or [[None]])[0][0]
    vol = msg.get("volume", "")
    iss = msg.get("issue", "")
    page = msg.get("page", "").replace("-", "–")
    art = msg.get("article-number", "")
    loc = f"{vol}" + (f"({iss})" if iss else "")
    tail = f"{loc}:{page}" if page else (f"{loc}:{art}" if art else loc)
    doi = msg["DOI"].lower()
    # Titles ending in ? or ! keep their mark and take no extra full stop;
    # abbreviated journal names already ending in "." take no second one.
    t_sep = "" if title.endswith(("?", "!")) else "."
    jrnl = jrnl.rstrip(". ")
    parts = [f"{authors(msg)}. {title}{t_sep} {jrnl}. {year}"]
    if tail.strip(":"):
        parts.append(f";{tail}")
    return "".join(parts) + f". https://doi.org/{doi}"


entries, prov, mismatches = [], [], []
print(f"Fetching {len(DOIS)} DOI records from CrossRef...\n")
seen = set()
for i, (doi, expect) in enumerate(DOIS, 1):
    d = doi.lower()
    if d in seen:
        print(f"  ! duplicate skipped: {d}")
        continue
    seen.add(d)
    msg = fetch(d)
    got = (msg.get("title") or [""])[0]
    if expect.lower() not in got.lower():
        mismatches.append((d, expect, got))
        print(f"  [{i:>2}] *** DOI/TITLE MISMATCH ***")
        print(f"        doi      : {d}")
        print(f"        expected : ...{expect}...")
        print(f"        registry : {got}")
        continue
    s = fmt(msg)
    entries.append(s)
    prov.append({"doi": d, "verified": "crossref", "title": got})
    print(f"  [{i:>2}] {s[:110]}")
    time.sleep(0.35)

if mismatches:
    print(f"\nABORTED — {len(mismatches)} DOI(s) resolve to the wrong paper. "
          f"Fix the DOI, never the expectation.")
    raise SystemExit(1)

print(f"\nAdding {len(REPORTS)} non-DOI institutional/monograph sources "
      f"(no DOI registered; cited with publisher/URL)")
for r in REPORTS:
    entries.append(r)
    prov.append({"doi": None, "verified": "institutional-no-doi",
                 "title": r[:70]})

OUT.write_text(json.dumps({"entries": entries, "provenance": prov},
                          indent=2, ensure_ascii=False), encoding="utf-8")
n_doi = sum(1 for p in prov if p["doi"])
print(f"\nTotal references : {len(entries)}")
print(f"  with DOI       : {n_doi}")
print(f"  institutional  : {len(entries) - n_doi}")
print(f"Saved            : {OUT}")
