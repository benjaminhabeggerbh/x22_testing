import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from MqttCommander import MqttCommander

commander = MqttCommander("167.235.159.207")

# Device ID - replace with your actual device ID
DEVICE_ID = "0D_16_76"

# Example commands:

# 1. Identify command - makes the device flash its LED
print("Sending identify command...")
commander.send_command(DEVICE_ID, "identify")

# 2. Enable data stream - starts streaming sensor data
print("Sending enable datastream command...")
commander.send_command(DEVICE_ID, "enable_datastream")

# 3. Disable data stream - stops streaming sensor data  
# print("Sending disable datastream command...")
# commander.send_command(DEVICE_ID, "disable_datastream")

# 4. Other useful commands (uncomment to use):
# commander.send_command(DEVICE_ID, "shutdown")           # Shutdown the device
# commander.send_command(DEVICE_ID, "reboot")             # Reboot the device
# commander.send_command(DEVICE_ID, "factory_reset")      # Factory reset (use with caution!)
# commander.send_command(DEVICE_ID, "sync")               # Sync data to cloud
# commander.send_command(DEVICE_ID, "wifi_sleep")         # Put WiFi to sleep
# commander.send_command(DEVICE_ID, "enable_force_record")  # Enable force offline recording
# commander.send_command(DEVICE_ID, "disable_force_record") # Disable force offline recording

# Add a small delay to ensure MQTT message is sent before program exits
import time
print("Waiting 3 seconds for message delivery...")
time.sleep(3)  # Wait 3 seconds for message delivery
print("Commands sent successfully!")
