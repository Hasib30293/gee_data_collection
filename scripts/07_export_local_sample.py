"""
Export a manageable local Sentinel-2 sample tile.

The configured AOI covers all of Bangladesh, which is too large for the
Earth Engine direct-download API at 10 m resolution. This script keeps the
same project, date range, dataset, and cloud settings, but clips downloads to
a small tile inside the AOI and saves everything under data/.
"""

import sys
from pathlib import Path

import ee

sys.path.insert(0, str(Path(__file__).parent.parent))

from config.settings import *  # noqa: F403
from scripts.gee_utils import (
    calculate_ndbi,
    calculate_ndvi,
    calculate_ndwi,
    download_image_collection_local,
    download_image_local,
    get_collection_size,
    initialize_gee,
    mask_sentinel2_clouds,
)


SENTINEL2_BANDS = [
    "B1",
    "B2",
    "B3",
    "B4",
    "B5",
    "B6",
    "B7",
    "B8",
    "B8A",
    "B11",
    "B12",
]


def create_sample_aoi(size_degrees=0.05):
    """Create a small rectangle centered inside the configured AOI."""
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
    """Mask clouds while preserving timestamps used for filenames."""
    return mask_sentinel2_clouds(image).copyProperties(image, image.propertyNames())


def main():
    print("\n" + "=" * 60)
    print("LOCAL SAMPLE EXPORT TO data/")
    print("=" * 60)

    if not initialize_gee(project_id=GEE_PROJECT_ID):
        return False

    output_folder = Path(DATA_DIR) / "sentinel2_downloads"
    output_folder.mkdir(parents=True, exist_ok=True)
    print(f"Output folder: {output_folder}")

    aoi = create_sample_aoi()
    collection = (
        ee.ImageCollection(SATELLITE_DATASET)
        .filterBounds(aoi)
        .filterDate(START_DATE, END_DATE)
        .filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", CLOUD_COVER_THRESHOLD))
        .map(mask_clouds_keep_properties)
        .select(SENTINEL2_BANDS)
        .limit(MAX_IMAGES)
    )

    size = get_collection_size(collection)
    print(f"Images found for sample tile: {size}")
    if size == 0:
        return False

    median = collection.median().clip(aoi)
    downloads = []

    exports = [
        ("sentinel2_rgb_median_sample", median.select(BANDS_RGB)),
        ("sentinel2_all_bands_median_sample", median.select(SENTINEL2_BANDS)),
        ("ndvi_index_sample", calculate_ndvi(median)),
        ("ndbi_index_sample", calculate_ndbi(median)),
        ("ndwi_index_sample", calculate_ndwi(median)),
    ]

    for filename, image in exports:
        path = download_image_local(
            image=image,
            aoi=aoi,
            filename=filename,
            output_folder=output_folder,
            scale=EXPORT_SCALE,
            crs=EXPORT_CRS,
        )
        if path:
            downloads.append(path)

    downloads.extend(
        download_image_collection_local(
            collection=collection,
            aoi=aoi,
            prefix="image_sample",
            output_folder=output_folder,
            scale=EXPORT_SCALE,
            crs=EXPORT_CRS,
            limit=min(5, MAX_IMAGES),
        )
    )

    print("\nDownloaded files:")
    for path in downloads:
        local_path = Path(path)
        size_mb = local_path.stat().st_size / 1024 / 1024
        print(f"  {local_path.name} ({size_mb:.2f} MB)")

    return bool(downloads)


if __name__ == "__main__":
    sys.exit(0 if main() else 1)
