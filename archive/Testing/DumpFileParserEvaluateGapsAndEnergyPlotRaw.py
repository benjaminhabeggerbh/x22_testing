import os
import re
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from dataParser import Parser

class FullScaleRangeConstants:
    accFactor = 0.488 / 1000
    gyroFactor = 140 / 1000
    magFactor = 1 / 1711

fsr = FullScaleRangeConstants

class DumpFileParser:
    def __init__(self):
        script_dir = os.path.dirname(os.path.abspath(__file__))
        self.directory_path = os.path.abspath(os.path.join(script_dir, "rawdata"))
        print("Initialized DumpFileParser with directory:", self.directory_path)

    def log_info(self, *args, **kwargs):
        message = " ".join(map(str, args))
        print("Log info:", message)

    def getParserBuffer(self, devName, timestamp, data):
        acc = np.array(data.dataDict["ImuAccRaw"].data).T
        gyr = np.array(data.dataDict["ImuGyrRaw"].data)[1:4].T
        mag = np.array(data.dataDict["ImuMagRaw"].data)[1:4].T
        bat = np.array(data.dataDict["Battery"].data).T
        temp = np.array(data.dataDict["ImuTemp"].data).T

        sanitized_devName = re.sub(r"[ :]+", "_", devName).strip()
        self.deviceData = {
            "x_vals": list(acc[:, 0]),
            "y_vals_acc": acc[:, 1:4] * fsr.accFactor,
            "y_vals_gyr": gyr * fsr.gyroFactor,
            "y_vals_mag": mag * fsr.magFactor,
            "y_vals_bat": bat,
            "y_vals_temp": temp,
        }
        print(f"Processed data for device: {sanitized_devName}")
        return self.deviceData

    def parse_and_load_to_memory(self, device_name, timestamp, binary_data):
        self.rawParser = Parser(logf=self.log_info)
        self.rawParser.parseStream(binary_data)
        print(f"Parsing data for device: {device_name}, Timestamp: {timestamp}")
        return self.getParserBuffer(device_name, timestamp, self.rawParser.dataBuffer)

    def find_and_parse_files(self):
        device_summary = {}
        print(f"Scanning directory: {self.directory_path} for files")
        for root, dirs, files in os.walk(self.directory_path):
            print(f"Found {len(files)} files in directory: {root}")
            for filename in files:
                if filename.endswith(".bd.uploaded"):
                    print(f"Processing file: {filename}")
                    with open(os.path.join(root, filename), "rb") as file:
                        binary_data = file.read()
                        device_name, timestamp = self.extract_info_from_filename(filename)
                        device_data = self.parse_and_load_to_memory(device_name, timestamp, binary_data)
                        if device_name not in device_summary:
                            device_summary[device_name] = {
                                "total_samples": 0,
                                "missing_samples": 0,
                                "average_current_mA": 0,
                                "average_voltage_mV": 0
                            }

                        self.plot_sensor_data(device_data)  # Call to plot data

                        x_vals = device_data["x_vals"]
                        bat_vals = device_data["y_vals_bat"]
                        total_samples = len(x_vals)
                        d = np.diff(x_vals)
                        missing_samples = np.sum(d - 1)  # sum of all differences minus one for each element
                        
                        # Calculate average current (in mA)
                        average_current = np.mean(bat_vals[:, 1])  # Assuming column 1 holds current data
                        
                        # Calculate average voltage (in mV)
                        average_voltage = np.mean(bat_vals[:, 2])  # Assuming column 0 holds voltage data
                        
                        device_summary[device_name]["total_samples"] += total_samples
                        device_summary[device_name]["missing_samples"] += missing_samples
                        device_summary[device_name]["average_current_mA"] = average_current
                        device_summary[device_name]["average_voltage_mV"] = average_voltage
                        
                        print(f"Updated summary for device: {device_name}")
        return device_summary

    def extract_info_from_filename(self, filename):
        match = re.match(r"(\w+)-(\d+)_rec.bd.uploaded", filename)
        if match:
            device_name = match.group(1)
            timestamp = int(match.group(2))
            print(f"Extracted device: {device_name}, timestamp: {timestamp} from filename")
            return device_name, timestamp
        else:
            return None, None

    def plot_sensor_data(self, device_data):
        time = np.array(device_data['x_vals'])
        acc_data = np.array(device_data['y_vals_acc'])
        gyr_data = np.array(device_data['y_vals_gyr'])
        mag_data = np.array(device_data['y_vals_mag'])

        fig = make_subplots(rows=3, cols=1, subplot_titles=("Accelerometer", "Gyroscope", "Magnetometer"))

        # Add traces for Accelerometer, Gyroscope, and Magnetometer
        for i, (data, name) in enumerate(zip([acc_data, gyr_data, mag_data], ['acc', 'gyr', 'mag'])):
            for j in range(3):
                fig.add_trace(go.Scatter(x=time, y=data[:, j], mode='lines', name=f'{name}_{["x", "y", "z"][j]}'), row=i+1, col=1)

        fig.update_layout(height=900, width=700, title_text="Sensor Data Visualization")
        fig.show()

if __name__ == "__main__":
    parser = DumpFileParser()
    summary = parser.find_and_parse_files()
