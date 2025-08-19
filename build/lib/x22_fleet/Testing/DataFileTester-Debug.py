import ftplib
import json
import os
import re
import pandas as pd
import pickle
import numpy as np
from datetime import datetime
from x22_fleet.Library.DumpFileParser import DumpFileParser
from x22_fleet.Testing.DataAnalysis import DataAnalysis

class DataFileTester:
    def __init__(self, credentials_path="credentials.json", stationname="", work_locally=False, cache_path="cache"):
        # Load credentials
        with open(credentials_path, "r") as f:
            credentials = json.load(f)
        
        self.server = credentials.get("server")  # Assuming the same field for server address
        self.username = credentials.get("username")
        self.password = credentials.get("password")
        self.basepath = credentials.get("basepath")
        self.ftppath = self.basepath + "/ftp"
        self.firmwarepath = self.ftppath + "/firmware"
        self.stationname = stationname
        self.work_locally = work_locally
        self.local_basepath = "/home/axiamo/ftp"  # Local base path for files
        self.cache_path = cache_path
        if not os.path.exists(self.cache_path):
            os.makedirs(self.cache_path)
        self.dump_parser = DumpFileParser()

    def list_files(self):
        """List files in the FTP directory or locally based on the work_locally flag."""
        if self.work_locally:
            # Local mode
            directory_path = os.path.join(self.local_basepath, "transfers", self.stationname)
            try:
                if os.path.exists(directory_path):
                    files = os.listdir(directory_path)
                    return files
                else:
                    return []
            except OSError as e:
                return []
        else:
            # FTP mode
            directory_path = f"{self.ftppath}/transfers/{self.stationname}"
            try:
                # Connect to FTP server
                with ftplib.FTP(self.server) as ftp:
                    ftp.login(user=self.username, passwd=self.password)
                    # Change to the specific directory
                    ftp.cwd(directory_path)
                    # List files
                    files = ftp.nlst()
                    return files
            except ftplib.all_errors as e:
                return []

    def evaluate_sessions(self, files, tolerance=60):
        """Evaluate timestamps in filenames and group similar timestamps."""
        def human_readable_size(size):
            """Convert size to human-readable format in KB or MB."""
            if size < 1024 * 1024:
                return f"{size / 1024:.2f} KB"
            else:
                return f"{size / (1024 * 1024):.2f} MB"

        def human_readable_timestamp(timestamp):
            """Convert timestamp to a human-readable datetime format."""
            return datetime.utcfromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')

        def human_readable_duration(seconds):
            """Convert seconds to a human-readable minutes:seconds format."""
            minutes = int(seconds) // 60
            remaining_seconds = int(seconds) % 60
            return f"{minutes}:{remaining_seconds:02d}"

        timestamp_pattern = re.compile(r".*-(\d+)_rec\.bd$")
        timestamps = []
        file_sizes = {}
        file_mod_times = {}
        session_files = {}

        for file in files:
            match = timestamp_pattern.match(file)
            if match:
                ts = int(match.group(1))
                timestamps.append(ts)
                file_path = os.path.join(self.local_basepath, "transfers", self.stationname, file) if self.work_locally else file
                try:
                    if self.work_locally and os.path.exists(file_path):
                        file_sizes[ts] = os.path.getsize(file_path)
                        file_mod_times[ts] = os.path.getmtime(file_path)
                except OSError as e:
                    pass

        # Sort timestamps and group them with tolerance
        timestamps.sort()
        grouped = []
        current_group = []
        for ts in timestamps:
            if not current_group or ts - current_group[-1] <= tolerance:
                current_group.append(ts)
            else:
                grouped.append(current_group)
                current_group = [ts]
        if current_group:
            grouped.append(current_group)

        # Summarize groups in a DataFrame and collect files per session
        summary = {
            "Group": [],
            "Start Timestamp": [],
            "Max Start Diff (s)": [],
            "File Count": [],
            "Min File Size": [],
            "Max File Size": [],
            "Avg File Size": [],
            "Total Upload Time": [],
            "Total Upload Size (MB)": [],
            "Upload Speed (MB/s)": []
        }
        session_files = {}

        for i, group in enumerate(grouped):
            sizes = [file_sizes.get(ts, 0) for ts in group]
            mod_times = [file_mod_times.get(ts, 0) for ts in group]
            files_in_group = [file for file in files if int(re.search(r".*-(\d+)_rec\.bd$", file).group(1)) in group]
            session_files[i + 1] = files_in_group

            summary["Group"].append(i + 1)
            summary["Start Timestamp"].append(human_readable_timestamp(group[0]))
            summary["Max Start Diff (s)"].append(group[-1] - group[0])
            summary["File Count"].append(len(group))
            summary["Min File Size"].append(human_readable_size(min(sizes)) if sizes else "0 KB")
            summary["Max File Size"].append(human_readable_size(max(sizes)) if sizes else "0 KB")
            summary["Avg File Size"].append(human_readable_size(sum(sizes) / len(sizes)) if sizes else "0 KB")
            total_size_mb = sum(sizes) / (1024 * 1024) if sizes else 0
            summary["Total Upload Size (MB)"].append(f"{total_size_mb:.2f} MB")
            if mod_times:
                total_upload_time = max(mod_times) - min(mod_times)
                summary["Total Upload Time"].append(human_readable_duration(total_upload_time))
                upload_speed = total_size_mb / total_upload_time if total_upload_time > 0 else 0
                summary["Upload Speed (MB/s)"].append(f"{upload_speed:.2f} MB/s")
            else:
                summary["Total Upload Time"].append("0:00")
                summary["Upload Speed (MB/s)"].append("0.00 MB/s")

        df = pd.DataFrame(summary)
        return df, session_files

    def get_or_create_cache(self, filename):
        """Check cache for pickle file or create one by processing the dump file."""
        cache_file = os.path.join(self.cache_path, f"{os.path.basename(filename)}.pkl")
        if os.path.exists(cache_file):
            with open(cache_file, "rb") as f:
                return pickle.load(f)
        else:
            root = os.path.dirname(filename)
            device_name, data = self.dump_parser.process_file(filename, root)
            with open(cache_file, "wb") as f:
                pickle.dump((device_name, data), f)
            return device_name, data

def main():
    """Main function for debugging."""
    # Update these parameters as needed
    credentials_path = "credentials.json"
    stationname = "EvoStationMaintenance"
    work_locally = True  # Ensure this is True to work locally

    tester = DataFileTester(credentials_path=credentials_path, stationname=stationname, work_locally=work_locally)
    specific_file = "X22_0D_1A_CE-1733729177_rec.bd"
    sample_file = os.path.join(tester.local_basepath, "transfers", stationname, specific_file)

    # Process the specific file
    try:
        device_name, data = tester.get_or_create_cache(sample_file)
        print(f"Processed file: {sample_file}")
        print(f"Device Name: {device_name}")

        # Analyze device data
        analysis = DataAnalysis(data).analyze()
        print("Analysis Results:")
        print(analysis)

    except Exception as e:
        print(f"An error occurred while processing the file: {e}")

if __name__ == "__main__":
    main()


if __name__ == "__main__":
    main()
