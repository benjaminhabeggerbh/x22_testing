import ssl
import re
import json
from collections import defaultdict, deque
import threading
import time
from rich.console import Console
from rich.table import Table

# Try to import Kafka, but don't fail if not available
try:
    from kafka import KafkaProducer
    KAFKA_AVAILABLE = True
except ImportError:
    print("Warning: Kafka library not available. Running in MQTT-only mode.")
    KAFKA_AVAILABLE = False

try:
    import paho.mqtt.client as mqtt
    MQTT_AVAILABLE = True
except ImportError:
    print("Error: paho-mqtt library not available. Please install with: pip install paho-mqtt")
    MQTT_AVAILABLE = False
    exit(1)

import struct
import crcmod

MQTT_BROKER = "mqtt.dev.artemys.link"
MQTT_PORT = 443
MQTT_TOPIC = "stream/+"

MQTT_TLS = True

KAFKA_BROKER = "localhost:9092"
KAFKA_TOPIC_TEMPLATE = "imu_data-{}"

# ALLOWED_SENSOR_IDS = {"0D_17_56"}  # Uncomment to restrict
ALLOWED_SENSOR_IDS = None  # None = allow all
active_sensor_ids = set()

sensor_byte_counts = defaultdict(int)
sensor_buffer_sizes = defaultdict(int)
sensor_bytes_parsed = defaultdict(int)
sensor_sample_counts = defaultdict(int)
sensor_sample_window = defaultdict(lambda: deque(maxlen=2))
sensor_sample_skips = defaultdict(int)
sensor_messages_received = defaultdict(int)

crc16_mod = crcmod.mkCrcFun(0x18005, rev=True, initCrc=0x0000, xorOut=0x0000)

# Initialize Kafka producer only if available
producer = None
if KAFKA_AVAILABLE:
    try:
        producer = KafkaProducer(
            bootstrap_servers=KAFKA_BROKER,
            value_serializer=lambda v: json.dumps(v).encode("utf-8"),
            # Add timeout and retry settings for better reliability
            request_timeout_ms=5000,
            retries=3
        )
        print(f"Successfully connected to Kafka broker at {KAFKA_BROKER}")
    except Exception as e:
        print(f"Warning: Could not connect to Kafka broker at {KAFKA_BROKER}: {e}")
        print("Running in MQTT-only mode. Data will be parsed and logged but not sent to Kafka.")
        producer = None
else:
    print("Running in MQTT-only mode (Kafka library not available)")

class MQTTDataParser:
    def __init__(self):
        self.HEADER_FORMAT = "<BBH"
        self.HEADER_LENGTH = struct.calcsize(self.HEADER_FORMAT)
        self.CRC_FORMAT = "<H"
        self.CRC_LENGTH = struct.calcsize(self.CRC_FORMAT)
        self.HEADER_ID_COMMAND = 0x7C
        self.DATA_TYPE_IMU_RAW_COMBO_V3 = 0x1E

        self.SAMPLE_V3_ACC_FORMAT = ">hhh"
        self.SAMPLE_V3_GYRO_FORMAT = ">hhh"
        self.SAMPLE_V3_MAG_FORMAT = "<hhh"
        self.SAMPLE_V3_TEMP_FORMAT = ">h"
        self.SAMPLE_V3_LENGTH = (
            struct.calcsize(self.SAMPLE_V3_ACC_FORMAT)
            + struct.calcsize(self.SAMPLE_V3_GYRO_FORMAT)
            + struct.calcsize(self.SAMPLE_V3_MAG_FORMAT)
            + struct.calcsize(self.SAMPLE_V3_TEMP_FORMAT)
        )

    def parse_from_buffer(self, buffer: bytearray, sensor_id):
        results = []
        i = 0
        total_len = len(buffer)
        min_len = self.HEADER_LENGTH + self.CRC_LENGTH

        while i <= total_len - min_len:
            try:
                header_candidate = buffer[i:i + self.HEADER_LENGTH]
                header_id, data_type, payload_length = struct.unpack(self.HEADER_FORMAT, header_candidate)

                if header_id != self.HEADER_ID_COMMAND or data_type != self.DATA_TYPE_IMU_RAW_COMBO_V3:
                    i += 1
                    continue

                expected_total_length = self.HEADER_LENGTH + payload_length + self.CRC_LENGTH
                if i + expected_total_length > total_len:
                    break

                candidate_packet = buffer[i:i + expected_total_length]
                crc_received = struct.unpack(self.CRC_FORMAT, candidate_packet[-self.CRC_LENGTH:])[0]
                data_to_crc = candidate_packet[:-self.CRC_LENGTH]
                crc_calculated = crc16_mod(data_to_crc)

                if crc_received != crc_calculated:
                    i += 1
                    continue

                payload_bytes = candidate_packet[self.HEADER_LENGTH:-self.CRC_LENGTH]
                start_index = 0
                base_sample_number = struct.unpack("I", payload_bytes[start_index:start_index + 4])[0]
                start_index += 4
                timestamp_us = struct.unpack("Q", payload_bytes[start_index:start_index + 8])[0]
                start_index += 8
                num_samples = struct.unpack("H", payload_bytes[start_index:start_index + 2])[0]
                start_index += 2

                expected_data_len = num_samples * self.SAMPLE_V3_LENGTH
                actual_data_len = len(payload_bytes) - start_index
                if actual_data_len < expected_data_len:
                    raise ValueError(f"[{sensor_id}] Not enough data for {num_samples} samples: expected {expected_data_len}, got {actual_data_len}")

                if sensor_sample_window[sensor_id]:
                    last_sample = sensor_sample_window[sensor_id][-1]
                    if base_sample_number > last_sample:
                        expected = last_sample + 1
                        missed = base_sample_number - expected
                        sensor_sample_skips[sensor_id] += missed

                sensor_sample_window[sensor_id].append(base_sample_number + num_samples - 1)
                sensor_sample_counts[sensor_id] += num_samples

                samples = []
                for j in range(num_samples):
                    acc = struct.unpack(self.SAMPLE_V3_ACC_FORMAT, payload_bytes[start_index:start_index + 6])
                    start_index += 6
                    gyro = struct.unpack(self.SAMPLE_V3_GYRO_FORMAT, payload_bytes[start_index:start_index + 6])
                    start_index += 6
                    mag = struct.unpack(self.SAMPLE_V3_MAG_FORMAT, payload_bytes[start_index:start_index + 6])
                    start_index += 6
                    temp = struct.unpack(self.SAMPLE_V3_TEMP_FORMAT, payload_bytes[start_index:start_index + 2])[0]
                    start_index += 2

                    samples.append({
                        "sample_index": base_sample_number + j,
                        "acc": {"x": acc[0], "y": acc[1], "z": acc[2]},
                        "gyro": {"x": gyro[0], "y": gyro[1], "z": gyro[2]},
                        "mag": {"x": mag[0], "y": mag[1], "z": mag[2]},
                        "temp_raw": temp
                    })

                results.append({
                    "sensor_id": sensor_id,
                    "timestamp_us": timestamp_us,
                    "base_sample_number": base_sample_number,
                    "num_samples_in_packet": num_samples,
                    "samples": samples
                })

                i += expected_total_length
            except Exception as e:
                print(f"[{sensor_id}] Exception during parsing at index {i}: {e}")
                i += 1

        sensor_bytes_parsed[sensor_id] += i
        del buffer[:i]
        return results

parser = MQTTDataParser()
stream_buffers = defaultdict(bytearray)
console = Console()
last_sample_counts = defaultdict(int)
last_message_counts = defaultdict(int)

def print_sensor_stats():
    log_file = open("stream_stats.log", "a")
    while True:
        time.sleep(5)
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        table = Table(title="Sensor Statistics")
        table.add_column("Sensor ID", style="cyan", no_wrap=True)
        table.add_column("Messages/sec", justify="right")
        table.add_column("Bytes Received", justify="right")
        table.add_column("Bytes in Buffer", justify="right")
        table.add_column("Bytes Parsed", justify="right")
        table.add_column("Samples/sec", justify="right")
        table.add_column("Skipped Samples", justify="right")
        table.add_column("Kafka Status", justify="center")

        sensor_ids_to_show = ALLOWED_SENSOR_IDS if ALLOWED_SENSOR_IDS is not None else active_sensor_ids
        for sensor_id in sorted(sensor_ids_to_show):
            samples_this_period = sensor_sample_counts[sensor_id] - last_sample_counts[sensor_id]
            messages_this_period = sensor_messages_received[sensor_id] - last_message_counts[sensor_id]
            sample_rate = samples_this_period / 5.0
            message_rate = messages_this_period / 5.0
            skipped = sensor_sample_skips[sensor_id]
            
            # Kafka status indicator
            kafka_status = "✅" if producer else "❌"
            
            row = (
                sensor_id,
                f"{message_rate:.1f}",
                str(sensor_byte_counts[sensor_id]),
                str(len(stream_buffers[sensor_id])),
                str(sensor_bytes_parsed[sensor_id]),
                f"{sample_rate:.1f}",
                str(skipped),
                kafka_status
            )
            table.add_row(*row)
            log_file.write(f"[{timestamp}] Sensor {sensor_id}: {sample_rate:.1f} samples/sec, {message_rate:.1f} msgs/sec, {skipped} skipped, Kafka: {'ON' if producer else 'OFF'}\n")
            last_sample_counts[sensor_id] = sensor_sample_counts[sensor_id]
            last_message_counts[sensor_id] = sensor_messages_received[sensor_id]

        log_file.flush()
        console.clear()
        console.print(table)

threading.Thread(target=print_sensor_stats, daemon=True).start()

def on_connect(client, userdata, flags, rc):
    print("Connected to MQTT broker with result code " + str(rc))
    client.subscribe(MQTT_TOPIC)
    print(f"Subscribed to topic: {MQTT_TOPIC}")

def on_message(client, userdata, msg):
    try:
        sensor_id_match = re.match(r"stream/(.+)", msg.topic)
        if not sensor_id_match:
            return

        sensor_id = sensor_id_match.group(1)

        if ALLOWED_SENSOR_IDS is not None and sensor_id not in ALLOWED_SENSOR_IDS:
            return

        active_sensor_ids.add(sensor_id)
        sensor_messages_received[sensor_id] += 1

        stream_buffers[sensor_id].extend(msg.payload)
        sensor_byte_counts[sensor_id] += len(msg.payload)
        parsed_payloads = parser.parse_from_buffer(stream_buffers[sensor_id], sensor_id)

        # Send to Kafka only if producer is available
        if producer:
            kafka_topic = KAFKA_TOPIC_TEMPLATE.format(sensor_id)
            for payload in parsed_payloads:
                try:
                    producer.send(kafka_topic, value=payload)
                except Exception as e:
                    print(f"Error sending to Kafka: {e}")
        # Removed verbose parsing messages when Kafka not available

    except Exception as e:
        print(f"Error parsing message: {e}")

if __name__ == '__main__':
    if not MQTT_AVAILABLE:
        print("Error: MQTT library not available")
        exit(1)
    
    print("Starting MQTT Stream Bridge...")
    if producer:
        print(f"✅ Kafka mode: Connected to {KAFKA_BROKER}")
    else:
        print("⚠️  MQTT-only mode: No Kafka broker available")
    
    client = mqtt.Client(callback_api_version=mqtt.CallbackAPIVersion.VERSION1)
    client.on_connect = on_connect
    client.on_message = on_message

    if MQTT_TLS:
        client.tls_set(cert_reqs=ssl.CERT_REQUIRED)

    try:
        client.connect(MQTT_BROKER, MQTT_PORT)
        print(f"Connecting to MQTT broker: {MQTT_BROKER}:{MQTT_PORT}")
        client.loop_forever()
    except Exception as e:
        print(f"Error connecting to MQTT broker: {e}")
        exit(1)
