
"""GEE: Copernicus DEM GLO-30 — terrain at 90m"""
import ee; ee.Initialize()
import importlib.util as _ilu, pathlib as _pl  # the setup module is 00_gee_setup.py, which cannot be imported by name
_spec = _ilu.spec_from_file_location("gee_setup", _pl.Path(__file__).with_name("00_gee_setup.py"))
gee_setup = _ilu.module_from_spec(_spec); _spec.loader.exec_module(gee_setup)
THAILAND, export_image, SCALE_90M = gee_setup.THAILAND, gee_setup.export_image, gee_setup.SCALE_90M

dem = ee.ImageCollection('COPERNICUS/DEM/GLO30').select('DEM').mosaic()

# Elevation
dem_90m = dem.reduceResolution(
    reducer=ee.Reducer.mean(), maxPixels=1024
).reproject(crs='EPSG:4326', scale=SCALE_90M)
export_image(dem_90m, 'CopernicusDEM_GLO30_elevation_90m_Thailand')

# Slope and Aspect (for solar correction)
terrain = ee.Terrain.products(dem)
slope  = terrain.select('slope')
aspect = terrain.select('aspect')

for name, img in [('slope', slope), ('aspect', aspect)]:
    img_90m = img.reduceResolution(
        reducer=ee.Reducer.mean(), maxPixels=1024
    ).reproject(crs='EPSG:4326', scale=SCALE_90M)
    export_image(img_90m, f'CopernicusDEM_{name}_90m_Thailand')

print('Copernicus DEM export queued (elevation + slope + aspect) → GEE Tasks')
