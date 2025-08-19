from x22_fleet.Library.StatusListener.SensorStateManager import SensorStateManager
from x22_fleet.Library.StatusListener.MqttHandler import MQTTHandler
from x22_fleet.Library.StatusListener.MessageProcessor import MessageProcessor
from x22_fleet.Library.StatusListener.FileWriter import FileWriter
from x22_fleet.Library.StatusListener.PeriodicTasks import PeriodicTasks
from x22_fleet.Library.StatusListener.GrpcServer import GrpcServer
from x22_fleet.Library.BaseLogger import BaseLogger
from x22_fleet.Library.SshHelper import SshHelper
import argparse, os, json, logging

class StatusListener:
    def __init__(self, broker_address, topics, log_to_file=True, log_to_console=True, credentials_path="credentials.json", debug=False):
        # Initialize logger
        self.logger = BaseLogger(
            log_file_path="StatusListener.log",
            log_to_file=log_to_file,
            log_to_console=log_to_console
        ).get_logger()
        if debug:
            self.logger.setLevel(logging.DEBUG)

        with open(credentials_path, "r") as f:
            credentials = json.load(f)
            logspath = credentials.get("logspath")

        self.file_writer = FileWriter(sensor_log_dir="sensor_logs", logger=self.logger)
        # Initialize components
        self.sensor_state_manager = SensorStateManager(
            file_writer=self.file_writer,
            state_file=f"{logspath}/sensor_logs/sensor_states.json",
            logger=self.logger,
            default_sensor_data={
                'fw': 0, 'v': 0, 'mA': 0, 'soc': 0, 'timeVal': 0,
                'sessions': 0, 'generic_message': "", 'lastseen': 0,
                'updateAge': 0, 'AP': None, 'sync': 0, 'sent': 0,
                'total': 0, 'progress': 0, 'speed': 0, 'speed_calc_time': None,
                'rec': 0, 'fwPending': 0, 'flashFree': 0
            }
        )
        self.message_processor = MessageProcessor(sensor_state_manager=self.sensor_state_manager, logger=self.logger)
        self.mqtt_handler = MQTTHandler(
            broker_address=broker_address,
            topics=topics,
            message_queue=self.message_processor.message_queue,
            logger=self.logger
        )
        self.firmware_updater = SshHelper(credentials_path=credentials_path)
        self.periodic_tasks = PeriodicTasks(
            sensor_state_manager=self.sensor_state_manager,
            logger=self.logger,
            firmware_updater=self.firmware_updater
        )

        self.grpc_server = GrpcServer(sensor_state_manager=self.sensor_state_manager)

    def start(self):
        self.logger.info("Starting Status Listener...")
        self.mqtt_handler.connect()
        self.periodic_tasks.start_tasks()
        self.grpc_server.start()

    def stop(self):
        self.logger.info("Stopping Status Listener...")
        self.mqtt_handler.disconnect()
        self.grpc_server.server.stop(0)

class StatusListenerService:
    def __init__(self, status_listener):
        self.status_listener = status_listener

    def run(self):
        try:
            self.status_listener.start()
            self.status_listener.grpc_server.wait_for_termination()
        except KeyboardInterrupt:
            self.status_listener.stop()


def main():
    parser = argparse.ArgumentParser(description="X22 Status Listener Service")
    parser.add_argument(
        "--credentials",
        type=str,
        default="credentials.json",
        help="Path to the credentials JSON file"
    )
    parser.add_argument(
        "--console",
        action="store_true",
        help="Enable console output (default: False)"
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug level logging"
    )

    args = parser.parse_args()

    with open(args.credentials, "r") as f:
        credentials = json.load(f)
        server = credentials.get("server")

    topics = ["#"]
    status_listener = StatusListener(
        broker_address=server,
        topics=topics,
        log_to_console=args.console,
        credentials_path=args.credentials,
        debug=args.debug
    )

    service = StatusListenerService(status_listener=status_listener)
    service.run()


if __name__ == "__main__":
    main()
