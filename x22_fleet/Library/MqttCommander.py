from AxiamoX22Composer import *
import paho.mqtt.client as mqtt

class MqttCommander:
    def __init__(self, broker_address):
        self.broker_address = broker_address
        self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1)
        self.composer = X22Composer()

        # Command mapping
        self.command_map = {
            "shutdown": self.composer.composeShutDown,
            "deepsleep": self.composer.composeDeepSleep,
            "reboot": self.composer.composeReboot,
            "factory_reset": self.composer.composeFactoryReset,
            "identify": self.composer.composeWifiIdentify,
            "enable_force_record": self.composer.composeEnableForceOffline,
            "disable_force_record": self.composer.composeDisableForceOffline,
            "sync": self.composer.composeSync,
            "erase_flash": self.composer.composeEraseFlash,
            "wifi_sleep": self.composer.composeWifiSleep,
            "enable_datastream": self.composer.composeEnableDataStream,
            "disable_datastream": self.composer.composeDisableDataStream
        }

        # Connect to the MQTT broker
        self.client.connect(self.broker_address, 1883, 60)

        # Start the network loop in a separate thread
        self.client.loop_start()

    def send_command(self, sensor_name, command_name):
        """
        Send a command to the specified sensor by name.

        :param sensor_name: The name of the sensor to which the command will be sent.
        :param command_name: The name of the command to send.
        """
        # Get the command byte array from the command map
        command_function = self.command_map.get(command_name)
        if command_function:
            command_byte_array = command_function()
            # Compose the topic string using the sensor name
            topic = f"command-{sensor_name}"

            # Publish the command to the MQTT topic with QoS 2
            tmp = bytes(command_byte_array)
            self.client.publish(topic, payload=tmp, qos=2)
            print(f"Publishing to topic: {topic}")
            print(f"Payload (bytes): {tmp}")
        else:
            print(f"Invalid command: {command_name}")

    def __del__(self):
        # Properly disconnect and stop the network loop
        self.client.loop_stop()
        self.client.disconnect()

# Example usage:
if __name__ == "__main__":
    # Create an instance with default localhost broker
    commander = ManualCommander()
    
    # Or specify a different broker
    # commander = ManualCommander("mqtt.example.com")
    
    # Send the factory reset command to a specific device
    commander.send_factory_reset("0d1b42")

