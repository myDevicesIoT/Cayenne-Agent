import unittest
from myDevices.utils.logger import exception, setDebug, info, debug, error, logToFile, setInfo
from myDevices.devices.digital.gpio import NativeGPIO

class GpioTest(unittest.TestCase):
    def testGPIO(self):
        gpio = NativeGPIO()
        pins = [pin for pin in gpio.MAPPING if type(pin) is int]
        for pin in pins:
            info('Testing pin {}'.format(pin))
            function = gpio.setFunctionString(pin, "OUT")
            if function == "UNKNOWN":
                info('Pin {} function UNKNOWN, skipping'.format(pin))
                continue
            self.assertEqual("OUT", function)
            value = gpio.digitalWrite(pin, 1)
            self.assertEqual(value, 1)
            value = gpio.digitalWrite(pin, 0)
            self.assertEqual(value, 0)


if __name__ == '__main__':
    setInfo()
    unittest.main()
