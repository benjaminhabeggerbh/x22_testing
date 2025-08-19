import sys
import os
from PySide6.QtCore import QObject, QUrl, Slot, QThread, Signal, Property
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtWidgets import QApplication
from x22_fleet.Library.StatusListener import StatusListener
from x22_fleet.Library.MqttCommander import MqttCommander
from x22_fleet.Library.SshHelper import SshHelper
from x22_fleet.CommanderGui.SensorListModel import *
from x22_fleet.CommanderGui.StatusListenerThread import *

class CommanderGui(QObject):
    def __init__(self, mqtt_broker_address, mqtt_topics):
        super().__init__()
        
        self._ap_list = ["All"]
        self._current_filter = "All"
        self.mqtt_commander = MqttCommander(mqtt_broker_address)
        self.status_listener_thread = StatusListenerThread(mqtt_broker_address, mqtt_topics)
        self.status_listener_thread.dataUpdated.connect(self.refresh_sensor_data)
        self.status_listener_thread.start()
        self.sshHelper = SshHelper()
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

    # Slot for refreshing sensor data
    @Slot()
    def refresh_sensor_data(self):
        # Get the current DataFrame from StatusListener
        df = self.status_listener_thread.status_listener.get_dataframe()
        sensor_data = []

        # Add a top row with "-" values to represent actions for all sensors
        top_row = {"name": "AllSensors"}
        for col in df.columns:
            top_row[col] = "-"
        sensor_data.append(top_row)

        # Apply the current filter if it's not "All"
        if self._current_filter != "All":
            df = df[df["AP"] == self._current_filter]

        # Add sensors to the list with their properties
        for index, row in df.iterrows():
            # Create dictionary with at least a "name" key, adding default values if needed
            sensor_info = {"name": str(index) if index is not None else "Unknown"}
            for col in df.columns:
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
    def deploy_fw_update(self, sensor_name,station,version):
        if self._current_filter == "All":        
            print("Running commands on All sensors is not allowed, filter for a station")
            return

        print(f"deploying fw update for {sensor_name}, {station}, {version}")

        if sensor_name == "AllSensors":
            # Send command to all sensors in the filtered view
            df = self.status_listener_thread.status_listener.get_dataframe()
            if self._current_filter != "All":
                df = df[df["AP"] == self._current_filter]
            for index in df.index:
                individual_sensor_name = str(index)
                self.sshHelper.deploy_firmware(individual_sensor_name,station,version)
        else:
            self.sshHelper.deploy_firmware(sensor_name,station,version)
        
    # Slot for sending command
    @Slot(str, str)
    def send_command(self, sensor_name, command):
        if self._current_filter == "All":        
            print("Running commands on All sensors is not allowed, filter for a station")
            return
        
        if sensor_name == "AllSensors":
            # Send command to all sensors in the filtered view
            df = self.status_listener_thread.status_listener.get_dataframe()
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
            print("filter changed: " + filter_value)
            self._current_filter = filter_value
            self.refresh_sensor_data()

def main():
    app = QApplication(sys.argv)
    mqtt_broker_address = "167.235.159.207"  # Replace with your broker address
    mqtt_topics = ["#"]  # Replace with your topics of interest
    gui = CommanderGui(mqtt_broker_address, mqtt_topics)
    sys.exit(app.exec())

if __name__ == "__main__":
    main()