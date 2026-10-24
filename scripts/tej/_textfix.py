"""Build-time text fixes shared by both assemblers (audit 2026-10-09).

inline_math(doc, keys)  replaces markers ⟪key⟫ in any paragraph (body, captions, table cells)
                        with an inline Word equation (OMML via MML2OMML), so symbols such as
                        v_ij print as mathematics and not as typed text with braces (F-1/F-2/F-9).
typography(doc)         hyphen-minus before a number → U+2212 minus (m1); an en dash between two
                        words → hyphen, since the house rule keeps the en dash for ranges (m2).
                        Reference entries ("[n] …") and equation objects are left untouched.
"""
import re
from copy import deepcopy

from lxml import etree

from _equations import _MML2OMML, _MML_NS, _wrap_fences

W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
M = "http://schemas.openxmlformats.org/officeDocument/2006/math"


# ── tiny MathML builders ─────────────────────────────────────────────────────
def mi(x):
    return f"<mi>{x}</mi>"


def mo(x):
    return f"<mo>{x}</mo>"


def mn(x):
    return f"<mn>{x}</mn>"


def mt(x):
    return f"<mtext>{x}</mtext>"


def sub(a, b):
    return f"<msub>{a}{b}</msub>"


def sup(a, b):
    return f"<msup>{a}{b}</msup>"


def subsup(a, b, c):
    return f"<msubsup>{a}{b}{c}</msubsup>"


def row(*xs):
    return "<mrow>" + "".join(xs) + "</mrow>"


def frac(a, b):
    return f"<mfrac>{a}{b}</mfrac>"


def ij():
    return row(mi("i"), mi("j"))


def sigma(idx):
    return f'<munder><mo largeop="true">&#x2211;</mo>{mi(idx)}</munder>'


PLUS, MINUS = mo("+"), mo("&#x2212;")
INLINE = {
    # main text
    "pai-def": row(mi("PAI"), mo("="), frac(sup(mi("d"), MINUS), row(sup(mi("d"), PLUS), mo("+"), sup(mi("d"), MINUS)))),
    "d-plus": sup(mi("d"), PLUS),
    "d-minus": sup(mi("d"), MINUS),
    "c4-dist": row(mi("d"), mo("="), MINUS, mn("5"), mo("&#x22C5;"), mi("ln"), mo("&#x2061;"), mt("C4")),
    # supplementary S13.1
    "V-def": row(mi("V"), mo("="), mo("["), sub(mi("v"), ij()), mo("]")),
    "v-def": row(sub(mi("v"), ij()), mo("="), sub(mi("w"), mi("j")), mo("&#x22C5;"), sub(mi("r"), ij())),
    "r-plus": row(subsup(mi("r"), mi("j"), PLUS), mo("="), mn("1")),
    "r-minus": row(subsup(mi("r"), mi("j"), MINUS), mo("="), mn("0")),
    "v-plus": row(subsup(mi("v"), mi("j"), PLUS), mo("="), sub(mi("w"), mi("j"))),
    "v-minus": row(subsup(mi("v"), mi("j"), MINUS), mo("="), mn("0")),
    "w-j": sub(mi("w"), mi("j")),
    "z-def": row(sub(mi("z"), mi("i")), mo("="), sub(mi("PAI"), mi("i")), MINUS,
                 '<mover><mi>PAI</mi><mo>&#x00AF;</mo></mover>'),
    "w-ij": sub(mi("w"), ij()),
    "S0-def": row(sub(mi("S"), mn("0")), mo("="), sigma("i"), sigma("j"), sub(mi("w"), ij())),
    # review 2026-10-24: the entropy convention moved out of display Eq. (S13.3) into the text
    "plnp-zero": row(sub(mi("p"), ij()), mi("ln"), mo("&#x2061;"), sub(mi("p"), ij()), mo("="), mn("0")),
    "pij-zero": row(sub(mi("p"), ij()), mo("="), mn("0")),
    "S0": sub(mi("S"), mn("0")),
    "n": mi("n"),
}


def _omml(key):
    x = etree.fromstring(f'<math xmlns="{_MML_NS}">{INLINE[key]}</math>'.encode("utf-8"))
    _wrap_fences(x)
    root = _MML2OMML(x).getroot()
    # MML2OMML may wrap in oMathPara. An inline equation must be a bare m:oMath.
    return root.find(f"{{{M}}}oMath") if root.tag == f"{{{M}}}oMathPara" else root


MARK = re.compile(r"⟪([A-Za-z0-9\-]+)⟫")


def inline_math(doc):
    body = doc.element.body
    n = 0
    for r in list(body.iter(f"{{{W}}}r")):
        t = r.find(f"{{{W}}}t")
        if t is None or not t.text or "⟪" not in t.text:
            continue
        cur = r
        while True:
            t = cur.find(f"{{{W}}}t")
            m = MARK.search(t.text or "")
            if not m:
                break
            before, after = t.text[:m.start()], t.text[m.end():]
            t.text = before
            t.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
            om = _omml(m[1])
            cur.addnext(om)
            nxt = deepcopy(cur)
            nxt.find(f"{{{W}}}t").text = after
            om.addnext(nxt)
            cur = nxt
            n += 1
    left = [t.text for t in body.iter(f"{{{W}}}t") if t.text and "⟪" in t.text]
    assert not left, f"unresolved inline-math markers: {left[:3]}"
    return n


_REF = re.compile(r"^\[\d+\] ")
_MINUS = re.compile(r"(?:(?<=[=(\s,])|^)-(?=\d)")
_WORD_EN = re.compile(r"(?<=[a-z]{3})–(?=[a-z]{3})")


def typography(doc):
    counts = {"minus": 0, "en_dash": 0}
    for p in doc.element.body.iter(f"{{{W}}}p"):
        text = "".join(t.text or "" for t in p.iter(f"{{{W}}}t"))
        if _REF.match(text):
            continue
        for t in p.iter(f"{{{W}}}t"):
            if not t.text:
                continue
            new, k1 = _MINUS.subn("−", t.text)
            new, k2 = _WORD_EN.subn("-", new)
            if k1 or k2:
                t.text = new
                counts["minus"] += k1
                counts["en_dash"] += k2
    return counts
