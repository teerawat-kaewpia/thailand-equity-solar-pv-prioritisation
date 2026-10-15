
"""GEE: Hansen Global Forest Change — forest cover at 90m"""
import ee; ee.Initialize()
from gee_setup import THAILAND, export_image, SCALE_90M

hansen = ee.Image('UMD/hansen/global_forest_change_2023_v1_11')

# Forest cover 2000 (baseline)
treecover2000 = hansen.select('treecover2000')

# Forest loss 2001-2023
lossyear = hansen.select('lossyear')
loss = hansen.select('loss')
gain = hansen.select('gain')

# 2023 forest cover estimate
forest_2023 = treecover2000.where(loss.eq(1), 0).where(gain.eq(1), 50)

for name, img in [('treecover2000', treecover2000),
                   ('loss_year', lossyear),
                   ('forest_2023', forest_2023),
                   ('gain', gain)]:
    img_90m = img.reduceResolution(
        reducer=ee.Reducer.mean(), maxPixels=1024
    ).reproject(crs='EPSG:4326', scale=SCALE_90M)
    export_image(img_90m, f'Hansen_{name}_90m_Thailand')

print('Hansen Forest export queued → GEE Tasks')
