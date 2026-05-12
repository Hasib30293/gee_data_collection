"""
Download Sentinel-2 RGB PNG images for the Dhaka region.
"""

import sys
import urllib.request
from datetime import datetime
from pathlib import Path

import ee

sys.path.insert(0, str(Path(__file__).parent.parent))

from config.settings import *  # noqa: F403
from scripts.gee_utils import initialize_gee, mask_sentinel2_clouds


DHAKA_BOUNDS = {
    "min_longitude": 90.25,
    "min_latitude": 23.65,
    "max_longitude": 90.55,
    "max_latitude": 23.90,
}


def create_aoi(bounds):
    return ee.Geometry.Rectangle(
        [
            bounds["min_longitude"],
            bounds["min_latitude"],
            bounds["max_longitude"],
            bounds["max_latitude"],
        ]
    )


def mask_clouds_keep_properties(image):
    return mask_sentinel2_clouds(image).copyProperties(image, image.propertyNames())


def image_date(image):
    timestamp = image.getNumber("system:time_start").getInfo()
    if timestamp is None:
        return "unknown_date"
    return datetime.fromtimestamp(timestamp / 1000).strftime("%Y%m%d_%H%M%S")


def download_png(image, aoi, output_path):
    rendered = image.select(BANDS_RGB).visualize(
        bands=BANDS_RGB,
        min=0,
        max=0.3,
        gamma=VIS_PARAMS["gamma"],
    )
    url = rendered.getThumbURL(
        {
            "region": aoi,
            "dimensions": 1024,
            "format": "png",
        }
    )
    urllib.request.urlretrieve(url, output_path)


def main():
    print("\n" + "=" * 60)
    print("DHAKA SENTINEL-2 PNG DOWNLOAD")
    print("=" * 60)

    if not initialize_gee(project_id=GEE_PROJECT_ID):
        return False

    output_folder = Path(DATA_DIR) / "dhaka_png"
    output_folder.mkdir(parents=True, exist_ok=True)
    print(f"Output folder: {output_folder}")

    aoi = create_aoi(DHAKA_BOUNDS)
    collection = (
        ee.ImageCollection(SATELLITE_DATASET)
        .filterBounds(aoi)
        .filterDate(START_DATE, END_DATE)
        .filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", CLOUD_COVER_THRESHOLD))
        .map(mask_clouds_keep_properties)
        .sort("system:time_start")
        .limit(MAX_IMAGES)
    )

    size = collection.size().getInfo()
    print(f"Images available after filters: {size}")
    if size == 0:
        return False

    image_list = collection.toList(size)
    downloaded = []

    for index in range(size):
        try:
            image = ee.Image(image_list.get(index)).clip(aoi)
            date_str = image_date(image)
            output_path = output_folder / f"dhaka_sentinel2_{index:03d}_{date_str}.png"

            print(f"[{index + 1}/{size}] Downloading {output_path.name}")
            download_png(image, aoi, output_path)
            downloaded.append(output_path)
        except Exception as exc:
            print(f"  Failed image {index}: {exc}")

    print("\nDownloaded PNG files:")
    for path in downloaded:
        print(f"  {path.name} ({path.stat().st_size / 1024:.1f} KB)")

    print(f"\nTotal PNGs downloaded: {len(downloaded)}")
    return bool(downloaded)


if __name__ == "__main__":
    sys.exit(0 if main() else 1)
