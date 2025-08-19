#!/usr/bin/env python

from oscpy.server import OSCThreadServer
from oscpy.client import OSCClient
from time import sleep
from DeviceHelper import *
import sys
import json
import pickle
import socket
import signal
import sys
from FsrConstants import FullScaleRangeConstants as fsrx22
from paho.mqtt import client as mqtt_client
import paho.mqtt.publish as publish
import os
import time
import numpy as np
from DeviceStats import DevStats
from multiprocessing import Process, Queue
from x22_fleet.Library.BaseLogger import BaseLogger
import plotly.graph_objects as go
import threading
import ssl

broker = 'mqtt.dev.artemys.link'
mqtt_port = 443

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
        

class DeviceHandler:
    def __init__(self,dataQueue,log_to_console = True):
        self.device_buffer = DeviceDataBuffer()
        self.device_parser = DeviceParser(dataCallBack=self.parsedData)
        self.dataQueue = dataQueue
        self.deviceName = ""
        self.samplerate = 0
        self.deviceInfo = {"address": "", "name": "unkwon yet","battery":{"voltage":0,"consumption":0,"percentage":0},"samplerate":0}
        self.storeLocal = False
        signal.signal(signal.SIGTERM, self.sigterm_handler)
        self.mqtt_client = mqtt_client.Client(client_id='', userdata={'bytes': 0, 'start_time': time.time()}, callback_api_version=mqtt_client.CallbackAPIVersion.VERSION1)
        self.mqtt_client.tls_set()  # Ensure correct CA certificates
        self.mqtt_client.tls_insecure_set(False)  # Enforce TLS verification
        self.mqtt_client.on_message = self.on_message
        self.mqtt_client.on_subscribe = self.on_subscribe
        self.mqtt_client.on_connect = self.on_connect
        self.logger = BaseLogger(log_file_path=f"DeviceHandler.log", log_to_console=log_to_console).get_logger()
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
    
    def sigterm_handler(signum, dummy1,dummy2):
        print("Device Process Received SIGTERM. Cleaning up and exiting.")
        shutdown()
    
    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            self.logger.info("Connected to MQTT broker successfully.")
            self.mqtt_client.subscribe("#", qos=2)  # Ensure subscription is made on connection
        else:
            self.logger.error(f"Failed to connect, return code {rc}")

    def on_subscribe(self, client, userdata, mid, granted_qos):
        self.logger.info(f"Subscribed to topics, MID: {mid}, Granted QoS: {granted_qos}")

    def on_message(self,client, userdata, message):
        self.incomingData(message.payload,topic=message.topic)

    def incomingData(self, data, topic):
        #self.logger.info(f"incoming data on: {topic} len: {len(data)}")
        #self.logger.info(f"incoming data on: {topic}")

        if "stream" in topic:
            sensorName = topic.replace("stream-", "")
            buffer = self.device_buffer.append_data(sensorName, data)
            bytesParsed = self.device_parser.getParser(sensorName).parseStream(buffer)
            self.device_buffer.truncate(sensorName, bytesParsed)

    def parsedData(self, type,sensorName):
        parser = self.device_parser.getParser(sensorName)


import matplotlib.pyplot as plt

import matplotlib.pyplot as plt

class IMUPlotter:
    def __init__(self):
        plt.ion()  # Turn on interactive mode
        self.fig, self.ax = plt.subplots()  # Create figure and axis
        self.lines = None  # Store line objects for updating
        self.max_samples = 200  # Limit the plot to the last 1000 samples


    def plot_tsf(self, rootParser):
        self.max_samples = 100  # Limit the plot to the last 1000 samples
        devs = rootParser.getDeviceNames()
        n_devices = len(devs)

        tsf_list = []
        ts_list = []

        # Make sure to iterate safely over device dictionary keys
        devs_copy = list(devs)  # Avoid modifying during iteration

        for dev in devs_copy:  
            devBuffer = rootParser.getParser(dev).dataBuffer

            # Convert keys to list to prevent dictionary modification errors
            data_dict_keys = list(devBuffer.dataDict.keys())  

            if "TimeSync" in data_dict_keys:
                data = devBuffer.dataDict["TimeSync"].data
                if len(data) >= 2:  # Ensure both tsf and ts exist
                    tsf = list(data[0])[-self.max_samples:]
                    ts = list(data[1])[-self.max_samples:]

                    # Normalize ts by subtracting the first element
                    if ts:  # Ensure ts is not empty
                        ts = [t - ts[0] for t in ts]

                    tsf_list.append(tsf)
                    ts_list.append(ts)
                else:
                    print(f"Warning: 'TimeSync' data in {dev} is incomplete.")
                    tsf_list.append([])
                    ts_list.append([])
            else:
                print(f"Warning: 'TimeSync' key missing in {dev}.")
                tsf_list.append([])
                ts_list.append([])

        # Ensure self.lines is initialized
        if self.lines is None:
            self.lines = [None] * n_devices

        # Resize self.lines if new devices are added
        if len(self.lines) < n_devices:
            self.lines.extend([None] * (n_devices - len(self.lines)))

        # Update or create lines for each device
        for i in range(n_devices):
            if self.lines[i] is None:  # New device, create plot
                if tsf_list[i] and ts_list[i]:  # Ensure data is not empty
                    line, = self.ax.plot(tsf_list[i], ts_list[i], label=f"Device {devs_copy[i]}")
                    self.lines[i] = line
            else:  # Existing device, update data
                if tsf_list[i] and ts_list[i]:  # Ensure data is not empty
                    self.lines[i].set_xdata(tsf_list[i])
                    self.lines[i].set_ydata(ts_list[i])

        # Trim self.lines if devices were removed
        self.lines = self.lines[:n_devices]

        self.ax.relim()
        self.ax.autoscale_view()

        plt.draw()
        plt.pause(0.01)
        
    def plot_acceleration(self, device_name, device_buffer):
        timestamps = list(device_buffer.dataDict["ImuAccRaw"].data[0])
        accX = list(device_buffer.dataDict["ImuAccRaw"].data[1])
        accY = list(device_buffer.dataDict["ImuAccRaw"].data[2])
        accZ = list(device_buffer.dataDict["ImuAccRaw"].data[3])

        gyrX = list(device_buffer.dataDict["ImuGyrRaw"].data[1])
        gyrY = list(device_buffer.dataDict["ImuGyrRaw"].data[2])
        gyrZ = list(device_buffer.dataDict["ImuGyrRaw"].data[3])


        magX = list(device_buffer.dataDict["ImuMagRaw"].data[1])
        magY = list(device_buffer.dataDict["ImuMagRaw"].data[2])
        magZ = list(device_buffer.dataDict["ImuMagRaw"].data[3])

        # Keep only the last `max_samples` data points
        timestamps = timestamps[-self.max_samples:]
        accX = accX[-self.max_samples:]
        accY = accY[-self.max_samples:]
        accZ = accZ[-self.max_samples:]

        gyrX = gyrX[-self.max_samples:]
        gyrY = gyrY[-self.max_samples:]
        gyrZ = gyrZ[-self.max_samples:]

        magX = magX[-self.max_samples:]
        magY = magY[-self.max_samples:]
        magZ = magZ[-self.max_samples:]

        if self.lines is None:
            # First time: Create line plots
            self.lines = [
                self.ax.plot(timestamps, accX, label="Acc X")[0],
                self.ax.plot(timestamps, accY, label="Acc Y")[0],
                self.ax.plot(timestamps, accZ, label="Acc Z")[0],
                self.ax.plot(timestamps, gyrX, label="Gyr X")[0],
                self.ax.plot(timestamps, gyrY, label="Gyr Y")[0],
                self.ax.plot(timestamps, gyrZ, label="Gyr Z")[0],
                self.ax.plot(timestamps, magX, label="Mag X")[0],
                self.ax.plot(timestamps, magY, label="Mag Y")[0],
                self.ax.plot(timestamps, magZ, label="Mag Z")[0]                

            ]
            self.ax.set_title(f"IMU Acceleration Data (Last {self.max_samples} Samples)")
            self.ax.set_xlabel("Timestamp")
            self.ax.set_ylabel("Acceleration")
            self.ax.legend()
        else:
            # Update existing lines with new data
            self.lines[0].set_xdata(timestamps)
            self.lines[0].set_ydata(accX)
            self.lines[1].set_xdata(timestamps)
            self.lines[1].set_ydata(accY)
            self.lines[2].set_xdata(timestamps)
            self.lines[2].set_ydata(accZ)
            self.lines[3].set_xdata(timestamps)
            self.lines[3].set_ydata(gyrX)
            self.lines[4].set_xdata(timestamps)
            self.lines[4].set_ydata(gyrY)
            self.lines[5].set_xdata(timestamps)
            self.lines[5].set_ydata(gyrZ)   
            self.lines[6].set_xdata(timestamps)
            self.lines[6].set_ydata(magX)
            self.lines[7].set_xdata(timestamps)
            self.lines[7].set_ydata(magY)
            self.lines[8].set_xdata(timestamps)
            self.lines[8].set_ydata(magZ)                                   
            self.ax.relim()  # Recalculate limits
            self.ax.autoscale_view()  # Rescale view

        plt.draw()
        plt.pause(0.01)  # Pause to update the figure

    def plot_synced_acceleration(self, rootParser):
            devs = rootParser.getDeviceNames()
            n_devices = len(devs)

            ts_list = []
            accX_list = []

            # Make sure to iterate safely over device dictionary keys
            devs_copy = list(devs)  

            for dev in devs_copy:  
                devBuffer = rootParser.getParser(dev).dataBuffer

                # Ensure both "TimeSync" and "ImuAccRaw" exist in the data dictionary
                if "TimeSync" in devBuffer.dataDict and "ImuAccRaw" in devBuffer.dataDict:
                    time_data = devBuffer.dataDict["TimeSync"].data
                    acc_data = devBuffer.dataDict["ImuAccRaw"].data

                    if len(time_data) >= 2 and len(acc_data) >= 2:  
                        ts = list(time_data[1])[-self.max_samples:]  # Time-sync timestamps
                        accX = list(acc_data[1])[-self.max_samples:]  # Acceleration X

                        # Normalize ts (subtract first timestamp to align)
                        if ts:
                            ts = [t - ts[0] for t in ts]

                        ts_list.append(ts)
                        accX_list.append(accX)
                    else:
                        print(f"Warning: Insufficient data in {dev}.")
                        ts_list.append([])
                        accX_list.append([])
                else:
                    print(f"Warning: Missing required keys in {dev}.")
                    ts_list.append([])
                    accX_list.append([])

            # Ensure self.lines is initialized
            if self.lines is None:
                self.lines = [None] * n_devices

            # Resize self.lines if new devices are added
            if len(self.lines) < n_devices:
                self.lines.extend([None] * (n_devices - len(self.lines)))

            # Update or create lines for each device
            for i in range(n_devices):
                if self.lines[i] is None:  # New device, create plot
                    if ts_list[i] and accX_list[i]:  # Ensure data is not empty
                        line, = self.ax.plot(ts_list[i], accX_list[i], label=f"Device {devs_copy[i]}")
                        self.lines[i] = line
                else:  # Existing device, update data
                    if ts_list[i] and accX_list[i]:  # Ensure data is not empty
                        self.lines[i].set_xdata(ts_list[i])
                        self.lines[i].set_ydata(accX_list[i])

            # Trim self.lines if devices were removed
            self.lines = self.lines[:n_devices]

            self.ax.set_title("Acceleration X with Synced Time")
            self.ax.set_xlabel("Time (relative)")
            self.ax.set_ylabel("Acceleration X")
            self.ax.legend()

            self.ax.relim()
            self.ax.autoscale_view()

            plt.draw()
            plt.pause(0.01)

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

        

    
def mainDeviceProcess(dataQueue):
    print("New Process for handling devices:")
    global Running
    
    devicehandler = DeviceHandler(dataQueue)
    stats = DevStats(devicehandler.device_parser)
    Running = True
    plotter = IMUPlotter()
    tsf = TsfSync()

    while(Running):
#        try:

        #plotter.plot_tsf(devicehandler.device_parser)
        #plotter.plot_synced_acceleration(devicehandler.device_parser)
        
        devCopy = list(devicehandler.device_parser.getDeviceNames()) 
        for dev in devCopy:
            stats.calcStats()
            stats.printStats()
            devBuffer = devicehandler.device_parser.getParser(dev).dataBuffer
            plotter.plot_acceleration(dev,devBuffer)
            tsf.calcFs(devBuffer)
            time.sleep(1)
#       time.sleep(.1)


if __name__ == '__main__':
    dataQueue = Queue()
    processes = []
    devProc = Process(target=mainDeviceProcess, args=(dataQueue,))
    devProc.start()
    processes.append(devProc)


    while(True):
        time.sleep(.5)
