import unittest
import os
import time
import threading
import json
from mqtt_file_client import MqttFileClient  # Assuming MqttFileClient is in a separate file
from mqtt_file_server import MqttFileServer  # Assuming MqttFileServer is in a separate file
from tqdm import tqdm  # Import tqdm for progress bar

class TestMqttFileTransfer(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config_path = os.path.join(os.path.dirname(__file__), "config.json")
        with open(cls.config_path, 'r') as f:
            cls.config = json.load(f)
        cls.save_directory = cls.config.get('save_directory', './received_files')
        cls.file_path = "test_file.bin"

        # Start the server in a separate thread
        cls.server = MqttFileServer(cls.config_path,log_to_console=False)
        cls.server_thread = threading.Thread(target=cls.server.start)
        cls.server_thread.daemon = True
        cls.server_thread.start()
        time.sleep(1)  # Give server time to start

    @classmethod
    def tearDownClass(cls):
        # Stop the server
        cls.server.client.loop_stop()
        cls.server.client.disconnect()
        # Remove the test file
        if os.path.exists(cls.file_path):
            os.remove(cls.file_path)
        # Remove received file
        received_file_path = os.path.join(cls.save_directory, os.path.basename(cls.file_path))
        if os.path.exists(received_file_path):
            os.remove(received_file_path)

    def create_binary_file(self, size_mb):
        # Create a binary test file of the specified size
        with open(self.file_path, "wb") as f:
            f.write(os.urandom(size_mb * 1024 * 1024))

    def test_file_transfer_1mb(self):
        self.create_binary_file(1)  # Create a 1 MB file
        self.perform_file_transfer(1)

    def test_file_transfer_10mb(self):
        self.create_binary_file(10)  # Create a 10 MB file
        self.perform_file_transfer(10)

    # def test_file_transfer_25mb(self):
    #     self.create_binary_file(25)  # Create a 25 MB file
    #     self.perform_file_transfer(25)

    # def test_file_transfer_50mb(self):
    #     self.create_binary_file(50)  # Create a 50 MB file
    #     self.perform_file_transfer(50)

    def perform_file_transfer(self, size_mb):
        # Start the client and send the file
        client = MqttFileClient(self.config_path,log_to_console=True)
        client.start()

        # Show progress bar
        total_chunks = (size_mb * 1024 * 1024 + client.chunk_size - 1) // client.chunk_size
        with tqdm(total=total_chunks, desc="Transferring File", unit="chunk") as pbar:
            original_send_file = client.send_file

            def send_file_with_progress(*args, **kwargs):
                original_send_file(*args, **kwargs)
                for _ in range(total_chunks):
                    pbar.update(1)

            client.send_file = send_file_with_progress
            client.send_file(self.file_path)

        # Wait for the server to finish receiving
        while  self.server.transfer_in_progress(os.path.basename(self.file_path)):
            time.sleep(1)  # Adjust time as needed based on file size and network speed
            print("waiting for transfer to be complete")

        client.stop()

        # Check if the file was received correctly
        received_file_path = os.path.join(self.server.save_directory, os.path.basename(self.file_path))
        self.assertTrue(os.path.exists(received_file_path))
        with open(received_file_path, "rb") as f:
            received_content = f.read()
        with open(self.file_path, "rb") as f:
            original_content = f.read()
        self.assertEqual(received_content, original_content)

if __name__ == "__main__":
    unittest.main()
