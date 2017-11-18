"""
This module provides a class for interfacing with sensors and actuators. It can add, edit and remove
sensors and actuators as well as monitor their states and execute commands.
"""
from myDevices.utils.logger import exception, info, warn, error, debug, logJson
from time import sleep, time
from json import loads, dumps
from threading import RLock
from myDevices.system import services
from datetime import datetime, timedelta
from os import path, getpid
from myDevices.utils.daemon import Daemon
from myDevices.cloud.dbmanager import DbManager
from myDevices.utils.threadpool import ThreadPool
from myDevices.devices.bus import checkAllBus, BUSLIST
from myDevices.devices.digital.gpio import NativeGPIO as GPIO
from myDevices.devices import manager
from myDevices.devices import instance
from myDevices.utils.types import M_JSON
from myDevices.system.systeminfo import SystemInfo
from myDevices.cloud import cayennemqtt

REFRESH_FREQUENCY = 5 #seconds
# SENSOR_INFO_SLEEP = 0.05

class SensorsClient():
    """Class for interfacing with sensors and actuators"""

    def __init__(self):
        """Initialize the bus and sensor info and start monitoring sensor states"""
        self.sensorMutex = RLock()
        self.continueMonitoring = False
        self.onDataChanged = None
        self.onSystemInfo = None
        self.systemData = []
        self.currentSystemState = []
        self.disabledSensors = {}
        self.disabledSensorTable = "disabled_sensors"
        checkAllBus()
        self.gpio = GPIO()
        manager.addDeviceInstance("GPIO", "GPIO", "GPIO", self.gpio, [], "system")
        manager.loadJsonDevices("rest")
        results = DbManager.Select(self.disabledSensorTable)
        if results:
            for row in results:
                self.disabledSensors[row[0]] = 1
        self.StartMonitoring()

    def SetDataChanged(self, onDataChanged=None, onSystemInfo=None):
        """Set callbacks to call when data has changed
        
        Args:
            onDataChanged: Function to call when sensor data changes
            onSystemInfo: Function to call when system info changes
        """
        self.onDataChanged = onDataChanged
        self.onSystemInfo = onSystemInfo

    def StartMonitoring(self):
        """Start thread monitoring sensor data"""
        self.continueMonitoring = True
        ThreadPool.Submit(self.Monitor)

    def StopMonitoring(self):
        """Stop thread monitoring sensor data"""
        self.continueMonitoring = False

    def Monitor(self):
        """Monitor bus/sensor states and system info and report changed data via callbacks"""
        nextTime = datetime.now()
        nextTimeSystemInfo = datetime.now()
        debug('Monitoring sensors and os resources started')
        while self.continueMonitoring:
            try:
                if datetime.now() > nextTime:
                    self.currentSystemState = []
                    self.MonitorSystemInformation()
                    self.MonitorSensors()
                    self.MonitorBus()
                    if self.currentSystemState != self.systemData:
                        changedSystemData = self.currentSystemState
                        if self.systemData:
                            changedSystemData = [x for x in self.currentSystemState if x not in self.systemData]
                        if self.onDataChanged and changedSystemData:
                            self.onDataChanged(changedSystemData)
                    self.systemData = self.currentSystemState
                    nextTime = datetime.now() + timedelta(seconds=REFRESH_FREQUENCY)
                sleep(REFRESH_FREQUENCY)
            except:
                exception('Monitoring sensors and os resources failed')
        debug('Monitoring sensors and os resources Finished')

    def MonitorSensors(self):
        """Check sensor states for changes"""
        if not self.continueMonitoring:
            return
        self.currentSystemState += self.SensorsInfo()

    def MonitorBus(self):
        """Check bus states for changes"""
        if self.continueMonitoring == False:
            return
        self.currentSystemState += self.BusInfo()

    def MonitorSystemInformation(self):
        """Check system info for changes"""
        if self.continueMonitoring == False:
            return
        self.currentSystemState += self.SystemInformation()

    def SystemInformation(self):
        """Return dict containing current system info, including CPU, RAM, storage and network info"""
        newSystemInfo = []
        try:
            systemInfo = SystemInfo()
            newSystemInfo = systemInfo.getSystemInformation()
        except Exception:
            exception('SystemInformation failed')
        return newSystemInfo

    def CallDeviceFunction(self, func, *args):
        """Call a function for a sensor/actuator device and format the result value type

        Args:
            func: Function to call
            args: Parameters to pass to the function

        Returns:
            True for success, False otherwise.
        """
        result = func(*args)
        if result != None:
            if hasattr(func, "contentType"):
                if func.contentType != M_JSON:
                    value_type = type(result)
                    response = value_type(func.format % result)
                else:
                    response = result
            else:
                response = result
        return response

    def BusInfo(self):
        """Return a dict with current bus info"""
        bus_info = []
        gpio_state = self.gpio.wildcard()
        for key, value in gpio_state.items():
            cayennemqtt.DataChannel.add(bus_info, cayennemqtt.SYS_GPIO, key, cayennemqtt.VALUE, value['value'])
            cayennemqtt.DataChannel.add(bus_info, cayennemqtt.SYS_GPIO, key, cayennemqtt.FUNCTION, value['function'])
        return bus_info

    def SensorsInfo(self):
        """Return a list with current sensor states for all enabled sensors"""
        devices = manager.getDeviceList()
        sensors_info = []
        if devices is None:
            return sensors_info
        for device in devices:
            sensor = instance.deviceInstance(device['name'])
            if 'enabled' not in device or device['enabled'] == 1:
                sensor_types = {'Temperature': {'function': 'getCelsius', 'data_args': {'type': 'temp', 'unit': 'c'}},
                                'Humidity': {'function': 'getHumidityPercent', 'data_args': {'type': 'rel_hum', 'unit': 'p'}},
                                'Pressure': {'function': 'getPascal', 'data_args': {'type': 'bp', 'unit': 'pa'}},
                                'Luminosity': {'function': 'getLux', 'data_args': {'type': 'lum', 'unit': 'lux'}},
                                'Distance': {'function': 'getCentimeter', 'data_args': {'type': 'prox', 'unit': 'cm'}},
                                'ServoMotor': {'function': 'readAngle', 'data_args': {'type': 'analog_actuator'}},
                                'DigitalSensor': {'function': 'read', 'data_args': {'type': 'digital_sensor', 'unit': 'd'}},
                                'DigitalActuator': {'function': 'read', 'data_args': {'type': 'digital_actuator', 'unit': 'd'}},
                                'AnalogSensor': {'function': 'readFloat', 'data_args': {'type': 'analog_sensor'}},
                                'AnalogActuator': {'function': 'readFloat', 'data_args': {'type': 'analog_actuator'}}}
                extension_types = {'ADC': {'function': 'analogReadAllFloat'},
                                    'DAC': {'function': 'analogReadAllFloat'},
                                    'PWM': {'function': 'pwmWildcard'},
                                    'DAC': {'function': 'wildcard'}}
                for device_type in device['type']:
                    if device_type in sensor_types:
                        try:
                            sensor_type = sensor_types[device_type]
                            func = getattr(sensor, sensor_type['function'])
                            if len(device['type']) > 1:
                                channel = '{}:{}'.format(device['name'], device_type.lower())
                            else:
                                channel = device['name']
                            cayennemqtt.DataChannel.add(sensors_info, cayennemqtt.DEV_SENSOR, channel, value=self.CallDeviceFunction(func), **sensor_type['data_args'])
                        except:
                            exception('Failed to get sensor data: {} {}'.format(device_type, device['name']))
                    else:
                        try:
                            extension_type = extension_types[device_type]
                            func = getattr(sensor, extension_type['function'])
                            values = self.CallDeviceFunction(func)
                            for pin, value in values.items():
                                cayennemqtt.DataChannel.add(sensors_info, cayennemqtt.DEV_SENSOR, device['name'] + ':' + str(pin), cayennemqtt.VALUE, value)
                        except:
                            exception('Failed to get extension data: {} {}'.format(device_type, device['name']))
        logJson('Sensors info: {}'.format(sensors_info))
        return sensors_info

    def AddSensor(self, name, description, device, args):
        """Add a new sensor/actuator
   
        Args:
            name: Name of sensor to add
            description: Sensor description
            device: Sensor device class
            args: Sensor specific args

        Returns:
            True for success, False otherwise.
        """
        info('AddSensor: {}, {}, {}, {}'.format(name, description, device, args))
        bVal = False
        try:
            sensorAdd = {}
            if name:
                sensorAdd['name'] = name
            if device:
                sensorAdd['device'] = device
            if args:
                sensorAdd['args'] = args
            if description:
                sensorAdd['description'] = description
            with self.sensorMutex:
                retValue = manager.addDeviceJSON(sensorAdd)
            info('Add device returned: {}'.format(retValue))
            if retValue[0] == 200:
                bVal = True
        except:
            bVal = False
        return bVal

    def EditSensor(self, name, description, device, args):
        """Edit an existing sensor/actuator
  
        Args:
            name: Name of sensor to edit
            description: New sensor description
            device: New sensor device class
            args: New sensor specific args

        Returns:
            True for success, False otherwise.
        """
        info('EditSensor: {}, {}, {}, {}'.format(name, description, device, args))
        bVal = False
        try:
            sensorEdit = {}
            name = name
            sensorEdit['name'] = name
            sensorEdit['device'] = device
            sensorEdit['description'] = description
            sensorEdit['args'] = args
            with self.sensorMutex:
                retValue = manager.updateDevice(name, sensorEdit)
            info('Edit device returned: {}'.format(retValue))
            if retValue[0] == 200:
                bVal = True
        except:
            exception("Edit sensor failed")
            bVal = False
        return bVal

    def RemoveSensor(self, name):
        """Remove an existing sensor/actuator

        Args:
            name: Name of sensor to remove

        Returns:
            True for success, False otherwise.
        """
        bVal = False
        try:
            sensorRemove = name
            with self.sensorMutex:
                retValue = manager.removeDevice(sensorRemove)
            info('Remove device returned: {}'.format(retValue))
            if retValue[0] == 200:
                bVal = True
        except:
            exception("Remove sensor failed")
            bVal = False
        return bVal

    def EnableSensor(self, sensor, enable):
        """Enable a sensor/actuator

        Args:
            sensor: Hash composed from name and device class/type
            enable: 1 to enable, 0 to disable

        Returns:
            True for success, False otherwise.
        """
        info('Enable sensor: ' + str(sensor) + ' ' + str(enable))
        try:
            if sensor is None:
                return False
            if enable is None:
                return False
            with self.sensorMutex:
                if enable == 0:
                    #add item to the list
                    if sensor not in self.disabledSensors:
                        rowId = DbManager.Insert(self.disabledSensorTable, sensor)
                        self.disabledSensors[sensor] = 1
                else:
                    #remove item from the list
                    if sensor in self.disabledSensors:
                        DbManager.Delete(self.disabledSensorTable, sensor)
                        del self.disabledSensors[sensor]
                    #save list
        except Exception as ex:
            error('EnableSensor Failed with exception: '  + str(ex))
            return False
        self.AddRefresh()
        return True

    def GpioCommand(self, command, channel, value):
        """Execute onboard GPIO command

        Args:
            command: Type of command to execute
            channel: GPIO pin
            value: Value to use for writing data

        Returns:
            String containing command specific return value on success, or 'failure' on failure
        """
        info('GpioCommand {}, channel {}, value {}'.format(command, channel, value))
        if command == 'function':
            if value.lower() in ('in', 'input'):
                return str(self.gpio.setFunctionString(channel, 'in'))
            elif value.lower() in ('out', 'output'):
                return str(self.gpio.setFunctionString(channel, 'out'))
        elif command in ('value', ''):
            return self.gpio.digitalWrite(channel, value)
        debug('GPIO command failed')
        return 'failure'

    def SensorCommand(self, command, sensorId, channel, value):
        """Execute sensor/actuator command

        Args:
            command: Type of command to execute
            sensorId: Sensor id
            channel: Pin/channel on device, None if there is no channel
            value: Value to use for setting the sensor state

        Returns:
            Command specific return value on success, False on failure
        """
        result = False
        info('SensorCommand: {}, sensor {}, channel {}, value {}'.format(command, sensorId, channel, value))
        try:
            commands = {'integer': {'function': 'write', 'value_type': int},
                        'value': {'function': 'write', 'value_type': int},
                        'function': {'function': 'setFunctionString', 'value_type': str},
                        'angle': {'function': 'writeAngle', 'value_type': float},
                        'float': {'function': 'writeFloat', 'value_type': float},
                        'volt': {'function': 'writeVolt', 'value_type': float}}
            with self.sensorMutex:
                if sensorId in self.disabledSensors:
                    info('Sensor disabled')
                    return result
                sensor = instance.deviceInstance(sensorId)
                if not sensor:
                    info('Sensor not found')
                    return result
                if command in commands:
                    info('Sensor found: {}'.format(instance.DEVICES[sensorId]))
                    func = getattr(sensor, commands[command]['function'])
                    value = commands[command]['value_type'](value)
                    if channel:
                        result = self.CallDeviceFunction(func, int(channel), value)
                    else:
                        result = self.CallDeviceFunction(func, value)
                    return result
                warn('Command not implemented: {}'.format(command))
                return result
        except Exception:
            exception('SensorCommand failed')
        return result

