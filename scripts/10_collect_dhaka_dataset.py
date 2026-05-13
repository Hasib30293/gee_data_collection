"""
Collect 10 m Sentinel-2 Dhaka tiles from Google Earth Engine.

User-edit section:
    PROJECT_ID
    AOI_COORDINATES
    MAX_IMAGES

Outputs:
    Google Drive:
        dhaka_gee_dataset_images/*.tif RGB images
        dhaka_gee_dataset_masks/*.tif segmentation masks
        dhaka_gee_dataset_metadata/*.geojson metadata backup
    Local:
        data/dhaka_png_previews/*.png preview images
        data/dhaka_metadata_json/*.json metadata files

Note:
    Earth Engine image exports to Google Drive support GeoTIFF/TFRecord, not
    true PNG. PNG previews are therefore downloaded locally with getThumbURL.
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
except ImportError:  # pragma: no cover - fallback for minimal environments.
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
MAX_IMAGES = 500


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
BATCH_SIZE = 100
DRIVE_BASE_FOLDER = "dhaka_gee_dataset"
LOCAL_PREVIEW_DIR = Path("data") / "dhaka_png_previews"
LOCAL_METADATA_DIR = Path("data") / "dhaka_metadata_json"
MANIFEST_PATH = Path("data") / "dhaka_export_manifest.json"
LOG_PATH = Path("dhaka_collection.log")
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
            logging.info("Run: earthengine authenticate")
            raise


def load_manifest() -> Dict[str, bool]:
    if not MANIFEST_PATH.exists():
        return {}
    try:
        return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        logging.warning("Manifest is invalid; starting with an empty manifest.")
        return {}


def save_manifest(manifest: Dict[str, bool]) -> None:
    MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2), encoding="utf-8")


def create_aoi() -> ee.Geometry:
    return ee.Geometry.Rectangle(
        [
            AOI_COORDINATES["min_longitude"],
            AOI_COORDINATES["min_latitude"],
            AOI_COORDINATES["max_longitude"],
            AOI_COORDINATES["max_latitude"],
        ]
    )


def make_tile_bounds() -> List[Tuple[float, float, float, float]]:
    center_lat = (
        AOI_COORDINATES["min_latitude"] + AOI_COORDINATES["max_latitude"]
    ) / 2
    lat_step = TILE_SIZE_METERS / 111_320
    lon_step = TILE_SIZE_METERS / (111_320 * math.cos(math.radians(center_lat)))

    tiles = []
    lat = AOI_COORDINATES["min_latitude"]
    while lat + lat_step <= AOI_COORDINATES["max_latitude"]:
        lon = AOI_COORDINATES["min_longitude"]
        while lon + lon_step <= AOI_COORDINATES["max_longitude"]:
            tiles.append((lon, lat, lon + lon_step, lat + lat_step))
            lon += lon_step
        lat += lat_step
    return tiles


def mask_sentinel2_clouds(image: ee.Image) -> ee.Image:
    qa = image.select("QA60")
    cloud_bit_mask = 1 << 10
    cirrus_bit_mask = 1 << 11
    mask = qa.bitwiseAnd(cloud_bit_mask).eq(0).And(
        qa.bitwiseAnd(cirrus_bit_mask).eq(0)
    )
    return image.updateMask(mask).divide(10000).copyProperties(
        image, image.propertyNames()
    )


def add_indices(image: ee.Image) -> ee.Image:
    ndvi = image.normalizedDifference(["B8", "B4"]).rename("NDVI")
    ndbi = image.normalizedDifference(["B11", "B8"]).rename("NDBI")
    mndwi = image.normalizedDifference(["B3", "B11"]).rename("MNDWI")
    return image.addBands([ndvi, ndbi, mndwi])


def classify_mask(image: ee.Image) -> ee.Image:
    ndvi = image.select("NDVI")
    ndbi = image.select("NDBI")
    mndwi = image.select("MNDWI")
    brightness = image.select(BANDS_RGB).reduce(ee.Reducer.mean())

    tree = ndvi.gt(0.35)
    water = mndwi.gt(0.20).And(ndvi.lt(0.20))
    building = ndbi.gt(0.08).And(ndvi.lt(0.25)).And(mndwi.lt(0.05))
    road = brightness.gt(0.12).And(brightness.lt(0.35)).And(
        ndvi.lt(0.20)
    ).And(mndwi.lt(0.00)).And(ndbi.lte(0.08))

    return (
        ee.Image(0)
        .where(tree, 1)
        .where(building, 2)
        .where(road, 3)
        .where(water, 4)
        .rename("mask")
        .toByte()
    )


def season_for_image(image: ee.Image) -> ee.String:
    month = ee.Number(ee.Date(image.get("system:time_start")).get("month"))
    return ee.String(ee.Algorithms.If(month.gte(5).And(month.lte(10)), "wet", "dry"))


def season_from_month(month: int) -> str:
    return "wet" if 5 <= month <= 10 else "dry"


def build_collection(aoi: ee.Geometry) -> ee.ImageCollection:
    return (
        ee.ImageCollection(DATASET)
        .filterBounds(aoi)
        .filterDate(START_DATE, END_DATE)
        .filter(ee.Filter.lte("CLOUDY_PIXEL_PERCENTAGE", CLOUD_COVER_MAX))
        .map(mask_sentinel2_clouds)
        .map(add_indices)
        .sort("system:time_start")
    )


def start_task(task: ee.batch.Task, label: str) -> bool:
    try:
        task.start()
        logging.info("Started task: %s", label)
        time.sleep(TASK_DELAY_SECONDS)
        return True
    except Exception as exc:
        logging.error("Failed to start %s: %s", label, exc)
        logging.info("Sleeping before continuing to avoid quota pressure.")
        time.sleep(TASK_DELAY_SECONDS)
        return False


def export_rgb_tif(image: ee.Image, region: ee.Geometry, file_id: str) -> ee.batch.Task:
    rgb = image.select(BANDS_RGB).multiply(10000).toUint16()
    return ee.batch.Export.image.toDrive(
        image=rgb,
        description=f"{file_id}_rgb",
        folder=f"{DRIVE_BASE_FOLDER}_images",
        fileNamePrefix=file_id,
        region=region,
        scale=SCALE,
        crs=CRS,
        maxPixels=MAX_PIXELS,
        fileFormat="GeoTIFF",
    )


def export_mask_tif(mask: ee.Image, region: ee.Geometry, file_id: str) -> ee.batch.Task:
    return ee.batch.Export.image.toDrive(
        image=mask,
        description=f"{file_id}_mask",
        folder=f"{DRIVE_BASE_FOLDER}_masks",
        fileNamePrefix=f"{file_id}_mask",
        region=region,
        scale=SCALE,
        crs=CRS,
        maxPixels=MAX_PIXELS,
        fileFormat="GeoTIFF",
    )


def export_metadata(
    image: ee.Image,
    region: ee.Geometry,
    bounds: Tuple[float, float, float, float],
    file_id: str,
) -> ee.batch.Task:
    metadata = ee.Feature(
        region,
        {
            "file_id": file_id,
            "date": ee.Date(image.get("system:time_start")).format("YYYY-MM-dd"),
            "cloud_cover": image.get("CLOUDY_PIXEL_PERCENTAGE"),
            "season": season_for_image(image),
            "min_longitude": bounds[0],
            "min_latitude": bounds[1],
            "max_longitude": bounds[2],
            "max_latitude": bounds[3],
            "classes": "0=background,1=tree,2=building,3=road,4=water",
        },
    )
    return ee.batch.Export.table.toDrive(
        collection=ee.FeatureCollection([metadata]),
        description=f"{file_id}_metadata",
        folder=f"{DRIVE_BASE_FOLDER}_metadata",
        fileNamePrefix=f"{file_id}_metadata",
        fileFormat="GeoJSON",
    )


def download_png_preview(image: ee.Image, region: ee.Geometry, file_id: str) -> None:
    LOCAL_PREVIEW_DIR.mkdir(parents=True, exist_ok=True)
    output_path = LOCAL_PREVIEW_DIR / f"{file_id}.png"
    if output_path.exists():
        logging.info("Skipping existing PNG: %s", output_path)
        return

    rendered = image.select(BANDS_RGB).visualize(
        bands=BANDS_RGB,
        min=0,
        max=0.3,
        gamma=1.2,
    )
    url = rendered.getThumbURL(
        {
            "region": region,
            "dimensions": TILE_PIXELS,
            "format": "png",
        }
    )
    try:
        urllib.request.urlretrieve(url, output_path)
    except (urllib.error.URLError, TimeoutError) as exc:
        logging.error("PNG preview failed for %s: %s", file_id, exc)


def write_metadata_json(
    file_id: str,
    image_timestamp_ms: int,
    cloud_cover: float,
    bounds: Tuple[float, float, float, float],
) -> None:
    LOCAL_METADATA_DIR.mkdir(parents=True, exist_ok=True)
    output_path = LOCAL_METADATA_DIR / f"{file_id}.json"
    if output_path.exists():
        logging.info("Skipping existing metadata JSON: %s", output_path)
        return

    dt = datetime.utcfromtimestamp(image_timestamp_ms / 1000)
    metadata = {
        "file_id": file_id,
        "rgb_tif": f"{file_id}.tif",
        "png_preview": f"{file_id}.png",
        "mask_tif": f"{file_id}_mask.tif",
        "date": dt.strftime("%Y-%m-%d"),
        "cloud_cover": cloud_cover,
        "season": season_from_month(dt.month),
        "coordinates": {
            "min_longitude": bounds[0],
            "min_latitude": bounds[1],
            "max_longitude": bounds[2],
            "max_latitude": bounds[3],
        },
        "classes": {
            "0": "background",
            "1": "tree",
            "2": "building",
            "3": "road",
            "4": "water",
        },
        "source": {
            "dataset": DATASET,
            "scale": SCALE,
            "crs": CRS,
            "bands_rgb": BANDS_RGB,
        },
    }
    output_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")


def progress(iterable: Iterable, total: int, label: str) -> Iterable:
    if tqdm is not None:
        return tqdm(iterable, total=total, desc=label)
    logging.info("%s: %s items", label, total)
    return iterable


def main() -> None:
    setup_logging()
    logging.info("Starting Dhaka Sentinel-2 collection.")
    initialize_earth_engine()

    aoi = create_aoi()
    tiles = make_tile_bounds()
    if not tiles:
        raise RuntimeError("AOI is too small for a 256x256 tile at 10 m.")

    collection = build_collection(aoi)
    image_count = collection.size().getInfo()
    logging.info("Images after cloud/date/AOI filters: %s", image_count)
    logging.info("Grid tiles per image: %s", len(tiles))

    possible_samples = image_count * len(tiles)
    target_samples = min(MAX_IMAGES, possible_samples)
    logging.info("Target samples: %s", target_samples)

    image_list = collection.toList(image_count)
    image_timestamps = collection.aggregate_array("system:time_start").getInfo()
    image_cloud_covers = collection.aggregate_array("CLOUDY_PIXEL_PERCENTAGE").getInfo()
    manifest = load_manifest()
    submitted = 0
    sample_index = 0

    iterator = range(target_samples)
    for _ in progress(iterator, target_samples, "Submitting exports"):
        image_index = sample_index // len(tiles)
        tile_index = sample_index % len(tiles)
        bounds = tiles[tile_index]
        region = ee.Geometry.Rectangle(list(bounds))
        image = ee.Image(image_list.get(image_index)).clip(region)
        mask = classify_mask(image).clip(region)
        file_id = f"dhaka_s2_{sample_index:06d}"
        sample_index += 1

        if manifest.get(file_id):
            logging.info("Skipping already submitted sample: %s", file_id)
            continue

        download_png_preview(image, region, file_id)
        write_metadata_json(
            file_id=file_id,
            image_timestamp_ms=image_timestamps[image_index],
            cloud_cover=image_cloud_covers[image_index],
            bounds=bounds,
        )

        tasks = [
            (export_rgb_tif(image, region, file_id), f"{file_id}_rgb"),
            (export_mask_tif(mask, region, file_id), f"{file_id}_mask"),
            (export_metadata(image, region, bounds, file_id), f"{file_id}_metadata"),
        ]

        ok = True
        for task, label in tasks:
            ok = start_task(task, label) and ok

        if ok:
            manifest[file_id] = True
            save_manifest(manifest)
            submitted += 1

        if submitted > 0 and submitted % BATCH_SIZE == 0:
            logging.info("Submitted %s samples; pausing between batches.", submitted)
            time.sleep(TASK_DELAY_SECONDS)

    logging.info("Done. Newly submitted samples: %s", submitted)
    logging.info("Drive folders: %s_images, %s_masks, %s_metadata", DRIVE_BASE_FOLDER, DRIVE_BASE_FOLDER, DRIVE_BASE_FOLDER)
    logging.info("Local PNG previews: %s", LOCAL_PREVIEW_DIR)
    logging.info("Local metadata JSON: %s", LOCAL_METADATA_DIR)


if __name__ == "__main__":
    main()
