import paramiko
import json
from x22_fleet.Library.BaseLogger import BaseLogger

class SshHelper:
    def __init__(self, credentials_path="credentials.json",log_to_console=False):
        """
        Initializes the SSH helper by loading server credentials from a JSON file.
        """
        # Load credentials
        with open(credentials_path, "r") as f:
            credentials = json.load(f)
        
        self.server = credentials.get("server")  # Assuming same field for server address
        self.username = credentials.get("username")
        self.password = credentials.get("password")
        self.basepath = credentials.get("basepath")
        self.logspath = credentials.get("logspath")    
        self.ftppath = self.basepath + "/ftp"
        self.firmwarepath = self.ftppath + "/firmware"
        self.sensorlogspath = self.logspath + "/sensor_logs"
        self.logger = BaseLogger(log_file_path=f"SshHelper.log", log_to_console=log_to_console).get_logger()
        
        # Validate credentials
        if not all([self.server, self.username, self.password]):
            raise ValueError("Invalid credentials in the JSON file.")
        
        self.client = None

    def connect(self):
        """
        Establishes an SSH connection to the server.
        """
        try:
            self.client = paramiko.SSHClient()
            self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            self.client.connect(hostname=self.server, username=self.username, password=self.password)
            self.logger.info(f"Connected to {self.server} as {self.username}")

        except Exception as e:
            raise ConnectionError(f"Failed to connect to {self.server}: {e}")

    def run_command(self, command, silent=True):
        """
        Executes a command on the server and returns its output.
        """
        if not self.client:
            self.connect()
        
        try:
            stdin, stdout, stderr = self.client.exec_command(command)
            output = stdout.read().decode().strip()
            error = stderr.read().decode().strip()
            result = f"{output}|{error}"
            if not silent:
                if error:
                    self.logger.info(f"Error executing command: {error}")
                self.logger.info(f"{command} | {result}")
            return result
        
        except Exception as e:
            raise RuntimeError(f"Failed to execute command: {e}")

    def deploy_firmware(self, sensor_name, station, version):
        try:
            command = f"cp {self.firmwarepath}/{version}/X22-Firmware-{version}-{station}.bin {self.firmwarepath}/{sensor_name}.bin"
            self.run_command(command, silent=False)
        except Exception as ex:
            self.logger.error(f"Exception deploying firmware: {ex}")

    def get_pending_updates(self):
        """
        Checks if a firmware update file exists for the given sensor.
        """
        command = f"ls {self.firmwarepath}/*.bin"
        return self.run_command(command)

    def check_update_pending(self, sensor_name):
        """
        Checks if a firmware update file exists for the given sensor.
        """
        command = f"test -f {self.firmwarepath}/{sensor_name}.bin && echo pending"
        return "pending" in self.run_command(command)

    def get_log_file(self, sensor_name, lines=100, offset=0):
        """
        Retrieves the log file for a given sensor with pagination support, 
        showing the latest logs on top.

        :param sensor_name: The name of the sensor.
        :param lines: The number of lines to fetch from the end of the log file.
        :param offset: The number of lines to skip from the end of the file.
        :return: The requested log lines in reverse order or None if an error occurs.
        """
        log_file_path = f"{self.sensorlogspath}/{sensor_name}/messages_{sensor_name}.txt"
        command = f"tail -n {offset + lines} {log_file_path} | head -n {lines} | tac"
        try:
            logs = self.run_command(command, silent=False)
            return logs
        except Exception as e:
            self.logger.info(f"Failed to retrieve log file for {sensor_name}: {e}")
            return None

    def disconnect(self):
        """
        Closes the SSH connection.
        """
        if self.client:
            self.client.close()
            self.client = None
            self.logger.info(f"Disconnected from {self.server}")
