import pandas as pd
import time, argparse, os, json
from datetime import datetime
from x22_fleet.Library.StatusListener import StatusListener
from x22_fleet.Library.MqttCommander import MqttCommander
from x22_fleet.Library.SshHelper import SshHelper
from x22_fleet.Library.BaseLogger import BaseLogger
import threading
from colorama import Fore, Style

class Distributor:
    def __init__(self, station_name = "EvoStationMaintenance", parallelUploads = 6, broker_address="167.235.159.207", topics=["#"],credentials_path="credentials.json"):
        self.broker_address = broker_address
        self.topics = topics
        self.station_name = station_name
        # Initialize StatusListener
        self.status_listener = StatusListener(self.broker_address, self.topics)
        self.mqtt_commander = MqttCommander(self.broker_address)
        self.updateThreshold = 5
        self.parallelUploads = parallelUploads
        self.sshHelper = SshHelper(credentials_path=credentials_path)
        self.sensors_df = pd.DataFrame()
        self.logger = BaseLogger(log_file_path=f"Distributor.{station_name}.log",log_to_console=False).get_logger()
        self.updateFirmwarePendingCount = 0

    def update_sensors(self):
        """
        Fetch sensor data from StatusListener and update the DataFrame.
        """

        if  self.updateFirmwarePendingCount == 5:
            self.status_listener.update_sensors_firmware_pending()
            self.updateFirmwarePendingCount = 0
        else:
             self.updateFirmwarePendingCount +=1

        # First filter by station
        self.all_sensors_df = self.status_listener.get_dataframe()
        self.sensors_df  = self.all_sensors_df[self.all_sensors_df["AP"] == self.station_name]


        # Then by state
        self.sensors_online  = self.sensors_df[self.sensors_df["updateAge"] < self.updateThreshold]        
        self.sensors_synced  = self.sensors_df[ (self.sensors_df["sessions"] == 0) & (self.sensors_df["fwPending"] == 0)]        
        self.sensors_online_and_synced = self.sensors_df[
            (self.sensors_df["sessions"] == 0) & (self.sensors_df["updateAge"] < self.updateThreshold) & (self.sensors_df["fwPending"] == 0)
        ]

        self.sensors_ready_to_sync  = self.sensors_df[
            (self.sensors_df["updateAge"] < self.updateThreshold) & ( (self.sensors_df["sessions"] > 0) | (self.sensors_df["fwPending"] == 1) ) & (self.sensors_df["sync"] == 0) & ((self.sensors_df["rec"] == 0) | pd.isna(self.sensors_df["rec"]))
        ]        

        self.sensors_syncing  = self.sensors_df[
            (self.sensors_df["sync"] == 1 )
        ]             

        self.distributeSync()

    def distributeSync(self):
        # send sen
        if len(self.sensors_ready_to_sync) > 0:
            for sensor_name in self.sensors_online_and_synced.index:
                self.mqtt_commander.send_command(sensor_name,"wifi_sleep")
            
            if len(self.sensors_syncing) < self.parallelUploads:
                if len(self.sensors_ready_to_sync) > 0:
                    sensorToStart = self.sensors_ready_to_sync.index[0]     
                    self.mqtt_commander.send_command(sensorToStart,"sync")
                    self.logger.info(f"start sync on {sensorToStart}")
                    time.sleep(5)

    def display_sensors(self):
        """
        self.logger.info the DataFrame to the console.
        """
        columns_to_display = ["AP", "fw", "updateAge", "sessions", "fwPending", "sync", "rec"]

        self.logger.info("======= Sensors Online ==================\n")
        self.logger.info(f"\n{self.sensors_online[columns_to_display]}")

        self.logger.info("======= Sensors Synced and Online (send to wifi sleep)  ==================\n")
        self.logger.info(f"\n{self.sensors_online_and_synced[columns_to_display]}")

        self.logger.info("======= Sensors ready to sync  ==================\n" )
        self.logger.info(f"\n{self.sensors_ready_to_sync[columns_to_display]}")
   
        self.logger.info("======= Sensors uploading  ==================\n" )
        self.logger.info(f"\n{self.sensors_syncing[columns_to_display]}")

    def run(self):
        current_time = datetime.now()

        while True:
            # Update sensor data from the StatusListener
            self.update_sensors()
            self.display_sensors()

            # Wait for the next update
            time.sleep(3)

def main(LogToConsole = False):
    logger = BaseLogger(log_file_path="DistributorMain.log",log_to_console=LogToConsole).get_logger()
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
        default="distributor.json",
        help="Path to the distributor JSON file"
    )
    args = parser.parse_args()

    current_path = os.getcwd()

    logger.info(f"x22 Distributor, currentpath: {current_path}")

    with open(args.credentials, "r") as f:
        credentials = json.load(f)
        server = credentials.get("server")

    with open(args.config, "r") as f:
        config = json.load(f)
    
    distributorThreads = []
    for distributorInstance in config:
        logger.info(f"creating Distributor instance {distributorInstance['name']}, parallel Uploads: {distributorInstance['parallelUploads']}")
        distributor = Distributor(station_name=distributorInstance['name'], parallelUploads=distributorInstance['parallelUploads'], credentials_path=args.credentials)
        t = threading.Thread(target=distributor.run)
        t.start()
        distributorThreads.append(distributorThreads)
    
    while True:
        time.sleep(1)

if __name__ == "__main__":
    main(LogToConsole=True)
