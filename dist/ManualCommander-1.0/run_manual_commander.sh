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
