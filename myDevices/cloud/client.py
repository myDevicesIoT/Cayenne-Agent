from socket import SOCK_STREAM, socket, AF_INET, gethostname, SHUT_RDWR
from ssl import CERT_REQUIRED, wrap_socket
from json import dumps, loads
from socket import error as socket_error
from threading import Thread, RLock
from time import strftime, localtime, tzset, time, sleep
from queue import Queue, Empty
from enum import Enum, unique
from ctypes import CDLL, CFUNCTYPE, create_string_buffer, c_char_p, c_bool, c_int, c_void_p
from myDevices.utils.config import Config
import myDevices.ipgetter
from myDevices.utils.logger import exception, info, warn, error, debug, logJson
from myDevices.os import services
from myDevices.sensors import sensors
from myDevices.os.hardware import Hardware
from myDevices.wifi import WifiManager
from myDevices.cloud.scheduler import SchedulerEngine
from myDevices.cloud.download_speed import DownloadSpeed
from myDevices.cloud.updater import Updater
from myDevices.os.raspiconfig import RaspiConfig
from myDevices.os.daemon import Daemon
from myDevices.os.threadpool import ThreadPool
from myDevices.utils.history import History
from select import select
from hashlib import sha256
from resource import getrusage, RUSAGE_SELF
from myDevices.cloud.apiclient import CayenneApiClient

@unique
class PacketTypes(Enum):
    PT_ACK= 0
    PT_START_COLLECTION= 1
    PT_STOP_COLLECTION= 2
    PT_UTILIZATION= 3
    PT_SYSTEM_INFO= 4
    PT_PROCESS_LIST= 5
    PT_DRIVE_LIST= 6
    PT_DEFRAG_ANALYSIS= 7
    PT_STARTUP_APPLICATIONS= 8
    PT_DEFRAG_DRIVE= 9
    PT_DEFRAG_COMPLETED= 10
    PT_START_RDS= 11
    PT_STOP_RDS= 12
    PT_START_SCAN= 13
    PT_CHECK_SCAN= 14
    PT_STOP_SCAN= 15
    PT_START_FIX= 16
    PT_CHECK_FIX= 17
    PT_STOP_FIX= 18
    PT_SCAN_RESPONSE= 19
    PT_FIX_RESPONSE= 20
    PT_END_SCAN= 21
    PT_DEFRAG_CHECK= 22
    PT_DEVICE_INFO_MOBILE= 23
    PT_LOCK_DESKTOP= 24
    PT_RESTART_COMPUTER= 25
    PT_SHUTDOWN_COMPUTER= 26
    PT_KILL_PROCESS= 27
    PT_CMD_NOTIFY= 28
    PT_PRINTER_INFO= 29
    PT_PRINT_TEST_PAGE= 30
    PT_ENABLE_FIREWALL= 31
    PT_WINDOWS_UPDATES= 32
    PT_LAUNCH_TASKMGR= 33
    PT_MALWARE_SCAN= 34
    PT_CANCEL_MALWARE_SCAN= 35
    PT_START_RDS_LOCAL_INIT= 36
    PT_MALWARE_GET_ITEMS= 37
    PT_MALWARE_DELETE_ITEMS= 38
    PT_MALWARE_RESTORE_ITEMS= 39
    PT_REQUEST_SCHEDULES= 40
    PT_UPDATE_SCHEDULES= 41
    PT_MALWARE_THREAT_DETECTED= 42
    PT_TOGGLE_MALWARE_SCANNER= 43
    PT_MALWARE_SCANNER_STATE= 44
    PT_AGENT_MESSAGE= 45
    PT_DRIVE_ANALYSIS= 46
    PT_FILE_TRANSFER= 47
    PT_PRINT_JOBS= 48
    PT_DISPLAY_WEB_PAGE= 49
    PT_PRODUCT_INFO= 50
    PT_UNINSTALL_AGENT= 51
    PT_ASK_RDS_CONTROL= 52
    PT_ANS_RDS_CONTROL= 53
    PT_REMOTE_CONTROL_ENDED= 54
    PT_STOP_RD_INVITE= 55
    PT_CLOSE_SALSA_CONNECTION= 56
    PT_INITIALIZED= 57
    PT_LOCATION = 58
    PT_SUPPORTED_SENSORS = 59
    PT_MACHINE_SENSORS  = 60
    PT_ADD_SENSOR = 61
    PT_REMOVE_SENSOR = 62
    PT_UPDATE_SENSOR = 63
    PT_DEVICE_COMMAND = 64
    PT_DEVICE_COMMAND_RESPONSE = 65
    PT_ADD_SCHEDULE = 66
    PT_REMOVE_SCHEDULE = 67
    PT_GET_SCHEDULES = 68
    PT_NOTIFICATION = 69
    PT_DATA_CHANGED = 70
    PT_HISTORY_DATA = 71
    PT_HISTORY_DATA_RESPONSE = 72
    PT_DISCOVERY = 73
    PT_AGENT_CONFIGURATION = 74


NETWORK_SETTINGS='/etc/myDevices/Network.ini'
APP_SETTINGS='/etc/myDevices/AppSettings.ini'
GENERAL_SLEEP_THREAD=0.20#was 0.05



# from contextlib import contextmanager
#
# @contextmanager
#import sys
# def stdout_redirector(stream):
#     old_stdout = sys.stdout
#     sys.stdout = stream
#     try:
#         yield
#     finally:
#         sys.stdout = old_stdout
        #with open(filepathdebug, "w+") as f: #replace filepath & filename
        #    with stdout_redirector(f):
                #tracker.print_diff()
                #countDebug=countDebug+1
                #print(str(datetime.now()) + ' Count: ' + str(countDebug))

# debugCount=0
# try:
#     import resource
#     import gc
#     gc.enable()
#     from objgraph import *
#     import random
#     from datetime import datetime
#
#     #from pympler.tracker import SummaryTracker
#     #tracker = SummaryTracker()
# except Exception as e:
#     error('failed to load debug modules: ' + str(e))
debugCount=0
def Debug():
    try:
        global debugCount
        debugCount = debugCount + 1
        resUsage=getrusage(RUSAGE_SELF)
        size=resUsage.ru_maxrss
        info("Memory usage : " + str(debugCount) + " size: " + str(size))
        info("Resouce usage info: " + str(resUsage))
        # Memory leaks display currently commented out
        # show_growth()
        # obj=get_leaking_objects()
        # warn('Leaking objects size='+str(len(obj)))
        # filepathdebug='/var/log/myDebug'+str(debugCount)
        # with open(filepathdebug, "w+") as f: #replace filepath & filename
        #     f.write('Debug resouce iteration: ' + str(debugCount) + " size: " + str(size))
        #     f.write('Leaking objects size='+str(len(obj)) + '\n')
        #     f.write('Leaking objects size='+str(typestats()) + '\n')
        #     f.write('Leaking objects'+str(obj) + '\n')
    except Exception as e:
        error('failed to track memory: ' + str(e))

def GetTime():
    tzset()
    cur=time()
    val=strftime("%Y-%m-%dT%T", localtime(cur))
    timezone=strftime("%z", localtime(cur))
    hourtime=int(timezone[1:3])
    timezone=timezone[:1] + str(int(timezone[1:3]))+':'+ timezone[3:7]
    if hourtime == 0:
        timezone=''      
    return val + timezone

class OSInfo(Thread):
    def __init__(self):
        #debug("OS Info init")
        try:
            sleep(GENERAL_SLEEP_THREAD)
            f = open('/etc/os-release','r')
            for line in f:
                splitLine =  line.split('=')
                if len(splitLine) < 2:
                    continue
                key = splitLine[0].strip()
                value = splitLine[1].strip().replace('"', '')
                if key=='PRETTY_NAME':
                    self.PRETTY_NAME = value
                    continue
                if key=='NAME':
                    self.NAME = value
                    continue
                if key=='VERSION_ID':
                    self.VERSION_ID = value
                    continue
                if key=='VERSION':
                    self.VERSION = value
                    continue
                if key=='ID_LIKE':
                    self.ID_LIKE = value
                    continue
                if key=='ID':
                    self.ID = value
                    continue
                if key=='ANSI_COLOR':
                    self.ANSI_COLOR = value
                    continue
                if key=='HOME_URL':
                    self.HOME_URL = value
                    continue
            f.close()
        except: 
            exception ("OSInfo Unexpected error")
#READER THREAD
class ReaderThread(Thread):
    def __init__(self, name, client):
        debug('ReaderThread init')
        Thread.__init__(self, name=name)
        self.cloudClient = client
        self.Continue = True
    def run(self):
        debug('ReaderThread run')
        debug('ReaderThread continue?:' + str(self.Continue) )
        while self.Continue:
            try:
                sleep(GENERAL_SLEEP_THREAD)
                if self.cloudClient.connected == False:
                    continue
                #debug('ReaderThread - Reading message')
                #self.cloudClient.mutex.acquire()
                bReturned = self.cloudClient.ReadMessage()
                # if bReturned:
                #    #debug('ReaderThread process message')
                #    t1 = Thread(target=self.cloudClient.ProcessMessage)
                #    t1.start()
            except:
                exception ("ReaderThread Unexpected error") 
        return
    def stop(self):
        debug('ReaderThread stop')
        self.Continue = False
class ProcessorThread(Thread):
    def __init__(self, name, client):
        debug('ProcessorThread init')
        Thread.__init__(self, name=name)
        self.cloudClient = client
        self.Continue = True
    def run(self):
        debug('ProcessorThread run')
        debug('ProcessorThread continue?:' + str(self.Continue) )
        while self.Continue:
            try:
                sleep(GENERAL_SLEEP_THREAD)
                self.cloudClient.ProcessMessage()
            except:
                exception ("ProcessorThread Unexpected error") 
        return
    def stop(self):
        debug('ProcessorThread stop')
        self.Continue = False
#WRITER THREAD
class WriterThread(Thread):
    def __init__(self, name, client):
        debug('WriterThread init')
        Thread.__init__(self, name=name)
        self.cloudClient = client
        self.Continue = True
    def run(self):
        debug('WriterThread run')
        while self.Continue:
            sleep(GENERAL_SLEEP_THREAD)
            try:
                if self.cloudClient.connected == False:
                    continue
                message = self.cloudClient.DequeuePacket()
                if not message:
                    continue
                self.cloudClient.SendMessage(message)
                del message
                message = None
            except:
                exception ("WriterThread Unexpected error") 
        return
    def stop(self):
        debug('WriterThread stop')
        self.Continue = False

#Run function at timed intervals
class TimerThread(Thread):
    def __init__(self, function, interval, initial_delay=0):
        Thread.__init__(self)
        self.setDaemon(True)
        self.function = function
        self.interval = interval
        self.initial_delay = initial_delay
        self.start()
    def run(self):
        sleep(self.initial_delay)
        while True:
            try:
                self.function()
                sleep(self.interval + GENERAL_SLEEP_THREAD)
            except:
                exception("TimerThread Unexpected error") 
        
class CloudServerClient:
    def __init__(self, host, port, cayenneApiHost):
        self.HOST = host
        self.PORT = port
        self.CayenneApiHost = cayenneApiHost
        self.onMessageReceived = None
        self.onMessageSent = None
        self.initialized = False
        self.machineName = gethostname()
        self.config = Config(APP_SETTINGS)
        inviteCode = self.config.get('Agent', 'InviteCode', fallback=None)
        if not inviteCode:
            error('No invite code found in {}'.format(APP_SETTINGS))
            print('Please input an invite code. This can be retrieved from the Cayenne dashboard by adding a new Raspberry Pi device.\n'
                  'The invite code will be part of the script name shown there: rpi_[invitecode].sh.')
            inviteCode = input('Invite code: ')
            if inviteCode:
                self.config.set('Agent', 'InviteCode', inviteCode)
            else:
                print('No invite code set, exiting.')
                quit()
        self.installDate=None
        try:
            self.installDate = self.config.get('Agent', 'InstallDate', fallback=None)
        except:
            pass
        if not self.installDate:
            self.installDate = int(time())
            self.config.set('Agent', 'InstallDate', self.installDate)
        self.networkConfig = Config(NETWORK_SETTINGS)
        #self.defaultRDServer = self.networkConfig.get('CONFIG','RemoteDesktopServerAddress')
        self.schedulerEngine = SchedulerEngine(self, 'client_scheduler')
        self.Initialize()
        self.CheckSubscription()
        self.FirstRun()
        self.updater = Updater(self.config, self.OnUpdateConfig)
        self.updater.start()
        self.initialized = True

    def __del__(self):
        self.Destroy()
    def OnUpdateConfig(self):
        pass
        # info('Requesting PT_AGENT_CONFIGURATION ')
        # data = {}
        # data['MachineName'] = self.MachineId
        # data['Timestamp'] = int(time())
        # data['Platform'] = 1  # raspberrypi platform id is 1
        # data['PacketType'] = PacketTypes.PT_AGENT_CONFIGURATION.value
        # self.EnqueuePacket(data)
    def Initialize(self):
        #debug('CloudServerClient init')
        try:
            self.mutex = RLock()
            self.readQueue = Queue()
            self.writeQueue = Queue()
            self.pingRate = 10
            self.pingTimeout = 35
            self.waitPing = 0
            self.lastPing = time()-self.pingRate - 1
            self.PublicIP = myDevices.ipgetter.myip()
            self.hardware = Hardware()
            self.oSInfo = OSInfo()
            self.downloadSpeed = DownloadSpeed(self.config)
            self.MachineId = None
            self.connected = False
            self.exiting = False
            self.Start
            self.count = 10000
            self.buff = bytearray(self.count)
            #start thread only after init of other fields
            self.sensorsClient = sensors.SensorsClient()
            self.sensorsClient.SetDataChanged(self.OnDataChanged, self.BuildPT_SYSTEM_INFO)
            self.processManager=services.ProcessManager()
            self.serviceManager=services.ServiceManager()
            self.wifiManager = WifiManager.WifiManager()
            self.writerThread = WriterThread('writer',self)
            self.writerThread.start()
            self.readerThread = ReaderThread('reader',self)
            self.readerThread.start()
            self.processorThread = ProcessorThread('processor', self)
            self.processorThread.start()
            #TimerThread(self.RequestSchedules, 600, 10)
            TimerThread(self.CheckConnectionAndPing, self.pingRate)
            self.sentHistoryData = {}
            self.historySendFails = 0
            self.historyThread = Thread(target=self.SendHistoryData)
            self.historyThread.setDaemon(True)
            self.historyThread.start()
        except Exception as e:
            exception('Initialize error: ' + str(e))
    def Destroy(self):
        info('Shutting down client')
        self.exiting = True
        self.sensorsClient.StopMonitoring()
        if hasattr(self, 'schedulerEngine'):
            self.schedulerEngine.stop()
        if hasattr(self, 'updater'):
            self.updater.stop()
        if hasattr(self, 'writerThread'):
            self.writerThread.stop()
        if hasattr(self, 'readerThread'):
            self.readerThread.stop()
        if hasattr(self, 'processorThread'):
            self.processorThread.stop()
        ThreadPool.Shutdown()
        self.Stop()
        info('Client shut down')
    # def Test(self):
    #     message = {}
    #     message['PacketType'] = PacketTypes.PT_DEVICE_COMMAND.value
    #     message['Type'] = ''
    #     message['Service'] = 'config'
    #     message['Id']=1021
    #     parameters = {}
    #     parameters['id'] = 16
    #     parameters['arguments'] = 'Asia/Tokyo'
    #     message['Parameters'] = parameters
    #     self.ExecuteMessage(message)
    #     message = {}
    #     message['PacketType'] = PacketTypes.PT_DEVICE_COMMAND.value
    #     message['Type'] = ''
    #     message['Service'] = 'config'
    #     message['Id']=1021
    #     parameters = {}
    #     parameters['id'] = 15
    #     parameters['arguments'] = ''
    #     message['Parameters'] = parameters
    #     self.ExecuteMessage(message)
    #     message = {}
    #     message['PacketType'] = PacketTypes.PT_DEVICE_COMMAND.value
    #     message['Type'] = ''
    #     message['Service'] = 'config'
    #     message['Id']=1021
    #     parameters = {}
    #     parameters['id'] = 0
    #     parameters['arguments'] = 'test'
    #     message['Parameters'] = parameters
    #     self.ExecuteMessage(message)
    def FirstRun(self):
        # self.BuildPT_LOCATION()
        self.BuildPT_SYSTEM_INFO()
        # data = {}
        # data['MachineName'] = self.MachineId
        # data['Timestamp'] = int(time())
        # data['PacketType'] = PacketTypes.PT_UTILIZATION.value
        # self.processManager.RefreshProcessManager()
        # data['VisibleMemory'] = 1000000
        # data['AvailableMemory'] = 100000
        # data['AverageProcessorUsage'] = 20
        # data['PeakProcessorUsage'] = 98
        # data['AverageMemoryUsage'] = 30
        # data['PeakMemoryUsage'] = 99
        # data['PercentProcessorTime'] = 80
        # self.EnqueuePacket(data)
        # data['PacketType'] = PacketTypes.PT_PROCESS_LIST.value
        # self.EnqueuePacket(data)
        # data['PacketType'] = PacketTypes.PT_DRIVE_LIST.value
        # self.EnqueuePacket(data)
        # data['PacketType'] = PacketTypes.PT_PRINTER_INFO.value
        # self.EnqueuePacket(data)
        self.RequestSchedules()
        # self.BuildPT_LOCATION()
        self.OnUpdateConfig()
    def BuildPT_LOCATION(self):
        data = {}
        data['position'] = {}
        data['position']['latitude'] = '30.022112'
        data['position']['longitude'] = '45.022112'
        data['position']['accuracy'] = '20'
        data['position']['method'] = 'Windows location provider'
        data['provider'] = 'other'
        data['time'] = int(time())
        data['PacketType'] = PacketTypes.PT_LOCATION.value
        data['MachineName'] = self.MachineId
        self.EnqueuePacket(data)
    def BuildPT_UTILIZATION(self):
        #debug('BuildPT_UTILIZATION')
        data = {}
        data['MachineName'] = self.MachineId
        data['Timestamp'] = int(time())
        data['PacketType'] = PacketTypes.PT_UTILIZATION.value
        self.processManager.RefreshProcessManager()
        data['VisibleMemory'] = self.processManager.VisibleMemory
        data['AvailableMemory'] =  self.processManager.AvailableMemory
        data['AverageProcessorUsage'] = self.processManager.AverageProcessorUsage
        data['PeakProcessorUsage'] = self.processManager.PeakProcessorUsage
        data['AverageMemoryUsage'] = self.processManager.AverageMemoryUsage
        data['PeakMemoryUsage'] = self.processManager.AverageMemoryUsage
        data['PercentProcessorTime'] = self.processManager.PercentProcessorTime
        self.EnqueuePacket(data)
    def OnDataChanged(self, raspberryValue):
        data = {}
        data['MachineName'] = self.MachineId
        data['PacketType'] = PacketTypes.PT_DATA_CHANGED.value
        data['Timestamp'] = int(time())
        data['RaspberryInfo'] = raspberryValue
        self.EnqueuePacket(data)
        del data
        del raspberryValue
    def BuildPT_SYSTEM_INFO(self):
        try:
            data = {}
            data['MachineName'] = self.MachineId
            data['PacketType'] = PacketTypes.PT_SYSTEM_INFO.value
            data['Timestamp'] = int(time())
            data['IpAddress'] = self.PublicIP
            data['GatewayMACAddress'] = self.hardware.getMac()
            raspberryValue = {}
            raspberryValue['NetworkSpeed'] = str(self.downloadSpeed.getDownloadSpeed())
            raspberryValue['AntiVirus'] = 'None'
            raspberryValue['Firewall'] = 'iptables'
            raspberryValue['FirewallEnabled'] = 'true'
            raspberryValue['ComputerMake'] =  self.hardware.getManufacturer()
            raspberryValue['ComputerModel'] = self.hardware.getModel()
            raspberryValue['OsName'] = self.oSInfo.ID
            raspberryValue['OsBuild'] = self.oSInfo.ID_LIKE if hasattr(self.oSInfo, 'ID_LIKE') else self.oSInfo.ID
            raspberryValue['OsArchitecture'] = self.hardware.Revision
            raspberryValue['OsVersion'] = self.oSInfo.VERSION_ID
            raspberryValue['ComputerName'] = self.machineName
            raspberryValue['AgentVersion'] = self.config.get('Agent', 'Version', fallback='1.0.1.0')
            raspberryValue['InstallDate'] = self.installDate
            raspberryValue['GatewayMACAddress'] = self.hardware.getMac()
            with self.sensorsClient.sensorMutex:
                raspberryValue['SystemInfo'] = self.sensorsClient.currentSystemInfo
                raspberryValue['SensorsInfo'] = self.sensorsClient.currentSensorsInfo
                raspberryValue['BusInfo'] = self.sensorsClient.currentBusInfo
            raspberryValue['OsSettings'] = RaspiConfig.getConfig()
            raspberryValue['NetworkId'] = WifiManager.Network.GetNetworkId()
            raspberryValue['WifiStatus'] = self.wifiManager.GetStatus()
            try:
                history = History()
                history.SaveAverages(raspberryValue)
            except:
                exception('History error')
            data['RaspberryInfo'] = raspberryValue
            self.EnqueuePacket(data)
            logJson('PT_SYSTEM_INFO: ' + dumps(data), 'PT_SYSTEM_INFO')
            del raspberryValue
            del data
            data=None
        except Exception as e:
            exception('ThreadSystemInfo unexpected error: ' + str(e))
        Debug()
    def BuildPT_STARTUP_APPLICATIONS(self):
        ThreadPool.Submit(self.ThreadServiceManager)
    def ThreadServiceManager(self):
        self.serviceManager.Run()
        sleep(GENERAL_SLEEP_THREAD)
        data = {}
        data['MachineName'] = self.MachineId
        data['PacketType'] = PacketTypes.PT_STARTUP_APPLICATIONS.value
        data['ProcessList'] = self.serviceManager.GetServiceList()
        self.EnqueuePacket(data)
    def BuildPT_PROCESS_LIST(self):
        ThreadPool.Submit(self.ThreadProcessManager)
    def ThreadProcessManager(self):
        self.processManager.Run()
        sleep(GENERAL_SLEEP_THREAD)
        data = {}
        data['MachineName'] = self.MachineId
        data['PacketType'] = PacketTypes.PT_PROCESS_LIST.value
        data['ProcessList'] = self.processManager.GetProcessList()
        self.EnqueuePacket(data)
    def ProcessPT_KILL_PROCESS(self, message):
        #debug('ProcessPT_KILL_PROCESS')
        pid = message['Pid']
        retVal = self.processManager.KillProcess(int(pid))  
        data = {}
        data['MachineName'] = self.MachineId
        data['PacketType'] = PacketTypes.PT_AGENT_MESSAGE.value
        data['Type'] = 'Info'
        if retVal:
            data['Message'] = 'Process Killed!'
        else:
            data['Message'] = 'Process not Killed!'
        self.EnqueuePacket(data)
    def CheckSubscription(self):
        inviteCode = self.config.get('Agent','InviteCode')
        cayenneApiClient = CayenneApiClient(self.CayenneApiHost)
        authId = cayenneApiClient.loginDevice(inviteCode)
        if authId == None:
            error('Registration failed for invite code {}, closing the process'.format(inviteCode))
            Daemon.Exit()
        else:
            info('Registration succeeded for invite code {}, auth id = {}'.format(inviteCode, authId))
            self.config.set('Agent', 'Initialized', 'true')
            self.MachineId = authId
    @property
    def Start(self):
        #debug('Start')
        if self.connected:
            ret = False
            error('Start already connected')
        else:
            info('Connecting to: {}:{}'.format(self.HOST, self.PORT))
            count = 0
            with self.mutex:
                count+=1
                while self.connected == False and count < 30:
                    try:
                        self.sock  = None
                        self.wrappedSocket = None
                        ##debug('Start wrap_socket')
                        self.sock = socket(AF_INET, SOCK_STREAM)
                        #self.wrappedSocket = wrap_socket(self.sock, ca_certs="/etc/myDevices/ca.crt", cert_reqs=CERT_REQUIRED)
                        self.wrappedSocket = wrap_socket(self.sock)
                        self.wrappedSocket.connect((self.HOST, self.PORT))
                        info('myDevices cloud connected')
                        self.connected = True
                    except socket_error as serr:
                        Daemon.OnFailure('cloud', serr.errno)
                        error ('Start failed: ' + str(self.HOST) + ':' + str(self.PORT) + ' Error:' + str(serr))
                        self.connected = False
                        sleep(30-count)
        return self.connected
    def Stop(self):
        #debug('Stop started')
        Daemon.Reset('cloud')
        ret = True
        if self.connected == False:
            ret = False
            error('Stop not connected')
        else:
            with self.mutex:
                try:
                    self.wrappedSocket.shutdown(SHUT_RDWR)
                    self.wrappedSocket.close()
                    info('myDevices cloud disconnected')
                except socket_error as serr:
                    debug(str(serr))
                    error ('myDevices cloud disconnected error:' + str(serr))
                    ret = False
                self.connected = False
        #debug('Stop finished')
        return ret
    def Restart(self):
        if not self.exiting:
            debug('Restarting cycle...')
            sleep(1)
            self.Stop()
            self.Start

    def SendMessage(self,message):
        logJson(message, 'SendMessage')
        ret = True
        if self.connected == False:
             error('SendMessage fail')
             ret = False
        else:
            try:
                data = bytes(message, 'UTF-8')
                max_size=16383
                if len(data) > max_size:
                    start = 0
                    current=max_size
                    end = len(data)
                    self.wrappedSocket.send(data[start:current])
                    while current < end:
                        start = current
                        current = start + max_size if start + max_size < end else end
                        self.wrappedSocket.send(data[start:current])
                else:
                    self.wrappedSocket.send(data)
                if self.onMessageSent:
                    self.onMessageSent(message)
                message = None
            except socket_error as serr:
                error ('SendMessage:' + str(serr))
                ret = False
                Daemon.OnFailure('cloud', serr.errno)
                sleep(1)
            except IOError as ioerr:
                debug('IOError: ' + str(ioerr))
                self.Restart()
                #Daemon.OnFailure('cloud', ioerr.errno)
            except socket_error as serr:
                Daemon.OnFailure('cloud', serr.errno)
            except: 
                exception('SendMessage error')
        return ret
    def CheckJson(self, message):
        try:
            test = loads(message)
        except ValueError:
            return False
        return True
    def ReadMessage(self):
        ret = True
        if self.connected == False:
             ret = False
        else:
            try:
                self.count=4096
                timeout_in_seconds=10
                ready = select([self.wrappedSocket], [], [], timeout_in_seconds)
                if ready[0]:
                    message = self.wrappedSocket.recv(self.count).decode()
                    buffering = len(message) == 4096
                    while buffering and message:
                         if self.CheckJson(message):
                             buffering = False
                         else:
                             more = self.wrappedSocket.recv(self.count).decode()
                             if not more:
                                 buffering = False
                             else:
                                 message += more
                    try:
                        if message:
                            messageObject = loads(message)
                            del message
                            self.readQueue.put(messageObject)
                        else:
                            error('ReadMessage received empty message string')
                    except:
                        exception('ReadMessage error: ' + str(message)) 
                        return False
                    Daemon.Reset('cloud')
            except IOError as ioerr:
                debug('IOError: ' + str(ioerr))
                self.Restart()
                #Daemon.OnFailure('cloud', ioerr.errno)
            except socket_error as serr:
                Daemon.OnFailure('cloud', serr.errno)
            except:
                exception('ReadMessage error') 
                ret = False
                sleep(1)
                Daemon.OnFailure('cloud')
        return ret
    def RunAction(self, action):
        #execute action in machine
        debug('RunAction')
        if 'MachineName' in action and self.MachineId != action['MachineName']:
            debug('Scheduler action is not assigned for this machine: ' + str(action))
            return
        self.ExecuteMessage(action)
    def SendNotification(self, notify, subject, body):
        info('SendNotification: ' + str(notify) + ' ' + str(subject) + ' ' + str(body))
        try:
            data = {}
            data['PacketType'] = PacketTypes.PT_NOTIFICATION.value
            data['MachineName'] = self.MachineId
            data['Subject'] = subject
            data['Body'] = body
            data['Notify'] = notify
            self.EnqueuePacket(data)
        except:
            debug('')
            return False
        return True
    def ProcessMessage(self):
        try:
            messageObject = self.readQueue.get(False)
            if not messageObject:
                return False         
        except Empty:
            return False
        with self.mutex:
            retVal = self.CheckPT_ACK(messageObject)
        if retVal:
            return
        self.ExecuteMessage(messageObject)  
    def CheckPT_ACK(self, messageObject):
        try:
            packetType = int(messageObject['PacketType'])
            if packetType == PacketTypes.PT_ACK.value:
                self.lastPing = time()
                return True
        except:
            debug('')
            error('CheckPT_ACK failure: ' + str(messageObject))
        return False
    def ExecuteMessage(self, messageObject):  
        if not messageObject:
            return
        info("ExecuteMessage: " + str(messageObject['PacketType']) )
        packetType = int(messageObject['PacketType'])
        if packetType == PacketTypes.PT_UTILIZATION.value:
            self.BuildPT_UTILIZATION()
            info(PacketTypes.PT_UTILIZATION)
            return
        if packetType == PacketTypes.PT_SYSTEM_INFO.value:
            self.BuildPT_SYSTEM_INFO()
            info(PacketTypes.PT_SYSTEM_INFO)
            return
        if packetType == PacketTypes.PT_UNINSTALL_AGENT.value:
            command = "sudo /etc/myDevices/uninstall/uninstall.sh"
            services.ServiceManager.ExecuteCommand(command)
            return
        if packetType == PacketTypes.PT_STARTUP_APPLICATIONS.value:
            self.BuildPT_STARTUP_APPLICATIONS()
            info(PacketTypes.PT_STARTUP_APPLICATIONS)
            return
        if packetType == PacketTypes.PT_PROCESS_LIST.value:
            self.BuildPT_PROCESS_LIST()            
            info(PacketTypes.PT_PROCESS_LIST)
            return
        if packetType == PacketTypes.PT_KILL_PROCESS.value:
            self.ProcessPT_KILL_PROCESS(messageObject)    
            info(PacketTypes.PT_KILL_PROCESS)
            return            
        if packetType == PacketTypes.PT_INITIALIZED.value:
            #self.libMYOPX.SetSubscription(messageObject)
            info(PacketTypes.PT_INITIALIZED)
            return    
        if packetType == PacketTypes.PT_PRODUCT_INFO.value:
            self.config.set('Subscription', 'ProductCode', messageObject['ProductCode']);
            info(PacketTypes.PT_PRODUCT_INFO)
            return   
        if packetType == PacketTypes.PT_START_RDS_LOCAL_INIT.value:
            error('PT_START_RDS_LOCAL_INIT not implemented')
            info(PacketTypes.PT_START_RDS_LOCAL_INIT)
            return   
        if packetType == PacketTypes.PT_RESTART_COMPUTER.value:
            info(PacketTypes.PT_RESTART_COMPUTER)
            data={}
            data['PacketType'] = PacketTypes.PT_AGENT_MESSAGE.value
            data['MachineName'] = self.MachineId
            data['Message'] = 'Computer Restarted!'
            self.EnqueuePacket(data)
            command = "sudo shutdown -r now"
            services.ServiceManager.ExecuteCommand(command)
            return
        if packetType == PacketTypes.PT_SHUTDOWN_COMPUTER.value:
            info(PacketTypes.PT_SHUTDOWN_COMPUTER)
            data={}
            data['PacketType'] = PacketTypes.PT_AGENT_MESSAGE.value
            data['MachineName'] = self.MachineId
            data['Message'] = 'Computer Powered Off!'
            self.EnqueuePacket(data)
            command = "sudo shutdown -h now"
            services.ServiceManager.ExecuteCommand(command)
            return
        if packetType == PacketTypes.PT_SUPPORTED_SENSORS.value:
            self.sensorsClient.SupportedSensorsUpdate(messageObject)
            info(PacketTypes.PT_SUPPORTED_SENSORS)
            return
        if packetType == PacketTypes.PT_MACHINE_SENSORS.value:
            self.sensorsClient.OnDbSensors(messageObject)
            info(PacketTypes.PT_MACHINE_SENSORS)
            return
        if packetType == PacketTypes.PT_AGENT_CONFIGURATION.value:
            info('PT_AGENT_CONFIGURATION: ' + str(messageObject.Data))
            self.config.setCloudConfig(messageObject.Data)
            return
        if packetType == PacketTypes.PT_ADD_SENSOR.value:
            try:
                info(PacketTypes.PT_ADD_SENSOR)
                parameters = None
                deviceName = None
                deviceClass = None
                description = None
                #for backward compatibility check the DisplayName and overwrite it over the other variables 
                displayName = None
                if 'DisplayName' in messageObject:
                    displayName = messageObject['DisplayName']

                if 'Parameters' in messageObject:
                    parameters =  messageObject['Parameters']

                if 'DeviceName' in messageObject:
                    deviceName =  messageObject['DeviceName']
                else:
                    deviceName = displayName

                if 'Description' in messageObject:
                    description = messageObject['Description']
                else:
                    description = deviceName
                
                if 'Class' in messageObject:
                    deviceClass = messageObject['Class']
                
                retValue = True
                retValue = self.sensorsClient.AddSensor(deviceName, description, deviceClass, parameters)
            except Exception as ex:
                exception ("PT_ADD_SENSOR Unexpected error"+  str(ex))
                retValue = False
            data = {}
            if 'Id' in messageObject:
                data['Id'] = messageObject['Id']
            #0 - None, 1 - Pending, 2-Success, 3 - Not responding, 4 - Failure
            if retValue:
                data['State'] = 2 
            else:
                data['State'] = 4
            data['PacketType'] = PacketTypes.PT_UPDATE_SENSOR.value
            data['MachineName'] = self.MachineId
            self.EnqueuePacket(data)
            return
        if packetType == PacketTypes.PT_REMOVE_SENSOR.value:
            try:
                info(PacketTypes.PT_REMOVE_SENSOR)
                retValue = False
                if 'Name' in messageObject:
                    Name = messageObject['Name']
                    retValue = self.sensorsClient.RemoveSensor(Name)
                data = {}
                data['Name'] = Name
                data['PacketType'] = PacketTypes.PT_REMOVE_SENSOR.value
                data['MachineName'] = self.MachineId
                data['Response'] = retValue
                self.EnqueuePacket(data)
            except Exception as ex:
                exception ("PT_REMOVE_SENSOR Unexpected error"+  str(ex))
                retValue = False            
            return
        if packetType == PacketTypes.PT_DEVICE_COMMAND.value:
            info(PacketTypes.PT_DEVICE_COMMAND)
            self.ProcessDeviceCommand(messageObject)
            return
        if packetType == PacketTypes.PT_ADD_SCHEDULE.value:
            info(PacketTypes.PT_ADD_SCHEDULE.value)
            retVal = self.schedulerEngine.AddScheduledItem(messageObject, True)
            if 'Update' in messageObject:
                messageObject['Update'] = messageObject['Update']
            messageObject['PacketType'] = PacketTypes.PT_ADD_SCHEDULE.value
            messageObject['MachineName'] = self.MachineId
            messageObject['Status'] = str(retVal)
            self.EnqueuePacket(messageObject)
            return
        if packetType == PacketTypes.PT_REMOVE_SCHEDULE.value:
            info(PacketTypes.PT_REMOVE_SCHEDULE)
            retVal = self.schedulerEngine.RemoveScheduledItem(messageObject)
            messageObject['PacketType'] = PacketTypes.PT_REMOVE_SCHEDULE.value
            messageObject['MachineName'] = self.MachineId
            messageObject['Status'] = str(retVal)
            self.EnqueuePacket(messageObject)
            return
        if packetType == PacketTypes.PT_GET_SCHEDULES.value:
            info(PacketTypes.PT_GET_SCHEDULES)
            schedulesJson = self.schedulerEngine.GetSchedules()
            data['Schedules'] = schedulesJson
            data['PacketType'] = PacketTypes.PT_GET_SCHEDULES.value
            data['MachineName'] = self.MachineId
            self.EnqueuePacket(data)
            return
        if packetType == PacketTypes.PT_UPDATE_SCHEDULES.value:
            info(PacketTypes.PT_UPDATE_SCHEDULES)
            retVal = self.schedulerEngine.UpdateSchedules(messageObject)
            return 
        if packetType == PacketTypes.PT_HISTORY_DATA_RESPONSE.value:
            info(PacketTypes.PT_HISTORY_DATA_RESPONSE)
            try:
                id = messageObject['Id']
                history = History()
                if messageObject['Status']:
                    history.Sent(True, self.sentHistoryData[id]['HistoryData'])
                    self.historySendFails = 0
                else:
                    history.Sent(False, self.sentHistoryData[id]['HistoryData'])
                    self.historySendFails += 1
                del self.sentHistoryData[id]
            except:
                exception('Processing history response packet failed')
            return
        info("Skipping not required packet: " + str(packetType))
    def ProcessDeviceCommand(self, messageObject):
    #     t1 = Thread(target=self.ThreadDeviceCommand)
    #     t1.start()
    # def ThreadDeviceCommand(self):
        commandType = messageObject['Type']
        commandService = messageObject['Service']
        parameters = messageObject['Parameters']
        info('PT_DEVICE_COMMAND: ' + dumps(messageObject))
        debug('ProcessDeviceCommand: ' + commandType + ' ' + commandService + ' ' + str(parameters))
        id = messageObject['Id']
        sensorId = None
        if 'SensorId' in messageObject:
            sensorId = messageObject['SensorId']
        data = {}
        retValue = ''
        if commandService == 'wifi':
            if commandType == 'status':
                retValue = self.wifiManager.GetStatus()
            if commandType == 'scan':
                retValue = self.wifiManager.GetWirelessNetworks()
            if commandType == 'setup':
                try:
                    ssid = parameters["ssid"]
                    password = parameters["password"]
                    interface = parameters["interface"]
                    retValue = self.wifiManager.Setup(ssid, password, interface)
                except:
                    retValue = False
        if commandService == 'services':
            serviceName = parameters['ServiceName']
            if commandType == 'status':
                retValue = self.serviceManager.Status(serviceName)
            if commandType == 'start':
                retValue = self.serviceManager.Start(serviceName)
            if commandType == 'stop':
                retValue = self.serviceManager.Stop(serviceName)
        if commandService == 'sensor':
            debug('SENSOR_COMMAND processing: ' + str(parameters))
            method = None
            channel = None
            value = None
            driverClass = None
            sensorType = None
            sensorName = None
            if 'SensorName' in parameters:
                sensorName = parameters["SensorName"]
            if 'DriverClass' in parameters:
                driverClass = parameters["DriverClass"]
            if commandType == 'enable':
                sensor = None
                enable = None
                if 'Sensor' in parameters:
                    sensor = parameters["Sensor"]
                if 'Enable' in parameters:
                    enable = parameters["Enable"]
                retValue = self.sensorsClient.EnableSensor(sensor, enable)
            else:
                if commandType == 'edit':
                    description = sensorName
                    device = None
                    if "Description" in parameters:
                        description=parameters["Description"]
                    if "Args" in parameters:
                        args=parameters["Args"]
                    retValue = self.sensorsClient.EditSensor(sensorName, description, driverClass, args)
                else:
                    if 'Channel' in parameters:
                        channel = parameters["Channel"]
                    if 'Method' in parameters:
                        method = parameters["Method"]
                    if 'Value' in parameters:
                        value = parameters["Value"]
                    if 'SensorType' in parameters:
                        sensorType = parameters["SensorType"]
                        #(self, commandType, sensorName, sensorType, driverClass, method, channel, value):
                    retValue = self.sensorsClient.SensorCommand(commandType, sensorName,  sensorType, driverClass, method, channel, value)
        if commandService == 'gpio':
            method = parameters["Method"]
            channel = parameters["Channel"]
            value = parameters["Value"]
            debug('ProcessDeviceCommand: ' + commandService + ' ' + method + ' ' + str(channel) + ' ' + str(value))
            retValue = str(self.sensorsClient.GpioCommand(commandType, method, channel, value))
            debug('ProcessDeviceCommand gpio returned value: ' + retValue)
        if commandService == 'config':
            try:
                config_id = parameters["id"]
                arguments = parameters["arguments"]
                (retValue, output) = RaspiConfig.Config(config_id, arguments)
                data["Output"] = output
                retValue = str(retValue)
            except:
                exception ("Exception on config")
        data['Response'] = retValue
        data['Id'] = id
        data['PacketType'] = PacketTypes.PT_DEVICE_COMMAND_RESPONSE.value
        data['MachineName'] = self.MachineId
        info('PT_DEVICE_COMMAND_RESPONSE: ' + dumps(data))
        if sensorId:
            data['SensorId'] = sensorId
        self.EnqueuePacket(data)
        #if commandService == 'processes': #Kill command is handled with PT_KILL_PROCESS 
    def EnqueuePacket(self,message):
        message['PacketTime'] = GetTime()
        #datetime.now().strftime("%Y-%m-%dT%H:%M:%S%z")
        json_data = dumps(message)+ '\n'
        message = None
        #debug(json_data)
        self.writeQueue.put(json_data)
    def DequeuePacket(self):
        packet = None
        try:
            packet = self.writeQueue.get()
        except Empty:
            packet = None
        return packet
    def CheckConnectionAndPing(self):
        ticksStart = time()
        with self.mutex:
            try:
                if(ticksStart - self.lastPing > self.pingTimeout):
                    #debug('CheckConnectionAndPing EXPIRED - trying to reconnect')
                    self.Stop()
                    self.Start
                    self.lastPing = time() - self.pingRate - 1
                    warn('Restarting cloud connection -> CheckConnectionAndPing EXPIRED: ' + str(self.lastPing))
                if (ticksStart - self.waitPing >= self.pingRate):
                    #debug("CheckConnectionAndPing sending ACK packet")
                    self.SendAckPacket()
            except:
                debug('')
                error('CheckConnectionAndPing error')
    def SendAckPacket(self): 
        data = {}
        debug('Last ping: ' + str(self.lastPing) + ' Wait ping: ' + str(self.waitPing))
        data['MachineName'] = self.MachineId
        data['IPAddress'] = self.PublicIP
        data['PacketType'] = PacketTypes.PT_ACK.value
        self.EnqueuePacket(data)
        self.waitPing = time()
    def RequestSchedules(self):
        data = {}
        data['MachineName'] = self.MachineId
        data['Stored'] = "dynamodb"
        data['PacketType'] = PacketTypes.PT_REQUEST_SCHEDULES.value
        self.EnqueuePacket(data)
    def SendHistoryData(self):
        try:
            info('SendHistoryData start')
            history = History()
            history.Reset()
            while True:
                try:
                    #If there is no acknowledgment after a minute we assume failure
                    sendFailed = [key for key, item in self.sentHistoryData.items() if (item['Timestamp'] + 60) < time()]
                    info('SendHistoryData previously SendFailed items: ' + str(sendFailed))
                    for id in sendFailed:
                        self.historySendFails += len(sendFailed)
                        history.Sent(False, self.sentHistoryData[id]['HistoryData'])
                        del self.sentHistoryData[id]
                    historyData = history.GetHistoricalData()
                    if historyData:
                        data = {}
                        info('SendHistoryData historyData: ' + str(historyData))
                        data['MachineName'] = self.MachineId
                        data['Timestamp'] = int(time())
                        data['PacketType'] = PacketTypes.PT_HISTORY_DATA.value
                        id = sha256(dumps(historyData).encode('utf8')).hexdigest()
                        data['Id'] = id
                        data['HistoryData'] = historyData
                        info('Sending history data, id = {}'.format(id))
                        debug('SendHistoryData historyData: ' + str(data))
                        self.EnqueuePacket(data)
                        #this will keep acumulating
                        self.sentHistoryData[id] = data
                except Exception as ex:
                    exception('SendHistoryData error' + str(ex))
                delay = 60
                if self.historySendFails > 2:
                    delay = 120
                if self.historySendFails > 4:
                    #Wait an hour if we keep getting send failures.
                    delay = 3600
                    self.historySendFails = 0
                sleep(delay)
        except Exception as ex:
            exception('SendHistoryData general exception: ' + str(ex))
