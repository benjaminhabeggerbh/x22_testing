import os
import shutil
import time
import webbrowser
from enum import Enum, auto
import graphviz
from x22_fleet.Library.BaseLogger import BaseLogger

# State machine implementation
class SensorState(Enum):
    IDLE = auto()
    READY_TO_SYNC = auto()
    SYNC_ORDERED = auto()
    SYNCING = auto()
    OFFLINE = auto()
    STUCK = auto()

class SensorStateMachine:
    def __init__(self, sensorName, logger):
        self.state = SensorState.OFFLINE
        self.logger = logger
        self.sensorName = sensorName
        self.stuckInSyncOrdered = 0
        self.stuckInSyncing = 0

    def transition(self, event):
        """
        Handle state transitions based on the given event.

        Args:
            event (str): The event triggering the transition.

        Returns:
            None
        """
        previous_state = self.state

        if self.state == SensorState.IDLE:
            if event == "update_ready":
                self.state = SensorState.READY_TO_SYNC
                self.logger.info(f"{self.sensorName}: Transitioned to READY_TO_SYNC")
            elif event == "offline":
                self.state = SensorState.OFFLINE
                self.logger.info(f"{self.sensorName}: Transitioned to OFFLINE")
            elif event == "sync_started":
                self.state = SensorState.SYNCING
                self.logger.info(f"{self.sensorName}: Transitioned to SYNCING")

        elif self.state == SensorState.READY_TO_SYNC:
            if event == "sync_command_issued":
                self.state = SensorState.SYNC_ORDERED
                self.logger.info(f"{self.sensorName}: Transitioned to SYNC_ORDERED")
            elif event == "no_longer_ready":
                self.state = SensorState.IDLE
                self.logger.info(f"{self.sensorName}: Transitioned to IDLE")
            elif event == "offline":
                self.state = SensorState.OFFLINE
                self.logger.info(f"{self.sensorName}: Transitioned to OFFLINE")

        elif self.state == SensorState.SYNC_ORDERED:
            if event == "sync_started":
                self.state = SensorState.SYNCING
                self.logger.info(f"{self.sensorName}: Transitioned to SYNCING")
            elif event == "offline":
                self.state = SensorState.OFFLINE
                self.logger.info(f"{self.sensorName}: Transitioned to OFFLINE")
            elif event == "sync_completed":
                self.state = SensorState.IDLE
                self.logger.info(f"{self.sensorName}: Transitioned to IDLE")
            elif event == "update_ready":
                if self.stuckInSyncOrdered > 20:
                    self.logger.error(f"Sensor {self.sensorName} stuck in SyncOrdered")
                    self.state = SensorState.IDLE
                    self.stuckInSyncOrdered = 0 
                else:
                    self.stuckInSyncOrdered += 1



        elif self.state == SensorState.SYNCING:
            if event == "sync_completed":
                self.state = SensorState.IDLE
                self.logger.info(f"{self.sensorName}: Transitioned to IDLE")
            elif event == "sync_failed":
                self.state = SensorState.READY_TO_SYNC
                self.logger.info(f"{self.sensorName}: Transitioned to READY_TO_SYNC")
            elif event == "offline":
                self.state = SensorState.OFFLINE
                self.logger.info(f"{self.sensorName}: Transitioned to OFFLINE")
            elif event == "stuck":
                if self.stuckInSyncing > 30:
                    self.state = SensorState.STUCK
                    self.logger.info(f"{self.sensorName}: Transitioned to OFFLINE after stuck in sync")
                    self.stuckInSyncing = 0
                else:
                    self.stuckInSyncing += 1

        elif self.state == SensorState.STUCK:
            if event == "reboot":
                self.state = SensorState.OFFLINE


        elif self.state == SensorState.OFFLINE:
            if event == "online":
                self.state = SensorState.IDLE
                self.logger.info(f"{self.sensorName}: Transitioned to IDLE")

        # Only update visualization if a transition occurred
        if self.state != previous_state:
            self.update_state_visualization()

    def get_name(self):
        return self.sensorName

    def get_state(self):
        return self.state

    def visualize_state(self):
        """
        Visualizes the current state as a diagram using graphviz.

        Returns:
            graphviz.Digraph: The state machine diagram with the current state highlighted.
        """
        dot = graphviz.Digraph(format='png')
        dot.attr(rankdir='LR')

        # Add nodes
        for state in SensorState:
            if state == self.state:
                dot.node(state.name, shape='doublecircle', style='filled', color='lightblue')
            else:
                dot.node(state.name, shape='circle')

        # Add edges
        dot.edge("IDLE", "READY_TO_SYNC", label="update_ready")
        dot.edge("READY_TO_SYNC", "SYNC_ORDERED", label="sync_command_issued")
        dot.edge("SYNC_ORDERED", "SYNCING", label="sync_started")
        dot.edge("SYNCING", "IDLE", label="sync_completed")
        dot.edge("SYNCING", "READY_TO_SYNC", label="sync_failed")
        dot.edge("READY_TO_SYNC", "IDLE", label="no_longer_ready")
        dot.edge("IDLE", "OFFLINE", label="offline")
        dot.edge("READY_TO_SYNC", "OFFLINE", label="offline")
        dot.edge("SYNC_ORDERED", "OFFLINE", label="offline")
        dot.edge("SYNCING", "OFFLINE", label="offline")
        dot.edge("OFFLINE", "IDLE", label="online")

        return dot

    def update_state_visualization(self):
        """
        Updates the state visualization and logs the HTTP link to the HTML file.
        """
        sensor_folder = os.path.join(SENSORS_DIR, self.sensorName)
        if not os.path.exists(sensor_folder):
            os.makedirs(sensor_folder)

        state_diagram_path = os.path.join(sensor_folder, "current_state.png")

        try:
            # Generate and save the state diagram
            dot = self.visualize_state()
            dot.render(state_diagram_path.replace(".png", ""), format="png", cleanup=True)
            self.logger.info(f"{self.sensorName}: Updated state diagram")

            # Copy HTML template to the sensor folder if it doesn't already exist
            html_path = os.path.join(sensor_folder, "index.html")
            if not os.path.exists(html_path):
                template_file = os.path.join(TEMPLATE_DIR, "index.html")
                if os.path.exists(template_file):
                    shutil.copy(template_file, html_path)
                    self.logger.info(f"{self.sensorName}: Copied HTML template to {html_path}")
                else:
                    self.logger.warning(f"{self.sensorName}: Template file {template_file} not found.")

            # Log the HTTP link to the existing HTML file
            http_link = f"file://{html_path}"
            self.logger.info(f"{self.sensorName}: State visualization available at: {http_link}")

        except Exception as e:
            self.logger.error(f"{self.sensorName}: Failed to update visualization: {e}")

# Main script for managing sensors and states
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SENSORS_DIR = os.path.join(os.getcwd(), "sensor_logs")
TEMPLATE_DIR = os.path.join(BASE_DIR, "templates")

class SensorManager:
    def __init__(self):
        self.logger = BaseLogger(log_file_path=f"SensorManager.log", log_to_console=True).get_logger()

    def ensure_sensor_folder(self, sensor_name):
        """
        Ensure the folder structure for a given sensor exists, and initialize if necessary.
        """
        sensor_folder = os.path.join(SENSORS_DIR, sensor_name)
        if not os.path.exists(sensor_folder):
            os.makedirs(sensor_folder)
            self.logger.info(f"Created folder for {sensor_name}")
        return sensor_folder

def main():
    sensor_manager = SensorManager()
    sensors = ["X22_0C_A6_D2", "X22_1B_C3_F7"]
    state_machines = {sensor: SensorStateMachine(sensor, sensor_manager.logger) for sensor in sensors}

    # Simulate events for each sensor
    events = ["update_ready", "sync_command_issued", "sync_started", "sync_completed", "offline", "online"]
    
    for sensor in sensors:
        for event in events:
            sensor_manager.logger.info(f"Processing {sensor}: {event}")
            state_machines[sensor].transition(event)
            time.sleep(5)  # Sleep for 5 seconds between transitions

if __name__ == "__main__":
    main()
