"""Single registry of every figure used by the TEJ manuscript and supplementary (organised 2026-10-15).

All figure files live under DER_TEJ/Figures:
  main/            Fig1..Fig6, named by the number printed in the manuscript (order = _floats.MAIN_F)
  supplementary/   FigS12, FigS13a..FigS13f, named by the label printed in the supplementary (_floats.SUPP_F)
  submission/      journal upload files Figure_1..Figure_6 (export_figures_tej.py)
  archive/         figures no longer used by either document (kept for the record, never read)

Figure scripts write through figout(key), the assemblers and the exporter read through figin(key).
figin() never falls back to the DER mirror, so a stale DER-era image can no longer be picked up.
"""
from _floats import MAIN_F, SUPP_F
from _paths import BASE, out_path

ROOT = BASE / "Figures"
STEM = {
    "framework": "Framework", "study-region": "Study_Area", "criteria-maps": "Criteria_Maps",
    "pai-map": "PAI_Map", "zones": "Zone_Map", "deployment": "Deployment",
    "S-district": "Bangkok_District", "corr": "Correlation", "weights": "EWM_Weights", "lisa": "LISA_Map",
    "ranking": "Province_Ranking", "sens": "Sensitivity", "radar": "Radar",
}
FIGS = {}
for n, k in enumerate(MAIN_F, start=1):
    FIGS[k] = ("main", f"Fig{n}_{STEM[k]}", f"Fig. {n}")
for k, lab in SUPP_F.items():
    FIGS[k] = ("supplementary", f"Fig{lab}_{STEM[k]}", f"Fig. {lab}")
assert len(FIGS) == len(MAIN_F) + len(SUPP_F) == 13


def figout(key, ext="png"):
    folder, name, _ = FIGS[key]
    return out_path("Figures", folder, f"{name}.{ext}")


TIFF_DPI = 1000


def save_tiff(fig, key, **kw):
    """Render the figure again at 1000 dpi (TEJ: bitmapped line art >= 1000 dpi) and store it as RGB
    LZW TIFF next to the PNG. Rendered natively, not upsampled from the 600 dpi PNG."""
    import io
    from PIL import Image
    Image.MAX_IMAGE_PIXELS = None
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=TIFF_DPI, **kw)
    buf.seek(0)
    with Image.open(buf) as im:
        im.convert("RGB").save(figout(key, "tif"), format="TIFF", compression="tiff_lzw", dpi=(TIFF_DPI, TIFF_DPI))
    return figout(key, "tif")


def figin(key, ext="png"):
    folder, name, _ = FIGS[key]
    p = ROOT / folder / f"{name}.{ext}"
    if not p.exists():
        raise FileNotFoundError(f"figure {key!r} has not been built: {p}")
    return p
