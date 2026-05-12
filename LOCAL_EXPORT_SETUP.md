# Local Export Configuration

Your GEE data pipeline has been updated to **download satellite images directly to your laptop** instead of exporting to Google Drive.

## Changes Made

### 1. Configuration (.env)
- ✅ Updated `GEE_PROJECT_ID` to: `cedar-spring-496007-j8`
- ✅ Changed export target to local storage
- ✅ Local data folder: `data/sentinel2_downloads/`

### 2. Utility Functions (scripts/gee_utils.py)
Added new functions for local downloads:
- `download_image_local()` - Download single image
- `download_image_collection_local()` - Download multiple images

### 3. Export Script (scripts/06_export_to_drive.py)
Completely rewritten to:
- ❌ No longer exports to Google Drive
- ✅ Downloads directly to `data/sentinel2_downloads/` folder
- ✅ Exports RGB composite
- ✅ Exports all 11 bands
- ✅ Calculates and exports indices (NDVI, NDBI, NDWI)
- ✅ Downloads sample individual images

## File Structure

After running the pipeline, your data folder will be organized as:

```
data/
├── sentinel2_downloads/
│   ├── sentinel2_rgb_median.tif           (3 bands: RGB)
│   ├── sentinel2_all_bands_median.tif     (11 bands: full spectrum)
│   ├── ndvi_index.tif                     (Vegetation Index)
│   ├── ndbi_index.tif                     (Built-up Index)
│   ├── ndwi_index.tif                     (Water Index)
│   ├── image_00_20230101_000000.tif       (Individual images)
│   ├── image_01_20230115_000000.tif
│   └── ...
└── (your custom folders)
```

## Download Specifications

| File | Bands | Resolution | Use Case |
|------|-------|-----------|----------|
| RGB Median | 3 | 10m | Preview, visualization |
| All Bands | 11 | 10m | ML training, full spectrum |
| NDVI | 1 | 10m | Vegetation classification |
| NDBI | 1 | 10m | Urban/built-up detection |
| NDWI | 1 | 10m | Water/flood detection |
| Individual | 11 | 10m | Time-series analysis |

## Data Preparation for GAN+VLM

Once downloaded, prepare for training:

### Step 1: Organize by Category
```bash
data/
├── flood/
│   ├── image_001.tif
│   └── image_002.tif
├── urban/
│   ├── image_001.tif
│   └── image_002.tif
├── forest/
│   └── ...
└── agricultural/
    └── ...
```

### Step 2: Resize Images (Optional)
```bash
# Resize to 256x256 (for most GANs)
gdal_translate -outsize 256 256 input.tif output_256x256.tif

# Or use Python
from PIL import Image
img = Image.open('image.tif')
img_resized = img.resize((256, 256))
img_resized.save('image_256x256.tif')
```

### Step 3: Create Captions (For VLM)
```
flood_region_001.txt:
"Satellite view of flooded agricultural area with standing water, wet soil visible in red wavelength"

urban_region_001.txt:
"Urban settlement showing buildings, roads, and built structures with characteristic spectral signature"
```

### Step 4: Use in Training
Your dataset is now ready for:
- **GAN**: Image-to-image translation, style transfer
- **VLM**: Vision-Language Model fine-tuning with image-caption pairs
- **Classification**: Flood/Urban/Forest detection models

## Quick Commands

### After registration, run full pipeline:
```bash
# Activate environment
gee_env\Scripts\activate

# Run steps 2-6
python scripts/02_initialize.py
python scripts/03_collect_images.py
python scripts/04_process_images.py
python scripts/05_visualize.py
python scripts/06_export_to_drive.py
```

### Check download progress:
```bash
# Windows
dir data\sentinel2_downloads\
ls -lh data/sentinel2_downloads/  # On Mac/Linux
```

### File sizes to expect:
- RGB Median: 5-15 MB
- All Bands: 20-50 MB
- Each Index: 5-10 MB
- Individual Images: 20-50 MB each

## Storage Requirements

| Scenario | Size |
|----------|------|
| RGB + Indices only | ~50 MB |
| RGB + All Bands + Indices | ~150 MB |
| + 5 Individual Images | ~250-500 MB |
| Full collection (50 images) | ~1-2 GB |

## No Google Drive Required!

✅ Everything stays on your laptop  
✅ No authentication to Google Drive needed  
✅ Full control over data organization  
✅ Ready for offline use and training  

## Troubleshooting

### Downloads are slow?
- Check internet connection
- Images are being downloaded from GEE servers
- Typical: 5-30 MB/min depending on image size

### Disk space issues?
- Check available space: `df -h` (Mac/Linux) or `dir C:\` (Windows)
- Reduce MAX_IMAGES in .env (default: 50)
- Reduce time range (START_DATE, END_DATE)

### GeoTIFF viewers
- QGIS (free, recommended)
- ArcGIS (commercial)
- Geospatial Python: `rasterio`, `gdal`

## Next Steps

1. **Register your project** (if not done yet):
   https://console.cloud.google.com/earth-engine/configuration?project=cedar-spring-496007-j8

2. **Verify initialization**:
   ```bash
   python scripts/02_initialize.py
   ```

3. **Run collection pipeline**:
   ```bash
   python scripts/03_collect_images.py
   python scripts/04_process_images.py
   python scripts/06_export_to_drive.py
   ```

4. **Check your data**:
   ```bash
   ls -la data/sentinel2_downloads/
   ```

5. **Prepare for GAN+VLM training** (see organization steps above)

---

**Last Updated**: May 2026  
**Data Source**: Sentinel-2 Satellite (10m resolution)  
**Storage**: Local laptop  
**Ready for**: GAN training, VLM fine-tuning, Classification models
