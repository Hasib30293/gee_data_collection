"""
Google Earth Engine Data Collection - Main Workflow
Run complete pipeline for satellite data collection, processing, and export
"""

import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from config.settings import *
from scripts.gee_utils import (
    authenticate_user, initialize_gee, is_authenticated,
    create_aoi_from_bounds, mask_sentinel2_clouds,
    filter_collection_by_cloud_cover, get_collection_size,
    calculate_ndvi, create_export_task, start_export_task
)
import ee


def print_header(text):
    """Print formatted section header"""
    print(f"\n{'='*70}")
    print(f"  {text}")
    print(f"{'='*70}\n")


def print_step(step_num, text):
    """Print step information"""
    print(f"\n[STEP {step_num}] {text}")
    print("-" * 70)


def step_1_authenticate():
    """Step 1: Authentication"""
    print_step(1, "AUTHENTICATION")
    
    if is_authenticated():
        print("✓ Already authenticated with Google Earth Engine")
        return True
    
    print("You need to authenticate with Google Earth Engine.")
    print("A browser window will open. Please:")
    print("  1. Sign in with your Google account")
    print("  2. Grant permission to Google Earth Engine")
    print("  3. Copy the authorization code if prompted")
    print("  4. Paste the code back into the terminal")
    
    input("\nPress Enter to start authentication...")
    
    if authenticate_user():
        print("\n✓ Authentication successful!")
        return True
    else:
        print("\n✗ Authentication failed. Please try again.")
        return False


def step_2_initialize():
    """Step 2: Initialize GEE"""
    print_step(2, "INITIALIZE GOOGLE EARTH ENGINE")
    
    print(f"Project ID: {GEE_PROJECT_ID}")
    
    if initialize_gee(project_id=GEE_PROJECT_ID):
        print("\n✓ GEE initialized successfully!")
        return True
    else:
        print("\n✗ Initialization failed.")
        print("Make sure your project ID is correct in .env or config/settings.py")
        return False


def step_3_collect_images():
    """Step 3: Collect satellite images"""
    print_step(3, "COLLECT SATELLITE IMAGES")
    
    print("Area of Interest:")
    print(f"  Longitude: {AOI_BOUNDS['min_longitude']} to {AOI_BOUNDS['max_longitude']}")
    print(f"  Latitude: {AOI_BOUNDS['min_latitude']} to {AOI_BOUNDS['max_latitude']}")
    
    print(f"\nCollection Parameters:")
    print(f"  Dataset: {SATELLITE_DATASET}")
    print(f"  Date range: {START_DATE} to {END_DATE}")
    print(f"  Cloud cover threshold: {CLOUD_COVER_THRESHOLD}%")
    print(f"  Max images: {MAX_IMAGES}")
    
    aoi = create_aoi_from_bounds(AOI_BOUNDS)
    
    print("\nCollecting images...")
    collection = ee.ImageCollection(SATELLITE_DATASET) \
        .filterBounds(aoi) \
        .filterDate(START_DATE, END_DATE) \
        .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', CLOUD_COVER_THRESHOLD)) \
        .map(mask_sentinel2_clouds) \
        .limit(MAX_IMAGES)
    
    size = get_collection_size(collection)
    
    if size == 0:
        print(f"\n✗ No images found with current parameters.")
        print("Try adjusting:")
        print("  - Date range (START_DATE, END_DATE)")
        print("  - Cloud cover threshold (CLOUD_COVER_THRESHOLD)")
        print("  - Area of interest (AOI_BOUNDS)")
        return None
    
    print(f"\n✓ Retrieved {size} images")
    
    # Show first image info
    first_image = ee.Image(collection.first())
    info = first_image.getInfo()
    print(f"  First image bands: {len(info['bands'])}")
    print(f"  Time range: {info['properties'].get('system:time_start', 'N/A')}")
    
    return collection, aoi


def step_4_process_images(collection, aoi):
    """Step 4: Process images"""
    print_step(4, "PROCESS IMAGES")
    
    print("Creating median composite...")
    median_image = collection.median().clip(aoi)
    
    print("Calculating indices...")
    ndvi = calculate_ndvi(median_image)
    
    print("✓ Processing complete")
    
    return median_image, ndvi


def step_5_preview():
    """Step 5: Preview and statistics"""
    print_step(5, "IMAGE STATISTICS & PREVIEW")
    
    print("Image processing summary:")
    print("  ✓ Median composite created")
    print("  ✓ Cloud mask applied")
    print("  ✓ NDVI calculated")
    print("\nTo visualize interactively:")
    print("  Option 1: jupyter notebook notebooks/visualization.ipynb")
    print("  Option 2: Run scripts/05_visualize.py")


def step_6_export(median_image, aoi):
    """Step 6: Export to Google Drive"""
    print_step(6, "EXPORT TO GOOGLE DRIVE")
    
    print(f"Preparing export to: {GOOGLE_DRIVE_FOLDER}")
    print(f"  Export scale: {EXPORT_SCALE} meters")
    print(f"  CRS: {EXPORT_CRS}")
    print(f"  Format: {EXPORT_FORMAT}")
    
    # Create RGB export
    rgb_image = median_image.select(['B4', 'B3', 'B2']).clip(aoi)
    
    task = create_export_task(
        image=rgb_image,
        description='satellite_rgb_main_workflow',
        folder=GOOGLE_DRIVE_FOLDER,
        aoi=aoi,
        scale=EXPORT_SCALE,
        crs=EXPORT_CRS,
        file_format=EXPORT_FORMAT
    )
    
    print("\nStarting export task...")
    task_id = start_export_task(task)
    
    return task_id


def step_7_next_steps():
    """Step 7: Display next steps"""
    print_step(7, "NEXT STEPS")
    
    print("""For GAN+VLM Training Dataset Preparation:

1. DOWNLOAD
   - Check Google Drive folder: {}
   - Download exported .tif files
   - Wait for export to complete (check Tasks in GEE Code Editor)

2. ORGANIZE
   - Create folders: flood/, urban/, forest/, agricultural/
   - Sort images by category

3. RESIZE
   - Use ImageMagick or Python:
     convert image.tif -resize 256x256 image_256.tif
   - Or run: python scripts/resize_images.py

4. PREPARE CAPTIONS (for VLM)
   - Basic: "flood", "urban", "forest"
   - Enhanced: "Satellite view of flooded area near [location]"

5. USE FOR TRAINING
   - GAN training: Image pairs for synthesis
   - VLM fine-tuning: Image+caption pairs
   - Classification: Feature extraction

DOCUMENTATION:
   - See README.md for detailed instructions
   - See config/settings.py for all parameters
   - Check individual scripts in scripts/ folder

TROUBLESHOOTING:
   - No images found? Check date range and cloud threshold
   - Map not showing? Install: pip install geemap
   - Python version? Use Python 3.6-3.12 (not 3.13+)
    """.format(GOOGLE_DRIVE_FOLDER))


def main():
    """Main workflow"""
    print_header("Google Earth Engine - Complete Data Collection Workflow")
    
    print("""This script will:
1. Authenticate with Google Earth Engine
2. Initialize your GEE project
3. Collect Sentinel-2 satellite images
4. Process and calculate indices
5. Export data to Google Drive

Total time: 2-10 minutes (depends on image availability)
    """)
    
    input("Press Enter to begin...")
    
    # Step 1: Authentication
    if not step_1_authenticate():
        return False
    
    # Step 2: Initialize
    if not step_2_initialize():
        return False
    
    # Step 3: Collect Images
    result = step_3_collect_images()
    if result is None:
        return False
    
    collection, aoi = result
    
    # Step 4: Process Images
    median_image, ndvi = step_4_process_images(collection, aoi)
    
    # Step 5: Preview
    step_5_preview()
    
    # Step 6: Export
    ask_export = input("\nDo you want to export data to Google Drive? (yes/no): ").lower().strip()
    if ask_export in ['yes', 'y', '']:
        task_id = step_6_export(median_image, aoi)
    
    # Step 7: Next Steps
    step_7_next_steps()
    
    print_header("✓ WORKFLOW COMPLETE")
    
    return True


if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n✗ Workflow interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
