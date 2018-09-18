"""
This module provides a class for interfacing with sensors and actuators. It can add, edit and remove
sensors and actuators as well as monitor their states and execute commands.
"""
from datetime import datetime, timedelta
from json import dumps, loads
from os import getpid, path
from threading import Event, RLock

from myDevices.cloud import cayennemqtt
from myDevices.cloud.dbmanager import DbManager
from myDevices.cloud.download_speed import DownloadSpeed
from myDevices.devices import instance, manager
from myDevices.devices.bus import BUSLIST, checkAllBus
from myDevices.devices.digital.gpio import NativeGPIO as GPIO
from myDevices.system import services
from myDevices.system.systeminfo import SystemInfo
from myDevices.plugins.manager import PluginManager
from myDevices.utils.config import Config, APP_SETTINGS
from myDevices.utils.daemon import Daemon
from myDevices.utils.logger import debug, error, exception, info, logJson, warn
from myDevices.utils.threadpool import ThreadPool
from myDevices.utils.types import M_JSON

REFRESH_FREQUENCY = 15 #seconds
DIGITAL_FREQUENCY = 60/55 #Seconds/messages, this is done to keep messages under the rate limit

class SensorsClient():
    """Class for interfacing with sensors and actuators"""

    def __init__(self):
        """Initialize the bus and sensor info and start monitoring sensor states"""
        self.sensorMutex = RLock()
        self.digitalMutex = RLock()
        self.exiting = Event()
        self.onDataChanged = None
        self.systemData = []
        self.currentSystemState = []
        self.currentDigitalData = {}                                
        self.queuedDigitalData = {}
        self.disabledSensors = {}
        self.disabledSensorTable = "disabled_sensors"
        checkAllBus()
        self.gpio = GPIO()
        self.downloadSpeed = DownloadSpeed(Config(APP_SETTINGS))
        self.downloadSpeed.getDownloadSpeed()
        manager.addDeviceInstance("GPIO", "GPIO", "GPIO", self.gpio, [], "system")
        manager.loadJsonDevices("rest")
        results = DbManager.Select(self.disabledSensorTable)
        if results:
            for row in results:
                self.disabledSensors[row[0]] = 1
        self.pluginManager = PluginManager()
        self.digitalMonitorRunning = False
        self.InitCallbacks()
        self.StartMonitoring()

    def SetDataChanged(self, onDataChanged=None):
        """Set callback to call when data has changed
        
        Args:
            onDataChanged: Function to call when sensor data changes
        """
        self.onDataChanged = onDataChanged

    def OnSensorChange(self, device, value):
        """Callback that is called when digital sensor data has changed

        Args:
            device: The device that has changed data
            value: The new data value
        """
        debug('OnSensorChange: {}, {}'.format(device, value))
        with self.digitalMutex:
            if device['name'] not in self.currentDigitalData:
                self.currentDigitalData[device['name']] = {'device': device, 'value': value}
            else:
                self.queuedDigitalData[device['name']] = {'device': device, 'value': value}

    def InitCallbacks(self):
        """Set callback function for any digital devices that support them"""
        devices = manager.getDeviceList()
        for device in devices:
            sensor = instance.deviceInstance(device['name'])
            if 'DigitalSensor' in device['type'] and hasattr(sensor, 'setCallback'):
                debug('Set callback for {}'.format(sensor))
                sensor.setCallback(self.OnSensorChange, device)
                if not self.digitalMonitorRunning:
                    ThreadPool.Submit(self.DigitalMonitor)

    def RemoveCallbacks(self):
        """Remove callback function for all digital devices"""
        devices = manager.getDeviceList()
        for device in devices:
            sensor = instance.deviceInstance(device['name'])
            if 'DigitalSensor' in device['type'] and hasattr(sensor, 'removeCallback'):
                sensor.removeCallback()

    def StartMonitoring(self):
        """Start thread monitoring sensor data"""
        ThreadPool.Submit(self.Monitor)

    def StopMonitoring(self):
        """Stop thread monitoring sensor data"""
        self.RemoveCallbacks()
        self.exiting.set()

    def Monitor(self):
        """Monitor bus/sensor states and system info and report changed data via callbacks"""
        debug('Monitoring sensors and os resources started')
        sendAllDataCount = 0
        nextTime = datetime.now()
        while not self.exiting.is_set():
            try:
                difference = nextTime - datetime.now()
                delay = min(REFRESH_FREQUENCY, difference.total_seconds())
                delay = max(0, delay)
                if not self.exiting.wait(delay):
                    nextTime = datetime.now() + timedelta(seconds=REFRESH_FREQUENCY)
                    self.currentSystemState = []
                    self.MonitorSystemInformation()
                    self.MonitorSensors()
                    self.MonitorPlugins()
                    self.MonitorBus()
                    if self.currentSystemState != self.systemData:
                        data = self.currentSystemState
                        if self.systemData and not sendAllDataCount == 0:
                            data = [x for x in self.currentSystemState if x not in self.systemData]
                        if self.onDataChanged and data:
                            self.onDataChanged(data)
                    sendAllDataCount += 1
                    if sendAllDataCount >= 4:
                        sendAllDataCount = 0
                    self.systemData = self.currentSystemState
            except:
                exception('Monitoring sensors and os resources failed')
        debug('Monitoring sensors and os resources finished')

    def DigitalMonitor(self):
        """Monitor digital state changes and report changed data via callbacks"""
        self.digitalMonitorRunning = True
        info('Monitoring digital sensor changes')
        nextTime = datetime.now()
        while not self.exiting.is_set():
            try:
                if not self.exiting.wait(0.5):
                    if datetime.now() > nextTime:
                        nextTime = datetime.now() + timedelta(seconds=DIGITAL_FREQUENCY)
                        data = []
                        with self.digitalMutex:
                            if self.currentDigitalData:
                                for name, item in self.currentDigitalData.items():
                                    cayennemqtt.DataChannel.add_unique(data, cayennemqtt.DEV_SENSOR, name, value=item['value'], name=item['device']['description'], type='digital_sensor', unit='d')
                                    try:
                                        cayennemqtt.DataChannel.add_unique(data, cayennemqtt.SYS_GPIO, item['device']['args']['channel'], cayennemqtt.VALUE, item['value'])
                                    except:
                                        pass
                                    if name in self.queuedDigitalData and self.queuedDigitalData[name]['value'] == item['value']:
                                        del self.queuedDigitalData[name]
                                self.currentDigitalData = self.queuedDigitalData
                                self.queuedDigitalData = {}
                        if data:
                            self.onDataChanged(data)
            except:
                exception('Monitoring digital sensor changes failed')
        debug('Monitoring digital sensor changes finished')
        self.digitalMonitorRunning = False

    def MonitorSensors(self):
        """Check sensor states for changes"""
        if self.exiting.is_set():
            return
        self.currentSystemState += self.SensorsInfo()

    def MonitorPlugins(self):
        """Check plugin states for changes"""
        if self.exiting.is_set():
            return
        self.currentSystemState += self.pluginManager.get_plugin_readings()

    def MonitorBus(self):
        """Check bus states for changes"""
        if self.exiting.is_set():
            return
        self.currentSystemState += self.BusInfo()

    def MonitorSystemInformation(self):
        """Check system info for changes"""
        if self.exiting.is_set():
            return
        self.currentSystemState += self.SystemInformation()

    def SystemInformation(self):
        """Return dict containing current system info, including CPU, RAM, storage and network info"""
        newSystemInfo = []
        try:
            systemInfo = SystemInfo()
            newSystemInfo = systemInfo.getSystemInformation()
            download_speed = self.downloadSpeed.getDownloadSpeed()
            if download_speed:
                cayennemqtt.DataChannel.add(newSystemInfo, cayennemqtt.SYS_NET, suffix=cayennemqtt.SPEEDTEST, value=download_speed, type='bw', unit='mbps')
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
        manager.deviceDetector()
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
                                    'GPIOPort': {'function': 'wildcard'}}
                for device_type in device['type']:
                    try:
                        display_name = device['description']
                    except:
                        display_name = None
                    if device_type in sensor_types:
                        try:
                            sensor_type = sensor_types[device_type]
                            func = getattr(sensor, sensor_type['function'])
                            if len(device['type']) > 1:
                                channel = '{}:{}'.format(device['name'], device_type.lower())
                            else:
                                channel = device['name']
                            cayennemqtt.DataChannel.add(sensors_info, cayennemqtt.DEV_SENSOR, channel, value=self.CallDeviceFunction(func), name=display_name, **sensor_type['data_args'])
                        except:
                            exception('Failed to get sensor data: {} {}'.format(device_type, device['name']))
                    else:
                        try:
                            extension_type = extension_types[device_type]
                            func = getattr(sensor, extension_type['function'])
                            values = self.CallDeviceFunction(func)
                            for pin, value in values.items():
                                cayennemqtt.DataChannel.add(sensors_info, cayennemqtt.DEV_SENSOR, device['name'] + ':' + str(pin), cayennemqtt.VALUE, value, name=display_name)
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
                self.InitCallbacks()
            info('Add device returned: {}'.format(retValue))
            if retValue[0] == 200:
                bVal = True
        except Exception:
            exception('Error adding sensor')
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
                self.InitCallbacks()
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
            if self.pluginManager.is_plugin(name):
                return self.pluginManager.disable(name)
            sensorRemove = name
            try:
                sensor = instance.deviceInstance(sensorRemove)
                if hasattr(sensor, 'removeCallback'):
                    sensor.removeCallback()
            except: 
                pass
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
                        DbManager.Insert(self.disabledSensorTable, sensor)
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
            return self.gpio.digitalWrite(channel, int(value))
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
            if self.pluginManager.is_plugin(sensorId, channel):
                return self.pluginManager.write_value(sensorId, channel, value)
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
