import time
import numpy as np
import os
import csv
from x22_fleet.Library.BaseLogger import BaseLogger
from datetime import datetime

class DevStats:
    def __init__(self,parser,log_to_console=True):
        self.parser = parser
        self.stats = {}  
        self.logger = BaseLogger(log_file_path=f"DeviceStats.log", log_to_console=log_to_console).get_logger()

    def calcStats(self):
        histLen = 100
        for dev in self.parser.getDeviceNames():
            stats = self.getStats(dev)

            currentLen = self.parser.getParser(dev).dataBuffer.maxLen()
            now = int(time.monotonic_ns())
            if stats["firstUpdate"] == 0:
                stats["firstUpdate"] = now

            if(stats["NumberOfSamples"] != 0):
                diffSamples = currentLen - self.stats[dev]["NumberOfSamples"]
                diffTime = (now - self.stats[dev]["LastUpdate"]) / 1e9
                diffTimeTot = (now - stats["firstUpdate"]) / 1e9
                samplesPerSec = np.floor(diffSamples / diffTime)
                samplesPerSecTot = np.floor(self.stats[dev]["NumberOfSamples"] / diffTimeTot)
                self.stats[dev]["samplesPerSec"]  = samplesPerSec
                # self.stats[dev]["samplesPerSecHist"].append(samplesPerSec)
                # self.stats[dev]["samplesPerSecHist"] = self.stats[dev]["samplesPerSecHist"][-histLen:]
                self.stats[dev]["samplesPerSecAvg"] = np.floor(samplesPerSecTot)
                self.stats[dev]["samplesPerSecTotalAvg"] = np.floor(samplesPerSecTot)  # Total average over entire runtime
                self.stats[dev]["missedSamples"] = self.parser.getParser(dev).missedSamples
                
                # Only log stats occasionally to reduce noise
                if hasattr(self, '_last_stats_log') and time.time() - self._last_stats_log > 10:  # Log every 10 seconds
                    self.logger.info(f"Stats: {dev} avg: {self.stats[dev]['samplesPerSecAvg']} missed: {self.stats[dev]['missedSamples'] }")
                    self._last_stats_log = time.time()
                elif not hasattr(self, '_last_stats_log'):
                    self._last_stats_log = time.time()

            self.stats[dev]["NumberOfSamples"] = currentLen
            self.stats[dev]["LastUpdate"] = now        
    
    def printStats(self):
        for dev in self.parser.getDeviceNames():
            # Get the current timestamp
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            # Create the filename
            filename = f"{dev}-stats.csv"
            
            # Prepare the data to write
            data = {
                'Time': timestamp,
                'NumberOfSamples': self.stats[dev]['NumberOfSamples'],
                'SamplesPerSec': self.stats[dev]['samplesPerSec'],
                'SamplesPerSecAvg': self.stats[dev]['samplesPerSecAvg'],
                'missedSamples': self.stats[dev]['missedSamples']
            }
            
            # Write the data to a CSV file
            # file_exists = os.path.isfile(filename)
            # with open(filename, mode='a', newline='') as file:
            #     writer = csv.writer(file)
            #     if not file_exists:
            #         writer.writerow(['Time', 'NumberOfSamples', 'SamplesPerSec', 'SamplesPerSecAvg', 'MissedSamples'])
            #     writer.writerow([data['Time'], data['NumberOfSamples'], data['SamplesPerSec'], data['SamplesPerSecAvg'], data['missedSamples']])
            
            # Log the information
            #Logger.info(f"{dev} Samples: {data['NumberOfSamples']} / SamplesPerSec(Inst/Avg): {data['SamplesPerSec']} / {data['SamplesPerSecAvg']} CheckmissedSamples: {data['missedSamples']}")
            
    def getStats(self, device_name):
        if device_name not in self.stats:
           self.stats[device_name] = {"NumberOfSamples": 0, "LastUpdate": 0,"samplesPerSecAvg":0,"samplesPerSec":0, "samplesPerSecTotalAvg":0, "firstUpdate": 0, "missedSamples":0}     
        return self.stats[device_name]              
