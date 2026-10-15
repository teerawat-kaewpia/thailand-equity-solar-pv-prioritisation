"""Lineage-checked loaders for TEJ-only variables.

The MV variable may be read ONLY through load_mv(), which accepts nothing but
the outputs of mv_distance.py and verifies them against its QA record.
"""
import json, hashlib
from pathlib import Path
from _paths import RAW, SRC, BASE
import pandas as pd

MV_DIR = BASE / "Data" / "mv_distance"
MV_SOURCE = RAW / "Energy map" / "GridFinder_Thailand" / "gridfinder_mv_lines_thailand.gpkg"
LEGACY = ("gridfinder_distance.json", "zone_grid_distance.json")


def sha256(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def load_mv():
    qa = json.loads((MV_DIR / "mv_distance_QA.json").read_text(encoding="utf-8"))
    assert Path(qa["source"]).resolve() == MV_SOURCE.resolve(), "MV source path changed"
    assert qa["source_sha256"] == sha256(MV_SOURCE), "MV source file changed since mv_distance.py ran"
    assert qa["crs"] == "EPSG:32647" and qa["res_m"] == 90.0, "MV grid spec differs from Amendment A3"
    tab = pd.read_csv(MV_DIR / "province_mv_distance.csv")
    assert len(tab) == 77 and tab.mv_dist_mean_km.notna().all()
    lineage = {"producer": "Scripts/mv_distance.py", "qa_file": "Data/mv_distance/mv_distance_QA.json",
               "qa_sha256": sha256(MV_DIR / "mv_distance_QA.json"),
               "source": MV_SOURCE.name, "source_sha256": qa["source_sha256"],
               "crs": qa["crs"], "res_m": qa["res_m"],
               "mask": "cell centre inside union of 77 GADM 4.1 level-1 polygons",
               "aggregation": "province mean of valid 90 m cells (median descriptive only)"}
    return tab, lineage
