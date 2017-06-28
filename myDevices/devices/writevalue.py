import sys
from myDevices.utils.logger import setInfo, info, error, logToFile

if __name__ == '__main__':
    # Write value to file in script so it can be called via sudo
    setInfo()
    logToFile()
    filepath = None
    mode = 'w'
    value = None
    i = 1
    while i < len(sys.argv):
        if sys.argv[i] in ["-f", "-F", "--file"]:
            filepath = sys.argv[i + 1]
            i += 1
        elif sys.argv[i] in ["-t", "-T", "--text"]:
            value = sys.argv[i + 1]
            i += 1
        elif sys.argv[i] in ["-b", "-B", "--bytearray"]:
            value = bytearray([int(sys.argv[i + 1])])
            mode = 'wb'
            i += 1
        i += 1
    try:
        info('Write value {} to {}'.format(value, filepath))
        with open(filepath, mode) as out_file:
            out_file.write(value)
    except Exception as ex:
        error('Error writing value {}'.format(ex))

