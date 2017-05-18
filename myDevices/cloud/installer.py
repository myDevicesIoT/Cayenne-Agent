from os import path, remove
from time import sleep
from myDevices.os import services
from myDevices.os.threadpool import ThreadPool
from myDevices.utils.config import Config
from myDevices.utils.logger import exception, info, debug

INSTALL_PATH = '/etc/myDevices'
PACKAGE_PATH = INSTALL_PATH + '/package'

class Installer():
    def __init__(self, config):
        self.installedSections = []
        #adding base
        self.installedSections.append('system')
        self.installedSections.append('core')
        self.totalSections = 1
        self.totalSteps = 5
        self.currentStep = None
        self.appSettings = config
    def reset(self):
        installSettings = Config(PACKAGE_PATH)
        installSettings.set('DEFAULT', 'isInstalled', '1')
    def start(self):
        if path.exists(PACKAGE_PATH):
            ThreadPool.Submit(self.run)
    def run(self):
        installerPackages = None
        info('Package install checking for required install packages... ')
        isRebootRequired = 1
        updateProgressPath = None
        inviteCode = None
        try:
            if path.exists(PACKAGE_PATH) == False:
                return
            installSettings = Config(PACKAGE_PATH)
            sleep(1)
            installerSections = installSettings.sections()
            self.totalSections=self.totalSections + len(installerSections) 
            self.totalSteps = int(installSettings.get('DEFAULT','total'))
            isInstalled = 0
            try:
                isInstalled = installSettings.get('DEFAULT', 'isInstalled')
            except:
                pass
            if isInstalled == 1:
                debug('Package already installed')
                return
            isRebootRequired = installSettings.get('DEFAULT','isRebootRequired')
            updateProgressPath = self.appSettings.get('Agent', 'UpdateProgress')
            inviteCode = self.appSettings.get('Agent', 'InviteCode')
        except:
            exception('Installer No package sections')
            return
        info('Package install started')
        bUpdateRequired = False
        for packageSection in installerSections:
            try:
                info('Getting package sections:' + packageSection)
                isInstalled = 0
                sleep(1)
                try:
                    isInstalled = installSettings.get(packageSection,'installed')
                    self.currentStep = installSettings.get(packageSection,'step')
                except:
                    isInstalled = 0
                if isInstalled == 1:
                    self.installedSections.append(packageSection)
                    continue
                installPath = installSettings.get(packageSection,'path')
                SETUP_PATH = INSTALL_PATH + installPath.strip()
                if path.exists(SETUP_PATH) == False:
                    info('Installer package not found: ' + SETUP_PATH)
                    continue
                command = "chmod +x " + SETUP_PATH
                (output, returncode) = services.ServiceManager.ExecuteCommand(command)
                del output
                command = "sudo sh " + SETUP_PATH + " > /var/log/" + packageSection + ".log"
                (output, returncode) = services.ServiceManager.ExecuteCommand(command)
                del output
                if inviteCode and updateProgressPath and self.currentStep:
                    command = "sudo nohup curl --data \"invitecode=" + inviteCode + "&progress=100&step=" + str(self.currentStep) + "\" " + updateProgressPath + " &>-"
                    (output, returncode) = services.ServiceManager.ExecuteCommand(command)
                    del output
                if returncode == 0:
                    installSettings.set(packageSection, 'installed', '1')
                    self.installedSections.append(packageSection)
                bUpdateRequired = True
            except:
                exception('Installer failed')
        installSettings.set('DEFAULT', 'isRebootRequired', '0')
        installSettings.set('DEFAULT', 'isInstalled', '1')
        if bUpdateRequired:
            command = "sudo nohup curl --data \"invitecode=" + inviteCode + "&progress=100&step=" + str(self.totalSteps+1) + "\" " + updateProgressPath + " &>-"
            (output, returncode) = services.ServiceManager.ExecuteCommand(command)
        #remove(PACKAGE_PATH)
        if int(isRebootRequired) == 1:
            from myDevices.os.daemon import Daemon
            Daemon.Restart()
        info('Package install finished')
