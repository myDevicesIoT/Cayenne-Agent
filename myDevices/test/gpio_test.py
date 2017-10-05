import unittest
from myDevices.utils.logger import exception, setDebug, info, debug, error, logToFile, setInfo
from myDevices.devices.digital.gpio import NativeGPIO

class GpioTest(unittest.TestCase):
    def setUp(self):
        self.gpio = NativeGPIO()

    def testGPIO(self):
        for pin in self.gpio.pins:
            info('Testing pin {}'.format(pin))
            function = self.gpio.setFunctionString(pin, "OUT")
            if function == "UNKNOWN":
                info('Pin {} function UNKNOWN, skipping'.format(pin))
                continue
            self.assertEqual("OUT", function)
            value = self.gpio.digitalWrite(pin, 1)
            self.assertEqual(value, 1)
            value = self.gpio.digitalWrite(pin, 0)
            self.assertEqual(value, 0)

    def testPinStatus(self):
        pin_status = self.gpio.wildcard()
        # print(pin_status)
        self.assertEqual(set(self.gpio.pins), set(pin_status.keys()))
        for pin in pin_status.values():
            self.assertCountEqual(pin.keys(), ('function', 'value'))
            self.assertGreaterEqual(pin['value'], 0)
            self.assertLessEqual(pin['value'], 1)


if __name__ == '__main__':
    setInfo()
    unittest.main()
