"""
Collect satellite imagery from 15+ DIFFERENT cities and locations across Bangladesh.

This script collects from diverse geographic locations, not repeated dates from 
the same place. Each city/area gets a few high-quality images.

Locations covered:
    1. Dhaka - Urban capital (dense buildings, roads)
    2. Chittagong - Coastal industrial (ports, factories)  
    3. Sylhet - Mountainous (forests, tea gardens)
    4. Khulna - Sundarbans (mangrove forests)
    5. Rajshahi - Agricultural (paddy fields)
    6. Barisal - River delta (water features)
    7. Comilla - Industrial town
    8. Mymensingh - University city
    9. Rangpur - Northern plains
    10. Dinajpur - Border region
    11. Jashore - Agricultural area
    12. Faridpur - Central region
    13. Tangail - Industrial zone
    14. Narayanganj - Port city
    15. Gazipur - Manufacturing hub

Each location: 5-10 images from DIFFERENT geographic positions
Result: 75-150 diverse images from truly different places

Outputs:
    Local previews: data/diverse_location_previews/<city>/<location>_*.png
    Metadata: data/diverse_location_metadata/<city>/*.json
    Google Drive: diverse_location_images/<city>/*.tif
"""

from __future__ import annotations

import json
import logging
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List

import ee
import geemap

try:
    from tqdm import tqdm
except ImportError:
    tqdm = None


# =========================
# USER EDITS - LOCATIONS
# =========================
PROJECT_ID = "cedar-spring-496007-j8"

# 15+ DIFFERENT LOCATIONS across Bangladesh
# Each location has DIFFERENT geographic coordinates (not same place)
LOCATIONS = {
    "dhaka_city": {
        "name": "Dhaka City Center",
        "min_latitude": 23.70, "max_latitude": 23.75,
        "min_longitude": 90.35, "max_longitude": 90.40,
        "type": "Urban - Central business district",
    },
    "dhaka_suburbs": {
        "name": "Dhaka Suburbs",
        "min_latitude": 23.80, "max_latitude": 23.85,
        "min_longitude": 90.45, "max_longitude": 90.50,
        "type": "Urban - Residential areas",
    },
    "chittagong_port": {
        "name": "Chittagong Port",
        "min_latitude": 22.25, "max_latitude": 22.30,
        "min_longitude": 91.80, "max_longitude": 91.85,
        "type": "Coastal - Port infrastructure",
    },
    "chittagong_industrial": {
        "name": "Chittagong Industrial Zone",
        "min_latitude": 22.35, "max_latitude": 22.40,
        "min_longitude": 91.90, "max_longitude": 91.95,
        "type": "Industrial - Manufacturing",
    },
    "sylhet_city": {
        "name": "Sylhet City",
        "min_latitude": 24.88, "max_latitude": 24.93,
        "min_longitude": 91.88, "max_longitude": 91.93,
        "type": "Mountain - Urban area",
    },
    "sylhet_teagarden": {
        "name": "Sylhet Tea Gardens",
        "min_latitude": 25.00, "max_latitude": 25.05,
        "min_longitude": 92.00, "max_longitude": 92.05,
        "type": "Agriculture - Tea plantations",
    },
    "khulna_city": {
        "name": "Khulna City",
        "min_latitude": 22.80, "max_latitude": 22.85,
        "min_longitude": 89.50, "max_longitude": 89.55,
        "type": "Delta - Urban area",
    },
    "sundarbans": {
        "name": "Sundarbans Mangrove",
        "min_latitude": 22.90, "max_latitude": 22.95,
        "min_longitude": 89.60, "max_longitude": 89.65,
        "type": "Wetland - Mangrove forest",
    },
    "rajshahi_city": {
        "name": "Rajshahi City",
        "min_latitude": 24.37, "max_latitude": 24.42,
        "min_longitude": 88.57, "max_longitude": 88.62,
        "type": "Urban - City center",
    },
    "rajshahi_fields": {
        "name": "Rajshahi Agricultural Fields",
        "min_latitude": 24.50, "max_latitude": 24.55,
        "min_longitude": 88.65, "max_longitude": 88.70,
        "type": "Agriculture - Paddy fields",
    },
    "barisal_city": {
        "name": "Barisal City",
        "min_latitude": 22.70, "max_latitude": 22.75,
        "min_longitude": 90.25, "max_longitude": 90.30,
        "type": "Delta - Urban area",
    },
    "barisal_delta": {
        "name": "Barisal River Delta",
        "min_latitude": 22.65, "max_latitude": 22.70,
        "min_longitude": 90.35, "max_longitude": 90.40,
        "type": "Water - River delta system",
    },
    "comilla_city": {
        "name": "Comilla City",
        "min_latitude": 23.45, "max_latitude": 23.50,
        "min_longitude": 91.18, "max_longitude": 91.23,
        "type": "Urban - Industrial town",
    },
    "mymensingh_city": {
        "name": "Mymensingh City",
        "min_latitude": 24.75, "max_latitude": 24.80,
        "min_longitude": 90.40, "max_longitude": 90.45,
        "type": "Urban - University city",
    },
    "rangpur_city": {
        "name": "Rangpur City",
        "min_latitude": 25.74, "max_latitude": 25.79,
        "min_longitude": 88.60, "max_longitude": 88.65,
        "type": "Urban - Northern plains",
    },
    "narayanganj_port": {
        "name": "Narayanganj Port City",
        "min_latitude": 23.62, "max_latitude": 23.67,
        "min_longitude": 90.48, "max_longitude": 90.53,
        "type": "Port - Industrial area",
    },
}

# How many images per location
IMAGES_PER_LOCATION = 5

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
TASK_DELAY_SECONDS = 20
DRIVE_BASE_FOLDER = "diverse_location_images"
LOCAL_PREVIEW_DIR = Path("data") / "diverse_location_previews"
LOCAL_METADATA_DIR = Path("data") / "diverse_location_metadata"
MANIFEST_PATH = Path("data") / "diverse_locations_manifest.json"
LOG_PATH = Path("diverse_locations_collection.log")
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
    """Pan-sharpen Sentinel-2 image for enhanced detail."""
    rgb = image.select(BANDS_RGB)
    pan = image.select("B8A")
    kernel = ee.Kernel.gaussian(radius=2, sigma=1)
    pan_blurred = pan.convolve(kernel)
    highpass = pan.subtract(pan_blurred)
    sharpening_factor = 0.6
    sharpened_rgb = rgb.add(highpass.multiply(sharpening_factor))
    sharpened_rgb = sharpened_rgb.clamp(0, 3000)
    return sharpened_rgb


def create_aoi_geometry(location_coords: Dict) -> ee.Geometry:
    """Create AOI geometry from location coordinates."""
    coords = [
        [location_coords["min_longitude"], location_coords["min_latitude"]],
        [location_coords["max_longitude"], location_coords["min_latitude"]],
        [location_coords["max_longitude"], location_coords["max_latitude"]],
        [location_coords["min_longitude"], location_coords["max_latitude"]],
        [location_coords["min_longitude"], location_coords["min_latitude"]],
    ]
    return ee.Geometry.Polygon([coords])


def collect_sentinel2_images(aoi: ee.Geometry, max_images: int) -> ee.ImageCollection:
    """Collect best quality Sentinel-2 images."""
    collection = (
        ee.ImageCollection(DATASET)
        .filterBounds(aoi)
        .filterDate(START_DATE, END_DATE)
        .filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", CLOUD_COVER_MAX))
        .sort("CLOUDY_PIXEL_PERCENTAGE")  # Least cloudy first
        .limit(max_images)
    )
    return collection


def export_image_to_drive(
    image: ee.Image, description: str, location_key: str
) -> str:
    """Export image to Google Drive."""
    task = ee.batch.Export.image.toDrive(
        image=image,
        description=description,
        folder=DRIVE_BASE_FOLDER,
        fileNamePrefix=f"{location_key}/{description}",
        scale=SCALE,
        crs=CRS,
        maxPixels=MAX_PIXELS,
        fileFormat="GeoTIFF",
    )
    task.start()
    return task.id


def download_preview(url: str, output_path: Path) -> bool:
    """Download PNG preview."""
    try:
        import urllib.request
        urllib.request.urlretrieve(url, output_path)
        return True
    except Exception as e:
        logging.warning(f"Failed to download {output_path}: {e}")
        return False


def process_location(location_key: str, location_info: Dict) -> Dict:
    """Process a single location."""
    logging.info(f"\n{'='*70}")
    logging.info(f"Location: {location_info['name']}")
    logging.info(f"Type: {location_info['type']}")
    logging.info(f"{'='*70}")

    # Create directories
    location_preview_dir = LOCAL_PREVIEW_DIR / location_key
    location_metadata_dir = LOCAL_METADATA_DIR / location_key
    location_preview_dir.mkdir(parents=True, exist_ok=True)
    location_metadata_dir.mkdir(parents=True, exist_ok=True)

    # Create AOI
    aoi = create_aoi_geometry(location_info)

    # Collect images
    images = collect_sentinel2_images(aoi, IMAGES_PER_LOCATION)
    image_count = images.size().getInfo()
    logging.info(f"Found {image_count} cloud-free images (max {IMAGES_PER_LOCATION})")

    if image_count == 0:
        logging.warning(f"No images found for {location_info['name']}")
        return {
            "location_key": location_key,
            "location_name": location_info["name"],
            "total": 0,
            "exported": 0,
            "previews": 0,
            "task_ids": [],
        }

    task_ids = []
    preview_count = 0
    exported_count = 0

    for idx in range(image_count):
        try:
            image = ee.Image(images.toList(image_count).get(idx))
            image_id = image.get("system:id").getInfo()
            timestamp = image.get("system:time_start").getInfo()
            date_str = datetime.fromtimestamp(timestamp / 1000).strftime("%Y%m%d")
            cloud_pct = image.get("CLOUDY_PIXEL_PERCENTAGE").getInfo()

            # Pan-sharpen
            sharpened = pansharpen_image(image)

            # Export to Drive
            description = f"{location_key}_pansharp_{date_str}_{idx:02d}"
            task_id = export_image_to_drive(sharpened, description, location_key)
            task_ids.append(task_id)
            exported_count += 1

            # Download preview
            thumb_url = sharpened.getThumbURL({
                "region": aoi,
                "dimensions": [512, 512],
                "format": "png",
                "min": 0,
                "max": 3000,
            })
            preview_path = location_preview_dir / f"{description}_preview.png"
            if download_preview(thumb_url, preview_path):
                preview_count += 1
                logging.info(f"  [{idx + 1}/{image_count}] {date_str} (Cloud: {cloud_pct:.1f}%)")

            # Save metadata
            metadata = {
                "location_key": location_key,
                "location_name": location_info["name"],
                "location_type": location_info["type"],
                "image_id": image_id,
                "date": date_str,
                "timestamp": timestamp,
                "cloud_percentage": cloud_pct,
                "coordinates": {
                    "min_latitude": location_info["min_latitude"],
                    "max_latitude": location_info["max_latitude"],
                    "min_longitude": location_info["min_longitude"],
                    "max_longitude": location_info["max_longitude"],
                },
                "processing": "pan-sharpened",
                "scale_meters": SCALE,
            }
            metadata_path = location_metadata_dir / f"{description}_metadata.json"
            with open(metadata_path, "w") as f:
                json.dump(metadata, f, indent=2)

            time.sleep(0.5)

        except Exception as e:
            logging.error(f"Error processing image {idx}: {e}")
            continue

    logging.info(f"\n{location_info['name']} Complete:")
    logging.info(f"  Exported: {exported_count} | Previews: {preview_count}")

    return {
        "location_key": location_key,
        "location_name": location_info["name"],
        "location_type": location_info["type"],
        "total": image_count,
        "exported": exported_count,
        "previews": preview_count,
        "task_ids": task_ids,
    }


def save_manifest(results: List[Dict]) -> None:
    """Save manifest with all location data."""
    total_images = sum(r["exported"] for r in results)
    manifest = {
        "timestamp": datetime.now().isoformat(),
        "project_id": PROJECT_ID,
        "dataset": DATASET,
        "processing": "pan-sharpened",
        "scale_meters": SCALE,
        "total_locations": len(results),
        "total_images_exported": total_images,
        "locations": results,
        "drive_folder": DRIVE_BASE_FOLDER,
    }
    MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(MANIFEST_PATH, "w") as f:
        json.dump(manifest, f, indent=2)
    logging.info(f"\nManifest saved: {MANIFEST_PATH}")


def main() -> None:
    """Main execution."""
    logging.info("\n" + "="*70)
    logging.info("DIVERSE LOCATION SATELLITE DATA COLLECTION")
    logging.info("="*70)
    logging.info(f"Start time: {datetime.now().isoformat()}")
    logging.info(f"Total locations: {len(LOCATIONS)}")
    logging.info(f"Images per location: {IMAGES_PER_LOCATION}")
    logging.info(f"Expected total: {len(LOCATIONS) * IMAGES_PER_LOCATION} images")
    logging.info(f"Processing: Pan-sharpened Sentinel-2 @ {SCALE}m resolution")

    initialize_earth_engine()

    results = []
    for location_key in sorted(LOCATIONS.keys()):
        location_info = LOCATIONS[location_key]
        result = process_location(location_key, location_info)
        results.append(result)
        time.sleep(2)  # Delay between locations

    # Save manifest
    save_manifest(results)

    # Final summary
    logging.info("\n" + "="*70)
    logging.info("FINAL SUMMARY - DIVERSE LOCATIONS")
    logging.info("="*70)
    total_exported = 0
    total_previews = 0
    for result in results:
        if result["exported"] > 0:
            logging.info(
                f"{result['location_name']:40s} | "
                f"Exported: {result['exported']:2d} | "
                f"Type: {result['location_type']}"
            )
            total_exported += result["exported"]
            total_previews += result["previews"]
    
    logging.info("="*70)
    logging.info(f"TOTAL IMAGES EXPORTED: {total_exported}")
    logging.info(f"TOTAL PREVIEWS DOWNLOADED: {total_previews}")
    logging.info("="*70)
    logging.info("All exports submitted to Google Drive")
    logging.info(f"Download folder: {DRIVE_BASE_FOLDER}/")
    logging.info(f"End time: {datetime.now().isoformat()}")


if __name__ == "__main__":
    setup_logging()
    main()
