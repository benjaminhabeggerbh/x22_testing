import sys
import os
import argparse
from PySide6.QtCore import QObject, QUrl, Slot, QThread, Signal, Property
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtWidgets import QApplication
from x22_fleet.Library.StatusListener import StatusListener
from x22_fleet.Library.MqttCommander import MqttCommander
from x22_fleet.Library.SshHelper import SshHelper
from x22_fleet.CommanderGui.SensorListModel import *
from x22_fleet.CommanderGui.StatusListenerThread import *
from x22_fleet.Library.BaseLogger import BaseLogger

class CommanderGui(QObject):
    def __init__(self, mqtt_broker_address, mqtt_topics, log_to_console=False):
        super().__init__()

        # Initialize logger
        self.logger = BaseLogger(
            log_file_path="CommanderGui.log",
            log_to_file=True,
            log_to_console=log_to_console
        ).get_logger()
        self.logger.info("Initializing CommanderGui")
        
        self._ap_list = ["All"]
        self._current_filter = "All"
        self._show_only_online = False
        self._sensors_online = 0
        self._sensors_total = 0
        self._status_listener_online = False

        self.mqtt_commander = MqttCommander(mqtt_broker_address)
        self.status_listener_thread = StatusListenerThread(mqtt_broker_address, mqtt_topics)
        self.status_listener_thread.dataUpdated.connect(self.refresh_sensor_data)
        self.status_listener_thread.start()
        self.sshHelper = SshHelper(log_to_console = log_to_console)
        # Load QML engine and set context property
        self.engine = QQmlApplicationEngine()
        self.engine.rootContext().setContextProperty("commanderGui", self)
        self.sensor_list_model = SensorListModel()
        self.engine.rootContext().setContextProperty("sensorListModel", self.sensor_list_model)
        
        # Load QML file relative to the script location
        qml_file_path = os.path.join(os.path.dirname(__file__), "commander_gui.qml")
        self.engine.load(QUrl.fromLocalFile(qml_file_path))

        # Ensure QML loaded properly
        if not self.engine.rootObjects():
            self.logger.error("Failed to load QML file.")
            raise RuntimeError("Failed to load QML file.")
        
        # Get root object
        self.root_object = self.engine.rootObjects()[0]

        # Refresh sensor data initially
        self.refresh_sensor_data()

    # Define the apList property
    def get_ap_list(self):
        return self._ap_list
    
    def set_ap_list(self, value):
        value = sorted(list(set(value)))  # Ensure no duplicates
        if self._ap_list != value:
            self._ap_list = value
            self.apListChanged.emit()

    apListChanged = Signal()
    apList = Property(list, get_ap_list, set_ap_list, notify=apListChanged)

    # Define the sensorsOnline property
    def get_sensors_online(self):
        return self._sensors_online

    def set_sensors_online(self, value):
        if self._sensors_online != value:
            self._sensors_online = value
            self.sensorsOnlineChanged.emit()

    sensorsOnlineChanged = Signal()
    sensorsOnline = Property(int, get_sensors_online, set_sensors_online, notify=sensorsOnlineChanged)

    # Define the sensorsTotal property
    def get_sensors_total(self):
        return self._sensors_total

    def set_sensors_total(self, value):
        if self._sensors_total != value:
            self._sensors_total = value
            self.sensorsTotalChanged.emit()

    sensorsTotalChanged = Signal()
    sensorsTotal = Property(int, get_sensors_total, set_sensors_total, notify=sensorsTotalChanged)

    # Define the statusListenerOnline property
    def get_status_listener_online(self):
        return self._status_listener_online

    def set_status_listener_online(self, value):
        if self._status_listener_online != value:
            self._status_listener_online = value
            self.statusListenerOnlineChanged.emit()

    statusListenerOnlineChanged = Signal()
    statusListenerOnline = Property(bool, get_status_listener_online, notify=statusListenerOnlineChanged)

    # Define the showOnlyOnline property
    def get_show_only_online(self):
        return self._show_only_online

    def set_show_only_online(self, value):
        if self._show_only_online != value:
            self.logger.info(f"Show only online filter changed from {self._show_only_online} to {value}")
            self._show_only_online = value
            self.showOnlyOnlineChanged.emit()
            self.refresh_sensor_data()

    showOnlyOnlineChanged = Signal()
    showOnlyOnline = Property(bool, get_show_only_online, set_show_only_online, notify=showOnlyOnlineChanged)

    # Slot for refreshing sensor data
    @Slot()
    def refresh_sensor_data(self):
        # Get the current DataFrame and online status from StatusListener
        data = self.status_listener_thread.get_data()
        df, is_online = data if isinstance(data, tuple) else (None, False)
        self.set_status_listener_online(is_online)

        if df is None or df.shape[0] == 0:
            self.logger.info("No sensor data available")
            self.set_sensors_online(0)
            self.set_sensors_total(0)
            return

        # Apply the current filter if it's not "All"
        filtered_df = df
        if self._current_filter != "All":
            self.logger.info(f"Filtering data for station: {self._current_filter}")
            filtered_df = df[df["AP"] == self._current_filter]

        # Update the sensorsTotal property
        self.set_sensors_total(filtered_df.shape[0])

        # Further filter for online sensors if showOnlyOnline is enabled
        df_online = filtered_df[filtered_df["updateAge"] < 30]
        self.set_sensors_online(df_online.shape[0])

        if self._show_only_online:
            self.logger.info("Applying online-only filter")
            filtered_df = df_online

        sensor_data = []

        # Add a top row with "-" values to represent actions for all sensors
        top_row = {"name": "AllSensors"}
        for col in filtered_df.columns:
            top_row[col] = "-"
        sensor_data.append(top_row)

        # Add sensors to the list with their properties
        for index, row in filtered_df.iterrows():
            # Create dictionary with at least a "name" key, adding default values if needed
            sensor_info = {"name": str(index) if index is not None else "Unknown"}
            for col in filtered_df.columns:
                sensor_info[col] = str(row[col]) if row[col] is not None else "N/A"
            
            sensor_data.append(sensor_info)
        
        # Update the QML model with sensor data
        self.sensor_list_model.updateData(sensor_data)

        # Update the AP list with unique entries
        unique_aps = self.get_unique_aps(df)
        self.set_ap_list(unique_aps)

    # Function to get unique APs from the unfiltered DataFrame
    def get_unique_aps(self, df):
        unique_aps = set(self._ap_list)  # Start with existing AP list to keep "All"
        unique_aps.update(df["AP"].dropna().unique())
        return list(unique_aps)

    @Slot(str, str, str)
    def deploy_fw_update(self, sensor_name, station, version):
        if self._current_filter == "All":        
            print("Running commands on All sensors is not allowed, filter for a station")
            return

        print(f"deploying fw update for {sensor_name}, {station}, {version}")

        if sensor_name == "AllSensors":
            # Send command to all sensors in the filtered view
            df = self.status_listener_thread.get_data()[0]
            if self._current_filter != "All":
                df = df[df["AP"] == self._current_filter]
            for index in df.index:
                individual_sensor_name = str(index)
                self.sshHelper.deploy_firmware(individual_sensor_name, station, version)
        else:
            self.sshHelper.deploy_firmware(sensor_name, station, version)
        
    # Slot for sending command
    @Slot(str, str)
    def send_command(self, sensor_name, command):
        if self._current_filter == "All":        
            print("Running commands on All sensors is not allowed, filter for a station")
            return
        
        if sensor_name == "AllSensors":
            # Send command to all sensors in the filtered view
            df = self.status_listener_thread.get_data()[0]
            if self._current_filter != "All":
                df = df[df["AP"] == self._current_filter]
            for index in df.index:
                individual_sensor_name = str(index)
                self.mqtt_commander.send_command(individual_sensor_name, command)
        else:
            # Send command to a specific sensor
            self.mqtt_commander.send_command(sensor_name, command)

    # Slot for filtering sensor data
    @Slot(str)
    def filter_changed(self, filter_value):
        if filter_value != self._current_filter:
            self.logger.info(f"Filter changed from '{self._current_filter}' to '{filter_value}'")
            self._current_filter = filter_value
            self.refresh_sensor_data()

    @Slot(str, int, int, result=str)
    def fetch_log_file(self, sensor_name, lines=100, offset=0):
        """
        Fetches the log file for a given sensor using SshHelper.
        
        :param sensor_name: The name of the sensor.
        :param lines: The number of lines to fetch from the log file.
        :param offset: The offset for pagination.
        :return: The requested log lines as a string.
        """
        try:
            self.logger.info(f"Fetching log file for sensor '{sensor_name}' (lines={lines}, offset={offset})")
            logs = str(self.sshHelper.get_log_file(sensor_name, lines, offset))
            self.logger.info(f"Successfully fetched logs for sensor '{sensor_name}'")
            return logs if logs else "No logs available."
        except Exception as e:
            self.logger.error(f"Error fetching logs for sensor '{sensor_name}': {str(e)}")
            return f"Error fetching logs: {e}"

def main():
    parser = argparse.ArgumentParser(description="Commander GUI")
    parser.add_argument("--console", action="store_true", help="Enable logging to console")
    args = parser.parse_args()

    app = QApplication(sys.argv)
    mqtt_broker_address = "167.235.159.207"  # Replace with your broker address
    mqtt_topics = ["#"]  # Replace with your topics of interest
    gui = CommanderGui(mqtt_broker_address, mqtt_topics, log_to_console=args.console)
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
