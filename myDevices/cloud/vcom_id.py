#VCOM MAC ID V03 COMPUTING
from uuid import getnode
from myDevices.utils.logger import exception, info, warn, error, debug

class VCOMMacId:
    def __init__(self, config):
        self.cpuSerial = ""
        self.mac_address = self.get_mac(4)
        self.cpuSerial = "0000000000000000"
        self.revision  = "0"
        try:
            f = open('/proc/cpuinfo','r')
            for line in f:
                splitLine =  line.split(':')
                if len(splitLine) < 2:
                    continue
                key = splitLine[0].strip()
                value = splitLine[1].strip()
                if key=='Serial':
                    self.cpuSerial = value
                if key=='CPU architecture':
                    self.cpuArchitecture = value
                if key=='CPU implementer':
                    self.cpuImplementer = value
                if key=='CPU revision':
                    self.cpuRevision = value
                if key=='model name':
                    self.modelName = value
                if key=='Features':
                    self.features = value
                if key=='Revision':
                    self.Revision = value
            f.close()
        except:
            exception ("VCOMMacId Unexpected error")    
            self.cpuSerial = "0000000000000000"
        self.model = {}
        self.model["Beta"] = "Model B (Beta)";
        self.model["000d"] = self.model["000e"] = self.model["000f"] = self.model["0002"] = self.model["0003"] = self.model["0004"] = self.model["0005"] = self.model["0006"] = "Model B";
        self.model["0007"] = self.model["0008"] = self.model["0009"] = "Model A";
        self.model["0010"] = "Model B+";
        self.model["0011"] = "Compute Module";
        self.model["0012"] = "Model A+";
        self.model["0013"] = "Model B+";
        self.model["a01041"] = "Pi 2 Model B";
        self.model["a21041"] = "Pi 2 Model B";
        self.model["900092"] = "Zero"
        self.model["a22082"]=self.model["a02082"] = "Pi 3 Model B"
        self.Id = None
        self.config = config
        try:
            self.Id = self.config.get('Agent','Id')
            info('Loaded machine id: ' + self.Id)
            if self.Id == '':
                self.Id = None
        except:
            pass

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
    def getMachineIdNoMac(self):
        serialCompute =  self.cpuRevision + self.cpuArchitecture + self.cpuImplementer
        hexCompute = "".join("{:02x}".format(ord(c)) for c in serialCompute)
        #machineId = 'V03-' + self.cpuSerial[8:16] + '-'+ hexCompute[:4] + '-' + hexCompute[5:9] + '-' + self.Revision[:4] + '-' + self.cpuSerial[0:4] + '-' + self.cpuSerial[4:8]
        machineId = hexCompute + self.Revision + self.cpuSerial[0:8]
        machineId = 'V03-' + self.cpuSerial[8:16] + '-' +'-'.join(machineId[i : i + 4] for i in range(0, 20, 4))
        #debug("MachineId: "+str(machineId.upper()))
        return str(machineId.upper())
    def getMachineId(self):
        if self.Id is None:
            self.Id = self.getMachineIdMac()
            self.config.set('Agent', 'Id', self.Id);
            info('Generated new machine id: ' + self.Id)
        return self.Id
    def getMachineIdMac(self):   
        serialCompute =  self.cpuRevision + self.cpuArchitecture + self.cpuImplementer
        hexCompute = "".join("{:02x}".format(ord(c)) for c in serialCompute)
        #machineId = 'V03-' + self.cpuSerial[8:16] + '-'+ hexCompute[:4] + '-' + hexCompute[5:9] + '-' + self.Revision[:4] + '-' + self.mac_address
        machineId = hexCompute + self.Revision
        machineId = 'V03-' + self.cpuSerial[8:16] + '-' +'-'.join(machineId[i : i + 4] for i in range(0, 12, 4)) + '-' + self.mac_address
        #debug("MachineId: "+str(machineId.upper()))
        return str(machineId.upper())
    def getRegistrationId(self, hostname):
        #WIN7ULTVM-PC, innotek GmbH, VirtualBox=V03-A5A5797C-904F-4C49-990E-AC69-C911-EF51=V02-0-0-2A5C-B0ED-E457-75414-0-0
        retVal = hostname + ',=' + self.getMachineId()
        return retVal
    def getMachineIdV02(self):
        #V02-0-0-2A5C-B0ED-E457-75414-0-0
        serialCompute =  self.cpuRevision + self.cpuArchitecture + self.cpuImplementer
        hexCompute = "".join("{:02x}".format(ord(c)) for c in serialCompute)
        machineId = 'V02-0-0-' + self.cpuSerial[8:11] + '-'+ hexCompute[:4] + '-' + self.Revision[:4] + hexCompute[5:10] + '-0-0'
        #debug("MachineId: "+str(machineId.upper()))
        return str(machineId.upper())
    def get_mac(self, format):
        if format < 2:
            format = 2
        if format > 4:
            format = 4
        mac_num = hex(getnode()).replace('0x', '').upper()
        mac = '-'.join(mac_num[i : i + format] for i in range(0, 11, format))
        #debug("Mac:" + mac)
        return mac
#vid=VCOMMacId()
#print(vid.getMachineId())