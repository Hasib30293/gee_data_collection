"""
Download a close Dhaka PNG preview from Google Earth Engine.

This uses Sentinel-2, so the native detail is 10 m per pixel. It cannot match
Google Maps-style sub-meter imagery or map labels.
"""

import sys
import urllib.request
from pathlib import Path

import ee

sys.path.insert(0, str(Path(__file__).parent.parent))

PROJECT_ID = "cedar-spring-496007-j8"
OUTPUT_DIR = Path("data") / "Dhaka_data"
OUTPUT_FILE = OUTPUT_DIR / "dhaka_badda_close_sentinel2.png"

# Al Sami Hospital / Middle Badda area.
CENTER_LAT = 23.78038
CENTER_LON = 90.42612

# Small close-view box around the point. Sentinel-2 is still native 10 m.
HALF_SIZE_DEGREES = 0.006
START_DATE = "2023-01-01"
END_DATE = "2024-12-31"
CLOUD_COVER_MAX = 5


def mask_sentinel2_clouds(image):
    qa = image.select("QA60")
    cloud_bit_mask = 1 << 10
    cirrus_bit_mask = 1 << 11
    mask = qa.bitwiseAnd(cloud_bit_mask).eq(0).And(
        qa.bitwiseAnd(cirrus_bit_mask).eq(0)
    )
    return image.updateMask(mask).divide(10000).copyProperties(
        image, image.propertyNames()
    )


def main():
    ee.Initialize(project=PROJECT_ID)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    region = ee.Geometry.Rectangle(
        [
            CENTER_LON - HALF_SIZE_DEGREES,
            CENTER_LAT - HALF_SIZE_DEGREES,
            CENTER_LON + HALF_SIZE_DEGREES,
            CENTER_LAT + HALF_SIZE_DEGREES,
        ]
    )

    image = (
        ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
        .filterBounds(region)
        .filterDate(START_DATE, END_DATE)
        .filter(ee.Filter.lte("CLOUDY_PIXEL_PERCENTAGE", CLOUD_COVER_MAX))
        .map(mask_sentinel2_clouds)
        .sort("CLOUDY_PIXEL_PERCENTAGE")
        .first()
        .clip(region)
    )

    rendered = image.select(["B4", "B3", "B2"]).visualize(
        bands=["B4", "B3", "B2"],
        min=0,
        max=0.3,
        gamma=1.2,
    )
    url = rendered.getThumbURL(
        {
            "region": region,
            "dimensions": 1024,
            "format": "png",
        }
    )

    urllib.request.urlretrieve(url, OUTPUT_FILE)
    print(f"Saved PNG: {OUTPUT_FILE}")
    print(f"Size: {OUTPUT_FILE.stat().st_size / 1024:.1f} KB")


if __name__ == "__main__":
    main()
