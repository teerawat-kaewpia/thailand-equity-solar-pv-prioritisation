"""Write Figures/FIGURES_MANIFEST.csv and check that the documents embed exactly these files.

For every registered figure: document, printed label, file, producing script, sha256, whether the
DOCX embeds a byte-identical image, and the matching submission file for main-text figures.
Fails (exit 1) if a figure is missing, an embedded image does not match, or a stray image sits in Figures/.
"""
import csv
import hashlib
import sys
from pathlib import Path

import docx

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _figures import FIGS, ROOT, figin
from _floats import MAIN_F
from _paths import BASE

SCRIPT = {
    "framework": "figures/fig01_framework_tej.py", "study-region": "figures/fig02_study_area_tej.py",
    "criteria-maps": "figures/fig03_input_layers_tej.py", "pai-map": "figures/fig06_07_pai_zone_maps_tej.py",
    "zones": "figures/fig06_07_pai_zone_maps_tej.py", "deployment": "figures/fig10_deployment_scatter_tej.py",
    "S-district": "figures/fig12_bangkok_district_tej.py", "corr": "figures/fig_s13ab_corr_weights_tej.py",
    "weights": "figures/fig_s13ab_corr_weights_tej.py", "lisa": "figures/fig08_lisa_map_tej.py",
    "ranking": "figures/fig11_sensitivity_tej.py", "sens": "figures/fig11_sensitivity_tej.py",
    "radar": "figures/fig13_14_radar_policy_tej.py",
}
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()


def embedded(name):
    d = docx.Document(str(BASE / "Manuscript" / f"{name}.docx"))
    return {hashlib.sha256(r.target_part.blob).hexdigest() for r in d.part.rels.values() if "image" in r.reltype}


EMB = {"main": embedded("DER_TEJ_Manuscript"), "supplementary": embedded("DER_TEJ_Supplementary")}
rows, bad = [], []
for key, (folder, name, label) in FIGS.items():
    png = figin(key)
    h = sha(png)
    vec = ROOT / folder / f"{name}.pdf"
    tif = figin(key, "tif")
    from PIL import Image
    Image.MAX_IMAGE_PIXELS = None
    with Image.open(tif) as im:
        tdpi = round(min(im.info.get("dpi", (0, 0))))
        tsize = im.size
    if tdpi < 1000:
        bad.append(f"{label}: TIFF at {tdpi} dpi")
    stem = f"Figure_{MAIN_F.index(key) + 1}" if key in MAIN_F else f"Figure_{label.split()[-1]}"
    subs = sorted(p.name for p in (ROOT / "submission").glob(f"{stem}.*"))
    if f"{stem}.tif" not in subs:
        bad.append(f"no 1000 dpi submission TIFF for {label}")
    elif sha(ROOT / "submission" / f"{stem}.tif") != sha(tif):
        bad.append(f"{label}: submission TIFF differs from {tif.name}")
    ok = h in EMB[folder]
    if not ok:
        bad.append(f"{label}: {png.name} is not the image embedded in the {folder} document")
    rows.append({"document": "manuscript" if folder == "main" else "supplementary", "label": label, "key": key,
                 "file": f"{folder}/{png.name}", "tiff_1000dpi": f"{folder}/{tif.name}",
                 "tiff_pixels": f"{tsize[0]}x{tsize[1]}", "vector": f"{folder}/{vec.name}" if vec.exists() else "",
                 "submission_files": " ".join(f"submission/{s}" for s in subs), "script": f"Scripts/{SCRIPT[key]}",
                 "sha256": h, "embedded_in_docx": "yes" if ok else "NO"})
expected = {r["file"] for r in rows} | {r["tiff_1000dpi"] for r in rows} | {r["vector"] for r in rows if r["vector"]} | \
           {s for r in rows for s in r["submission_files"].split()}
for p in ROOT.rglob("*"):
    if p.is_file() and p.suffix.lower() in (".png", ".pdf", ".tif", ".tiff"):
        rel = p.relative_to(ROOT).as_posix()
        if rel not in expected and not rel.startswith("archive/"):
            bad.append(f"stray image outside the registry: {rel}")
out = ROOT / "FIGURES_MANIFEST.csv"
with open(out, "w", newline="", encoding="utf-8") as fh:
    w = csv.DictWriter(fh, fieldnames=list(rows[0]))
    w.writeheader()
    w.writerows(rows)
for r in rows:
    print(f"{r['label']:<10} {r['file']:<44} embedded={r['embedded_in_docx']:<3} tiff={r['tiff_pixels']:<12} {r['submission_files']}")
print("archive:", [p.name for p in (ROOT / "archive").glob("*")])
print("MANIFEST", "PASS" if not bad else "FAIL", *bad, sep="\n  ")
sys.exit(1 if bad else 0)
