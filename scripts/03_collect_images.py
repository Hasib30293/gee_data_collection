"""
Step 3: Collect Satellite Images from GEE
Retrieve Sentinel-2 imagery based on specified parameters
"""

import sys
import ee
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config.settings import *
from scripts.gee_utils import (
    initialize_gee, create_aoi_from_bounds, mask_sentinel2_clouds,
    filter_collection_by_cloud_cover, filter_collection_by_date,
    filter_collection_by_bounds, get_collection_size, print_collection_info
)


def collect_sentinel2_images(aoi, start_date, end_date, cloud_threshold, max_images):
    """
    Collect Sentinel-2 images for specified area and date range
    
    Args:
        aoi (ee.Geometry): Area of interest
        start_date (str): Start date (YYYY-MM-DD)
        end_date (str): End date (YYYY-MM-DD)
        cloud_threshold (int): Maximum cloud cover percentage
        max_images (int): Maximum number of images to retrieve
    
    Returns:
        ee.ImageCollection: Filtered image collection
    """
    collection = ee.ImageCollection(SATELLITE_DATASET)
    
    # Apply filters
    collection = filter_collection_by_bounds(collection, aoi)
    collection = filter_collection_by_date(collection, start_date, end_date)
    collection = filter_collection_by_cloud_cover(collection, cloud_threshold)
    
    # Mask clouds
    collection = collection.map(mask_sentinel2_clouds)
    
    # Limit images
    collection = collection.limit(max_images)
    
    return collection


def main():
    """Main image collection function"""
    print("\n" + "="*60)
    print("STEP 3: Collect Satellite Images")
    print("="*60)
    
    # Initialize GEE
    print("\nInitializing Earth Engine...")
    if not initialize_gee():
        return False
    
    # Create Area of Interest
    print(f"\nCreating Area of Interest...")
    print(f"  Longitude: {AOI_BOUNDS['min_longitude']} to {AOI_BOUNDS['max_longitude']}")
    print(f"  Latitude: {AOI_BOUNDS['min_latitude']} to {AOI_BOUNDS['max_latitude']}")
    
    aoi = create_aoi_from_bounds(AOI_BOUNDS)
    
    # Collect images
    print(f"\nCollecting Sentinel-2 images...")
    print(f"  Date range: {START_DATE} to {END_DATE}")
    print(f"  Cloud cover threshold: {CLOUD_COVER_THRESHOLD}%")
    print(f"  Maximum images: {MAX_IMAGES}")
    
    collection = collect_sentinel2_images(
        aoi=aoi,
        start_date=START_DATE,
        end_date=END_DATE,
        cloud_threshold=CLOUD_COVER_THRESHOLD,
        max_images=MAX_IMAGES
    )
    
    # Get collection info
    size = get_collection_size(collection)
    print(f"\n✓ Collection retrieved: {size} images")
    
    if size == 0:
        print("✗ No images found. Try adjusting your parameters.")
        return False
    
    print_collection_info(collection, "Sentinel-2 Collection")
    
    # Display bands information
    first_image = ee.Image(collection.first())
    info = first_image.getInfo()
    
    print(f"Available bands in first image:")
    for i, band in enumerate(info['bands'][:5]):  # Show first 5 bands
        print(f"  {band['id']}")
    print(f"  ... and {len(info['bands']) - 5} more" if len(info['bands']) > 5 else "")
    
    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
