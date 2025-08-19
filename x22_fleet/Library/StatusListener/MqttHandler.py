import paho.mqtt.client as mqtt
from queue import Queue

class MQTTHandler:
    def __init__(self, broker_address, topics, message_queue, logger):
        self.broker_address = broker_address
        self.topics = topics
        self.message_queue = message_queue
        self.logger = logger

        self.client = mqtt.Client(callback_api_version=mqtt.CallbackAPIVersion.VERSION1)
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message

    def connect(self):
        try:
            self.client.connect(self.broker_address, 1883, 60)
            self.client.loop_start()
        except Exception as e:
            self.logger.error(f"Failed to connect to MQTT broker: {e}")

    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            self.logger.info("Connected to MQTT broker")
            for topic in self.topics:
                self.client.subscribe(topic)
                self.logger.info(f"Subscribed to topic: {topic}")
        else:
            self.logger.error(f"Connection failed with code {rc}")

    def on_message(self, client, userdata, msg):
        print(msg.topic)
        if "command" in msg.topic: return
        try:
            self.message_queue.put((msg.topic, msg.payload))
        except Exception as e:
            self.logger.error(f"Failed to queue message: {e}")

    def disconnect(self):
        try:
            self.client.loop_stop()
            self.client.disconnect()
        except Exception as e:
            self.logger.error(f"Failed to disconnect MQTT client: {e}")
