from PySide6.QtCore import QThread, Signal
from x22_fleet.Library.StatusListener.StatusListenerClient import StatusListenerClient
import json

class StatusListenerThread(QThread):
    dataUpdated = Signal()

    def __init__(self, broker_address, topics, credentials_path="credentials.json"):
        super().__init__()

        with open(credentials_path, "r") as f:
            credentials = json.load(f)
            server = credentials.get("server")

        self.status_listener = StatusListenerClient(server)
        self.previous_data = None
        
    def get_data(self):
        return self.previous_data, self.status_listener.is_online
        
    def run(self):
        updateFirmwarePendingCount = 0
        while True:
            current_data, is_online = self.status_listener.fetch_data()              
            
            # Only emit signal if data has changed
            if not current_data.equals(self.previous_data) or not is_online:
                self.previous_data = current_data 
                self.dataUpdated.emit()
            self.msleep(1000)  # Sleep to reduce update frequency (5 seconds)
