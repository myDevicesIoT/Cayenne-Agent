"""
This module provides a class for modifying Raspberry Pi configuration settings.
"""
from myDevices.utils.logger import exception, info, warn, error, debug
from myDevices.system.services import ServiceManager
from time import sleep
from myDevices.utils.threadpool import ThreadPool

CUSTOM_CONFIG_SCRIPT = "/etc/myDevices/scripts/config.sh"

class RaspiConfig:
    """Class for modifying configuration settings"""

    @staticmethod
    def ExpandRootfs():
        """Expand the filesystem"""
        command = "sudo raspi-config --expand-rootfs"
        debug('ExpandRootfs command:' + command)
        (output, returnCode) = ServiceManager.ExecuteCommand(command)
        debug('ExpandRootfs command:' + command + " retCode: " + returnCode)
        output = 'reboot required'
        return (returnCode, output)

    @staticmethod
    def ExecuteConfigCommand(config_id, parameters):
        """Execute specified command to modify configuration
        
        Args:
            config_id: Id of command to run
            parameters: Parameters to use when executing command
        """
        debug('RaspiConfig::ExecuteConfigCommand')
        if config_id == 0:
            return RaspiConfig.ExpandRootfs()
        command = "sudo " + CUSTOM_CONFIG_SCRIPT + " " + str(config_id) + " " + str(parameters)
        (output, returnCode) = ServiceManager.ExecuteCommand(command)        
        debug('ExecuteConfigCommand '+ str(config_id) + ' args: ' + str(parameters) + ' retCode: ' + str(returnCode) + ' output: ' + output )
        if "reboot required" in output:
            ThreadPool.Submit(RaspiConfig.RestartService)
        return (returnCode, output)

    @staticmethod
    def RestartService():
        """Reboot the device"""
        sleep(5)
        command = "sudo shutdown -r now"
        (output, returnCode) = ServiceManager.ExecuteCommand(command)

    @staticmethod
    def getConfig():
        """Return dict containing configuration settings"""
        configItem = {}
        try:
            (returnCode, output) = RaspiConfig.ExecuteConfigCommand(17, '')
            if output:
                values = output.strip().split(' ')
                configItem['Camera'] = {}
                for i in values:
                    if '=' in i:
                        val1 = i.split('=')
                        configItem['Camera'][val1[0]] = int(val1[1])
            del output
        except:
            exception('Camera config')

        try:
            (returnCode, output) = RaspiConfig.ExecuteConfigCommand(10, '')
            if output:
                configItem['DeviceTree'] = int(output.strip())
            del output
            (returnCode, output) = RaspiConfig.ExecuteConfigCommand(18, '')
            if output:
                configItem['Serial'] = int(output.strip())
            del output
            (returnCode, output) = RaspiConfig.ExecuteConfigCommand(20, '')
            if output:
                configItem['OneWire'] = int(output.strip())
            del output
        except:
            exception('Camera config')
        info('RaspiConfig: {}'.format(configItem))
        return configItem