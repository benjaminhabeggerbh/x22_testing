import paho.mqtt.client as mqtt
import os
import json
import threading
from Library.BaseLogger import *

class MqttFileServer:
    def __init__(self, config_file,log_to_file=True, log_to_console=False, log_file_path="application.log"):
        with open(config_file, 'r') as f:
            config = json.load(f)
        
        self.broker_address = config['broker_address']
        self.base_topic = config['base_topic']
        self.save_directory = config['save_directory']
        self.file_data = {}  # Tracks file assembly state
        self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1)
        self.logger = BaseLogger(log_to_file=log_to_file, log_to_console=log_to_console).get_logger()

    def transfer_in_progress(self, filename):
        # Check if any file is being received but not yet completed
        file_info = self.file_data.get(filename)
        if file_info and len(file_info['chunks']) < file_info['expected_chunks']:
            return True
        return False

    def start(self):
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.client.connect(self.broker_address)
        self.client.loop_start()

    def on_connect(self, client, userdata, flags, rc):
        self.logger.info(f"Connected with result code {rc}")
        self.client.subscribe(f"{self.base_topic}/#")

    def on_message(self, client, userdata, msg):
        topic = msg.topic
        if topic.endswith('/control'):
            self.handle_metadata(msg.payload)
        elif topic.endswith('/data'):
            self.handle_chunk(msg.payload)

    def handle_metadata(self, payload):
        # Decode metadata (assume JSON or a similar format)
        metadata = self.parse_metadata(payload)
        filename = metadata['filename']
        chunk_size = metadata['chunk_size']
        # Initialize tracking for this file
        self.file_data[filename] = {
            'chunks': {},
            'chunk_size': chunk_size,
            'expected_chunks': metadata.get('expected_chunks', -1),
        }
        self.logger.info(f"Initialized file transfer for {filename}")

    def handle_chunk(self, payload):
        # Decode chunk data
        chunk_info = self.parse_chunk(payload)
        filename = chunk_info['filename']
        sequence = chunk_info['sequence']
        data = chunk_info['data']
        # Write chunk data to temporary storage
        if filename in self.file_data:
            self.file_data[filename]['chunks'][sequence] = data
            self.logger.info(f"Received chunk {sequence} for {filename}")
        # Check if all chunks are received and reassemble
        self.check_file_completion(filename)

    def check_file_completion(self, filename):
        file_info = self.file_data.get(filename)
        if file_info:
            all_chunks_received = (
                file_info['expected_chunks'] > 0 and
                len(file_info['chunks']) == file_info['expected_chunks']
            )
            if all_chunks_received:
                self.reassemble_file(filename)

    def reassemble_file(self, filename):
        file_info = self.file_data[filename]
        path = os.path.join(self.save_directory, filename)
        with open(path, 'wb') as f:
            for seq in sorted(file_info['chunks']):
                f.write(file_info['chunks'][seq])
        self.logger.info(f"File {filename} successfully reassembled")
        del self.file_data[filename]

    @staticmethod
    def parse_metadata(payload):
        # Implement payload parsing (e.g., JSON or custom binary format)
        return json.loads(payload)

    @staticmethod
    def parse_chunk(payload):
        # Implement chunk parsing (e.g., binary decoding)
        chunk_info = json.loads(payload)
        return {
            'filename': chunk_info['filename'],
            'sequence': chunk_info['sequence'],
            'data': bytes.fromhex(chunk_info['data']),
        }


# Example usage
if __name__ == "__main__":
    config_path = os.path.join(os.path.dirname(__file__), "config.json")

    server = MqttFileServer(config_path,log_to_console=False)
    server.start()
