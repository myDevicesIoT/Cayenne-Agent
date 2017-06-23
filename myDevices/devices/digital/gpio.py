#   Copyright 2012-2013 Eric Ptak - trouch.com
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

import os
import mmap
from time import sleep
from myDevices.utils.types import M_JSON
from myDevices.utils.logger import debug, info, error, exception
from myDevices.devices.digital import GPIOPort
from myDevices.decorators.rest import request, response
from myDevices.system.hardware import MAPPING
try:
    import ASUS.GPIO as gpio_library
except:
    gpio_library = None

FSEL_OFFSET = 0 # 0x0000
PINLEVEL_OFFSET = 13 # 0x0034 / 4

BLOCK_SIZE = (4*1024)

FUNCTIONS   = ["IN", "OUT", "ALT5", "ALT4", "ALT0", "ALT1", "ALT2", "ALT3", "PWM"]

class NativeGPIO(GPIOPort):
    IN = 0
    OUT = 1
    ALT5 = 2
    ALT4 = 3
    ALT0 = 4
    ALT1 = 5
    ALT2 = 6
    ALT3 = 7
    PWM = 8

    ASUS_GPIO = 44

    LOW = 0
    HIGH = 1

    PUD_OFF = 0
    PUD_DOWN = 1
    PUD_UP = 2

    RATIO = 1
    ANGLE = 2
    instance = None

    def __init__(self):
        if not NativeGPIO.instance:
            self.pins = [pin for pin in MAPPING if type(pin) is int]
            GPIOPort.__init__(self, max(self.pins) + 1)
            self.post_value = True
            self.post_function = True
            self.gpio_setup = []
            self.gpio_reset = []
            self.gpio_map = None
            self.valueFile = {pin:0 for pin in self.pins}
            self.functionFile = {pin:0 for pin in self.pins}
            for pin in self.pins:
                # Export the pins here to prevent a delay when accessing the values for the 
                # first time while waiting for the file group to be set
                self.__checkFilesystemExport__(pin)
            if gpio_library:
                gpio_library.setmode(gpio_library.ASUS)
            else:
                try:
                    with open('/dev/gpiomem', 'rb') as gpiomem:
                        self.gpio_map = mmap.mmap(gpiomem.fileno(), BLOCK_SIZE, prot=mmap.PROT_READ)
                except OSError as err:
                    error(err)
            NativeGPIO.instance = self

    def __del__(self):
        if self.gpio_map:
            self.gpio_map.close()

    class SetupException(BaseException):
        pass

    class InvalidDirectionException(BaseException):
        pass

    class InvalidChannelException(BaseException):
        pass

    class InvalidPullException(BaseException):
        pass

    def __str__(self):
        return "NativeGPIO"

    def addGPIO(self, lst, gpio, params):
        gpio = int(gpio)
        params = params.split(" ")
        func = params[0].lower()
        if func == "in":
            func = self.IN
        elif func == "out":
            func = self.OUT
        else:
            raise Exception("Unknown function")

        value = -1
        if len(params) > 1:
            value = int(params[1])
        lst.append({"gpio": gpio, "func": func, "value": value})

    def addGPIOSetup(self, gpio, params):
        self.addGPIO(self.gpio_setup, gpio, params)

    def addGPIOReset(self, gpio, params):
        self.addGPIO(self.gpio_reset, gpio, params)

    def addSetups(self, gpios):
        for (gpio, params) in gpios:
            self.addGPIOSetup(gpio, params)

    def addResets(self, gpios):
        for (gpio, params) in gpios:
            self.addGPIOReset(gpio, params)

    def setup(self):
        for g in self.gpio_setup:
            gpio = g["gpio"]
            debug("Setup GPIO %d" % gpio)
            self.setFunction(gpio, g["func"])
            if g["value"] >= 0 and self.getFunction(gpio) == self.OUT:
                self.__digitalWrite__(gpio, g["value"])

    def close(self):
        for g in self.gpio_reset:
            gpio = g["gpio"]
            debug("Reset GPIO %d" % gpio)
            self.setFunction(gpio, g["func"])
            if g["value"] >= 0 and self.getFunction(gpio) == self.OUT:
                self.__digitalWrite__(gpio, g["value"])

    def checkDigitalChannelExported(self, channel):
        if not channel in self.pins:
            raise Exception("Channel %d is not allowed" % channel)

    def checkPostingFunctionAllowed(self):
        if not self.post_function:
            raise ValueError("POSTing function to native GPIO not allowed")

    def checkPostingValueAllowed(self):
        if not self.post_value:
            raise ValueError("POSTing value to native GPIO not allowed")

    def __checkFilesystemExport__(self, channel):
        #debug("checkExport for channel %d" % channel)
        if not os.path.isdir("/sys/class/gpio/gpio%s" % channel):
            #debug("gpio %d not exported" % channel)
            try:
                with open("/sys/class/gpio/export", "a") as f:
                    f.write("%s" % channel)
            except Exception as ex:
                #error('Failed on __checkFilesystemExport__: ' + str(channel) + ' ' + str(ex))
                return False
        return True

    def __checkFilesystemFunction__(self, channel):
        if self.functionFile[channel] == 0:
            #debug("function file %d not open" %channel)
            valRet = self.__checkFilesystemExport__(channel)
            if not valRet:
                return
            for i in range(10):
                try:
                    self.functionFile[channel] = open("/sys/class/gpio/gpio%s/direction" % channel, "w+")
                    break
                except PermissionError:
                    # Try again since the file group might not have been set to the gpio group
                    # since there is a delay when the gpio channel is first exported
                    sleep(0.01)
            

    def __checkFilesystemValue__(self, channel):
        if self.valueFile[channel] == 0:
            #debug("value file %d not open" %channel)
            valRet = self.__checkFilesystemExport__(channel)
            if not valRet:
                return
            for i in range(10):
                try:
                    self.valueFile[channel] = open("/sys/class/gpio/gpio%s/value" % channel, "w+")
                    break
                except PermissionError:
                    # Try again since the file group might not have been set to the gpio group
                    # since there is a delay when the gpio channel is first exported
                    sleep(0.01)

    def __digitalRead__(self, channel):
        self.__checkFilesystemValue__(channel)
        #self.checkDigitalChannelExported(channel)
        try:
            r = self.valueFile[channel].read(1)
            self.valueFile[channel].seek(0)
            if r[0] == '1':
                return self.HIGH
            else:
                return self.LOW
        except:
            #error('Error' + str(ex))
            return -1

    def __digitalWrite__(self, channel, value):
        self.__checkFilesystemValue__(channel)
        #self.checkDigitalChannelExported(channel)
        #self.checkPostingValueAllowed()
        try:
            if (value == 1):
                self.valueFile[channel].write('1')
            else:
                self.valueFile[channel].write('0')
            self.valueFile[channel].seek(0)
            pass
        except:
            pass

    def __getFunction__(self, channel):
        try:
            offset = FSEL_OFFSET + int(channel / 10) * 4
            shift = int(channel % 10) * 3
            self.gpio_map.seek(offset)
            value = int.from_bytes(self.gpio_map.read(4), byteorder='little')
            value >>= shift
            value &= 7
            return value # 0=input, 1=output, 4=alt0
        except:
            pass
        self.__checkFilesystemFunction__(channel)
        self.checkDigitalChannelExported(channel)
        try:
            if gpio_library:
                value = gpio_library.gpio_function(channel)
                # If this is not a GPIO function return it, otherwise check the function file to see
                # if it is an IN or OUT pin since the ASUS library doesn't provide that info.
                if value != self.ASUS_GPIO:
                    return value
            r = self.functionFile[channel].read()
            self.functionFile[channel].seek(0)
            if r.startswith("out"):
                return self.OUT
            else:
                return self.IN
        except Exception as ex:
            # error('Failed on __getFunction__: '+  str(channel) + ' ' + str(ex))
            return -1

    def __setFunction__(self, channel, value):
        self.__checkFilesystemFunction__(channel)
        self.checkDigitalChannelExported(channel)
        self.checkPostingFunctionAllowed()
        try:
            if (value == self.IN):
                self.functionFile[channel].write("in")
            else:
                self.functionFile[channel].write("out")
            self.functionFile[channel].seek(0)
        except Exception as ex:
            error('Failed on __setFunction__: ' + str(channel) + ' ' + str(ex))
            pass

    def __portRead__(self):
        value = 0
        for i in self.pins:
            value |= self.__digitalRead__(i) << i
        return value

    def __portWrite__(self, value):
        if len(self.pins) <= value.bit_length():
            for i in self.pins:
                if self.getFunction(i) == self.OUT:
                    self.__digitalWrite__(i, (value >> i) & 1)
        else:
            raise Exception("Please limit exported GPIO to write integers")

    #@request("GET", "*")
    @response(contentType=M_JSON)
    def wildcard(self, compact=False):
        if compact:
            f = "f"
            v = "v"
        else:
            f = "function"
            v = "value"

        values = {}
        for i in self.pins:
            if compact:
                func = self.getFunction(i)
            else:
                func = self.getFunctionString(i)
            values[i] = {f: func, v: int(self.__digitalRead__(i))}
        return values

    def getFunction(self, channel):
        return self.__getFunction__(channel)
    
    def getFunctionString(self, channel):
        f = self.getFunction(channel)
        function_string = 'UNKNOWN'
        if f >= 0:
            try:
                function_string = FUNCTIONS[f]
            except:
                pass
        return function_string

    def input(self, channel):
        value =  self.__digitalRead__(channel)
        return value

