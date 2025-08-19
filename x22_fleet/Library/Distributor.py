import pandas as pd
import time, argparse, os, json
from datetime import datetime
from x22_fleet.Library.StatusListener.StatusListenerClient import StatusListenerClient
from x22_fleet.Library.MqttCommander import MqttCommander
from x22_fleet.Library.SshHelper import SshHelper
from x22_fleet.Library.BaseLogger import BaseLogger
from x22_fleet.Library.DistributorGui import DistributorGui
from x22_fleet.Library.SensorState.SensorState import SensorState, SensorStateMachine
import threading

class Distributor:
    def __init__(self, station_name="EvoStation1", parallelUploads=6, broker_address="167.235.159.207", credentials_path="credentials.json"):
        self.broker_address = broker_address
        self.station_name = station_name
        self.parallelUploads = parallelUploads
        self.status_listener = StatusListenerClient(self.broker_address)
        self.mqtt_commander = MqttCommander(self.broker_address)
        self.updateThreshold = 30
        self.uploadTimeout = 30  # Timeout for detecting stuck uploads
        self.sshHelper = SshHelper(credentials_path=credentials_path)
        self.logger = BaseLogger(log_file_path=f"Distributor.{station_name}.log", log_to_console=True).get_logger()

        self.sensors = {}  # Sensor state machines
        self.sensors_df = pd.DataFrame()
        self.last_progress = {}  # Tracks last progress timestamp for sensors

        # Load credentials
        with open(credentials_path, "r") as f:
            credentials = json.load(f)
        self.server = credentials.get("server")  # Assuming same field for server address
        self.username = credentials.get("username")
        self.password = credentials.get("password")
        self.basepath = credentials.get("basepath")
        self.logspath = credentials.get("logspath")
        self.ftppath = self.basepath + "/ftp"

        # Initialize upload directory
        self.init_upload_dir()

    def init_upload_dir(self):
        """
        Ensures that the directory for the station name exists under ftppath/transfers.
        """
        station_dir = os.path.join(self.ftppath, "transfers", self.station_name)
        try:
            if not os.path.exists(station_dir):
                os.makedirs(station_dir)
                self.logger.info(f"Created upload directory for station: {station_dir}")
            else:
                self.logger.info(f"Upload directory already exists: {station_dir}")
        except Exception as e:
            self.logger.error(f"Failed to create upload directory: {e}")



    def distributeSync(self):
        syncing_count = sum(1 for sm in self.sensors.values() if sm.get_state() == SensorState.SYNCING or sm.get_state() == SensorState.SYNC_ORDERED)
        ready_sensors = [name for name, sm in self.sensors.items() if sm.get_state() == SensorState.READY_TO_SYNC]
        idle_sensors = [name for name, sm in self.sensors.items() if sm.get_state() == SensorState.IDLE]

        for sensor_name in ready_sensors:
            if syncing_count < self.parallelUploads:
                self.mqtt_commander.send_command(sensor_name, "sync")
                self.sensors[sensor_name].transition("sync_command_issued")
                syncing_count += 1
            else:
                self.mqtt_commander.send_command(sensor_name, "wifi_sleep")
        
        if len(ready_sensors) > 0 or syncing_count > 0:
            for sensor_name in idle_sensors:
                self.mqtt_commander.send_command(sensor_name, "wifi_sleep")                  

    def get_sensors(self):
        sensor_data = []
        for _, row in self.sensors_df.iterrows():
            state = row.get("state", "UNKNOWN")
            progress = round(row.get("progress", 0) * 100, 2)  # Convert progress to percentage
            speed = round(row.get("speed", 0), 2)             # Ensure speed is displayed as a float
            sensor_data.append({"name": row['SensorName'], "state": state, "progress": progress, "speed": speed})

        # Custom order of states: syncing, syncordered, ready_to_sync, stuck, idle, offline
        state_order = {"SYNCING": 1, "SYNC_ORDERED": 2, "READY_TO_SYNC": 3, "STUCK": 4, "IDLE": 5, "OFFLINE": 6}
        return sorted(sensor_data, key=lambda x: state_order.get(x["state"].upper(), 99))

    def update_sensors(self):
        try:
            self.all_sensors_df, online = self.status_listener.fetch_data()

            if not online:
                self.logger.error("StatusListenerClient of Distributor instance not connected.")
                return

            self.sensors_df = self.all_sensors_df[self.all_sensors_df["AP"] == self.station_name].copy()
            self.sensors_df.reset_index(inplace=True)
            self.sensors_df.rename(columns={"index": "SensorName"}, inplace=True)

            current_time = time.time()

            for _, row in self.sensors_df.iterrows():
                sensor_name = row['SensorName']
                if sensor_name not in self.sensors:
                    self.sensors[sensor_name] = SensorStateMachine(sensor_name, logger=self.logger)
                    self.last_progress[sensor_name] = {"progress": 0, "last_update_time": current_time}

                state_machine = self.sensors[sensor_name]
                sensor_progress = row.get("progress", 0)

                # Online trigger
                if row["updateAge"] > self.updateThreshold:
                    state_machine.transition("offline")
                else:
                    state_machine.transition("online")

                # Check stuck condition (only during upload)
                if state_machine.get_state() == SensorState.SYNCING:
                    if sensor_progress != self.last_progress[sensor_name]["progress"]: #explanation: progress may also be smaller since we rolled over to the next file and restarted at zero
                        # Progress updated, reset timeout
                        self.last_progress[sensor_name] = {"progress": sensor_progress, "last_update_time": current_time}
                    elif current_time - self.last_progress[sensor_name]["last_update_time"] > self.uploadTimeout:
                        state_machine.transition("stuck")

                # Check stuck condition (only during upload)
                if state_machine.get_state() == SensorState.STUCK:
                        self.mqtt_commander.send_command(sensor_name, "reboot")                        
                        state_machine.transition("reboot")
                        self.logger.warning(f"Sensor {sensor_name} is stuck on upload, will reboot")
                        self.mqtt_commander.send_command(sensor_name, "reboot")                        


                # Handle other state transitions
                if row["sync"] == 1:
                    state_machine.transition("sync_started")
                elif row["sync"] == 0 and row["fwPending"] == 0 and row["sessions"] == 0:
                    state_machine.transition("sync_completed")
                elif row["sync"] == 0 and ( row["sessions"] > 0 or row["fwPending"] > 0 ):
                    state_machine.transition("update_ready")
                else:
                    state_machine.transition("idle")

                # Update the DataFrame with the current state
                self.sensors_df.loc[self.sensors_df["SensorName"] == sensor_name, "state"] = state_machine.get_state().name

        except Exception as ex:
            self.logger.warning(f"Exception updating sensors: {ex}")


    def run(self):
        while True:
            try:
                self.update_sensors()
                self.distributeSync()
            except Exception as ex:
                self.logger.error(f"Error in Distributor run loop: {ex}")

            time.sleep(3)

def main(LogToConsole=False):
    logger = BaseLogger(log_file_path="DistributorMain.log", log_to_console=LogToConsole).get_logger()
    parser = argparse.ArgumentParser(description="X22 Status Listener Service")
    parser.add_argument(
        "--credentials",
        type=str,
        default="credentials.json",
        help="Path to the credentials JSON file"
    )
    parser.add_argument(
        "--config",
        type=str,
        default="config/distributor.json",
        help="Path to the distributor JSON file"
    )

    args = parser.parse_args()
    logger.info(f"Arguments passed: {args}")

    current_path = os.getcwd()
    logger.info(f"x22 Distributor, current path: {current_path}")

    with open(args.config, "r") as f:
        config = json.load(f)

    base_port = 5100

    distributors = []
    for distributor_instance in config:
        logger.info(f"Creating Distributor instance {distributor_instance['name']}, parallel Uploads: {distributor_instance['parallelUploads']}")
        distributor = Distributor(
            station_name=distributor_instance['name'],
            parallelUploads=distributor_instance['parallelUploads'],
            credentials_path=args.credentials
        )
        distributors.append(distributor)
        threading.Thread(target=distributor.run, daemon=True).start()

    gui = DistributorGui(distributors, base_port, LogToConsole)
    gui.run()

    while True:
        time.sleep(1)

if __name__ == "__main__":
    main(LogToConsole=True)
