"""
Google Earth Engine Utility Functions
Helper functions for authentication, initialization, and data processing
"""

import ee
import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config.settings import *


def is_authenticated():
    """Check if user is already authenticated with GEE"""
    try:
        ee.ee_exception.EEException
        ee.Image('USGS/SRTMGL1_003')
        return True
    except Exception:
        return False


def authenticate_user(force=False):
    """
    Authenticate with Google Earth Engine
    
    Args:
        force (bool): Force re-authentication
    
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        if force:
            ee.Authenticate(force=True)
        else:
            ee.Authenticate()
        print("✓ Google Earth Engine authentication successful!")
        return True
    except Exception as e:
        print(f"✗ Authentication failed: {e}")
        print("Please ensure you have a valid Google account and GEE access.")
        return False


def initialize_gee(project_id=None):
    """
    Initialize Google Earth Engine
    
    Args:
        project_id (str): GEE project ID. Uses GEE_PROJECT_ID from config if None
    
    Returns:
        bool: True if successful, False otherwise
    """
    if project_id is None:
        project_id = GEE_PROJECT_ID
    
    try:
        ee.Initialize(project=project_id)
        print(f"✓ Earth Engine initialized with project: {project_id}")
        
        # Test the connection
        test_image = ee.Image('USGS/SRTMGL1_003')
        info = test_image.getInfo()
        print(f"✓ Test image loaded: {info['type']}")
        
        return True
    except Exception as e:
        print(f"✗ Initialization failed: {e}")
        print(f"Ensure project ID '{project_id}' is correct and you have access.")
        return False


def create_aoi_from_bounds(bounds):
    """
    Create Area of Interest geometry from bounds
    
    Args:
        bounds (dict): Dictionary with min_longitude, min_latitude, max_longitude, max_latitude
    
    Returns:
        ee.Geometry: Rectangle geometry
    """
    return ee.Geometry.Rectangle([
        bounds['min_longitude'],
        bounds['min_latitude'],
        bounds['max_longitude'],
        bounds['max_latitude']
    ])


def create_aoi_from_coordinates(coords):
    """
    Create Area of Interest from list of coordinates
    
    Args:
        coords (list): [minLon, minLat, maxLon, maxLat]
    
    Returns:
        ee.Geometry: Rectangle geometry
    """
    return ee.Geometry.Rectangle(coords)


def mask_sentinel2_clouds(image):
    """
    Mask clouds and shadows in Sentinel-2 imagery
    
    Args:
        image (ee.Image): Sentinel-2 image
    
    Returns:
        ee.Image: Masked image with normalized reflectance
    """
    qa = image.select('QA60')
    cloudBitMask = (1 << 10) | (1 << 11)
    mask = qa.bitwiseAnd(cloudBitMask).eq(0)
    return image.updateMask(mask).divide(10000)


def mask_landsat_clouds(image):
    """
    Mask clouds and shadows in Landsat imagery
    
    Args:
        image (ee.Image): Landsat image
    
    Returns:
        ee.Image: Masked image
    """
    qa = image.select('QA_PIXEL')
    # Bits 3 and 4 are cloud and cloud shadow respectively
    cloudBitMask = (1 << 3) | (1 << 4)
    mask = qa.bitwiseAnd(cloudBitMask).eq(0)
    return image.updateMask(mask).divide(10000)


def calculate_ndvi(image):
    """
    Calculate Normalized Difference Vegetation Index (NDVI)
    
    Args:
        image (ee.Image): Sentinel-2 image with NIR (B8) and RED (B4)
    
    Returns:
        ee.Image: NDVI band
    """
    nir = image.select('B8')
    red = image.select('B4')
    ndvi = nir.subtract(red).divide(nir.add(red)).rename('NDVI')
    return ndvi


def calculate_ndbi(image):
    """
    Calculate Normalized Difference Built-up Index (NDBI)
    
    Args:
        image (ee.Image): Sentinel-2 image with SWIR (B11) and NIR (B8)
    
    Returns:
        ee.Image: NDBI band
    """
    swir = image.select('B11')
    nir = image.select('B8')
    ndbi = swir.subtract(nir).divide(swir.add(nir)).rename('NDBI')
    return ndbi


def calculate_ndwi(image):
    """
    Calculate Normalized Difference Water Index (NDWI)
    
    Args:
        image (ee.Image): Sentinel-2 image with NIR (B8) and GREEN (B3)
    
    Returns:
        ee.Image: NDWI band
    """
    nir = image.select('B8')
    green = image.select('B3')
    ndwi = nir.subtract(green).divide(nir.add(green)).rename('NDWI')
    return ndwi


def get_collection_size(collection):
    """
    Get the size of an image collection
    
    Args:
        collection (ee.ImageCollection): Image collection
    
    Returns:
        int: Number of images in collection
    """
    return collection.size().getInfo()


def print_collection_info(collection, name="Collection"):
    """
    Print information about an image collection
    
    Args:
        collection (ee.ImageCollection): Image collection
        name (str): Name of collection for display
    """
    size = get_collection_size(collection)
    first_image = ee.Image(collection.first())
    info = first_image.getInfo()
    
    print(f"\n{'='*50}")
    print(f"{name} Information")
    print(f"{'='*50}")
    print(f"Total images: {size}")
    print(f"First image date: {info['properties'].get('system:time_start', 'N/A')}")
    print(f"Bands: {len(info['bands'])}")
    print(f"{'='*50}\n")


def filter_collection_by_cloud_cover(collection, threshold=CLOUD_COVER_THRESHOLD):
    """
    Filter collection by cloud cover percentage
    
    Args:
        collection (ee.ImageCollection): Image collection
        threshold (int): Maximum cloud cover percentage
    
    Returns:
        ee.ImageCollection: Filtered collection
    """
    return collection.filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', threshold))


def filter_collection_by_date(collection, start_date, end_date):
    """
    Filter collection by date range
    
    Args:
        collection (ee.ImageCollection): Image collection
        start_date (str): Start date (YYYY-MM-DD)
        end_date (str): End date (YYYY-MM-DD)
    
    Returns:
        ee.ImageCollection: Filtered collection
    """
    return collection.filterDate(start_date, end_date)


def filter_collection_by_bounds(collection, aoi):
    """
    Filter collection by area of interest
    
    Args:
        collection (ee.ImageCollection): Image collection
        aoi (ee.Geometry): Area of interest
    
    Returns:
        ee.ImageCollection: Filtered collection
    """
    return collection.filterBounds(aoi)


def create_export_task(image, description, folder, aoi, scale=EXPORT_SCALE, 
                       crs=EXPORT_CRS, file_format=EXPORT_FORMAT):
    """
    Create an export task for Google Drive
    
    Args:
        image (ee.Image): Image to export
        description (str): Export task description
        folder (str): Google Drive folder name
        aoi (ee.Geometry): Area of interest for export region
        scale (int): Resolution in meters
        crs (str): Coordinate reference system
        file_format (str): Output format (GeoTIFF, TFRecord, etc.)
    
    Returns:
        ee.batch.Task: Export task
    """
    task = ee.batch.Export.image.toDrive(
        image=image,
        description=description,
        folder=folder,
        region=aoi,
        scale=scale,
        crs=crs,
        maxPixels=int(MAX_PIXELS),
        fileFormat=file_format
    )
    return task


def start_export_task(task):
    """
    Start an export task
    
    Args:
        task (ee.batch.Task): Export task
    
    Returns:
        str: Task ID
    """
    task.start()
    task_id = task.id
    print(f"✓ Export task started: {task_id}")
    print("  Check Google Drive or GEE Code Editor Tasks tab for progress")
    return task_id


def check_task_status(task):
    """
    Check the status of an export task
    
    Args:
        task (ee.batch.Task): Export task
    
    Returns:
        dict: Task status information
    """
    return task.status()


def download_image_local(image, aoi, filename, output_folder, scale=EXPORT_SCALE, 
                        crs=EXPORT_CRS, max_pixels=int(MAX_PIXELS)):
    """
    Download image locally from Google Earth Engine
    
    Args:
        image (ee.Image): Image to download
        aoi (ee.Geometry): Area of interest
        filename (str): Output filename (without extension)
        output_folder (str): Local folder to save file
        scale (int): Resolution in meters
        crs (str): Coordinate reference system
        max_pixels (int): Maximum number of pixels
    
    Returns:
        str: Full path to downloaded file
    """
    import urllib.request
    import json
    
    # Create output folder if not exists
    Path(output_folder).mkdir(parents=True, exist_ok=True)
    
    # Prepare download URL
    download_url = image.getDownloadUrl({
        'scale': scale,
        'crs': crs,
        'region': aoi,
        'format': 'GeoTIFF',
        'maxPixels': max_pixels
    })
    
    # Download file
    output_path = Path(output_folder) / f"{filename}.tif"
    print(f"  Downloading to: {output_path}")
    
    try:
        urllib.request.urlretrieve(download_url, str(output_path))
        print(f"  ✓ Downloaded: {filename}.tif ({output_path.stat().st_size / 1024 / 1024:.2f} MB)")
        return str(output_path)
    except Exception as e:
        print(f"  ✗ Download failed: {e}")
        return None


def download_image_collection_local(collection, aoi, prefix, output_folder, 
                                   scale=EXPORT_SCALE, crs=EXPORT_CRS, 
                                   max_pixels=int(MAX_PIXELS), limit=50):
    """
    Download multiple images from collection locally
    
    Args:
        collection (ee.ImageCollection): Image collection
        aoi (ee.Geometry): Area of interest
        prefix (str): Prefix for filenames
        output_folder (str): Local folder to save files
        scale (int): Resolution in meters
        crs (str): Coordinate reference system
        max_pixels (int): Maximum pixels per image
        limit (int): Maximum number of images to download
    
    Returns:
        list: Paths to downloaded files
    """
    # Limit collection size
    limited_collection = collection.limit(limit)
    size = limited_collection.size().getInfo()
    
    print(f"\n  Downloading {size} images...")
    downloaded_files = []
    
    # Get list of images
    image_list = limited_collection.toList(size)
    
    for i in range(size):
        try:
            image = ee.Image(image_list.get(i))
            timestamp = image.getNumber('system:time_start').getInfo()
            from datetime import datetime
            date_str = datetime.fromtimestamp(timestamp/1000).strftime('%Y%m%d_%H%M%S')
            
            filename = f"{prefix}_{i:02d}_{date_str}"
            output_path = download_image_local(image, aoi, filename, output_folder, 
                                             scale, crs, max_pixels)
            if output_path:
                downloaded_files.append(output_path)
                
        except Exception as e:
            print(f"  ✗ Error downloading image {i}: {e}")
            continue
    
    return downloaded_files
