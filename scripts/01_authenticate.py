"""
Step 1: Google Earth Engine Authentication
Run this script ONCE to authenticate your Google account with GEE
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.gee_utils import authenticate_user, is_authenticated


def main():
    """Main authentication function"""
    print("\n" + "="*60)
    print("STEP 1: Google Earth Engine Authentication")
    print("="*60)
    
    # Check if already authenticated
    if is_authenticated():
        print("✓ Already authenticated with Google Earth Engine!")
        return True
    
    print("\nAuthentication required. A browser window will open.")
    print("Follow these steps:")
    print("  1. Sign in with your Google account")
    print("  2. Click 'Allow' to grant GEE access")
    print("  3. Copy the authorization code (if prompted)")
    print("  4. Paste it back into the terminal")
    
    input("\nPress Enter to continue...")
    
    success = authenticate_user(force=False)
    
    if success:
        print("\n✓ Authentication successful!")
        print("You can now run other scripts.")
    else:
        print("\n✗ Authentication failed.")
        print("Please try again with: python 01_authenticate.py")
        return False
    
    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
