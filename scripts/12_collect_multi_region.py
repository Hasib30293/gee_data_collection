"""
Collect high-resolution satellite imagery from multiple regions of Bangladesh.

This script rotates through different cities and geographic areas to provide
diverse training data without repeating the same location.

Supported regions:
    - Dhaka (urban capital)
    - Chittagong (coastal/industrial)
    - Sylhet (mountainous/forest)
    - Khulna (water/agriculture)
    - Rajshahi (agricultural/river)
    - Barisal (delta/water features)

Outputs:
    Google Drive:
        multi_region_images/<region>/*.tif RGB images
        multi_region_metadata/<region>/*.geojson metadata
    Local:
        data/multi_region_previews/<region>/*.png preview images

Resolution: 10m multispectral (pan-sharpened for detail)
"""

from __future__ import annotations

import json
import logging
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple

import ee
import geemap

try:
    from tqdm import tqdm
except ImportError:
    tqdm = None


# =========================
# USER EDITS - SELECT REGIONS
# =========================
PROJECT_ID = "cedar-spring-496007-j8"

# Define multiple geographic regions to rotate through
REGIONS = {
    "dhaka": {
        "name": "Dhaka Metropolitan",
        "min_latitude": 23.7,
        "max_latitude": 23.9,
        "min_longitude": 90.35,
        "max_longitude": 90.45,
        "description": "Capital city - dense urban development, roads, buildings",
    },
    "chittagong": {
        "name": "Chittagong Port City",
        "min_latitude": 22.2,
        "max_latitude": 22.4,
        "min_longitude": 91.8,
        "max_longitude": 92.0,
        "description": "Coastal industrial city - port, industrial areas, urban sprawl",
    },
    "sylhet": {
        "name": "Sylhet Region",
        "min_latitude": 24.8,
        "max_latitude": 25.0,
        "min_longitude": 91.8,
        "max_longitude": 92.0,
        "description": "Mountainous region - tea gardens, forests, water bodies",
    },
    "khulna": {
        "name": "Khulna Delta",
        "min_latitude": 22.8,
        "max_latitude": 23.0,
        "min_longitude": 89.5,
        "max_longitude": 89.7,
        "description": "Sundarbans delta - mangrove forests, water channels, wetlands",
    },
    "rajshahi": {
        "name": "Rajshahi Agriculture",
        "min_latitude": 24.35,
        "max_latitude": 24.55,
        "min_longitude": 88.55,
        "max_longitude": 88.75,
        "description": "Agricultural heartland - paddy fields, rural areas, river systems",
    },
    "barisal": {
        "name": "Barisal Delta",
        "min_latitude": 22.6,
        "max_latitude": 22.8,
        "min_longitude": 90.2,
        "max_longitude": 90.4,
        "description": "River delta - water features, flood plains, seasonal flooding",
    },
}

# Which regions to collect from (modify as needed)
REGIONS_TO_COLLECT = ["dhaka", "chittagong", "sylhet"]  # Change this list
MAX_IMAGES_PER_REGION = 30


# =========================
# Fixed collection settings
# =========================
DATASET = "COPERNICUS/S2_SR_HARMONIZED"
START_DATE = "2023-01-01"
END_DATE = "2024-12-31"
CLOUD_COVER_MAX = 5
SCALE = 10
CRS = "EPSG:4326"
MAX_PIXELS = 1e9
TILE_PIXELS = 256
TILE_SIZE_METERS = TILE_PIXELS * SCALE
TASK_DELAY_SECONDS = 30
DRIVE_BASE_FOLDER = "multi_region_images"
LOCAL_PREVIEW_DIR = Path("data") / "multi_region_previews"
LOCAL_METADATA_DIR = Path("data") / "multi_region_metadata"
MANIFEST_PATH = Path("data") / "multi_region_manifest.json"
LOG_PATH = Path("multi_region_collection.log")
BANDS_RGB = ["B4", "B3", "B2"]


def setup_logging() -> None:
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        filename=LOG_PATH,
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s",
    )
    console = logging.StreamHandler(sys.stdout)
    console.setLevel(logging.INFO)
    console.setFormatter(logging.Formatter("%(message)s"))
    logging.getLogger().addHandler(console)


def initialize_earth_engine() -> None:
    try:
        geemap.ee_initialize(project=PROJECT_ID)
    except Exception:
        try:
            ee.Initialize(project=PROJECT_ID)
        except Exception as exc:
            logging.error("Earth Engine initialization failed: %s", exc)
            raise


def pansharpen_image(image: ee.Image) -> ee.Image:
    """
    Pan-sharpen Sentinel-2 image for enhanced detail.
    
    Uses high-pass filter technique with B8A band to enhance edges.
    """
    rgb = image.select(BANDS_RGB)
    pan = image.select("B8A")
    
    kernel = ee.Kernel.gaussian(radius=2, sigma=1)
    pan_blurred = pan.convolve(kernel)
    highpass = pan.subtract(pan_blurred)
    
    sharpening_factor = 0.6  # Increased for more detail
    sharpened_rgb = rgb.add(highpass.multiply(sharpening_factor))
    sharpened_rgb = sharpened_rgb.clamp(0, 3000)
    
    return sharpened_rgb


def create_aoi_geometry(region_coords: Dict) -> ee.Geometry:
    """Create AOI geometry from region coordinates."""
    coords = [
        [region_coords["min_longitude"], region_coords["min_latitude"]],
        [region_coords["max_longitude"], region_coords["min_latitude"]],
        [region_coords["max_longitude"], region_coords["max_latitude"]],
        [region_coords["min_longitude"], region_coords["max_latitude"]],
        [region_coords["min_longitude"], region_coords["min_latitude"]],
    ]
    return ee.Geometry.Polygon([coords])


def collect_sentinel2_images(aoi: ee.Geometry, max_images: int) -> ee.ImageCollection:
    """Collect Sentinel-2 images with quality filtering."""
    collection = (
        ee.ImageCollection(DATASET)
        .filterBounds(aoi)
        .filterDate(START_DATE, END_DATE)
        .filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", CLOUD_COVER_MAX))
        .sort("system:time_start", False)  # Most recent first
        .limit(max_images)
    )
    return collection


def export_image_to_drive(
    image: ee.Image, description: str, region_name: str
) -> str:
    """Export image to Google Drive as GeoTIFF."""
    task = ee.batch.Export.image.toDrive(
        image=image,
        description=description,
        folder=DRIVE_BASE_FOLDER,
        fileNamePrefix=f"{region_name}/{description}",
        scale=SCALE,
        crs=CRS,
        maxPixels=MAX_PIXELS,
        fileFormat="GeoTIFF",
    )
    task.start()
    logging.info(f"Export started: {description} (Task ID: {task.id})")
    return task.id


def download_preview(url: str, output_path: Path) -> bool:
    """Download PNG preview thumbnail."""
    try:
        import urllib.request
        urllib.request.urlretrieve(url, output_path)
        return True
    except Exception as e:
        logging.warning(f"Failed to download {output_path}: {e}")
        return False


def process_region(region_key: str, region_info: Dict) -> Dict[str, any]:
    """Process all images from a single region."""
    logging.info(f"\n{'='*60}")
    logging.info(f"Processing Region: {region_info['name']}")
    logging.info(f"Description: {region_info['description']}")
    logging.info(f"{'='*60}\n")

    # Create region directories
    region_preview_dir = LOCAL_PREVIEW_DIR / region_key
    region_metadata_dir = LOCAL_METADATA_DIR / region_key
    region_preview_dir.mkdir(parents=True, exist_ok=True)
    region_metadata_dir.mkdir(parents=True, exist_ok=True)

    # Create AOI
    aoi = create_aoi_geometry(region_info)
    logging.info(f"AOI created for {region_info['name']}")

    # Collect images
    images = collect_sentinel2_images(aoi, MAX_IMAGES_PER_REGION)
    image_count = images.size().getInfo()
    logging.info(f"Found {image_count} Sentinel-2 images (max {MAX_IMAGES_PER_REGION})")

    if image_count == 0:
        logging.warning(f"No images found for {region_info['name']}")
        return {
            "region": region_key,
            "total": 0,
            "exported": 0,
            "previews": 0,
            "task_ids": [],
        }

    # Process each image
    task_ids = []
    preview_count = 0
    exported_count = 0

    for idx in range(image_count):
        try:
            # Get image info
            image = ee.Image(images.toList(image_count).get(idx))
            image_id = image.get("system:id").getInfo()
            timestamp = image.get("system:time_start").getInfo()
            date_str = datetime.fromtimestamp(timestamp / 1000).strftime("%Y%m%d")

            # Apply pan-sharpening
            sharpened = pansharpen_image(image)

            # Export to Drive
            description = f"{region_key}_pansharp_{date_str}_{idx:03d}"
            task_id = export_image_to_drive(sharpened, description, region_key)
            task_ids.append(task_id)
            exported_count += 1

            # Generate thumbnail URL
            thumb_url = sharpened.getThumbURL({
                "region": aoi,
                "dimensions": [512, 512],
                "format": "png",
                "min": 0,
                "max": 3000,
            })

            # Download preview
            preview_path = region_preview_dir / f"{description}_preview.png"
            if download_preview(thumb_url, preview_path):
                preview_count += 1
                logging.info(f"  [{idx + 1}/{image_count}] Preview: {date_str}")

            # Save metadata
            metadata = {
                "region": region_key,
                "region_name": region_info["name"],
                "image_id": image_id,
                "date": date_str,
                "timestamp": timestamp,
                "coordinates": {
                    "min_latitude": region_info["min_latitude"],
                    "max_latitude": region_info["max_latitude"],
                    "min_longitude": region_info["min_longitude"],
                    "max_longitude": region_info["max_longitude"],
                },
                "processing": "pan-sharpened",
                "scale_meters": SCALE,
                "dataset": DATASET,
            }
            metadata_path = region_metadata_dir / f"{description}_metadata.json"
            with open(metadata_path, "w") as f:
                json.dump(metadata, f, indent=2)

            time.sleep(1)  # Rate limiting

        except Exception as e:
            logging.error(f"Error processing image {idx}: {e}")
            continue

    logging.info(f"\nRegion {region_info['name']} Results:")
    logging.info(f"  Total found: {image_count}")
    logging.info(f"  Exported: {exported_count}")
    logging.info(f"  Previews: {preview_count}")

    return {
        "region": region_key,
        "region_name": region_info["name"],
        "total": image_count,
        "exported": exported_count,
        "previews": preview_count,
        "task_ids": task_ids,
    }


def save_manifest(results: List[Dict]) -> None:
    """Save manifest with all collection info."""
    manifest = {
        "timestamp": datetime.now().isoformat(),
        "project_id": PROJECT_ID,
        "dataset": DATASET,
        "scale_meters": SCALE,
        "processing": "pan-sharpened",
        "regions_collected": len(results),
        "regions": results,
        "total_tasks": sum(len(r["task_ids"]) for r in results),
        "drive_folder": DRIVE_BASE_FOLDER,
    }
    MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(MANIFEST_PATH, "w") as f:
        json.dump(manifest, f, indent=2)
    logging.info(f"\nManifest saved: {MANIFEST_PATH}")


def main() -> None:
    """Main execution - collect from all selected regions."""
    logging.info("\n" + "="*60)
    logging.info("MULTI-REGION SATELLITE DATA COLLECTION")
    logging.info("="*60)
    logging.info(f"Start time: {datetime.now().isoformat()}")
    logging.info(f"Regions to collect: {', '.join(REGIONS_TO_COLLECT)}")
    logging.info(f"Max images per region: {MAX_IMAGES_PER_REGION}")
    logging.info(f"Date range: {START_DATE} to {END_DATE}")
    logging.info(f"Cloud cover max: {CLOUD_COVER_MAX}%")
    logging.info(f"Processing: Pan-sharpened Sentinel-2 @ {SCALE}m resolution")

    initialize_earth_engine()

    results = []
    for region_key in REGIONS_TO_COLLECT:
        if region_key not in REGIONS:
            logging.error(f"Region '{region_key}' not found")
            continue

        region_info = REGIONS[region_key]
        result = process_region(region_key, region_info)
        results.append(result)
        time.sleep(5)  # Delay between regions to avoid rate limits

    # Save manifest
    save_manifest(results)

    # Final summary
    logging.info("\n" + "="*60)
    logging.info("COLLECTION SUMMARY")
    logging.info("="*60)
    for result in results:
        logging.info(
            f"{result['region_name']}: {result['exported']} images exported, "
            f"{result['previews']} previews saved"
        )
    logging.info("="*60)
    logging.info("All exports submitted to Google Drive")
    logging.info("Monitor progress in Earth Engine Code Editor or Drive folder")
    logging.info(f"End time: {datetime.now().isoformat()}")


if __name__ == "__main__":
    setup_logging()
    main()
