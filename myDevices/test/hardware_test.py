import unittest
from myDevices.utils.logger import setInfo, info
from myDevices.system.hardware import Hardware, BOARD_REVISION, CPU_REVISION, CPU_HARDWARE

class HarwareTest(unittest.TestCase):
    def setUp(self):
        setInfo()
        self.hardware = Hardware()

    def testGetManufacturer(self):
        manufacturer = self.hardware.getManufacturer()
        info(manufacturer)
        self.assertNotEqual(manufacturer, '')

    def testGetModel(self):
        model = self.hardware.getModel()
        info(model)
        self.assertNotEqual(model, 'Unknown')

    def testGetMac(self):
        mac = self.hardware.getMac()
        info(mac)
        self.assertRegex(mac, '^([0-9a-fA-F]{2}[:-]){5}([0-9a-fA-F]{2})$')

    def testBoardRevision(self):
        info(BOARD_REVISION)
        self.assertGreaterEqual(BOARD_REVISION, 0)
        self.assertLessEqual(BOARD_REVISION, 3)

    def testCpuRevision(self):
        info(CPU_REVISION)
        self.assertNotEqual(CPU_REVISION, '0')

    def testCpuHardware(self):
        info(CPU_HARDWARE)
        self.assertNotEqual(CPU_HARDWARE, '')

    def testDeviceVerification(self):
        device_checks = (self.hardware.isRaspberryPi(), self.hardware.isTinkerBoard(), self.hardware.isBeagleBone())
        self.assertEqual(device_checks.count(True), 1)

if __name__ == '__main__':
    unittest.main()