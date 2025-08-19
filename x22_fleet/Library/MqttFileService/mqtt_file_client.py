import paho.mqtt.client as mqtt
import os
import json
import time
from Library.BaseLogger import *

class MqttFileClient:
    def __init__(self, config_file, log_to_file=True, log_to_console=False):
        with open(config_file, 'r') as f:
            config = json.load(f)
        
        self.broker_address = config['broker_address']
        self.base_topic = config['base_topic']
        self.chunk_size = config['chunk_size']
        self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1)
        self.logger = BaseLogger(log_to_file=log_to_file, log_to_console=log_to_console).get_logger()

    def start(self):
        self.client.connect(self.broker_address)
        self.client.loop_start()

    def send_file(self, file_path):
        # Extract file metadata
        filename = os.path.basename(file_path)
        file_size = os.path.getsize(file_path)
        total_chunks = (file_size + self.chunk_size - 1) // self.chunk_size

        # Send metadata
        metadata = {
            "filename": filename,
            "chunk_size": self.chunk_size,
            "expected_chunks": total_chunks,
        }
        self.client.publish(
            f"{self.base_topic}/control",
            payload=json.dumps(metadata),
            qos=2
        )
        self.logger.info(f"Sent metadata for {filename}")

        # Send file chunks
        with open(file_path, 'rb') as f:
            for sequence in range(total_chunks):
                chunk_data = f.read(self.chunk_size)
                chunk_payload = {
                    "filename": filename,
                    "sequence": sequence,
                    "data": chunk_data.hex(),  # Encode binary data as hex for JSON
                }
                self.client.publish(
                    f"{self.base_topic}/data",
                    payload=json.dumps(chunk_payload),
                    qos=2
                )
                self.logger.info(f"Sent chunk {sequence + 1}/{total_chunks} for {filename}")
                #time.sleep(0.1)  # Prevent flooding the broker

        self.logger.info(f"File {filename} transfer complete.")

    def stop(self):
        self.client.loop_stop()
        self.client.disconnect()


# Example usage
if __name__ == "__main__":
    config_path = "config.json"
    file_path = "example_file.txt"

    client = MqttFileClient(config_path, log_to_file=True, log_to_console=False)
    try:
        client.start()
        client.send_file(file_path)
    finally:
        client.stop()
