#!/usr/bin/env python3

from time import sleep
import sys
import json
import signal
from DeviceHelper import Parser
from FsrConstants import FullScaleRangeConstants as fsrx22
from paho.mqtt import client as mqtt_client
import os
import time
import numpy as np
from DeviceStats import DevStats
from multiprocessing import Process, Queue
from x22_fleet.Library.BaseLogger import BaseLogger
import threading
import ssl
from PySide6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QLabel, QGridLayout, QScrollArea
from PySide6.QtCharts import QChart, QChartView, QLineSeries, QValueAxis
from PySide6.QtCore import QTimer, Qt, QPointF
from PySide6.QtGui import QPainter, QFont
import logging
from datetime import datetime
import struct

# Try to import tabulate for nice CLI tables, fallback to simple formatting if not available
try:
    from tabulate import tabulate
    HAS_TABULATE = True
except ImportError:
    HAS_TABULATE = False

# Configure logging - reduce verbosity
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('IMUPlotter')

#broker = '162.55.163.160'
#broker = '91.99.118.156'
broker = '167.235.159.207'

mqtt_port = 1883

# Global flag for running state
Running = True

def sigterm_handler(signum, frame):
    global Running
    print("Received SIGTERM. Cleaning up and exiting.")
    Running = False

signal.signal(signal.SIGTERM, sigterm_handler)

class DeviceDataBuffer:
    def __init__(self):
        self.dataBuffer = {}  # Initialize the dictionary of bytearrays

    def append_data(self, device_name, data):
        if device_name not in self.dataBuffer:
            self.dataBuffer[device_name] = bytearray()
        self.dataBuffer[device_name].extend(data)
        return self.dataBuffer[device_name]
    
    def truncate(self,device_name,bytesParsed):
        self.dataBuffer[device_name] = self.dataBuffer[device_name][bytesParsed:]

def logThis(logmessage):
    # Reduce verbose logging - only log errors or important messages
    if "error" in logmessage.lower() or "warning" in logmessage.lower():
        print(logmessage)

class DeviceParser:
    def __init__(self,dataCallBack):
        self.parsers = {}  
        self.dataCallBack = dataCallBack

    def getParser(self, device_name):
        if device_name not in self.parsers:
           self.parsers[device_name] = Parser(deviceName = device_name,logf=logThis)     
           self.parsers[device_name].dataCallback = self.dataCallBack
        return self.parsers[device_name]       
    
    
    def getDeviceNames(self):
        return self.parsers.keys()
        

class RealtimePlotter(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Real-time IMU Data & Stats")
        self.setGeometry(100, 100, 1400, 900)
        
        # Add counter for received points
        self.total_points_received = 0
        self.start_time = time.time()

        # Create the main widget and layout
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        self.layout = QVBoxLayout(main_widget)

        # Create stats display area
        self.stats_area = QScrollArea()
        self.stats_widget = QWidget()
        self.stats_layout = QGridLayout(self.stats_widget)
        self.stats_layout.setSpacing(10)  # Add spacing between labels
        self.stats_layout.setContentsMargins(10, 10, 10, 10)  # Add margins
        self.stats_area.setWidget(self.stats_widget)
        self.stats_area.setMaximumHeight(200)  # Increased from 150 to accommodate larger labels
        self.stats_area.setWidgetResizable(True)
        self.layout.addWidget(self.stats_area)

        # Store device-specific charts and series
        self.device_charts = {}  # {device_name: QChart}
        self.device_series = {}  # {device_name: [series1, series2, ...]}
        self.device_views = {}   # {device_name: QChartView}
        self.device_stats_labels = {}  # {device_name: QLabel}
        
        # Common settings
        self.max_points = 1000
        self.labels = [
            "Acc X", "Acc Y", "Acc Z",
            "Gyr X", "Gyr Y", "Gyr Z",
            "Mag X", "Mag Y", "Mag Z"
        ]
        self.colors = [
            Qt.red, Qt.green, Qt.blue,
            Qt.cyan, Qt.magenta, Qt.yellow,
            Qt.darkRed, Qt.darkGreen, Qt.darkBlue
        ]
        self.scale_margin = 0.1

    def ensure_device_chart(self, device_name):
        """Create or get existing chart for a device"""
        if device_name not in self.device_charts:
            # Create new chart
            chart = QChart()
            chart.setTitle(f"IMU Data - {device_name}")
            chart.setAnimationOptions(QChart.NoAnimation)

            # Create axes
            axis_x = QValueAxis()
            axis_x.setTitleText("Sample Number")
            axis_x.setRange(0, self.max_points)
            axis_x.setLabelFormat("%d")

            axis_y = QValueAxis()
            axis_y.setRange(-10, 10)
            axis_y.setLabelFormat("%.2f")
            axis_y.setTitleText("Value")

            chart.addAxis(axis_x, Qt.AlignBottom)
            chart.addAxis(axis_y, Qt.AlignLeft)

            # Create series
            series_list = []
            for label, color in zip(self.labels, self.colors):
                series = QLineSeries()
                series.setName(label)
                pen = series.pen()
                pen.setColor(color)
                pen.setWidth(2)
                series.setPen(pen)
                chart.addSeries(series)
                series.attachAxis(axis_x)
                series.attachAxis(axis_y)
                series_list.append(series)

            # Create chart view
            chart_view = QChartView(chart)
            chart_view.setRenderHint(QPainter.Antialiasing)
            chart_view.setViewportUpdateMode(QChartView.ViewportUpdateMode.MinimalViewportUpdate)
            self.layout.addWidget(chart_view)

            # Create stats label for this device
            stats_label = QLabel(f"{device_name}: Initializing...")
            stats_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))
            stats_label.setStyleSheet("""
                QLabel { 
                    background-color: #ffffff; 
                    color: #000000;
                    padding: 8px; 
                    border: 2px solid #333333; 
                    border-radius: 5px;
                    font-weight: bold;
                }
            """)
            self.stats_layout.addWidget(stats_label, len(self.device_stats_labels), 0)
            self.device_stats_labels[device_name] = stats_label

            # Store everything
            self.device_charts[device_name] = chart
            self.device_series[device_name] = series_list
            self.device_views[device_name] = chart_view

        return self.device_charts[device_name], self.device_series[device_name]

    def update_stats_display(self, device_name, stats_data):
        """Update the stats display for a specific device"""
        if device_name in self.device_stats_labels:
            label = self.device_stats_labels[device_name]
            stats_text = f"{device_name}: Current: {stats_data['samplesPerSec']:.1f} Hz | Recent Avg: {stats_data['samplesPerSecAvg']:.1f} Hz | Total Avg: {stats_data.get('samplesPerSecTotalAvg', 0):.1f} Hz | Missed: {stats_data['missedSamples']} | Total: {stats_data['NumberOfSamples']}"
            label.setText(stats_text)

    def update_imu_data(self, device_name, device_buffer):
        try:
            # Ensure we have a chart for this device
            chart, series_list = self.ensure_device_chart(device_name)

            # Get IMU data from device buffer
            acc_data = device_buffer.dataDict["ImuAccRaw"].data
            gyr_data = device_buffer.dataDict["ImuGyrRaw"].data
            mag_data = device_buffer.dataDict["ImuMagRaw"].data

            # Get the current buffer lengths
            acc_len = len(acc_data[1])
            gyr_len = len(gyr_data[1])
            mag_len = len(mag_data[1])

            # Find the minimum length to ensure we have matching data points
            min_len = min(acc_len, gyr_len, mag_len)
            if min_len == 0:
                return

            # Take only the last max_points of data
            start_idx = max(0, min_len - self.max_points)
            
            # Create points for each series
            for series_idx, series in enumerate(series_list):
                points = []
                # Get the right data array based on series index
                if series_idx < 3:
                    data = acc_data[series_idx + 1][start_idx:]
                elif series_idx < 6:
                    data = gyr_data[(series_idx - 3) + 1][start_idx:]
                else:
                    data = mag_data[(series_idx - 6) + 1][start_idx:]
                
                # Create points with x values from 0 to max_points
                for i, value in enumerate(data):
                    x = i * (self.max_points / len(data))
                    points.append(QPointF(x, value))
                
                # Replace all points in the series
                series.replace(points)

            # Update y-axis scaling periodically
            if min_len > 100:  # Only scale when we have enough data
                all_values = []
                for series in series_list:
                    points = series.points()
                    if points:
                        all_values.extend(point.y() for point in points)
                
                if all_values:
                    current_min = min(all_values)
                    current_max = max(all_values)
                    value_range = current_max - current_min
                    margin = value_range * self.scale_margin
                    chart.axisY().setRange(current_min - margin, current_max + margin)

            # Force an immediate update
            chart.update()
            QApplication.processEvents()

        except (KeyError, IndexError) as e:
            logger.error(f"Error updating IMU data for {device_name}: {str(e)}")
            pass

    def closeEvent(self, event):
        super().closeEvent(event)

class DeviceHandler:
    def __init__(self,dataQueue,useTLS = False, log_to_console = True):
        # Create data logging directory
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.data_dir = os.path.join("data", timestamp)
        os.makedirs(self.data_dir, exist_ok=True)
        
        self.device_buffer = DeviceDataBuffer()
        self.device_parser = DeviceParser(dataCallBack=self.parsedData)
        self.useTLS = useTLS
        self.dataQueue = dataQueue
        self.deviceName = ""
        self.samplerate = 0
        self.deviceInfo = {"address": "", "name": "unkwon yet","battery":{"voltage":0,"consumption":0,"percentage":0},"samplerate":0}
        self.storeLocal = False
        
        # Add sampling rate tracking
        self.first_packet_time = None
        self.first_sample_count = 0
        self.last_5_times = []
        self.last_5_samples = []
        
        signal.signal(signal.SIGTERM, self.sigterm_handler)
        signal.signal(signal.SIGINT, self.sigterm_handler)
        
        # Create plotter instance
        self.plotter = RealtimePlotter()
        self.plotter.show()
        
        self.mqtt_client = mqtt_client.Client(client_id='', userdata={'bytes': 0, 'start_time': time.time()}, callback_api_version=mqtt_client.CallbackAPIVersion.VERSION1)
        if self.useTLS:
            self.mqtt_client.tls_set()  # Ensure correct CA certificates
            self.mqtt_client.tls_insecure_set(False)  # Enforce TLS verification

        self.mqtt_client.on_message = self.on_message
        self.mqtt_client.on_subscribe = self.on_subscribe
        self.mqtt_client.on_connect = self.on_connect
        self.logger = BaseLogger(log_file_path=f"DeviceHandler.log", log_to_console=False).get_logger()  # Reduce console logging
        try:
            self.mqtt_client.connect(broker, mqtt_port)
            self.logger.info("MQTT client successfully connected.")
        except Exception as e:
            self.logger.error(f"MQTT connection failed: {e}")

        self.mqtt_client.loop_start()
        self.logger.info(f"mqtt client: {self.mqtt_client}")
        
        # Start connection check thread
        self.connection_check_thread = threading.Thread(target=self.check_mqtt_connection, daemon=True)
        self.connection_check_thread.start()

    def check_mqtt_connection(self):
        while True:
            if not self.mqtt_client.is_connected():
                self.logger.warning("MQTT client disconnected, attempting to reconnect...")
                try:
                    self.mqtt_client.reconnect()
                    self.logger.info("MQTT client reconnected.")
                except Exception as e:
                    self.logger.error(f"Failed to reconnect MQTT client: {e}")
        
            time.sleep(10)  # Check every 10 seconds
    
    def sigterm_handler(self, signum, frame):
        print("\nReceived signal to terminate. Saving data...")
        self.export_all_data()
        print("Data saved. Cleaning up and exiting.")
        sys.exit(0)

    def export_all_data(self):
        """Export all accumulated data to files"""
        for device_name, parser in self.device_parser.parsers.items():
            try:
                # Create files
                clean_name = device_name.replace('stream/', '')
                data_path = os.path.join(self.data_dir, f"{clean_name}.csv")
                timesync_path = os.path.join(self.data_dir, f"{clean_name}_timesync.csv")
                
                # Export IMU data
                with open(data_path, 'w') as data_file:
                    # Write header
                    data_file.write("timestamp,acc_x,acc_y,acc_z,gyr_x,gyr_y,gyr_z,mag_x,mag_y,mag_z\n")
                    
                    # Get all data arrays
                    acc_data = parser.dataBuffer.dataDict["ImuAccRaw"].data
                    gyr_data = parser.dataBuffer.dataDict["ImuGyrRaw"].data
                    mag_data = parser.dataBuffer.dataDict["ImuMagRaw"].data
                    
                    # Find the length of data to write
                    min_len = min(len(acc_data[1]), len(gyr_data[1]), len(mag_data[1]))
                    
                    # Write all data points
                    for i in range(min_len):
                        data_file.write(f"{acc_data[0][i]},{acc_data[1][i]},{acc_data[2][i]},{acc_data[3][i]},"
                                      f"{gyr_data[1][i]},{gyr_data[2][i]},{gyr_data[3][i]},"
                                      f"{mag_data[1][i]},{mag_data[2][i]},{mag_data[3][i]}\n")
                
                # Export TimeSync data
                if "TimeSync" in parser.dataBuffer.dataDict:
                    with open(timesync_path, 'w') as timesync_file:
                        # Write header
                        timesync_file.write("tsf,timestamp\n")
                        
                        # Get TimeSync data
                        tsf_data = parser.dataBuffer.dataDict["TimeSync"].data[0]
                        ts_data = parser.dataBuffer.dataDict["TimeSync"].data[1]
                        
                        # Write all TimeSync data points
                        for tsf, ts in zip(tsf_data, ts_data):
                            timesync_file.write(f"{tsf},{ts}\n")
                
                print(f"Exported data for device {clean_name}")
                
            except Exception as e:
                print(f"Error exporting data for device {device_name}: {e}")

    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            self.logger.info("Connected to MQTT broker successfully.")
            self.mqtt_client.subscribe("#", qos=2)  # Ensure subscription is made on connection
        else:
            self.logger.error(f"Failed to connect, return code {rc}")

    def on_subscribe(self, client, userdata, mid, granted_qos):
        self.logger.info(f"Subscribed to topics, MID: {mid}, Granted QoS: {granted_qos}")

    def on_message(self,client, userdata, message):
        current_time = time.time()
        
        # Process the data first
        self.incomingData(message.payload,topic=message.topic)
        
        # Get current sample count from parser
        if "stream" in message.topic:
            sensorName = message.topic.replace("stream-", "")
            parser = self.device_parser.getParser(sensorName)
            current_samples = parser.dataBuffer.maxLen()
            
            # Initialize first packet tracking
            if self.first_packet_time is None:
                self.first_packet_time = current_time
                self.first_sample_count = current_samples
            
            # Update last 5 packets tracking
            self.last_5_times.append(current_time)
            self.last_5_samples.append(current_samples)
            if len(self.last_5_times) > 5:
                self.last_5_times.pop(0)
                self.last_5_samples.pop(0)
            
            # Calculate rates if we have enough data
            if len(self.last_5_times) > 1:
                # Calculate total rate
                total_time = current_time - self.first_packet_time
                total_samples = current_samples - self.first_sample_count
                total_fs = total_samples / total_time if total_time > 0 else 0
                
                # Calculate immediate rate (last 5 packets)
                recent_time = self.last_5_times[-1] - self.last_5_times[0]
                recent_samples = self.last_5_samples[-1] - self.last_5_samples[0]
                immediate_fs = recent_samples / recent_time if recent_time > 0 else 0
                
                # Only log sampling rates occasionally to reduce noise
                if hasattr(self, '_last_rate_log') and current_time - self._last_rate_log > 5:  # Log every 5 seconds
                    self.logger.info(f"Sampling rates - Total: {total_fs:.2f} Hz, Immediate (5 packets): {immediate_fs:.2f} Hz")
                    self._last_rate_log = current_time
                elif not hasattr(self, '_last_rate_log'):
                    self._last_rate_log = current_time

    def incomingData(self, data, topic):
        # Reduce verbose logging - only log occasionally
        if not hasattr(self, '_last_data_log') or time.time() - self._last_data_log > 10:  # Log every 10 seconds
            self.logger.info(f"incoming data on: {topic} len: {len(data)}")
            self._last_data_log = time.time()
        
        if "stream" in topic:  # Accept any topic containing "stream"
            sensorName = topic.replace("stream-", "")
            # Remove verbose processing logs
            buffer = self.device_buffer.append_data(sensorName, data)
            bytesParsed = self.device_parser.getParser(sensorName).parseStream(buffer)
            # Only log parsing errors or significant events
            if bytesParsed == 0 and len(data) > 0:
                self.logger.warning(f"No bytes parsed for {sensorName}, data length: {len(data)}")
            self.device_buffer.truncate(sensorName, bytesParsed)

    def parsedData(self, type, sensorName):
        parser = self.device_parser.getParser(sensorName)
        
        # Handle stream token events
        if type == parser.DataStreamType.DATA_TYPE_STREAM_TOKEN:
            stream_tokens = parser.dataBuffer.dataDict["StreamToken"]
            if len(stream_tokens.data[0]) > 0:  # Check if we have stream token data
                action = stream_tokens.data[0][-1]  # Get the latest action
                timestamp = stream_tokens.data[1][-1]  # Get the latest timestamp
                action_str = "STARTED" if action == 1 else "STOPPED"
                
                # Convert Unix timestamp to human-readable format
                try:
                    device_time = datetime.fromtimestamp(timestamp)
                    device_time_str = device_time.strftime("%Y-%m-%d %H:%M:%S")
                except (ValueError, OSError):
                    device_time_str = f"Invalid timestamp: {timestamp}"
                
                # Log to console with prominent formatting
                current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                print(f"\n{'='*80}")
                print(f"🚀 STREAM {action_str} TOKEN RECEIVED")
                print(f"{'='*80}")
                print(f"📱 Device: {sensorName}")
                print(f"⏰ Receiver Time: {current_time}")
                print(f"📅 Device Time: {device_time_str}")
                print(f"🕐 Unix Timestamp: {timestamp}")
                print(f"📊 Action: {action_str} ({action})")
                print(f"{'='*80}\n")
                
                # Also log to the logger
                self.logger.info(f"STREAM {action_str} - Device: {sensorName}, Device Time: {device_time_str}, Unix Timestamp: {timestamp}")
        
        pass

class TsfSync:
    def __init__(self):
        pass
    
    def calcFs(self,device_buffer):
        tsf = device_buffer.dataDict["TimeSync"].data[0]
        ts = device_buffer.dataDict["TimeSync"].data[1]
        dtsf = np.diff(tsf)
        dts = np.diff(ts)
        ratio = dtsf / dts
        fs = 1e6 / ratio
        #print (fs)

def print_stats_table(devicehandler, stats):
    """Print a nice CLI table with device stats"""
    table_data = []
    headers = ["Device", "Current Hz", "Recent Avg Hz", "Total Avg Hz", "Missed", "Total Samples"]
    
    for dev in devicehandler.device_parser.getDeviceNames():
        dev_stats = stats.getStats(dev)
        table_data.append([
            dev,
            f"{dev_stats['samplesPerSec']:.1f}",
            f"{dev_stats['samplesPerSecAvg']:.1f}",
            f"{dev_stats.get('samplesPerSecTotalAvg', 0):.1f}",
            dev_stats['missedSamples'],
            dev_stats['NumberOfSamples']
        ])
    
    if table_data:
        # Add extra spacing to preserve stream token messages
        current_time = datetime.now().strftime("%H:%M:%S")
        print(f"\n\n[{current_time}] " + "="*100)
        print("DEVICE STATISTICS")
        print("="*100)
        if HAS_TABULATE:
            print(tabulate(table_data, headers=headers, tablefmt="grid"))
        else:
            # Simple table format without tabulate
            print(f"{'Device':<20} {'Current Hz':<12} {'Recent Avg':<12} {'Total Avg':<12} {'Missed':<8} {'Total':<12}")
            print("-" * 100)
            for row in table_data:
                print(f"{row[0]:<20} {row[1]:<12} {row[2]:<12} {row[3]:<12} {row[4]:<8} {row[5]:<12}")
        print("="*100)

def clear_screen():
    """Clear the terminal screen"""
    os.system('cls' if os.name == 'nt' else 'clear')

def main():
    global Running
    
    # Create QApplication instance
    app = QApplication(sys.argv)
    
    # Create data queue and device handler
    dataQueue = Queue()
    devicehandler = DeviceHandler(dataQueue)
    stats = DevStats(devicehandler.device_parser, log_to_console=False)  # Reduce console logging
    tsf = TsfSync()

    # Add a timer for periodic updates
    update_timer = QTimer()
    update_timer.timeout.connect(lambda: process_device_updates(devicehandler, stats, tsf))
    update_timer.start(50)  # Update every 50ms (20 Hz) for plot updates
    
    # Add a separate timer for stats updates
    stats_timer = QTimer()
    stats_timer.timeout.connect(lambda: update_stats(devicehandler, stats, tsf))
    stats_timer.start(2000)  # Update stats every 2000ms (0.5 Hz) - less frequent
    
    # Add a timer for CLI table updates
    table_timer = QTimer()
    table_timer.timeout.connect(lambda: update_cli_table(devicehandler, stats))
    table_timer.start(5000)  # Update CLI table every 5 seconds
    
    # Start the Qt event loop
    app.exec_()
    
    # Cleanup
    Running = False
    devicehandler.mqtt_client.loop_stop()
    devicehandler.mqtt_client.disconnect()

def process_device_updates(devicehandler, stats, tsf):
    try:
        # Update plot and log data for each device
        for dev in devicehandler.device_parser.getDeviceNames():
            devBuffer = devicehandler.device_parser.getParser(dev).dataBuffer
            # Update plot
            if hasattr(devicehandler, 'plotter'):
                devicehandler.plotter.update_imu_data(dev, devBuffer)
    except Exception as e:
        logger.error(f"Error in process_device_updates: {str(e)}")

def update_stats(devicehandler, stats, tsf):
    try:
        devCopy = list(devicehandler.device_parser.getDeviceNames()) 
        for dev in devCopy:
            stats.calcStats()
            # Update GUI stats display
            if hasattr(devicehandler, 'plotter'):
                dev_stats = stats.getStats(dev)
                devicehandler.plotter.update_stats_display(dev, dev_stats)
            devBuffer = devicehandler.device_parser.getParser(dev).dataBuffer
            tsf.calcFs(devBuffer)
    except Exception as e:
        logger.error(f"Error in update_stats: {str(e)}")

def update_cli_table(devicehandler, stats):
    """Update the CLI table display"""
    try:
        # Don't clear screen to preserve stream token messages
        # clear_screen()  # Commented out to preserve stream token messages
        print_stats_table(devicehandler, stats)
    except Exception as e:
        logger.error(f"Error in update_cli_table: {str(e)}")

if __name__ == '__main__':
    main()
