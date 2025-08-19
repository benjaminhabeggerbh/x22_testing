import os
import re
import numpy as np
import pandas as pd
from datetime import datetime
from x22_fleet.Library.dataParser import Parser

class FullScaleRangeConstants:
    """
    Constants for full-scale range factors.
    """
    ACC_FACTOR = 0.488 / 1000
    GYRO_FACTOR = 140 / 1000
    MAG_FACTOR = 1 / 1711

class DumpFileParser:
    """
    Class to parse dump files and extract relevant information.
    """

    def __init__(self, raw_data_dir="rawdata"):
        self.directory_path = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), raw_data_dir))
        print(f"Initialized DumpFileParser with directory: {self.directory_path}")

    @staticmethod
    def log_info(*args):
        message = " ".join(map(str, args))
        print(f"Log info: {message}")

    def get_parser_buffer(self, device_name, timestamp, data):
        acc = np.array(data.dataDict["ImuAccRaw"].data).T
        gyr = np.array(data.dataDict["ImuGyrRaw"].data)[1:4].T
        mag = np.array(data.dataDict["ImuMagRaw"].data)[1:4].T
        bat = np.array(data.dataDict["Battery"].data).T
        temp = np.array(data.dataDict["ImuTemp"].data).T

        sanitized_device_name = re.sub(r"[ :]+", "_", device_name).strip()
        device_data = {
            "x_vals": list(acc[:, 0]),
            "y_vals_acc": acc[:, 1:4] * FullScaleRangeConstants.ACC_FACTOR,
            "y_vals_gyr": gyr * FullScaleRangeConstants.GYRO_FACTOR,
            "y_vals_mag": mag * FullScaleRangeConstants.MAG_FACTOR,
            "y_vals_bat": bat,
            "y_vals_temp": temp,
        }
        print(f"Processed data for device: {sanitized_device_name}")
        return device_data

    def parse_and_load_to_memory(self, device_name, timestamp, binary_data):
        parser = Parser(logf=self.log_info)
        parser.parseStream(binary_data)
        print(f"Parsing data for device: {device_name}, Timestamp: {timestamp}")
        return self.get_parser_buffer(device_name, timestamp, parser.dataBuffer)

    def find_and_parse_files(self):
        parsed_data = []
        print(f"Scanning directory: {self.directory_path} for files")
        for root, _, files in os.walk(self.directory_path):
            print(f"Found {len(files)} files in directory: {root}")
            for filename in files:
                if filename.endswith(".bd.uploaded"):
                    parsed_data.append(self.process_file(filename, root))
        return parsed_data

    def process_file(self, filename, root):
        print(f"Processing file: {filename}")
        with open(os.path.join(root, filename), "rb") as file:
            binary_data = file.read()
            device_name, timestamp = self.extract_info_from_filename(filename)
            if device_name and timestamp:
                return device_name, self.parse_and_load_to_memory(device_name, timestamp, binary_data)
        return None, None

    @staticmethod
    def extract_info_from_filename(filename):
        match = re.search(r"([\w_]+)-(-?\d+)_rec\.bd(?:\.uploaded)?$", filename)
        if match:
            device_name = match.group(1)
            timestamp = int(match.group(2))
            print(f"Extracted device: {device_name}, timestamp: {timestamp} from filename")
            return device_name, timestamp
        return None, None

class EvaluationSummary:
    """
    Class to handle evaluation, summary generation, and device summary updates.
    """

    @staticmethod
    def update_device_summary(device_summary, device_name, device_data):
        if device_name not in device_summary:
            device_summary[device_name] = {"total_samples": 0, "missing_samples": 0}
        x_vals = device_data["x_vals"]
        total_samples = len(x_vals)
        missing_samples = np.sum(np.diff(x_vals) - 1)
        device_summary[device_name]["total_samples"] += total_samples
        device_summary[device_name]["missing_samples"] += missing_samples
        print(f"Updated summary for device: {device_name}")

    @staticmethod
    def generate_summary(parsed_data):
        device_summary = {}
        for device_name, device_data in parsed_data:
            if device_name and device_data:
                EvaluationSummary.update_device_summary(device_summary, device_name, device_data)

        df = pd.DataFrame.from_dict(device_summary, orient='index', columns=['total_samples', 'missing_samples'])
        df['time_seconds'] = df['total_samples'] / 500
        df['percent_missing'] = (df['missing_samples'] / df['total_samples']) * 100

        summary_row = df.sum()
        summary_row['percent_missing'] = (summary_row['missing_samples'] / summary_row['total_samples']) * 100
        df.loc['Total'] = summary_row

        return df

    @staticmethod
    def save_summary(df, output_path):
        df.to_csv(output_path, index_label='device_name')
        print(f"Summary saved to {output_path}")

if __name__ == "__main__":
    parser = DumpFileParser()
    parsed_data = parser.find_and_parse_files()

    evaluation = EvaluationSummary()
    df = evaluation.generate_summary(parsed_data)

    summary_file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "device_summary.csv")
    evaluation.save_summary(df, summary_file_path)

    print(df)
