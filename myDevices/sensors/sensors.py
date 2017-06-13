from myDevices.utils.logger import exception, info, warn, error, debug, logJson
from time import sleep, time
from json import loads,dumps
from threading import Thread, RLock
from myDevices.os import services
from copy import deepcopy
from datetime import datetime, timedelta
from os import path, getpid
from urllib import parse
import http.client as httplib
from myDevices.os.daemon import Daemon
from myDevices.cloud.dbmanager import DbManager
from myDevices.os.threadpool import ThreadPool
from hashlib import sha1
from http.client import CannotSendRequest
import urllib.request as req
from myDevices.utils.version import MAPPING
from myDevices.devices.bus import checkAllBus, BUSLIST
from myDevices.devices.digital.gpio import NativeGPIO as GPIO
from myDevices.devices import manager
from myDevices.devices import instance
from myDevices.utils.types import M_JSON
from myDevices.os.systeminfo import SystemInfo

REFRESH_FREQUENCY = 0.10 #seconds
SENSOR_INFO_SLEEP = 0.05

class SensorsClient():
    def __init__(self):
        self.sensorMutex = RLock()
        self.systemMutex = RLock()
        self.continueMonitoring = False
        self.onDataChanged = None
        self.onSystemInfo = None
        self.currentBusInfo = self.previousBusInfo = None
        self.currentSensorsInfo = self.previousSensorsInfo = None
        self.currentSystemInfo = self.previousSystemInfo = None
        self.disabledSensors = {}
        self.sensorsRefreshCount = 0
        self.retrievingSystemInfo = False
        self.disabledSensorTable = "disabled_sensors"
        self.systemInfoRefreshList = []
        checkAllBus()
        self.gpio = GPIO()
        manager.addDeviceInstance("GPIO", "GPIO", "GPIO", self.gpio, [], "system")
        manager.loadJsonDevices("rest")
        results = DbManager.Select(self.disabledSensorTable)
        if results:
            for row in results:
                self.disabledSensors[row[0]] = 1
        self.StartMonitoring()
    def SetDataChanged(self, onDataChanged = None, onSystemInfo = None):
        #one parameter only that contains data in a dictionary for changed items only
        self.onDataChanged = onDataChanged
        self.onSystemInfo = onSystemInfo
    def StartMonitoring(self):
        self.continueMonitoring = True
        #thread = Thread(target = self.Monitor)
        #thread.start()
        ThreadPool.Submit(self.Monitor)
    def StopMonitoring(self):
        self.continueMonitoring = False
    def Monitor(self):
        nextTime = datetime.now()
        nextTimeSystemInfo = datetime.now()
        debug('Monitoring sensors and os resources started')
        while self.continueMonitoring:
            try:
                if datetime.now() > nextTime:
                    self.raspberryValue = None
                    self.raspberryValue = {}
                    refreshTime = int(time())
                    if datetime.now() > nextTimeSystemInfo:
                        with self.systemMutex:
                            if not self.retrievingSystemInfo:
                                ThreadPool.Submit(self.MonitorSystemInformation())
                        nextTimeSystemInfo = datetime.now() + timedelta(seconds=5)
                    self.MonitorSensors()
                    self.MonitorBus()
                    if self.onDataChanged != None:
                        self.onDataChanged(self.raspberryValue)
                    bResult=self.RemoveRefresh(refreshTime)
                    if bResult == True and self.onSystemInfo != None:
                        self.onSystemInfo()
                    self.sensorsRefreshCount += 1
                    nextTime = datetime.now() + timedelta(seconds=REFRESH_FREQUENCY)
                sleep(REFRESH_FREQUENCY)
            except:
                exception("Monitoring sensors and os resources failed: " + str() )
        debug('Monitoring sensors and os resources Finished')
    def MonitorSensors(self):
        if self.continueMonitoring == False:
            return
        debug(str(time()) + ' Get sensors info ' + str(self.sensorsRefreshCount))
        self.SensorsInfo()
        debug(str(time()) + ' Got sensors info ' + str(self.sensorsRefreshCount))
        with self.sensorMutex:
            if self.SHA_Calc(self.currentSensorsInfo) != self.SHA_Calc(self.previousSensorsInfo):
                #do merge
                mergedSensors = self.ChangedSensorsList()
                if self.previousSensorsInfo:
                    del self.previousSensorsInfo
                    self.previousSensorsInfo = None
                if mergedSensors == None:
                    self.previousSensorsInfo = self.currentSensorsInfo
                    return
                self.raspberryValue['SensorsInfo'] = mergedSensors
                self.previousSensorsInfo = self.currentSensorsInfo
        debug(str(time()) + ' Merge sensors info ' + str(self.sensorsRefreshCount))
    def ChangedSensorsList(self):
        if self.continueMonitoring == False:
            return None
        if self.previousSensorsInfo == None:
            return None
        if self.currentSensorsInfo == None:
            return None
        changedSensors = []
        previousSensorsDictionary = dict((i['sensor'], i) for i in self.previousSensorsInfo)
        for item in self.currentSensorsInfo:
            oldItem = None
            if item['sensor'] in previousSensorsDictionary:
                oldItem = previousSensorsDictionary[item['sensor']]
                if self.SHA_Calc(item) != self.SHA_Calc(oldItem):
                    changedSensors.append(item)
            else:
                changedSensors.append(item)
        return changedSensors
    def MonitorBus(self):
        if self.continueMonitoring == False:
            return
        debug(str(time()) + ' Get bus info ' + str(self.sensorsRefreshCount))
        self.BusInfo()
        debug(str(time()) + ' Got bus info ' + str(self.sensorsRefreshCount))
        if self.SHA_Calc(self.currentBusInfo) != self.SHA_Calc(self.previousBusInfo):
            self.raspberryValue['BusInfo'] = self.currentBusInfo
            if self.previousBusInfo: 
                del self.previousBusInfo
                self.previousBusInfo = None
            self.previousBusInfo = self.currentBusInfo
    def MonitorSystemInformation(self):
        if self.continueMonitoring == False:
            return
        debug(str(time()) + ' Get system info ' + str(self.sensorsRefreshCount))
        self.SystemInformation()
        debug(str(time()) + ' Got system info ' + str(self.sensorsRefreshCount))
        firstSHA = self.SHA_Calc(self.currentSystemInfo) 
        secondSHA = self.SHA_Calc(self.previousSystemInfo)
        if firstSHA != secondSHA:
            if self.previousSystemInfo:
                del self.previousSystemInfo
                self.previousSystemInfo = None
            self.previousSystemInfo = self.currentSystemInfo
            self.raspberryValue['SystemInfo'] = self.currentSystemInfo
    def SystemInformation(self):
        with self.systemMutex:
             self.retrievingSystemInfo = True
        try:
            systemInfo = SystemInfo()
            newSystemInfo = systemInfo.getSystemInformation()
            if newSystemInfo:
                self.currentSystemInfo = newSystemInfo
        except Exception as ex:
            exception('SystemInformation failed: '+str(ex))
        with self.systemMutex:
             self.retrievingSystemInfo = False
        return self.currentSystemInfo
    def SHA_Calc(self, object):
        if object == None:
            return ''
        try:
            strVal = dumps(object)
        except:
            exception('SHA_Calc failed for:' + str(object))
            return ''
        return self.SHA_Calc_str(strVal)
    def SHA_Calc_str(self, stringVal):
        m = sha1()
        m.update(stringVal.encode('utf8'))
        sDigest = str(m.hexdigest())
        return sDigest
    def AppendToDeviceList(self, device_list, source, device_type):
        device = source.copy()
        del device['origin']
        device['name'] = parse.unquote(device['name'])
        device['type'] = device_type
        if len(source['type']) > 1:
            device['hash'] = self.SHA_Calc_str(device['name']+device['type'])
        else:
            device['hash'] = self.SHA_Calc_str(device['name']+device['device'])
        if device['hash'] in self.disabledSensors:
            device['enabled'] = 0
        else:
            device['enabled'] = 1
        device_list.append(device)
    def GetDevices(self):
        device_list = manager.getDeviceList()
        devices = []
        for dev in device_list:
            try:
                if len(dev['type']) == 0:
                    self.AppendToDeviceList(devices, dev, '')
                else:
                    for device_type in dev['type']:
                        self.AppendToDeviceList(devices, dev, device_type)
            except:
                exception ("Failed to get device: {}".format(dev))
        return devices
    def CallDeviceFunction(self, func, *args):
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
        json = {}
        for (bus, value) in BUSLIST.items():
            json[bus] = int(value["enabled"])
        gpios = {}
        for gpio in range(GPIO.GPIO_COUNT):
            gpios[gpio] = {}
            gpios[gpio]['function'] = self.gpio.getFunctionString(gpio)
            gpios[gpio]['value'] = int(self.gpio.input(gpio))
        json['GPIO'] = gpios
        json['GpioMap'] = MAPPING
        self.currentBusInfo = json
        return self.currentBusInfo
    def SensorsInfo(self):
        with self.sensorMutex:
            devices = self.GetDevices()
            debug(str(time()) + ' Got devices info ' + str(self.sensorsRefreshCount))
            if devices is None:
                return {}
            for value in devices:
                sensor = instance.deviceInstance(value['name'])
                if 'enabled' not in value or value['enabled'] == 1:
                    sleep(SENSOR_INFO_SLEEP)
                    try:
                        if value['type'] == 'Temperature':
                            value['Celsius'] = self.CallDeviceFunction(sensor.getCelsius)
                            value['Fahrenheit'] = self.CallDeviceFunction(sensor.getFahrenheit)
                            value['Kelvin'] =self.CallDeviceFunction(sensor.getKelvin)
                        if value['type'] == 'Pressure':
                            value['Pascal'] = self.CallDeviceFunction(sensor.getPascal)
                        if value['type'] == 'Luminosity':
                            value['Lux'] = self.CallDeviceFunction(sensor.getLux)
                        if value['type'] == 'Distance':
                            value['Centimeter'] = self.CallDeviceFunction(sensor.getCentimeter)
                            value['Inch'] = self.CallDeviceFunction(sensor.getInch)
                        if value['type'] in ('ADC', 'DAC', 'PWM'):
                            value['channelCount'] = self.CallDeviceFunction(sensor.analogCount)
                            value['maxInteger'] = self.CallDeviceFunction(sensor.analogMaximum)
                            value['resolution'] = self.CallDeviceFunction(sensor.analogResolution)
                            value['allInteger'] = self.CallDeviceFunction(sensor.analogReadAll)
                            value['allVolt'] = self.CallDeviceFunction(sensor.analogReadAllVolt)
                            value['allFloat'] = self.CallDeviceFunction(sensor.analogReadAllFloat)
                            if value['type'] in ('DAC'):
                                value['vref'] = self.CallDeviceFunction(sensor.analogReference)
                        if value['type'] == 'PWM':
                            value['channelCount'] = self.CallDeviceFunction(sensor.pwmCount)
                            value['maxInteger'] = self.CallDeviceFunction(sensor.pwmMaximum)
                            value['resolution'] = self.CallDeviceFunction(sensor.pwmResolution)
                            value['all'] = self.CallDeviceFunction(sensor.pwmWildcard)
                        if value['type'] == 'Humidity':
                            value['float']=self.CallDeviceFunction(sensor.getHumidity)
                            value['percent']=self.CallDeviceFunction(sensor.getHumidityPercent)
                        if value['type'] == 'PiFaceDigital':
                            value['all'] = self.CallDeviceFunction(sensor.readAll)
                        if value['type'] in ('DigitalSensor', 'DigitalActuator'):
                            value['value'] = self.CallDeviceFunction(sensor.read)
                        if value['type'] == 'GPIOPort':
                            value['channelCount'] = self.CallDeviceFunction(sensor.digitalCount)
                            value['all'] = self.CallDeviceFunction(sensor.wildcard)
                        if value['type'] == 'AnalogSensor':
                            value['integer'] = self.CallDeviceFunction(sensor.read)
                            value['float'] = self.CallDeviceFunction(sensor.readFloat)
                            value['volt'] = self.CallDeviceFunction(sensor.readVolt)
                        if value['type'] == 'ServoMotor':
                            value['angle'] = self.CallDeviceFunction(sensor.readAngle)
                        if value['type'] == 'AnalogActuator':
                            value['float'] = self.CallDeviceFunction(sensor.readFloat)
                    except:
                        exception ("Sensor values failed: "+ value['type'] + " " + value['name']) 
                try:
                    if 'hash' in value:
                        value['sensor'] = value['hash']
                        del value['hash']
                except KeyError:
                    pass
            if self.currentSensorsInfo:
                del self.currentSensorsInfo
                self.currentSensorsInfo = None
            self.currentSensorsInfo = devices
            devices = None
        if self.sensorsRefreshCount == 0:
            info('System sensors info at start '+str(self.currentSensorsInfo))
        debug(('New sensors info retrieved: {}').format(self.sensorsRefreshCount))
        logJson('Sensors Info updated: ' + str(self.currentSensorsInfo))
        return self.currentSensorsInfo
    def AddSensor(self, name, description, device, args):
        info('AddSensor: {}, {}, {}, {}'.format(name, description, device, args))
        bVal = False
        try:
            sensorAdd = {}
            if name:
                sensorAdd['name'] = req.pathname2url(name)
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
                self.AddRefresh()
        except:
            bVal = False
        return bVal
    def EditSensor(self, name, description, device, args):
        info('EditSensor: {}, {}, {}, {}'.format(name, description, device, args))
        bVal = False
        try:
            sensorEdit= {}
            name = req.pathname2url(name)
            sensorEdit['name'] = name
            sensorEdit['device'] = device
            sensorEdit['description'] = description
            sensorEdit['args'] = args
            with self.sensorMutex:
                retValue = manager.updateDevice(name, sensorEdit)
            info('Edit device returned: {}'.format(retValue))
            try:
                hashKey = self.SHA_Calc_str(name+device)
                with self.sensorMutex:
                    if self.currentSensorsInfo:
                        currentSensorsDictionary = dict((i['sensor'], i) for i in self.currentSensorsInfo)
                        sensorData = currentSensorsDictionary[hashKey]
                        sensor = sensorData[hashKey]
                        raspberryValue = {}
                        sensor['args'] = args
                        sensor['description'] = description
                        raspberryValue['SensorsInfo'] = []
                        raspberryValue['SensorsInfo'].append(sensor)
                        if self.onDataChanged != None:
                            self.onDataChanged(raspberryValue)
            except:
                pass
            if retValue[0] == 200:
                bVal = True
                self.AddRefresh()
        except:
            exception ("Edit sensor failed") 
            bVal = False
        return bVal
    def DeleteSensor(self, name):
        bVal = False
        try:
            sensorRemove = req.pathname2url(name)
            with self.sensorMutex:
                retValue = manager.removeDevice(sensorRemove)
            info('Remove device returned: {}'.format(retValue))
            if retValue[0] == 200:
                bVal = True
                self.AddRefresh()
        except:
            exception ("Remove sensor failed")
            bVal = False
        return bVal
    def RemoveSensor(self, name):
        debug('')
        return self.DeleteSensor(name)
    def EnableSensor(self, sensor, enable):
        #sensor is the hash composed from name and device class/type
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
    def AddRefresh(self):
        self.systemInfoRefreshList.append(int(time()))
    def RemoveRefresh(self, newRefresh):
        bReturn = False
        for i in self.systemInfoRefreshList:
            if i < newRefresh:
                self.systemInfoRefreshList.remove(i)
                bReturn = True
        return bReturn
    def GpioCommand(self, commandType, method, channel, value):
        debug('')
        info('GpioCommand ' + commandType + ' method ' + method + ' Channel: ' + str(channel) + ' Value: ' + str(value))
        if commandType == 'function':
            if method == 'POST':
                debug('setFunction:' + str(channel) + ' ' + str(value))
                return str(self.gpio.setFunctionString(channel, value))
            if method == 'GET':
                debug('getFunction:' + str(channel) + ' ' + str(value))
                return str(self.gpio.getFunctionString(channel))
        if commandType == 'value':
            if method == 'POST':
                debug('digitalWrite:' + str(channel) + ' ' + str(value))
                retVal = str(self.gpio.digitalWrite(channel, value))
                return retVal
            if method == 'GET':
                debug('digitalRead:' + str(channel))
                return str(self.gpio.digitalRead(channel))
        if commandType == 'integer':
            if method == 'POST':
                debug('portWrite:' + str(value))
                return str(self.gpio.portWrite(value))
            if method == 'GET':
                debug('portRead:' )
                return str(self.gpio.portRead())
        debug.log('GpioCommand not set')
        return 'failure'
    def SensorCommand(self, commandType, sensorName, sensorType, driverClass, method, channel, value):
        retVal = False
        info('SensorCommand: {} SensorName {} SensorType {} DriverClass {} Method {} Channel {} Value {}'.format(commandType, sensorName, sensorType, driverClass, method, channel, value) )
        try:
            self.AddRefresh()
            debug('')
            actuators=('GPIOPort', 'ServoMotor', 'AnalogActuator', 'LoadSensor', 'PiFaceDigital', 'DistanceSensor', 'Thermistor', 'Photoresistor', 'LightDimmer', 'LightSwitch', 'DigitalSensor', 'DigitalActuator', 'MotorSwitch', 'RelaySwitch', 'ValveSwitch', 'MotionSensor')
            gpioExtensions=('GPIOPort', 'PiFaceDigital')
            if driverClass is None:
                hashKey = self.SHA_Calc_str(sensorName+sensorType)
            else:
                hashKey = self.SHA_Calc_str(sensorName+driverClass)
            with self.sensorMutex:
                if hashKey in self.disabledSensors:
                    return retVal
                sensor = instance.deviceInstance(sensorName)
                if not sensor:
                    info('Sensor not found')
                    return retVal
                if (sensorType in actuators) or (driverClass in actuators):
                    if sensorType in gpioExtensions or driverClass in gpioExtensions:
                        if commandType == 'integer' or commandType == 'value':
                            retVal = str(self.CallDeviceFunction(sensor.write, int(channel), int(value)))
                            return retVal
                    else:
                        if commandType == 'integer':
                            retVal = str(self.CallDeviceFunction(sensor.write, int(value)))
                            return retVal
                    if commandType == 'function':
                        retVal = str(self.CallDeviceFunction(sensor.setFunctionString, channel, value))
                        return retVal
                    if commandType == 'angle':
                        retVal = self.CallDeviceFunction(sensor.writeAngle, value)
                        return retVal
                    if commandType == 'float':
                        retVal = self.CallDeviceFunction(sensor.writeFloat, float(value))
                        return retVal
                if commandType == 'integer':
                    retVal = float(self.CallDeviceFunction(sensor.write, int(channel), int(value)))
                    return retVal
                if commandType == 'float':
                    retVal = float(self.CallDeviceFunction(sensor.writeFloat, int(channel), float(value)))
                    return retVal
                if commandType == 'volt':
                    retVal = float(self.CallDeviceFunction(sensor.writeVolt, int(channel), float(value)))
                    return retVal
                if commandType == 'angle':
                    retVal = float(self.CallDeviceFunction(sensor.writeAngle, int(channel), float(value)))
                    return retVal
                warn('Command not implemented: ' + commandType)
                return retVal
        except Exception as ex:
            exception('SensorCommand failed with: ' +str(ex))
            pass
        finally:
            #looks like this breaks actuators refresh by updating and not sending data changed
            #then refresh never comes for the specific sensor
            #ThreadPool.SubmitParam(self.Monitor, hashKey)
            return retVal

