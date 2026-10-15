"""Float (table/figure) label registry for the TEJ manuscript and supplementary.

Source text refers to floats only through tokens: {T:label} for tables and
{F:label} for figures. A label is resolved by membership:
  MAIN_T / MAIN_F  -> its 1-based position (main-text numbering)
  SUPP             -> its fixed supplementary id (e.g. "S11a")
The declared order of MAIN_T / MAIN_F must equal the order in which captions
appear in the built manuscript. resolve_tokens() enforces this, together with
"every label defined once" and "every main float cited in the text".
"""
import re

# ── main text (order = numbering) ────────────────────────────────────────────
MAIN_T = ["criteria", "data", "weights", "zones", "grid", "allocation", "policy"]
MAIN_F = ["framework", "study-region", "criteria-maps", "pai-map", "zones", "deployment"]

# ── supplementary (fixed ids) ────────────────────────────────────────────────
SUPP_T = {"S-pearson": "S1", "S-spearman": "S2", "S-ranking": "S3", "S-rankshift": "S4",
          "S-spatialp": "S5", "S-maup": "S6", "S-lisa": "S7", "S-index-a": "S8a",
          "S-index-b": "S8b", "S-lv": "S9", "S-sources": "S10", "S-policy-full": "S11a",
          "S-policy-docs": "S11b", "S-district": "S12a",
          "bounds": "S13a", "transfer": "S13b", "desc": "S13c", "corr": "S13d",
          "top20": "S13e", "osmzones": "S13f", "construct": "S13g", "sens": "S13h", "erp": "S13i"}
SUPP_F = {"S-district": "S12", "corr": "S13a", "weights": "S13b", "lisa": "S13c",
          "ranking": "S13d", "sens": "S13e", "radar": "S13f"}

TOKEN = re.compile(r"\{([TF]):([A-Za-z0-9\-]+)\}")


def render(kind, label):
    main, supp = (MAIN_T, SUPP_T) if kind == "T" else (MAIN_F, SUPP_F)
    if label in main:
        assert label not in supp, f"{kind}:{label} declared both main and supplementary"
        return str(main.index(label) + 1)
    if label in supp:
        return supp[label]
    raise KeyError(f"undeclared float label {{{kind}:{label}}}")


def resolve_text(text):
    return TOKEN.sub(lambda m: render(m.group(1), m.group(2)), text)


CAPTION = re.compile(r"^(Table|Fig\.) \{([TF]):([A-Za-z0-9\-]+)\}\.")


def check_and_resolve(nodes_text, is_main):
    """nodes_text: list of (paragraph_text, is_caption). Returns problems (list of str)."""
    problems, defined, cited = [], [], set()
    for txt, is_cap in nodes_text:
        if is_cap:
            m = CAPTION.match(txt)
            if not m:
                problems.append(f"caption without a float token: {txt[:60]!r}")
                continue
            defined.append((m.group(2), m.group(3)))
            rest = txt[m.end():]
        else:
            rest = txt
        for k, lab in TOKEN.findall(rest):
            cited.add((k, lab))
    if is_main:
        for kind, decl in (("T", MAIN_T), ("F", MAIN_F)):
            got = [lab for k, lab in defined if k == kind]
            if got != decl:
                problems.append(f"{kind} caption order {got} != declared {decl}")
            for lab in decl:
                if (kind, lab) not in cited:
                    problems.append(f"main {kind}:{lab} is never cited in the text")
    dups = {x for x in defined if defined.count(x) > 1}
    if dups:
        problems.append(f"labels defined more than once: {sorted(dups)}")
    for k, lab in cited:
        try:
            render(k, lab)
        except KeyError as e:
            problems.append(str(e))
    return problems
