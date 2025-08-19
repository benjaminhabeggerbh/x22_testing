import os
import re
import argparse
import struct
from enum import Enum
import time
import array as arr
import crcmod
import binascii

crc16_mod = crcmod.mkCrcFun(0x18005, rev=True, initCrc=0x0000, xorOut=0x0000)


class DeviceDataBuffer:
    def __init__(self):
        self.clearSets()

    def clearSets(self):
        self.dataDict = {
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
                [arr.array("L"), arr.array("l"), arr.array("l")],
            ),
            "Battery": Parser.ParsedData(
                Parser.DataStreamType.DATA_TYPE_SYS_BATTERY,
                [arr.array("L"), arr.array("h"), arr.array("H"), arr.array("H")],
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
        DATA_TYPE_IMU_RAW_COMBO_V2 = 0x1C
        DATA_TYPE_IMU_RAW_TEMP = 0x1D

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

        DATA_TYPE_FILEINFO = 0x90
        DATA_TYPE_FILEPART = 0x91

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

    def __init__(self, logf=lambda *args, **kwargs: None):
        self.logf = logf
        self.dataCallback = None
        self.dataBuffer = DeviceDataBuffer()
        self.deviceName = ""
        # self.gattParser = GattParser(logf=self.logf)
        pass

    def setDataCallBack(self, dataCallback):
        self.dataCallback = dataCallback

    @classmethod
    def int2DataStreamType(cls, val):
        try:
            return cls.DataStreamType(val)
        except:
            cls.logf("type", val, "invalid")
            return None

    def parseIMUAcc(self, buffer, startIndex, sampleLength, timeStamp):
        (accXVal, accYVal, accZVal) = struct.unpack(
            "fff", buffer[startIndex : startIndex + 12]
        )

        # (accXVal, accYVal, accZVal) = struct.unpack('hhh', buffer[startIndex:startIndex+6])

        # accXVal = accXVal/float((1<<14))
        # accYVal = accYVal/float((1<<14))
        # accZVal = accZVal/float((1<<14))

        self.dataBuffer.dataDict["ImuAcc"].data[0].append(timeStamp)
        self.dataBuffer.dataDict["ImuAcc"].data[1].append(accXVal)
        self.dataBuffer.dataDict["ImuAcc"].data[2].append(accYVal)
        self.dataBuffer.dataDict["ImuAcc"].data[3].append(accZVal)

    def parseIMURawComboV2(self, buffer, startIndex, sampleLength, timeStamp):
        (timeStamp,) = struct.unpack("I", buffer[startIndex : startIndex + 4])
        startIndex += 4
        (numberOfSamples,) = struct.unpack("H", buffer[startIndex : startIndex + 2])
        startIndex += 2
        for i in range(numberOfSamples):
            # (checkA,) = struct.unpack(
            #     "B", buffer[startIndex : startIndex + 1]
            # )
            # startIndex += 1
            (accXValRaw, accYValRaw, accZValRaw) = struct.unpack(
                ">hhh", buffer[startIndex : startIndex + 6]
            )
            startIndex += 6
            # (checkB,) = struct.unpack(
            #     "B", buffer[startIndex : startIndex + 1]
            # )
            # startIndex += 1
            (gyrXValRaw, gyrYValRaw, gyrZValRaw) = struct.unpack(
                ">hhh", buffer[startIndex : startIndex + 6]
            )
            startIndex += 6
            # (checkC,) = struct.unpack(
            #     "B", buffer[startIndex : startIndex + 1]
            # )
            # startIndex += 1
            (magXValRaw, magYValRaw, magZValRaw) = struct.unpack(
                "<hhh", buffer[startIndex : startIndex + 6]
            )
            startIndex += 6
            # (checkD,) = struct.unpack(
            #     "B", buffer[startIndex : startIndex + 1]
            # )
            # startIndex += 1
            (temperature,) = struct.unpack(">h", buffer[startIndex : startIndex + 2])
            # self.logf(f"Temperature: {temperature} | {binascii.hexlify( buffer[startIndex : startIndex + 2])}")
            startIndex += 2
            # (checkE,) = struct.unpack(
            #     "B", buffer[startIndex : startIndex + 1]
            # )
            # startIndex += 1

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
            # self.logf(f"{timeStamp+i} : {hex(checkA)}, {hex(checkB)}, {hex(checkC)}, {hex(checkD)}, {hex(checkE)}")
            # self.logf(f"{timeStamp+i} : {accXValRaw}, {accYValRaw}, {accZValRaw}, {gyrXValRaw}, {gyrYValRaw}, {gyrZValRaw}, {temperature}, {magXValRaw}, {magYValRaw}, {magZValRaw}")

    def parseIMURawCombo(self, buffer, startIndex, sampleLength, timeStamp):

        (accXValRaw, accYValRaw, accZValRaw) = struct.unpack(
            ">hhh", buffer[startIndex : startIndex + 6]
        )
        startIndex += 6
        (gyrXValRaw, gyrYValRaw, gyrZValRaw) = struct.unpack(
            ">hhh", buffer[startIndex : startIndex + 6]
        )
        startIndex += 6
        temperature = struct.unpack(">h", buffer[startIndex : startIndex + 2])[0]
        startIndex += 2
        (magXValRaw, magYValRaw, magZValRaw) = struct.unpack(
            "<hhh", buffer[startIndex : startIndex + 6]
        )
        startIndex += 6
        (timeStamp,) = struct.unpack("I", buffer[startIndex : startIndex + 4])

        self.dataBuffer.dataDict["ImuAccRaw"].data[0].append(timeStamp)
        self.dataBuffer.dataDict["ImuAccRaw"].data[1].append(accXValRaw)
        self.dataBuffer.dataDict["ImuAccRaw"].data[2].append(accYValRaw)
        self.dataBuffer.dataDict["ImuAccRaw"].data[3].append(accZValRaw)

        self.dataBuffer.dataDict["ImuGyrRaw"].data[0].append(timeStamp)
        self.dataBuffer.dataDict["ImuGyrRaw"].data[1].append(gyrXValRaw)
        self.dataBuffer.dataDict["ImuGyrRaw"].data[2].append(gyrYValRaw)
        self.dataBuffer.dataDict["ImuGyrRaw"].data[3].append(gyrZValRaw)

        self.dataBuffer.dataDict["ImuMagRaw"].data[0].append(timeStamp)
        self.dataBuffer.dataDict["ImuMagRaw"].data[1].append(magXValRaw)
        self.dataBuffer.dataDict["ImuMagRaw"].data[2].append(magYValRaw)
        self.dataBuffer.dataDict["ImuMagRaw"].data[3].append(magZValRaw)

    def parseDeviceName(self, buffer, startIndex, sampleLength, timeStamp):
        self.deviceName = (
            bytes(buffer[startIndex : startIndex + sampleLength])
            .decode("utf-8")
            .rstrip("\x00")
        )

    def parseBPM(self, buffer, startIndex, sampleLength, timeStamp):
        bpmVal = struct.unpack("H", buffer[startIndex : startIndex + 2])[0]
        self.dataBuffer.bpmSet.data[0].append(timeStamp)
        self.dataBuffer.bpmSet.data[1].append(bpmVal)
        print("Parsed BPM: " + str(bpmVal))

    def parseIMUGyr(self, buffer, startIndex, sampleLength, timeStamp):
        (gyrXVal, gyrYVal, gyrZVal) = struct.unpack(
            "fff", buffer[startIndex : startIndex + 12]
        )
        self.dataBuffer.dataDict["ImuGyr"].data[0].append(timeStamp)
        self.dataBuffer.dataDict["ImuGyr"].data[1].append(gyrXVal)
        self.dataBuffer.dataDict["ImuGyr"].data[2].append(gyrYVal)
        self.dataBuffer.dataDict["ImuGyr"].data[3].append(gyrZVal)

    def parseIMUMag(self, buffer, startIndex, sampleLength, timeStamp):
        (magXVal, magYVal, magZVal) = struct.unpack(
            "hhh", buffer[startIndex : startIndex + 6]
        )

        magXVal = float(magXVal)
        magYVal = float(magYVal)
        magZVal = float(magZVal)
        self.dataBuffer.dataDict["ImuMag"].data[0].append(timeStamp)
        self.dataBuffer.dataDict["ImuMag"].data[1].append(magXVal)
        self.dataBuffer.dataDict["ImuMag"].data[2].append(magYVal)
        self.dataBuffer.dataDict["ImuMag"].data[3].append(magZVal)

    def parseIMUQuatData(self, buffer, startIndex, sampleLength, timeStamp):
        (quatW, quatX, quatY, quatZ) = struct.unpack(
            "ffff", buffer[startIndex : startIndex + 16]
        )
        self.dataBuffer.dataDict["Quat"].data[0].append(timeStamp)
        self.dataBuffer.dataDict["Quat"].data[1].append(quatW)
        self.dataBuffer.dataDict["Quat"].data[2].append(quatX)
        self.dataBuffer.dataDict["Quat"].data[3].append(quatY)
        self.dataBuffer.dataDict["Quat"].data[4].append(quatZ)

    def parseIMUStepData(self, buffer, startIndex, sampleLength, timeStamp):
        steps = struct.unpack("Q", buffer[startIndex : startIndex + 8])[0]
        self.dataBuffer.dataDict["Steps"].data[0].append(timeStamp)
        self.dataBuffer.dataDict["Steps"].data[1].append(steps)

    def parseIMURawAcc(self, buffer, startIndex, sampleLength, timeStamp):
        ">hhh --> Big endian shortshortshort"
        (accXValRaw, accYValRaw, accZValRaw) = struct.unpack(
            ">hhh", buffer[startIndex : startIndex + 6]
        )
        self.dataBuffer.dataDict["ImuAccRaw"].data[0].append(timeStamp)
        self.dataBuffer.dataDict["ImuAccRaw"].data[1].append(accXValRaw)
        self.dataBuffer.dataDict["ImuAccRaw"].data[2].append(accYValRaw)
        self.dataBuffer.dataDict["ImuAccRaw"].data[3].append(accZValRaw)

    def parseIMURawGyr(self, buffer, startIndex, sampleLength, timeStamp):
        (gyrXValRaw, gyrYValRaw, gyrZValRaw) = struct.unpack(
            ">hhh", buffer[startIndex : startIndex + 6]
        )
        self.dataBuffer.dataDict["ImuGyrRaw"].data[0].append(timeStamp)
        self.dataBuffer.dataDict["ImuGyrRaw"].data[1].append(gyrXValRaw)
        self.dataBuffer.dataDict["ImuGyrRaw"].data[2].append(gyrYValRaw)
        self.dataBuffer.dataDict["ImuGyrRaw"].data[3].append(gyrZValRaw)

    def parseIMURawMag(self, buffer, startIndex, sampleLength, timeStamp):
        (magXValRaw, magYValRaw, magZValRaw) = struct.unpack(
            ">hhh", buffer[startIndex : startIndex + 6]
        )

        (timeStamp,) = struct.unpack("I", buffer[startIndex : startIndex + 4])
        self.dataBuffer.dataDict["ImuMagRaw"].data[0].append(timeStamp)
        self.dataBuffer.dataDict["ImuMagRaw"].data[1].append(magXValRaw)
        self.dataBuffer.dataDict["ImuMagRaw"].data[2].append(magYValRaw)
        self.dataBuffer.dataDict["ImuMagRaw"].data[3].append(magZValRaw)

    def parseIMURawCounter(self, buffer, startIndex, sampleLength, timeStamp):
        pass

    def parseBarometerData(self, buffer, startIndex, sampleLength, timeStamp):
        (pressureVal, temperatureVal) = struct.unpack(
            "ii", buffer[startIndex : startIndex + 8]
        )
        self.dataBuffer.dataDict["Barometer"].data[0].append(timeStamp)
        self.dataBuffer.dataDict["Barometer"].data[1].append(pressureVal)
        self.dataBuffer.dataDict["Barometer"].data[2].append(temperatureVal)

    def parseIMURawGyrPrimaryAxisOnly(
        self, buffer, startIndex, sampleLength, timeStamp
    ):
        # self.logf(f"parsingSingleAxis")
        (gyrPrimAxVal,) = struct.unpack(">h", buffer[startIndex : startIndex + 2])
        startIndex += 2
        (primAxIdx,) = struct.unpack("B", buffer[startIndex : startIndex + 1])
        startIndex += 1
        (timeStamp,) = struct.unpack("I", buffer[startIndex : startIndex + 4])
        startIndex += 4

        self.dataBuffer.dataDict["ImuGyrRaw"].data[0].append(timeStamp)
        primAxIdx += 1
        for idx in range(1, 4):
            if idx == primAxIdx:
                self.dataBuffer.dataDict["ImuGyrRaw"].data[idx].append(gyrPrimAxVal)
            else:
                self.dataBuffer.dataDict["ImuGyrRaw"].data[idx].append(0)

    def parseStatesData(self, buffer, startIndex, sampleLength, timeStamp):
        (
            secsSinceEpoch,
            appRevMajor,
            appRevMinor,
            sessionID,
            shirtIdL,
            shirtIdH,
        ) = struct.unpack("=LBBLQQ", buffer[startIndex : startIndex + 26])

        dataOffset = 4 + 1 + 1 + 4 + 8 + 8

        self.dataBuffer.dataDict["States"].data[0].append(timeStamp)
        self.dataBuffer.dataDict["States"].data[1].append(secsSinceEpoch)
        self.dataBuffer.dataDict["States"].data[2].append(appRevMajor)
        self.dataBuffer.dataDict["States"].data[3].append(appRevMinor)
        self.dataBuffer.dataDict["States"].data[4].append(sessionID)
        self.dataBuffer.dataDict["States"].data[5].append(shirtIdL)
        self.dataBuffer.dataDict["States"].data[6].append(shirtIdH)

        self.dataBuffer.imei = buffer[
            startIndex + dataOffset : startIndex + dataOffset + self.IMEI_LEN
        ].decode("ascii")

    def parseBatteryData(self, buffer, startIndex, sampleLength, timeStamp):
        (consumption, voltageLevel, currentPercentage) = struct.unpack(
            "hHH", buffer[startIndex : startIndex + 6]
        )
        self.dataBuffer.dataDict["Battery"].data[0].append(timeStamp)
        self.dataBuffer.dataDict["Battery"].data[1].append(consumption)
        self.dataBuffer.dataDict["Battery"].data[2].append(voltageLevel)
        self.dataBuffer.dataDict["Battery"].data[3].append(currentPercentage)

    def parsePingData(self, buffer, startIndex, sampleLength, timeStamp):
        ticksSinceStart = struct.unpack("Q", buffer[startIndex : startIndex + 8])[0]
        dataOffset = 8

        usSinceEpoch = struct.unpack(
            "Q", buffer[startIndex + dataOffset : startIndex + dataOffset + 8]
        )[0]
        dataOffset = dataOffset + 8

        deviceUid = struct.unpack(
            "Q", buffer[startIndex + dataOffset : startIndex + dataOffset + 8]
        )[0]
        deviceUid = deviceUid & 0xFFFFFFFFFFFF
        dataOffset = dataOffset + 6

        sensorState = struct.unpack(
            "H", buffer[startIndex + dataOffset : startIndex + dataOffset + 2]
        )[0]
        dataOffset = dataOffset + 2

        self.dataBuffer.dataDict["Ping"].data[0].append(timeStamp)
        self.dataBuffer.dataDict["Ping"].data[1].append(deviceUid)
        self.dataBuffer.dataDict["Ping"].data[2].append(ticksSinceStart)
        self.dataBuffer.dataDict["Ping"].data[3].append(usSinceEpoch)
        self.dataBuffer.dataDict["Ping"].data[4].append(sensorState)

    def parsePingV2Data(self, buffer, startIndex, sampleLength, timeStamp):
        ticksSinceStart = struct.unpack("Q", buffer[startIndex : startIndex + 8])[0]
        dataOffset = 8

        usSinceEpoch = struct.unpack(
            "Q", buffer[startIndex + dataOffset : startIndex + dataOffset + 8]
        )[0]
        dataOffset = dataOffset + 8

        self.dataBuffer.dataDict["PingV2"].data[0].append(timeStamp)
        self.dataBuffer.dataDict["PingV2"].data[1].append(ticksSinceStart)
        self.dataBuffer.dataDict["PingV2"].data[2].append(usSinceEpoch)

    def parseIMUConfig(self, buffer, startIndex, sampleLength, timeStamp):
        imuConfig = struct.unpack("I", buffer[startIndex : startIndex + 4])[0]
        dataRate = imuConfig & self.maskImuDataRate
        accelerometerFSR = imuConfig & self.maskImuAccFsr
        gyroscopeFSR = imuConfig & self.maskImuGyrFsr
        features = imuConfig & self.maskImuFeatures

        values = [[dataRate, accelerometerFSR, gyroscopeFSR, features]]
        data = self.ParsedData(self.DataStreamType.DATA_TYPE_IMU_CONFIG, values)
        # TODO NEEDS STORAGE

    def parseBARConfig(self, buffer, startIndex, sampleLength, timeStamp):
        barConfig = struct.unpack("I", buffer[startIndex : startIndex + 4])[0]

        data = self.ParsedData(self.DataStreamType.DATA_TYPE_BAR_CONFIG, [[barConfig]])
        # TODO NEEDS STORAGE

    def parseTaskDataStats(self, buffer, startIndex, sampleLength, timeStamp):
        # TODO add this stuff

        taskName = buffer[startIndex : startIndex + 15].decode("ascii").split("\x00")[0]
        (
            frequency,
            samplesProduced,
            maxBytesProduced,
            bytesProduced,
            bufferOverflows,
            stackHighWatermark,
        ) = struct.unpack("fHHHHH", buffer[startIndex + 16 : startIndex + 30])
        values = [
            [
                taskName,
                frequency,
                samplesProduced,
                maxBytesProduced,
                bytesProduced,
                bufferOverflows,
                stackHighWatermark,
            ]
        ]
        data = self.ParsedData(self.DataStreamType.DATA_TYPE_SYS_TASK_STATS, values)
        # TODO NEEDS STORAGE

    def parseResourceDataStats(self, buffer, startIndex, sampleLength, timeStamp):
        (
            core0Idle,
            core1Idle,
            heapMinFree8bit,
            heapMinFree32bit,
            heapFree8bit,
            heapFree32bit,
            sdCardAvgTimeToSave,
        ) = struct.unpack("BBIIIIB", buffer[startIndex : startIndex + 21])
        # print(str(core0Idle), str(core1Idle), str(heapMinFree8bit), str(heapMinFree32bit), str(heapFree8bit), str(heapFree32bit), str(sdCardAvgTimeToSave))
        values = [
            [
                core0Idle,
                core1Idle,
                heapMinFree8bit,
                heapMinFree32bit,
                heapFree8bit,
                heapFree32bit,
                sdCardAvgTimeToSave,
            ]
        ]
        data = self.ParsedData(self.DataStreamType.DATA_TYPE_SYS_RESOURCES, values)
        # TODO NEEDS STORAGE

    def parseSysTime(self, buffer, startIndex, sampleLength, timeStamp):
        time = struct.unpack("l", buffer[startIndex : startIndex + 8])
        # self.logf(str(time))
        data = self.ParsedData(self.DataStreamType.DATA_TYPE_SYS_TIME, [[time]])
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

    parsers = {
        DataStreamType.DATA_TYPE_DEVICE_NAME: parseDeviceName,
        DataStreamType.DATA_TYPE_IMU_RAW_COMBO: parseIMURawCombo,
        DataStreamType.DATA_TYPE_IMU_RAW_COMBO_V2: parseIMURawComboV2,
        DataStreamType.DATA_TYPE_IMU_ACC: parseIMUAcc,
        DataStreamType.DATA_TYPE_IMU_GYR: parseIMUGyr,
        DataStreamType.DATA_TYPE_IMU_MAG: parseIMUMag,
        DataStreamType.DATA_TYPE_IMU_QUAT: parseIMUQuatData,
        DataStreamType.DATA_TYPE_IMU_STEP: parseIMUStepData,
        DataStreamType.DATA_TYPE_IMU_RAW_ACC: parseIMURawAcc,
        DataStreamType.DATA_TYPE_IMU_RAW_GYR: parseIMURawGyr,
        DataStreamType.DATA_TYPE_IMU_RAW_MAG: parseIMURawMag,
        DataStreamType.DATA_TYPE_IMU_RAW_COUNTER: parseIMURawCounter,
        DataStreamType.DATA_TYPE_BAR: parseBarometerData,
        DataStreamType.DATA_TYPE_IMU_RAW_COMBO: parseIMURawCombo,
        DataStreamType.DATA_TYPE_IMU_GYR_PRIMARY_AXIS_ONLY: parseIMURawGyrPrimaryAxisOnly,
        DataStreamType.DATA_TYPE_SYS_STATES: parseStatesData,
        DataStreamType.DATA_TYPE_SYS_BATTERY: parseBatteryData,
        DataStreamType.DATA_TYPE_SYS_PING: parsePingData,
        DataStreamType.DATA_TYPE_SYS_PING_V2: parsePingV2Data,
        DataStreamType.DATA_TYPE_IMU_CONFIG: parseIMUConfig,
        DataStreamType.DATA_TYPE_BAR_CONFIG: parseBARConfig,
        DataStreamType.DATA_TYPE_SYS_TASK_STATS: parseTaskDataStats,
        DataStreamType.DATA_TYPE_SYS_RESOURCES: parseResourceDataStats,
        DataStreamType.DATA_TYPE_SYS_TIME: parseSysTime,
        DataStreamType.DATA_TYPE_FILEINFO: parseFileInfo,
        DataStreamType.DATA_TYPE_FILEPART: parseFilePart,
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
        while i < bufferLength:
            if (bufferLength - i) <= self.HEADER_LENGTH:
                return i
            if buffer[i] != self.HEADER_ID_COMMAND:
                i = i + 1
                continue
            # import pdb; pdb.set_trace()

            (datatype,) = struct.unpack("xB", buffer[i : i + 2])
            (sampleLength,) = struct.unpack("<H", buffer[i + 2 : i + 4])

            packetLength = self.HEADER_LENGTH + sampleLength + self.CRC_LENGTH

            if packetLength > self.MAX_PACKET_LEN:
                i = i + 1
                continue

            if (bufferLength - i) < packetLength:
                return i

            if self.crcValid(buffer, i, sampleLength) is not True:
                self.logf(
                    f"Parser: CRC mismatch. seems not to be a valid packet, continuing...: {str(self.int2DataStreamType(datatype))}"
                )
                i = i + 1
                continue

            datatypeEnum = self.int2DataStreamType(datatype)
            if datatypeEnum is None:
                self.logf(
                    f"Parser: Unknown frame type: {datatype} dropping whole sample"
                )
                i = i + packetLength
                continue
            # self.logf(f"Datatype: {datatypeEnum}")
            parserFunc = self.parsers.get(datatypeEnum, None)
            if parserFunc:
                try:
                    parserFunc(
                        self, buffer, i + self.HEADER_LENGTH, sampleLength, timestamp
                    )
                    timestamp += 1
                except Exception as e:
                    self.logf(
                        f"Parser: Exception while parising: {str(e)} in function: {str(parserFunc)}"
                    )
                if self.dataCallback:
                    self.dataCallback()

            i = i + packetLength

        return i

    def parseGattHeartRateMeasurement(self, buffer, timestamp):
        flags = struct.unpack("B", buffer[:1])[0]
        dataOffset = 1
        heartRateValueFormatFlag = bool(flags & 1 << 0)
        sensorContactFlag = bool(flags & 1 << 1)
        sensorContactSupportedFlag = bool(flags & 1 << 2)
        energyExpendedPresentFlag = bool(flags & 1 << 3)
        rrIntervalPresentFlag = bool(flags & 1 << 4)

        hrValSize = 2 if heartRateValueFormatFlag else 1
        hrValStructString = "H" if heartRateValueFormatFlag else "B"
        hrVal = struct.unpack(
            hrValStructString, buffer[dataOffset : dataOffset + hrValSize]
        )[0]
        dataOffset += hrValSize
        energyExpended = None
        if energyExpendedPresentFlag:
            energyExpended = struct.unpack("H", buffer[dataOffset : dataOffset + 2])[0]
            dataOffset += 2
        rrInterval = None
        if rrIntervalPresentFlag:
            rrInterval = struct.unpack("H", buffer[dataOffset : dataOffset + 2])[0]
        self.dataBuffer.dataDict["gatt"]["HeartRate"] = self.dataBuffer.dataDict[
            "gatt"
        ].get("HeartRate", [])
        self.dataBuffer.dataDict["gatt"]["HeartRate"].append(
            [
                timestamp,
                hrVal,
                energyExpended,
                rrInterval,
                sensorContactFlag,
                sensorContactSupportedFlag,
            ]
        )

    def parseCumWheelRevs(self, buffer):
        wheelRevs, timestamp = struct.unpack("IH", buffer[:6])
        nBytesParsed = 6
        timestamp = (
            timestamp * 1000 * 1000 / 1024
        )  # unit was 1/1024 seconds, is microseconds
        return nBytesParsed, timestamp, wheelRevs

    def parseCumCrankRevs(self, buffer):
        crankRevs, timestamp = struct.unpack("HH", buffer[:4])
        nBytesParsed = 4
        timestamp = (
            timestamp * 1000 * 1000 / 1024
        )  # unit was 1/1024 seconds, is microseconds
        return nBytesParsed, timestamp, crankRevs

    def parseGattCSC(self, buffer, timestamp):
        flags = struct.unpack("B", buffer[:1])[0]
        dataOffset = 1
        now = timestamp

        wheelRevFlag = bool(flags & 1 << 0)
        crankRevFlag = bool(flags & 1 << 1)

        if wheelRevFlag:
            nBytesParsed, timestamp, wheelRevs = self.parseCumWheelRevs(
                buffer[dataOffset:]
            )
            dataOffset += nBytesParsed
            self.dataBuffer.dataDict["gatt"]["CumulativeWheelRevolutions"] = (
                self.dataBuffer.dataDict["gatt"].get("CumulativeWheelRevolutions", [])
            )
            self.dataBuffer.dataDict["gatt"]["CumulativeWheelRevolutions"].append(
                [now, wheelRevs]
            )

        if crankRevFlag:
            nBytesParsed, timestamp, crankRevs = self.parseCumCrankRevs(
                buffer[dataOffset:]
            )
            dataOffset += nBytesParsed
            self.dataBuffer.dataDict["gatt"]["CumulativeCrankRevolutions"] = (
                self.dataBuffer.dataDict["gatt"].get("CumulativeCrankRevolutions", [])
            )
            self.dataBuffer.dataDict["gatt"]["CumulativeCrankRevolutions"].append(
                [now, crankRevs]
            )

    def parseGattCyclingPowerMeasurement(self, buffer, timestamp):
        flags = struct.unpack("H", buffer[:2])[0]
        dataOffset = 2

        outData = []

        now = timestamp
        outData.append(now)

        instantaneousPower = struct.unpack("h", buffer[dataOffset : dataOffset + 2])[0]
        dataOffset += 2
        outData.append(instantaneousPower)

        pedalPowerBalanceData = None
        pedalPowerBalancePresentFlag = bool(flags & 1 << 0)
        if pedalPowerBalancePresentFlag:
            pedalPowerBalanceReferenceFlag = bool(flags & 1 << 1)
            pedalPowerBalance = struct.unpack("B", buffer[dataOffset : dataOffset + 1])[
                0
            ]
            dataOffset += 1
            pedalPowerBalanceData = (
                pedalPowerBalance / 2,
                pedalPowerBalanceReferenceFlag,
            )
        outData.append(pedalPowerBalanceData)

        accumulatedTorqueData = None
        accumulatedTorquePresentFlag = bool(flags & 1 << 2)
        if accumulatedTorquePresentFlag:
            accumulatedTorqueSourceFlag = bool(flags & 1 << 3)
            accumulatedTorque = struct.unpack("H", buffer[dataOffset : dataOffset + 2])[
                0
            ]
            dataOffset += 2
            accumulatedTorqueData = (
                accumulatedTorque / 32,
                accumulatedTorqueSourceFlag,
            )
        outData.append(accumulatedTorqueData)

        wheelRevolutionDataData = None
        wheelRevolutionDataPresentFlag = bool(flags & 1 << 4)
        if wheelRevolutionDataPresentFlag:
            nBytesParsed, timestamp, wheelRevs = self.parseCumWheelRevs(
                buffer[dataOffset:]
            )
            dataOffset += nBytesParsed
            wheelRevolutionDataData = (timestamp, wheelRevs)

        outData.append(wheelRevolutionDataData)

        crankRevolutionDataData = None
        crankRevolutionDataPresentFlag = bool(flags & 1 << 5)
        if crankRevolutionDataPresentFlag:
            nBytesParsed, timestamp, crankRevs = self.parseCumCrankRevs(
                buffer[dataOffset:]
            )
            dataOffset += nBytesParsed
            crankRevolutionDataData = (timestamp, crankRevs)
        outData.append(crankRevolutionDataData)

        extremeForceMagnitudesData = None
        extremeForceMagnitudesPresentFlag = bool(flags & 1 << 6)
        if extremeForceMagnitudesPresentFlag:
            maxForce, minForce = struct.unpack(
                "hh", buffer[dataOffset : dataOffset + 4]
            )
            dataOffset += 4
            extremeForceMagnitudesData = (maxForce, minForce)
        outData.append(extremeForceMagnitudesData)

        extremeTorqueMagnitudesData = None
        extremeTorqueMagnitudesPresentFlag = bool(flags & 1 << 7)
        if extremeTorqueMagnitudesPresentFlag:
            maxTorque, minTorque = struct.unpack(
                "hh", buffer[dataOffset : dataOffset + 4]
            )
            dataOffset += 4
            extremeTorqueMagnitudesData = (maxTorque, minTorque)
        outData.append(extremeTorqueMagnitudesData)

        extremeAnglesData = None
        extremeAnglesPresentFlag = bool(flags & 1 << 8)
        if extremeAnglesPresentFlag:
            dataOffset += 3
        outData.append(extremeAnglesData)

        topDeadSpotAngleData = None
        topDeadSpotAnglePresentFlag = bool(flags & 1 << 9)
        if topDeadSpotAnglePresentFlag:
            dataOffset += 2
        outData.append(topDeadSpotAngleData)

        bottomDeadSpotAngleData = None
        bottomDeadSpotAnglePresentFlag = bool(flags & 1 << 10)
        if bottomDeadSpotAnglePresentFlag:
            dataOffset += 2
        outData.append(bottomDeadSpotAngleData)

        accumulatedEnergyData = None
        accumulatedEnergyPresentFlag = bool(flags & 1 << 11)
        if accumulatedEnergyPresentFlag:
            accumulatedEnergy = struct.unpack("h", buffer[dataOffset : dataOffset + 2])[
                0
            ]
            dataOffset += 2
            accumulatedEnergyData = accumulatedEnergy

        outData.append(accumulatedEnergyData)

        offsetCompensationIndicatorFlag = bool(flags & 1 << 12)

        self.dataBuffer.dataDict["gatt"][
            "CyclingPowerMeasurement"
        ] = self.dataBuffer.dataDict["gatt"].get(
            "CyclingPowerMeasurement",
            {
                "fields": [
                    "WallTime",
                    "InstantaneousPower",
                    "PedalPowerBalance",
                    "AccumulatedTorque",
                    "WheelRevolutionData",
                    "CrankRevolutionData",
                    "ExtremeForceMagnitudes",
                    "ExtremeTorqueMagnitudes",
                    "ExtremeAngles",
                    "TopDeadSpotAngle",
                    "BottomDeadSpotAngle",
                    "AccumulatedEnergy",
                    "OffsetCompensationIndicator",
                ],
                "data": [],
            },
        )

        self.dataBuffer.dataDict["gatt"]["CyclingPowerMeasurement"]["data"].append(
            outData
        )

    gattParsers = {
        "2a5b": parseGattCSC,
        "2a63": parseGattCyclingPowerMeasurement,
        "2a37": parseGattHeartRateMeasurement,
    }

    def parseGattBattery(self, buffer) -> int:
        batteryLevel = struct.unpack("B", buffer[:1])[0]
        return batteryLevel

    def parseGatt(self, uuid, gattDataBuffer, timestamp):
        gattParserFunc = self.gattParsers.get(uuid, None)
        if gattParserFunc:
            # gattParserFunc(self, gattDataBuffer)
            try:
                gattParserFunc(self, gattDataBuffer, timestamp)
            except Exception as e:
                self.logf(
                    f"Parser: Exception while parising: {str(e)} in function: {str(gattParserFunc)}"
                )
        else:
            self.dataBuffer.dataDict["gatt"][uuid] = self.dataBuffer.dataDict[
                "gatt"
            ].get(uuid, [])
            self.dataBuffer.dataDict["gatt"][uuid].append(gattDataBuffer)


if __name__ == "__main__":
    pass
