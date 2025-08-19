from PySide6.QtCore import QThread, Signal
from x22_fleet.Library.StatusListener import StatusListener

class StatusListenerThread(QThread):
    dataUpdated = Signal()

    def __init__(self, broker_address, topics, credentials_path="credentials.json"):
        super().__init__()
        self.status_listener = StatusListener(broker_address, topics,credentials_path=credentials_path)

        self.previous_data = None

    def run(self):
        updateFirmwarePendingCount = 0
        while True:
            # Continuously update the data frame
            self.status_listener.update_last_seen()
            if updateFirmwarePendingCount == 5:
                self.status_listener.update_sensors_firmware_pending()
                updateFirmwarePendingCount = 0
            else:
                updateFirmwarePendingCount +=1

            current_data = self.status_listener.get_dataframe()
          
                
            
            # Only emit signal if data has changed
            if not current_data.equals(self.previous_data):
                self.previous_data = current_data
                self.dataUpdated.emit()
            self.msleep(1000)  # Sleep to reduce update frequency (5 seconds)
