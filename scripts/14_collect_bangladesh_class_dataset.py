"""
Collect a 2,000-image Bangladesh class dataset from Google Earth Engine.

Classes:
    tree, floods, wildfire, city

The script writes local PNG chips plus JSON metadata:
    data/New_data/bangladesh_2000_class_dataset/images/<class>/*.png
    data/New_data/bangladesh_2000_class_dataset/metadata/<class>/*.json
    data/New_data/bangladesh_2000_class_dataset/manifest.json

It is designed to be resumable. Re-run it and existing PNG/JSON pairs are
kept, then missing samples continue from the manifest count.
"""

from __future__ import annotations

import json
import logging
import math
import os
import random
import sys
import time
import urllib.request
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

import ee


PROJECT_ID = "cedar-spring-496007-j8"
DATASET = "COPERNICUS/S2_SR_HARMONIZED"
START_DATE = "2023-01-01"
END_DATE = "2024-12-31"
CLOUD_COVER_MAX = 8
BANDS_RGB = ["B4", "B3", "B2"]

CLASSES = ["city", "floods", "wildfire", "tree"]
TOTAL_IMAGES = int(os.getenv("BD_TOTAL_IMAGES", "2000"))
BASE_IMAGES_PER_CLASS = TOTAL_IMAGES // len(CLASSES)
CLASS_TARGETS = {
    class_name: BASE_IMAGES_PER_CLASS + (1 if idx < TOTAL_IMAGES % len(CLASSES) else 0)
    for idx, class_name in enumerate(CLASSES)
}

# Sentinel-2 RGB is 10 m. A ~2.56 km chip at 512 px provides a closer view
# while preserving native 10 m detail for crisp, clear samples.
CHIP_SIZE_METERS = int(os.getenv("BD_CHIP_SIZE_METERS", "2560"))
THUMBNAIL_PIXELS = int(os.getenv("BD_THUMBNAIL_PIXELS", "640"))
DOWNLOAD_SLEEP_SECONDS = 0.15
PANSHARP_STRENGTH = float(os.getenv("BD_PANSHARP_STRENGTH", "0.45"))
VIS_MIN = int(os.getenv("BD_VIS_MIN", "0"))
VIS_MAX = int(os.getenv("BD_VIS_MAX", "2500"))
VIS_GAMMA = float(os.getenv("BD_VIS_GAMMA", "1.05"))
MAX_ATTEMPTS_PER_CLASS = int(
    os.getenv("BD_MAX_ATTEMPTS_PER_CLASS", str(max(CLASS_TARGETS.values()) * 10))
)

OUTPUT_DIR = Path("data") / "New_data" / "bangladesh_2000_class_dataset"
IMAGE_DIR = OUTPUT_DIR / "images"
METADATA_DIR = OUTPUT_DIR / "metadata"
MANIFEST_PATH = OUTPUT_DIR / "manifest.json"
LOG_PATH = Path("bangladesh_2000_class_collection.log")

BANGLADESH_BOUNDS = {
    "min_lat": 20.75,
    "max_lat": 26.65,
    "min_lon": 88.00,
    "max_lon": 92.70,
}


@dataclass(frozen=True)
class Region:
    key: str
    label: str
    min_lat: float
    max_lat: float
    min_lon: float
    max_lon: float


REGIONS: Dict[str, List[Region]] = {
    "tree": [
        Region("sundarbans_west", "Sundarbans mangrove forest", 21.82, 22.42, 89.05, 89.70),
        Region("sundarbans_east", "Sundarbans mangrove forest", 21.75, 22.45, 89.70, 90.28),
        Region("sylhet_forest", "Sylhet forest and tea-garden tree cover", 24.78, 25.20, 91.80, 92.35),
        Region("chittagong_hill_tracts", "Chittagong Hill Tracts forest", 21.65, 23.35, 91.75, 92.65),
        Region("madhupur_forest", "Madhupur sal forest", 24.25, 24.72, 90.00, 90.25),
    ],
    "floods": [
        Region("haor_sunamganj", "Sunamganj haor monsoon floodplain", 24.55, 25.18, 90.95, 91.55),
        Region("haor_kishoreganj", "Kishoreganj haor monsoon floodplain", 24.20, 24.70, 90.70, 91.20),
        Region("jamuna_floodplain", "Jamuna river floodplain", 23.80, 24.85, 89.45, 90.05),
        Region("padma_floodplain", "Padma river floodplain", 23.20, 24.05, 89.10, 90.30),
        Region("meghna_floodplain", "Lower Meghna floodplain", 22.70, 23.55, 90.45, 91.15),
        Region("barisal_delta", "Barisal delta wet floodplain", 22.20, 22.85, 90.05, 90.75),
    ],
    "city": [
        Region("dhaka", "Dhaka dense city", 23.68, 23.91, 90.32, 90.55),
        Region("chattogram", "Chattogram city and port", 22.22, 22.45, 91.75, 92.02),
        Region("khulna", "Khulna city", 22.75, 22.90, 89.45, 89.62),
        Region("rajshahi", "Rajshahi city", 24.32, 24.45, 88.52, 88.68),
        Region("sylhet_city", "Sylhet city", 24.84, 24.96, 91.82, 92.00),
        Region("barisal_city", "Barisal city", 22.65, 22.78, 90.25, 90.42),
        Region("rangpur", "Rangpur city", 25.68, 25.84, 88.55, 88.72),
        Region("mymensingh", "Mymensingh city", 24.68, 24.83, 90.32, 90.48),
        Region("comilla", "Cumilla city", 23.40, 23.52, 91.12, 91.28),
        Region("narayanganj", "Narayanganj city", 23.58, 23.72, 90.45, 90.58),
    ],
    "wildfire": [
        Region("chittagong_hills", "Chittagong Hill Tracts dry forest", 21.65, 23.35, 91.75, 92.65),
        Region("coxsbazar", "Cox's Bazar-Teknaf dry scrub", 20.84, 21.20, 92.10, 92.35),
        Region("madhupur", "Madhupur sal forest dry season", 24.25, 24.72, 90.00, 90.25),
        Region("barind", "Barind tract dry woodland", 24.30, 25.15, 88.30, 89.20),
        Region("sylhet_hills", "Sylhet hill forest dry season", 24.80, 25.30, 91.80, 92.40),
    ],
}

CLASS_DATE_WINDOWS = {
    "tree": (START_DATE, END_DATE),
    "floods": ("2023-06-01", "2024-10-31"),
    "wildfire": ("2023-11-01", "2024-04-30"),
    "city": (START_DATE, END_DATE),
}


def setup_logging() -> None:
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
        ee.Initialize(project=PROJECT_ID)
    except Exception as exc:
        raise RuntimeError(
            "Earth Engine is not authenticated for this Python environment. "
            "Run `earthengine authenticate`, then rerun this script."
        ) from exc


def chip_geometry(lat: float, lon: float, size_meters: int = CHIP_SIZE_METERS) -> ee.Geometry:
    half = size_meters / 2
    lat_delta = half / 111_320
    lon_delta = half / (111_320 * math.cos(math.radians(lat)))
    return ee.Geometry.Rectangle(
        [lon - lon_delta, lat - lat_delta, lon + lon_delta, lat + lat_delta],
        proj="EPSG:4326",
        geodesic=False,
    )


def random_point(region: Region) -> Tuple[float, float]:
    lat = random.uniform(region.min_lat, region.max_lat)
    lon = random.uniform(region.min_lon, region.max_lon)
    return lat, lon


def pansharpen_image(image: ee.Image) -> ee.Image:
    rgb = image.select(BANDS_RGB)
    pan = image.select("B8")
    kernel = ee.Kernel.gaussian(radius=2, sigma=1)
    highpass = pan.subtract(pan.convolve(kernel))
    return rgb.add(highpass.multiply(PANSHARP_STRENGTH)).clamp(0, 3000)


def image_with_scores(image: ee.Image) -> ee.Image:
    ndvi = image.normalizedDifference(["B8", "B4"]).rename("ndvi")
    ndwi = image.normalizedDifference(["B3", "B8"]).rename("ndwi")
    ndbi = image.normalizedDifference(["B11", "B8"]).rename("ndbi")
    nbr = image.normalizedDifference(["B8", "B12"]).rename("nbr")
    return image.addBands([ndvi, ndwi, ndbi, nbr])


def best_sentinel_image(aoi: ee.Geometry, class_name: str) -> ee.Image | None:
    start_date, end_date = CLASS_DATE_WINDOWS[class_name]
    collection = (
        ee.ImageCollection(DATASET)
        .filterBounds(aoi)
        .filterDate(start_date, end_date)
        .filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", CLOUD_COVER_MAX))
        .sort("CLOUDY_PIXEL_PERCENTAGE")
        .limit(12)
    )
    if collection.size().getInfo() == 0:
        return None
    return ee.Image(collection.first())


def class_quality(image: ee.Image, aoi: ee.Geometry, class_name: str) -> Tuple[bool, Dict[str, float]]:
    scored = image_with_scores(image)
    stats = scored.select(["ndvi", "ndwi", "ndbi", "nbr"]).reduceRegion(
        reducer=ee.Reducer.mean(),
        geometry=aoi,
        scale=20,
        maxPixels=1e8,
        bestEffort=True,
    ).getInfo()
    ndvi = float(stats.get("ndvi") or -1)
    ndwi = float(stats.get("ndwi") or -1)
    ndbi = float(stats.get("ndbi") or -1)
    nbr = float(stats.get("nbr") or -1)

    if class_name == "tree":
        ok = ndvi >= 0.42
    elif class_name == "floods":
        ok = ndwi >= -0.22 and ndbi <= 0.10
    elif class_name == "city":
        ok = ndbi >= -0.12 and ndvi <= 0.45
    elif class_name == "wildfire":
        ok = nbr <= 0.25 and ndvi >= 0.1 and ndwi <= 0.1
    else:
        # Active fire is rare at Sentinel-2 overpass time. Use dry vegetation
        # chips from fire-prone regions and keep scores for downstream review.
        ok = ndvi >= 0.15 and ndwi <= 0.10

    return ok, {
        "ndvi": round(ndvi, 4),
        "ndwi": round(ndwi, 4),
        "ndbi": round(ndbi, 4),
        "nbr": round(nbr, 4),
    }


def existing_count(class_name: str) -> int:
    class_dir = IMAGE_DIR / class_name
    return len(list(class_dir.glob("*.png"))) if class_dir.exists() else 0


def next_index(class_name: str) -> int:
    class_dir = IMAGE_DIR / class_name
    if not class_dir.exists():
        return 0
    indices = []
    for path in class_dir.glob(f"{class_name}_*.png"):
        try:
            indices.append(int(path.stem.split("_")[-1]))
        except ValueError:
            continue
    return max(indices) + 1 if indices else 0


def write_json(path: Path, payload: Dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)


def download_png(image: ee.Image, aoi: ee.Geometry, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    url = pansharpen_image(image).getThumbURL(
        {
            "region": aoi,
            "dimensions": [THUMBNAIL_PIXELS, THUMBNAIL_PIXELS],
            "format": "png",
            "min": VIS_MIN,
            "max": VIS_MAX,
            "gamma": VIS_GAMMA,
        }
    )
    urllib.request.urlretrieve(url, output_path)


def collect_class(class_name: str) -> Dict:
    target = CLASS_TARGETS[class_name]
    regions = REGIONS[class_name]
    start_idx = next_index(class_name)
    current = existing_count(class_name)
    attempts = 0
    downloaded = 0

    logging.info("")
    logging.info("=" * 72)
    logging.info("Collecting class '%s' (%s/%s already present)", class_name, current, target)
    logging.info("=" * 72)

    while current < target and attempts < MAX_ATTEMPTS_PER_CLASS:
        attempts += 1
        sample_idx = start_idx + downloaded
        region = regions[sample_idx % len(regions)]
        lat, lon = random_point(region)
        aoi = chip_geometry(lat, lon)

        try:
            image = best_sentinel_image(aoi, class_name)
            if image is None:
                continue

            ok, scores = class_quality(image, aoi, class_name)
            if not ok:
                continue

            timestamp = image.get("system:time_start").getInfo()
            date_str = datetime.fromtimestamp(timestamp / 1000).strftime("%Y%m%d")
            cloud_pct = image.get("CLOUDY_PIXEL_PERCENTAGE").getInfo()
            image_id = image.get("system:id").getInfo()
            filename = f"{class_name}_{sample_idx:04d}"
            png_path = IMAGE_DIR / class_name / f"{filename}.png"
            metadata_path = METADATA_DIR / class_name / f"{filename}.json"

            if png_path.exists() and metadata_path.exists():
                current += 1
                continue

            download_png(image, aoi, png_path)
            metadata = {
                "class": class_name,
                "index": sample_idx,
                "region_key": region.key,
                "region_label": region.label,
                "latitude": round(lat, 7),
                "longitude": round(lon, 7),
                "chip_size_meters": CHIP_SIZE_METERS,
                "thumbnail_pixels": THUMBNAIL_PIXELS,
                "dataset": DATASET,
                "image_id": image_id,
                "date": date_str,
                "cloud_percentage": cloud_pct,
                "scores": scores,
                "processing": "pan-sharpened Sentinel-2 RGB thumbnail",
            }
            write_json(metadata_path, metadata)

            current += 1
            downloaded += 1
            if current % 25 == 0 or current == target:
                logging.info("%s: %s/%s complete", class_name, current, target)
            time.sleep(DOWNLOAD_SLEEP_SECONDS)

        except Exception as exc:
            logging.warning("%s attempt %s failed: %s", class_name, attempts, exc)
            time.sleep(1)

    return {
        "class": class_name,
        "target": target,
        "existing_before_run": start_idx,
        "downloaded_this_run": downloaded,
        "available_after_run": existing_count(class_name),
        "attempts": attempts,
        "complete": existing_count(class_name) >= target,
    }


def save_manifest(results: Iterable[Dict]) -> None:
    results = list(results)
    manifest = {
        "timestamp": datetime.now().isoformat(),
        "project_id": PROJECT_ID,
        "country": "Bangladesh",
        "total_target": TOTAL_IMAGES,
        "classes": CLASSES,
        "class_targets": CLASS_TARGETS,
        "chip_size_meters": CHIP_SIZE_METERS,
        "thumbnail_pixels": THUMBNAIL_PIXELS,
        "cloud_cover_max": CLOUD_COVER_MAX,
        "date_range": {"start": START_DATE, "end": END_DATE},
        "output_dir": str(OUTPUT_DIR),
        "results": results,
        "total_available": sum(existing_count(c) for c in CLASSES),
    }
    write_json(MANIFEST_PATH, manifest)


def main() -> None:
    random.seed(20260516)
    setup_logging()
    logging.info("Bangladesh %s-image class dataset collection started", TOTAL_IMAGES)
    logging.info("Output: %s", OUTPUT_DIR)
    initialize_earth_engine()

    for class_name in CLASSES:
        (IMAGE_DIR / class_name).mkdir(parents=True, exist_ok=True)
        (METADATA_DIR / class_name).mkdir(parents=True, exist_ok=True)

    results = []
    for class_name in CLASSES:
        result = collect_class(class_name)
        results.append(result)
        save_manifest(results)

    save_manifest(results)
    logging.info("")
    logging.info("=" * 72)
    logging.info("Collection finished. Total PNGs available: %s", sum(existing_count(c) for c in CLASSES))
    logging.info("Manifest: %s", MANIFEST_PATH)
    logging.info("=" * 72)


if __name__ == "__main__":
    main()
