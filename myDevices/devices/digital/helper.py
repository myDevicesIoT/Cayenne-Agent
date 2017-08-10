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
from myDevices.utils.types import toint, str2bool
from myDevices.devices import instance
from myDevices.devices.digital.gpio import NativeGPIO as GPIO


class DigitalSensor():
    
    def __init__(self, gpio, channel, invert=False):
        self.gpioname = gpio
        self.channel = toint(channel)
        if isinstance(invert, str):
            self.invert = str2bool(invert)
        else :
            self.invert = invert
        self.gpio = None
        self.setGPIOInstance()
        self.gpio.setFunction(self.channel, GPIO.IN)

    def __str__(self):
        return "DigitalSensor"
    
    def __family__(self):
        return "DigitalSensor"

    def setGPIOInstance(self):
        if not self.gpio:
            if self.gpioname != "GPIO":
                self.gpio = instance.deviceInstance(self.gpioname)
            else:
                self.gpio = GPIO()
            if self.gpio:
                self.gpio.setFunction(self.channel, GPIO.IN)

    #@request("GET", "value")
    @response("%d")
    def read(self):
        self.setGPIOInstance()
        value = self.gpio.digitalRead(self.channel)
        if self.invert:
            value = not value
        return int(value)
        
class MotionSensor(DigitalSensor):
    def __init__(self, gpio, channel, invert=False):
        DigitalSensor.__init__(self, gpio, channel, invert)

    def __str__(self):
        return "MotionSensor"
    
class DigitalActuator(DigitalSensor):
    def __init__(self, gpio, channel, invert=False):
        DigitalSensor.__init__(self, gpio, channel, invert)
        self.gpio.setFunction(self.channel, GPIO.OUT)
    
    def __str__(self):
        return "DigitalActuator"

    def __family__(self):
        return "DigitalActuator"

    #@request("POST", "value/%(value)d")
    @response("%d")
    def write(self, value):
        if self.invert:
            value = int(not value)
        self.gpio.digitalWrite(self.channel, value)
        return self.read()

class LightSwitch(DigitalActuator):        
    def __init__(self, gpio, channel, invert=False):
        DigitalActuator.__init__(self, gpio, channel, invert)

    def __str__(self):
        return "LightSwitch"

class MotorSwitch(DigitalActuator):        
    def __init__(self, gpio, channel, invert=False):
        DigitalActuator.__init__(self, gpio, channel, invert)
        
    def __str__(self):
        return "MotorSwitch"

class RelaySwitch(DigitalActuator):        
    def __init__(self, gpio, channel, invert=False):
        DigitalActuator.__init__(self, gpio, channel, invert)
        
    def __str__(self):
        return "RelaySwitch"

class ValveSwitch(DigitalActuator):        
    def __init__(self, gpio, channel, invert=False):
        DigitalActuator.__init__(self, gpio, channel, invert)
        
    def __str__(self):
        return "ValveSwitch"

