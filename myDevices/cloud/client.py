"""
This module contains the main agent client for connecting to the Cayenne server. The client connects
to server, retrives system info as well as sensor and actuator info and sends that data to the server.
It also responds messages from the server, to set actuator values, change system config settings, etc.
"""

from socket import SOCK_STREAM, socket, AF_INET, gethostname, SHUT_RDWR
from ssl import CERT_REQUIRED, wrap_socket
from json import dumps, loads
from threading import Thread, RLock
from time import strftime, localtime, tzset, time, sleep
from queue import Queue, Empty
from enum import Enum, unique
from myDevices.utils.config import Config
from myDevices.utils.logger import exception, info, warn, error, debug, logJson
from myDevices.system import services, ipgetter
from myDevices.sensors import sensors
from myDevices.system.hardware import Hardware
# from myDevices.wifi import WifiManager
from myDevices.cloud.scheduler import SchedulerEngine
from myDevices.cloud.download_speed import DownloadSpeed
from myDevices.cloud.updater import Updater
from myDevices.system.systemconfig import SystemConfig
from myDevices.utils.daemon import Daemon
from myDevices.utils.threadpool import ThreadPool
from myDevices.utils.history import History
from myDevices.utils.subprocess import executeCommand
from select import select
from hashlib import sha256
from myDevices.cloud.apiclient import CayenneApiClient
import myDevices.cloud.cayennemqtt as cayennemqtt

NETWORK_SETTINGS = '/etc/myDevices/Network.ini'
APP_SETTINGS = '/etc/myDevices/AppSettings.ini'
GENERAL_SLEEP_THREAD = 0.20


@unique
class PacketTypes(Enum):
    """Packet types used when sending/receiving messages"""
    # PT_UTILIZATION = 3
    PT_SYSTEM_INFO = 4
    # PT_PROCESS_LIST = 5
    # PT_STARTUP_APPLICATIONS = 8
    PT_START_RDS = 11
    PT_STOP_RDS = 12
    # PT_RESTART_COMPUTER = 25
    # PT_SHUTDOWN_COMPUTER = 26
    # PT_KILL_PROCESS = 27
    PT_REQUEST_SCHEDULES = 40
    PT_UPDATE_SCHEDULES = 41
    PT_AGENT_MESSAGE = 45
    # PT_PRODUCT_INFO = 50
    PT_UNINSTALL_AGENT = 51
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
    PT_AGENT_CONFIGURATION = 74


def GetTime():
    """Return string with the current time"""
    tzset()
    cur = time()
    val = strftime("%Y-%m-%dT%T", localtime(cur))
    timezone = strftime("%z", localtime(cur))
    hourtime = int(timezone[1:3])
    timezone = timezone[:1] + str(int(timezone[1:3]))+':'+ timezone[3:7]
    if hourtime == 0:
        timezone = ''
    return val + timezone


class OSInfo():
    """Class for getting information about the OS"""

    def __init__(self):
        """Initialize variables with OS information"""
        try:
            with open('/etc/os-release', 'r') as os_file:
                for line in os_file:
                    splitLine = line.split('=')
                    if len(splitLine) < 2:
                        continue
                    key = splitLine[0].strip()
                    value = splitLine[1].strip().replace('"', '')
                    if key == 'PRETTY_NAME':
                        self.PRETTY_NAME = value
                        continue
                    if key == 'NAME':
                        self.NAME = value
                        continue
                    if key == 'VERSION_ID':
                        self.VERSION_ID = value
                        continue
                    if key == 'VERSION':
                        self.VERSION = value
                        continue
                    if key == 'ID_LIKE':
                        self.ID_LIKE = value
                        continue
                    if key == 'ID':
                        self.ID = value
                        continue
                    if key == 'ANSI_COLOR':
                        self.ANSI_COLOR = value
                        continue
                    if key == 'HOME_URL':
                        self.HOME_URL = value
                        continue
        except:
            exception("OSInfo Unexpected error")


class ProcessorThread(Thread):
    """Class for processing messages from the server on a thread"""

    def __init__(self, name, client):
        """Initialize processor thread"""
        debug('ProcessorThread init')
        Thread.__init__(self, name=name)
        self.cloudClient = client
        self.Continue = True

    def run(self):
        """Process messages from the server until the thread is stopped"""
        debug('ProcessorThread run,  continue: ' + str(self.Continue))
        while self.Continue:
            try:
                sleep(GENERAL_SLEEP_THREAD)
                self.cloudClient.ProcessMessage()
            except:
                exception("ProcessorThread Unexpected error")
        return

    def stop(self):
        """Stop processing messages from the server"""
        debug('ProcessorThread stop')
        self.Continue = False


class WriterThread(Thread):
    """Class for sending messages to the server on a thread"""

    def __init__(self, name, client):
        """Initialize writer thread"""
        debug('WriterThread init')
        Thread.__init__(self, name=name)
        self.cloudClient = client
        self.Continue = True

    def run(self):
        """Send messages to the server until the thread is stopped"""
        debug('WriterThread run')
        while self.Continue:
            sleep(GENERAL_SLEEP_THREAD)
            try:
                if self.cloudClient.mqttClient.connected == False:
                    info('WriterThread mqttClient not connected')
                    continue
                message = self.cloudClient.DequeuePacket()
                if not message:
                    info('WriterThread mqttClient no message, {}'.format(message))
                    continue
                debug('WriterThread, topic: {} {}'.format(cayennemqtt.DATA_TOPIC, type(message)))
                self.cloudClient.mqttClient.publish_packet(cayennemqtt.DATA_TOPIC, message)
                message = None
            except:
                exception("WriterThread Unexpected error")
        return

    def stop(self):
        """Stop sending messages to the server"""
        debug('WriterThread stop')
        self.Continue = False


class TimerThread(Thread):
    """Class to run a function on a thread at timed intervals"""

    def __init__(self, function, interval, initial_delay=0):
        """Set function to run at intervals and start thread"""
        Thread.__init__(self)
        self.setDaemon(True)
        self.function = function
        self.interval = interval
        self.initial_delay = initial_delay
        self.start()

    def run(self):
        """Run function at intervals"""
        sleep(self.initial_delay)
        while True:
            try:
                self.function()
                sleep(self.interval + GENERAL_SLEEP_THREAD)
            except:
                exception("TimerThread Unexpected error")


class CloudServerClient:
    """Class to connect to the server and send and receive data"""

    def __init__(self, host, port, cayenneApiHost):
        """Initialize the client configuration"""
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
        self.sensorsClient = sensors.SensorsClient()
        self.MachineId = None
        self.username = None
        self.password = None
        self.clientId = None
        self.CheckSubscription()
        #self.defaultRDServer = self.networkConfig.get('CONFIG','RemoteDesktopServerAddress')
        self.schedulerEngine = SchedulerEngine(self, 'client_scheduler')
        self.Initialize()
        # self.FirstRun()
        self.updater = Updater(self.config)
        self.updater.start()
        self.initialized = True

    def __del__(self):
        """Delete the client"""
        self.Destroy()

    def Initialize(self):
        """Initialize server connection and background threads"""
        try:
            self.mutex = RLock()
            self.readQueue = Queue()
            self.writeQueue = Queue()
            self.PublicIP = ipgetter.myip()
            self.hardware = Hardware()
            self.oSInfo = OSInfo()
            self.downloadSpeed = DownloadSpeed(self.config)
            self.downloadSpeed.getDownloadSpeed()
            self.connected = False
            self.exiting = False
            self.Start
            self.count = 10000
            self.buff = bytearray(self.count)
            #start thread only after init of other fields
            self.sensorsClient.SetDataChanged(self.OnDataChanged)
            self.processManager = services.ProcessManager()
            self.serviceManager = services.ServiceManager()
            # self.wifiManager = WifiManager.WifiManager()
            self.writerThread = WriterThread('writer', self)
            self.writerThread.start()
            self.processorThread = ProcessorThread('processor', self)
            self.processorThread.start()
            TimerThread(self.SendSystemInfo, 300)
            TimerThread(self.SendSystemState, 30, 5)
            self.previousSystemInfo = None
            self.sentHistoryData = {}
            self.historySendFails = 0
            self.historyThread = Thread(target=self.SendHistoryData)
            self.historyThread.setDaemon(True)
            self.historyThread.start()
        except Exception as e:
            exception('Initialize error: ' + str(e))

    def Destroy(self):
        """Destroy client and stop client threads"""
        info('Shutting down client')
        self.exiting = True
        self.sensorsClient.StopMonitoring()
        if hasattr(self, 'schedulerEngine'):
            self.schedulerEngine.stop()
        if hasattr(self, 'updater'):
            self.updater.stop()
        if hasattr(self, 'writerThread'):
            self.writerThread.stop()
        if hasattr(self, 'processorThread'):
            self.processorThread.stop()
        ThreadPool.Shutdown()
        self.Stop()
        info('Client shut down')

    # def FirstRun(self):
    #     """Send messages when client is first started"""
    #     self.SendSystemInfo()

    def OnDataChanged(self, systemData):
        """Enqueue a packet containing changed system data to send to the server"""
        data = {}
        data['MachineName'] = self.MachineId
        data['PacketType'] = PacketTypes.PT_DATA_CHANGED.value
        data['Timestamp'] = int(time())
        data['RaspberryInfo'] = systemData
        self.EnqueuePacket(data)
        del data
        del systemData

    def SendSystemInfo(self):
        """Enqueue a packet containing system info to send to the server"""
        try:
            # debug('SendSystemInfo')
            data_list = []
            cayennemqtt.DataChannel.add(data_list, cayennemqtt.SYS_HARDWARE_MAKE, value=self.hardware.getManufacturer())
            cayennemqtt.DataChannel.add(data_list, cayennemqtt.SYS_HARDWARE_MODEL, value=self.hardware.getModel())
            cayennemqtt.DataChannel.add(data_list, cayennemqtt.SYS_OS_NAME, value=self.oSInfo.ID)
            cayennemqtt.DataChannel.add(data_list, cayennemqtt.SYS_OS_VERSION, value=self.oSInfo.VERSION_ID)
            cayennemqtt.DataChannel.add(data_list, cayennemqtt.AGENT_VERSION, value=self.config.get('Agent','Version'))
            self.EnqueuePacket(data_list)
            # data = {}
            # data['MachineName'] = self.MachineId
            # data['PacketType'] = PacketTypes.PT_SYSTEM_INFO.value
            # data['IpAddress'] = self.PublicIP
            # data['GatewayMACAddress'] = self.hardware.getMac()
            # systemData = {}
            # # systemData['NetworkSpeed'] = str(self.downloadSpeed.getDownloadSpeed())
            # # systemData['AntiVirus'] = 'None'
            # # systemData['Firewall'] = 'iptables'
            # # systemData['FirewallEnabled'] = 'true'
            # systemData['ComputerMake'] =  self.hardware.getManufacturer()
            # systemData['ComputerModel'] = self.hardware.getModel()
            # systemData['OsName'] = self.oSInfo.ID
            # # systemData['OsBuild'] = self.oSInfo.ID_LIKE
            # # systemData['OsArchitecture'] = self.hardware.Revision
            # systemData['OsVersion'] = self.oSInfo.VERSION_ID
            # systemData['ComputerName'] = self.machineName
            # systemData['AgentVersion'] = self.config.get('Agent','Version')
            # systemData['GatewayMACAddress'] = self.hardware.getMac()
            # systemData['OsSettings'] = SystemConfig.getConfig()
            # systemData['NetworkId'] = WifiManager.Network.GetNetworkId()
            # systemData['WifiStatus'] = self.wifiManager.GetStatus()
            # data['RaspberryInfo'] = systemData
            # if data != self.previousSystemInfo:
            #     self.previousSystemInfo = data.copy()
            #     data['Timestamp'] = int(time())
            #     self.EnqueuePacket(data)
            #     logJson('SendSystemInfo: ' + dumps(data), 'SendSystemInfo')
            # del systemData
            # del data
            # data=None
        except Exception:
            exception('SendSystemInfo unexpected error')

    # def SendSystemUtilization(self):
    #     """Enqueue a packet containing system utilization data to send to the server"""
    #     data = {}
    #     data['MachineName'] = self.MachineId
    #     data['Timestamp'] = int(time())
    #     data['PacketType'] = PacketTypes.PT_UTILIZATION.value
    #     self.processManager.RefreshProcessManager()
    #     data['VisibleMemory'] = self.processManager.VisibleMemory
    #     data['AvailableMemory'] = self.processManager.AvailableMemory
    #     data['AverageProcessorUsage'] = self.processManager.AverageProcessorUsage
    #     data['PeakProcessorUsage'] = self.processManager.PeakProcessorUsage
    #     data['AverageMemoryUsage'] = self.processManager.AverageMemoryUsage
    #     data['PeakMemoryUsage'] = self.processManager.AverageMemoryUsage
    #     data['PercentProcessorTime'] = self.processManager.PercentProcessorTime
    #     self.EnqueuePacket(data)

    def SendSystemState(self):
        """Enqueue a packet containing system information to send to the server"""
        try:
            # debug('SendSystemState')
            # self.SendSystemInfo()
            # self.SendSystemUtilization()
            data_list = []
            download_speed = self.downloadSpeed.getDownloadSpeed()
            if download_speed:
                cayennemqtt.DataChannel.add(data_list, cayennemqtt.SYS_NET, suffix=cayennemqtt.SPEEDTEST, value=download_speed)
            data_list += self.sensorsClient.systemData
            config = SystemConfig.getConfig()
            if config:
                channel_map = {'I2C': cayennemqtt.SYS_I2C, 'SPI': cayennemqtt.SYS_SPI, 'Serial': cayennemqtt.SYS_UART, 'DeviceTree': cayennemqtt.SYS_DEVICETREE}
                for key, channel in channel_map.items():
                    try:
                        cayennemqtt.DataChannel.add(data_list, channel, value=config[key])
                    except:
                        pass
            self.EnqueuePacket(data_list)
            # data = {}
            # data['MachineName'] = self.MachineId
            # data['PacketType'] = PacketTypes.PT_SYSTEM_INFO.value
            # data['Timestamp'] = int(time())
            # data['IpAddress'] = self.PublicIP
            # data['GatewayMACAddress'] = self.hardware.getMac()
            # systemData = {}
            # systemData['NetworkSpeed'] = str(self.downloadSpeed.getDownloadSpeed())
            # systemData['AntiVirus'] = 'None'
            # systemData['Firewall'] = 'iptables'
            # systemData['FirewallEnabled'] = 'true'
            # systemData['ComputerMake'] = self.hardware.getManufacturer()
            # systemData['ComputerModel'] = self.hardware.getModel()
            # systemData['OsName'] = self.oSInfo.ID
            # systemData['OsBuild'] = self.oSInfo.ID_LIKE if hasattr(self.oSInfo, 'ID_LIKE') else self.oSInfo.ID
            # systemData['OsArchitecture'] = self.hardware.Revision
            # systemData['OsVersion'] = self.oSInfo.VERSION_ID
            # systemData['ComputerName'] = self.machineName
            # systemData['AgentVersion'] = self.config.get('Agent', 'Version', fallback='1.0.1.0')
            # systemData['InstallDate'] = self.installDate
            # systemData['GatewayMACAddress'] = self.hardware.getMac()
            # with self.sensorsClient.sensorMutex:
            #     systemData['SystemInfo'] = self.sensorsClient.currentSystemInfo
            #     systemData['SensorsInfo'] = self.sensorsClient.currentSensorsInfo
            #     systemData['BusInfo'] = self.sensorsClient.currentBusInfo
            # systemData['OsSettings'] = SystemConfig.getConfig()
            # systemData['NetworkId'] = WifiManager.Network.GetNetworkId()
            # systemData['WifiStatus'] = self.wifiManager.GetStatus()
            # try:
            #     history = History()
            #     history.SaveAverages(systemData)
            # except:
            #     exception('History error')
            # data['RaspberryInfo'] = systemData
            # self.EnqueuePacket(data)
            # logJson('PT_SYSTEM_INFO: ' + dumps(data), 'PT_SYSTEM_INFO')
            # del systemData
            # del data
            # data = None
        except Exception as e:
            exception('ThreadSystemInfo unexpected error: ' + str(e))

    # def BuildPT_STARTUP_APPLICATIONS(self):
    #     """Schedule a function to run for retrieving a list of services"""
    #     ThreadPool.Submit(self.ThreadServiceManager)

    # def ThreadServiceManager(self):
    #     """Enqueue a packet containing a list of services to send to the server"""
    #     self.serviceManager.Run()
    #     sleep(GENERAL_SLEEP_THREAD)
    #     data = {}
    #     data['MachineName'] = self.MachineId
    #     data['PacketType'] = PacketTypes.PT_STARTUP_APPLICATIONS.value
    #     data['ProcessList'] = self.serviceManager.GetServiceList()
    #     self.EnqueuePacket(data)

    # def BuildPT_PROCESS_LIST(self):
    #     """Schedule a function to run for retrieving a list of processes"""
    #     ThreadPool.Submit(self.ThreadProcessManager)

    # def ThreadProcessManager(self):
    #     """Enqueue a packet containing a list of processes to send to the server"""
    #     self.processManager.Run()
    #     sleep(GENERAL_SLEEP_THREAD)
    #     data = {}
    #     data['MachineName'] = self.MachineId
    #     data['PacketType'] = PacketTypes.PT_PROCESS_LIST.value
    #     data['ProcessList'] = self.processManager.GetProcessList()
    #     self.EnqueuePacket(data)

    # def ProcessPT_KILL_PROCESS(self, message):
    #     """Kill a process specified in message"""
    #     pid = message['Pid']
    #     retVal = self.processManager.KillProcess(int(pid))
    #     data = {}
    #     data['MachineName'] = self.MachineId
    #     data['PacketType'] = PacketTypes.PT_AGENT_MESSAGE.value
    #     data['Type'] = 'Info'
    #     if retVal:
    #         data['Message'] = 'Process Killed!'
    #     else:
    #         data['Message'] = 'Process not Killed!'
    #     self.EnqueuePacket(data)

    def CheckSubscription(self):
        """Check that an invite code is valid"""
        inviteCode = self.config.get('Agent', 'InviteCode')
        cayenneApiClient = CayenneApiClient(self.CayenneApiHost)
        credentials = cayenneApiClient.loginDevice(inviteCode)
        if credentials == None:
            error('Registration failed for invite code {}, closing the process'.format(inviteCode))
            Daemon.Exit()
        else:
            info('Registration succeeded for invite code {}, credentials = {}'.format(inviteCode, credentials))
            self.config.set('Agent', 'Initialized', 'true')
            try:
                self.MachineId = credentials #credentials['id']
                self.username = 'username' #credentials['mqtt']['username']
                self.password = 'password' #credentials['mqtt']['password']
                self.clientId = 'client_id' #credentials['mqtt']['clientId']
                self.config.set('Agent', 'Id', self.MachineId)
            except:
                exception('Invalid credentials, closing the process')
                Daemon.Exit()
        info('CheckSubscription: MachineId {}'.format(self.MachineId))
 
    @property
    def Start(self):
        """Connect to the server"""
        started = False
        count = 0
        while started == False and count < 30:
            try:
                self.mqttClient = cayennemqtt.CayenneMQTTClient()
                self.mqttClient.on_message = self.OnMessage
                self.mqttClient.begin(self.username, self.password, self.clientId, self.HOST, self.PORT)
                self.mqttClient.loop_start()
                started = True
            except OSError as oserror:
                Daemon.OnFailure('cloud', oserror.errno)
                error ('Start failed: ' + str(self.HOST) + ':' + str(self.PORT) + ' Error:' + str(oserror))
                started = False
                sleep(30-count)
        return started

    def Stop(self):
        """Disconnect from the server"""
        Daemon.Reset('cloud')
        try:
            self.mqttClient.loop_stop()
            info('myDevices cloud disconnected')
        except:
            exception('Error stopping client')

    def Restart(self):
        """Restart the server connection"""
        if not self.exiting:
            debug('Restarting cycle...')
            sleep(1)
            self.Stop()
            self.Start

    def CheckJson(self, message):
        """Check if a JSON message is valid"""
        try:
            test = loads(message)
        except ValueError:
            return False
        return True

    def OnMessage(self, message):
        """Add message from the server to the queue"""
        info('OnMessage: {}'.format(message))
        self.readQueue.put(message)

    def RunAction(self, action):
        """Run a specified action"""
        debug('RunAction')
        if 'MachineName' in action:
            #Use the config file machine if self.MachineId has not been set yet due to connection issues 
            machine_id = self.MachineId if self.MachineId else self.config.get('Agent', 'Id')
            if machine_id != action['MachineName']:
                debug('Scheduler action is not assigned for this machine: ' + str(action))
                return
        self.ExecuteMessage(action)

    def SendNotification(self, notify, subject, body):
        """Enqueue a notification message packet to send to the server"""
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
        """Process a message from the server"""
        try:
            messageObject = self.readQueue.get(False)
            if not messageObject:
                return False
        except Empty:
            return False
        self.ExecuteMessage(messageObject)

    def ExecuteMessage(self, messageObject):
        """Execute an action described in a message object"""
        if not messageObject:
            return
        channel = messageObject['channel']
        info('ExecuteMessage: {}'.format(channel))
        if channel == cayennemqtt.SYS_POWER:
            if messageObject['payload'] == 'reset':
                executeCommand('sudo shutdown -r now')
            elif messageObject['payload'] == 'halt':
                executeCommand('sudo shutdown -h now')
        elif channel in (cayennemqtt.SYS_I2C, cayennemqtt.SYS_SPI, cayennemqtt.SYS_UART, cayennemqtt.SYS_DEVICETREE):
            self.ProcessConfigCommand(messageObject)
        elif channel.startswith(cayennemqtt.SYS_GPIO):
            self.ProcessGpioCommand(messageObject)

        packetType = int(messageObject['PacketType'])
        # if packetType == PacketTypes.PT_UTILIZATION.value:
        #     self.SendSystemUtilization()
        #     info(PacketTypes.PT_UTILIZATION)
        #     return
        if packetType == PacketTypes.PT_SYSTEM_INFO.value:
            info("ExecuteMessage - sysinfo - Calling SendSystemState")
            self.SendSystemState()
            info(PacketTypes.PT_SYSTEM_INFO)
            return
        if packetType == PacketTypes.PT_UNINSTALL_AGENT.value:
            command = "sudo /etc/myDevices/uninstall/uninstall.sh"
            executeCommand(command)
            return
        # if packetType == PacketTypes.PT_STARTUP_APPLICATIONS.value:
        #     self.BuildPT_STARTUP_APPLICATIONS()
        #     info(PacketTypes.PT_STARTUP_APPLICATIONS)
        #     return
        # if packetType == PacketTypes.PT_PROCESS_LIST.value:
        #     self.BuildPT_PROCESS_LIST()
        #     info(PacketTypes.PT_PROCESS_LIST)
        #     return
        # if packetType == PacketTypes.PT_KILL_PROCESS.value:
        #     self.ProcessPT_KILL_PROCESS(messageObject)
        #     info(PacketTypes.PT_KILL_PROCESS)
        #     return
        # if packetType == PacketTypes.PT_PRODUCT_INFO.value:
        #     self.config.set('Subscription', 'ProductCode', messageObject['ProductCode'])
        #     info(PacketTypes.PT_PRODUCT_INFO)
        #     return   
        # if packetType == PacketTypes.PT_RESTART_COMPUTER.value:
        #     info(PacketTypes.PT_RESTART_COMPUTER)
        #     data = {}
        #     data['PacketType'] = PacketTypes.PT_AGENT_MESSAGE.value
        #     data['MachineName'] = self.MachineId
        #     data['Message'] = 'Computer Restarted!'
        #     self.EnqueuePacket(data)
        #     command = "sudo shutdown -r now"
        #     executeCommand(command)
        #     return
        # if packetType == PacketTypes.PT_SHUTDOWN_COMPUTER.value:
        #     info(PacketTypes.PT_SHUTDOWN_COMPUTER)
        #     data = {}
        #     data['PacketType'] = PacketTypes.PT_AGENT_MESSAGE.value
        #     data['MachineName'] = self.MachineId
        #     data['Message'] = 'Computer Powered Off!'
        #     self.EnqueuePacket(data)
        #     command = "sudo shutdown -h now"
        #     executeCommand(command)
        #     return
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
                    parameters = messageObject['Parameters']

                if 'DeviceName' in messageObject:
                    deviceName = messageObject['DeviceName']
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
                exception("PT_ADD_SENSOR Unexpected error"+  str(ex))
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
                exception("PT_REMOVE_SENSOR Unexpected error"+  str(ex))
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

    def ProcessConfigCommand(self, message):
        """Process system configuration command"""
        value = 1 - int(message['payload']) #Invert the value since the config script uses 0 for enable and 1 for disable
        command_id = {cayennemqtt.SYS_I2C: 11, cayennemqtt.SYS_SPI: 12, cayennemqtt.SYS_UART: 13, cayennemqtt.SYS_DEVICETREE: 9}
        result, output = SystemConfig.ExecuteConfigCommand(command_id[message['channel']], value)
        debug('ProcessConfigCommand: {}, result: {}, output: {}'.format(message, result, output))
    
    def ProcessGpioCommand(self, message):
        """Process GPIO command"""
        info('ProcessGpioCommand: {}'.format(message))
        channel = int(message['channel'].replace(cayennemqtt.SYS_GPIO + ':', ''))
        result = self.sensorsClient.GpioCommand(message['suffix'], channel, message['payload'])
        debug('ProcessGpioCommand result: {}'.format(result))

    def ProcessDeviceCommand(self, messageObject):
        """Execute a command to run on the device as specified in a message object"""
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
        # if commandService == 'wifi':
        #     if commandType == 'status':
        #         retValue = self.wifiManager.GetStatus()
        #     if commandType == 'scan':
        #         retValue = self.wifiManager.GetWirelessNetworks()
        #     if commandType == 'setup':
        #         try:
        #             ssid = parameters["ssid"]
        #             password = parameters["password"]
        #             interface = parameters["interface"]
        #             retValue = self.wifiManager.Setup(ssid, password, interface)
        #         except:
        #             retValue = False
        # if commandService == 'services':
        #     serviceName = parameters['ServiceName']
        #     if commandType == 'status':
        #         retValue = self.serviceManager.Status(serviceName)
        #     if commandType == 'start':
        #         retValue = self.serviceManager.Start(serviceName)
        #     if commandType == 'stop':
        #         retValue = self.serviceManager.Stop(serviceName)
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
                        description = parameters["Description"]
                    if "Args" in parameters:
                        args = parameters["Args"]
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
                    retValue = self.sensorsClient.SensorCommand(commandType, sensorName, sensorType, driverClass, method, channel, value)
        # if commandService == 'gpio':
        #     method = parameters["Method"]
        #     channel = parameters["Channel"]
        #     value = parameters["Value"]
        #     debug('ProcessDeviceCommand: ' + commandService + ' ' + method + ' ' + str(channel) + ' ' + str(value))
        #     retValue = str(self.sensorsClient.GpioCommand(commandType, method, channel, value))
        #     debug('ProcessDeviceCommand gpio returned value: ' + retValue)
        # if commandService == 'config':
        #     try:
        #         config_id = parameters["id"]
        #         arguments = parameters["arguments"]
        #         (retValue, output) = SystemConfig.ExecuteConfigCommand(config_id, arguments)
        #         data["Output"] = output
        #         retValue = str(retValue)
        #     except:
        #         exception("Exception on config")
        data['Response'] = retValue
        data['Id'] = id
        data['PacketType'] = PacketTypes.PT_DEVICE_COMMAND_RESPONSE.value
        data['MachineName'] = self.MachineId
        info('PT_DEVICE_COMMAND_RESPONSE: ' + dumps(data))
        if sensorId:
            data['SensorId'] = sensorId
        self.EnqueuePacket(data)

    def EnqueuePacket(self, message):
        """Enqueue a message packet to send to the server"""
        if isinstance(message, dict):
            message['PacketTime'] = GetTime()
        json_data = dumps(message) + '\n'
        message = None
        self.writeQueue.put(json_data)

    def DequeuePacket(self):
        """Dequeue a message packet to send to the server"""
        packet = None
        try:
            packet = self.writeQueue.get()
        except Empty:
            packet = None
        return packet

    def RequestSchedules(self):
        """Enqueue a packet to request schedules from the server"""
        data = {}
        data['MachineName'] = self.MachineId
        data['Stored'] = "dynamodb"
        data['PacketType'] = PacketTypes.PT_REQUEST_SCHEDULES.value
        self.EnqueuePacket(data)

    def SendHistoryData(self):
        """Enqueue a packet containing historical data to send to the server"""
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
                        #this will keep accumulating
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
