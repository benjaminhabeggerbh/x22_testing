import json
import os
import re
import pandas as pd
import pickle
from datetime import datetime
from dash import Dash, dcc, html, Input, Output
from x22_fleet.Library.DumpFileParser import DumpFileParser
from x22_fleet.Testing.DataAnalysis import DataAnalysis
from x22_fleet.Testing.DetailsAnalysisLoader import DetailedAnalysisLoader
from x22_fleet.Library.BaseLogger import BaseLogger

class UploadStatistics:
    def __init__(self, local_basepath="rawdata", stationname="", log_to_console=True):
        self.local_basepath = local_basepath
        self.stationname = stationname
        self.logger = BaseLogger(log_file_path=f"UploadStatistics.log", log_to_console=log_to_console).get_logger()

    def list_files(self):
        self.logger.info("Starting to list files.")
        """List files in the local directory."""
        directory_path = os.path.join(self.local_basepath, "transfers", self.stationname)
        try:
            if os.path.exists(directory_path):
                self.logger.info(f"Directory {directory_path} found.")
                files = os.listdir(directory_path)
                self.logger.info(f"Found {len(files)} files in directory {directory_path}.")
                return files
            else:
                self.logger.warning(f"Directory {directory_path} does not exist.")
                return []
        except OSError as e:
            self.logger.error(f"Error accessing directory {directory_path}: {e}")
            return []

    def group_files(self, files, tolerance=60, min_timestamp=None):
        self.logger.info("Starting to group files.")
        """Group files based on timestamps in filenames."""
        timestamp_pattern = re.compile(r".*-(\d+)_rec\.bd(?:\.uploaded)?$")
        timestamps = []
        file_sizes = {}
        file_mod_times = {}

        for file in files:
            match = timestamp_pattern.match(file)
            if match:
                ts = int(match.group(1))
                if min_timestamp and ts < min_timestamp:
                    self.logger.debug(f"File {file} skipped due to min_timestamp filter.")
                    continue
                timestamps.append(ts)
                file_path = os.path.join(self.local_basepath, "transfers", self.stationname, file)
                try:
                    if os.path.exists(file_path):
                        file_sizes[ts] = os.path.getsize(file_path)
                        file_mod_times[ts] = os.path.getmtime(file_path)
                        self.logger.debug(f"File {file} added with timestamp {ts}, size {file_sizes[ts]} bytes.")
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

        self.logger.info(f"Grouping complete. Found {len(grouped)} groups.")
        return grouped, file_sizes, file_mod_times


def create_dash_app(statistics):
    app = Dash(__name__)

    app.layout = html.Div([
        html.H1("EvoStation3 Upload Statistics"),
        dcc.Dropdown(id="group-selection", placeholder="Select a Group"),
        html.Div(id="file-details"),
        html.Div(id="coarse-analysis")
    ])

    @app.callback(
        Output("group-selection", "options"),
        Input("group-selection", "value")
    )
    def update_groups(_):
        files = statistics.list_files()
        if files:
            grouped, _, _ = statistics.group_files(files)
            return [{"label": f"Group {i+1}", "value": i} for i in range(len(grouped))]
        return []

    @app.callback(
        Output("coarse-analysis", "children"),
        Input("group-selection", "value")
    )
    def display_coarse_analysis(selected_group):
        files = statistics.list_files()
        if not files:
            return "No files found."

        grouped, file_sizes, file_mod_times = statistics.group_files(files)
        if selected_group is None or selected_group >= len(grouped):
            return "Please select a valid group."

        group = grouped[selected_group]
        details = []
        for ts in group:
            size = file_sizes.get(ts, 0)
            mod_time = file_mod_times.get(ts, 0)
            details.append(html.Div([
                f"Timestamp: {datetime.utcfromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S')}, ",
                f"Size: {size} bytes, ",
                f"Modified: {datetime.utcfromtimestamp(mod_time).strftime('%Y-%m-%d %H:%M:%S') if mod_time else 'N/A'}"
            ]))
        return details

    return app

if __name__ == "__main__":
    stationname = "EvoStation3"
    statistics = UploadStatistics(local_basepath="rawdata", stationname=stationname)
    app = create_dash_app(statistics)
    app.run_server(debug=True, host="0.0.0.0", port=5101)
