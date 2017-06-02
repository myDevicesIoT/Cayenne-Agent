import psutil
import os
from time import sleep
from myDevices.utils.logger import exception

class CpuInfo(object):
    """Class for retrieving CPU info"""

    def get_cpu_info(self):
        """Return CPU temperature, load average and usage info as a dict"""
        info = {}
        info['temperature'] = self.get_cpu_temp()
        info["loadavg"] = self.get_load_avg()
        info["usage"] = self.get_cpu_usage()
        return info

    def get_cpu_usage(self):
        """Return dict with overall CPU usage"""
        usage = {}
        try:
            fields = ('user', 'system', 'idle', 'nice', 'iowait', 'irq', 'softirq', 'steal')
            usage = {key: value for key, value in psutil.cpu_times()._asdict().items() if key in fields}
            usage['total'] = round(sum(usage.values()), 2)
        except:
            exception('Error getting CPU usage info')
        return usage

    def get_cpu_load(self, interval = 1):
        """Return CPU load

        :param interval: time interval in seconds to wait when calculating CPU usage
        :returns: dict containing overall CPU load, as a percentage
        """
        cpu_load = {}
        try:
            cpu_load['cpu'] = psutil.cpu_percent(interval)
        except:
            exception('Error getting CPU load info')
        return cpu_load

    def get_cpu_temp(self):
        """Get CPU temperature"""
        info = {}
        file = "/sys/class/thermal/thermal_zone0/temp"
        temp = 0.0
        try:
            with open(file, 'r') as f_stat:
                content = int(f_stat.read().strip())
                temp = content/1000.0
        except Exception as e:
            print('Temp exception:' + str(e))
        return temp

    def get_load_avg(self):
        """Get CPU average load for the last one, five, and 10 minute periods"""
        info = {}
        file = "/proc/loadavg"
        one     = 0
        five    = 0
        ten     = 0
        try:
            with open(file, 'r') as f_stat:
                content = f_stat.read().strip().split(' ')
                one = float(content[0])
                five = float(content[1])
                ten = float(content[2])
        except Exception as e:
            print('Cpu Loadavg exception:' + str(e))
        info['one']     = one
        info['five']    = five
        info['ten']     = ten
        return info

