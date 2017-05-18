import wifi
from wifi import Cell, Scheme
import json
from json import dumps, loads, JSONEncoder, JSONDecoder
import pickle
import jsonpickle

class WifiEndpoint(object):
    def __init__(self):
        self.ssid = None
        self.signal = None
        self.quality = None
        self.frequency = None
        self.bitrates = None
        self.encrypted = None
        self.channel = None
        self.address = None
        self.mode = None

class WifiSetup(object):
    def __init__(self, interface):
        self.interface = interface

    def Search(self):
        cells = Cell.all('wlan0')
        self.endpoints = list(cells)
        serializableEndpoints = []
        for i in self.endpoints:
            wifiEndpoint = WifiEndpoint()
            wifiEndpoint.ssid = i.ssid
            wifiEndpoint.signal = i.signal
            wifiEndpoint.quality = i.quality
            wifiEndpoint.frequency = i.frequency
            wifiEndpoint.bitrates = i.bitrates
            wifiEndpoint.encrypted = i.encrypted
            wifiEndpoint.channel = i.channel
            wifiEndpoint.address = i.address
            wifiEndpoint.mode = i.mode
            serializableEndpoints.append(wifiEndpoint)
            #print (i.ssid, i.signal, i.quality, i.frequency)            
        schemes = Scheme.all()
        #print(jsonpickle.encode(schemes))
        return jsonpickle.encode(serializableEndpoints)


    def Setup(self, ssid, password):
        cell = None
        for i in self.endpoints:
            if i.ssid == ssid:
                cell = i
                break
        if cell is None:
            cell = Cell.from_string(ssid)
            if cell is None:
                #print('failure')
                return False
        scheme = Scheme.for_cell(self.interface, ssid, cell, password)
        scheme.save()
        scheme.activate()
        scheme.autoreconnect()
        #print('success')
        return True
        
        
#wifi_setup = WifiSetup('wlan0')

#str = wifi_setup.Search()

#print(str)

#val = wifi_setup.Setup('Lizuca&Patrocle', 'fatadraganufitrista')




