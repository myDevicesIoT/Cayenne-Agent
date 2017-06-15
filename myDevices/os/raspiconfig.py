from myDevices.utils.logger import exception, info, warn, error, debug
from myDevices.os.services import ServiceManager
from time import sleep
from myDevices.utils.threadpool import ThreadPool

CUSTOM_CONFIG_SCRIPT = "/etc/myDevices/scripts/config.sh"

class RaspiConfig:
    def Config(config_id, parameters):
        if config_id == 0:
            return RaspiConfig.ExpandRootfs()
        else:
            return RaspiConfig.ExecuteConfigCommand(config_id, parameters)
    def ExpandRootfs():
        command = "sudo raspi-config --expand-rootfs"
        debug('ExpandRootfs command:' + command)
        (output, returnCode) = ServiceManager.ExecuteCommand(command)
        debug('ExpandRootfs command:' + command + " retCode: " + returnCode)
        output = 'reboot required'
        return (returnCode, output)
    def ExecuteConfigCommand(config_id, parameters):
        debug('RaspiConfig::config')
        command = "sudo " + CUSTOM_CONFIG_SCRIPT + " " + str(config_id) + " " + str(parameters)
        (output, returnCode) = ServiceManager.ExecuteCommand(command)        
        debug('ExecuteConfigCommand '+ str(config_id) + ' args: ' + str(parameters) + ' retCode: ' + str(returnCode) + ' output: ' + output )
        if "reboot required" in output:
            ThreadPool.Submit(RaspiConfig.RestartService)
        #del output
        return (returnCode, output)
    def RestartService():
        sleep(5)
        command = "sudo shutdown -r now"
        (output, returnCode) = ServiceManager.ExecuteCommand(command) 
    def getConfig():
        configItem = {}
        try:
            (returnCode, output) = RaspiConfig.ExecuteConfigCommand(17, '')
            if output:
                print('output: ' + output)
                values = output.strip().split(' ')
                configItem['Camera'] = {}
                for i in values:
                    val1 = i.split('=')
                    configItem['Camera'][val1[0]] = int(val1[1])
            del output
        except:
            exception('Camera config')

        try:
            (returnCode, output) = RaspiConfig.ExecuteConfigCommand(10, '')
            if output:
                print('output: ' + output)
                configItem['DeviceTree'] = int(output.strip())
            del output
            (returnCode, output) = RaspiConfig.ExecuteConfigCommand(18, '')
            if output:
                print('output: ' + output)
                configItem['Serial'] = int(output.strip())
            del output
            (returnCode, output) = RaspiConfig.ExecuteConfigCommand(20, '')
            if output:
                print('output: ' + output)
                configItem['OneWire'] = int(output.strip())
            del output
        except:
            exception('Camera config')
        return configItem