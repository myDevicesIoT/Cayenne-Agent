import psutil
import os
from glob import glob
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
        thermal_dirs = glob('/sys/class/thermal/thermal_zone*')
        thermal_dirs.sort()
        temp = 0.0
        try:
            for thermal_dir in thermal_dirs:
                try:
                    thermal_type = ''
                    with open(thermal_dir + '/type', 'r') as type_file:
                        thermal_type = type_file.read().strip()
                    if thermal_type != 'gpu_thermal':
                        with open(thermal_dir + '/temp', 'r') as temp_file:
                            content = int(temp_file.read().strip())
                            temp = content / 1000.0
                            break
                except:
                    pass
        except Exception:
            exception('Error getting CPU temperature')
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
        except Exception:
            exception('Error getting CPU load average')
        info['one']     = one
        info['five']    = five
        info['ten']     = ten
        return info

