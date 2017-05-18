from datetime import datetime, timedelta
from os import path, remove
from urllib import request, error
from myDevices.utils.logger import exception, info, warn, error, debug
from threading import Thread
from time import sleep
from random import randint
from socket import error as socket_error
from myDevices.os.daemon import Daemon
from myDevices.os.threadpool import ThreadPool

defaultUrl = "http://updates.mydevices.com/test/10MB.zip"
download_path = "/etc/myDevices/test"
mb = 1024*1024
#in seconds download Rate = 24 hours
defaultDownloadRate = 24*60*60

class DownloadSpeed():
    def __init__(self, config):
        self.downloadSpeed = None
        self.uploadSpeed = None
        self.testTime = None
        self.isRunning = False
        self.Start()
        self.config = config
        #add a random delay to the start of download 
        self.delay = randint(0,100)
    def Start(self):
        #thread = Thread(target = self.Test)
        #thread.start()
        ThreadPool.Submit(self.Test)
    def Test(self):
        if self.isRunning:
            return False
        self.isRunning = True
        sleep(1)
        self.TestDownload()
        sleep(1)
        self.TestUpload()
        self.testTime = datetime.now()
        self.isRunning = False
        return True
    def TestDownload(self):
        try:
            a = datetime.now()
            info('Excuting regular download test for network speed')
            url = self.config.cloudConfig.DownloadSpeedTestUrl if 'DownloadSpeedTestUrl' in self.config.cloudConfig else defaultUrl
            debug(url + ' ' + download_path)
            request.urlretrieve(url, download_path)
            request.urlcleanup()
            b = datetime.now()
            c = b - a
            if path.exists(download_path):
                size = path.getsize(download_path)/mb
                self.downloadSpeed = size/c.total_seconds()
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
    def TestUpload(self):
        debug('Network Speed TestUpload - Not implemented')
        self.uploadSpeed = 0
    def IsDownloadTime(self):
        if self.testTime is None:
            return True
        downloadRate = int(self.config.cloudConfig.DownloadSpeedTestRate) if 'DownloadSpeedTestRate' in self.config.cloudConfig else defaultDownloadRate
        if self.testTime +timedelta(seconds=downloadRate+self.delay ) < datetime.now():
            return True
        return False
    def getDownloadSpeed(self):
        if self.IsDownloadTime():
            self.Start()
        return self.downloadSpeed
    def getUploadSpeed(self):
        return self.uploadSpeed    

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
