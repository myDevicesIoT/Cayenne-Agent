import unittest
from ctypes import CDLL, c_char_p
from myDevices.os.systeminfo import SystemInfo
from json import loads
from myDevices.os.services import ProcessManager
from myDevices.os.cpu import CpuInfo
from time import sleep
from myDevices.os.hardware import Hardware
from myDevices.utils.logger import setInfo

from psutil import cpu_times, virtual_memory
from myDevices.sensors import sensors

class SystemInfoTest(unittest.TestCase):
    def setUp(self):
        setInfo()
        libSystemInformation=CDLL("/etc/myDevices/libs/libSystemInformation.so")
        if libSystemInformation:
            libSystemInformation.GetSystemInformation.restype=c_char_p
            currentSystemInfo = libSystemInformation.GetSystemInformation().decode('utf-8')
            libSystemInformation.FreeSystemInformation()
        self.c_library_info = loads(currentSystemInfo)

    def testSystemInfo(self):
        system_info = SystemInfo()
        info = loads(system_info.getSystemInformation())
        # print('info type {}, {}'.format(type(info), info))
        # info = loads(info)
        print(info.keys())
        # client = sensors.SensorsClient()
        # sys_info = client.SystemInformation()
        # print(sys_info['CpuLoad'])
        # client.StopMonitoring()
        cpu_info = info['Cpu']
        print(cpu_info)
        print(cpu_times())
        self.assertEqual(set(cpu_info.keys()), set(('loadavg', 'usage', 'temperature')))
        self.assertEqual(set(cpu_info['loadavg'].keys()), set(('one', 'five', 'ten')))
        self.assertEqual(set(cpu_info['usage'].keys()), set(('user', 'nice', 'system', 'idle', 'iowait', 'irq', 'softirq', 'total', 'busy')))
        memory_info = info['Memory']
        print(memory_info)
        self.assertEqual(set(memory_info.keys()), set(('total', 'free', 'used', 'buffers', 'cached', 'processes', 'swap')))
        self.assertEqual(set(memory_info['swap'].keys()), set(('total', 'free', 'used')))
        print(info['Uptime'])
        for key in info['Storage'].keys():
            print('{} : {}'.format(key, info['Storage'][key].keys()))
        print(info['Storage'].keys())
        print(info['Network'].keys())

        # print(virtual_memory())

    # def testSystemInfo(self):
    #     hardware = Hardware()
    #     print(hardware.getManufacturer())
    #     print(hardware.getModel())
    #     print(hardware.getMac())
    #     info = loads(getSystemInformation())
    #     print(info['Cpu'])
    #     cpuLoad = GetCpuLoad()
    #     print(cpuLoad.getcpuload())
    #     processManager = ProcessManager()
    #     data = {}
    #     processManager.RefreshProcessManager()
    #     data['VisibleMemory'] = processManager.VisibleMemory
    #     data['AvailableMemory'] =  processManager.AvailableMemory
    #     data['AverageProcessorUsage'] = processManager.AverageProcessorUsage
    #     data['PeakProcessorUsage'] = processManager.PeakProcessorUsage
    #     data['AverageMemoryUsage'] = processManager.AverageMemoryUsage
    #     data['PeakMemoryUsage'] = processManager.AverageMemoryUsage
    #     data['PercentProcessorTime'] = processManager.PercentProcessorTime
    #     print(data)
    #     for i in range(10):
    #         sleep(5)
    #         print(cpuLoad.getcpuload())
        
        
if __name__ == '__main__':
    unittest.main()