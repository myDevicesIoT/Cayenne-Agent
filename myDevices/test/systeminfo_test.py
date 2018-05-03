import unittest
from myDevices.system.systeminfo import SystemInfo
from myDevices.utils.logger import setInfo, info


class SystemInfoTest(unittest.TestCase):
    def setUp(self):
        setInfo()
        system_info = SystemInfo()
        self.info = {item['channel']:item for item in system_info.getSystemInformation()}
        info(self.info)

    def testSystemInfo(self):
        self.assertIn('sys:cpu;load', self.info)
        self.assertEqual(self.info['sys:cpu;load']['type'], 'cpuload')
        self.assertEqual(self.info['sys:cpu;load']['unit'], 'p')
        self.assertIn('sys:cpu;temp', self.info)
        self.assertEqual(self.info['sys:cpu;temp']['type'], 'temp')
        self.assertEqual(self.info['sys:cpu;temp']['unit'], 'c')
        self.assertIn('sys:ram;usage', self.info)
        self.assertEqual(self.info['sys:ram;usage']['type'], 'memory')
        self.assertEqual(self.info['sys:ram;usage']['unit'], 'b')
        self.assertIn('sys:storage:/;usage', self.info)
        self.assertEqual(self.info['sys:storage:/;usage']['type'], 'memory')
        self.assertEqual(self.info['sys:storage:/;usage']['unit'], 'b')
        self.assertIn('sys:net;ip', self.info)
        # self.assertIn('sys:net;ssid', self.info)
        
        
if __name__ == '__main__':
    unittest.main()