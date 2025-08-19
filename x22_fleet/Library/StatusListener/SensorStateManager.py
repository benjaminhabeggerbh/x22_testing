import json
import pandas as pd
import os
from threading import RLock

class SensorStateManager:
    def __init__(self, state_file, default_sensor_data, file_writer, logger):
        self.state_file = state_file
        self.default_sensor_data = default_sensor_data
        self.file_writer = file_writer
        self.logger = logger
        self.data_store = self.load_state()
        self.lock = RLock()

    def load_state(self):
        if os.path.exists(self.state_file):
            try:
                with open(self.state_file, "r") as f:
                    self.logger.error(f"Loaded state file: {self.state_file}")                                    
                    return json.load(f)
            except Exception as e:
                self.logger.error(f"Failed to load state file: {e}")
        else:
            self.logger.error(f"State file does not exist: {self.state_file}")                
        return {}

    def save_state(self):
        self.logger.debug("Attempting to acquire lock for save_state.")
        with self.lock:
            self.logger.debug("Lock acquired for save_state.")
            try:
                self.logger.debug(f"Saving state to {self.state_file}")
                self.file_writer.write_json_to_file(self.state_file, self.data_store)
            except Exception as e:
                self.logger.error(f"Failed to save state file: {e}")
            finally:
                self.logger.debug("Lock released for save_state.")

    def update_sensor_data(self, topic, data, timestamp):
        self.logger.debug(f"Attempting to acquire lock for update_sensor_data on topic: {topic}.")
        with self.lock:
            self.logger.debug(f"Lock acquired for update_sensor_data on topic: {topic}.")
            if topic not in self.data_store:
                self.logger.debug(f"Topic {topic} not in data_store, initializing with default data.")
                self.data_store[topic] = self.default_sensor_data.copy()

            for key, value in data.items():
                self.data_store[topic][key] = value

            if timestamp is not None:
                self.data_store[topic]['lastseen'] = timestamp

            # Save individual sensor state to a CSV file
            self.logger.debug(f"Writing sensor data for topic {topic} to CSV.")
            self.file_writer.write_data_to_csv(topic, self.data_store[topic])
            self.logger.debug(f"Lock released for update_sensor_data on topic: {topic}.")

    def update_generic_message(self, topic, message,timestamp):
        self.logger.debug(f"Attempting to acquire lock for update_generic_message on topic: {topic}.")
        with self.lock:
            self.logger.debug(f"Lock acquired for update_generic_message on topic: {topic}.")
            if topic not in self.data_store:
                self.logger.debug(f"Topic {topic} not in data_store, initializing with default data.")
                self.data_store[topic] = self.default_sensor_data.copy()

            self.data_store[topic]['generic_message'] = message

            # Save the message to a text file
            self.logger.debug(f"Writing generic message for topic {topic} to file.")
            self.file_writer.write_generic_messages_to_file(topic, message,timestamp)
            self.logger.debug(f"Lock released for update_generic_message on topic: {topic}.")

    def update_last_seen(self):
        self.logger.debug("Attempting to acquire lock for update_last_seen.")
        current_time = pd.Timestamp.now()
        with self.lock:
            self.logger.debug("Lock acquired for update_last_seen.")
            for topic, data in self.data_store.items():
                if 'lastseen' in data and data['lastseen'] is not None:
                    updateAge = round((current_time - pd.Timestamp(data['lastseen'])).total_seconds(), 1)
                    self.data_store[topic]['updateAge'] = updateAge

            # Save the updated state
            self.logger.debug(f"Saving state after updating last seen.")
            self.save_state()
            self.logger.debug("Lock released for update_last_seen.")

    def get_dataframe(self):
        self.logger.debug("Attempting to acquire lock for get_dataframe.")
        with self.lock:
            self.logger.debug("Lock acquired for get_dataframe.")
            df = pd.DataFrame.from_dict(self.data_store, orient='index')
            sorted_df = df.sort_index()

            if 'fwPending' not in sorted_df.columns:
                sorted_df['fwPending'] = 0

            self.logger.debug("Lock released for get_dataframe.")
            return sorted_df

    def get_sensor_data(self, topic):
        self.logger.debug(f"Attempting to acquire lock for get_sensor_data on topic: {topic}.")
        with self.lock:
            self.logger.debug(f"Lock acquired for get_sensor_data on topic: {topic}.")
            data = self.data_store.get(topic, self.default_sensor_data.copy())
            self.logger.debug(f"Lock released for get_sensor_data on topic: {topic}.")
            return data