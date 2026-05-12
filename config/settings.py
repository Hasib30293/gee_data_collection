"""
GEE Data Collection - Configuration Settings
"""

import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# ============= GEE Project Configuration =============
GEE_PROJECT_ID = os.getenv('GEE_PROJECT_ID', 'ee-yourusername')

# ============= Google Drive Configuration =============
GOOGLE_DRIVE_FOLDER = os.getenv('GOOGLE_DRIVE_FOLDER', 'GEE_Exports')

# ============= Local Export Configuration =============
LOCAL_DATA_FOLDER = os.getenv('LOCAL_DATA_FOLDER', 'data')
EXPORT_LOCAL = os.getenv('EXPORT_LOCAL', 'True').lower() == 'true'

# ============= Area of Interest (AOI) =============
# Default: Bangladesh region
AOI_BOUNDS = {
    'min_longitude': float(os.getenv('AOI_MIN_LONGITUDE', 88.0)),
    'min_latitude': float(os.getenv('AOI_MIN_LATITUDE', 20.0)),
    'max_longitude': float(os.getenv('AOI_MAX_LONGITUDE', 92.5)),
    'max_latitude': float(os.getenv('AOI_MAX_LATITUDE', 26.5))
}

# ============= Collection Parameters =============
START_DATE = os.getenv('START_DATE', '2023-01-01')
END_DATE = os.getenv('END_DATE', '2023-12-31')
CLOUD_COVER_THRESHOLD = int(os.getenv('CLOUD_COVER_THRESHOLD', 20))
MAX_IMAGES = int(os.getenv('MAX_IMAGES', 50))

# ============= Export Parameters =============
EXPORT_SCALE = int(os.getenv('EXPORT_SCALE', 10))
EXPORT_CRS = os.getenv('EXPORT_CRS', 'EPSG:4326')
EXPORT_FORMAT = os.getenv('EXPORT_FORMAT', 'GeoTIFF')
MAX_PIXELS = 1e9

# ============= Image Collection Settings =============
SATELLITE_DATASET = os.getenv('SATELLITE_DATASET', 'COPERNICUS/S2_SR_HARMONIZED')

# RGB Bands for Sentinel-2
BANDS_RGB = ['B4', 'B3', 'B2']  # Red, Green, Blue

# ============= Visualization Parameters =============
VIS_PARAMS = {
    'bands': BANDS_RGB,
    'min': 0,
    'max': 3000,
    'gamma': float(os.getenv('VIS_GAMMA', 1.2))
}

# ============= Categories for GAN+VLM Training =============
CATEGORIES = ['flood', 'urban', 'forest', 'agricultural', 'water', 'barren']

# ============= Image Resizing for ML =============
RESIZE_DIMENSIONS = [256, 128]  # pixels

# ============= Paths =============
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS_DIR = os.path.join(BASE_DIR, 'scripts')
DATA_DIR = os.path.join(BASE_DIR, 'data')
CONFIG_DIR = os.path.join(BASE_DIR, 'config')
NOTEBOOKS_DIR = os.path.join(BASE_DIR, 'notebooks')

# Create directories if they don't exist
os.makedirs(DATA_DIR, exist_ok=True)
