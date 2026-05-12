"""
Step 4: Process Satellite Images
Apply filters, calculate indices, and prepare for visualization/export
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
    filter_collection_by_bounds, calculate_ndvi, calculate_ndbi,
    calculate_ndwi, get_collection_size
)


def process_collection(collection, aoi, indices=None):
    """
    Process satellite image collection
    
    Args:
        collection (ee.ImageCollection): Image collection to process
        aoi (ee.Geometry): Area of interest for clipping
        indices (list): Indices to calculate ['ndvi', 'ndbi', 'ndwi']
    
    Returns:
        tuple: (median_image, index_images)
    """
    if indices is None:
        indices = ['ndvi']
    
    # Create median composite
    median_image = collection.median().clip(aoi)
    
    # Calculate indices
    index_images = {}
    
    if 'ndvi' in indices:
        index_images['ndvi'] = calculate_ndvi(median_image)
    
    if 'ndbi' in indices:
        index_images['ndbi'] = calculate_ndbi(median_image)
    
    if 'ndwi' in indices:
        index_images['ndwi'] = calculate_ndwi(median_image)
    
    return median_image, index_images


def main():
    """Main image processing function"""
    print("\n" + "="*60)
    print("STEP 4: Process Satellite Images")
    print("="*60)
    
    # Initialize GEE
    print("\nInitializing Earth Engine...")
    if not initialize_gee():
        return False
    
    # Create Area of Interest
    aoi = create_aoi_from_bounds(AOI_BOUNDS)
    
    # Collect images
    print("\nCollecting Sentinel-2 images...")
    collection = ee.ImageCollection(SATELLITE_DATASET) \
        .filterBounds(aoi) \
        .filterDate(START_DATE, END_DATE) \
        .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', CLOUD_COVER_THRESHOLD)) \
        .map(mask_sentinel2_clouds) \
        .limit(MAX_IMAGES)
    
    size = get_collection_size(collection)
    print(f"✓ Retrieved {size} images")
    
    if size == 0:
        print("✗ No images found.")
        return False
    
    # Process images
    print("\nProcessing images...")
    print("  Creating median composite...")
    print("  Calculating vegetation indices...")
    
    median_image, indices = process_collection(
        collection=collection,
        aoi=aoi,
        indices=['ndvi', 'ndbi', 'ndwi']
    )
    
    # Combine bands for analysis
    print("  Combining RGB and indices...")
    rgb_image = median_image.select(BANDS_RGB)
    
    combined = median_image.select(['B2', 'B3', 'B4', 'B8', 'B11']) \
        .addBands(indices['ndvi']) \
        .addBands(indices['ndbi']) \
        .addBands(indices['ndwi'])
    
    print("\n✓ Image processing complete!")
    
    print("\nOutput information:")
    info = combined.getInfo()
    print(f"  Total bands: {len(info['bands'])}")
    print(f"  Band names:")
    for band in info['bands']:
        print(f"    - {band['id']}")
    
    # Statistics
    print("\nCalculating statistics...")
    stats = combined.reduceRegion(
        reducer=ee.Reducer.mean().combine(
            ee.Reducer.minMax(),
            sharedInputs=True
        ),
        geometry=aoi,
        scale=EXPORT_SCALE,
        maxPixels=int(MAX_PIXELS)
    )
    
    stats_dict = stats.getInfo()
    print("\nMean values:")
    for key, value in sorted(stats_dict.items()):
        if 'mean' in key:
            print(f"  {key}: {value:.4f}")
    
    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
