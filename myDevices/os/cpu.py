#!/usr/bin/python 
# -*- coding: utf-8 -*-

"""
Created on 04.12.2014

@author: plagtag
"""
from time import sleep


class CpuInfo(object):
    """Class for retrieving CPU info"""

    def __init__(self):
        """Initialize the CpuInfo class"""
        self.cpustat = '/proc/stat'
        self.sep = ' '

    def get_cpu_time(self):
        """Return dict with CPU usage info for each CPU as well as overall CPU usage

        This is calculated from info in the /proc/stat file.
        http://stackoverflow.com/questions/23367857/accurate-calculation-of-cpu-usage-given-in-percentage-in-linux
        read in cpu information from file
        The meanings of the columns are as follows, from left to right:
            0cpuid: number of cpu
            1user: normal processes executing in user mode
            2nice: niced processes executing in user mode
            3system: processes executing in kernel mode
            4idle: twiddling thumbs
            5iowait: waiting for I/O to complete
            6irq: servicing interrupts
            7softirq: servicing softirqs

        #the formulas from htop 
             user    nice   system  idle      iowait irq   softirq  steal  guest  guest_nice
        cpu  74608   2520   24433   1117073   6176   4054  0        0      0      0


        Idle=idle+iowait
        NonIdle=user+nice+system+irq+softirq+steal
        Total=Idle+NonIdle # first line of file for all cpus

        CPU_Percentage=((Total-PrevTotal)-(Idle-PrevIdle))/(Total-PrevTotal)
        """
        cpu_infos = {} #collect here the information
        with open(self.cpustat,'r') as f_stat:
            lines = [line.split(self.sep) for content in f_stat.readlines() for line in content.split('\n') if line.startswith('cpu')]

            #compute for every cpu
            for cpu_line in lines:
                if '' in cpu_line: cpu_line.remove('') #remove empty elements
                cpu_line = [cpu_line[0]]+[int(i) for i in cpu_line[1:]] #type casting
                cpu_id,user,nice,system,idle,iowait,irq,softrig,steal,guest,guest_nice = cpu_line

                Idle=idle+iowait
                NonIdle=user+nice+system+irq+softrig+steal
                busy = user + nice + system + irq + softrig

                Total=Idle+NonIdle
                #update dictionary
                cpu_infos.update({cpu_id:{'total':Total,'idle':Idle, 'irq': irq, 'softirq': softrig, 'system': system, 'user': user, 'nice': nice, 'busy': busy,'iowait': iowait }})
            return cpu_infos

    def get_cpu_load(self, sleeptime = 1):
        """Return CPU load

        :param sleeptime: time interval in seconds to wait when calculating CPU usage
        :returns: dict containing CPU load for each CPU, and overall load, as a percentage
        """
        start = self.get_cpu_time()
        sleep(sleeptime)
        stop = self.get_cpu_time()
        cpu_load = {}
        for cpu in start:
            Total = float(stop[cpu]['total'])
            PrevTotal = float(start[cpu]['total'])
            Idle = float(stop[cpu]['idle'])
            PrevIdle = float(start[cpu]['idle'])
            CPU_Percentage=((Total-PrevTotal)-(Idle-PrevIdle))/(Total-PrevTotal)*100
            CPU_Percentage=float('{0:.1f}'.format(CPU_Percentage))
            cpu_load.update({cpu: CPU_Percentage})
            del CPU_Percentage
            CPU_Percentage = None
        start = None
        stop = None
        return cpu_load

    def build_info(self):
        """Return CPU temperature, load average and usage info as a dict"""
        info = {}
        info['temperature'] = self.get_cpu_temp()
        info["loadavg"] = self.get_load_avg()
        info["usage"] = self.get_cpu_time()['cpu']
        return info

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

