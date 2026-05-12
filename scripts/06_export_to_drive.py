"""
Step 6: Export Satellite Images Locally
Download images to your laptop for training and analysis
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
    filter_collection_by_bounds, download_image_local, 
    download_image_collection_local, get_collection_size,
    calculate_ndvi, calculate_ndbi, calculate_ndwi
)


def export_median_image_local(collection, aoi, filename, output_folder):
    """
    Export median composite image locally
    
    Args:
        collection (ee.ImageCollection): Image collection
        aoi (ee.Geometry): Area of interest
        filename (str): Output filename
        output_folder (str): Local folder path
    
    Returns:
        str: Path to saved file
    """
    median_image = collection.median().clip(aoi)
    
    # Select RGB bands
    rgb_image = median_image.select(BANDS_RGB)
    
    return download_image_local(
        image=rgb_image,
        aoi=aoi,
        filename=filename,
        output_folder=output_folder,
        scale=EXPORT_SCALE,
        crs=EXPORT_CRS
    )


def export_all_bands_local(collection, aoi, filename, output_folder):
    """
    Export all bands locally
    
    Args:
        collection (ee.ImageCollection): Image collection
        aoi (ee.Geometry): Area of interest
        filename (str): Output filename
        output_folder (str): Local folder path
    
    Returns:
        str: Path to saved file
    """
    image = collection.median().clip(aoi)
    
    return download_image_local(
        image=image,
        aoi=aoi,
        filename=filename,
        output_folder=output_folder,
        scale=EXPORT_SCALE,
        crs=EXPORT_CRS
    )


def export_indices_local(collection, aoi, output_folder):
    """
    Export calculated indices locally
    
    Args:
        collection (ee.ImageCollection): Image collection
        aoi (ee.Geometry): Area of interest
        output_folder (str): Local folder path
    
    Returns:
        list: Paths to saved files
    """
    median = collection.median().clip(aoi)
    downloaded = []
    
    # NDVI
    print("\n  Exporting NDVI...")
    ndvi = calculate_ndvi(median)
    path = download_image_local(ndvi, aoi, 'ndvi_index', output_folder, 
                               EXPORT_SCALE, EXPORT_CRS)
    if path:
        downloaded.append(path)
    
    # NDBI
    print("  Exporting NDBI...")
    ndbi = calculate_ndbi(median)
    path = download_image_local(ndbi, aoi, 'ndbi_index', output_folder, 
                               EXPORT_SCALE, EXPORT_CRS)
    if path:
        downloaded.append(path)
    
    # NDWI
    print("  Exporting NDWI...")
    ndwi = calculate_ndwi(median)
    path = download_image_local(ndwi, aoi, 'ndwi_index', output_folder, 
                               EXPORT_SCALE, EXPORT_CRS)
    if path:
        downloaded.append(path)
    
    return downloaded


def main():
    """Main export function"""
    print("\n" + "="*60)
    print("STEP 6: Export Images to Local Folder")
    print("="*60)
    
    # Initialize GEE
    print("\nInitializing Earth Engine...")
    if not initialize_gee():
        return False
    
    # Create output folder
    output_folder = Path.cwd() / 'data' / 'sentinel2_downloads'
    output_folder.mkdir(parents=True, exist_ok=True)
    print(f"✓ Output folder: {output_folder}")
    
    # Create Area of Interest
    aoi = create_aoi_from_bounds(AOI_BOUNDS)
    
    # Collect images
    print("\nCollecting Sentinel-2 images...")
    collection = ee.ImageCollection(SATELLITE_DATASET) \
        .filterBounds(aoi) \
        .filterDate(START_DATE, END_DATE) \
        .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', CLOUD_COVER_THRESHOLD)) \
        .map(mask_sentinel2_clouds)
    
    size = get_collection_size(collection)
    print(f"✓ Retrieved {size} images")
    
    if size == 0:
        print("✗ No images found. Check your AOI and date range.")
        return False
    
    # Export options
    print("\n" + "="*60)
    print("Export Options:")
    print("="*60)
    print("1. RGB Median Composite")
    print("2. All Bands (11 bands)")
    print("3. Vegetation/Water Indices (NDVI, NDBI, NDWI)")
    print("4. Individual Images from Collection")
    print("5. All of the above")
    print("="*60)
    
    # For automated export, do all
    downloads = []
    
    print("\n[1/4] Exporting RGB Median Composite...")
    path = export_median_image_local(collection, aoi, 'sentinel2_rgb_median', 
                                    output_folder)
    if path:
        downloads.append(path)
    
    print("\n[2/4] Exporting All Bands...")
    path = export_all_bands_local(collection, aoi, 'sentinel2_all_bands_median', 
                                 output_folder)
    if path:
        downloads.append(path)
    
    print("\n[3/4] Exporting Indices...")
    indices = export_indices_local(collection, aoi, output_folder)
    downloads.extend(indices)
    
    print("\n[4/4] Exporting Individual Images...")
    limited_collection = collection.limit(MAX_IMAGES)
    individual_downloads = download_image_collection_local(
        limited_collection, aoi, 'image', output_folder, 
        limit=min(5, MAX_IMAGES)  # Limit to 5 individual images
    )
    downloads.extend(individual_downloads)
    
    # Summary
    print("\n" + "="*60)
    print("Export Complete!")
    print("="*60)
    print(f"\nDownloaded {len(downloads)} files to:")
    print(f"  {output_folder}")
    
    print("\nFiles downloaded:")
    for i, file_path in enumerate(downloads, 1):
        file_size = Path(file_path).stat().st_size / 1024 / 1024
        print(f"  {i}. {Path(file_path).name} ({file_size:.2f} MB)")
    
    print("\n" + "="*60)
    print("Next Steps for GAN+VLM Training:")
    print("="*60)
    print("1. Organize images by category:")
    print("   data/")
    print("   ├── flood/")
    print("   ├── urban/")
    print("   ├── forest/")
    print("   └── agricultural/")
    print("\n2. Resize images to 256x256 or 128x128 pixels")
    print("3. Create captions for VLM training")
    print("4. Use in your training pipeline")
    print("="*60)
    
    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

