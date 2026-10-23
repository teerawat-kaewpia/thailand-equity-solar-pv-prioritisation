"""A4 re-run: run the DER province chain inside the mirror, in order, with the roots pointed at the mirror.
Usage: python rerun_c2fix_chain.py <label>      (label = baseline | corrected; used for the log name)
Stops at the first failing step. The real DER folder is never on any path used here.
"""
import os
import subprocess
import sys
import time
from pathlib import Path

PY = r"C:\Users\user\AppData\Local\Microsoft\WindowsApps\python3.exe"
M = Path(r"D:\Clude Code GIS\Energy\DER_TEJ\Rerun_C2fix\Energy")
S = M / "DER" / "Scripts"
CHAIN = [
    "02_Preprocessing/rasterize_c2_poverty.py",
    "06_Priority_Areas/compute_pai_province_level.py",
    "06_Priority_Areas/spatial_autocorrelation.py",
    "06_Priority_Areas/reviewer_robustness_checks.py",
    "06_Priority_Areas/sensitivity_analysis.py",
    "06_Priority_Areas/bootstrap_weights.py",
    "06_Priority_Areas/validate_solar_osm.py",
    "06_Priority_Areas/sensitivity_validation_province.py",   # rewrites validation_solar_osm.csv (332 plants), as in DER
    "06_Priority_Areas/validate_zones_province.py",           # must read the 332-plant file (DER json 21:12 > csv 20:37)
    "06_Priority_Areas/spatial_permutation_test.py",
    "06_Priority_Areas/maup_analysis.py",
    "06_Priority_Areas/sensitivity_pai_mv.py",
    "06_Priority_Areas/validate_ser_external.py",
]
label = sys.argv[1]
only = sys.argv[2:] or None
env = dict(os.environ, ENERGY_DATA_ROOT=str(M), DER_PROJECT_ROOT=str(M / "DER"), PYTHONIOENCODING="utf-8",
           MPLBACKEND="Agg")
log = M.parent / f"run_{label}.log"
with open(log, "a", encoding="utf-8") as fh:
    for step in CHAIN:
        if only and not any(o in step for o in only):
            continue
        t0 = time.time()
        r = subprocess.run([PY, str(S / step)], cwd=str((S / step).parent), env=env,
                           capture_output=True, text=True, encoding="utf-8", errors="replace")
        fh.write(f"\n===== {step} | rc={r.returncode} | {time.time() - t0:.0f}s\n{r.stdout[-6000:]}\n{r.stderr[-4000:]}\n")
        fh.flush()
        print(f"{step}: rc={r.returncode} ({time.time() - t0:.0f}s)", flush=True)
        if r.returncode != 0:
            print(r.stderr[-2500:])
            sys.exit(1)
print("chain done, log:", log)
