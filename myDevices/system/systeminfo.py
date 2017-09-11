"""
This module retrieves information about the system, including CPU, RAM, disk and network data.
"""

import psutil
import netifaces
from myDevices.utils.logger import exception
from myDevices.system.cpu import CpuInfo


class SystemInfo():
    """Class to get system CPU, memory, uptime, storage and network info"""

    def getSystemInformation(self):
        """Get a dict containing CPU, memory, uptime, storage and network info"""
        system_info = {}
        try:
            cpu_info = CpuInfo()
            system_info['Cpu'] = cpu_info.get_cpu_info()
            system_info['CpuLoad'] = cpu_info.get_cpu_load()
            system_info['Memory'] = self.getMemoryInfo()
            system_info['Uptime'] = self.getUptime()
            system_info['Storage'] = self.getDiskInfo()
            system_info['Network'] = self.getNetworkInfo()
        except:
            exception('Error retrieving system info')
        return system_info

    def getMemoryInfo(self):
        """Get a dict containing the memory info

        Returned dict example::

            {
                'used': 377036800,
                'total': 903979008,
                'buffers': 129654784,
                'cached': 135168000,
                'processes': 112214016,
                'free': 526942208,
                'swap': {
                    'used': 0,
                    'free': 104853504,
                    'total': 104853504
                }
            }
        """
        memory = {}
        try:
            vmem = psutil.virtual_memory()
            memory['total'] = vmem.total
            memory['free'] = vmem.available
            memory['used'] = memory['total'] - memory['free']
            memory['buffers'] = vmem.buffers
            memory['cached'] = vmem.cached
            memory['processes'] = memory['used']
            swap = psutil.swap_memory()
            memory['swap'] = {}
            memory['swap']['total'] = swap.total
            memory['swap']['free'] = swap.free
            memory['swap']['used'] = swap.used
        except:
            exception('Error getting memory info')
        return memory

    def getUptime(self):
        """Get system uptime as a dict

        Returned dict example::

            {
                'uptime': 90844.69,
                'idle': 391082.64
            }
        """
        info = {}
        uptime = 0.0
        idle = 0.0
        try:
            with open('/proc/uptime', 'r') as f_stat:
                lines = [line.split(' ') for content in f_stat.readlines() for line in content.split('\n') if line != '']
                uptime = float(lines[0][0])
                idle = float(lines[0][1])
        except:
            exception('Error getting uptime')
        info['uptime'] = uptime
        return info

    def getDiskInfo(self):
        """Get disk usage info as a dict

        Returned dict example::

            {
                'list': [{
                    'filesystem': 'ext4',
                    'size': 13646516224,
                    'use': 0.346063,
                    'mount': '/',
                    'device': '/dev/root',
                    'available': 8923963392,
                    'used': 4005748736
                }, {
                    "device": "/dev/mmcblk0p5",
                    "filesystem": "vfat",
                    "mount": "/boot",
                }]
            }
        """
        disk_list = []
        try:
            for partition in psutil.disk_partitions(True):
                disk = {}
                disk['filesystem'] = partition.fstype
                disk['mount'] = partition.mountpoint
                disk['device'] = partition.device
                try:
                    usage = psutil.disk_usage(partition.mountpoint)
                    if usage.total:
                        disk['size'] = usage.total
                        disk['used'] = usage.used
                        disk['available'] = usage.free
                        disk['use'] = round((usage.total - usage.free) / usage.total, 6)
                except:
                    pass
                disk_list.append(disk)
        except:
            exception('Error getting disk info')
        info = {}
        info['list'] = disk_list
        return info

    def getNetworkInfo(self):
        """Get network information as a dict

        Returned dict example::

            {
                "eth0": {
                    "ip": {
                        "address": "192.168.0.25",
                    },
                    "ipv6": [{
                        "address": "2001:db8:3c4d::1a2f:1a2b",
                    }],
                    "mac": "aa:bb:cc:dd:ee:ff",
                },
                "wlan0": {
                    "ipv6": [{
                        "address": "2001:db8:3c4d::1a2f:1a2b",
                    }],
                    "mac": "aa:bb:cc:dd:ee:ff"
                }
            }
        """
        network_info = {}
        try:
            for interface in netifaces.interfaces():
                addresses = netifaces.ifaddresses(interface)
                interface_info = {}
                try:
                    addr = addresses[netifaces.AF_INET][0]['addr']
                    interface_info['ip'] = {}
                    interface_info['ip']['address'] = addr
                except:
                    pass
                try:
                    interface_info['ipv6'] = [{'address': addr['addr'].split('%')[0]} for addr in addresses[netifaces.AF_INET6]]
                except:
                    pass
                try:
                    interface_info['mac'] = addresses[netifaces.AF_LINK][0]['addr']
                except:
                    pass
                if interface_info:
                    network_info[interface] = interface_info
        except:
            exception('Error getting network info')
        info = {}
        info['list'] = network_info
        return info
