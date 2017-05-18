import sys
from myDevices.utils.logger import setInfo, info, error, logToFile

if __name__ == '__main__':
    # Write value to file in script so it can be called via sudo
    setInfo()
    logToFile()
    try:
        info('Write value {} to {}'.format(sys.argv[2], sys.argv[1]))
        with open(sys.argv[1], "wb") as out_file:
            out_file.write(bytearray([int(sys.argv[2])]))
    except Exception as ex:
        error('Error writing value {}'.format(ex))

