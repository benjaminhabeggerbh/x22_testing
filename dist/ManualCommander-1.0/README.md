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
