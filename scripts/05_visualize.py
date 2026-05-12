"""
Step 5: Visualize Satellite Images
Create interactive maps with geemap and folium
Requires Jupyter notebook environment or display-capable environment
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
    filter_collection_by_bounds, calculate_ndvi
)

try:
    import geemap
    GEEMAP_AVAILABLE = True
except ImportError:
    GEEMAP_AVAILABLE = False
    print("Warning: geemap not available. Install with: pip install geemap")


def visualize_with_geemap(collection, aoi, vis_params):
    """
    Visualize satellite images using geemap
    
    Args:
        collection (ee.ImageCollection): Image collection
        aoi (ee.Geometry): Area of interest
        vis_params (dict): Visualization parameters
    
    Returns:
        geemap.Map: Interactive map
    """
    if not GEEMAP_AVAILABLE:
        print("✗ geemap not available. Install with: pip install geemap")
        return None
    
    # Create median image
    median_image = collection.median().clip(aoi)
    
    # Create map
    Map = geemap.Map(center=(
        (AOI_BOUNDS['min_latitude'] + AOI_BOUNDS['max_latitude']) / 2,
        (AOI_BOUNDS['min_longitude'] + AOI_BOUNDS['max_longitude']) / 2
    ), zoom=8)
    
    # Add RGB layer
    Map.addLayer(median_image, vis_params, 'Sentinel-2 RGB')
    
    # Add NDVI layer
    ndvi_image = calculate_ndvi(median_image)
    ndvi_params = {'min': -1, 'max': 1, 'palette': ['red', 'yellow', 'green']}
    Map.addLayer(ndvi_image, ndvi_params, 'NDVI')
    
    # Add layer control
    Map.addLayerControl()
    
    return Map


def main():
    """Main visualization function"""
    print("\n" + "="*60)
    print("STEP 5: Visualize Satellite Images")
    print("="*60)
    
    if not GEEMAP_AVAILABLE:
        print("\n✗ geemap is required for visualization.")
        print("Install with: pip install geemap")
        print("\nAlternatively, use the Jupyter notebook: notebooks/visualization.ipynb")
        return False
    
    # Initialize GEE
    print("\nInitializing Earth Engine...")
    if not initialize_gee():
        return False
    
    # Create Area of Interest
    aoi = create_aoi_from_bounds(AOI_BOUNDS)
    
    # Collect images
    print("\nCollecting and processing images...")
    collection = ee.ImageCollection(SATELLITE_DATASET) \
        .filterBounds(aoi) \
        .filterDate(START_DATE, END_DATE) \
        .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', CLOUD_COVER_THRESHOLD)) \
        .map(mask_sentinel2_clouds) \
        .limit(MAX_IMAGES)
    
    # Visualize
    print("\nCreating interactive map...")
    Map = visualize_with_geemap(collection, aoi, VIS_PARAMS)
    
    if Map is not None:
        print("✓ Map created successfully!")
        print("\nNote: For Jupyter notebooks, display the map with: Map")
        return True
    
    return False


if __name__ == "__main__":
    success = main()
    
    if success:
        print("\n" + "="*60)
        print("For interactive visualization, use Jupyter notebook:")
        print("  jupyter notebook notebooks/visualization.ipynb")
        print("="*60)
    
    sys.exit(0 if success else 1)
