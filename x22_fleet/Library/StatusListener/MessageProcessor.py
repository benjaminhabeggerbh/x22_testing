import json
import pandas as pd
from threading import Thread
from queue import Queue

class MessageProcessor:
    def __init__(self, sensor_state_manager, logger):
        self.sensor_state_manager = sensor_state_manager
        self.logger = logger
        self.message_queue = Queue()
        self.worker_thread = Thread(target=self.process_message_queue, daemon=True)
        self.worker_thread.start()

    def queue_message(self, topic, payload):
        try:
            self.message_queue.put((topic, payload))
        except Exception as e:
            self.logger.error(f"Failed to queue message: {e}")

    def process_message_queue(self):
        while True:
            try:
                topic, payload = self.message_queue.get()
                if topic is None:
                    break
                self.handle_message(topic, payload)
                self.message_queue.task_done()
            except Exception as e:
                self.logger.error(f"Error processing message queue: {e}")

    def handle_message(self, topic, payload):
        current_time = pd.Timestamp.now()
        topic = topic.replace("status-", "")
        try:
            # Parse the message payload from JSON format
            message_data = json.loads(payload.decode('utf-8'))
            self.sensor_state_manager.update_sensor_data(topic, message_data, current_time)

            if 'sync' in message_data:
                self.process_sync_data(topic, message_data, current_time)
        except json.JSONDecodeError:
            self.handle_generic_message(topic, payload)
        except Exception as e:
            self.logger.error(f"Error handling message on topic {topic}: {e}")

    def handle_generic_message(self, topic, payload):
        current_time = pd.Timestamp.now().floor('S')
        try:
            message = f"{current_time}: {payload.decode('utf-8')}"

            self.sensor_state_manager.update_generic_message(topic, message, current_time)

            self.logger.info(f"Logged generic message for topic {topic}: {message}")
        except Exception as e:
            self.logger.error(f"Error handling generic message for topic {topic}: {e}")

    def process_sync_data(self, topic, data, current_time):

        try:
            sent = data.get('sent', 0)
            total = data.get('total', 0)
            sync = data.get('sync', 0)
            speed = 0
            progress =0

            if sync == 1:
                sensor_data = self.sensor_state_manager.get_sensor_data(topic)
                last_progress = sensor_data.get('progress', 0)
                speed = sensor_data.get('progress', 0)
                last_time = sensor_data.get('speed_calc_time', current_time)
                progress = sent / total if total > 0 else 0

                if abs(progress - last_progress) > 0.01:
                    time_diff = (current_time - pd.Timestamp(last_time)).total_seconds()
                    if time_diff > 0:
                        speed = round((progress - last_progress) * total / time_diff / 1024, 2)
                

            self.sensor_state_manager.update_sensor_data(topic, {
                'progress': progress,
                'speed': max(speed, 0),
                'speed_calc_time': current_time
            }, current_time)

        except Exception as e:
            self.logger.error(f"Error processing sync data for topic {topic}: {e}")
