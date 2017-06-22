from myDevices.wifi.WirelessLib import Wireless
from json import dumps, loads, JSONEncoder, JSONDecoder
from myDevices.utils.logger import exception, info, warn, error, debug
from myDevices.system.services import ServiceManager

class Network():
    def GetNetworkId():
        ip = None
        network = None
        returnValue = {}
        try:
            import netifaces
            gws=netifaces.gateways()
            defaultNet = gws['default'].values()
            for key, val in defaultNet:
               ip = key
               network = val
            command = 'arp -n ' + ip + ' | grep ' + network + ' | awk \'{print $3}\''
            (output, retCode) = ServiceManager.ExecuteCommand(command)
            if int(retCode) > 0:
                return None
            returnValue['Ip'] = ip
            returnValue['Network'] = network
            returnValue['MAC'] = output.strip()
            del output
        except Exception as ex:
            debug('Could not initialize netifaces module: ' + str(ex))
        return returnValue

#{'stats': {'updated': 75, 'noise': 0, 'quality': 67, 'level': 213}, 'Frequency': b'2.412 GHz', 'Access Point': b'B8:55:10:AC:8F:D8', 'Mode': b'Master', 'Key': b'off', 'BitRate': b'54 Mb/s', 'ESSID': b'SRX-WR300WH'}
class WifiEndpoint(object):
    def __init__(self):
        self.Updated = 0
        self.Signal = 0
        self.Quality = 0
        self.Noise = 0
        self.Ssid = None
        self.Frequency = None
        self.BitRate = None
        self.AccessPoint = None
        self.Mode = None
        self.Key = None
    def Update(self, endpoint):
        debug(str(endpoint))
        self.Ssid = endpoint["ESSID"].decode('ascii')
        self.Frequency = endpoint["Frequency"].decode('ascii')
        self.BitRate = endpoint["BitRate"].decode('ascii')
        self.Quality = endpoint["stats"]['quality']
        self.Noise = endpoint["stats"]['noise']
        self.Signal = endpoint["stats"]['level']
        self.Updated = endpoint["stats"]['level']
        self.AccessPoint = endpoint['Access Point'].decode('ascii')
        self.Mode = endpoint['Mode'].decode('ascii')
        self.Key = endpoint['Key'].decode('ascii')

class WifiManager(object):
    def __init__(self): 
        
        try:
            self.wirelessModules = {}
            interfaces = self.Interfaces()    
            for key in interfaces:
                self.wirelessModules[key] = Wireless(key)
        except Exception as ex:
            warn('Could not initialize Wireless module: ' + str(ex))

    def Interfaces(self):
        try:
            interfaces = Wireless.interfaces()
        except:
            interfaces = []
        return interfaces  
        
    def Search(self, interface):
        if interface in self.wirelessModules:
            try:
                from iwlib import iwlist
                endpoints = iwlist.scan(interface)
                return endpoints
            except:
                exception('Wifi search address')
        return None


    def Setup(self, ssid, password, interface):
        if interface in self.wirelessModules:
            status = self.wirelessModules[interface].connect(ssid, password)
            return str(status)
        return False
        
    def GetIpAddress(self, interface):
        ip_addr = None
        try:
            from netifaces import AF_INET, AF_INET6, ifaddresses
            ip_addr = ifaddresses(interface)[AF_INET][0]['addr']
        except:
            exception('GetIpAddress failed')
        
        return ip_addr
    def GetCurretSSID(self, interface):
        if interface in self.wirelessModules:
            return self.wirelessModules[interface].current()
        return None
    def GetDriver(self, interface):
        if interface in self.wirelessModules:
            return self.wirelessModules[interface].driver()
        return None
    def GetPowerStatus(self, interface):
        if interface in self.wirelessModules:
            return self.wirelessModules[interface].power()
        return None
        
        
    def GetStatus(self):
        
        try:
            jsonDictionary = {}
            interfaces = self.Interfaces()
            from netifaces import AF_INET, AF_INET6, ifaddresses
            for i in interfaces:
                #retrieve interface info
                jsonDictionary[str(i)] = {}
                addresses = ifaddresses(i)
                #{17: [{'broadcast': 'ff:ff:ff:ff:ff:ff', 'addr': '40:a5:ef:05:68:cb'}], 2: [{'broadcast': '192.168.1.255', 'netmask': '255.255.255.0', 'addr': '192.168.1.110'}]}
                if AF_INET in addresses:
                    addressesIPv4 = addresses[AF_INET]
                    jsonDictionary[str(i)]["ipv4"] = []
                    for item in addressesIPv4:
                        jsonDictionary[str(i)]["ipv4"].append(item)
                if AF_INET6 in addresses:
                    addressesIPv6 = addresses[AF_INET6]
                    jsonDictionary[str(i)]["ipv6"] = []
                    for item in addressesIPv6:
                        jsonDictionary[str(i)]["ipv6"].append(item)
                ssid = self.GetCurretSSID(i)
                powerStatus = self.GetPowerStatus(i)
                driver = self.GetDriver(i)
                bitRate = ""
                stats = ""
                frequency = ""
                
                if ssid is None:
                    ssid = ""
                else:
                    interfaceEndpoints = self.Search(i)
                    for endpoint in interfaceEndpoints:
                        if endpoint["ESSID"].decode('ascii') == ssid:
                            frequency = endpoint["Frequency"].decode('ascii')
                            bitRate = endpoint["BitRate"].decode('ascii')
                            stats = ToJson(endpoint["stats"])
                    jsonDictionary[str(i)]["ssid"] = ssid
                    jsonDictionary[str(i)]["PowerStatus"] = str(powerStatus)
                    jsonDictionary[str(i)]["Frequency"] = str(frequency)
                    jsonDictionary[str(i)]["BitRate"] = str(bitRate)
                    jsonDictionary[str(i)]["stats"] = str(stats)
        except Exception as ex:
            debug('GetStatus: failed address: ' + str(ex))
        return ToJson(jsonDictionary)

    def GetWirelessNetworks(self): 
        jsonDictionary = {}
        try:
            interfaces = self.Interfaces()
            for i in interfaces:
                endpointsList = self.Search(i)
                wifiEndpoints = []
                for endpoint in endpointsList:
                    wifiEndpoint = WifiEndpoint()
                    wifiEndpoint.Update(endpoint)
                    wifiEndpoints.append(wifiEndpoint)
                jsonDictionary[str(i)] = wifiEndpoints
        except Exception as ex:
            debug('GetWirelessNetworks failed: ' + str(ex))
        return ToJson(jsonDictionary)
        
def ToJson(object):
    returnValue = "{}"
    try:
        import jsonpickle
        returnValue = jsonpickle.encode(object)
    except:
        exception('Json encoding failed')
    return returnValue 

def testWifiManager():
    wifiManager = WifiManager()
    info(ToJson(wifiManager.Interfaces()))
    info(str(wifiManager.GetWirelessNetworks()))
    info(str(wifiManager.GetCurretSSID('wlan0')))
    info(str(wifiManager.GetDriver('wlan0')))
    info(str(wifiManager.GetPowerStatus('wlan0')))
    info(str(wifiManager.GetStatus()))
    
    SetBadNetwork(wifiManager)
    
def SetBadNetwork(wifiManager):
    info('============SETUP TESTS============')
    info('Bad password test: ' + str(wifiManager.Setup('Lizuca&Patrocle', 'badpasswd')))
    info('Bad network test: ' + str(wifiManager.Setup('None', 'badpasswd')))
    info('Success setup test: ' + str(wifiManager.Setup('Lizuca&Patrocle', 'fatadraganufitrista')))

#testWifiManager()
