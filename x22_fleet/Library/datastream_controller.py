#!/usr/bin/env python3
"""
Minimalistic MQTT Datastream Controller for X22 Devices
Based on the existing MqttCommander class

Usage:
    python datastream_controller.py enable
    python datastream_controller.py disable
"""

import sys
from MqttCommander import MqttCommander

# Configuration - Easy to change
DEVICE_NAME = "HackerSpace2503"  # Change this to your device name

MQTT_BROKER = "localhost"  # Change this to your MQTT broker address

def main():
    if len(sys.argv) != 2:
        print("Usage: python datastream_controller.py [enable|disable]")
        sys.exit(1)
    
    action = sys.argv[1].lower()
    
    if action not in ["enable", "disable"]:
        print("Invalid action. Use 'enable' or 'disable'")
        sys.exit(1)
    
    # Create MQTT commander instance
    commander = MqttCommander(MQTT_BROKER)
    
    try:
        # Send the appropriate command
        command_name = f"{action}_datastream"
        print(f"Sending {action} datastream command to {DEVICE_NAME}...")
        
        commander.send_command(DEVICE_NAME, command_name)
        
        print(f"✅ Datastream {action} command sent successfully!")
        
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        # Clean up
        del commander

if __name__ == "__main__":
    main() 