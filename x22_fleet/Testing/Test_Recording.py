# conftest.py
import pytest
import json, time
from x22_fleet.Library.StatusListener.StatusListenerClient import StatusListenerClient
from x22_fleet.Testing.SensorStats import SensorStats
from x22_fleet.Library.BaseLogger import BaseLogger
from x22_fleet.Library.MqttCommander import MqttCommander
#from x22_fleet.Testing.DataFileTester import DataFileTester
#from DataFileTester import DataFileTester

@pytest.fixture(scope="session")
def setup_environment():
    # Setup code for initializing the environment
    topics = ["#"]

    with open("credentials.json", "r") as f:
        credentials = json.load(f)
        server = credentials.get("server")

    listener = StatusListenerClient(server)
    sensorStats = SensorStats(listener, "EvoStationMaintenance")
    numberOfSensors = 20
    logger = BaseLogger(log_file_path="TestRecording.log", log_to_file=True, log_to_console=True).get_logger()
    mqtt_commander = MqttCommander(server)

    return {
        "listener": listener,
        "sensorStats": sensorStats,
        "numberOfSensors": numberOfSensors,
        "logger": logger,
        "commander": mqtt_commander,
    }

@pytest.fixture(scope="session", autouse=True)
def initialize_globals(setup_environment):
    # Set up global variables
    global listener, sensorStats, numberOfSensors, logger, commander, data_file_tester
    listener = setup_environment["listener"]
    sensorStats = setup_environment["sensorStats"]
    numberOfSensors = setup_environment["numberOfSensors"]
    logger = setup_environment["logger"]
    commander = setup_environment["commander"]
    data_file_tester = "nothing"
    #data_file_tester = DataFileTester()

# test_status_listener.py
import time

def test_empty():
    logger.info("Checking if listener is initialized.")
    assert listener is not None

def test_enumerate_sensors():
    logger.info("Testing connection to statuslistener")
    assert sensorStats.statusListenerOnline()

def test_count_sensors_online(record_property):
    happy = False
    while not happy:
        online_sensors = sensorStats.count_sensors_online()
        logger.info(f"Waiting for sensors to be online. Number of online sensors: {online_sensors}")
        happy = online_sensors >= numberOfSensors
        record_property("online_sensors", online_sensors)        
        time.sleep(60)

    assert online_sensors >= numberOfSensors

def test_start_recording():
    logger.info("Sending 'enable_force_record' command to all sensors.")
    send_command(commander, sensorStats.get_sensors_online(),"enable_force_record")
    assert True

def test_wait_10_seconds():
    logger.info("Waiting for 10 seconds.")
    time.sleep(10)
    assert True

def test_stop_recording():
    logger.info("Sending 'disable_force_record' command to all sensors.")
    send_command(commander, sensorStats.get_sensors_online(),"disable_force_record")
    time.sleep(10)
    assert True

def test_wait_for_uploads_to_finish():
    time.sleep(30)
    happy = False
    while not happy:
        numberofSessionsOnSensors = sensorStats.count_sensors_with_sessions()
        logger.info(f"Waiting for uploads to finish, remaining: {numberofSessionsOnSensors}.")
        happy = numberofSessionsOnSensors == 0
        time.sleep(10)

    assert listener is not None

def test_wait_before_next_iteration():
    logger.info("Waiting for 60 seconds.")
    time.sleep(60)
    assert True

# def test_count_files():
#     logger.info("Counting files uploaded.")
#     data_dir = "/path/to/data"  # Replace with actual data directory
#     file_count = data_file_tester.count_files(data_dir)
#     logger.info(f"Number of files in '{data_dir}': {file_count}")
#     assert file_count > 0

# def test_analyze_files():
#     logger.info("Analyzing uploaded files.")
#     data_dir = "/path/to/data"  # Replace with actual data directory
#     analysis_results = data_file_tester.analyze_files(data_dir)
#     logger.info(f"Analysis results for files in '{data_dir}': {analysis_results}")
#     assert analysis_results is not None

def send_command(commander,df, command):
    # Send command to all sensors in the filtered view
    for index in df.index:
        individual_sensor_name = str(index)
        logger.info(f"Sending '{command}' to {individual_sensor_name}")
        commander.send_command(individual_sensor_name, command)
