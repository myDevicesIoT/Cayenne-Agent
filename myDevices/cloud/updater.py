from myDevices.utils.logger import exception, info, warn, error, debug, setDebug
from time import time, sleep
from sched import scheduler
from distutils.version import LooseVersion, StrictVersion
from os import mkdir, path
from threading import Thread
from shutil import rmtree
from datetime import datetime, timedelta
import random
from myDevices.utils.config import Config
from myDevices.utils.subprocess import executeCommand

SETUP_NAME = 'myDevicesSetup_raspberrypi.sh'
INSTALL_PATH = '/etc/myDevices/'
UPDATE_PATH = INSTALL_PATH + 'updates/'
UPDATE_CFG = UPDATE_PATH + 'update'
SETUP_PATH = UPDATE_PATH + SETUP_NAME

TIME_TO_CHECK = 60 + random.randint(60, 300) #seconds - at least 2 minutes or
TIME_TO_SLEEP = 60
UPDATE_URL = 'https://updates.mydevices.com/raspberry/update'
SETUP_URL = 'https://updates.mydevices.com/raspberry/'

try:
    # For Python 3.0 and later
    from urllib.request import urlopen
except ImportError:
    # Fall back to Python 2's urllib2
    from urllib2 import urlopen

class Updater(Thread):

    def __init__(self, config, onUpdateConfig = None):

        #disable debug after testing is finished
        #setDebug()
        Thread.__init__(self, name='updater')
        self.setDaemon(True)
        self.appSettings = config
        self.onUpdateConfig = onUpdateConfig
        self.env = self.appSettings.get('Agent','Environment', fallback='live')
        global SETUP_URL
        global UPDATE_URL
        if self.env == 'live':
            SETUP_URL = SETUP_URL + SETUP_NAME
        else:
            SETUP_URL = SETUP_URL + self.env + '_' + SETUP_NAME
            UPDATE_URL = UPDATE_URL + self.env
        UPDATE_URL = self.appSettings.get('Agent', 'UpdateUrl', UPDATE_URL)
        SETUP_URL = self.appSettings.get('Agent', 'SetupUrl', SETUP_URL)
        self.scheduler = scheduler(time, sleep)
        self.Continue = True
        self.currentVersion = ''
        self.newVersion = ''
        self.downloadUrl = ''
        self.UpdateCleanup()
        self.startTime = datetime.now() - timedelta(days=1)

    def run(self):
        debug('UpdaterThread started')
        while self.Continue:
            sleep(TIME_TO_SLEEP)
            self.SetupUpdater()
            self.scheduler.run()
        debug('UpdaterThread finished')

    def stop(self):
        debug('Updater stop called')
        self.Continue = False

    def UpdateCleanup(self):
        try:
            debug('Updater cleanup: '+ str(path.exists(UPDATE_PATH)))
            if path.exists(UPDATE_PATH) == True:
                debug('Updater cleanup executes delete')
                rmtree(UPDATE_PATH)
                return
        except:
            exception('UpdateCleanup error')
            
    def CheckUpdate(self):
        doUpdates = self.appSettings.get('Agent', 'DoUpdates', 'true')
        if doUpdates.lower() == 'false':
            info('DoUpdates is false, skipping update check')
            return
        if self.onUpdateConfig:
            self.onUpdateConfig()
        now = datetime.now()
        info('Checking for updates...')
        elapsedTime=now-self.startTime
        if elapsedTime.total_seconds() < TIME_TO_CHECK:
            return
        self.startTime = datetime.now()
        if path.exists(UPDATE_PATH) == True:
            error('myDevices updater another update in progress')
            return
        sleep(1)
        # Run the update as root
        executeCommand('sudo python3 -m myDevices.cloud.doupdatecheck')

    def DoUpdateCheck(self):
        mkdir(UPDATE_PATH)
        sleep(1)
        try:
            self.currentVersion = self.appSettings.get('Agent', 'Version', fallback='1.0.1.0')
        except:
            error('Updater Current Version not found')
        sleep(1)
        if not self.currentVersion:
            error('Current version not available. Cannot update agent.')
            self.UpdateCleanup()
            return
        retValue = self.RetrieveUpdate()
        sleep(1)
        if retValue is False:
            error('Update version cannot be retrieved. Cannot update agent.')
            self.UpdateCleanup()
            return
        sleep(1)
        retValue = self.CheckVersion(self.currentVersion, self.newVersion)
        if retValue is True:
            info('Update needed, current version: {}, update version: {}'.format(self.currentVersion, self.newVersion))
            retValue = self.ExecuteUpdate()
            if retValue is False:
                self.UpdateCleanup()
                error('Agent failed to update')
                return
        else:
            info('Update not needed, current version: {}, update version: {}'.format(self.currentVersion, self.newVersion))
        sleep(1)
        self.UpdateCleanup()

    def SetupUpdater(self):
        global TIME_TO_CHECK
        TIME_TO_CHECK = self.appSettings.get('Agent', 'UpdateCheckRate', TIME_TO_CHECK)
        self.scheduler.enter(TIME_TO_CHECK, 1, self.CheckUpdate, ())

    def RetrieveUpdate(self):
        try:
            info('Checking update version')
            debug('Retrieve update config: {} {}'.format(UPDATE_URL, UPDATE_CFG))
            retValue = self.DownloadFile(UPDATE_URL, UPDATE_CFG)
            if retValue is False:
                error('Failed to download update file')
                return retValue
            updateConfig = Config(UPDATE_CFG)
            try:
                self.newVersion = updateConfig.get('UPDATES','Version')
                self.downloadUrl = updateConfig.get('UPDATES','Url')
            except:
                error('Updater missing: update version or Url')
            info('Updater retrieve update success')
            return True
        except:
            error('Updater retrieve update failure')
            return False

    def DownloadFile(self, url, localPath):
        try:
            info( url + ' ' + localPath)
            with urlopen(url) as response:
                with open(localPath, 'wb') as output:
                    output.write(response.read())
            debug('Updater download success')
            return True
        except:
            debug('Updater download failed')
            return False

    def ExecuteUpdate(self):
        debug('Execute update: {} {}'.format(SETUP_URL, SETUP_PATH))
        retValue = self.DownloadFile(SETUP_URL, SETUP_PATH)
        if retValue is False:
            return retValue
        command = "chmod +x " + SETUP_PATH
        (output, returncode) = executeCommand(command)
        del output
        command = "nohup " + SETUP_PATH + ' -update >/var/log/myDevices/myDevices.update 2>/var/log/myDevices/myDevices.update.err'
        debug('execute command started: {}'.format(command))
        (output, returncode) = executeCommand(command)
        del output
        debug('Updater execute command finished')

    def CheckVersion(self, currentVersion, newVersion):
        debug('')
        bVal = False
        try:
            bVal = LooseVersion(currentVersion) < LooseVersion(newVersion)
        except:
            exception('CheckVersion failed')
        return bVal
