import os
import re
import argparse
import struct
from enum import Enum
import time
import array as arr
import crcmod
import binascii
import logging

crc16_mod = crcmod.mkCrcFun(0x18005, rev=True, initCrc=0x0000, xorOut=0x0000)

# Set up logging for parser warnings
parser_logger = logging.getLogger('DataParser')
parser_logger.setLevel(logging.WARNING)
parser_logger.propagate = False  # Prevent propagation to console
if not parser_logger.handlers:
    file_handler = logging.FileHandler('data_parser_warnings.log')
    file_handler.setLevel(logging.WARNING)
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(formatter)
    parser_logger.addHandler(file_handler)

class DeviceDataBuffer:
    def __init__(self):
        self.clearSets()

    def clearSets(self):
        self.dataDict = {
            "TimeSync": Parser.ParsedData(
                Parser.DataStreamType.DATA_TYPE_TIME_SYNC,
                [arr.array("Q"), arr.array("L")],
            ),
            "ImuAcc": Parser.ParsedData(
                Parser.DataStreamType.DATA_TYPE_IMU_ACC,
                [arr.array("L"), arr.array("f"), arr.array("f"), arr.array("f")],
            ),
            "ImuGyr": Parser.ParsedData(
                Parser.DataStreamType.DATA_TYPE_IMU_GYR,
                [arr.array("L"), arr.array("f"), arr.array("f"), arr.array("f")],
            ),
            "ImuTemp": Parser.ParsedData(
                Parser.DataStreamType.DATA_TYPE_IMU_RAW_TEMP,
                [arr.array("L"), arr.array("f")],
            ),            
            "ImuMag": Parser.ParsedData(
                Parser.DataStreamType.DATA_TYPE_IMU_MAG,
                [arr.array("L"), arr.array("f"), arr.array("f"), arr.array("f")],
            ),
            "Quat": Parser.ParsedData(
                Parser.DataStreamType.DATA_TYPE_IMU_QUAT,
                [
                    arr.array("L"),
                    arr.array("f"),
                    arr.array("f"),
                    arr.array("f"),
                    arr.array("f"),
                ],
            ),
            "ImuAccRaw": Parser.ParsedData(
                Parser.DataStreamType.DATA_TYPE_IMU_RAW_ACC,
                [arr.array("L"), arr.array("h"), arr.array("h"), arr.array("h")],
            ),
            "ImuGyrRaw": Parser.ParsedData(
                Parser.DataStreamType.DATA_TYPE_IMU_RAW_GYR,
                [arr.array("L"), arr.array("h"), arr.array("h"), arr.array("h")],
            ),
            "ImuMagRaw": Parser.ParsedData(
                Parser.DataStreamType.DATA_TYPE_IMU_RAW_MAG,
                [arr.array("L"), arr.array("h"), arr.array("h"), arr.array("h")],
            ),
            "ImuRawCombo": Parser.ParsedData(
                Parser.DataStreamType.DATA_TYPE_IMU_RAW_MAG,
                [
                    arr.array("L"),
                    arr.array("h"),
                    arr.array("h"),
                    arr.array("h"),
                    arr.array("h"),
                    arr.array("h"),
                    arr.array("h"),
                    arr.array("h"),
                ],
            ),
            "Steps": Parser.ParsedData(
                Parser.DataStreamType.DATA_TYPE_IMU_STEP,
                [arr.array("L"), arr.array("Q")],
            ),
            "Barometer": Parser.ParsedData(
                Parser.DataStreamType.DATA_TYPE_BAR,
                [arr.array('L'), arr.array('l'), arr.array('l')]
            ),
            "Battery": Parser.ParsedData(
                Parser.DataStreamType.DATA_TYPE_SYS_BATTERY,
                [arr.array("I"), arr.array("h"), arr.array("H"), arr.array("B")],
            ),
            "Ping": Parser.ParsedData(
                Parser.DataStreamType.DATA_TYPE_SYS_PING,
                [
                    arr.array("L"),
                    arr.array("Q"),
                    arr.array("Q"),
                    arr.array("Q"),
                    arr.array("H"),
                ],
            ),
            "PingV2": Parser.ParsedData(
                Parser.DataStreamType.DATA_TYPE_SYS_PING_V2,
                [arr.array("L"), arr.array("Q"), arr.array("Q")],
            ),
            "StreamToken": Parser.ParsedData(
                Parser.DataStreamType.DATA_TYPE_STREAM_TOKEN,
                [arr.array("B"), arr.array("Q")],  # action, timestamp
            ),
            # "States":       Parser.ParsedData(Parser.DatabinasciiStreamType.DATA_TYPE_SYS_STATES,
            #                                   [arr.array('L'), arr.array('L'), arr.array('B'), arr.array('B'), arr.array('L'), arr.array('Q'), arr.array('Q')]),
            "gatt": {},
        }

        self.imei = ""

    def totLen(self):
        dataLen = 0
        for key in self.dataDict.keys():
            if key == "gatt":
                continue
            dataLen += len(self.dataDict[key].data[0])
        return dataLen

    def maxLen(self):
        maxVal = 0
        for key in self.dataDict.keys():
            if key == "gatt":
                continue
            entryLen = len(self.dataDict[key].data[0])
            if entryLen > maxVal:
                maxVal = entryLen
        return maxVal


class Parser:
    def __init__(self, deviceName="", logf=lambda *args, **kwargs: None):
        self.logf = logf
        self.dataCallback = None
        self.dataBuffer = DeviceDataBuffer()
        self.deviceName = deviceName
        self.missedSamples = 0
        pass

    HEADER_ID_COMMAND = 0x7C  # --> |
    HEADER_ID_PARAMETERS = 0x7D  # --> }
    CRC_LENGTH = 2
    HEADER_LENGTH = 4  # [headerID:1] [type:1] [length:2]
    MAX_PACKET_LEN = 2048  # --> 255
    WIFI_NUM_PROFILES = 3
    WIFI_LEN_SSID = 32
    ECG_NUM_CHANNELS = 5
    IMEI_LEN = 15

    maskImuDataRate = 0x00000003
    maskImuAccFsr = 0x00000F00
    maskImuGyrFsr = 0x000F0000
    maskImuFeatures = 0x00F00000

    class DataStreamType(Enum):
        DATA_TYPE_TIME_SYNC = 0x01        
        DATA_TYPE_IMU_ACC = 0x10
        DATA_TYPE_IMU_GYR = 0x11
        DATA_TYPE_IMU_MAG = 0x12
        DATA_TYPE_IMU_QUAT = 0x13
        DATA_TYPE_IMU_STEP = 0x14

        DATA_TYPE_IMU_RAW_ACC = 0x15
        DATA_TYPE_IMU_RAW_GYR = 0x16
        DATA_TYPE_IMU_RAW_MAG = 0x17

        DATA_TYPE_IMU_RAW_COUNTER = 0x18
        DATA_TYPE_IMU_RAW_COMBO = 0x19
        DATA_TYPE_IMU_RAW_COMBO_V2  = 0x1C
        DATA_TYPE_IMU_RAW_TEMP = 0x1D
        DATA_TYPE_IMU_RAW_COMBO_V3  = 0x1E        


        DATA_TYPE_BAR = 0x20
        DATA_TYPE_CELLULAR_STATUS = 0x33

        DATA_TYPE_IMU_GYR_PRIMARY_AXIS_ONLY = 0x1B

        DATA_TYPE_SYS_STATES = 0x40
        DATA_TYPE_SYS_BATTERY = 0x41
        DATA_TYPE_SYS_PING = 0x42
        DATA_TYPE_SYS_PING_V2 = 0x43
        DATA_TYPE_WIFI_CREDENTIALS = 0x44
        DATA_TYPE_WIFI_STATUS = 0x45
        DATA_TYPE_DEVICE_NAME = 0x47

        DATA_TYPE_IMU_CONFIG = 0x51
        DATA_TYPE_BAR_CONFIG = 0x52
        DATA_TYPE_CEL_GPS_CONFIG = 0x53
        DATA_TYPE_SDCARD_CONFIG = 0x54
        DATA_TYPE_BT_DEVICES = 0x55

        DATA_TYPE_SYS_TASK_STATS = 0x60
        DATA_TYPE_SYS_RESOURCES = 0x61
        DATA_TYPE_SYS_TIME = 0x62

        DATA_TYPE_GATT = 0x80
        DATA_TYPE_LIVE_BPM = 0x81

        DATA_TYPE_FILEINFO          = 0x90
        DATA_TYPE_FILEPART          = 0x91
        DATA_TYPE_STREAM_TOKEN      = 0x9A  # Stream start/stop notification

        DATA_TYPE_SYS_CNT_TEST = 0xFC

        DATA_TYPE_SYS_NVS_TEST = 0xFD
        DATA_TYPE_SYS_SDCARD_TEST = 0xFE
        DATA_TYPE_SYS_TEST = 0xFF

    class ParsedData:
        def __init__(self, dataType, data):
            self.type = dataType
            self.data = data

        def __str__(self):
            return str(self.type) + " : " + str(self.data)

        def __sizeof__(self):
            return self.type.__sizeof__() + self.data.__sizeof__()

    logf = lambda *args, **kwargs: None

    def setDataCallBack(self, dataCallback):
        self.dataCallback = dataCallback

    @classmethod
    def int2DataStreamType(cls, val):
        try:
            result = cls.DataStreamType(val)
            # Add debugging for stream token
            if val == 0x9A:
                print(f"DEBUG: Successfully converted stream token type {val} to {result}")
                cls.logf(f"DEBUG: Successfully converted stream token type {val} to {result}")
            return result
        except Exception as e:
            print(f"ERROR: type {val} invalid: {str(e)}")
            # Add debugging to show all enum values
            print(f"DEBUG: Available enum values: {list(cls.DataStreamType)}")
            parser_logger.error(f"Type {val} invalid: {str(e)}")
            return None


    def parseDeviceName(self, buffer, startIndex, sampleLength, timeStamp):
        self.deviceName = (
            bytes(buffer[startIndex : startIndex + sampleLength])
            .decode("utf-8")
            .rstrip("\x00")
        )

    def parseBatteryData(self, buffer, startIndex, sampleLength, timeStamp):
        (ts,consumption, voltageLevel, currentPercentage) = struct.unpack(
            "IhHB", buffer[startIndex : startIndex + 4 + 2 + 2 +1]
        )
        self.dataBuffer.dataDict["Battery"].data[0].append(ts)
        self.dataBuffer.dataDict["Battery"].data[1].append(consumption)
        self.dataBuffer.dataDict["Battery"].data[2].append(voltageLevel)
        self.dataBuffer.dataDict["Battery"].data[3].append(currentPercentage)
    
    def parseIMURawComboV2(self, buffer, startIndex, sampleLength, timeStamp):
            # Validate packet length matches expected size for 64 samples
            expected_length = 4 + 2 + (64 * 20)  # timestamp + numSamples + (64 * sample_size)
            if sampleLength != expected_length:
                parser_logger.warning(f"Invalid packet length {sampleLength}, expected {expected_length}")
                return startIndex

            (timeStamp,) = struct.unpack("I", buffer[startIndex : startIndex + 4])
            startIndex += 4
            (numberOfSamples,) = struct.unpack("H", buffer[startIndex : startIndex + 2])
            startIndex += 2

            # Validate number of samples
            if numberOfSamples != 64:
                parser_logger.warning(f"Invalid number of samples {numberOfSamples}, expected 64")
                return startIndex

            self.logf(f"numberOfSamplesInPacket: {numberOfSamples}")
            
            # Calculate end index to ensure we don't read past packet boundary
            end_index = startIndex + (numberOfSamples * 20)  # 20 bytes per sample
            if end_index > len(buffer):
                parser_logger.warning(f"Packet would read past buffer end")
                return startIndex

            for i in range(numberOfSamples):
                sample_start = startIndex + (i * 20)
                
                # Read accelerometer data
                (accXValRaw, accYValRaw, accZValRaw) = struct.unpack(
                    ">hhh", buffer[sample_start : sample_start + 6]
                )
                
                # Read gyroscope data
                (gyrXValRaw, gyrYValRaw, gyrZValRaw) = struct.unpack(
                    ">hhh", buffer[sample_start + 6 : sample_start + 12]
                )
                
                # Read magnetometer data
                (magXValRaw, magYValRaw, magZValRaw) = struct.unpack(
                    "<hhh", buffer[sample_start + 12 : sample_start + 18]
                )
                
                # Read temperature
                (temperature,) = struct.unpack(">h", buffer[sample_start + 18 : sample_start + 20])

                # Store the data
                self.dataBuffer.dataDict["ImuAccRaw"].data[0].append(timeStamp + i)
                self.dataBuffer.dataDict["ImuAccRaw"].data[1].append(accXValRaw)
                self.dataBuffer.dataDict["ImuAccRaw"].data[2].append(accYValRaw)
                self.dataBuffer.dataDict["ImuAccRaw"].data[3].append(accZValRaw)

                self.dataBuffer.dataDict["ImuGyrRaw"].data[0].append(timeStamp + i)
                self.dataBuffer.dataDict["ImuGyrRaw"].data[1].append(gyrXValRaw)
                self.dataBuffer.dataDict["ImuGyrRaw"].data[2].append(gyrYValRaw)
                self.dataBuffer.dataDict["ImuGyrRaw"].data[3].append(gyrZValRaw)

                self.dataBuffer.dataDict["ImuMagRaw"].data[0].append(timeStamp + i)
                self.dataBuffer.dataDict["ImuMagRaw"].data[1].append(magXValRaw)
                self.dataBuffer.dataDict["ImuMagRaw"].data[2].append(magYValRaw)
                self.dataBuffer.dataDict["ImuMagRaw"].data[3].append(magZValRaw)

                self.dataBuffer.dataDict["ImuTemp"].data[0].append(timeStamp + i)
                self.dataBuffer.dataDict["ImuTemp"].data[1].append(temperature)

            startIndex = end_index
            return startIndex

    def parseIMURawComboV3(self, buffer, startIndex, sampleLength, timeStamp):
        (timeStamp,) = struct.unpack("I", buffer[startIndex : startIndex + 4])
        startIndex += 4
        (tsf,) = struct.unpack("Q", buffer[startIndex : startIndex + 8])
        startIndex += 8        
        (numberOfSamples,) = struct.unpack("H", buffer[startIndex : startIndex + 2])
        startIndex += 2

        self.dataBuffer.dataDict["TimeSync"].data[0].append(tsf)
        self.dataBuffer.dataDict["TimeSync"].data[1].append(timeStamp)

        for i in range(numberOfSamples):
            (accXValRaw, accYValRaw, accZValRaw) = struct.unpack( 
                ">hhh", buffer[startIndex : startIndex + 6]
            )
            startIndex += 6
            (gyrXValRaw, gyrYValRaw, gyrZValRaw) = struct.unpack(
                ">hhh", buffer[startIndex : startIndex + 6]
            )
            startIndex += 6
            (magXValRaw, magYValRaw, magZValRaw) = struct.unpack(
                "<hhh", buffer[startIndex : startIndex + 6]
            )
            startIndex += 6
            (temperature,) = struct.unpack(">h", buffer[startIndex : startIndex + 2])
            startIndex += 2
            ts = timeStamp + i
            if len(self.dataBuffer.dataDict["ImuAccRaw"].data[0]) > 10:
                lastTs = self.dataBuffer.dataDict["ImuAccRaw"].data[0][-1]
                if abs(lastTs - ts) != 1:
                    self.missedSamples += 1

            self.dataBuffer.dataDict["ImuAccRaw"].data[0].append(ts)
            self.dataBuffer.dataDict["ImuAccRaw"].data[1].append(accXValRaw)
            self.dataBuffer.dataDict["ImuAccRaw"].data[2].append(accYValRaw)
            self.dataBuffer.dataDict["ImuAccRaw"].data[3].append(accZValRaw)

            self.dataBuffer.dataDict["ImuGyrRaw"].data[0].append(timeStamp + i)
            self.dataBuffer.dataDict["ImuGyrRaw"].data[1].append(gyrXValRaw)
            self.dataBuffer.dataDict["ImuGyrRaw"].data[2].append(gyrYValRaw)
            self.dataBuffer.dataDict["ImuGyrRaw"].data[3].append(gyrZValRaw)

            self.dataBuffer.dataDict["ImuMagRaw"].data[0].append(timeStamp + i)
            self.dataBuffer.dataDict["ImuMagRaw"].data[1].append(magXValRaw)
            self.dataBuffer.dataDict["ImuMagRaw"].data[2].append(magYValRaw)
            self.dataBuffer.dataDict["ImuMagRaw"].data[3].append(magZValRaw)

            self.dataBuffer.dataDict["ImuTemp"].data[0].append(timeStamp + i)
            self.dataBuffer.dataDict["ImuTemp"].data[1].append(temperature)

    def parsePingV2Data(self, buffer, startIndex, sampleLength, timeStamp):
        (timeStamp,) = struct.unpack("I", buffer[startIndex : startIndex + 4])
        startIndex += 4

        ticksSinceStart = struct.unpack("Q", buffer[startIndex : startIndex + 8])[0]
        startIndex += 8

        usSinceEpoch = struct.unpack("Q", buffer[startIndex : startIndex + 8])[0]
        startIndex += 8

        startIndex += 8

        self.dataBuffer.dataDict["PingV2"].data[0].append(timeStamp)
        self.dataBuffer.dataDict["PingV2"].data[1].append(ticksSinceStart)
        self.dataBuffer.dataDict["PingV2"].data[2].append(usSinceEpoch)

    def parseIMUConfig(self, buffer, startIndex, sampleLength, timeStamp):
        imuConfig = struct.unpack('I', buffer[startIndex:startIndex + 4])[0]
        dataRate = imuConfig & self.maskImuDataRate
        accelerometerFSR = imuConfig & self.maskImuAccFsr
        gyroscopeFSR = imuConfig & self.maskImuGyrFsr
        features = imuConfig & self.maskImuFeatures

        values = [[dataRate, accelerometerFSR, gyroscopeFSR, features]]
        data = self.ParsedData(self.DataStreamType.DATA_TYPE_IMU_CONFIG, values)
        # TODO NEEDS STORAGE

    def parseFileInfo(self, buffer, startIndex, sampleLength, timeStamp):
        fSize = struct.unpack("<I", buffer[:4])[0]
        fName = buffer[startIndex:sampleLength].decode("ascii")
        self.logf(f"Fname: {fName}, fSize: {fSize}")
        # return fSize, fName

    def parseFilePart(self, buffer, startIndex, sampleLength, timeStamp):
        chunkNo = struct.unpack("<H", buffer[:2])[0]
        chunkData = buffer[startIndex:sampleLength]
        # return chunkNo, chunkData

    def parseStreamToken(self, buffer, startIndex, sampleLength, timeStamp):
        """Parse stream start/stop token"""
        print(f"DEBUG: parseStreamToken called with length={sampleLength}")
        try:
            if sampleLength != 9:  # 1 byte action + 8 bytes timestamp
                parser_logger.warning(f"Invalid stream token length {sampleLength}, expected 9")
                return startIndex + sampleLength  # Skip the invalid data
                
            (action,) = struct.unpack("B", buffer[startIndex : startIndex + 1])
            (timestamp,) = struct.unpack("<Q", buffer[startIndex + 1 : startIndex + 9])  # Use little-endian format
            
            print(f"DEBUG: Parsed stream token - action={action}, timestamp={timestamp}")
            
            self.dataBuffer.dataDict["StreamToken"].data[0].append(action)
            self.dataBuffer.dataDict["StreamToken"].data[1].append(timestamp)
            
            # Log the stream token
            action_str = "START" if action == 1 else "STOP"
            print(f"🚀 STREAM {action_str} TOKEN received - Device: {self.deviceName}, Timestamp: {timestamp}")
            self.logf(f"🚀 STREAM {action_str} TOKEN received - Device: {self.deviceName}, Timestamp: {timestamp}")
            
            return startIndex + 9
            
        except Exception as e:
            parser_logger.error(f"Error parsing stream token: {str(e)}")
            return startIndex + sampleLength  # Skip the problematic data


    parsers = {
        DataStreamType.DATA_TYPE_DEVICE_NAME:               parseDeviceName,
        DataStreamType.DATA_TYPE_SYS_BATTERY:               parseBatteryData,
        DataStreamType.DATA_TYPE_SYS_PING_V2:               parsePingV2Data,
        DataStreamType.DATA_TYPE_IMU_RAW_COMBO_V2:          parseIMURawComboV2,
        DataStreamType.DATA_TYPE_IMU_RAW_COMBO_V3:          parseIMURawComboV3,        
        DataStreamType.DATA_TYPE_IMU_CONFIG:                parseIMUConfig,
        DataStreamType.DATA_TYPE_FILEINFO:                  parseFileInfo,
        DataStreamType.DATA_TYPE_FILEPART:                  parseFilePart,
        DataStreamType.DATA_TYPE_STREAM_TOKEN:              parseStreamToken,
    }

    def crcValid(self, data, start, length):
        crcStart = start + length + self.HEADER_LENGTH

        crcGot = struct.unpack("H", data[crcStart : crcStart + 2])[0]
        crcCalc = Parser.crc16(data, start, length + self.HEADER_LENGTH)
        if crcGot == crcCalc:
            return True

        return False

    @staticmethod
    def crc16(data, start, size):
        return crc16_mod(memoryview(data)[start : start + size])

    def parseStream(self, buffer):
        bufferLength = len(buffer)
        i = 0
        timestamp = 0
        
        # Minimum valid packet size: header(4) + min_data(1) + crc(2)
        MIN_PACKET_SIZE = self.HEADER_LENGTH + 1 + self.CRC_LENGTH
        
        while i < bufferLength:
            # Ensure we have enough bytes for a minimum packet
            if (bufferLength - i) < MIN_PACKET_SIZE:
                return i

            # Look for packet header marker
            if buffer[i] != self.HEADER_ID_COMMAND:
                i += 1
                continue

            # Read packet header
            try:
                (datatype,) = struct.unpack("xB", buffer[i : i + 2])
                (sampleLength,) = struct.unpack("<H", buffer[i + 2 : i + 4])
                # Add debugging for all packet types
                if datatype == 0x9A:
                    print(f"DEBUG: Found stream token packet header: type=0x{datatype:02X}, length={sampleLength}")
                self.logf(f"Found packet: type={datatype} (0x{datatype:02X}), length={sampleLength}")
            except struct.error:
                i += 1
                continue

            # Calculate total packet length
            packetLength = self.HEADER_LENGTH + sampleLength + self.CRC_LENGTH

            # Validate packet length
            if packetLength > self.MAX_PACKET_LEN:
                parser_logger.warning(f"Packet length {packetLength} exceeds maximum {self.MAX_PACKET_LEN}")
                i += 1
                continue

            # Ensure we have the complete packet
            if (bufferLength - i) < packetLength:
                return i

            # Validate CRC
            if not self.crcValid(buffer, i, sampleLength):
                parser_logger.warning(f"CRC mismatch for packet at offset {i}")
                i += 1
                continue

            # Get packet type
            datatypeEnum = self.int2DataStreamType(datatype)
            if datatypeEnum is None:
                parser_logger.warning(f"Unknown packet type {datatype} (0x{datatype:02X})")
                i += packetLength
                continue

            # Add debugging for stream token
            if datatype == 0x9A:
                print(f"DEBUG: Found stream token packet, enum: {datatypeEnum}")
                self.logf(f"DEBUG: Found stream token packet, enum: {datatypeEnum}")

            # Find parser for this packet type
            parserFunc = self.parsers.get(datatypeEnum, None)
            if parserFunc:
                # Add debugging for stream token
                if datatype == 0x9A:
                    print(f"DEBUG: Found stream token parser function: {parserFunc}")
                    self.logf(f"DEBUG: Found stream token parser function: {parserFunc}")
                
                try:
                    # Extract packet number for IMU data
                    if datatypeEnum == self.DataStreamType.DATA_TYPE_IMU_RAW_COMBO_V2 and i >= 4:
                        try:
                            (packetNumber,) = struct.unpack("I", buffer[i - 4 : i])
                            self.logf(f"found packetNumber: {packetNumber} type {datatypeEnum} len {sampleLength}")
                        except struct.error:
                            pass

                    # Parse packet data
                    bytes_parsed = parserFunc(self, buffer, i + self.HEADER_LENGTH, sampleLength, timestamp)
                    
                    # Verify parsing progress
                    if bytes_parsed <= i:
                        parser_logger.warning(f"Parser made no progress, skipping packet")
                        i += packetLength
                        continue
                        
                    i = bytes_parsed

                except Exception as e:
                    parser_logger.error(f"Error parsing packet: {str(e)}")
                    i += packetLength
                    continue

                if self.dataCallback:
                    self.dataCallback(datatype, self.deviceName)
            else:
                parser_logger.warning(f"No parser found for data type {datatypeEnum}")
                i += packetLength

        return i

    
if __name__ == "__main__":
    pass
