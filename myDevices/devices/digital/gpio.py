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
from myDevices.utils.singleton import Singleton
from myDevices.devices.digital import GPIOPort
from myDevices.decorators.rest import response
from myDevices.system.hardware import BOARD_REVISION, Hardware
from myDevices.system.systemconfig import SystemConfig
from myDevices.utils.subprocess import executeCommand
try:
    import ASUS.GPIO as gpio_library
except:
    gpio_library = None


FSEL_OFFSET = 0 # 0x0000
PINLEVEL_OFFSET = 13 # 0x0034 / 4

BLOCK_SIZE = (4*1024)

class NativeGPIO(Singleton, GPIOPort):
    IN = 0
    OUT = 1

    ASUS_GPIO = 44

    LOW = 0
    HIGH = 1

    PUD_OFF = 0
    PUD_DOWN = 1
    PUD_UP = 2

    RATIO = 1
    ANGLE = 2

    MAPPING = []

    def __init__(self):
        self.setPinMapping()
        GPIOPort.__init__(self, max(self.pins) + 1)
        self.post_value = True
        self.post_function = True
        self.gpio_setup = []
        self.gpio_reset = []
        self.gpio_map = None
        self.pinFunctionSet = set()
        self.valueFile = {pin:None for pin in self.pins}
        self.functionFile = {pin:None for pin in self.pins}
        for pin in self.pins:
            # Export the pins here to prevent a delay when accessing the values for the 
            # first time while waiting for the file group to be set
            self.__checkFilesystemExport__(pin)
        if gpio_library:
            gpio_library.setmode(gpio_library.ASUS)
        elif not Hardware().isRaspberryPi3():
            # On the Pi 3 the memory mapped /dev/gpiomem file seems to give strange, inconsistent readings, like duplicated
            # 4 byte sequences and "oipg" ASCII values. This might be some issue with the way Python mmap works since it didn't
            # seem to happen with the wiringPi C library using uint32_t pointers. For now we just avoid using /dev/gpiomem on Pi 3.
            try:
                with open('/dev/gpiomem', 'rb') as gpiomem:
                    self.gpio_map = mmap.mmap(gpiomem.fileno(), BLOCK_SIZE, prot=mmap.PROT_READ)
            except FileNotFoundError:
                pass
            except OSError as err:
                error(err)

    def __del__(self):
        if hasattr(self, 'gpio_map'):
            self.gpio_map.close()
        for value in self.valueFile.values():
            if value:
                value.close()
        for value in self.functionFile.values():
            if value:
                value.close()

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
    
    def __getFunctionFilePath__(self, channel):
        return "/sys/class/gpio/gpio%s/direction" % channel

    def __getValueFilePath__(self, channel):
        return "/sys/class/gpio/gpio%s/value" % channel

    def __checkFilesystemExport__(self, channel):
        #debug("checkExport for channel %d" % channel)
        if not os.path.isdir("/sys/class/gpio/gpio%s" % channel):
            #debug("gpio %d not exported" % channel)
            try:
                with open("/sys/class/gpio/export", "a") as f:
                    f.write("%s" % channel)
            except PermissionError:
                command = 'sudo python3 -m myDevices.devices.writevalue -f /sys/class/gpio/export -t {}'.format(channel)
                executeCommand(command)               
            except Exception as ex:
                error('Failed on __checkFilesystemExport__: ' + str(channel) + ' ' + str(ex))
                return False
        return True

    def __checkFilesystemFunction__(self, channel):
        if not self.functionFile[channel]:
            #debug("function file %d not open" %channel)
            valRet = self.__checkFilesystemExport__(channel)
            if not valRet:
                return
            mode = 'w+'
            if (gpio_library or Hardware().isBeagleBone()) and os.geteuid() != 0:
                #On devices with root permissions on gpio files open the file in read mode from non-root process
                mode = 'r'
            for i in range(10):
                try:
                    self.functionFile[channel] = open(self.__getFunctionFilePath__(channel), mode)
                    break
                except PermissionError:
                    # Try again since the file group might not have been set to the gpio group
                    # since there is a delay when the gpio channel is first exported
                    sleep(0.01)


    def __checkFilesystemValue__(self, channel):
        if not self.valueFile[channel]:
            #debug("value file %d not open" %channel)
            valRet = self.__checkFilesystemExport__(channel)
            if not valRet:
                return
            mode = 'w+'
            if (gpio_library or Hardware().isBeagleBone()) and os.geteuid() != 0:
                #On devices with root permissions on gpio files open the file in read mode from non-root process
                mode = 'r'
            for i in range(10):
                try:
                    self.valueFile[channel] = open(self.__getValueFilePath__(channel), mode)
                    break
                except PermissionError:
                    # Try again since the file group might not have been set to the gpio group
                    # since there is a delay when the gpio channel is first exported
                    sleep(0.01)

    def __digitalRead__(self, channel):
        try:
            self.__checkFilesystemValue__(channel)
            value = self.valueFile[channel].read(1)
            self.valueFile[channel].seek(0)
            if value[0] == '1':
                return self.HIGH
            else:
                return self.LOW
        except:
            return -1

    def __digitalWrite__(self, channel, value):
        self.__checkFilesystemValue__(channel)
        try:
            if value == 1:
                value = '1'
            else:
                value = '0'
            try:
                self.valueFile[channel].write(value)
                self.valueFile[channel].seek(0)
            except:
                command = 'sudo python3 -m myDevices.devices.writevalue -f {} -t {}'.format(self.__getValueFilePath__(channel), value)
                executeCommand(command)
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
            # If we haven't already set the channel function on an ASUS device, we use the GPIO 
            # library to get the function. Otherwise we just fall through and read the file itself
            # since we can assume the pin is a GPIO pin and reading the function file is quicker
            #  than launching a separate process.
            if gpio_library and channel not in self.pinFunctionSet:
                if os.geteuid() == 0:
                    value = gpio_library.gpio_function(channel)
                else:
                    value, err = executeCommand('sudo python3 -m myDevices.devices.readvalue -c {}'.format(channel))
                    return int(value.splitlines()[0])
                # If this is not a GPIO function return it, otherwise check the function file to see
                # if it is an IN or OUT pin since the ASUS library doesn't provide that info.
                if value != self.ASUS_GPIO:
                    return value
            function = self.functionFile[channel].read()
            self.functionFile[channel].seek(0)
            if function.startswith("out"):
                return self.OUT
            else:
                return self.IN
        except Exception as ex:
            error('Failed on __getFunction__: '+  str(channel) + ' ' + str(ex))
            return -1

    def __setFunction__(self, channel, value):
        self.__checkFilesystemFunction__(channel)
        self.checkDigitalChannelExported(channel)
        self.checkPostingFunctionAllowed()
        try:
            if value == self.IN:
                value = 'in'
            else:
                value = 'out'
            try:               
                self.functionFile[channel].write(value)
                self.functionFile[channel].seek(0)
            except:
                command = 'sudo python3 -m myDevices.devices.writevalue -f {} -t {}'.format(self.__getFunctionFilePath__(channel), value)
                executeCommand(command)
            self.pinFunctionSet.add(channel)
        except Exception as ex:
            exception('Failed on __setFunction__: ' + str(channel) + ' ' + str(ex))
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
        if gpio_library and os.geteuid() != 0:
            #If not root on an ASUS device get the pin states as root
            value, err = executeCommand('sudo python3 -m myDevices.devices.readvalue --pins')
            value = value.splitlines()[0]
            import json
            return json.loads(value)
        if compact:
            f = "f"
            v = "v"
        else:
            f = "function"
            v = "value"
        values = {}
        self.system_config = SystemConfig.getConfig()
        for i in self.pins + self.overlay_pins:
            if compact:
                func = self.getFunction(i)
            else:
                func = self.getFunctionString(i)
            values[i] = {f: func, v: int(self.__digitalRead__(i))}
        return values

    def getFunction(self, channel):
        return self.__getFunction__(channel)
    
    def getFunctionString(self, channel):
        f = -1
        function_string = 'UNKNOWN'
        functions = {0:'IN', 1:'OUT', 2:'ALT5', 3:'ALT4', 4:'ALT0', 5:'ALT1', 6:'ALT2', 7:'ALT3', 8:'PWM',
                    40:'SERIAL', 41:'SPI', 42:'I2C', 43:'PWM', 44:'GPIO', 45:'TS_XXXX', 46:'RESERVED', 47:'I2S'}
        try:
            f = self.getFunction(channel)
            function_string = functions[f]
        except:
            pass
        try:
            # On Raspberry Pis using the spi_bcm2835 driver SPI chip select is done via software rather than hardware
            # so the pin function is OUT instead of ALT0. Here we override that (and the I2C to be safe) so the GPIO map
            # in the UI will display the appropriate pin info.
            if channel in self.spi_pins and self.system_config['SPI'] == 1:
                function_string = functions[4]
            if channel in self.i2c_pins and self.system_config['I2C'] == 1:
                function_string = functions[4]
        except:
            pass
        try:
            # If 1-Wire is enabled specify the pin function as a device tree overlay.
            if channel in self.overlay_pins:
                function_string = 'OVERLAY'
        except:
            pass
        return function_string

    def setPinMapping(self):
        hardware = Hardware()
        if hardware.isTinkerBoard():
           self.MAPPING = [{'name': 'GPIO',
                            'map': [
                                {'power': 'V33'},
                                {'power': 'V50'},
                                {'gpio': 252},
                                {'power': 'V50'},
                                {'gpio': 253},
                                {'power': 'GND'},
                                {'gpio': 17},
                                {'gpio': 161},
                                {'power': 'GND'},
                                {'gpio': 160},
                                {'gpio': 164},
                                {'gpio': 184},
                                {'gpio': 166},
                                {'power': 'GND'},
                                {'gpio': 167},
                                {'gpio': 162},
                                {'power': 'V33'},
                                {'gpio': 163},
                                {'gpio': 257},
                                {'power': 'GND'},
                                {'gpio': 256},
                                {'gpio': 171},
                                {'gpio': 254},
                                {'gpio': 255},
                                {'power': 'GND'},
                                {'gpio': 251},
                                {'dnc': True},
                                {'dnc': True},
                                {'gpio': 165},
                                {'power': 'GND'},
                                {'gpio': 168},
                                {'gpio': 239},
                                {'gpio': 238},
                                {'power': 'GND'},
                                {'gpio': 185},
                                {'gpio': 223},
                                {'gpio': 224},
                                {'gpio': 187},
                                {'power': 'GND'},
                                {'gpio': 188}
                            ]}]
        elif hardware.isBeagleBone():
            self.MAPPING = [{'name': 'P9',
                            'map': [
                                {'power': 'GND'},
                                {'power': 'GND'},
                                {'power': 'V33'},
                                {'power': 'V33'},
                                {'power': 'V50'},
                                {'power': 'V50'},
                                {'power': 'V50'},
                                {'power': 'V50'},
                                {'power': 'PWR'},
                                {'power': 'RST'},
                                {'gpio': 30},
                                {'gpio': 60},
                                {'gpio': 31},
                                {'gpio': 50},
                                {'gpio': 48},
                                {'gpio': 51},
                                {'gpio': 5},
                                {'gpio': 4},
                                {'alt0': {'channel': 'sys:i2c:2', 'name': 'SCL'}},
                                {'alt0': {'channel': 'sys:i2c:2', 'name': 'SDA'}},
                                {'gpio': 3},
                                {'gpio': 2},
                                {'gpio': 49},
                                {'gpio': 15},
                                {'gpio': 117},
                                {'gpio': 14},
                                {'gpio': 115},
                                {'gpio': 113, 'alt0': {'channel': 'sys:spi:1', 'name': 'CS0'}},
                                {'gpio': 111, 'alt0': {'channel': 'sys:spi:1', 'name': 'D0'}},
                                {'gpio': 112, 'alt0': {'channel': 'sys:spi:1', 'name': 'D1'}},
                                {'gpio': 110, 'alt0': {'channel': 'sys:spi:1', 'name': 'SCLK'}},
                                {'power': 'VDD_ADC'},
                                {'analog': 4},
                                {'power': 'GNDA_ADC'},
                                {'analog': 6},
                                {'analog': 5},
                                {'analog': 2},
                                {'analog': 3},
                                {'analog': 0},
                                {'analog': 1},
                                {'gpio': 20},
                                {'gpio': 7},
                                {'power': 'GND'},
                                {'power': 'GND'},
                                {'power': 'GND'},
                                {'power': 'GND'}]},
                            {'name': 'P8',
                            'map': [
                                {'power': 'GND'},
                                {'power': 'GND'},
                                {'gpio': 38},
                                {'gpio': 39},
                                {'gpio': 34},
                                {'gpio': 35},
                                {'gpio': 66},
                                {'gpio': 67},
                                {'gpio': 69},
                                {'gpio': 68},
                                {'gpio': 45},
                                {'gpio': 44},
                                {'gpio': 23},
                                {'gpio': 26},
                                {'gpio': 47},
                                {'gpio': 46},
                                {'gpio': 27},
                                {'gpio': 65},
                                {'gpio': 22},
                                {'gpio': 63},
                                {'gpio': 62},
                                {'gpio': 37},
                                {'gpio': 36},
                                {'gpio': 33},
                                {'gpio': 32},
                                {'gpio': 61},
                                {'gpio': 86},
                                {'gpio': 88},
                                {'gpio': 87},
                                {'gpio': 89},
                                {'gpio': 10},
                                {'gpio': 11},
                                {'gpio': 9},
                                {'gpio': 81},
                                {'gpio': 8},
                                {'gpio': 80},
                                {'gpio': 78},
                                {'gpio': 79},
                                {'gpio': 76},
                                {'gpio': 77},
                                {'gpio': 74},
                                {'gpio': 75},
                                {'gpio': 72},
                                {'gpio': 73},
                                {'gpio': 70},
                                {'gpio': 71}
                            ]}]
        else:
            if BOARD_REVISION == 1: 
                self.MAPPING = [{'name': 'P1',
                                'map': [
                                    {'power': 'V33'},
                                    {'power': 'V50'},
                                    {'gpio': 0, 'alt0': {'channel': 'sys:i2c', 'name': 'SDA'}},
                                    {'power': 'V50'},
                                    {'gpio': 1, 'alt0': {'channel': 'sys:i2c', 'name': 'SCL'}},
                                    {'power': 'GND'},
                                    {'gpio': 4, 'overlay': {'channel': 'sys:1wire', 'name': 'DATA'}},
                                    {'gpio': 14, 'alt0': {'channel': 'sys:uart', 'name': 'TX'}},
                                    {'power': 'GND'},
                                    {'gpio': 15, 'alt0': {'channel': 'sys:uart', 'name': 'RX'}},
                                    {'gpio': 17},
                                    {'gpio': 18},
                                    {'gpio': 21},
                                    {'power': 'GND'},
                                    {'gpio': 22},
                                    {'gpio': 23},
                                    {'power': 'V33'},
                                    {'gpio': 24},
                                    {'gpio': 10, 'alt0': {'channel': 'sys:spi', 'name': 'MOSI'}},
                                    {'power': 'GND'},
                                    {'gpio': 9, 'alt0': {'channel': 'sys:spi', 'name': 'MISO'}},
                                    {'gpio': 25},
                                    {'gpio': 11, 'alt0': {'channel': 'sys:spi', 'name': 'SCLK'}},
                                    {'gpio': 8, 'alt0': {'channel': 'sys:spi', 'name': 'CE0'}},
                                    {'power': 'GND'},
                                    {'gpio': 7, 'alt0': {'channel': 'sys:spi', 'name': 'CE1'}}
                                ]}]
            elif BOARD_REVISION == 2:
                self.MAPPING = [{'name': 'P1',
                                'map': [
                                    {'power': 'V33'},
                                    {'power': 'V50'},
                                    {'gpio': 2, 'alt0': {'channel': 'sys:i2c', 'name': 'SDA'}},
                                    {'power': 'V50'},
                                    {'gpio': 3, 'alt0': {'channel': 'sys:i2c', 'name': 'SCL'}},
                                    {'power': 'GND'},
                                    {'gpio': 4, 'overlay': {'channel': 'sys:1wire', 'name': 'DATA'}},
                                    {'gpio': 14, 'alt0': {'channel': 'sys:uart', 'name': 'TX'}},
                                    {'power': 'GND'},
                                    {'gpio': 15, 'alt0': {'channel': 'sys:uart', 'name': 'RX'}},
                                    {'gpio': 17},
                                    {'gpio': 18},
                                    {'gpio': 27},
                                    {'power': 'GND'},
                                    {'gpio': 22},
                                    {'gpio': 23},
                                    {'power': 'V33'},
                                    {'gpio': 24},
                                    {'gpio': 10, 'alt0': {'channel': 'sys:spi', 'name': 'MOSI'}},
                                    {'power': 'GND'},
                                    {'gpio': 9, 'alt0': {'channel': 'sys:spi', 'name': 'MISO'}},
                                    {'gpio': 25},
                                    {'gpio': 11, 'alt0': {'channel': 'sys:spi', 'name': 'SCLK'}},
                                    {'gpio': 8, 'alt0': {'channel': 'sys:spi', 'name': 'CE0'}},
                                    {'power': 'GND'},
                                    {'gpio': 7, 'alt0': {'channel': 'sys:spi', 'name': 'CE1'}}
                                ]}]
            elif BOARD_REVISION == 3:
                self.MAPPING = [{'name': 'P1',
                                'map': [
                                    {'power': 'V33'},
                                    {'power': 'V50'},
                                    {'gpio': 2, 'alt0': {'channel': 'sys:i2c', 'name': 'SDA'}},
                                    {'power': 'V50'},
                                    {'gpio': 3, 'alt0': {'channel': 'sys:i2c', 'name': 'SCL'}},
                                    {'power': 'GND'},
                                    {'gpio': 4, 'overlay': {'channel': 'sys:1wire', 'name': 'DATA'}},
                                    {'gpio': 14, 'alt0': {'channel': 'sys:uart', 'name': 'TX'}},
                                    {'power': 'GND'},
                                    {'gpio': 15, 'alt0': {'channel': 'sys:uart', 'name': 'RX'}},
                                    {'gpio': 17},
                                    {'gpio': 18},
                                    {'gpio': 27},
                                    {'power': 'GND'},
                                    {'gpio': 22},
                                    {'gpio': 23},
                                    {'power': 'V33'},
                                    {'gpio': 24},
                                    {'gpio': 10, 'alt0': {'channel': 'sys:spi', 'name': 'MOSI'}},
                                    {'power': 'GND'},
                                    {'gpio': 9, 'alt0': {'channel': 'sys:spi', 'name': 'MISO'}},
                                    {'gpio': 25},
                                    {'gpio': 11, 'alt0': {'channel': 'sys:spi', 'name': 'SCLK'}},
                                    {'gpio': 8, 'alt0': {'channel': 'sys:spi', 'name': 'CE0'}},
                                    {'power': 'GND'},
                                    {'gpio': 7, 'alt0': {'channel': 'sys:spi', 'name': 'CE1'}},
                                    {'dnc': True},
                                    {'dnc': True},
                                    {'gpio': 5},
                                    {'power': 'GND'},
                                    {'gpio': 6},
                                    {'gpio': 12},
                                    {'gpio': 13},
                                    {'power': 'GND'},
                                    {'gpio': 19},
                                    {'gpio': 16},
                                    {'gpio': 26},
                                    {'gpio': 20},
                                    {'power': 'GND'},
                                    {'gpio': 21}
                                ]}]
        if isinstance(self.MAPPING, list):
            self.pins = []
            self.overlay_pins = []
            self.spi_pins = []
            self.i2c_pins = []
            self.system_config = SystemConfig.getConfig()
            for header in self.MAPPING:
                self.pins.extend([pin['gpio'] for pin in header['map'] if 'gpio' in pin])
            try:
                if Hardware().isRaspberryPi():
                    if self.system_config['OneWire'] == 1:
                        self.overlay_pins.extend([pin['gpio'] for pin in header['map'] if 'overlay' in pin and pin['overlay']['channel'] == 'sys:1wire'])
                        self.pins = [pin for pin in self.pins if pin not in self.overlay_pins]
                    self.spi_pins.extend([pin['gpio'] for pin in header['map'] if 'alt0' in pin and pin['alt0']['channel'] == 'sys:spi'])
                    self.i2c_pins.extend([pin['gpio'] for pin in header['map'] if 'alt0' in pin and pin['alt0']['channel'] == 'sys:i2c'])
            except:
                pass
