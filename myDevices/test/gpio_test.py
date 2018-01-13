import unittest
from myDevices.utils.logger import exception, setDebug, info, debug, error, logToFile, setInfo
from myDevices.devices.digital.gpio import NativeGPIO

class GpioTest(unittest.TestCase):
    def setUp(self):
        self.gpio = NativeGPIO()

    def testGPIO(self):
        pins = []
        for header in self.gpio.MAPPING:
            pins.extend([pin['gpio'] for pin in header['map'] if 'gpio' in pin and 'alt0' not in pin and 'overlay' not in pin])
        for pin in pins:
            info('Testing pin {}'.format(pin))
            function = self.gpio.setFunctionString(pin, 'OUT')
            if function == 'UNKNOWN':
                info('Pin {} function UNKNOWN, skipping'.format(pin))
                continue
            self.assertEqual('OUT', function)
            value = self.gpio.digitalWrite(pin, 1)
            self.assertEqual(value, 1)
            value = self.gpio.digitalWrite(pin, 0)
            self.assertEqual(value, 0)

    def testPinStatus(self):
        pin_status = self.gpio.wildcard()
        info(pin_status)
        self.assertEqual(set(self.gpio.pins + self.gpio.overlay_pins), set(pin_status.keys()))
        for key, value in pin_status.items():
            self.assertCountEqual(value.keys(), ('function', 'value'))
            if key in self.gpio.pins:
                self.assertGreaterEqual(value['value'], 0)
                self.assertLessEqual(value['value'], 1)


if __name__ == '__main__':
    setInfo()
    unittest.main()
