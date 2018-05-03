"""
This module retrieves information about the system, including CPU, RAM, disk and network data.
"""

import psutil
import netifaces
from myDevices.utils.logger import exception
from myDevices.system.cpu import CpuInfo
from myDevices.cloud import cayennemqtt
from myDevices.wifi import WifiManager

class SystemInfo():
    """Class to get system CPU, memory, uptime, storage and network info"""

    def getSystemInformation(self):
        """Get a dict containing CPU, memory, uptime, storage and network info"""
        system_info = []
        try:
            system_info += self.getCpuInfo()
            system_info += self.getMemoryInfo((cayennemqtt.USAGE,))
            system_info += self.getDiskInfo((cayennemqtt.USAGE,))
            system_info += self.getNetworkInfo()
        except:
            exception('Error retrieving system info')
        return system_info

    def getCpuInfo(self):
        """Get CPU information as a list formatted for Cayenne MQTT

        Returned list example::

            [{
                'channel': 'sys:cpu;load',
                'value': 12.8,
                'type': 'cpuload',
                'unit': 'p'
            }, {
                'channel': 'sys:cpu;temp',
                'value': 50.843,
                'type': 'temp',
                'unit': 'c'                
            }]
        """
        cpu_info = []
        try:
            cayennemqtt.DataChannel.add(cpu_info, cayennemqtt.SYS_CPU, suffix=cayennemqtt.LOAD, value=psutil.cpu_percent(1), type='cpuload', unit='p')
            cayennemqtt.DataChannel.add(cpu_info, cayennemqtt.SYS_CPU, suffix=cayennemqtt.TEMPERATURE, value=CpuInfo.get_cpu_temp(), type='temp', unit='c')
        except:
            exception('Error getting CPU info')
        return cpu_info

    def getMemoryInfo(self, types):
        """Get memory information as a list formatted for Cayenne MQTT.

        Args:
            types: Iterable containing types of memory info to retrieve matching cayennemqtt suffixes, e.g. cayennemqtt.USAGE

        Returned list example::

            [{
                'channel': 'sys:ram;capacity',
                'value': 968208384,
                'type': 'memory',                
                'type': 'b'
            }, {
                'channel': 'sys:ram;usage',
                'value': 296620032,
                'type': 'memory',                
                'type': 'b'               
            }]
        """
        memory_info = []
        try:
            vmem = psutil.virtual_memory()
            if not types or cayennemqtt.USAGE in types:
                cayennemqtt.DataChannel.add(memory_info, cayennemqtt.SYS_RAM, suffix=cayennemqtt.USAGE, value=vmem.total - vmem.available, type='memory', unit='b')
            if not types or cayennemqtt.CAPACITY in types:
                cayennemqtt.DataChannel.add(memory_info, cayennemqtt.SYS_RAM, suffix=cayennemqtt.CAPACITY, value=vmem.total, type='memory', unit='b')
        except:
            exception('Error getting memory info')
        return memory_info

    def getDiskInfo(self, types):
        """Get disk information as a list formatted for Cayenne MQTT

        Args:
            types: Iterable containing types of disk info to retrieve matching cayennemqtt suffixes, e.g. cayennemqtt.USAGE

        Returned list example::

            [{
                'channel': 'sys:storage:/;capacity',
                'value': 13646516224,
                'type': 'memory',                
                'type': 'b'
            }, {
                'channel': 'sys:storage:/;usage',
                'value': 6353821696,
                'type': 'memory',                
                'type': 'b'
            }, {
                'channel': 'sys:storage:/mnt/cdrom;capacity',
                'value': 479383552,
                'type': 'memory',                
                'type': 'b'
            }, {
                'channel': 'sys:storage:/mnt/cdrom;usage',
                'value': 0,
                'type': 'memory',                
                'type': 'b'
            }]
        """
        storage_info = []
        try:
            for partition in psutil.disk_partitions(True):
                try:
                    if partition.mountpoint == '/':
                        usage = psutil.disk_usage(partition.mountpoint)
                        if usage.total:
                            if not types or cayennemqtt.USAGE in types:
                                cayennemqtt.DataChannel.add(storage_info, cayennemqtt.SYS_STORAGE, partition.mountpoint, cayennemqtt.USAGE, usage.used, type='memory', unit='b')
                            if not types or cayennemqtt.CAPACITY in types:
                                cayennemqtt.DataChannel.add(storage_info, cayennemqtt.SYS_STORAGE, partition.mountpoint, cayennemqtt.CAPACITY, usage.total, type='memory', unit='b')
                except:
                    pass
        except:
            exception('Error getting disk info')
        return storage_info

    def getNetworkInfo(self):
        """Get network information as a list formatted for Cayenne MQTT

        Returned list example::

            [{
                'channel': 'sys:net;ip',
                'value': '192.168.0.2'
            }, {
                'channel': 'sys:net;ssid',
                'value': 'myWifi'
            }]
        """
        network_info = []
        try:
            wifi_manager = WifiManager.WifiManager()
            wifi_status = wifi_manager.GetStatus()
            default_interface = netifaces.gateways()['default'][netifaces.AF_INET][1]
            try:
                cayennemqtt.DataChannel.add(network_info, cayennemqtt.SYS_NET, suffix=cayennemqtt.SSID, value=wifi_status[default_interface]['ssid'])
            except:
                pass
            addresses = netifaces.ifaddresses(default_interface)
            addr = addresses[netifaces.AF_INET][0]['addr']
            cayennemqtt.DataChannel.add(network_info, cayennemqtt.SYS_NET, suffix=cayennemqtt.IP, value=addr)
        except:
            exception('Error getting network info')
        return network_info
