"""
Download the clearest available Dhaka PNG preview from GEE.

Primary source: Planet NICFI monthly basemaps, about 4.8 m pixels.
Fallback: Sentinel-2, 10 m pixels.
"""

import sys
import urllib.request
from pathlib import Path

import ee

sys.path.insert(0, str(Path(__file__).parent.parent))

PROJECT_ID = "cedar-spring-496007-j8"
OUTPUT_DIR = Path("data") / "Dhaka_data"
CENTER_LAT = 23.78038
CENTER_LON = 90.42612
HALF_SIZE_DEGREES = 0.004


def region():
    return ee.Geometry.Rectangle(
        [
            CENTER_LON - HALF_SIZE_DEGREES,
            CENTER_LAT - HALF_SIZE_DEGREES,
            CENTER_LON + HALF_SIZE_DEGREES,
            CENTER_LAT + HALF_SIZE_DEGREES,
        ]
    )


def save_png(image, bounds, output_path, bands, min_value, max_value, dimensions=2048):
    rendered = image.select(bands).visualize(
        bands=bands,
        min=min_value,
        max=max_value,
        gamma=1.1,
    )
    url = rendered.getThumbURL(
        {
            "region": bounds,
            "dimensions": dimensions,
            "format": "png",
        }
    )
    urllib.request.urlretrieve(url, output_path)


def download_nicfi(bounds):
    # Asia monthly tropical basemaps. Requires NICFI access in Earth Engine.
    collection = (
        ee.ImageCollection("projects/planet-nicfi/assets/basemaps/asia")
        .filterBounds(bounds)
        .filterDate("2024-01-01", "2024-12-31")
        .sort("system:time_start", False)
    )
    image = ee.Image(collection.first()).clip(bounds)
    output_path = OUTPUT_DIR / "dhaka_badda_clear_planet_nicfi.png"
    save_png(
        image=image,
        bounds=bounds,
        output_path=output_path,
        bands=["R", "G", "B"],
        min_value=64,
        max_value=5454,
    )
    return output_path


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


def download_sentinel2(bounds):
    image = (
        ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
        .filterBounds(bounds)
        .filterDate("2023-01-01", "2024-12-31")
        .filter(ee.Filter.lte("CLOUDY_PIXEL_PERCENTAGE", 5))
        .map(mask_sentinel2_clouds)
        .sort("CLOUDY_PIXEL_PERCENTAGE")
        .first()
        .clip(bounds)
    )
    output_path = OUTPUT_DIR / "dhaka_badda_best_sentinel2.png"
    save_png(
        image=image,
        bounds=bounds,
        output_path=output_path,
        bands=["B4", "B3", "B2"],
        min_value=0,
        max_value=0.3,
    )
    return output_path


def main():
    ee.Initialize(project=PROJECT_ID)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    bounds = region()

    try:
        path = download_nicfi(bounds)
        print(f"Saved clearer Planet/NICFI PNG: {path}")
        print(f"Size: {path.stat().st_size / 1024:.1f} KB")
    except Exception as exc:
        print(f"Planet/NICFI download failed: {exc}")
        path = download_sentinel2(bounds)
        print(f"Saved Sentinel-2 fallback PNG: {path}")
        print(f"Size: {path.stat().st_size / 1024:.1f} KB")


if __name__ == "__main__":
    main()
