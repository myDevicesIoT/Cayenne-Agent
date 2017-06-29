import time
import unittest
from myDevices.utils.logger import exception, setDebug, info, debug, error, logToFile, setInfo
from myDevices.devices.digital.gpio import NativeGPIO

class GpioTest(unittest.TestCase):
    def testGPIO(self):
        gpio = NativeGPIO()
        pins = [pin for pin in gpio.MAPPING if type(pin) is int]
        for pin in pins:
            info('Testing pin {}'.format(pin))
            start = time.time()
            function = gpio.setFunctionString(pin, "OUT")
            info('testGPIO setFunctionString, elapsed time {}'.format(time.time() - start))
            if function == "UNKNOWN":
                info('Pin {} function UNKNOWN, skipping'.format(pin))
                continue
            self.assertEqual("OUT", function)
            start = time.time()
            value = gpio.digitalWrite(pin, 1)
            info('testGPIO digitalWrite, elapsed time {}'.format(time.time() - start))
            self.assertEqual(value, 1)
            start = time.time()
            value = gpio.digitalWrite(pin, 0)
            info('testGPIO digitalWrite, elapsed time {}'.format(time.time() - start))
            self.assertEqual(value, 0)


if __name__ == '__main__':
    setInfo()
    unittest.main()
