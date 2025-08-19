# conftest.py
import pytest
import json, time
from Library.StatusListener import StatusListener
from Library.SensorStats import SensorStats
from Library.BaseLogger import BaseLogger

@pytest.fixture(scope="session")
def setup_environment():
    # Setup code for initializing the environment
    topics = ["#"]

    with open("credentials.json", "r") as f:
        credentials = json.load(f)
        server = credentials.get("server")

    listener = StatusListener(server, topics, log_to_console=True)
    sensorStats = SensorStats(listener, "EvoStationMaintenance")
    numberOfSensors = 49
    logger = BaseLogger(log_file_path="TestRecording.log",log_to_file=True, log_to_console=True).get_logger()

    return {
        "listener": listener,
        "sensorStats": sensorStats,
        "numberOfSensors": numberOfSensors,
        "logger": logger,
    }

@pytest.fixture(scope="session", autouse=True)
def initialize_globals(setup_environment):
    # Set up global variables
    global listener, sensorStats, numberOfSensors, logger
    listener = setup_environment["listener"]
    sensorStats = setup_environment["sensorStats"]
    numberOfSensors = setup_environment["numberOfSensors"]
    logger = setup_environment["logger"]


# test_status_listener.py
import time

def test_empty():
    assert listener is not None

def test_enumerate_sensors():
    logger.info("Waiting for sensors to enumerate")
    time.sleep(10)
    assert True

def test_count_sensors_online():
    assert sensorStats.count_sensors() == numberOfSensors

def test_start_recording():
    assert listener is not None

def test_wait_5_minutes():
    assert listener is not None

def test_stop_recording():
    assert listener is not None

def test_wait_for_uploads_to_finish():
    assert listener is not None

def test_count_files():
    assert listener is not None

def test_analyze_files():
    assert listener is not None
