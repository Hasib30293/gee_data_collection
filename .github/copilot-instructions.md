- [x] Verify that the copilot-instructions.md file in the .github directory is created.

- [x] Project clarified
    - Python project for Google Earth Engine (GEE) satellite data collection
    - Target: GAN+VLM training datasets (flood, urban, forest classification)
    - Requirements: Python 3.6-3.12, Google account, GEE account, VS Code

- [x] Project scaffolded
    - Created directory structure: scripts/, config/, notebooks/, data/
    - Created 6 sequential Python scripts (01_authenticate → 06_export_to_drive)
    - Created utility module (gee_utils.py) with helper functions
    - Created configuration system with .env support

- [ ] Install dependencies
    - Install Python packages from requirements.txt
    - Verify earthengine-api, geemap, and other dependencies

- [ ] Create virtual environment
    - Set up Python virtual environment (gee_env)
    - Activate environment for all subsequent steps

- [ ] First-time authentication
    - Run 01_authenticate.py to authenticate with Google
    - Obtain and save GEE credentials

- [ ] Verify GEE setup
    - Configure .env with GEE project ID
    - Run 02_initialize.py to test connection

- [ ] Test data collection
    - Run 03_collect_images.py to verify image retrieval
    - Confirm Sentinel-2 imagery collection works

- [ ] Verify full workflow
    - Test image processing (04_process_images.py)
    - Test visualization (05_visualize.py)
    - Test export (06_export_to_drive.py)

- [ ] Documentation complete
    - README.md exists and is current
    - All scripts have docstrings
    - Project is ready for use

## Quick Start Guide

1. **Activate virtual environment:**
   ```bash
   gee_env\Scripts\activate  # Windows
   source gee_env/bin/activate  # Mac/Linux
   ```

2. **Run authentication (first time only):**
   ```bash
   python scripts/01_authenticate.py
   ```

3. **Initialize GEE:**
   ```bash
   python scripts/02_initialize.py
   ```

4. **Collect images:**
   ```bash
   python scripts/03_collect_images.py
   ```

5. **Process and export:**
   ```bash
   python scripts/04_process_images.py
   python scripts/06_export_to_drive.py
   ```

## Project Features

- ✓ Modular design: 6 independent scripts for each workflow step
- ✓ Configuration-based: .env file for easy customization
- ✓ Utility functions: Reusable code for common tasks
- ✓ Error handling: Clear error messages and debugging
- ✓ Documentation: Docstrings and inline comments
- ✓ Ready for production: Handles credentials securely

## Configuration

Before first run, create `.env` file:
```bash
cp .env.example .env
# Edit .env with your GEE project ID and AOI
```

## Support

- See README.md for troubleshooting
- Check individual script files for specific options
- Review GEE documentation: https://developers.google.com/earth-engine
