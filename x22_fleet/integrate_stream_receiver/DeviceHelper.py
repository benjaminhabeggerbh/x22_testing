from dataParser import Parser

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


class DeviceParser:
    def __init__(self):
        self.parsers = {}  

    def getParser(self, device_name):
        if device_name not in self.parsers:
           self.parsers[device_name] = Parser()     
        return self.parsers[device_name]       
    
    def getDeviceNames(self):
        return self.parsers.keys()
