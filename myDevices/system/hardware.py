"""
This module provides constants for the board revision info and pin mapping as well as
a class for getting hardware info, including manufacturer, model and MAC address.
"""
import re
import sys
from myDevices.utils.logger import exception, info, warn, error, debug

BOARD_REVISION = 0
CPU_REVISION = "0"
CPU_HARDWARE = ""

try:
    with open("/proc/cpuinfo") as f:
        cpuinfo = f.read()
        rc = re.compile("Revision\s*:\s(.*)\n")
        result = rc.search(cpuinfo)
        if result:
            CPU_REVISION = result.group(1)
            if CPU_REVISION.startswith("1000"):
                CPU_REVISION = CPU_REVISION[-4:]
            if CPU_REVISION != "0000":
                cpurev = int(CPU_REVISION, 16)
                if cpurev < 0x04:
                    BOARD_REVISION = 1
                elif cpurev < 0x10:
                    BOARD_REVISION = 2
                else:
                    BOARD_REVISION = 3
        rc = re.compile("Hardware\s*:\s(.*)\n")
        result = rc.search(cpuinfo)
        CPU_HARDWARE = result.group(1)
except:
    exception("Error reading cpuinfo")


class Hardware:
    """Class for getting hardware info, including manufacturer, model and MAC address."""

    def __init__(self):
        """Initialize board revision and model info"""
        self.Revision = '0'
        self.Serial = None
        try:
            with open('/proc/cpuinfo','r') as f:
                for line in f:
                    splitLine = line.split(':')
                    if len(splitLine) < 2:
                        continue
                    key = splitLine[0].strip()
                    value = splitLine[1].strip()
                    if key == 'Revision':
                        self.Revision = value
                    if key == 'Serial' and value != len(value) * '0':
                        self.Serial = value
        except:
            exception ("Error reading cpuinfo")
        self.model = 'Unknown'
        if self.Revision == 'Beta':
            self.model = 'Raspberry Pi Model B (Beta)'
        if self.Revision in ('000d', '000e', '000f', '0002', '0003', '0004', '0005', '0006'):
            self.model = 'Raspberry Pi Model B'
        if self.Revision in ('0007', '0008', '0009'):
            self.model = 'Raspberry Pi Model A'
        if self.Revision in ('0010', '0013', '900032'):
            self.model = 'Raspberry Pi Model B +'
        if self.Revision in ('0011', '0014'):
            self.model = 'Raspberry Pi Compute Module'
        if self.Revision in ('0012', '0015'):
            self.model = 'Raspberry Pi Model A+'
        if self.Revision in ('a01040', 'a01041', 'a21041', 'a22042'):
            self.model = 'Raspberry Pi 2 Model B'
        if self.Revision in ('900092', '900093', '920093'):
            self.model = 'Raspberry Pi Zero'
        if self.Revision in ('9000c1',):
            self.model = 'Raspberry Pi Zero W'
        if self.Revision in ('a02082', 'a22082', 'a32082'):
            self.model = 'Raspberry Pi 3 Model B'            
        if self.Revision in ('a020d3'):
            self.model = 'Raspberry Pi 3 Model B+'
        if self.Revision in ('a020a0'):
            self.model = 'Raspberry Pi Compute Module 3'
        if 'Rockchip' in CPU_HARDWARE:
            self.model = 'Tinker Board'
        self.manufacturer = 'Element14/Premier Farnell'
        if self.Revision in ('a01041', '900092', 'a02082', '0012', '0011', '0010', '000e', '0008', '0004', 'a020d3', 'a01040', 'a020a0'):
            self.manufacturer = 'Sony, UK'
        if self.Revision in ('a32082'):
            self.manufacturer = 'Sony, Japan'
        if self.Revision in ('0014', '0015', 'a21041', 'a22082', '920093'):
            self.manufacturer = 'Embest, China'
        if self.Revision in ('0005', '0009', '000f'):
            self.manufacturer = 'Qisda'
        if self.Revision in ('0006', '0007', '000d'):
            self.manufacturer = 'Egoman'
        if self.Revision == '0000':
            if 'Rockchip' in CPU_HARDWARE:
                self.manufacturer = 'ASUS'
            else:
                try:
                    with open('/proc/device-tree/model', 'r') as model_file:
                        for line in model_file:
                            if 'BeagleBone' in line:
                                index = line.index('BeagleBone')
                                self.manufacturer = line[:index - 1].strip(' \n\t\0')
                                self.model = line[index:].strip(' \n\t\0')
                                break
                except:
                    exception ("Error reading model")


    def getManufacturer(self):
        """Return manufacturer name as string"""
        return self.manufacturer

    def getModel(self):
        """Return model name as string"""
        return self.model

    def getMac(self):
        """Return MAC address as a string or None if no MAC address is found"""
        # Import netifaces here to prevent error importing this module in setup.py
        import netifaces
        interfaces = ['eth0', 'wlan0']
        try:
            interfaces.append(netifaces.gateways()['default'][netifaces.AF_INET][1])
        except:
            pass
        for interface in interfaces:
            try:
                return netifaces.ifaddresses(interface)[netifaces.AF_LINK][0]['addr']
            except ValueError:
                pass
            except:
                exception('Error getting MAC address')
        return None

    def isRaspberryPi(self):
        """Return True if device is a Raspberry Pi"""
        return 'Raspberry Pi' in self.model

    def isTinkerBoard(self):
        """Return True if device is a Tinker Board"""
        return 'Tinker Board' == self.model

    def isBeagleBone(self):
        """Return True if device is a BeagleBone"""
        return 'BeagleBone' in self.model
