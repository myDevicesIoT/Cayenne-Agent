#!/usr/bin/python 
# -*- coding: utf-8 -*-

'''
Created on 04.12.2014

@author: plagtag
'''
from time import sleep


class GetCpuLoad(object):
    '''
    classdocs
    '''


    def __init__(self, percentage=True, sleeptime = 1):
        '''
        @parent class: GetCpuLoad
        @date: 04.12.2014
        @author: plagtag
        @info: 
        @param:
        @return: CPU load in percentage
        '''
        self.percentage = percentage
        self.cpustat = '/proc/stat'
        self.sep = ' '
        self.sleeptime = sleeptime

    def getcputime(self):
        '''
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
        '''
        cpu_infos = {} #collect here the information
        with open(self.cpustat,'r') as f_stat:
            lines = [line.split(self.sep) for content in f_stat.readlines() for line in content.split('\n') if line.startswith('cpu')]

            #compute for every cpu
            for cpu_line in lines:
                if '' in cpu_line: cpu_line.remove('')#remove empty elements
                cpu_line = [cpu_line[0]]+[float(i) for i in cpu_line[1:]]#type casting
                cpu_id,user,nice,system,idle,iowait,irq,softrig,steal,guest,guest_nice = cpu_line

                Idle=idle+iowait
                NonIdle=user+nice+system+irq+softrig+steal
                busy = user + nice + system + irq + softrig

                Total=Idle+NonIdle
                #update dictionionary
                cpu_infos.update({cpu_id:{'total':Total,'idle':Idle, 'irq': irq, 'softirq': softrig, 'system': system, 'user': user, 'nice': nice, 'busy': busy,'iowait': iowait }})
            return cpu_infos

    def getcpuload(self):
        '''
        CPU_Percentage=((Total-PrevTotal)-(Idle-PrevIdle))/(Total-PrevTotal)
        '''
        start = self.getcputime()
        #wait a second
        sleep(self.sleeptime)
        stop = self.getcputime()
        cpu_load = {}
        for cpu in start:
            Total = stop[cpu]['total']
            PrevTotal = start[cpu]['total']
            Idle = stop[cpu]['idle']
            PrevIdle = start[cpu]['idle']
            CPU_Percentage=((Total-PrevTotal)-(Idle-PrevIdle))/(Total-PrevTotal)*100
            CPU_Percentage=float('{0:.1f}'.format(CPU_Percentage))
            cpu_load.update({cpu: CPU_Percentage})
            del CPU_Percentage
            CPU_Percentage = None
        start = None
        stop = None
        return cpu_load
    def build_info(self):
        info = {}
        info['temperature'] = self.get_cpu_temp()
        info["loadavg"] = self.get_loadavg()
        info["usage"] = self.getcputime()['cpu']
        return info
    def get_cpu_temp(self):
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
    def get_loadavg(self):
        info = {}
        file = "/proc/loadavg"
        one     = 0
        five    = 0
        ten     = 0
        try:
            with open(file, 'r') as f_stat:
                content = f_stat.read().strip().split(' ')
                one = content[0]
                five = content[1]
                ten = content[2]
        except Exception as e:
            print('Cpu Loadavg exception:' + str(e))
        info['one']     = one
        info['five']    = five
        info['ten']     = ten
        return info

# gpl = GetCpuLoad()
# print(gpl.build_info())