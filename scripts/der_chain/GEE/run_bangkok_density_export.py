# -*- coding: utf-8 -*-
"""
Google Open Buildings v3 -> footprint DENSITY (coverage fraction), Bangkok.
Python / command-line twin of run_bangkok_density_export.js.

Third and finest of the Bangkok building layers:
  presence (run_bangkok_buildings_export.py) : v3 paint @30 m, binary 0/1
  density  (THIS script)                     : v3 paint @5 m -> mean @30 m,
                                               = fraction of each 30 m cell
                                                 actually covered by building
                                                 footprint (continuous 0-1)
  fraction/height (run_bangkok_2p5d_export.py): the 2.5D Temporal bands

"Density" is the truest C5 rooftop-availability proxy: not just "is there a
building in this cell" (presence) but "how much of the cell is roof".

Why this no longer hits "Reprojection output too large (15030x15368)":
paint() is rasterised at 5 m ONLY where the 30 m output is requested.
setDefaultProjection(.., 5) declares the input granularity, then
reduceResolution averages the 5 m footprint cells into each 30 m output cell
-- GEE tiles that work by the 30 m output (256x256), so only ~3.8M px of 30 m
result is ever materialised. No full-bbox 5 m render, no tiling.
(36 5 m sub-cells per 30 m cell << maxPixels; bestEffort is a safety net.)

Output (Drive -> DER_Bangkok_Buildings/):
  GoogleOB_v3_density_30m_Bangkok.tif   (footprint coverage fraction, 0-1)

Usage:
  1) earthengine authenticate      (one-time)
  2) python run_bangkok_density_export.py
  3) Download from Drive -> DER_Bangkok_Buildings/ into:
     D:\\Clude Code GIS\\Energy\\DER\\Data\\07_Buildings\\Bangkok\\
"""

import time
import ee

# ---- config ----
PROJECT    = 'ee-teerawat'
BANGKOK    = ee.Geometry.Rectangle([100.3200, 13.4925, 100.9391, 13.9543])
CRS        = 'EPSG:4326'
SCALE_30M  = 30
FINE_SCALE = 5      # granularity at which footprints are rasterised
MAX_PIXELS = 5e8
FOLDER     = 'DER_Bangkok_Buildings'


def submit_tasks():
    ee.Initialize(project=PROJECT)
    print(f'GEE initialized (project={PROJECT})')

    obV3 = (ee.FeatureCollection('GOOGLE/Research/open-buildings/v3/polygons')
            .filterBounds(BANGKOK))

    # paint footprints, DECLARE 5 m granularity, then areal-mean to 30 m.
    # setDefaultProjection is what lets reduceResolution aggregate 5 m -> 30 m
    # per output tile instead of rendering the whole 5 m grid at once.
    density_30m = (ee.Image().byte().paint(obV3, 1).unmask(0)
                   .setDefaultProjection(CRS, None, FINE_SCALE)
                   .reduceResolution(reducer=ee.Reducer.mean(),
                                    maxPixels=1024, bestEffort=True)
                   .reproject(crs=CRS, scale=SCALE_30M)
                   .rename('building_density')
                   .clip(BANGKOK))

    name = f'GoogleOB_v3_density_{SCALE_30M}m_Bangkok'
    task = ee.batch.Export.image.toDrive(
        image=density_30m,
        description=name,
        folder=FOLDER,
        fileNamePrefix=name,
        scale=SCALE_30M,
        crs=CRS,
        region=BANGKOK,
        maxPixels=int(MAX_PIXELS),
        fileFormat='GeoTIFF',
    )
    task.start()
    print(f'  Queued: {name}')
    return [(name, task)]


def wait_for_tasks(tasks, poll_seconds=30):
    print(f'\nWaiting for {len(tasks)} export task(s) to complete...')
    pending = list(tasks)
    while pending:
        still_pending = []
        for name, task in pending:
            status = task.status()
            state  = status['state']
            if state == 'COMPLETED':
                print(f'  DONE:    {name}')
            elif state == 'FAILED':
                print(f'  FAILED:  {name}  error={status.get("error_message","?")}')
            elif state in ('CANCEL_REQUESTED', 'CANCELLED'):
                print(f'  CANCELLED: {name}')
            else:
                still_pending.append((name, task))
        pending = still_pending
        if pending:
            names = ', '.join(n for n, _ in pending)
            print(f'  [{time.strftime("%H:%M:%S")}] Still running: {names}')
            time.sleep(poll_seconds)

    print('\nAll tasks finished.')
    print(f'Download from Google Drive -> {FOLDER}/')
    print('Place in: D:\\Clude Code GIS\\Energy\\DER\\Data\\07_Buildings\\Bangkok\\')


if __name__ == '__main__':
    tasks = submit_tasks()
    wait_for_tasks(tasks)
