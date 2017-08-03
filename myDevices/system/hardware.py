"""
This module provides constants for the board revision info and pin mapping as well as
a class for getting hardware info, including manufacturer, model and MAC address.
"""
import re
import sys
from uuid import getnode
from myDevices.utils.logger import exception, info, warn, error, debug

BOARD_REVISION = 0
CPU_REVISION = "0"
MAPPING = []

try:
    with open("/proc/cpuinfo") as f:
        rc = re.compile("Revision\s*:\s(.*)\n")
        info = f.read()
        result = rc.search(info)
        if result:
            CPU_REVISION = result.group(1)
            if CPU_REVISION.startswith("1000"):
                CPU_REVISION = CPU_REVISION[-4:]
            cpurev = int(CPU_REVISION, 16)
            if cpurev < 0x04:
                BOARD_REVISION = 1
                MAPPING = ["V33", "V50", 0, "V50", 1, "GND", 4, 14, "GND", 15, 17, 18, 21, "GND", 22, 23, "V33", 24, 10, "GND", 9, 25, 11, 8, "GND", 7]
            elif cpurev < 0x10:
                BOARD_REVISION = 2
                MAPPING = ["V33", "V50", 2, "V50", 3, "GND", 4, 14, "GND", 15, 17, 18, 27, "GND", 22, 23, "V33", 24, 10, "GND", 9, 25, 11, 8, "GND", 7]
            else:
                BOARD_REVISION = 3
                MAPPING = ["V33", "V50", 2, "V50", 3, "GND", 4, 14, "GND", 15, 17, 18, 27, "GND", 22, 23, "V33", 24, 10, "GND", 9, 25, 11, 8, "GND", 7, "DNC", "DNC" , 5, "GND", 6, 12, 13, "GND", 19, 16, 26, 20, "GND", 21]
except:
    exception("Error reading cpuinfo")


class Hardware:
    """Class for getting hardware info, including manufacturer, model and MAC address."""

    def __init__(self):
        """Initialize board revision and model dict"""
        self.Revision = CPU_REVISION
        self.model = 'Unknown'
        if self.Revision == 'Beta':
            self.model = 'Model B (Beta)'
        if self.Revision in ('000d', '000e', '000f', '0002', '0003', '0004', '0005', '0006'):
            self.model = 'Model B'
        if self.Revision in ('0007', '0008', '0009'):
            self.model = 'Model A'
        if self.Revision in ('0010', '0013', '900032'):
            self.model = 'Model B +'
        if self.Revision in ('0011', '0014'):
            self.model = 'Compute Module'
        if self.Revision in ('0012', '0015'):
            self.model = 'Model A+'
        if self.Revision in ('a01041', 'a21041', 'a22042'):
            self.model = 'Pi 2 Model B'
        if self.Revision in ('900092', '900093'):
            self.model = 'Zero'
        if self.Revision in ('9000c1',):
            self.model = 'Zero W'
        if self.Revision in ('a02082', 'a22082'):
            self.model = 'Pi 3 Model B'            
        self.manufacturer = 'Element14/Premier Farnell'
        if self.Revision in ('a01041', '900092', 'a02082', '0012', '0011', '0010', '000e', '0008', '0004'):
            self.manufacturer = 'Sony, UK'
        if self.Revision in ('0014', '0015', 'a21041', 'a22082'):
            self.manufacturer = 'Embest, China'
        if self.Revision in ('0005', '0009', '000f'):
            self.manufacturer = 'Qisda'
        if self.Revision in ('0006', '0007', '000d'):
            self.manufacturer = 'Egoman'

    def getManufacturer(self):
        """Return manufacturer name as string"""
        return self.manufacturer

    def getModel(self):
        """Return model name as string"""
        return self.model

    def getMac(self, format=2):
        """Return MAC address as string"""
        if format < 2:
            format = 2
        if format > 4:
            format = 4
        mac_num = hex(getnode()).replace('0x', '').upper()
        mac = '-'.join(mac_num[i : i + format] for i in range(0, 11, format))
        return mac

