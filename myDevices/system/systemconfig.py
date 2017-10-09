"""
This module provides a class for modifying system configuration settings.
"""
from time import sleep
from myDevices.utils.logger import exception, info, warn, error, debug
from myDevices.utils.subprocess import executeCommand
from myDevices.utils.threadpool import ThreadPool
from myDevices.system.hardware import Hardware

CUSTOM_CONFIG_SCRIPT = "/etc/myDevices/scripts/config.sh"

class SystemConfig:
    """Class for modifying configuration settings"""

    @staticmethod
    def ExpandRootfs():
        """Expand the filesystem"""
        command = "sudo raspi-config --expand-rootfs"
        debug('ExpandRootfs command:' + command)
        (output, returnCode) = executeCommand(command)
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
        if any(model in Hardware().getModel() for model in ('Tinker Board', 'BeagleBone')):
            return (1, 'Not supported')
        debug('SystemConfig::ExecuteConfigCommand')
        if config_id == 0:
            return SystemConfig.ExpandRootfs()
        command = "sudo " + CUSTOM_CONFIG_SCRIPT + " " + str(config_id) + " " + str(parameters)
        (output, returnCode) = executeCommand(command)        
        debug('ExecuteConfigCommand '+ str(config_id) + ' args: ' + str(parameters) + ' retCode: ' + str(returnCode) + ' output: ' + output )
        if "reboot required" in output:
            ThreadPool.Submit(SystemConfig.RestartService)
        return (returnCode, output)

    @staticmethod
    def RestartService():
        """Reboot the device"""
        sleep(5)
        command = "sudo shutdown -r now"
        (output, returnCode) = executeCommand(command)

    @staticmethod
    def getConfig():
        """Return dict containing configuration settings"""
        configItem = {}
        if any(model in Hardware().getModel() for model in ('Tinker Board', 'BeagleBone')):
            return configItem
        # try:
        #     (returnCode, output) = SystemConfig.ExecuteConfigCommand(17, '')
        #     if output:
        #         values = output.strip().split(' ')
        #         configItem['Camera'] = {}
        #         for i in values:
        #             if '=' in i:
        #                 val1 = i.split('=')
        #                 configItem['Camera'][val1[0]] = int(val1[1])
        #     del output
        # except:
        #     exception('Get camera config')

        try:
            (returnCode, output) = SystemConfig.ExecuteConfigCommand(10, '')
            if output:
                configItem['DeviceTree'] = int(output.strip())
            del output
            (returnCode, output) = SystemConfig.ExecuteConfigCommand(18, '')
            if output:
                configItem['Serial'] = int(output.strip())
            del output
            (returnCode, output) = SystemConfig.ExecuteConfigCommand(20, '')
            if output:
                configItem['OneWire'] = int(output.strip())
            del output
        except:
            exception('Get config')
        info('SystemConfig: {}'.format(configItem))
        return configItem