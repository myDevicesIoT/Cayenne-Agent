from uuid import getnode
from myDevices.utils.logger import exception, info, warn, error, debug

class Hardware:
    def __init__(self):
        self.Revision  = "0"
        try:
            with open('/proc/cpuinfo','r') as f:
                for line in f:
                    splitLine =  line.split(':')
                    if len(splitLine) < 2:
                        continue
                    key = splitLine[0].strip()
                    value = splitLine[1].strip()
                    if key=='Revision':
                        self.Revision = value
        except:
            exception ("Error reading cpuinfo")    
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
        self.model["a22082"]=self.model["a02082"] = "Pi 3 Model B"

    def getManufacturer(self):
        if self.Revision in ["a01041","900092", "a02082", "0012", "0011", "0010", "000e", "0008", "0004"]:
            return "Sony, UK" 
        if self.Revision == "a21041":
            return "Embest, China"
        if self.Revision in ["0005", "0009", "000f"]:
            return "Qisda"
        if self.Revision in ["0006", "0007", "000d"]:
            return "Egoman"
        return "Element14/Premier Farnell"

    def getModel(self):
        try:
            model = self.model[self.Revision]
        except:
            model = "Unknown"
        return model

    def getMac(self, format=2):
        if format < 2:
            format = 2
        if format > 4:
            format = 4
        mac_num = hex(getnode()).replace('0x', '').upper()
        mac = '-'.join(mac_num[i : i + format] for i in range(0, 11, format))
        #debug("Mac:" + mac)
        return mac
