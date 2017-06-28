import sys
from myDevices.utils.logger import setInfo, info, error, logToFile
from myDevices.devices.digital.gpio import NativeGPIO

if __name__ == '__main__':
    # Read data using script so it can be called via sudo
    setInfo()
    logToFile()
    i = 1
    while i < len(sys.argv):
        if sys.argv[i] in ['-p', '--pins']:
            import json
            gpio = NativeGPIO()
            print(json.dumps(gpio.wildcard()))
        if sys.argv[i] in ['-c', '--channel']:
            import json
            gpio = NativeGPIO()
            i += 1
            channel = int(sys.argv[i])
            print(gpio.getFunction(channel))
        i += 1
