import requests, time, json, os
import paho.mqtt.client as mqtt

class PowerRelais:
    def __init__(self, credentials_path, ip_address):
        """
        Initialize the PowerRelais instance with the IP address of the Shelly device and MQTT credentials.
        
        :param credentials_path: str, Path to the credentials JSON file
        :param ip_address: str, IP address of the Shelly device
        """
        self.ip_address = ip_address

        # Load MQTT credentials
        with open(credentials_path, "r") as f:
            credentials = json.load(f)

        self.mqtt_server = credentials["server"]

        # Set up MQTT client
        self.mqtt_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1)
        self.mqtt_client.on_message = self.on_mqtt_message
        self.mqtt_client.connect(self.mqtt_server, 1883, 60)

    def control_relay(self, relay_number, action):
        """
        Send a command to the Shelly device to control a relay.

        :param relay_number: int, Relay number (0 or 1) to control
        :param action: str, Action to perform ("on" or "off")
        """
        url = f"http://{self.ip_address}/relay/{relay_number}?turn={action}"
        try:
            response = requests.get(url)
            if response.status_code == 200:
                print(f"Relay {relay_number} successfully turned {action}.")
            else:
                print(f"Failed to turn {action} relay {relay_number}. Status code: {response.status_code}")
        except requests.exceptions.RequestException as e:
            print(f"Error: {e}")

    def on_mqtt_message(self, client, userdata, message):
        """
        Handle incoming MQTT messages.

        :param client: MQTT client instance
        :param userdata: User data passed to the callback
        :param message: MQTT message instance
        """
        payload = message.payload.decode("utf-8").strip().lower()
        print(f"Received MQTT message on topic {message.topic}: {payload}")
        if payload == "on":
            self.control_relay(0, "on")
        elif payload == "off":
            self.control_relay(0, "off")
        else:
            print("Unknown command received via MQTT.")

    def start_mqtt_listener(self):
        """
        Start the MQTT listener to subscribe to the topic and process incoming messages.
        """
        topic = "testbench-sensor-power"
        self.mqtt_client.subscribe(topic)
        print(f"Subscribed to MQTT topic: {topic}")
        self.mqtt_client.loop_start()
def main():
    current_path = os.getcwd()
    print(f"Power relais service, the current working directory is: {current_path}")

    # Replace with the IP address of your Shelly device and path to credentials
    shelly_ip = "192.168.1.251"
    credentials_path = "credentials.json"

    power_relais = PowerRelais(credentials_path, shelly_ip)
    power_relais.start_mqtt_listener()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Exiting...")
        power_relais.mqtt_client.loop_stop()


# Usage example
if __name__ == "__main__":
    main()
