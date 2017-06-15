import unittest
import os
import grp
from myDevices.sensors import sensors
from myDevices.devices import manager
from myDevices.utils.config import Config
from myDevices.utils import types
from myDevices.utils.logger import exception, setDebug, info, debug, error, logToFile, setInfo
from myDevices.devices.bus import checkAllBus, BUSLIST
from myDevices.devices.digital.gpio import NativeGPIO as GPIO
from myDevices.devices import instance
from time import sleep
from json import loads, dumps

class SensorsClientTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = sensors.SensorsClient()

    @classmethod
    def tearDownClass(cls):
        cls.client.StopMonitoring()
        del cls.client
        del GPIO.instance

    def testBusInfo(self):
        bus = SensorsClientTest.client.BusInfo()
        # # Compare our GPIO function values with the ones from RPi.GPIO library
        # import RPi.GPIO
        # RPi.GPIO.setmode(RPi.GPIO.BCM)
        # port_use = {0:"GPIO.OUT", 1:"GPIO.IN", 40:"GPIO.SERIAL", 41:"GPIO.SPI", 42:"GPIO.I2C", 43:"GPIO.HARD_PWM", -1:"GPIO.UNKNOWN"}
        # for gpio in range(GPIO.GPIO_COUNT):
        #     try:
        #         print('{}: {} | {}'.format(gpio, bus['GPIO'][gpio]['function'], port_use[RPi.GPIO.gpio_function(gpio)]))
        #     except ValueError as error:
        #         print('{}: {}'.format(error, gpio))
        self.assertEqual(set(bus.keys()), set(['GpioMap', 'SPI', 'GPIO', 'ONEWIRE', 'I2C', 'UART']))

    def testSetFunction(self):
        self.setChannelFunction(5, 'IN')
        self.setChannelFunction(5, 'OUT')

    def testSetValue(self):
        self.setChannelValue(5, 1)
        self.setChannelValue(5, 0)

    def testSensors(self):
        #Test adding a sensor
        testSensor = {'description': 'Digital Input', 'device': 'DigitalSensor', 'args': {'gpio': 'GPIO', 'invert': False, 'channel': 12}, 'name': 'testdevice'}
        compareKeys = ('args', 'description', 'device')
        retValue = SensorsClientTest.client.AddSensor(testSensor['name'], testSensor['description'], testSensor['device'], testSensor['args'])
        self.assertTrue(retValue)
        retrievedSensor = next(obj for obj in SensorsClientTest.client.GetDevices() if obj['name'] == testSensor['name'])
        for key in compareKeys:
            self.assertEqual(testSensor[key], retrievedSensor[key])
        #Test updating a sensor
        editedSensor = testSensor
        editedSensor['args']['channel'] = 13
        retValue = SensorsClientTest.client.EditSensor(editedSensor['name'], editedSensor['description'], editedSensor['device'], editedSensor['args'])
        self.assertTrue(retValue)
        retrievedSensor = next(obj for obj in SensorsClientTest.client.GetDevices() if obj['name'] == editedSensor['name'])
        for key in compareKeys:
            self.assertEqual(editedSensor[key], retrievedSensor[key])
        #Test removing a sensor
        retValue = SensorsClientTest.client.RemoveSensor(testSensor['name'])
        self.assertTrue(retValue)
        deviceNames = [device['name'] for device in SensorsClientTest.client.GetDevices()]
        self.assertNotIn(testSensor['name'], deviceNames)

    def testSensorInfo(self):
        sensors = {'actuator' : {'description': 'Digital Output', 'device': 'DigitalActuator', 'args': {'gpio': 'GPIO', 'invert': False, 'channel': 16}, 'name': 'test_actuator'},
                   'MCP3004' : {'description': 'MCP3004', 'device': 'MCP3004', 'args': {'chip': '0'}, 'name': 'test_MCP3004'},
                   'distance' : {'description': 'Analog Distance Sensor', 'device': 'DistanceSensor', 'args': {'adc': 'test_MCP3004', 'channel': 0}, 'name': 'test_distance'}}
        for sensor in sensors.values():
            SensorsClientTest.client.AddSensor(sensor['name'], sensor['description'], sensor['device'], sensor['args'])
        SensorsClientTest.client.SensorsInfo()
        #Test setting sensor values
        self.setSensorValue(sensors['actuator'], 1)
        self.setSensorValue(sensors['actuator'], 0)
        #Test getting analog value
        retrievedSensorInfo = next(obj for obj in SensorsClientTest.client.SensorsInfo() if obj['name'] == sensors['distance']['name'])
        self.assertEqual(retrievedSensorInfo['float'], 0.0)
        for sensor in sensors.values():
            self.assertTrue(SensorsClientTest.client.RemoveSensor(sensor['name']))

    def testSystemInfo(self):
        system_info = SensorsClientTest.client.SystemInformation()
        self.assertEqual(set(system_info.keys()), set(['Storage', 'Cpu', 'CpuLoad', 'Uptime', 'Network', 'Memory']))

    def setSensorValue(self, sensor, value):
        SensorsClientTest.client.SensorCommand('integer', sensor['name'], sensor['device'], None, None, None, value)
        sensorInfo = next(obj for obj in SensorsClientTest.client.SensorsInfo() if obj['name'] == sensor['name'])
        self.assertEqual(value, sensorInfo['value'])

    def setChannelFunction(self, channel, function):
        SensorsClientTest.client.gpio.setFunctionString(channel, function)
        bus = SensorsClientTest.client.BusInfo()
        self.assertEqual(function, bus['GPIO'][channel]['function'])

    def setChannelValue(self, channel, value):
        SensorsClientTest.client.gpio.digitalWrite(channel, value)
        bus = SensorsClientTest.client.BusInfo()
        self.assertEqual(value, bus['GPIO'][channel]['value'])

if __name__ == '__main__':
    setInfo()
    unittest.main()
