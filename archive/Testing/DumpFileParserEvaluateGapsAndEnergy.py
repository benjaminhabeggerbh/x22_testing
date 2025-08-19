import os
import re
import numpy as np
import pandas as pd
from dataParser import Parser
import matplotlib.pyplot as plt

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
        device_summary = []
        print(f"Scanning directory: {self.directory_path} for files")
        
        for root, dirs, files in os.walk(self.directory_path):
            subfolder_name = os.path.basename(root)  # Get the current subfolder name
            print(f"Found {len(files)} files in directory: {root}")
            
            for filename in files:
                if filename.endswith(".bd.uploaded"):
                    print(f"Processing file: {filename}")
                    with open(os.path.join(root, filename), "rb") as file:
                        binary_data = file.read()
                        device_name, timestamp = self.extract_info_from_filename(filename)
                        device_data = self.parse_and_load_to_memory(device_name, timestamp, binary_data)
                        
                        x_vals = device_data["x_vals"]
                        bat_vals = device_data["y_vals_bat"]
                        total_samples = len(x_vals)
                        d = np.diff(x_vals)
                        missing_samples = np.sum(d - 1)  # sum of all differences minus one for each element
                        
                        # Calculate average current (in mA)
                        average_current = np.mean(bat_vals[:, 1])  # Assuming column 1 holds current data in battery array
                        
                        # Calculate average voltage (in mV)
                        average_voltage = np.mean(bat_vals[:, 2])  # Assuming column 0 holds voltage data in battery array
                        
                        device_summary.append({
                            "device_name": device_name,
                            "subfolder": subfolder_name,
                            "total_samples": total_samples,
                            "missing_samples": missing_samples,
                            "average_current_mA": average_current,
                            "average_voltage_mV": average_voltage
                        })
                        print(f"Added data for device: {device_name} in subfolder: {subfolder_name}")
                        
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

    def display_summary_data(self, summary_data):
        # Create a DataFrame from the parsed data
        df = pd.DataFrame(summary_data)
        fs = 200
        
        # Calculate additional columns
        df['time_seconds'] = df['total_samples'] / fs  # Calculate time in seconds
        df['percent_missing'] = (df['missing_samples'] / df['total_samples']) * 100

        # Add summary row
        summary_row = df.sum(numeric_only=True)
        summary_row['percent_missing'] = (summary_row['missing_samples'] / summary_row['total_samples']) * 100
        summary_row['device_name'] = 'Total'
        summary_row['subfolder'] = 'All'
        df = df.append(summary_row, ignore_index=True)

        # Plotting the DataFrame graphically
        df.plot(x='device_name', y=['total_samples', 'missing_samples', 'average_current_mA', 'average_voltage_mV'], kind='bar', figsize=(10, 6))
        plt.title('Device Summary Data')
        plt.xlabel('Device Name')
        plt.ylabel('Values')
        plt.xticks(rotation=45)
        plt.tight_layout()
        plt.show()

    def load_summary_from_csv_and_display(self, csv_path):
        # Load the DataFrame from CSV
        df = pd.read_csv(csv_path)
        
        # Plotting the DataFrame graphically
        df.plot(x='device_name', y=['total_samples', 'missing_samples', 'average_current_mA', 'average_voltage_mV'], kind='bar', figsize=(10, 6))
        plt.title('Device Summary Data from CSV')
        plt.xlabel('Device Name')
        plt.ylabel('Values')
        plt.xticks(rotation=45)
        plt.tight_layout()
        plt.show()

if __name__ == "__main__":
    parser = DumpFileParser()
    choice = input("Do you want to scan and analyze data (1) or load summary from CSV (2)? Enter 1 or 2: ")
    if choice == '1':
        summary_data = parser.find_and_parse_files()
        
        # Display the summary data graphically
        parser.display_summary_data(summary_data)
        
        # Create a DataFrame from the parsed data
        df = pd.DataFrame(summary_data)
        fs = 200
        
        # Calculate additional columns
        df['time_seconds'] = df['total_samples'] / fs  # Calculate time in seconds
        df['percent_missing'] = (df['missing_samples'] / df['total_samples']) * 100

        # Add summary row
        summary_row = df.sum(numeric_only=True)
        summary_row['percent_missing'] = (summary_row['missing_samples'] / summary_row['total_samples']) * 100
        summary_row['device_name'] = 'Total'
        summary_row['subfolder'] = 'All'
        df = df.append(summary_row, ignore_index=True)

        # Save the DataFrame to a CSV file
        summary_file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "device_summary.csv")
        df.to_csv(summary_file_path, index=False)
        print(f"Summary saved to {summary_file_path}")

        # Print the DataFrame to console
        print(df)
    elif choice == '2':
        csv_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "device_summary.csv")
        parser.load_summary_from_csv_and_display(csv_path)
    else:
        print("Invalid choice. Please enter 1 or 2.")
