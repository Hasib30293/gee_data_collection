"""
Download a rendered Sentinel-2 RGB PNG sample to data/.
"""

import sys
import urllib.request
from pathlib import Path

import ee

sys.path.insert(0, str(Path(__file__).parent.parent))

from config.settings import *  # noqa: F403
from scripts.gee_utils import initialize_gee, mask_sentinel2_clouds


def create_sample_aoi(size_degrees=0.05):
    center_lon = (AOI_BOUNDS["min_longitude"] + AOI_BOUNDS["max_longitude"]) / 2
    center_lat = (AOI_BOUNDS["min_latitude"] + AOI_BOUNDS["max_latitude"]) / 2
    half = size_degrees / 2
    return ee.Geometry.Rectangle(
        [
            center_lon - half,
            center_lat - half,
            center_lon + half,
            center_lat + half,
        ]
    )


def mask_clouds_keep_properties(image):
    return mask_sentinel2_clouds(image).copyProperties(image, image.propertyNames())


def main():
    if not initialize_gee(project_id=GEE_PROJECT_ID):
        return False

    output_folder = Path(DATA_DIR) / "sentinel2_downloads"
    output_folder.mkdir(parents=True, exist_ok=True)
    output_path = output_folder / "sentinel2_rgb_median_sample.png"

    aoi = create_sample_aoi()
    collection = (
        ee.ImageCollection(SATELLITE_DATASET)
        .filterBounds(aoi)
        .filterDate(START_DATE, END_DATE)
        .filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", CLOUD_COVER_THRESHOLD))
        .map(mask_clouds_keep_properties)
        .limit(MAX_IMAGES)
    )

    image = collection.median().clip(aoi).select(BANDS_RGB)
    rendered = image.visualize(bands=BANDS_RGB, min=0, max=0.3, gamma=VIS_PARAMS["gamma"])
    url = rendered.getThumbURL(
        {
            "region": aoi,
            "dimensions": 1024,
            "format": "png",
        }
    )

    urllib.request.urlretrieve(url, output_path)
    print(f"Downloaded PNG: {output_path}")
    print(f"Size: {output_path.stat().st_size / 1024:.1f} KB")
    return True


if __name__ == "__main__":
    sys.exit(0 if main() else 1)
