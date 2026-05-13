"""
Dhaka Sentinel-2 Dataset Exporter

Edit only:
    PROJECT_ID
    AOI_COORDINATES
    MAX_IMAGES

Outputs:
    Google Drive:
        dhaka_gee_dataset/images/*.tif
        dhaka_gee_dataset/masks/*.tif

    Local workspace:
        data/dhaka_dataset/previews/*.png
        data/dhaka_dataset/metadata/*.json
        dhaka_collection.log

Notes:
    Earth Engine batch exports support GeoTIFF/TFRecord for Drive image
    exports, not PNG or JSON. PNG previews and JSON metadata are therefore
    written locally while the training-grade RGB and mask GeoTIFFs are exported
    to Google Drive.
"""

import json
import logging
import time
import urllib.request
from datetime import datetime
from pathlib import Path

import ee
import geemap

try:
    from tqdm import tqdm
except ImportError:
    def tqdm(iterable, desc="Progress"):
        total = len(iterable)
        for index, item in enumerate(iterable, 1):
            print(f"{desc}: {index}/{total}")
            yield item


# ===================== USER SETTINGS: EDIT ONLY THESE =====================
PROJECT_ID = "cedar-spring-496007-j8"
AOI_COORDINATES = [90.35, 23.7, 90.45, 23.9]  # [min_lon, min_lat, max_lon, max_lat]
MAX_IMAGES = 500
# ========================================================================


DRIVE_ROOT = "dhaka_gee_dataset"
LOCAL_ROOT = Path("data") / "dhaka_dataset"
LOG_FILE = "dhaka_collection.log"

START_DATE = "2023-01-01"
END_DATE = "2024-12-31"
CLOUD_LIMIT = 5
SCALE = 10
CRS = "EPSG:4326"
MAX_PIXELS = 1e9
TILE_PIXELS = 256
TILE_SIZE_METERS = TILE_PIXELS * SCALE
EXPORT_DELAY_SECONDS = 30
MAX_TASKS_PER_BATCH = 100

RGB_BANDS = ["B4", "B3", "B2"]
S2_BANDS = ["B2", "B3", "B4", "B8", "B11", "QA60"]


def setup_logging():
    logging.basicConfig(
        filename=LOG_FILE,
        filemode="a",
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )
    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    console.setFormatter(logging.Formatter("%(message)s"))
    logging.getLogger().addHandler(console)


def initialize_earth_engine():
    try:
        ee.Initialize(project=PROJECT_ID)
        logging.info("Earth Engine initialized with project: %s", PROJECT_ID)
    except Exception as exc:
        logging.warning("Earth Engine initialization failed: %s", exc)
        logging.info("Starting authentication flow...")
        ee.Authenticate()
        ee.Initialize(project=PROJECT_ID)
        logging.info("Earth Engine initialized after authentication.")


def season_from_month(month):
    if month in [11, 12, 1, 2]:
        return "dry"
    if month in [6, 7, 8, 9, 10]:
        return "wet"
    if month in [3, 4, 5]:
        return "pre_monsoon"
    return "post_monsoon"


def mask_sentinel2_clouds(image):
    qa = image.select("QA60")
    cloud_bit_mask = 1 << 10
    cirrus_bit_mask = 1 << 11
    mask = qa.bitwiseAnd(cloud_bit_mask).eq(0).And(
        qa.bitwiseAnd(cirrus_bit_mask).eq(0)
    )
    return (
        image.updateMask(mask)
        .divide(10000)
        .copyProperties(image, image.propertyNames())
    )


def add_indices(image):
    ndvi = image.normalizedDifference(["B8", "B4"]).rename("NDVI")
    ndbi = image.normalizedDifference(["B11", "B8"]).rename("NDBI")
    mndwi = image.normalizedDifference(["B3", "B11"]).rename("MNDWI")
    return image.addBands([ndvi, ndbi, mndwi])


def build_segmentation_mask(image):
    ndvi = image.select("NDVI")
    ndbi = image.select("NDBI")
    mndwi = image.select("MNDWI")
    red = image.select("B4")
    green = image.select("B3")
    blue = image.select("B2")

    water = mndwi.gt(0.25)
    tree = ndvi.gt(0.35).And(water.Not())
    building = ndbi.gt(0.08).And(ndvi.lt(0.25)).And(water.Not())

    brightness = red.add(green).add(blue).divide(3)
    road = (
        brightness.gt(0.12)
        .And(ndvi.lt(0.2))
        .And(ndbi.gt(-0.05))
        .And(building.Not())
        .And(water.Not())
    )

    return (
        ee.Image(0)
        .where(tree, 1)
        .where(building, 2)
        .where(road, 3)
        .where(water, 4)
        .rename("class")
        .toByte()
    )


def create_tile_grid(aoi):
    projection = ee.Projection(CRS).atScale(SCALE)
    covering = aoi.coveringGrid(projection, TILE_SIZE_METERS)
    return covering.map(lambda feature: feature.intersection(aoi, 1))


def prepare_collection(aoi):
    raw = (
        ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
        .filterBounds(aoi)
        .filterDate(START_DATE, END_DATE)
        .filter(ee.Filter.lte("CLOUDY_PIXEL_PERCENTAGE", CLOUD_LIMIT))
        .select(S2_BANDS)
        .sort("system:time_start")
    )
    return raw.map(mask_sentinel2_clouds).map(add_indices)


def build_export_specs(collection, grid):
    images = collection.toList(collection.size())
    image_count = collection.size()
    tile_count = grid.size()
    total = image_count.multiply(tile_count).min(MAX_IMAGES)

    def spec_for_index(index):
        index = ee.Number(index)
        image_index = index.divide(tile_count).floor()
        tile_index = index.mod(tile_count)

        image = ee.Image(images.get(image_index))
        tile = ee.Feature(grid.toList(tile_count).get(tile_index))
        geom = tile.geometry()
        date = ee.Date(image.get("system:time_start"))
        date_text = date.format("YYYYMMdd")
        name = ee.String("dhaka_").cat(date_text).cat("_tile_").cat(tile_index.format("%03d"))

        centroid = geom.centroid(1).coordinates()
        metadata = ee.Dictionary(
            {
                "id": name,
                "date": date.format("YYYY-MM-dd"),
                "season": ee.Algorithms.If(
                    date.get("month").lte(2).Or(date.get("month").gte(11)),
                    "dry",
                    ee.Algorithms.If(
                        date.get("month").gte(6).And(date.get("month").lte(10)),
                        "wet",
                        ee.Algorithms.If(date.get("month").lte(5), "pre_monsoon", "post_monsoon"),
                    ),
                ),
                "cloud_cover": image.get("CLOUDY_PIXEL_PERCENTAGE"),
                "center_lon": centroid.get(0),
                "center_lat": centroid.get(1),
                "tile_index": tile_index,
            }
        )

        return ee.Feature(
            geom,
            {
                "name": name,
                "image_index": image_index,
                "tile_index": tile_index,
                "metadata": metadata,
            },
        )

    return ee.FeatureCollection(ee.List.sequence(0, total.subtract(1)).map(spec_for_index))


def existing_stem(path):
    return {item.stem for item in path.glob("*") if item.is_file()}


def start_drive_export(image, description, folder, region):
    task = ee.batch.Export.image.toDrive(
        image=image,
        description=description,
        folder=folder,
        fileNamePrefix=description,
        region=region,
        scale=SCALE,
        crs=CRS,
        maxPixels=MAX_PIXELS,
        fileFormat="GeoTIFF",
    )
    task.start()
    return task


def write_png_preview(rgb_image, region, output_path):
    rendered = rgb_image.visualize(bands=RGB_BANDS, min=0, max=0.3, gamma=1.2)
    url = rendered.getThumbURL(
        {
            "region": region,
            "dimensions": TILE_PIXELS,
            "format": "png",
        }
    )
    urllib.request.urlretrieve(url, output_path)


def export_dataset(collection, specs):
    image_list = collection.toList(collection.size())
    spec_items = specs.getInfo()["features"]

    preview_dir = LOCAL_ROOT / "previews"
    metadata_dir = LOCAL_ROOT / "metadata"
    preview_dir.mkdir(parents=True, exist_ok=True)
    metadata_dir.mkdir(parents=True, exist_ok=True)

    existing_previews = existing_stem(preview_dir)
    existing_metadata = existing_stem(metadata_dir)
    tasks_started = 0

    for batch_start in range(0, len(spec_items), MAX_TASKS_PER_BATCH):
        batch = spec_items[batch_start : batch_start + MAX_TASKS_PER_BATCH]
        logging.info("Starting batch %s-%s", batch_start + 1, batch_start + len(batch))

        for feature in tqdm(batch, desc="Exporting Dhaka tiles"):
            props = feature["properties"]
            name = props["name"]
            region = ee.Geometry(feature["geometry"])
            image = ee.Image(image_list.get(props["image_index"])).clip(region)
            rgb = image.select(RGB_BANDS)
            mask = build_segmentation_mask(image).clip(region)

            if name not in existing_previews:
                try:
                    write_png_preview(rgb, region, preview_dir / f"{name}.png")
                    existing_previews.add(name)
                except Exception as exc:
                    logging.error("PNG preview failed for %s: %s", name, exc)

            if name not in existing_metadata:
                with open(metadata_dir / f"{name}.json", "w", encoding="utf-8") as file:
                    json.dump(props["metadata"], file, indent=2)
                existing_metadata.add(name)

            try:
                start_drive_export(rgb, f"{name}_rgb", f"{DRIVE_ROOT}/images", region)
                time.sleep(EXPORT_DELAY_SECONDS)
                start_drive_export(mask, f"{name}_mask", f"{DRIVE_ROOT}/masks", region)
                tasks_started += 2
                logging.info("Started exports for %s", name)
                time.sleep(EXPORT_DELAY_SECONDS)
            except Exception as exc:
                logging.error("Drive export failed for %s: %s", name, exc)

        logging.info("Batch complete. Tasks started so far: %s", tasks_started)

    return tasks_started


def main():
    setup_logging()
    logging.info("Dhaka dataset export started.")
    logging.info("AOI: %s", AOI_COORDINATES)
    logging.info("MAX_IMAGES: %s", MAX_IMAGES)

    initialize_earth_engine()
    geemap.ee_initialize(project=PROJECT_ID)

    aoi = ee.Geometry.Rectangle(AOI_COORDINATES)
    grid = create_tile_grid(aoi)
    collection = prepare_collection(aoi)
    specs = build_export_specs(collection, grid)

    total_specs = specs.size().getInfo()
    logging.info("Prepared %s image-tile export specs.", total_specs)
    if total_specs == 0:
        logging.warning("No images found. Try widening date range or cloud threshold.")
        return

    tasks_started = export_dataset(collection, specs)
    logging.info("Done. Started %s Drive export tasks.", tasks_started)
    logging.info("Check Earth Engine Tasks and Google Drive folder: %s", DRIVE_ROOT)


if __name__ == "__main__":
    main()
