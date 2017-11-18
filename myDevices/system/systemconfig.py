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
    def ExecuteConfigCommand(config_id, parameters=''):
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
            ThreadPool.Submit(SystemConfig.RestartDevice)
        return (returnCode, output)

    @staticmethod
    def RestartDevice():
        """Reboot the device"""
        sleep(5)
        command = "sudo shutdown -r now"
        (output, returnCode) = executeCommand(command)

    @staticmethod
    def getConfig():
        """Return dict containing configuration settings"""
        config = {}
        if any(model in Hardware().getModel() for model in ('Tinker Board', 'BeagleBone')):
            return config
        commands = {10: 'DeviceTree', 18: 'Serial', 20: 'OneWire', 21: 'I2C', 22: 'SPI'}
        for command, name in commands.items():
            try:
                (returnCode, output) = SystemConfig.ExecuteConfigCommand(command)
                if output:
                    config[name] = 1 - int(output.strip()) #Invert the value since the config script uses 0 for enable and 1 for disable
            except:
                exception('Get config')
        info('SystemConfig: {}'.format(config))
        return config
