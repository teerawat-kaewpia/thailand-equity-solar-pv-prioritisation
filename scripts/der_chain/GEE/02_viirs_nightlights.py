
"""GEE: VIIRS Night-time Lights — annual composite 2018-2023"""
import ee; ee.Initialize()
from gee_setup import THAILAND, export_image, SCALE_90M

for year in [2018, 2019, 2020, 2021, 2022, 2023]:
    viirs = (ee.ImageCollection('NOAA/VIIRS/DNB/MONTHLY_V1/VCMCFG')
               .filterDate(f'{year}-01-01', f'{year}-12-31')
               .select('avg_rad')
               .median())

    viirs_90m = viirs.reduceResolution(
        reducer=ee.Reducer.mean(), maxPixels=1024
    ).reproject(crs='EPSG:4326', scale=SCALE_90M)

    export_image(viirs_90m, f'VIIRS_NTL_annual_{year}_90m_Thailand')

print('VIIRS export queued for 2018-2023 → GEE Tasks')
