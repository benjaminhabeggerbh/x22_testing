#!/usr/bin/env python3
"""
Script to find the correct device name from MQTT subscription logs

Usage:
    python find_device_name.py [log_file]
    python find_device_name.py  # Reads from serial port
"""

import sys
import re
import serial
import time

def find_device_name_in_logs(log_content):
    """Extract device names from MQTT subscription logs"""
    device_names = set()
    
    # Look for MQTT_SUB events with command topics
    patterns = [
        r'MQTT Subscribe.*command-([^\s\']+)',  # MQTT_SUB events
        r'command-([^\s\']+)',                   # Any command topic
        r'product_name.*?([^\s]+)',              # Product name
        r'X22[^\s]*',                            # X22 device patterns
    ]
    
    for pattern in patterns:
        matches = re.findall(pattern, log_content, re.IGNORECASE)
        device_names.update(matches)
    
    return sorted(list(device_names))

def read_from_serial(port="/dev/ttyUSB0", baudrate=115200, timeout=5):
    """Read logs from serial port"""
    try:
        ser = serial.Serial(port, baudrate, timeout=timeout)
        print(f"Reading from {port}... (Press Ctrl+C to stop)")
        
        log_content = ""
        start_time = time.time()
        
        while time.time() - start_time < 30:  # Read for 30 seconds
            if ser.in_waiting:
                line = ser.readline().decode('utf-8', errors='ignore').strip()
                if line:
                    print(f"LOG: {line}")
                    log_content += line + "\n"
                    
                    # Check for device names in real-time
                    device_names = find_device_name_in_logs(log_content)
                    if device_names:
                        print(f"\n🔍 Found device names: {device_names}")
        
        ser.close()
        return log_content
        
    except serial.SerialException as e:
        print(f"Serial error: {e}")
        return ""
    except KeyboardInterrupt:
        print("\nStopped reading from serial port")
        ser.close()
        return ""

def read_from_file(filename):
    """Read logs from file"""
    try:
        with open(filename, 'r') as f:
            return f.read()
    except FileNotFoundError:
        print(f"File not found: {filename}")
        return ""

def main():
    if len(sys.argv) > 1:
        # Read from file
        log_content = read_from_file(sys.argv[1])
    else:
        # Read from serial port
        log_content = read_from_serial()
    
    if not log_content:
        print("No log content found. Try:")
        print("  python find_device_name.py log_file.txt")
        print("  python find_device_name.py  # Reads from /dev/ttyUSB0")
        return
    
    # Find device names
    device_names = find_device_name_in_logs(log_content)
    
    if device_names:
        print(f"\n🎯 Found {len(device_names)} device name(s):")
        for i, name in enumerate(device_names, 1):
            print(f"  {i}. {name}")
        
        print(f"\n💡 Use this in datastream_controller.py:")
        print(f"   DEVICE_NAME = \"{device_names[0]}\"")
    else:
        print("\n❌ No device names found in logs.")
        print("Make sure the device is connected and MQTT is working.")

if __name__ == "__main__":
    main() 