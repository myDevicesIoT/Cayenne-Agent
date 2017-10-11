import unittest
from myDevices.system.systeminfo import SystemInfo
from myDevices.utils.logger import setInfo, info


class SystemInfoTest(unittest.TestCase):
    def setUp(self):
        # setInfo()
        system_info = SystemInfo()
        self.info = {item['channel']:item['value'] for item in system_info.getSystemInformation()}
        info(self.info)

    def testSystemInfo(self):
        self.assertIn('sys:cpu;load', self.info)
        self.assertIn('sys:cpu;temp', self.info)
        self.assertIn('sys:ram;usage', self.info)
        self.assertIn('sys:ram;capacity', self.info)
        self.assertIn('sys:storage:/;usage', self.info)
        self.assertIn('sys:storage:/;capacity', self.info)
        self.assertIn('sys:eth:eth0;ip', self.info)
        self.assertIn('sys:wifi:wlan0;ip', self.info)
        self.assertIn('sys:wifi:wlan0;ssid', self.info)
        
        
if __name__ == '__main__':
    unittest.main()