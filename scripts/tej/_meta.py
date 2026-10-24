"""Single source for the article title and the data deposit (review items 2 and 8, 2026-10-16).

TITLE: the supplementary once carried the title of the withdrawn SCS version.
REPO_URL / RELEASE / DOI: the Data availability statement reads them from here. DOI stays None until the
Zenodo release exists; the statement then says the DOI-versioned archive will be cited at acceptance.
"""
TITLE = ("Equity-aware spatial prioritisation of distributed solar PV in Thailand: "
         "Policy scenarios for electricity distribution planning")
REPO_URL = "https://github.com/teerawat-kaewpia/thailand-equity-solar-pv-prioritisation"
RELEASE = "v1.0.2"   # v1.0.2 (2026-10-24): Fig. 1 redesign, Supplementary equation layout; v1.0.0 and v1.0.1 kept as tagged
DOI = None   # e.g. "10.5281/zenodo.1234567" once the Zenodo release is minted

# Authors in title-page order, and their CRediT roles (CRediT draft approved by the corresponding author,
# 2026-10-23). Read by the manuscript (CRediT section) and by build_submission_docs.py.
AUTHORS = ["Thanapon Saengsuwan", "Teerawat Kaewpia"]
CORRESPONDING = "Teerawat Kaewpia"
CREDIT = {
    "Thanapon Saengsuwan": ["Conceptualization", "Investigation", "Validation", "Resources",
                            "Writing – review & editing"],
    "Teerawat Kaewpia": ["Conceptualization", "Methodology", "Software", "Formal analysis", "Data curation",
                         "Visualization", "Writing – original draft", "Writing – review & editing",
                         "Project administration"],
}


def credit_statement():
    return " ".join(f"{a}: {', '.join(CREDIT[a])}." for a in AUTHORS)
