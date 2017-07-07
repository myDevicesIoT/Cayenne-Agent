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
CPU_HARDWARE = ""

try:
    with open("/proc/cpuinfo") as f:
        info = f.read()
        rc = re.compile("Revision\s*:\s(.*)\n")
        result = rc.search(info)
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
        result = rc.search(info)
        CPU_HARDWARE = result.group(1)
except:
    exception("Error reading cpuinfo")


class Hardware:
    """Class for getting hardware info, including manufacturer, model and MAC address."""

    def __init__(self):
        """Initialize board revision and model dict"""
        self.Revision = CPU_REVISION
        self.model = {}
        self.model["Beta"] = "Model B (Beta)"
        self.model["000d"] = self.model["000e"] = self.model["000f"] = self.model["0002"] = self.model["0003"] = self.model["0004"] = self.model["0005"] = self.model["0006"] = "Model B"
        self.model["0007"] = self.model["0008"] = self.model["0009"] = "Model A"
        self.model["0010"] = "Model B+"
        self.model["0011"] = "Compute Module"
        self.model["0012"] = "Model A+"
        self.model["0013"] = "Model B+"
        self.model["a01041"] = "Pi 2 Model B"
        self.model["a21041"] = "Pi 2 Model B"
        self.model["900092"] = "Zero"
        self.model["a22082"] = self.model["a02082"] = "Pi 3 Model B"
        if "Rockchip" in CPU_HARDWARE:
            self.model["0000"] = "Tinker Board"

    def getManufacturer(self):
        """Return manufacturer name as string"""
        if self.Revision in ["a01041","900092", "a02082", "0012", "0011", "0010", "000e", "0008", "0004"]:
            return "Sony, UK" 
        if self.Revision == "a21041":
            return "Embest, China"
        if self.Revision in ["0005", "0009", "000f"]:
            return "Qisda"
        if self.Revision in ["0006", "0007", "000d"]:
            return "Egoman"
        if self.Revision == "0000" and "Rockchip" in CPU_HARDWARE:
            return "ASUS"
        return "Element14/Premier Farnell"

    def getModel(self):
        """Return model name as string"""
        try:
            model = self.model[self.Revision]
        except:
            model = "Unknown"
        return model

    def getMac(self, format=2):
        """Return MAC address as string"""
        if format < 2:
            format = 2
        if format > 4:
            format = 4
        mac_num = hex(getnode()).replace('0x', '').upper()
        mac = '-'.join(mac_num[i : i + format] for i in range(0, 11, format))
        return mac

