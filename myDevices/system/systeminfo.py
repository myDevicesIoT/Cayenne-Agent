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
            system_info += self.getMemoryInfo()
            system_info += self.getDiskInfo()
            system_info += self.getNetworkInfo()
        except:
            exception('Error retrieving system info')
        return system_info

    def getCpuInfo(self):
        """Get CPU information as a list formatted for Cayenne MQTT

        Returned list example::

            [{
                'channel': 'sys:cpu;load',
                'value': 12.8
            }, {
                'channel': 'sys:cpu;temp',
                'value': 50.843
            }]
        """
        cpu_info = []
        try:
            cayennemqtt.DataChannel.add(cpu_info, cayennemqtt.SYS_CPU, suffix=cayennemqtt.LOAD, value=psutil.cpu_percent(1))
            cayennemqtt.DataChannel.add(cpu_info, cayennemqtt.SYS_CPU, suffix=cayennemqtt.TEMPERATURE, value=CpuInfo.get_cpu_temp())
        except:
            exception('Error getting CPU info')
        return cpu_info

    def getMemoryInfo(self):
        """Get disk usage information as a list formatted for Cayenne MQTT

        Returned list example::

            [{
                'channel': 'sys:ram;capacity',
                'value': 968208384
            }, {
                'channel': 'sys:ram;usage',
                'value': 296620032
            }]
        """
        memory_info = []
        try:
            vmem = psutil.virtual_memory()
            cayennemqtt.DataChannel.add(memory_info, cayennemqtt.SYS_RAM, suffix=cayennemqtt.USAGE, value=vmem.total - vmem.available)
            cayennemqtt.DataChannel.add(memory_info, cayennemqtt.SYS_RAM, suffix=cayennemqtt.CAPACITY, value=vmem.total)
        except:
            exception('Error getting memory info')
        return memory_info

    # def getUptime(self):
    #     """Get system uptime as a dict

    #     Returned dict example::

    #         {
    #             'uptime': 90844.69,
    #             'idle': 391082.64
    #         }
    #     """
    #     info = {}
    #     uptime = 0.0
    #     idle = 0.0
    #     try:
    #         with open('/proc/uptime', 'r') as f_stat:
    #             lines = [line.split(' ') for content in f_stat.readlines() for line in content.split('\n') if line != '']
    #             uptime = float(lines[0][0])
    #             idle = float(lines[0][1])
    #     except:
    #         exception('Error getting uptime')
    #     info['uptime'] = uptime
    #     return info

    def getDiskInfo(self):
        """Get disk usage information as a list formatted for Cayenne MQTT

        Returned list example::

            [{
                'channel': 'sys:storage:/;capacity',
                'value': 13646516224
            }, {
                'channel': 'sys:storage:/;usage',
                'value': 6353821696
            }, {
                'channel': 'sys:storage:/dev;capacity',
                'value': 479383552
            }, {
                'channel': 'sys:storage:/dev;usage',
                'value': 0
            }]
        """
        storage_info = []
        try:
            for partition in psutil.disk_partitions(True):
                try:
                    usage = psutil.disk_usage(partition.mountpoint)
                    if usage.total:
                        cayennemqtt.DataChannel.add(storage_info, cayennemqtt.SYS_STORAGE, partition.mountpoint, cayennemqtt.USAGE, usage.used)
                        cayennemqtt.DataChannel.add(storage_info, cayennemqtt.SYS_STORAGE, partition.mountpoint, cayennemqtt.CAPACITY, usage.total)
                except:
                    pass
        except:
            exception('Error getting disk info')
        return storage_info

    def getNetworkInfo(self):
        """Get network information as a list formatted for Cayenne MQTT

        Returned list example::

            [{
                'channel': 'sys:net;ip'
                'value': '192.168.0.2',
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
            for default_interface in wifi_status.keys():
                cayennemqtt.DataChannel.add(network_info, cayennemqtt.SYS_NET, suffix=cayennemqtt.SSID, value=wifi_status[default_interface]['ssid'])
            addresses = netifaces.ifaddresses(default_interface)
            addr = addresses[netifaces.AF_INET][0]['addr']
            cayennemqtt.DataChannel.add(network_info, cayennemqtt.SYS_NET, suffix=cayennemqtt.IP, value=addr)
        except:
            exception('Error getting network info')
        return network_info
