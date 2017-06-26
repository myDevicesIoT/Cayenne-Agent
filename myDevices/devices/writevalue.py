import sys
from myDevices.utils.logger import setInfo, info, error, logToFile

if __name__ == '__main__':
    # Write value to file in script so it can be called via sudo
    setInfo()
    logToFile()
    write_bytearray = False
    filepath = None
    mode = 'w'
    value = None
    i = 1
    while i < len(sys.argv):
        if sys.argv[i] in ["-f", "-F", "--file"]:
            filepath = sys.argv[i + 1]
            i += 1
        elif sys.argv[i] in ["-v", "-V", "--value"]:
            value = sys.argv[i + 1]
            i += 1
        elif sys.argv[i] in ["-b", "-B", "--bytearray"]:
            write_bytearray = True
            mode = 'wb'
        i += 1
    try:
        info('Write value {} to {}'.format(value, filepath))
        with open(filepath, mode) as out_file:
            if write_bytearray:
                out_file.write(bytearray([int(value)]))
            else:
                out_file.write(value)
    except Exception as ex:
        error('Error writing value {}'.format(ex))

