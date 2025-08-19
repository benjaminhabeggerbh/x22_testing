import subprocess
import time

def run_mosquitto_pub(topic, host, message, delay=1):
    """
    Run the mosquitto_pub command with specified parameters.

    Args:
        topic (str): The MQTT topic.
        host (str): The MQTT broker host.
        message (str): The message to publish.
        delay (int, optional): Delay in seconds before the next step. Defaults to 1.
    """
    try:
        print(f"Publishing to topic '{topic}' with message '{message}'...")
        subprocess.run([
            "mosquitto_pub",
            "-t", topic,
            "-h", host,
            "-m", message
        ], check=True)
        print("Published successfully.")
    except subprocess.CalledProcessError as e:
        print(f"Error running mosquitto_pub: {e}")
    time.sleep(delay)

if __name__ == "__main__":
    # Define the sequence of commands with delays (in seconds)
    sequence = [
        {"message": "off", "delay": 60},   # Wait 1 minutes
        {"message": "on", "delay": 60},    # Wait 1 minutes

        {"message": "off", "delay": 300},   # Wait 5 minutes
        {"message": "on", "delay": 600},    # Wait 10 minutes
        {"message": "off", "delay": 1800},  # Wait 30 minutes
        {"message": "on", "delay": 3600},   # Wait 60 minutes
        {"message": "off", "delay": 3600},  # Wait 60 minutes
        {"message": "on", "delay": 7200},   # Wait 120 minutes
        {"message": "off", "delay": 7200},  # Wait 120 minutes
        {"message": "on", "delay": 10800},  # Wait 180 minutes
    ]

    topic = "testbench-sensor-power"
    host = "167.235.159.207"

    # Repeat the sequence indefinitely
    while True:
        for command in sequence:
            run_mosquitto_pub(topic, host, command["message"], command["delay"])
