from logging import Formatter, getLogger, StreamHandler, WARN, INFO, DEBUG
from logging.handlers import TimedRotatingFileHandler,MemoryHandler, RotatingFileHandler
from inspect import getouterframes, currentframe, getargvalues
from traceback import extract_stack
import tarfile
from os import path, getpid, remove
from datetime import datetime
from hashlib import sha256
import time
from myDevices.os.threadpool import ThreadPool
from glob import iglob

MAX_JSON_ITEMS_PER_CATEGORY = 100
JSON_FILE_LOGGER = '/var/log/myDevices/JSONData'
JSON_FILE_DUMP_TIME = 60
FLOOD_INTERVAL_DROP = 60
FLOOD_LOGGING_COUNT = 10
LOG_FORMATTER = Formatter(fmt='%(asctime)s - %(name)s - %(levelname)s - %(message)s', datefmt="%Y-%m-%d %H:%M:%S")
LOGGER = getLogger("myDevices")
LOGGER.setLevel(WARN)

CONSOLE_HANDLER = StreamHandler()
CONSOLE_HANDLER.setFormatter(LOG_FORMATTER)
LOGGER.addHandler(CONSOLE_HANDLER)

jsonData = {}
messageFrequence={}
#this code disables logger
#LOGGER.propagate = False

def namer(name):
    return name + ".bz2"

def rotator(source, dest):
    try:
        # print('Log rotator, pid:' + str(getpid()))
        size=path.getsize(source)
        if size > 100000000:
            # files larger than 100MB will be deleted
            remove(source)
        else:
            tar = tarfile.open(dest, "w:bz2")
            tar.add(source)
            tar.close()
            remove(source)
        # Remove old myDevices.log backups if they are older than a week. This code can be removed
        # in later versions if myDevices.log files have been replaced with cayenne.log.
        for old_file in iglob('/var/log/myDevices/myDevices.log*'):
            if path.getmtime(old_file) + 604800 < time.time(): 
                remove(old_file)
    except Exception as ex:
        print('Log rotator failed with: ' +str(ex))

def rotatorJsonMp():
    try:
        debug('rotatorJsonMp called')
        global jsonData
        output = open(JSON_FILE_LOGGER, 'w')
        for key in jsonData.keys():
            for message in jsonData[key]:
                output.write(message)
        output.close()
    except:
        exception('rotatorJsonMp exception')
        return 1
    return 0

lastRotate=datetime(1970, 1, 1)
def rotatorJson():
    try:
        global lastRotate
        if (datetime.now() - lastRotate).total_seconds() < JSON_FILE_DUMP_TIME:
            return
        debug('rotatorJson called')
        lastRotate = datetime.now()
        ThreadPool.Submit(rotatorJsonMp)
    except:
        exception('rotatorJson exception')

def setInfo():
    LOGGER.setLevel(INFO)
    return
    
def setDebug():
    LOGGER.setLevel(DEBUG)
    return
    
def debugEnabled():
    return LOGGER.level == DEBUG
    
def logToFile(filename=None):
    if not filename:
        filename = '/var/log/myDevices/cayenne.log'
    handler = TimedRotatingFileHandler(filename, when="midnight", interval=1, backupCount=7)
    handler.setFormatter(LOG_FORMATTER)
    handler.rotator=rotator
    handler.namer=namer
    LOGGER.addHandler(handler)

def debug(message):
    outerFrame = getouterframes(currentframe())[1][0]
    (args, _, _, values) = getargvalues(outerFrame)
    argsValue = ''
    
    for i in args:
        if i is 'self':
            continue
        argsValue += "(%s=%s)" % (i, str(values[i]))
    
    stack = extract_stack()
    (filename, line, procname, text) = stack[-2]
    LOGGER.debug(str(filename) + ' ' + str(procname) + str(argsValue) + ':' + str(line) + '> '  + str(message))

def checkFlood(message):
    try:
        # Remove old saved keys to prevent excess memory usage
        remove = [key for key, value in messageFrequence.items() if (time.time() - value['Last']) > FLOOD_INTERVAL_DROP]
        for key in remove:
            messageFrequence.pop(key, None)
        sha_key=sha256(str(message).encode('utf8')).hexdigest()
        if sha_key in messageFrequence:
            if messageFrequence[sha_key]['Count'] > FLOOD_LOGGING_COUNT:
                if time.time() - messageFrequence[sha_key]['Last'] < FLOOD_INTERVAL_DROP:
                    return True
                else:
                    messageFrequence[sha_key]['Count'] = 0
            messageFrequence[sha_key]['Count'] += 1
            messageFrequence[sha_key]['Last'] = int(time.time())
        else:
            messageFrequence[sha_key] = {'Count': 1, 'Last': int(time.time())}
    except Exception as ex:
        print('logger message flood failed:' + str(ex))
    return False

def info(message):
    # if checkFlood(message):
    #     return
    LOGGER.info(message)

def warn(message):
    if checkFlood(message):
        return
    LOGGER.warn(message)

def error(message, *args, **kwargs):
    if checkFlood(message):
        return
    LOGGER.error(message, *args, **kwargs)

def exception(message):
    if checkFlood(message):
        return
    LOGGER.exception(message)

def logJson(message, category = ''):
    if debugEnabled() == False:
        return
    if checkFlood(message):
        return
    try:
        if category not in jsonData:
            jsonData[category] = []
        if len(jsonData[category]) > MAX_JSON_ITEMS_PER_CATEGORY:
            del jsonData[category][0]
        #2016-03-23 03:53:16 - myDevices - INFO -
        message = str(datetime.today()) + ' - myDevices - INFO - ' + message
        jsonData[category].append(message)
        rotatorJson()
    except Exception as ex:
        exception("logJson failed")

def printBytes(buff):
    for i in range(0, len(buff)):
        print("%03d: 0x%02X %03d %c" % (i, buff[i], buff[i], buff[i]))
        
