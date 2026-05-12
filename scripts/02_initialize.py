"""
Step 2: Google Earth Engine Initialization
Initialize GEE with your project ID
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config.settings import GEE_PROJECT_ID
from scripts.gee_utils import initialize_gee, authenticate_user, is_authenticated


def main():
    """Main initialization function"""
    print("\n" + "="*60)
    print("STEP 2: Google Earth Engine Initialization")
    print("="*60)
    
    # Check authentication
    if not is_authenticated():
        print("\n✗ Not authenticated. Running authentication...")
        if not authenticate_user():
            print("Authentication failed. Please run 01_authenticate.py first.")
            return False
    
    # Initialize GEE
    print(f"\nInitializing GEE with project: {GEE_PROJECT_ID}")
    success = initialize_gee(project_id=GEE_PROJECT_ID)
    
    if success:
        print("\n✓ Earth Engine initialization successful!")
        print("You can now run data collection scripts.")
    else:
        print("\n✗ Initialization failed.")
        print("Please check your project ID in config/settings.py or .env file")
        return False
    
    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
