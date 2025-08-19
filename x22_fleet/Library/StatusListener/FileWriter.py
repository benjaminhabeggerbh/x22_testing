import os
import pandas as pd
from threading import Thread
from queue import Queue
import json

class FileWriter:
    def __init__(self, sensor_log_dir, logger):
        self.sensor_log_dir = sensor_log_dir
        self.logger = logger
        self.write_queue = Queue()
        self.worker_thread = Thread(target=self.process_write_queue, daemon=True)
        self.worker_thread.start()
        self.logger.debug("FileWriter worker thread started.")

    def queue_write(self, func, *args):
        try:
            self.logger.debug(f"Queueing write operation for function {func.__name__} with args {args}")
            self.write_queue.put((func, args))
        except Exception as e:
            self.logger.error(f"Failed to queue write operation: {e}")

    def process_write_queue(self):
        self.logger.debug("FileWriter process_write_queue started.")
        while True:
            try:
                self.logger.debug("Waiting for task in queue...")
                task = self.write_queue.get()
                if task is None:
                    self.logger.debug("Received stop signal, exiting queue processor.")
                    break
                func, args = task
                self.logger.debug(f"Processing write operation for function {func.__name__} with args {args}")
                func(*args)
                self.logger.debug(f"Completed write operation for function {func.__name__}")
                self.write_queue.task_done()
            except Exception as e:
                self.logger.error(f"Error processing write queue: {e}")

    def ensure_basepath_exists(self, file_path):
        try:
            base_path = os.path.dirname(file_path)
            self.logger.debug(f"Ensuring base path exists for {file_path}")
            if not os.path.exists(base_path):
                os.makedirs(base_path)
        except Exception as e:
            self.logger.error(f"Failed to ensure base path exists for {file_path}: {e}")

    def write_data_to_csv(self, topic, data):
        try:
            log_dir = f"{self.sensor_log_dir}/{topic}"
            file_path = f"{log_dir}/{topic}.csv"
            self.logger.debug(f"Writing data to CSV for topic {topic} at {file_path}")
            self.ensure_basepath_exists(file_path)
            df_new = pd.DataFrame([data])

            if not os.path.isfile(file_path):
                df_new.to_csv(file_path, mode='w', index=False, header=True)
            else:
                df_new.to_csv(file_path, mode='a', index=False, header=False)
            self.logger.debug(f"Successfully wrote data to CSV for topic {topic}")
        except Exception as e:
            self.logger.error(f"Failed to write data to CSV for topic {topic}: {e}")

    def write_generic_messages_to_file(self, topic, message,timestamp):
        try:
            log_dir = f"{self.sensor_log_dir}/{topic}"
            file_path = f"{log_dir}/messages_{topic}.txt"
            self.logger.debug(f"Writing generic message to file for topic {topic} at {file_path}")
            self.ensure_basepath_exists(file_path)

            if os.path.exists(file_path) and os.path.getsize(file_path) >= 100 * 1024 * 1024:
                base, ext = os.path.splitext(file_path)
                rotated_path = f"{base}_old{ext}"
                self.logger.debug(f"Rotating file {file_path} to {rotated_path}")
                os.rename(file_path, rotated_path)

            with open(file_path, "a") as f:
                f.write(message + "\n")
            self.logger.debug(f"Successfully wrote message to file for topic {topic}")
        except Exception as e:
            self.logger.error(f"Failed to write message to file for topic {topic}: {e}")

    def write_json_to_file(self, file_path, data):
        """Write JSON data to a file using the queue."""
        try:
            self.logger.debug(f"Queueing JSON write operation for file {file_path}")
            self.ensure_basepath_exists(file_path)
            self.queue_write(self._write_json, file_path, data)
        except Exception as e:
            self.logger.error(f"Failed to queue JSON write operation: {e}")

    def _write_json(self, file_path, data):
        try:
            self.logger.debug(f"Writing JSON data to file {file_path}")
            with open(file_path, "w") as f:
                json.dump(data, f, default=str)
            self.logger.debug(f"Successfully wrote JSON data to file {file_path}")
        except Exception as e:
            self.logger.error(f"Failed to write JSON data to file {file_path}: {e}")
