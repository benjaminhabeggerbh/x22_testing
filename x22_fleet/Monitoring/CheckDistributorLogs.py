import os
import re
from collections import defaultdict
import plotly.graph_objects as go

class CheckDistributorLogs:
    def __init__(self, basepath, station_name):
        self.basepath = basepath
        self.station_name = station_name
        self.log_dir = f"{self.basepath}/logs"
        self.sensor_states = defaultdict(list)
        self.transition_pattern = re.compile(r"(?P<timestamp>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3}) - Distributor - INFO - (?P<sensor_id>\S+): Transitioned to (?P<state>\S+)")

    def parse_logs(self):
        log_files = [f for f in os.listdir(self.log_dir) if re.match(f"Distributor\\.{self.station_name}\\.log(\\.\\d+)?$", f)]

        for log_file in sorted(log_files, reverse=True):  # Process rotated files first
            log_path = os.path.join(self.log_dir, log_file)
            print(f"Opening log file: {log_path}")  # Console output for opened files
            with open(log_path, "r") as f:
                for line in f:
                    match = self.transition_pattern.search(line)
                    if match:
                        sensor_id = match.group("sensor_id")
                        state = match.group("state")
                        timestamp = match.group("timestamp")
                        self.sensor_states[sensor_id].append((timestamp, state))

    def get_sensor_states(self):
        return self.sensor_states

    def get_distinct_states(self):
        distinct_states = set()
        for transitions in self.sensor_states.values():
            for _, state in transitions:
                distinct_states.add(state)
        return distinct_states

    def plot_states_per_sensor(self):
        station_output_dir = os.path.join("plots", self.station_name)
        os.makedirs(station_output_dir, exist_ok=True)
        state_order = ["IDLE", "OFFLINE", "READY_TO_SYNC", "SYNCING", "SYNC_ORDERED"]

        for sensor_id, transitions in self.sensor_states.items():
            fig = go.Figure()
            timestamps = [t[0] for t in transitions]
            states = [state_order.index(t[1]) for t in transitions if t[1] in state_order]

            fig.add_trace(go.Scatter(
                x=timestamps,
                y=states,
                mode="lines+markers",
                name=sensor_id
            ))

            fig.update_layout(
                title=f"Sensor {sensor_id} State Transitions",
                xaxis_title="Timestamp",
                yaxis_title="State",
                yaxis=dict(
                    tickmode="array",
                    tickvals=list(range(len(state_order))),
                    ticktext=state_order
                ),
                legend_title="Sensor ID",
            )

            output_file = os.path.join(station_output_dir, f"{sensor_id}_states.html")
            fig.write_html(output_file)
            print(f"Plot for sensor {sensor_id} saved to {output_file}")

    def print_sorted_sensor_states(self):
        for sensor_id, transitions in sorted(self.sensor_states.items()):
            print(f"Sensor ID: {sensor_id}")
            for timestamp, state in transitions:
                print(f"  {timestamp} - {state}")

if __name__ == "__main__":
    BASEPATH = "/var/axiamo_transfer"
    STATION_NAME = "EvoStation3"

    log_checker = CheckDistributorLogs(BASEPATH, STATION_NAME)
    log_checker.parse_logs()
    log_checker.print_sorted_sensor_states()

    distinct_states = log_checker.get_distinct_states()
    print("\nDistinct States:")
    for state in sorted(distinct_states):
        print(f"  {state}")

    log_checker.plot_states_per_sensor()
