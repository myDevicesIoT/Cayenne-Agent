from ctypes import CDLL,c_char_p
from myDevices.utils.logger import exception, info, warn, error, debug, logJson
from os import path, getpid
from json import loads, dumps
from psutil import virtual_memory

def getSystemInformation():
        currentSystemInfo = "{}"
        try:
            debug('Child process for systeminformation pid:' + str(getpid()))
            libSystemInformation=CDLL("/etc/myDevices/libs/libSystemInformation.so")
            if libSystemInformation:
                libSystemInformation.GetSystemInformation.restype=c_char_p
                currentSystemInfo = libSystemInformation.GetSystemInformation().decode('utf-8')
                libSystemInformation.FreeSystemInformation()
                del libSystemInformation
                libSystemInformation = None
                memory = virtual_memory()
                try:
                    system_info = loads(currentSystemInfo)
                    system_info['Memory']['free'] = memory.available
                    system_info['Memory']['used'] = system_info['Memory']['total'] - memory.available
                    currentSystemInfo = dumps(system_info)
                except:
                    pass
        except Exception as ex:
            exception('getSystemInformation failed to retrieve: ' + str(ex))
        finally:
            return currentSystemInfo