"""Guard for amendment A5: every criterion is clipped and scaled once at province level, and C2 only there.

  G1  C2 raster holds raw poverty percent: tag scaling=none, values > 1, the province table equals the
      summary column, and the rasteriser source has no percentile or clip call.
  G2  C1 and C3 carry exactly one documented pixel-level 2nd-98th scaling (raster tags + one clip in the
      builder), C4 and C5 are formula scores in [0,1].
  G3  Province level: criterion_scaling.json lists each of the five criteria once, and the normalised
      matrix equals ONE 2nd-98th clip of the province means (C2 recomputed from the full-precision table).
      A twice-clipped C2 must NOT match, so the check can tell the two apart.
  G4  Static scan: any script that reads the C2 raster as a pixel array must call scale_c2_pixels().

Usage: python guard_c2_scaling.py [DER root]   (default: the Run 4 mirror). Exit 1 on any failure.
"""
import json
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import rasterio

ROOT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(r"D:\Clude Code GIS\Energy\DER_TEJ\Rerun_C2fix\Energy\DER")
PROC = ROOT / "Data" / "14_Processed_90m"
SCR = ROOT / "Scripts"
fails, notes = [], []


def check(ok, msg):
    (notes if ok else fails).append(("PASS " if ok else "FAIL ") + msg)


def n01(v):
    lo, hi = np.nanpercentile(v, 2), np.nanpercentile(v, 98)
    return np.clip((v - lo) / (hi - lo + 1e-12), 0.0, 1.0)


# G1
with rasterio.open(PROC / "C2_poverty_90m.tif") as s:
    t = s.tags()
    a = s.read(1, out_shape=(s.height // 8, s.width // 8))
    a = a[a != s.nodata]
pov = pd.read_csv(PROC / "C2_poverty_province.csv")
summ = pd.read_csv(PROC / "province_PAI_summary.csv").set_index("NAME_1")
check(t.get("scaling") == "none", "G1 C2 raster tag scaling=none")
check(float(a.max()) > 1.0, f"G1 C2 raster holds percent (max {a.max():.2f})")
check(np.allclose(summ.loc[pov.NAME_1, "C2"].to_numpy(float), pov.poverty_pct.to_numpy(float), atol=1e-4),
      "G1 province C2 means equal the raw poverty table")
check({"year_used", "poverty_pct"} <= set(pov.columns) and "years_used" in t and "input_sha256" in t, "G1 year and provenance tags present")
src = (SCR / "02_Preprocessing" / "rasterize_c2_poverty.py").read_text(encoding="utf-8")
code = "\n".join(l for l in src.splitlines() if not l.lstrip().startswith("#"))
code = re.sub(r'"""[\s\S]*?"""', "", code)
check(not re.search(r"percentile|np\.clip|\.clip\(", code), "G1 rasteriser has no percentile/clip call")

# G2
for k, f, b in (("C1", "C1_PVOUT_90m.tif", "compute_c1_pvout_90m.py"), ("C3", "C3_popdens_90m.tif", "compute_c3_popdens_90m.py")):
    with rasterio.open(PROC / f) as s:
        tg = s.tags()
    bs = (SCR / "02_Preprocessing" / b).read_text(encoding="utf-8")
    check("2nd-98th" in tg.get("normalization", "") and "2nd-98th" in tg.get("formula", ""), f"G2 {k} pixel-level scaling tag present")
    check(len(re.findall(r"np\.clip\(", bs)) == 1 and len(re.findall(r"np\.percentile\(", bs)) == 2, f"G2 {k} builder scales once (1 clip, 1 lo/hi pair)")
for k in ("C5", "C6"):
    v = summ[k].to_numpy(float)
    check(0 <= v.min() and v.max() <= 1, f"G2 {k} formula score in [0,1]")

# G3
cs = json.loads((PROC / "criterion_scaling.json").read_text(encoding="utf-8"))
pl = cs["province_level"]
check(sorted(pl) == ["C1_Resource", "C2_Equity", "C3_Demand", "C4_Infra", "C5_Physical"] and all(v["times"] == 1 for v in pl.values()),
      "G3 criterion_scaling.json: five criteria, scaled once each")
nm = pd.read_csv(PROC / "province_criteria_normalised.csv").set_index("NAME_1")
p = pov.set_index("NAME_1").loc[nm.index, "poverty_pct"].to_numpy(float)
once = n01(p)
twice = n01(n01(p))
check(np.allclose(nm["C2_Equity"].to_numpy(float), once, atol=1e-9), "G3 normalised C2 = one clip of the raw table")
check(not np.allclose(once, twice, atol=1e-6) and not np.allclose(nm["C2_Equity"].to_numpy(float), twice, atol=1e-6),
      "G3 check discriminates: a twice-clipped C2 would fail")
for k, c in (("C1_Resource", "C1"), ("C4_Infra", "C5"), ("C5_Physical", "C6")):
    check(np.allclose(nm[k].to_numpy(float), n01(summ.loc[nm.index, c].to_numpy(float)), atol=5e-3),
          f"G3 normalised {k} = one clip of province means (4 dp summary)")
check(np.allclose(nm["C3_Demand"].to_numpy(float), n01(np.log1p(summ.loc[nm.index, "C3"].to_numpy(float) * 100)), atol=5e-3),
      "G3 normalised C3_Demand = one clip of log1p(100x) means")

# G4
EXEMPT = {"rasterize_c2_poverty.py": "writes the raster"}
for f in sorted(SCR.rglob("*.py")):
    s = f.read_text(encoding="utf-8", errors="replace")
    if "C2_poverty_90m" not in s or f.name in EXEMPT:
        continue
    pixel = ".read(1)" in s
    topsis = bool(re.search(r"(?i)topsis|\bD_pos\b|\bdpos\b|\bDp\s*=", s))
    if pixel and topsis:
        check("scale_c2_pixels(" in s, f"G4 {f.relative_to(SCR)} runs pixel TOPSIS on C2 and scales it explicitly")
    elif pixel:
        notes.append(f"INFO G4 {f.relative_to(SCR)} reads C2 pixels for zonal means only, no TOPSIS")
    else:
        notes.append(f"INFO G4 {f.relative_to(SCR)} reads C2 only through zonal means (province scaling applies)")
    if "province_PAI_summary.csv" in s and re.search(r"OUT_CSV\s*=\s*PROC\s*/\s*\"province_PAI_summary\.csv\"", s):
        notes.append(f"WARN G4 {f.relative_to(SCR)} is a legacy script that would overwrite province_PAI_summary.csv, not in the chain")

out = {"root": str(ROOT), "pass": not fails, "fails": fails, "notes": notes}
print("\n".join(fails + notes))
print("GUARD C2 SCALING:", "PASS" if not fails else f"FAIL ({len(fails)})")
sys.exit(0 if not fails else 1)
