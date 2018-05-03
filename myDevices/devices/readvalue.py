"""
This script reads GPIO info. It is intended to be launched via sudo in order to 
read data from files that require root access so the main agent code can run from
a non-root process and only elevate to root when necessary.
"""
import sys
# from myDevices.utils.logger import setInfo, info, error, logToFile
from myDevices.devices.digital.gpio import NativeGPIO

if __name__ == '__main__':
    # Read data using script so it can be called via sudo, sends the data to the main process by writing to stdout
    # setInfo()
    # logToFile()
    i = 1
    while i < len(sys.argv):
        if sys.argv[i] in ['-p', '--pins']:
            import json
            gpio = NativeGPIO()
            print(json.dumps(gpio.wildcard()))
        if sys.argv[i] in ['-c', '--channel']:
            gpio = NativeGPIO()
            i += 1
            channel = int(sys.argv[i])
            print(gpio.getFunction(channel))
        i += 1
