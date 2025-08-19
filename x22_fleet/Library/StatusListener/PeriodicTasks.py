import time
from threading import Thread
import pandas as pd

class PeriodicTasks:
    def __init__(self, sensor_state_manager, logger, firmware_updater):
        self.sensor_state_manager = sensor_state_manager
        self.logger = logger
        self.firmware_updater = firmware_updater
        self.threads = []

    def start_tasks(self):
        self.threads.append(Thread(target=self.periodic_update_last_seen, daemon=True))
        self.threads.append(Thread(target=self.periodic_update_firmware_pending, daemon=True))
        self.threads.append(Thread(target=self.periodic_save_state, daemon=True))

        for thread in self.threads:
            thread.start()

    def periodic_update_last_seen(self):
        while True:
            try:
                self.sensor_state_manager.update_last_seen()
            except Exception as e:
                self.logger.error(f"Error in periodic update of last seen: {e}")
            time.sleep(1)  # Update every 1 second

    def periodic_update_firmware_pending(self):
        while True:
            try:
                updates_pending = self.firmware_updater.get_pending_updates()
                for sensor in self.sensor_state_manager.data_store.keys():
                    is_pending = sensor in updates_pending
                    self.sensor_state_manager.update_sensor_data(sensor, {'fwPending': int(is_pending)}, None)
            except Exception as e:
                self.logger.error(f"Error in periodic firmware pending update: {e}")
            time.sleep(5)  # Update every 5 seconds

    def periodic_save_state(self):
        while True:
            try:
                self.sensor_state_manager.save_state()
            except Exception as e:
                self.logger.error(f"Error in periodic state saving: {e}")
            time.sleep(5)  # Save state every 5 seconds