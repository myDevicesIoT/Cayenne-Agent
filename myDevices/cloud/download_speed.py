"""
This module provides a class for testing download speed
"""
from datetime import datetime, timedelta
from os import path, remove
from urllib import request, error
from myDevices.utils.logger import exception, info, warn, error, debug
from time import sleep
from random import randint
from socket import error as socket_error
from myDevices.utils.daemon import Daemon
from myDevices.utils.threadpool import ThreadPool

defaultUrl = "https://updates.mydevices.com/test/10MB.zip"
download_path = "/etc/myDevices/test"
mb = 1024*1024
#in seconds download Rate = 24 hours
defaultDownloadRate = 24*60*60

class DownloadSpeed():
    """Class for checking download speed"""

    def __init__(self, config):
        """Initialize variables and start download speed test"""
        self.downloadSpeed = None
        self.testTime = None
        self.isRunning = False
        self.Start()
        self.config = config
        #add a random delay to the start of download 
        self.delay = randint(0, 100)

    def Start(self):
        """Start download speed thread"""
        ThreadPool.Submit(self.Test)

    def Test(self):
        """Run speed test"""
        if self.isRunning:
            return False
        self.isRunning = True
        sleep(1)
        self.TestDownload()
        sleep(1)
        self.testTime = datetime.now()
        self.isRunning = False
        return True

    def TestDownload(self):
        """Test download speed by retrieving a file"""
        try:
            info('Executing regular download test for network speed')
            url = self.config.get('Agent', 'DownloadSpeedTestUrl', defaultUrl)
            debug(url + ' ' + download_path)
            a = datetime.now()
            request.urlretrieve(url, download_path)
            b = datetime.now()
            request.urlcleanup()
            c = b - a
            if path.exists(download_path):
                size = path.getsize(download_path)/mb
                self.downloadSpeed = size/c.total_seconds() * 8 #Convert to megabits per second
                remove(download_path)
                return True
        except socket_error as serr:
            error ('TestDownload:' + str(serr))
            ret = False
            Daemon.OnFailure('cloud', serr.errno)
            return
        except:
            exception('TestDownload Failed')
        return False

    def IsDownloadTime(self):
        """Return true if it is time to run a new download speed test"""
        if self.testTime is None:
            return True
        downloadRate = self.config.getInt('Agent', 'DownloadSpeedTestRate', defaultDownloadRate)
        if self.testTime + timedelta(seconds=downloadRate+self.delay ) < datetime.now():
            return True
        return False

    def getDownloadSpeed(self):
        """Start a new download speed test if necessary and return the download speed"""
        if self.IsDownloadTime():
            self.Start()
        return self.downloadSpeed

def Test():
    from myDevices.utils.config import Config    
    testDownload = DownloadSpeed(Config('/etc/myDevices/AppSettings.ini'))
    speed = testDownload.getDownloadSpeed()
    print('Download speed 1: ' + str(speed))
    sleep(20)
    speed = testDownload.getDownloadSpeed()
    print('Download speed 2: ' + str(speed))
    sleep(20)
    speed = testDownload.getDownloadSpeed()
    print('Download speed 3: ' + str(speed))
