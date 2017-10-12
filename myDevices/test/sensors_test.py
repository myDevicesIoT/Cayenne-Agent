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

    def OnDataChanged(self, sensor_data):
        self.previousSystemData = self.currentSystemData
        self.currentSystemData = sensor_data
        if self.previousSystemData:
            self.done = True

    def testMonitor(self):
        self.previousSystemData = None
        self.currentSystemData = None
        self.done = False
        SensorsClientTest.client.SetDataChanged(self.OnDataChanged)
        # self.setChannelFunction(GPIO().pins[7], 'OUT')
        for i in range(5):
            sleep(5)
            # self.setChannelValue(GPIO().pins[7], i % 2)
            if self.done:
                break
        info('Changed items: {}'.format([x for x in self.currentSystemData if x not in self.previousSystemData]))
        self.assertNotEqual(self.previousSystemData, self.currentSystemData)

    def testBusInfo(self):
        bus = {item['channel']:item['value'] for item in SensorsClientTest.client.BusInfo()}
        info('Bus info: {}'.format(bus))
        self.assertIn('sys:i2c', bus)
        self.assertIn('sys:spi', bus)
        self.assertIn('sys:uart', bus)
        for pin in GPIO().pins:
            self.assertIn('sys:gpio:{};function'.format(pin), bus)
            self.assertIn('sys:gpio:{};value'.format(pin), bus)

    def testSensorsInfo(self):
        sensors = SensorsClientTest.client.SensorsInfo()
        info('Sensors info: {}'.format(sensors))
        for sensor in sensors:
            self.assertEqual('dev:', sensor['channel'][:4])
            self.assertIn('value', sensor)

 
    # def testSetFunction(self):
    #     self.setChannelFunction(GPIO().pins[7], 'IN')
    #     self.setChannelFunction(GPIO().pins[7], 'OUT')

    # def testSetValue(self):
    #     self.setChannelFunction(GPIO().pins[7], 'OUT')
    #     self.setChannelValue(GPIO().pins[7], 1)
    #     self.setChannelValue(GPIO().pins[7], 0)

    # def testSensors(self):
    #     #Test adding a sensor
    #     channel = GPIO().pins[8]
    #     testSensor = {'description': 'Digital Input', 'device': 'DigitalSensor', 'args': {'gpio': 'GPIO', 'invert': False, 'channel': channel}, 'name': 'testdevice'}
    #     compareKeys = ('args', 'description', 'device')
    #     retValue = SensorsClientTest.client.AddSensor(testSensor['name'], testSensor['description'], testSensor['device'], testSensor['args'])
    #     self.assertTrue(retValue)
    #     retrievedSensor = next(obj for obj in SensorsClientTest.client.GetDevices() if obj['name'] == testSensor['name'])
    #     for key in compareKeys:
    #         self.assertEqual(testSensor[key], retrievedSensor[key])
    #     #Test updating a sensor
    #     editedSensor = testSensor
    #     editedSensor['args']['channel'] = GPIO().pins[5]
    #     retValue = SensorsClientTest.client.EditSensor(editedSensor['name'], editedSensor['description'], editedSensor['device'], editedSensor['args'])
    #     self.assertTrue(retValue)
    #     retrievedSensor = next(obj for obj in SensorsClientTest.client.GetDevices() if obj['name'] == editedSensor['name'])
    #     for key in compareKeys:
    #         self.assertEqual(editedSensor[key], retrievedSensor[key])
    #     #Test removing a sensor
    #     retValue = SensorsClientTest.client.RemoveSensor(testSensor['name'])
    #     self.assertTrue(retValue)
    #     deviceNames = [device['name'] for device in SensorsClientTest.client.GetDevices()]
    #     self.assertNotIn(testSensor['name'], deviceNames)

    # def testSensorInfo(self):
    #     actuator_channel = GPIO().pins[9]
    #     light_switch_channel = GPIO().pins[9]
    #     sensors = {'actuator' : {'description': 'Digital Output', 'device': 'DigitalActuator', 'args': {'gpio': 'GPIO', 'invert': False, 'channel': actuator_channel}, 'name': 'test_actuator'},
    #                'light_switch' : {'description': 'Light Switch', 'device': 'LightSwitch', 'args': {'gpio': 'GPIO', 'invert': True, 'channel': light_switch_channel}, 'name': 'test_light_switch'},
    #             #    'MCP3004' : {'description': 'MCP3004', 'device': 'MCP3004', 'args': {'chip': '0'}, 'name': 'test_MCP3004'},
    #             #    'distance' : {'description': 'Analog Distance Sensor', 'device': 'DistanceSensor', 'args': {'adc': 'test_MCP3004', 'channel': 0}, 'name': 'test_distance'}
    #               }
    #     for sensor in sensors.values():
    #         SensorsClientTest.client.AddSensor(sensor['name'], sensor['description'], sensor['device'], sensor['args'])
    #     SensorsClientTest.client.SensorsInfo()
    #     #Test setting sensor values
    #     self.setSensorValue(sensors['actuator'], 1)
    #     self.setSensorValue(sensors['actuator'], 0)
    #     self.setSensorValue(sensors['light_switch'], 1)
    #     self.setSensorValue(sensors['light_switch'], 0)
    #     #Test getting analog value
    #     # retrievedSensorInfo = next(obj for obj in SensorsClientTest.client.SensorsInfo() if obj['name'] == sensors['distance']['name'])
    #     # self.assertEqual(retrievedSensorInfo['float'], 0.0)
    #     for sensor in sensors.values():
    #         self.assertTrue(SensorsClientTest.client.RemoveSensor(sensor['name']))

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
