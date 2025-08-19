from kafka import KafkaConsumer
import json
import time
from rich.table import Table
from rich.console import Console
from collections import defaultdict, deque

TOPIC_PATTERN = "imu_data-"
BROKER = "localhost:9092"

console = Console()

sensor_stats = defaultdict(lambda: {
    "count": 0,
    "skipped": 0,
    "last_index": None,
    "last_sample": None,
    "history": deque(maxlen=2)
})

consumer = KafkaConsumer(
    bootstrap_servers=[BROKER],
    auto_offset_reset="latest",
    value_deserializer=lambda m: json.loads(m.decode("utf-8")),
    group_id="debug-visualizer",
    consumer_timeout_ms=100
)
consumer.subscribe(pattern=f"{TOPIC_PATTERN}.*")

print("📡 Listening to all imu_data-* topics\n")

last_print = time.time()
while True:
    has_data = False
    for message in consumer:
        has_data = True
        payload = message.value
        sensor_id = payload["sensor_id"]
        samples = payload.get("samples", [])
        if not samples:
            continue

        stats = sensor_stats[sensor_id]
        for sample in samples:
            index = sample["sample_index"]
            stats["count"] += 1
            stats["last_sample"] = sample

            if stats["last_index"] is not None and index > stats["last_index"] + 1:
                stats["skipped"] += index - stats["last_index"] - 1

            stats["last_index"] = index

    now = time.time()
    if now - last_print >= 5:
        table = Table(title="Sensor Stats", show_lines=True)
        table.add_column("Sensor ID", style="bold cyan")
        table.add_column("Samples/sec", justify="right")
        table.add_column("Skipped Samples", justify="right")
        table.add_column("Total Samples", justify="right")
        table.add_column("Last ACC (x,y,z)", justify="center")
        table.add_column("Last GYRO (x,y,z)", justify="center")
        table.add_column("Last MAG (x,y,z)", justify="center", style="dim")

        for sensor_id, stats in sorted(sensor_stats.items()):
            rate = stats["count"] / 5.0
            total = stats["last_index"] + 1 if stats["last_index"] is not None else 0
            last = stats["last_sample"]
            if last:
                acc = f"{last['acc']['x']}, {last['acc']['y']}, {last['acc']['z']}"
                gyro = f"{last['gyro']['x']}, {last['gyro']['y']}, {last['gyro']['z']}"
                mag = f"{last['mag']['x']}, {last['mag']['y']}, {last['mag']['z']}"
            else:
                acc = gyro = mag = "–"

            table.add_row(sensor_id, f"{rate:.1f}", str(stats["skipped"]), str(total), acc, gyro, mag)
            stats["count"] = 0  # reset sample counter

        console.clear()
        console.print(table)
        last_print = now

    time.sleep(0.1)  # avoid busy loop

