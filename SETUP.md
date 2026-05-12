# Google Earth Engine Project - Setup Instructions

Complete step-by-step guide to set up the GEE data collection project.

## Prerequisites Check

Before starting, verify you have:

- ✓ **Windows, macOS, or Linux** - Any modern OS works
- ✓ **Google Account** - Gmail or institutional email
- ✓ **GEE Account** - Register at https://signup.earthengine.google.com (free)
- ✓ **VS Code** - Download from https://code.visualstudio.com
- ✓ **Python 3.6-3.12** - Download from https://www.python.org (NOT 3.13)
- ✓ **Internet Connection** - Required for GEE access

## Step 1: Verify Python Installation

Open a terminal and check your Python version:

```bash
# Windows
python --version

# macOS/Linux
python3 --version
```

You should see: `Python 3.x.x` where x is 6-12.

**If not installed:** Download from https://www.python.org

## Step 2: Open Project in VS Code

1. Open this folder in VS Code
   - File → Open Folder → Select `gee_data_collection`
2. Open Terminal: Ctrl + ` (backtick)

## Step 3: Create Virtual Environment

In the VS Code terminal, run:

### Windows:
```bash
python -m venv gee_env
gee_env\Scripts\activate
```

### macOS/Linux:
```bash
python3 -m venv gee_env
source gee_env/bin/activate
```

**Success indicator:** Your terminal should show `(gee_env)` at the beginning of each line.

## Step 4: Install Dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

This installs:
- `earthengine-api` - Main GEE library
- `geemap` - Interactive mapping
- `jupyter` - Notebook support
- `numpy, pandas` - Data processing
- And more...

**Expected time:** 2-5 minutes

**Success indicator:** Terminal shows `Successfully installed...` with no errors.

## Step 5: Configure Your Project

### Create .env file:

```bash
# Copy the template
cp .env.example .env
```

### Edit .env file:

1. Open `.env` in VS Code
2. Find your GEE Project ID:
   - Go to https://code.earthengine.google.com
   - Click your profile picture (top right)
   - Click "Project Info"
   - Copy the Project ID (looks like: `ee-yourusername`)
3. Replace `ee-yourusername` with your actual project ID
4. Adjust other parameters if needed:
   - `AOI_*` - Area boundaries (currently set to Bangladesh)
   - `START_DATE`, `END_DATE` - Date range
   - `CLOUD_COVER_THRESHOLD` - Maximum cloud cover (%)

Save the file.

## Step 6: First-Time Authentication

```bash
python scripts/01_authenticate.py
```

**What happens:**
1. Terminal shows: "Press any key to continue..."
2. Your default browser opens
3. Sign in with your Google account
4. Grant permission to Google Earth Engine
5. Terminal shows: "✓ Google Earth Engine authentication successful!"

**Note:** This only happens once. The credentials are saved securely.

## Step 7: Test GEE Initialization

```bash
python scripts/02_initialize.py
```

**Success output:**
```
✓ Initialized with project: ee-yourusername
✓ Earth Engine initialized successfully
```

## Step 8: Run the Complete Workflow

```bash
python main.py
```

This runs the entire pipeline:
1. Collects satellite images
2. Processes them
3. Calculates indices
4. Exports to Google Drive

**What to expect:**
- Takes 2-10 minutes
- Shows progress messages
- Creates export tasks

## Step 9: Access Results

### Download from Google Drive:

1. Open Google Drive: https://drive.google.com
2. Find folder: `GEE_Exports`
3. Download `.tif` files

### Or run individual steps:

```bash
python scripts/03_collect_images.py   # Just collect
python scripts/04_process_images.py   # Just process
python scripts/05_visualize.py        # View on map
python scripts/06_export_to_drive.py  # Just export
```

## Step 10 (Optional): Interactive Visualization

For interactive maps and detailed visualization:

```bash
jupyter notebook notebooks/visualization.ipynb
```

This opens Jupyter with interactive maps, statistics, and visualization options.

## Troubleshooting

### "ModuleNotFoundError: earthengine-api"

```bash
# Make sure your virtual environment is activated
# Then reinstall
pip install -r requirements.txt
```

### "Authentication failed"

```bash
# Force re-authentication
python -c "import ee; ee.Authenticate(force=True)"
```

### "No images found"

Edit `.env` and try:
- Longer date range
- Higher cloud cover threshold (e.g., 50 instead of 20)
- Different area of interest

### "Python 3.13 not supported"

Install Python 3.12 or earlier:
```bash
python3.12 --version  # Check if installed
# Or download from https://www.python.org
```

### "Port already in use" (Jupyter)

```bash
jupyter notebook notebooks/visualization.ipynb --port 8889
```

## File Structure

```
gee_data_collection/
├── main.py                      ← Start here
├── scripts/
│   ├── 01_authenticate.py      ← First authentication
│   ├── 02_initialize.py        ← Initialize GEE
│   ├── 03_collect_images.py    ← Get satellite data
│   ├── 04_process_images.py    ← Process & analyze
│   ├── 05_visualize.py         ← View on map
│   ├── 06_export_to_drive.py   ← Export results
│   └── gee_utils.py            ← Helper functions
├── config/
│   └── settings.py             ← Configuration
├── notebooks/
│   └── visualization.ipynb     ← Interactive notebook
├── .env                        ← Your settings (create from .env.example)
├── .env.example                ← Template
├── requirements.txt            ← Dependencies
├── README.md                   ← Full documentation
└── SETUP.md                    ← This file
```

## Quick Reference Commands

```bash
# Activate environment
gee_env\Scripts\activate           # Windows
source gee_env/bin/activate        # Mac/Linux

# First time setup
python scripts/01_authenticate.py
python scripts/02_initialize.py

# Run workflow
python main.py

# Run individual steps
python scripts/03_collect_images.py
python scripts/04_process_images.py
python scripts/06_export_to_drive.py

# Interactive visualization
jupyter notebook notebooks/visualization.ipynb

# Install more packages (if needed)
pip install package_name

# Deactivate environment
deactivate
```

## Useful Resources

- **GEE Documentation:** https://developers.google.com/earth-engine
- **Sentinel-2 Info:** https://sentinel.esa.int
- **geemap Docs:** https://geemap.org/
- **Python Docs:** https://docs.python.org/3/

## Next Steps

1. ✓ Create virtual environment
2. ✓ Install dependencies
3. ✓ Authenticate
4. ✓ Run main.py
5. Download data from Google Drive
6. Resize images (256×256 or 128×128)
7. Organize by category (flood, urban, forest, etc.)
8. Use for GAN/VLM training

## Support

If you encounter issues:

1. Check the Troubleshooting section above
2. Review error messages carefully
3. Check GEE documentation
4. Verify Python version is 3.6-3.12
5. Ensure .env has correct Project ID

---

**Ready?** Open a terminal and run:

```bash
python main.py
```

Or for step-by-step:

```bash
python scripts/01_authenticate.py
python scripts/02_initialize.py
```

Happy collecting! 🛰️📡🌍
