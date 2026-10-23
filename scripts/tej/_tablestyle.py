"""Journal table style (TEJ guide: "Avoid vertical rules and shading within table cells").

Horizontal rules only: a top rule, a rule under the header row and a bottom rule.
No vertical rules, no inside horizontal rules, no cell shading.
"""
from docx.oxml import OxmlElement
from docx.oxml.ns import qn


def _border(tag, val="single", sz="8"):
    el = OxmlElement(f"w:{tag}")
    el.set(qn("w:val"), val)
    if val != "nil":
        el.set(qn("w:sz"), sz); el.set(qn("w:space"), "0"); el.set(qn("w:color"), "000000")
    return el


def fit_widths(df, col_widths, font_size, max_total=15.92):
    """Widen any column narrower than its longest unbreakable token (a number, a range such as 0.595–0.706,
    or a single word), taking the extra width from the columns with the most slack, so the table keeps its
    total width (review 2026-10-18: values and header words were split over two lines)."""
    import math
    import pandas as pd
    cw = 0.018 * font_size                            # cm per character, Times New Roman digits are 0.5 em
    pad = 0.40                                        # default left + right cell margins (0.19 cm each)
    need = []
    for j, col in enumerate(df.columns):
        toks = [t for t in str(col).replace('-', '- ').split()] or [""]
        hdr = max(len(t) for t in toks) * cw * 1.08   # bold header
        body = 0.0
        for v in df.iloc[:, j]:
            if v is None or (isinstance(v, float) and math.isnan(v)):
                continue
            s = str(v)
            if s.startswith("http") or "/" in s and len(s) > 25:   # URLs and paths may wrap at slashes
                continue
            # Word breaks lines at spaces and after hyphens, so a hyphenated term is several tokens
            body = max(body, max((len(t) for t in s.replace('-', '- ').split()), default=0) * cw)
        need.append(max(hdr, body) + pad)
    w = list(col_widths)
    short = [max(0.0, n - x) for n, x in zip(need, w)]
    extra = sum(short)
    if extra <= 0:
        return w
    slack = [max(0.0, x - n) for n, x in zip(need, w)]
    spare = max(0.0, max_total - sum(w))             # unused page width may be used first
    take = max(0.0, extra - spare)                   # what must come from other columns
    if sum(slack) < take:
        return w                                      # cannot fit inside the page width: leave as given
    out = []
    for x, s_, sl in zip(w, short, slack):
        out.append(round(x + s_ - (take * sl / sum(slack) if take else 0.0), 3))
    return out


def apply_rules(tbl):
    tblPr = tbl._tbl.tblPr
    for old in tblPr.findall(qn("w:tblBorders")):
        tblPr.remove(old)
    borders = OxmlElement("w:tblBorders")
    for tag in ("top", "bottom"):
        borders.append(_border(tag))
    for tag in ("left", "right", "insideH", "insideV"):
        borders.append(_border(tag, "nil"))
    tblPr.append(borders)
    for cell in tbl.rows[0].cells:                      # rule under the header row
        tcPr = cell._tc.get_or_add_tcPr()
        for old in tcPr.findall(qn("w:tcBorders")):
            tcPr.remove(old)
        cb = OxmlElement("w:tcBorders")
        cb.append(_border("bottom", sz="6"))
        tcPr.append(cb)
    for row in tbl.rows:                                # no shading anywhere
        for cell in row.cells:
            for shd in cell._tc.get_or_add_tcPr().findall(qn("w:shd")):
                shd.getparent().remove(shd)
    # review 2026-10-18: tables that run onto a new page repeat their header row, and no row is split
    # across a page break
    for i, row in enumerate(tbl.rows):
        trPr = row._tr.get_or_add_trPr()
        for tag in ("w:tblHeader", "w:cantSplit"):
            for old in trPr.findall(qn(tag)):
                trPr.remove(old)
        trPr.append(OxmlElement("w:cantSplit"))
        if i == 0:
            trPr.append(OxmlElement("w:tblHeader"))
    return tbl
