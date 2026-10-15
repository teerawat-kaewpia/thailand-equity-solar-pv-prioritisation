# -*- coding: utf-8 -*-
"""
Export GridFinder predicted power grid data for Thailand from the GEE
community catalog (sat-io), since the original Zenodo source
(zenodo.org/records/3628142) is blocked by a network-level WAF for this
project (confirmed 403 on every record ID / API path tried).

Requires: earthengine authenticate (run once, opens a browser login).

Asset IDs (GEE community catalog, "sat-io"):
  lv      : projects/sat-io/open-datasets/predictive-global-power-system/lv
  targets : projects/sat-io/open-datasets/predictive-global-power-system/targets
  lines   : projects/sat-io/open-datasets/predictive-global-power-system/distribution-transmission-lines
"""
import ee

ee.Initialize()

THAILAND_BBOX = ee.Geometry.Rectangle([97.5, 5.5, 105.7, 20.5])
DRIVE_FOLDER = "DER_Thailand_GridFinder"

# --- lv.tif (predicted low-voltage infra, km per cell) ---
lv = ee.Image("projects/sat-io/open-datasets/predictive-global-power-system/lv").clip(THAILAND_BBOX)
ee.batch.Export.image.toDrive(
    image=lv,
    description="Thailand_gridfinder_lv",
    folder=DRIVE_FOLDER,
    region=THAILAND_BBOX,
    scale=90,
    crs="EPSG:4326",
    maxPixels=1e13,
).start()

# --- targets.tif (binary: predicted connected to grid) ---
targets = ee.Image("projects/sat-io/open-datasets/predictive-global-power-system/targets").clip(THAILAND_BBOX)
ee.batch.Export.image.toDrive(
    image=targets,
    description="Thailand_gridfinder_targets",
    folder=DRIVE_FOLDER,
    region=THAILAND_BBOX,
    scale=90,
    crs="EPSG:4326",
    maxPixels=1e13,
).start()

# --- distribution-transmission-lines (vector, MV/HV lines) ---
lines = ee.FeatureCollection(
    "projects/sat-io/open-datasets/predictive-global-power-system/distribution-transmission-lines"
).filterBounds(THAILAND_BBOX)
ee.batch.Export.table.toDrive(
    collection=lines,
    description="Thailand_gridfinder_lines",
    folder=DRIVE_FOLDER,
    fileFormat="GeoJSON",
).start()

print("3 export tasks started - check progress at code.earthengine.google.com (Tasks tab)")
print(f"Output will appear in Google Drive folder: {DRIVE_FOLDER}")
