"""Shared paths for the Electricity Journal (TEJ) manuscript workspace.

SRC  = the original DER project. READ-ONLY: master results, processed data,
       figures and tables are reused from there, never written.
BASE = this workspace (DER_TEJ). Every output goes here.
"""
from pathlib import Path
import os

# A4 (2026-10-09): the shared DER data carry a C2 input error (GADM Thai-name join). The corrected
# re-run lives in a mirror inside this workspace, and SRC points there. DER itself is never modified.
SRC = Path(os.environ.get("DER_SOURCE_ROOT", r"D:\Clude Code GIS\Energy\DER_TEJ\Rerun_C2fix\Energy\DER")).resolve()
DER_ORIGINAL = Path(r"D:\Clude Code GIS\Energy\DER").resolve()   # read-only reference for old-vs-new comparisons
BASE = Path(__file__).resolve().parents[1]
RAW = Path(os.environ.get("ENERGY_RAW_ROOT", str(Path(r"D:\Clude Code GIS\Energy")))).resolve()   # raw inputs (Energy map), read-only


def out_path(*parts):
    """Return an output path inside BASE. Refuses anything that resolves into SRC."""
    p = BASE.joinpath(*parts).resolve()
    if SRC in p.parents or p == SRC:
        raise RuntimeError(f"Refusing to write into the source project: {p}")
    if BASE not in p.parents:
        raise RuntimeError(f"Output must stay inside {BASE}: {p}")
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def fig(name):
    """Retired 2026-10-15: figures are read through _figures.figin(), never from the DER mirror."""
    raise RuntimeError(f"_paths.fig({name!r}) is retired, use _figures.figin(key)")


def data(*parts):
    """TEJ-specific data file if present in DER_TEJ/Data, else the shared DER file."""
    own = BASE.joinpath("Data", *parts)
    return own if own.exists() else SRC.joinpath("Data", *parts)
