
"""
Google Earth Engine Setup
Install: pip install earthengine-api
Auth:    earthengine authenticate
"""
import ee

# Thailand bounding box
THAILAND = ee.Geometry.Rectangle([97.5, 5.5, 105.7, 20.5])
SCALE_90M = 90        # 3 arc-second target
SCALE_30M = 30
CRS = 'EPSG:4326'
EXPORT_FOLDER = 'DER_Thailand_Research'

def export_image(image, name, scale=SCALE_90M, region=THAILAND):
    task = ee.batch.Export.image.toDrive(
        image=image.clip(region),
        description=name,
        folder=EXPORT_FOLDER,
        fileNamePrefix=name,
        scale=scale,
        crs=CRS,
        region=region,
        maxPixels=1e13,
        fileFormat='GeoTIFF'
    )
    task.start()
    print(f'✓ Export started: {name}')
    return task

print('GEE setup loaded. Run individual scripts below.')
print('All outputs → Google Drive / DER_Thailand_Research/')
