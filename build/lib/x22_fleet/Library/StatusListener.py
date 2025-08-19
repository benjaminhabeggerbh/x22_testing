import json
import pandas as pd
import paho.mqtt.client as mqtt
import time
import os
import argparse
from x22_fleet.Library.BaseLogger import BaseLogger
from x22_fleet.Library.SshHelper import SshHelper

class StatusListener:
    def __init__(self, broker_address, topics,log_to_file = True,log_to_console=True,credentials_path="credentials.json"):
        self.start_time = pd.Timestamp.now()
        pd.set_option('display.max_columns', None)
        pd.set_option('display.max_rows', None)
        pd.set_option('display.width', None)

        self.broker_address = broker_address
        self.topics = topics
        self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        self.logger = BaseLogger(log_file_path="StatusListener.log", log_to_file=log_to_file, log_to_console=log_to_console).get_logger()
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.sensorMessageLog = {}
        self.sensor_log_dir = "sensor_logs"
        # Initialize an empty DataFrame to store messages
        self.df = pd.DataFrame(index=topics, columns=['fw', 'v', 'mA', 'soc', 'timeVal', 'sessions', 'generic_message', 'lastseen', 'updateAge', 'AP','sync','sent','total', 'progress', 'speed','speed_calc_time','rec','fwPending'])

        # Connect to the MQTT broker
        self.client.connect(self.broker_address, 1883, 60)

        # Start the network loop in a separate thread
        self.client.loop_start()
        self.sshHelper = SshHelper(credentials_path=credentials_path)

    def update_sensors_firmware_pending(self):
        try:
            updatesPending = self.sshHelper.get_pending_updates()
            for sensor_name in self.df.index:
                is_pending = sensor_name in updatesPending
                self.df.at[sensor_name, 'fwPending'] = 1 if is_pending else 0
        except Exception as ex:
            print(f"update firmware pending failed {ex}")                        
            self.logger.warning(f"update firmware pending failed {ex}")            

    def on_connect(self, client, userdata, flags, rc,properties):
        self.logger.info(f"Connected with result code {rc}")
        # Subscribe to topics
        for topic in self.topics:
            self.client.subscribe(topic)

    def on_message(self, client, userdata, msg):
        current_time = pd.Timestamp.now()
        current_time_to_second = current_time.floor("s")
        topic = msg.topic.replace("status-", "")  # Store the topic

        if topic.startswith("command"):
            # ignore messages we send to the sensors
            return

        try:
            # Parse the message payload from JSON format
            messageString = msg.payload.decode('utf-8')
            data = json.loads(messageString)

            # Update the DataFrame with new data and last seen time
            for key, value in data.items():
                self.df.at[topic, key] = value

            try:
                if 'sync' in data:
                    if data['sync'] == 1:
                        sent = int(data.get('sent', 0))
                        total = int(data.get('total', 1))
                        last_progress = self.df.at[topic, 'progress'] if pd.notna(self.df.at[topic, 'progress']) else 0
                        last_time = self.df.at[topic, 'speed_calc_time'] if pd.notna(self.df.at[topic, 'speed_calc_time']) else current_time
                        self.df.at[topic, 'speed_calc_time'] = last_time

                        self.df.at[topic, 'speed_calc_time'] = current_time

                        progress = sent / total if total > 0 else 0
                        time_diff = (current_time - last_time).total_seconds()
                        if time_diff < 0: time_diff = 0
                        speed = round((progress - last_progress) * total / time_diff / 1024) if time_diff > 0 else 0
                        if speed < 0: 
                            speed = 0
                        sync = 1
                    else:
                        progress = 0
                        speed = 0
                        sync = 0

                    self.df.at[topic, 'sync'] = sync
                    self.df.at[topic, 'progress'] = progress
                    self.df.at[topic, 'speed'] = speed

            except Exception as e:
                self.logger.info(f"Error calculating progress and speed: {e}")

            # Write to CSV file, appending data
            self.write_data_to_csv(topic, data, current_time)

        except json.JSONDecodeError:
            message = f"{current_time_to_second}: {messageString}"

            if topic in self.sensorMessageLog:
                self.sensorMessageLog[topic].append(message)
                self.sensorMessageLog[topic] = self.sensorMessageLog[topic][-5:]
            else:
                self.sensorMessageLog[topic] = [message]

            self.df.at[topic, 'generic_message'] = " | ".join(reversed(self.sensorMessageLog[topic]))
            self.logger.info(self.sensorMessageLog[topic])
        except Exception as ex:
            pass

        self.df.at[topic, 'lastseen'] = current_time
        self.update_last_seen()
    
    def write_data_to_csv(self, topic, data, timestamp):
        log_dir = f"{self.sensor_log_dir}/{topic}"
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)

        file_path = f'{log_dir}/{topic}.csv'

        data['lastseen'] = timestamp
        df_new = pd.DataFrame([data])

        if not os.path.isfile(file_path):
            df_new.to_csv(file_path, mode='w', index=False, header=True)
        else:
            df_new.to_csv(file_path, mode='a', index=False, header=False)

    def update_last_seen(self):
        current_time = pd.Timestamp.now()
        for topic in self.df.index:
            if pd.notna(self.df.at[topic, 'lastseen']):
                updateAge = round((current_time - self.df.at[topic, 'lastseen']).total_seconds(), 1)
                self.df.at[topic, 'updateAge'] = updateAge

    def get_dataframe(self):
        if 'fw' in self.df.columns:
            sorted_df = self.df.sort_values(by='fw')
            sorted_df = sorted_df.sort_index()
        else:
            sorted_df = self.df.sort_index()

        return sorted_df

def main():
    parser = argparse.ArgumentParser(description="X22 Status Listener Service")
    parser.add_argument(
        "--credentials",
        type=str,
        default="credentials.json",
        help="Path to the credentials JSON file"
    )
    args = parser.parse_args()

    current_path = os.getcwd()

    topics = ["#"]

    with open(args.credentials, "r") as f:
        credentials = json.load(f)
        server = credentials.get("server")

    listener = StatusListener(server, topics,log_to_console=false,credentials_path=args.credentials)
    listener.logger.info(f"X22 status listener service, the current working directory is: {current_path}")

    while True:
        listener.logger.info("waiting on sensor updates")
        time.sleep(1)
        df = listener.get_dataframe()
        listener.logger.info(f" number of sensors online: {df.shape[0]}")

if __name__ == '__main__':
    main()
