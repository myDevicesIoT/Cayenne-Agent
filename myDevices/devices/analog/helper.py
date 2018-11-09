#   Copyright 2015 Eric Ptak - trouch.com
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.

from myDevices.decorators.rest import request, response
from myDevices.utils.types import toint
from myDevices.devices import instance
from myDevices.utils.logger import info
from myDevices.plugins.manager import PluginManager

class AnalogSensor():
    def __init__(self, adc, channel):
        self.adcname = adc
        self.channel = toint(channel)
        self.adc = None
        self.pluginManager = PluginManager()
        self.setADCInstance()

    def __str__(self):
        return "AnalogSensor"
    
    def __family__(self):
        return "AnalogSensor"
    
    def setADCInstance(self):
        if not self.adc:
            self.adc = instance.deviceInstance(self.adcname)
            if not self.adc:
                self.adc = self.pluginManager.get_extension(self.adcname)

    @response("%d")
    def read(self):
        self.setADCInstance()
        try:
            value = self.adc.analogRead(self.channel)
        except:
            value = getattr(self.adc['instance'], self.adc['read'])(self.channel)
        return value
    
    @response("%.2f")
    def readFloat(self):
        self.setADCInstance()
        try:
            value = self.adc.analogReadFloat(self.channel)
        except:
            value = getattr(self.adc['instance'], self.adc['read'])(self.channel, 'float')
        return value
    
    @response("%.2f")
    def readVolt(self):
        self.setADCInstance()
        try:
            value = self.adc.analogReadVolt(self.channel)
        except:
            value = getattr(self.adc['instance'], self.adc['read'])(self.channel, 'volt')
        return value


class Photoresistor(AnalogSensor):
    def __init__(self, adc, channel):
        AnalogSensor.__init__(self, adc, channel)

    def __str__(self):
        return "Photoresistor"
            
class Thermistor(AnalogSensor):
    def __init__(self, adc, channel):
        AnalogSensor.__init__(self, adc, channel)

    def __str__(self):
        return "Thermistor"
    
class DistanceSensor(AnalogSensor):
    def __init__(self, adc, channel):
        info('DistanceSensor init {} {}'.format(adc, channel))
        AnalogSensor.__init__(self, adc, channel)

    def __str__(self):
        return "DistanceSensor"
    
class LoadSensor(AnalogSensor):
    def __init__(self, adc, channel):
        AnalogSensor.__init__(self, adc, channel)

    def __str__(self):
        return "LoadSensor"
    
    
    
class ServoMotor():
    def __init__(self, pwm, channel):
        self.pwmname = pwm
        self.channel = toint(channel)
        self.pwm = None
        self.setPWMInstance()
        self.pwm.pwmWriteAngle(self.channel, 0)
        
        
    def __str__(self):
        return "ServoMotor"
    
    def __family__(self):
        return "ServoMotor"
    
    def setPWMInstance(self):
        if not self.pwm:
            self.pwm = instance.deviceInstance(self.pwmname)

    #@request("GET", "angle")
    @response("%.2f")
    def readAngle(self):
        self.setPWMInstance()
        return self.pwm.pwmReadAngle(self.channel)
        
    #@request("POST", "angle/%(value)f")
    @response("%.2f")
    def writeAngle(self, value):
        self.setPWMInstance()
        return self.pwm.pwmWriteAngle(self.channel, value)
    
class AnalogActuator():
    def __init__(self, pwm, channel):
        self.pwmname = pwm
        self.pwm = None
        self.setPWMInstance()
        self.channel = toint(channel)
        
    def __str__(self):
        return "AnalogActuator"
    
    def __family__(self):
        return "AnalogActuator"

    def setPWMInstance(self):
        if not self.pwm:
            self.pwm = instance.deviceInstance(self.pwmname)

    #@request("GET", "float")
    @response("%.2f")
    def readFloat(self):
        self.setPWMInstance()
        return self.pwm.pwmReadFloat(self.channel)
        
    #@request("POST", "float/%(value)f")
    @response("%.2f")
    def writeFloat(self, value):
        self.setPWMInstance()
        return self.pwm.pwmWriteFloat(self.channel, value)

class LightDimmer(AnalogActuator):
    def __init__(self, pwm, channel):
        AnalogActuator.__init__(self, pwm, channel)

    def __str__(self):
        return "LightDimmer"
