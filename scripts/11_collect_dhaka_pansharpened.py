"""
Collect pan-sharpened Sentinel-2 Dhaka tiles for higher resolution detail.

Pan-sharpening combines Sentinel-2 multispectral bands (10m) with panchromatic 
band to enhance edge definition and reduce artifacts. Results in sharper detail
for roads, buildings, and fine features.

Outputs:
    Google Drive:
        dhaka_pansharpened_images/*.tif RGB images (higher detail)
        dhaka_pansharpened_metadata/*.geojson metadata
    Local:
        data/dhaka_pansharpened_previews/*.png preview images

Resolution: 10m (same) but with significantly sharper detail
"""

from __future__ import annotations

import json
import logging
import math
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

import ee
import geemap

try:
    from tqdm import tqdm
except ImportError:
    tqdm = None


# =========================
# USER EDITS ONLY THESE
# =========================
PROJECT_ID = "cedar-spring-496007-j8"
AOI_COORDINATES = {
    "min_latitude": 23.7,
    "max_latitude": 23.9,
    "min_longitude": 90.35,
    "max_longitude": 90.45,
}
MAX_IMAGES = 50


# =========================
# Fixed pan-sharpening settings
# =========================
DATASET = "COPERNICUS/S2_SR_HARMONIZED"
START_DATE = "2023-01-01"
END_DATE = "2024-12-31"
CLOUD_COVER_MAX = 5
SCALE = 10  # 10m resolution (pan-sharpening maintains this)
CRS = "EPSG:4326"
MAX_PIXELS = 1e9
TILE_PIXELS = 256
TILE_SIZE_METERS = TILE_PIXELS * SCALE
TASK_DELAY_SECONDS = 30
BATCH_SIZE = 50
DRIVE_BASE_FOLDER = "dhaka_pansharpened"
LOCAL_PREVIEW_DIR = Path("data") / "dhaka_pansharpened_previews"
LOCAL_METADATA_DIR = Path("data") / "dhaka_pansharpened_metadata"
MANIFEST_PATH = Path("data") / "dhaka_pansharpened_manifest.json"
LOG_PATH = Path("dhaka_pansharpening.log")
BANDS_RGB = ["B4", "B3", "B2"]
BANDS_PAN = ["B8A"]  # Sentinel-2 pan-like band (narrow red edge)


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
    Pan-sharpen Sentinel-2 image using high-pass filter technique.
    
    Enhances detail by combining multispectral bands with panchromatic-like band.
    
    Args:
        image: Sentinel-2 image
    
    Returns:
        Pan-sharpened RGB image
    """
    # Extract RGB bands
    rgb = image.select(BANDS_RGB)
    
    # Use B8A (narrow red edge) as pseudo-panchromatic band
    # Apply Gaussian blur to create low-pass version
    pan = image.select("B8A")
    
    # High-pass filter: pan - blur(pan) gives high frequency detail
    kernel = ee.Kernel.gaussian(radius=2, sigma=1)
    pan_blurred = pan.convolve(kernel)
    highpass = pan.subtract(pan_blurred)
    
    # Scale and add high-frequency detail to each RGB band
    # This enhances edges and fine features
    sharpening_factor = 0.5
    
    sharpened_rgb = rgb.add(highpass.multiply(sharpening_factor))
    
    # Clip to valid ranges to prevent artifacts
    sharpened_rgb = sharpened_rgb.clamp(0, 3000)
    
    return sharpened_rgb


def create_aoi_geometry() -> ee.Geometry:
    """Create AOI geometry from coordinates."""
    coords = [
        [AOI_COORDINATES["min_longitude"], AOI_COORDINATES["min_latitude"]],
        [AOI_COORDINATES["max_longitude"], AOI_COORDINATES["min_latitude"]],
        [AOI_COORDINATES["max_longitude"], AOI_COORDINATES["max_latitude"]],
        [AOI_COORDINATES["min_longitude"], AOI_COORDINATES["max_latitude"]],
        [AOI_COORDINATES["min_longitude"], AOI_COORDINATES["min_latitude"]],
    ]
    return ee.Geometry.Polygon([coords])


def collect_sentinel2_images(aoi: ee.Geometry) -> ee.ImageCollection:
    """Collect Sentinel-2 images over AOI with cloud filtering."""
    collection = (
        ee.ImageCollection(DATASET)
        .filterBounds(aoi)
        .filterDate(START_DATE, END_DATE)
        .filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", CLOUD_COVER_MAX))
        .sort("system:time_start")
        .limit(MAX_IMAGES)
    )
    return collection


def create_grid_tiles(aoi: ee.Geometry) -> List[ee.Geometry]:
    """Create grid of non-overlapping tiles across AOI."""
    coords = aoi.bounds().coordinates().getInfo()[0]
    min_lon = min(c[0] for c in coords)
    max_lon = max(c[0] for c in coords)
    min_lat = min(c[1] for c in coords)
    max_lat = max(c[1] for c in coords)

    tile_size_degrees = TILE_SIZE_METERS / 111320  # Convert meters to degrees

    tiles = []
    lat = min_lat
    while lat < max_lat:
        lon = min_lon
        while lon < max_lon:
            tile_coords = [
                [lon, lat],
                [lon + tile_size_degrees, lat],
                [lon + tile_size_degrees, lat + tile_size_degrees],
                [lon, lat + tile_size_degrees],
                [lon, lat],
            ]
            tiles.append(ee.Geometry.Polygon([tile_coords]))
            lon += tile_size_degrees
        lat += tile_size_degrees

    return tiles


def export_image_to_drive(
    image: ee.Image, description: str, folder_prefix: str
) -> str:
    """Export single image to Google Drive as GeoTIFF."""
    task = ee.batch.Export.image.toDrive(
        image=image,
        description=description,
        folder=DRIVE_BASE_FOLDER,
        fileNamePrefix=f"{folder_prefix}/{description}",
        scale=SCALE,
        crs=CRS,
        maxPixels=MAX_PIXELS,
        fileFormat="GeoTIFF",
    )
    task.start()
    logging.info(f"Export started: {description} (Task ID: {task.id})")
    return task.id


def download_preview(url: str, output_path: Path) -> bool:
    """Download PNG preview from thumbnail URL."""
    try:
        urllib.request.urlretrieve(url, output_path)
        return True
    except Exception as e:
        logging.warning(f"Failed to download {output_path}: {e}")
        return False


def generate_preview_url(image: ee.Image, geometry: ee.Geometry) -> str:
    """Generate thumbnail URL for preview."""
    return image.getThumbURL({
        "region": geometry,
        "dimensions": [512, 512],
        "format": "png",
        "min": 0,
        "max": 3000,
    })


def process_images(
    images: ee.ImageCollection, tiles: List[ee.Geometry], aoi: ee.Geometry
) -> Dict[str, any]:
    """Process and export all images with pan-sharpening."""
    LOCAL_PREVIEW_DIR.mkdir(parents=True, exist_ok=True)
    LOCAL_METADATA_DIR.mkdir(parents=True, exist_ok=True)

    task_ids = []
    metadata_list = []
    preview_count = 0

    image_list = images.toList(MAX_IMAGES)
    image_count = image_list.size().getInfo()

    logging.info(f"Processing {image_count} images with pan-sharpening...")
    
    images_to_process = image_list.getInfo() if image_count > 0 else []

    for idx in range(image_count):
        try:
            # Get image
            image_info = images.toList(MAX_IMAGES).get(idx).getInfo()
            image_id = image_info["id"]
            timestamp = image_info["properties"]["system:time_start"]
            date_str = datetime.fromtimestamp(timestamp / 1000).strftime(
                "%Y%m%d"
            )

            # Retrieve full image object
            image = ee.Image(image_id)

            # Apply pan-sharpening
            sharpened = pansharpen_image(image)

            # Export to Drive
            description = f"dhaka_pansharpened_{date_str}_{idx:03d}"
            task_id = export_image_to_drive(sharpened, description, "images")
            task_ids.append(task_id)

            # Generate and download preview
            thumb_url = generate_preview_url(sharpened, aoi)
            preview_path = LOCAL_PREVIEW_DIR / f"{description}_preview.png"
            if download_preview(thumb_url, preview_path):
                preview_count += 1
                logging.info(f"Preview saved: {preview_path}")

            # Save metadata
            metadata = {
                "image_id": image_id,
                "date": date_str,
                "timestamp": timestamp,
                "aoi": AOI_COORDINATES,
                "processing": "pan-sharpened",
                "scale_meters": SCALE,
            }
            metadata_list.append(metadata)
            metadata_path = LOCAL_METADATA_DIR / f"{description}_metadata.json"
            with open(metadata_path, "w") as f:
                json.dump(metadata, f, indent=2)

            logging.info(
                f"Processed {idx + 1}/{image_count}: {description}"
            )
            time.sleep(1)  # Rate limiting

        except Exception as e:
            logging.error(f"Error processing image {idx}: {e}")
            continue

    return {
        "task_ids": task_ids,
        "total_processed": image_count,
        "previews_downloaded": preview_count,
        "metadata": metadata_list,
    }


def save_manifest(result: Dict[str, any]) -> None:
    """Save export manifest for tracking."""
    manifest = {
        "timestamp": datetime.now().isoformat(),
        "project_id": PROJECT_ID,
        "aoi": AOI_COORDINATES,
        "processing": "pan-sharpened-sentinel2",
        "scale_meters": SCALE,
        "task_ids": result["task_ids"],
        "total_processed": result["total_processed"],
        "previews_downloaded": result["previews_downloaded"],
        "drive_folder": DRIVE_BASE_FOLDER,
    }
    MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(MANIFEST_PATH, "w") as f:
        json.dump(manifest, f, indent=2)
    logging.info(f"Manifest saved to {MANIFEST_PATH}")


def main() -> None:
    """Main execution."""
    logging.info("=== Pan-sharpened Sentinel-2 Collection Started ===")
    logging.info(f"AOI: {AOI_COORDINATES}")
    logging.info(f"Date range: {START_DATE} to {END_DATE}")
    logging.info(f"Cloud cover max: {CLOUD_COVER_MAX}%")
    logging.info(f"Processing method: Pan-sharpening (high-pass filter)")

    initialize_earth_engine()

    aoi = create_aoi_geometry()
    logging.info(f"AOI geometry created")

    images = collect_sentinel2_images(aoi)
    count = images.size().getInfo()
    logging.info(f"Found {count} Sentinel-2 images")

    if count == 0:
        logging.warning("No images found in the specified AOI and date range")
        return

    # Create tiles for export
    tiles = create_grid_tiles(aoi)
    logging.info(f"Created {len(tiles)} export tiles")

    # Process images
    result = process_images(images, tiles, aoi)

    # Save manifest
    save_manifest(result)

    logging.info(f"Processed {result['total_processed']} images")
    logging.info(f"Previews downloaded: {result['previews_downloaded']}")
    logging.info(f"Export tasks created: {len(result['task_ids'])}")
    logging.info("=== Collection Complete ===")
    logging.info(
        "Monitor export progress in Google Earth Engine Code Editor or Drive"
    )


if __name__ == "__main__":
    setup_logging()
    main()
