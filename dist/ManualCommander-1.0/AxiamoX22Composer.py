cmd = []
import binascii
import crcmod
import struct


class X22Composer:
    def __init__(self):
        self.crc16_mod = crcmod.mkCrcFun(
            0x18005, rev=True, initCrc=0x0000, xorOut=0x0000
        )

        self.HEADER_ID_PARAMETERS = 0x7D
        # self.WIFI_1 = 0
        # self.SAVE_SETTINGS = 5
        # self.SET_CONSUMER_MASK = 7

        self.WIFI_1                          = 0
        self.WIFI_2                          = 1
        self.WIFI_3                          = 2
        self.TOTAL_WIFI_PROFILES             = 3
        self.GET_PERIPHERAL_CONFIGURATIONS   = 4
        self.SAVE_SETTINGS                   = 5
        self.SET_BT_MAC_ADDRESS              = 6
        self.SET_CONSUMER_MASK               = 7
        self.SET_DATETIME                    = 8
        self.SET_OFFLINE_RECORDING_ENABLED   = 9
        self.SET_START_OFFLINE_RECORDING     = 10
        self.SET_CPU_FREQUENCY               = 6
        self.SET_IMU_FREQUENCY               = 16
        self.CMD_DEVICE                      = 1 << 5
        self.DATARATE_56HZ = 0x00000000
        self.DATARATE_112HZ = 0x00000001
        self.DATARATE_225HZ = 0x00000002

        self.DATARATE_RAW_100HZ = 0x00000003
        self.DATARATE_RAW_200HZ = 0x00000004
        self.DATARATE_RAW_500HZ = 0x00000005
        self.DATARATE_RAW_1000HZ = 0x00000006
        self.TEST_MODE = 0x00000007

        self.DATARATE_RAW_1Hz = 0x00000010
        self.DATARATE_RAW_10Hz = 0x00000011
        self.DATARATE_RAW_25Hz = 0x00000012
        self.DATARATE_RAW_50Hz = 0x00000013
        self.DATARATE_RAW_400Hz = 0x00000016
        self.DATARATE_RAW_800Hz = 0x00000017
        self.DATARATE_RAW_1600Hz = 0x00000018
        self.DATARATE_RAW_3200Hz = 0x00000019
        self.DATARATE_RAW_6400Hz = 0x0000001A

        self.DATARATE_FIFO_6Hz5 = 0x00000020
        self.DATARATE_FIFO_12Hz5 = 0x00000021
        self.DATARATE_FIFO_26Hz = 0x00000022
        self.DATARATE_FIFO_52Hz = 0x00000023
        self.DATARATE_FIFO_104Hz = 0x00000024
        self.DATARATE_FIFO_208Hz = 0x00000025
        self.DATARATE_FIFO_416Hz = 0x00000026
        self.DATARATE_FIFO_833Hz = 0x00000027
        self.DATARATE_FIFO_1666Hz = 0x00000028
        self.DATARATE_FIFO_3332Hz = 0x00000029
        self.DATARATE_FIFO_6667Hz = 0x0000002A

        self.ACC_2G = 0x00000100
        self.ACC_4G = 0x00000200
        self.ACC_8G = 0x00000300
        self.ACC_16G = 0x00000400

        self.GYR_250DPS = 0x00010000
        self.GYR_500DPS = 0x00020000
        self.GYR_1000DPS = 0x00030000
        self.GYR_2000DPS = 0x00040000
        self.GYR_125DPS = 0x00050000
        self.GYR_4000DPS = 0x00060000
        self.MAG_16GFFSR = 0x00400000

        #### Commands
        self.HEADER_ID_COMMAND = 0x7C
        self.SET_MODE = 8
        #### Request
        self.HEADER_ID_REQUEST = 0x7E

        ## Producer indices
        self.IndexDevice = int(0x0000)
        self.IndexWiFi = int(0x0001)
        self.IndexIMU = int(0x0003)
        self.IndexFuelGauge = int(0x0004)
        self.IndexPing = int(0x0005)
        self.IndexBluetooth = int(0x000B)
        self.INDEX_STORAGE = int(0x000C)

        ## Consumer indices
        self.INDEX_BT = (0,)
        self.INDEX_STORAGE = (1,)
        self.INDEX_WIFI = 2

        ##DeviceCmdPayload
        self.DeviceShutdown = 1
        self.DeviceReboot   = 2
        self.DeviceFactory  = 3
        self.DeviceButtonPress = 4
        self.DeviceDeepSleep  = 5
        self.EnableForceOfflineRec = 55
        self.DisableForceOfflineRec = 56
        self.SyncData = 57
        self.EraseFlash = 58
        self.WifiSleep = 59
        self.EnableDataStream = 60
        self.DisableDataStream = 61
        self.ToggleImuComboFormat = 62


        ##WifiConfigurations:
        self.WIFI_IDENTIFY            = 1
        # WIFI_DISCOVERY              = 0,
        # WIFI_START_UDP_SYNCED       = 2,
        # WIFI_STOP_UDP_STREAM        = 3,
        # WIFI_START_WIFI_UPLOAD      = 4,
        # WIFI_STOP_WIFI_UPLOAD       = 5,
        # WIFI_UPLOAD_DONE            = 6,
        # WIFI_CONNECT_TO_NETWORK     = 7,
        # WIFI_RESYNC                 = 8,
        # WIFI_START_UDP_STREAM       = 9

    def crc16(self, data, start, size):
        return self.crc16_mod(memoryview(data)[start : start + size])

    def composeWifiCred(self, WifiName, WifiPW):
        packetlength = len(WifiName) + len(WifiPW) + 2
        context = self.WIFI_1
        cmd = bytearray()
        cmd.append(self.HEADER_ID_PARAMETERS)
        cmd.append(packetlength)
        cmd.append(context)
        cmd.extend(WifiName.encode())
        cmd.extend("\t".encode())
        cmd.extend(WifiPW.encode())
        cmd.extend(self.crc16(cmd, 0, packetlength + 4).to_bytes(2, "big"))
        return cmd

    def composeWifiIdentify(self):
        packetlength = 4
        cmd = bytearray()
        cmd.append(self.HEADER_ID_COMMAND)
        cmd.append(packetlength)
        cmd.extend(self.IndexWiFi.to_bytes(2, "big"))
        cmd.append(self.SET_MODE)
        cmd.append(self.WIFI_IDENTIFY)
        cmd.extend(self.crc16(cmd, 0, packetlength + 4).to_bytes(2, "big"))
        return cmd

        

    def composeSaveSettings(self):
        packetlength = 1
        context = self.SAVE_SETTINGS
        cmd = bytearray()
        cmd.append(self.HEADER_ID_PARAMETERS)
        cmd.append(packetlength)
        cmd.append(context)
        cmd.extend(self.crc16(cmd, 0, packetlength + 4).to_bytes(2, "big"))
        return cmd

    def composeSetCpuFrequency(self, frequency_mhz):
        """Compose a command to set CPU frequency
        
        Args:
            frequency_mhz (int): CPU frequency in MHz (80, 160, or 240)
        """
        packetlength = 2  # Fixed: context (1 byte) + frequency (1 byte) = 2 bytes
        context = self.SET_CPU_FREQUENCY
        cmd = bytearray()
        cmd.append(self.HEADER_ID_PARAMETERS)
        cmd.append(packetlength)
        cmd.append(context)
        cmd.append(frequency_mhz)
        cmd.extend(self.crc16(cmd, 0, packetlength + 4).to_bytes(2, "big"))
        return cmd

    def composeSetImuFrequency(self, frequency_hz):
        """Compose a parameter command to set IMU frequency
        
        Args:
            frequency_hz (int): IMU frequency in Hz (1, 10, 25, 50, 100, 200, 400, 500, 800, 1000, 1600, 3200, 6400)
        """
        packetlength = 5  # Fixed: context (1 byte) + frequency (4 bytes) = 5 bytes
        context = self.SET_IMU_FREQUENCY
        cmd = bytearray()
        cmd.append(self.HEADER_ID_PARAMETERS)
        cmd.append(packetlength)
        cmd.append(context)
        # Add frequency as 4-byte little-endian
        cmd.extend(frequency_hz.to_bytes(4, "little"))
        cmd.extend(self.crc16(cmd, 0, packetlength + 4).to_bytes(2, "big"))
        return cmd

    def composeSetupSensors(self, rate, rangeAccel, rangeGyro,rangeMag):
        packetlength = 7
        cmd = bytearray()
        cmd.append(self.HEADER_ID_COMMAND)
        cmd.append(packetlength)
        cmd.extend(self.IndexIMU.to_bytes(2, "big"))
        cmd.append(self.SET_MODE)
        modeToSet = rate | rangeAccel | rangeGyro | rangeMag
        cmd.extend(modeToSet.to_bytes(4, "little"))
        cmd.extend(self.crc16(cmd, 0, packetlength + 4).to_bytes(2, "big"))
        return cmd

    def composeConsumersMask(self, producers):
        packetlength = 4
        context = self.SET_CONSUMER_MASK
        cmd = bytearray()
        cmd.append(self.HEADER_ID_PARAMETERS)
        cmd.append(packetlength)
        cmd.append(context)
        cmd.append(self.INDEX_WIFI)  # which consumer we want to configure
        cmd.append(producers & 0xFF)
        cmd.append((producers & 0xFF00) >> 8)
        cmd.extend(self.crc16(cmd, 0, packetlength + 4).to_bytes(2, "big"))
        return cmd
    

    def composeFactoryReset(self):
        return bytearray.fromhex("7c0400002003fda3")

    def composeShutDown(self):
        packetlength = 4
        cmd = bytearray()
        cmd.append(self.HEADER_ID_COMMAND)
        cmd.append(packetlength)
        cmd.extend(self.IndexDevice.to_bytes(2, "big"))
        cmd.append(self.CMD_DEVICE)
        cmd.append(self.DeviceShutdown)
        cmd.extend(self.crc16(cmd, 0, len(cmd)).to_bytes(2, "big"))
        return cmd

    def composeDeepSleep(self):
        packetlength = 4
        cmd = bytearray()
        cmd.append(self.HEADER_ID_COMMAND)
        cmd.append(packetlength)
        cmd.extend(self.IndexDevice.to_bytes(2, "big"))
        cmd.append(self.CMD_DEVICE)
        cmd.append(self.DeviceDeepSleep)
        cmd.extend(self.crc16(cmd, 0, len(cmd)).to_bytes(2, "big"))
        return cmd
    

    
    def composeReboot(self):
        packetlength = 4
        cmd = bytearray()
        cmd.append(self.HEADER_ID_COMMAND)
        cmd.append(packetlength)
        cmd.extend(self.IndexDevice.to_bytes(2, "big"))
        cmd.append(self.CMD_DEVICE)
        cmd.append(self.DeviceReboot)
        cmd.extend(self.crc16(cmd, 0, len(cmd)).to_bytes(2, "big"))
        return cmd

    def composeEnableForceOffline(self):
        packetlength = 4
        cmd = bytearray()
        cmd.append(self.HEADER_ID_COMMAND)
        cmd.append(packetlength)
        cmd.extend(self.IndexDevice.to_bytes(2, "big"))
        cmd.append(self.CMD_DEVICE)
        cmd.append(self.EnableForceOfflineRec)
        cmd.extend(self.crc16(cmd, 0, len(cmd)).to_bytes(2, "big"))
        return cmd        
    
    def composeDisableForceOffline(self):
        packetlength = 4
        cmd = bytearray()
        cmd.append(self.HEADER_ID_COMMAND)
        cmd.append(packetlength)
        cmd.extend(self.IndexDevice.to_bytes(2, "big"))
        cmd.append(self.CMD_DEVICE)
        cmd.append(self.DisableForceOfflineRec)
        cmd.extend(self.crc16(cmd, 0, len(cmd)).to_bytes(2, "big"))
        return cmd 

    def composeWifiSleep(self):
        packetlength = 4
        cmd = bytearray()
        cmd.append(self.HEADER_ID_COMMAND)
        cmd.append(packetlength)
        cmd.extend(self.IndexDevice.to_bytes(2, "big"))
        cmd.append(self.CMD_DEVICE)
        cmd.append(self.WifiSleep)
        cmd.extend(self.crc16(cmd, 0, len(cmd)).to_bytes(2, "big"))
        return cmd             

    def composeSync(self):
        packetlength = 4
        cmd = bytearray()
        cmd.append(self.HEADER_ID_COMMAND)
        cmd.append(packetlength)
        cmd.extend(self.IndexDevice.to_bytes(2, "big"))
        cmd.append(self.CMD_DEVICE)
        cmd.append(self.SyncData)
        cmd.extend(self.crc16(cmd, 0, len(cmd)).to_bytes(2, "big"))
        return cmd     
    
    def composeEraseFlash(self):
        packetlength = 4
        cmd = bytearray()
        cmd.append(self.HEADER_ID_COMMAND)
        cmd.append(packetlength)
        cmd.extend(self.IndexDevice.to_bytes(2, "big"))
        cmd.append(self.CMD_DEVICE)
        cmd.append(self.EraseFlash)
        cmd.extend(self.crc16(cmd, 0, len(cmd)).to_bytes(2, "big"))
        return cmd     

    def composeEnableDataStream(self):
        """Compose a command to enable datastream"""
        packetlength = 4
        cmd = bytearray()
        cmd.append(self.HEADER_ID_COMMAND)
        cmd.append(packetlength)
        cmd.extend(self.IndexDevice.to_bytes(2, "big"))
        cmd.append(self.CMD_DEVICE)
        cmd.append(self.EnableDataStream)
        cmd.extend(self.crc16(cmd, 0, len(cmd)).to_bytes(2, "big"))
        return cmd

    def composeDisableDataStream(self):
        """Compose a command to disable datastream"""
        packetlength = 4
        cmd = bytearray()
        cmd.append(self.HEADER_ID_COMMAND)
        cmd.append(packetlength)
        cmd.extend(self.IndexDevice.to_bytes(2, "big"))
        cmd.append(self.CMD_DEVICE)
        cmd.append(self.DisableDataStream)
        cmd.extend(self.crc16(cmd, 0, len(cmd)).to_bytes(2, "big"))
        return cmd

    def composeToggleImuComboFormat(self):
        packetlength = 4
        cmd = bytearray()
        cmd.append(self.HEADER_ID_COMMAND)
        cmd.append(packetlength)
        cmd.extend(self.IndexDevice.to_bytes(2, "big"))
        cmd.append(self.CMD_DEVICE)
        cmd.append(self.ToggleImuComboFormat)
        cmd.extend(self.crc16(cmd, 0, len(cmd)).to_bytes(2, "big"))
        return cmd

    def composeX22Command(self, deviceIndex, payloadCmd, args):
        bytestream = struct.pack(
            ">BBHB",
            self.HEADER_ID_COMMAND,
            7 if args else 3,  # 2 + 1 + 4
            deviceIndex,
            payloadCmd,
        )
        if args:
            bytestream += struct.pack("=I", args)
        crc = self.crc16(bytestream, 0, 9 if args else 5)
        bytestream += struct.pack(">H", crc)
        return bytestream

    def composeX22Parameter(self, paramCtx, data: bytes):
        paramLen = 1 + len(data)
        bytestream = struct.pack(
            ">BBB",
            self.HEADER_ID_PARAMETERS,
            paramLen,
            paramCtx,
        )
        bytestream += data
        crc = self.crc16(bytestream, 0, paramLen + 2)
        bytestream += struct.pack(">H", crc)
        return bytestream

    def composeX22Request(self, deviceIndex, command, data):
        paramLen = 4 + len(data)
        bytestream = struct.pack(
            ">BBHH",
            self.HEADER_ID_REQUEST,
            paramLen,
            deviceIndex,
            command,
        )
        bytestream += data
        crc = self.crc16(bytestream, 0, paramLen + 2)
        bytestream += struct.pack(">H", crc)
        return bytestream

    # Task Tracer Methods
    def composeTracerStart(self):
        """Compose a command to start task tracing"""
        return self.composeX22Parameter(11, b'')  # TASK_TRACER_START = 11
    
    def composeTracerStop(self):
        """Compose a command to stop task tracing"""
        return self.composeX22Parameter(12, b'')  # TASK_TRACER_STOP = 12
    
    def composeTracerClear(self):
        """Compose a command to clear task trace buffer"""
        return self.composeX22Parameter(13, b'')  # TASK_TRACER_CLEAR = 13
    
    def composeTracerUpload(self):
        """Compose a command to upload task trace data"""
        return self.composeX22Parameter(14, b'')  # TASK_TRACER_UPLOAD = 14


