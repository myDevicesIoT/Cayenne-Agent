import unittest
from myDevices.system.systeminfo import SystemInfo
from myDevices.utils.logger import setInfo, info


class SystemInfoTest(unittest.TestCase):
    def setUp(self):
        # setInfo()
        system_info = SystemInfo()
        self.info = system_info.getSystemInformation()

    def testCpuInfo(self):
        cpu_info = self.info['Cpu']
        info(cpu_info)
        self.assertEqual(set(cpu_info.keys()), set(('loadavg', 'usage', 'temperature')))
        self.assertEqual(set(cpu_info['loadavg'].keys()), set(('one', 'five', 'ten')))
        self.assertGreaterEqual(set(cpu_info['usage'].keys()), set(('user', 'nice', 'system', 'idle', 'iowait', 'irq', 'softirq', 'total')))

    def testCpuLoadInfo(self):
        cpu_load_info = self.info['CpuLoad']
        info(cpu_load_info)
        self.assertGreaterEqual(set(cpu_load_info.keys()), set(('cpu',)))

    def testMemoryInfo(self):
        memory_info = self.info['Memory']
        info(memory_info)
        self.assertEqual(set(memory_info.keys()), set(('total', 'free', 'used', 'buffers', 'cached', 'processes', 'swap')))
        self.assertEqual(set(memory_info['swap'].keys()), set(('total', 'free', 'used')))

    def testUptimeInfo(self):
        uptime_info = self.info['Uptime']
        info(uptime_info)
        self.assertEqual(set(uptime_info.keys()), set(('uptime',)))

    def testStorageInfo(self):
        storage_info = self.info['Storage']
        info(storage_info)
        self.assertEqual(set(storage_info.keys()), set(('list',)))
        for item in storage_info['list']:
            self.assertLessEqual(set(('device', 'filesystem', 'mount')), set(item.keys()))

    def testNetworkInfo(self):
        network_info = self.info['Network']
        info(network_info)
        self.assertGreaterEqual(set(network_info.keys()), set(('list',)))
        for key, value in network_info['list'].items():
            self.assertTrue(value)
            self.assertLessEqual(set(value.keys()), set(('ip', 'ipv6', 'mac')))
        self.assertIsNotNone(network_info['list']['eth0']['ip']['address'])
        
        
if __name__ == '__main__':
    unittest.main()