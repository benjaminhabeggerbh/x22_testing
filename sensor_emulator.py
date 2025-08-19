# sensor_emulator.py
import time
import struct
import math
import crcmod
from paho.mqtt import client as mqtt_client


# %% --- Sensor Data Emulator Class with fs parameter ---
class SensorEmulator:
    def __init__(
        self,
        fs=100,  # sampling rate in Hz
        num_samples_per_packet=10,
        sine_period=50,
        acc_amplitude=100,  # amplitude for acceleration sine wave (raw counts)
        gyro_amplitude=1000,  # amplitude for gyro sine wave (raw counts)
        mag_amplitude=500,  # amplitude for magnetometer sine wave (raw counts)
        temperature_raw=250,
    ):
        self.fs = fs
        # Calculate the sample interval in microseconds (integer value)
        self.sample_interval = int(1e6 / fs)
        self.num_samples_per_packet = num_samples_per_packet
        self.sine_period = sine_period
        self.acc_amplitude = acc_amplitude
        self.gyro_amplitude = gyro_amplitude
        self.mag_amplitude = mag_amplitude
        self.temperature_raw = temperature_raw
        # Use current time (in microseconds) as the base timestamp; truncated to 32 bits.
        self.last_timestamp = int(time.time() * 1e6) & 0xFFFFFFFF

        # CRC function (same settings as in your parser)
        self.crc16_mod = crcmod.mkCrcFun(
            0x18005, rev=True, initCrc=0x0000, xorOut=0x0000
        )
        # Packet format constants
        self.HEADER_ID_COMMAND = 0x7C
        self.DATA_TYPE_IMU_RAW_COMBO_V3 = 0x1E

    def build_packet(self):
        # Use the current base timestamp as header timestamp
        header_timestamp = self.last_timestamp
        # tsf is simulated using the current time in microseconds (64-bit)
        tsf = int(time.time() * 1e6) & 0xFFFFFFFFFFFFFFFF
        num_samples = self.num_samples_per_packet

        payload = b""
        # Pack header timestamp, tsf, and the number of samples
        payload += struct.pack("<I", header_timestamp)  # 4 bytes (little-endian)
        payload += struct.pack("<Q", tsf)  # 8 bytes (little-endian)
        payload += struct.pack("<H", num_samples)  # 2 bytes (little-endian)

        # For each sample, compute a timestamp based on the fs parameter.
        for i in range(num_samples):
            # Each sample's timestamp is the header timestamp plus an increment.
            sample_timestamp = header_timestamp + i * self.sample_interval

            # Use the sample index (or sample_timestamp) to generate a phase.
            # Here we use the relative sample number to drive the sine waves.
            phase = (i % self.sine_period) * (2 * math.pi / self.sine_period)

            # Generate sine waves for acceleration, gyroscope, and magnetometer:
            acc_x = int(self.acc_amplitude * math.sin(phase))
            acc_y = int(self.acc_amplitude * math.sin(phase + 2 * math.pi / 3))
            acc_z = int(self.acc_amplitude * math.sin(phase + 4 * math.pi / 3))

            gyro_x = int(self.gyro_amplitude * math.sin(phase))
            gyro_y = int(self.gyro_amplitude * math.sin(phase + 2 * math.pi / 3))
            gyro_z = int(self.gyro_amplitude * math.sin(phase + 4 * math.pi / 3))

            mag_x = int(self.mag_amplitude * math.sin(phase))
            mag_y = int(self.mag_amplitude * math.sin(phase + 2 * math.pi / 3))
            mag_z = int(self.mag_amplitude * math.sin(phase + 4 * math.pi / 3))

            # Pack sample data:
            payload += struct.pack(
                ">hhh", acc_x, acc_y, acc_z
            )  # Acceleration (big-endian)
            payload += struct.pack(
                ">hhh", gyro_x, gyro_y, gyro_z
            )  # Gyroscope (big-endian)
            payload += struct.pack(
                "<hhh", mag_x, mag_y, mag_z
            )  # Magnetometer (little-endian)
            payload += struct.pack(
                ">h", self.temperature_raw
            )  # Temperature (big-endian)

        # Update the base timestamp for the next packet
        self.last_timestamp = header_timestamp + num_samples * self.sample_interval

        # Build header: 1 byte header, 1 byte type, 2 bytes payload length (little-endian)
        payload_length = len(payload)
        header = struct.pack(
            "<BBH",
            self.HEADER_ID_COMMAND,
            self.DATA_TYPE_IMU_RAW_COMBO_V3,
            payload_length,
        )
        packet_without_crc = header + payload

        # Compute CRC over header and payload, then append it to the packet.
        crc = self.crc16_mod(packet_without_crc)
        crc_bytes = struct.pack("<H", crc)
        packet = packet_without_crc + crc_bytes
        return packet


# %% --- MQTT settings ---
BROKER = "mqtt.dev.artemys.link"
MQTT_PORT = 443
TOPIC = "stream-sensor_emulator"


# --- MQTT Publishing Logic (separated from sensor emulation) ---
def connect_mqtt():
    client = mqtt_client.Client()
    client.tls_set()  # Using default CA certificates
    client.tls_insecure_set(False)
    client.connect(BROKER, MQTT_PORT)
    return client


def publish_loop(emulator, client, topic, delay=0.1):
    try:
        while True:
            packet = emulator.build_packet()
            result = client.publish(topic, packet, qos=1)
            status = result[0]
            if status == 0:
                print(
                    f"Published packet with {emulator.num_samples_per_packet} samples; base timestamp: {emulator.last_timestamp}"
                )
            else:
                print("Failed to publish packet")
            time.sleep(delay)
    except KeyboardInterrupt:
        print("Exiting sensor emulator publishing loop...")


def main():
    emulator = SensorEmulator(
        fs=200,  # sampling rate
        num_samples_per_packet=10,
        sine_period=50,
        acc_amplitude=100,
        gyro_amplitude=1000,
        mag_amplitude=500,
        temperature_raw=250,
    )
    client = connect_mqtt()
    client.loop_start()
    publish_loop(emulator, client, TOPIC)
    client.loop_stop()
    client.disconnect()


if __name__ == "__main__":
    main()
