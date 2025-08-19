#!/bin/bash

# Package ManualCommander for standalone distribution
# This script creates a zip file that can be downloaded and extracted
# to run ManualCommander on both Windows and Linux

set -e

# Configuration
PACKAGE_NAME="ManualCommander"
PACKAGE_VERSION="1.0"
DIST_DIR="dist"
PACKAGE_DIR="${DIST_DIR}/${PACKAGE_NAME}-${PACKAGE_VERSION}"
ZIP_FILE="${DIST_DIR}/${PACKAGE_NAME}-${PACKAGE_VERSION}.zip"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}=== Packaging ManualCommander ===${NC}"

# Create distribution directory
echo -e "${YELLOW}Creating distribution directory...${NC}"
rm -rf "${DIST_DIR}"
mkdir -p "${PACKAGE_DIR}"

# Copy required files
echo -e "${YELLOW}Copying files...${NC}"

# Copy the Library files
cp -r x22_fleet/Library/AxiamoX22Composer.py "${PACKAGE_DIR}/"
cp -r x22_fleet/Library/MqttCommander.py "${PACKAGE_DIR}/"
cp -r x22_fleet/Library/ManualCommander.py "${PACKAGE_DIR}/"

# Create Windows batch file
echo -e "${YELLOW}Creating Windows batch file...${NC}"
cat > "${PACKAGE_DIR}/run_manual_commander.bat" << 'EOF'
@echo off
echo ========================================
echo    ManualCommander - X22 Device Control
echo ========================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.7+ from https://python.org
    pause
    exit /b 1
)

REM Check if required packages are installed
echo Checking required packages...
MISSING_PACKAGES=""

python -c "import paho.mqtt.client" >nul 2>&1
if errorlevel 1 (
    set MISSING_PACKAGES=%MISSING_PACKAGES% paho-mqtt
)

python -c "import crcmod" >nul 2>&1
if errorlevel 1 (
    set MISSING_PACKAGES=%MISSING_PACKAGES% crcmod
)

if not "%MISSING_PACKAGES%"=="" (
    echo Installing required packages: %MISSING_PACKAGES%
    pip install %MISSING_PACKAGES%
)

echo.
echo Starting ManualCommander...
echo.

REM Run the ManualCommander
python ManualCommander.py

echo.
echo ManualCommander finished.
pause
EOF

# Create Linux shell script
echo -e "${YELLOW}Creating Linux shell script...${NC}"
cat > "${PACKAGE_DIR}/run_manual_commander.sh" << 'EOF'
#!/bin/bash

echo "========================================"
echo "   ManualCommander - X22 Device Control"
echo "========================================"
echo

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "ERROR: Python 3 is not installed"
    echo "Please install Python 3.7+ using your package manager"
    echo "Ubuntu/Debian: sudo apt install python3 python3-pip"
    echo "CentOS/RHEL: sudo yum install python3 python3-pip"
    exit 1
fi

# Check if required packages are installed
echo "Checking required packages..."
MISSING_PACKAGES=""

if ! python3 -c "import paho.mqtt.client" &> /dev/null; then
    MISSING_PACKAGES="$MISSING_PACKAGES paho-mqtt"
fi

if ! python3 -c "import crcmod" &> /dev/null; then
    MISSING_PACKAGES="$MISSING_PACKAGES crcmod"
fi

if [ ! -z "$MISSING_PACKAGES" ]; then
    echo "Installing required packages: $MISSING_PACKAGES"
    pip3 install $MISSING_PACKAGES
fi

echo
echo "Starting ManualCommander..."
echo

# Run the ManualCommander
python3 ManualCommander.py

echo
echo "ManualCommander finished."
EOF

# Make the shell script executable
chmod +x "${PACKAGE_DIR}/run_manual_commander.sh"

# Create README file
echo -e "${YELLOW}Creating README...${NC}"
cat > "${PACKAGE_DIR}/README.md" << 'EOF'
# ManualCommander - X22 Device Control

A simple command-line tool to control X22 devices via MQTT.

## Requirements

- Python 3.7 or higher
- Internet connection (for MQTT communication)

## Installation

### Windows
1. Extract this zip file to a folder
2. Double-click `run_manual_commander.bat`
3. The script will automatically install required packages if needed

### Linux/macOS
1. Extract this zip file to a folder
2. Open terminal in the extracted folder
3. Run: `./run_manual_commander.sh`
4. The script will automatically install required packages if needed

## Configuration

Edit `ManualCommander.py` to configure:
- **Device ID**: Change `DEVICE_ID = "0D_16_76"` to your device ID
- **MQTT Broker**: Change the broker address if needed
- **Commands**: Uncomment the commands you want to use

## Available Commands

### Data Stream Control
- `enable_datastream` - Start streaming sensor data
- `disable_datastream` - Stop streaming sensor data

### Device Control
- `identify` - Flash device LED for identification
- `shutdown` - Shutdown the device
- `reboot` - Reboot the device
- `factory_reset` - Factory reset (use with caution!)
- `sync` - Sync data to cloud
- `wifi_sleep` - Put WiFi to sleep
- `enable_force_record` - Enable force offline recording
- `disable_force_record` - Disable force offline recording

## Usage

1. Configure your device ID in `ManualCommander.py`
2. Run the appropriate script for your platform
3. The tool will send commands to your device via MQTT

## Troubleshooting

- **"Python not found"**: Install Python 3.7+ from python.org
- **"Module not found"**: The script will automatically install required packages
- **"Connection failed"**: Check your internet connection and MQTT broker address
- **"Invalid command"**: Make sure you're using the latest version of this tool

## Version

ManualCommander v1.0
EOF

# Create requirements.txt
echo -e "${YELLOW}Creating requirements.txt...${NC}"
cat > "${PACKAGE_DIR}/requirements.txt" << 'EOF'
paho-mqtt>=1.6.0
crcmod>=1.7
EOF

# Create a simple installation script for pip packages
echo -e "${YELLOW}Creating install script...${NC}"
cat > "${PACKAGE_DIR}/install_requirements.py" << 'EOF'
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
EOF

# Create zip file
echo -e "${YELLOW}Creating zip file...${NC}"
cd "${DIST_DIR}"
zip -r "${PACKAGE_NAME}-${PACKAGE_VERSION}.zip" "${PACKAGE_NAME}-${PACKAGE_VERSION}/"
cd ..

# Show results
echo -e "${GREEN}=== Packaging Complete ===${NC}"
echo -e "${GREEN}Package created: ${ZIP_FILE}${NC}"
echo -e "${GREEN}Package size: $(du -h "${ZIP_FILE}" | cut -f1)${NC}"
echo
echo -e "${BLUE}Package contents:${NC}"
ls -la "${PACKAGE_DIR}/"
echo
echo -e "${YELLOW}To distribute:${NC}"
echo -e "Upload ${ZIP_FILE} to your download location"
echo -e "Users can extract and run the appropriate script for their platform" 