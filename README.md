# Google Earth Engine (GEE) Data Collection Project

Complete Python project for collecting, processing, and exporting satellite imagery from Google Earth Engine. Optimized for GAN and VLM training datasets.

## Features

- ✓ **GEE Authentication** - Secure OAuth2 authentication
- ✓ **Image Collection** - Sentinel-2 satellite imagery retrieval
- ✓ **Cloud Masking** - Automatic cloud detection and removal
- ✓ **Image Processing** - NDVI, NDBI, NDWI calculation
- ✓ **Visualization** - Interactive maps with geemap
- ✓ **Export to Drive** - Batch export to Google Drive
- ✓ **Configurable** - Environment-based settings

## Project Structure

```
gee_data_collection/
├── scripts/                      # Main Python scripts
│   ├── 01_authenticate.py       # GEE authentication
│   ├── 02_initialize.py         # GEE initialization
│   ├── 03_collect_images.py     # Image collection
│   ├── 04_process_images.py     # Image processing
│   ├── 05_visualize.py          # Visualization
│   ├── 06_export_to_drive.py    # Export to Google Drive
│   └── gee_utils.py             # Utility functions
├── config/
│   └── settings.py              # Configuration settings
├── notebooks/
│   └── visualization.ipynb      # Jupyter notebook for interactive visualization
├── data/                        # Local data storage
├── requirements.txt             # Python dependencies
├── .env.example                 # Environment variables template
├── .gitignore                   # Git ignore rules
└── README.md                    # This file
```

## Prerequisites

| Item | Version | Notes |
|------|---------|-------|
| Python | 3.6 - 3.12 | Python 3.13 not supported yet |
| Google Account | Any | Gmail or institutional email |
| GEE Account | - | Free at [signup.earthengine.google.com](https://signup.earthengine.google.com) |
| Internet Connection | - | Required for GEE access |

## Installation

### 1. Clone or Download Project

```bash
# Navigate to your projects directory
cd your_projects_folder
```

### 2. Create Virtual Environment

```bash
# Windows
python -m venv gee_env
gee_env\Scripts\activate

# macOS/Linux
python3 -m venv gee_env
source gee_env/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Settings

```bash
# Copy environment template
cp .env.example .env

# Edit .env with your settings
# - Set GEE_PROJECT_ID (from GEE Code Editor)
# - Adjust AOI bounds as needed
# - Update other parameters if desired
```

## Quick Start

### Step 1: Authenticate (First Time Only)

```bash
python scripts/01_authenticate.py
```
This opens your browser to authorize GEE access.

### Step 2: Initialize GEE

```bash
python scripts/02_initialize.py
```
Verifies connection with your GEE project.

### Step 3: Collect Images

```bash
python scripts/03_collect_images.py
```
Retrieves Sentinel-2 imagery for your area of interest.

### Step 4: Process Images

```bash
python scripts/04_process_images.py
```
Creates composites and calculates vegetation indices.

### Step 5: Visualize (Optional)

```bash
# Interactive map (if in Jupyter)
python scripts/05_visualize.py

# Or use Jupyter notebook
jupyter notebook notebooks/visualization.ipynb
```

### Step 6: Export to Google Drive

```bash
python scripts/06_export_to_drive.py
```
Exports processed images to your Google Drive folder.

## Configuration

### Environment Variables (.env)

```bash
# GEE Project
GEE_PROJECT_ID=ee-yourusername

# Area of Interest (Latitude/Longitude bounds)
AOI_MIN_LONGITUDE=88.0
AOI_MIN_LATITUDE=20.0
AOI_MAX_LONGITUDE=92.5
AOI_MAX_LATITUDE=26.5

# Data Collection
START_DATE=2023-01-01
END_DATE=2023-12-31
CLOUD_COVER_THRESHOLD=20
MAX_IMAGES=50

# Export Settings
EXPORT_SCALE=10              # meters (Sentinel-2 native)
EXPORT_CRS=EPSG:4326        # Lat/Lon
EXPORT_FORMAT=GeoTIFF
```

### Custom AOI (Area of Interest)

Edit `config/settings.py` or `.env` to change:
- **Latitude/Longitude bounds**
- **Date range**
- **Cloud cover threshold**
- **Number of images**

## Usage Examples

### Collect Images for Bangladesh

```python
from scripts.gee_utils import *
from config.settings import *

initialize_gee()
aoi = create_aoi_from_bounds(AOI_BOUNDS)
collection = ee.ImageCollection(SATELLITE_DATASET) \
    .filterBounds(aoi) \
    .filterDate('2023-01-01', '2023-12-31') \
    .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 20))
```

### Calculate Vegetation Index

```python
from scripts.gee_utils import calculate_ndvi, initialize_gee
import ee

initialize_gee()
image = ee.Image('COPERNICUS/S2_SR_HARMONIZED/20230615T040559_20230615T041557_T45RUI')
ndvi = calculate_ndvi(image)
```

### Export Custom Image

```python
from scripts.gee_utils import create_export_task, start_export_task
from config.settings import *

task = create_export_task(
    image=your_image,
    description='my_export',
    folder='GEE_Exports',
    aoi=aoi,
    scale=10
)
start_export_task(task)
```

## Troubleshooting

| Issue | Solution |
|-------|----------|
| `ModuleNotFoundError: earthengine-api` | Run: `pip install -r requirements.txt` |
| Authentication fails | Run: `python scripts/01_authenticate.py --force` |
| No images found | Check date range, cloud threshold, and AOI bounds |
| Map not displaying | Install: `pip install geemap` |
| Python 3.13 error | Use Python 3.12 or earlier |
| Google Drive folder not found | Create the folder in Google Drive first |

## For GAN+VLM Training

After downloading images from Google Drive:

1. **Organize by category:**
   ```
   data/
   ├── flood/
   ├── urban/
   ├── forest/
   └── agricultural/
   ```

2. **Resize images:**
   ```bash
   # To 256x256
   convert image.tif -resize 256x256 image_256.tif
   
   # To 128x128
   convert image.tif -resize 128x128 image_128.tif
   ```

3. **Create captions:**
   - Basic: `flood`, `urban`, `forest`
   - Enhanced: `Satellite view of flooded agricultural area`

4. **Use for training:**
   - GAN training: Pairs of image→label or style transfer
   - VLM fine-tuning: Image+caption pairs for vision-language models

## Supported Datasets

| Dataset | ID | Resolution | Bands |
|---------|----|-----------|----|
| Sentinel-2 | `COPERNICUS/S2_SR_HARMONIZED` | 10m | 11 bands |
| Landsat 8 | `USGS/LANDSAT_8_SR` | 30m | 11 bands |
| Landsat 9 | `USGS/LANDSAT_9_SR` | 30m | 11 bands |

## Common Sentinel-2 Bands

| Band | Name | Wavelength | Resolution |
|------|------|-----------|-----------|
| B2 | Blue | 490 nm | 10 m |
| B3 | Green | 560 nm | 10 m |
| B4 | Red | 665 nm | 10 m |
| B5 | Vegetation Edge | 705 nm | 20 m |
| B8 | NIR | 842 nm | 10 m |
| B11 | SWIR | 1610 nm | 20 m |
| B12 | SWIR | 2190 nm | 20 m |

## Useful Resources

- [GEE Documentation](https://developers.google.com/earth-engine/guides)
- [Sentinel-2 Info](https://sentinel.esa.int/web/sentinel/missions/sentinel-2)
- [geemap Documentation](https://geemap.org/)
- [GEE Tutorials](https://github.com/google/earthengine-api/tree/master/python/examples)

## License

MIT License - See LICENSE file for details

## Support

For issues, errors, or questions:
1. Check the Troubleshooting section
2. Review GEE documentation
3. Check error messages carefully
4. Verify your project ID and authentication

## Credits

Built for GAN+VLM training pipeline with satellite imagery from Google Earth Engine.

---

**Last Updated:** May 2026
**Python Version:** 3.6 - 3.12
**GEE API Version:** Latest
