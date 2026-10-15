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
    return tbl
