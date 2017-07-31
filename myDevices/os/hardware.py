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
        return self.manufacturer

    def getModel(self):
        return self.model

    def getMac(self, format=2):
        if format < 2:
            format = 2
        if format > 4:
            format = 4
        mac_num = hex(getnode()).replace('0x', '').upper()
        mac = '-'.join(mac_num[i : i + format] for i in range(0, 11, format))
        #debug("Mac:" + mac)
        return mac
