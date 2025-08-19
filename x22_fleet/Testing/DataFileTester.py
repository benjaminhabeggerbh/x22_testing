import json
import os
import re
import pandas as pd
import pickle
from datetime import datetime
from x22_fleet.Library.DumpFileParser import DumpFileParser
from x22_fleet.Testing.DataAnalysis import DataAnalysis
from x22_fleet.Testing.DetailsAnalysisLoader import DetailedAnalysisLoader
from x22_fleet.Library.BaseLogger import BaseLogger

class DataFileTester:
    def __init__(self, credentials_path="credentials.json", stationname="", work_locally=True, cache_path="cache", log_to_console=True):
        # Load credentials
        with open(credentials_path, "r") as f:
            credentials = json.load(f)
        
        self.stationname = stationname
        self.work_locally = work_locally
        self.local_basepath = "rawdata"  # Local directory for raw data files relative to current working directory
        self.cache_path = cache_path
        if not os.path.exists(self.cache_path):
            os.makedirs(self.cache_path)
        if not os.path.exists(self.local_basepath):
            os.makedirs(self.local_basepath)

        self.logger = BaseLogger(log_file_path=f"DataFileTester.log", log_to_console=log_to_console).get_logger()
        self.dump_parser = DumpFileParser()

    def list_files(self):
        self.logger.info("List files")
        """List files in the local directory."""
        directory_path = os.path.join(self.local_basepath, "transfers", self.stationname)
        try:
            if os.path.exists(directory_path):
                files = os.listdir(directory_path)
                return files
            else:
                return []
        except OSError as e:
            self.logger.error(f"Error accessing directory {directory_path}: {e}")
            return []

    def evaluate_sessions(self, files, tolerance=60, min_timestamp=None):
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

        timestamp_pattern = re.compile(r".*-(\d+)_rec\.bd(?:\.uploaded)?$")
        timestamps = []
        file_sizes = {}
        file_mod_times = {}
        session_files = {}

        for file in files:
            match = timestamp_pattern.match(file)
            if match:
                ts = int(match.group(1))
                if min_timestamp and ts < min_timestamp:
                    continue
                timestamps.append(ts)
                file_path = os.path.join(self.local_basepath, "transfers", self.stationname, file)
                try:
                    if os.path.exists(file_path):
                        file_sizes[ts] = os.path.getsize(file_path)
                        file_mod_times[ts] = os.path.getmtime(file_path)
                except OSError as e:
                    self.logger.warning(f"Error accessing file {file_path}: {e}")
            else:
                self.logger.warning(f"File {file} did not match the expected pattern and was skipped.")

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
            files_in_group = [
                file for file in files
                if re.search(r".*-(\d+)_rec\.bd(?:\.uploaded)?$", file) and
                int(re.search(r".*-(\d+)_rec\.bd(?:\.uploaded)?$", file).group(1)) in group
            ]
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
            local_file_path = os.path.join(self.local_basepath, filename)
            if not os.path.exists(local_file_path):
                self.logger.error(f"File {filename} not found locally.")
                return None
            # Use the correct local file path for processing
            root = ""
            device_name, data = self.dump_parser.process_file(local_file_path, root)
            with open(cache_file, "wb") as f:
                pickle.dump((device_name, data), f)
            return device_name, data


def main():
    """Main function for example usage."""
    # Update these parameters as needed
    credentials_path = "credentials.json"
    stationname = "EvoStation3"
    work_locally = True  # Always work locally now

    # Set a minimum timestamp (e.g., 1733720000)
    min_timestamp = int(datetime(2024, 12, 9, 12, 0).timestamp())  # Example setup

    tester = DataFileTester(credentials_path=credentials_path, stationname=stationname, work_locally=work_locally)
    files = tester.list_files()

    # Evaluate sessions
    if files:
        df, session_files = tester.evaluate_sessions(files, tolerance=60, min_timestamp=min_timestamp)

        # Display session summary
        tester.logger.info("Session Evaluation:")
        tester.logger.info(df)

        # Evaluate all sessions and store detailed analysis
        all_detailed_analysis = {}
        for session, session_files_list in session_files.items():
            detailed_analysis = []
            for file_name in session_files_list:
                try:
                    tester.logger.info(f"analyzing file: {file_name}")
                    sample_file = os.path.join(tester.local_basepath, "transfers", stationname, file_name)
                    cache_result = tester.get_or_create_cache(sample_file)
                    if cache_result:
                        device_name, data = cache_result
                        analysis = DataAnalysis(data).analyze()
                        detailed_analysis.append({"File Name": file_name, **analysis})
                except Exception as ex:
                    tester.logger.error(f"Exception analyzing file {file_name}: {ex}")            

            detailed_df = pd.DataFrame(detailed_analysis)
            all_detailed_analysis[session] = detailed_df

        # Store results in a pickle file
        analysis_pickle_path = os.path.join(tester.cache_path, "detailed_analysis.pkl")
        with open(analysis_pickle_path, "wb") as f:
            pickle.dump(all_detailed_analysis, f)

        tester.logger.info(f"Detailed analysis for all sessions has been saved to {analysis_pickle_path}")
        loader = DetailedAnalysisLoader()
        loader.load_and_display_analysis(limited_display=True)


if __name__ == "__main__":
    main()
