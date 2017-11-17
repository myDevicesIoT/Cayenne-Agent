"""
This module contains the main agent client for connecting to the Cayenne server. The client connects
to server, retrives system info as well as sensor and actuator info and sends that data to the server.
It also responds messages from the server, to set actuator values, change system config settings, etc.
"""

from json import dumps, loads
from threading import Thread
from time import strftime, localtime, tzset, time, sleep
from queue import Queue, Empty
from myDevices.utils.config import Config
from myDevices.utils.logger import exception, info, warn, error, debug, logJson
from myDevices.sensors import sensors
from myDevices.system.hardware import Hardware
# from myDevices.cloud.scheduler import SchedulerEngine
from myDevices.cloud.download_speed import DownloadSpeed
from myDevices.cloud.updater import Updater
from myDevices.system.systemconfig import SystemConfig
from myDevices.utils.daemon import Daemon
from myDevices.utils.threadpool import ThreadPool
# from myDevices.utils.history import History
from myDevices.utils.subprocess import executeCommand
# from hashlib import sha256
from myDevices.cloud.apiclient import CayenneApiClient
import myDevices.cloud.cayennemqtt as cayennemqtt

NETWORK_SETTINGS = '/etc/myDevices/Network.ini'
APP_SETTINGS = '/etc/myDevices/AppSettings.ini'
GENERAL_SLEEP_THREAD = 0.20


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
                    keys = ('VERSION_ID', 'ID')
                    if key in keys:
                        setattr(self, key, value)
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
                # debug('WriterThread, topic: {} {}'.format(cayennemqtt.DATA_TOPIC, message))
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
        self.username = None
        self.password = None
        self.clientId = None
        self.CheckSubscription()
        # self.schedulerEngine = SchedulerEngine(self, 'client_scheduler')
        self.Initialize()
        self.updater = Updater(self.config)
        self.updater.start()

    def __del__(self):
        """Delete the client"""
        self.Destroy()

    def Initialize(self):
        """Initialize server connection and background threads"""
        try:
            self.readQueue = Queue()
            self.writeQueue = Queue()
            self.hardware = Hardware()
            self.oSInfo = OSInfo()
            self.connected = False
            self.exiting = False
            self.Start()
            self.count = 10000
            self.buff = bytearray(self.count)
            self.downloadSpeed = DownloadSpeed(self.config)
            self.downloadSpeed.getDownloadSpeed()
            self.sensorsClient.SetDataChanged(self.OnDataChanged)
            self.writerThread = WriterThread('writer', self)
            self.writerThread.start()
            self.processorThread = ProcessorThread('processor', self)
            self.processorThread.start()
            TimerThread(self.SendSystemInfo, 300)
            TimerThread(self.SendSystemState, 30, 5)
            # self.sentHistoryData = {}
            # self.historySendFails = 0
            # self.historyThread = Thread(target=self.SendHistoryData)
            # self.historyThread.setDaemon(True)
            # self.historyThread.start()
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

    def OnDataChanged(self, data):
        """Enqueue a packet containing changed system data to send to the server"""
        info('Send changed data: {}'.format([{item['channel']:item['value']} for item in data]))
        self.EnqueuePacket(data)

    def SendSystemInfo(self):
        """Enqueue a packet containing system info to send to the server"""
        try:
            data = []
            cayennemqtt.DataChannel.add(data, cayennemqtt.SYS_HARDWARE_MAKE, value=self.hardware.getManufacturer())
            cayennemqtt.DataChannel.add(data, cayennemqtt.SYS_HARDWARE_MODEL, value=self.hardware.getModel())
            cayennemqtt.DataChannel.add(data, cayennemqtt.SYS_OS_NAME, value=self.oSInfo.ID)
            cayennemqtt.DataChannel.add(data, cayennemqtt.SYS_OS_VERSION, value=self.oSInfo.VERSION_ID)
            cayennemqtt.DataChannel.add(data, cayennemqtt.AGENT_VERSION, value=self.config.get('Agent','Version'))
            config = SystemConfig.getConfig()
            if config:
                channel_map = {'I2C': cayennemqtt.SYS_I2C, 'SPI': cayennemqtt.SYS_SPI, 'Serial': cayennemqtt.SYS_UART, 'DeviceTree': cayennemqtt.SYS_DEVICETREE}
                for key, channel in channel_map.items():
                    try:
                        cayennemqtt.DataChannel.add(data, channel, value=config[key])
                    except:
                        pass
            info('Send system info: {}'.format([{item['channel']:item['value']} for item in data]))
            self.EnqueuePacket(data)
        except Exception:
            exception('SendSystemInfo unexpected error')

    def SendSystemState(self):
        """Enqueue a packet containing system information to send to the server"""
        try:
            data = []
            download_speed = self.downloadSpeed.getDownloadSpeed()
            if download_speed:
                cayennemqtt.DataChannel.add(data, cayennemqtt.SYS_NET, suffix=cayennemqtt.SPEEDTEST, value=download_speed)
            data += self.sensorsClient.systemData
            info('Send system state: {} items'.format(len(data)))
            self.EnqueuePacket(data)
        except Exception as e:
            exception('ThreadSystemInfo unexpected error: ' + str(e))

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
                self.username = credentials['mqtt']['username']
                self.password = credentials['mqtt']['password']
                self.clientId = credentials['mqtt']['clientId']
            except:
                exception('Invalid credentials, closing the process')
                Daemon.Exit()
 
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
            self.Start()

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
        self.ExecuteMessage(action)

    def ProcessMessage(self):
        """Process a message from the server"""
        try:
            messageObject = self.readQueue.get(False)
            if not messageObject:
                return False
        except Empty:
            return False
        self.ExecuteMessage(messageObject)

    def ExecuteMessage(self, message):
        """Execute an action described in a message object"""
        if not message:
            return
        channel = message['channel']
        info('ExecuteMessage: {}'.format(message))
        if channel == cayennemqtt.SYS_POWER:
            self.ProcessPowerCommand(message)
        elif channel.startswith(cayennemqtt.DEV_SENSOR):
            self.ProcessSensorCommand(message)
        elif channel.startswith(cayennemqtt.SYS_GPIO):
            self.ProcessGpioCommand(message)
        elif channel == cayennemqtt.AGENT_DEVICES:
            self.ProcessDeviceCommand(message)
        elif channel in (cayennemqtt.SYS_I2C, cayennemqtt.SYS_SPI, cayennemqtt.SYS_UART, cayennemqtt.SYS_DEVICETREE):
            self.ProcessConfigCommand(message)
        elif channel == cayennemqtt.AGENT_MANAGE:
            self.ProcessAgentCommand(message)
        else:
            info('Unknown message')

    def ProcessPowerCommand(self, message):
        """Process command to reboot/shutdown the system"""
        commands = {'reset': 'sudo shutdown -r now', 'halt': 'sudo shutdown -h now'}
        output, result = executeCommand(commands[message['payload']])
        debug('ProcessPowerCommand: {}, result: {}, output: {}'.format(message, result, output))

    def ProcessAgentCommand(self, message):
        """Process command to manage the agent state"""
        if message['suffix'] == 'uninstall':
            output, result = executeCommand('sudo /etc/myDevices/uninstall/uninstall.sh')
            debug('ProcessAgentCommand: {}, result: {}, output: {}'.format(message, result, output))
        elif message['suffix'] == 'config':
            for key, value in message['payload'].items():
                if value is None:
                    info('Remove config item: {}'.format(key))
                    self.config.remove('Agent', key)
                else:
                    info('Set config item: {} {}'.format(key, value))
                    self.config.set('Agent', key, value)

    def ProcessConfigCommand(self, message):
        """Process system configuration command"""
        value = 1 - int(message['payload']) #Invert the value since the config script uses 0 for enable and 1 for disable
        command_id = {cayennemqtt.SYS_I2C: 11, cayennemqtt.SYS_SPI: 12, cayennemqtt.SYS_UART: 13, cayennemqtt.SYS_DEVICETREE: 9}
        result, output = SystemConfig.ExecuteConfigCommand(command_id[message['channel']], value)
        debug('ProcessConfigCommand: {}, result: {}, output: {}'.format(message, result, output))
    
    def ProcessGpioCommand(self, message):
        """Process GPIO command"""
        channel = int(message['channel'].replace(cayennemqtt.SYS_GPIO + ':', ''))
        result = self.sensorsClient.GpioCommand(message['suffix'], channel, message['payload'])
        debug('ProcessGpioCommand result: {}'.format(result))

    def ProcessSensorCommand(self, message):
        """Process sensor command"""
        sensor_info = message['channel'].replace(cayennemqtt.DEV_SENSOR + ':', '').split(':')
        sensor = sensor_info[0]
        channel = None
        if len(sensor_info) > 1:
            channel = sensor_info[1]
        result = self.sensorsClient.SensorCommand(message['suffix'], sensor, channel, message['payload'])
        debug('ProcessSensorCommand result: {}'.format(result))

    def ProcessDeviceCommand(self, message):
        """Process a device command to add/edit/remove a sensor"""
        payload = message['payload']
        info('ProcessDeviceCommand payload: {}'.format(payload))
        if message['suffix'] == 'add':
            result = self.sensorsClient.AddSensor(payload['id'], payload['description'], payload['class'], payload['args'])
        elif message['suffix'] == 'edit':
            result = self.sensorsClient.EditSensor(payload['id'], payload['description'], payload['class'], payload['args'])
        elif message['suffix'] == 'delete':
            result = self.sensorsClient.RemoveSensor(payload['id'])
        else:
            info('Unknown device command: {}'.format(message['suffix']))
        debug('ProcessDeviceCommand result: {}'.format(result))

    def EnqueuePacket(self, message):
        """Enqueue a message packet to send to the server"""
        json_data = dumps(message)
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

    # def SendHistoryData(self):
    #     """Enqueue a packet containing historical data to send to the server"""
    #     try:
    #         info('SendHistoryData start')
    #         history = History()
    #         history.Reset()
    #         while True:
    #             try:
    #                 #If there is no acknowledgment after a minute we assume failure
    #                 sendFailed = [key for key, item in self.sentHistoryData.items() if (item['Timestamp'] + 60) < time()]
    #                 info('SendHistoryData previously SendFailed items: ' + str(sendFailed))
    #                 for id in sendFailed:
    #                     self.historySendFails += len(sendFailed)
    #                     history.Sent(False, self.sentHistoryData[id]['HistoryData'])
    #                     del self.sentHistoryData[id]
    #                 historyData = history.GetHistoricalData()
    #                 if historyData:
    #                     data = {}
    #                     info('SendHistoryData historyData: ' + str(historyData))
    #                     data['MachineName'] = self.MachineId
    #                     data['Timestamp'] = int(time())
    #                     data['PacketType'] = PacketTypes.PT_HISTORY_DATA.value
    #                     id = sha256(dumps(historyData).encode('utf8')).hexdigest()
    #                     data['Id'] = id
    #                     data['HistoryData'] = historyData
    #                     info('Sending history data, id = {}'.format(id))
    #                     debug('SendHistoryData historyData: ' + str(data))
    #                     self.EnqueuePacket(data)
    #                     #this will keep accumulating
    #                     self.sentHistoryData[id] = data
    #             except Exception as ex:
    #                 exception('SendHistoryData error' + str(ex))
    #             delay = 60
    #             if self.historySendFails > 2:
    #                 delay = 120
    #             if self.historySendFails > 4:
    #                 #Wait an hour if we keep getting send failures.
    #                 delay = 3600
    #                 self.historySendFails = 0
    #             sleep(delay)
    #     except Exception as ex:
    #         exception('SendHistoryData general exception: ' + str(ex))