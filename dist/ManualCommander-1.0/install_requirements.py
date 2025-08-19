#!/usr/bin/env python3
"""
Install required packages for ManualCommander
"""

import subprocess
import sys

def install_package(package):
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", package])
        print(f"✓ Installed {package}")
        return True
    except subprocess.CalledProcessError:
        print(f"✗ Failed to install {package}")
        return False

def main():
    print("Installing required packages for ManualCommander...")
    
    packages = [
        "paho-mqtt>=1.6.0",
        "crcmod>=1.7"
    ]
    
    success = True
    for package in packages:
        if not install_package(package):
            success = False
    
    if success:
        print("\n✓ All packages installed successfully!")
        print("You can now run ManualCommander.")
    else:
        print("\n✗ Some packages failed to install.")
        print("Please install them manually: pip install paho-mqtt crcmod")
    
    input("\nPress Enter to continue...")

if __name__ == "__main__":
    main()
