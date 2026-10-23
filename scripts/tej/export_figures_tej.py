"""Export the figures as separate submission files (TEJ Guide for Authors, artwork).

Main text: Figure_N follows _floats.MAIN_F, so N matches the number printed in the manuscript.
Every main figure goes out as a 1000 dpi RGB LZW TIFF (the guide's level for bitmapped line art,
2026-10-15), rendered natively at 1000 dpi by the figure scripts. The two drawings, Figure 1
(framework) and Figure 6 (deployment chart), also go out as vector PDF.
Supplementary: Figure_S12, Figure_S13a..S13f as 1000 dpi TIFF, named by their printed labels.
"""
import shutil

from PIL import Image

from _figures import FIGS, TIFF_DPI, figin
from _floats import MAIN_F, SUPP_F
from _paths import out_path

Image.MAX_IMAGE_PIXELS = None
VECTOR = {"framework", "deployment"}
assert VECTOR <= set(MAIN_F)

out_dir = out_path("Figures", "submission", "_").parent
out_dir.mkdir(parents=True, exist_ok=True)
for old in out_dir.glob("Figure_*"):
    old.unlink()


def tiff(key, dst):
    src = figin(key, "tif")
    with Image.open(src) as im:
        dpi = im.info.get("dpi", (0, 0))
        assert min(round(d) for d in dpi) >= TIFF_DPI and im.mode == "RGB", (src, dpi, im.mode)
        size = im.size
    shutil.copyfile(src, dst)
    return f"{src.name} -> {dst.name} ({size[0]}x{size[1]} px, {round(dpi[0])} dpi)"


for n, key in enumerate(MAIN_F, start=1):
    print(f"Figure_{n} ({key}): {tiff(key, out_dir / f'Figure_{n}.tif')}")
    if key in VECTOR:
        shutil.copyfile(figin(key, "pdf"), out_dir / f"Figure_{n}.pdf")
        print(f"Figure_{n} ({key}): vector PDF")
for key, lab in SUPP_F.items():
    print(f"Figure_{lab} ({key}): {tiff(key, out_dir / f'Figure_{lab}.tif')}")
