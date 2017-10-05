"""
This module provides a class for restarting the agent if errors occur and exiting on critical failures.
"""
from sys import exit
from datetime import datetime
from myDevices.utils.logger import exception, info, warn, error, debug
from myDevices.utils.subprocess import executeCommand

#defining reset timeout in seconds
RESET_TIMEOUT = 30
FAILURE_COUNT = 1000
failureCount = {}
startFailure = {}
errorList = (-3, -2, 12, 9, 24)


class Daemon:
    """class for restarting the agent if errors occur and exiting on critical failures."""

    @staticmethod
    def OnFailure(component, error=0):
        """Handle error in component and restart the agent if necessary"""
        #-3=Temporary failure in name resolution
        info('Daemon failure handling ' + str(error))
        if error in errorList:
            Daemon.Restart()
        if component not in failureCount:
            Daemon.Reset(component)
        failureCount[component] += 1
        now = datetime.now()
        if startFailure[component] == 0:
            startFailure[component] = now
        elapsedTime = now - startFailure[component]
        if (elapsedTime.total_seconds() >= RESET_TIMEOUT) or (failureCount[component] > FAILURE_COUNT):
            warn('Daemon::OnFailure myDevices is going to restart after ' + str(component) + ' failed: ' + str(elapsedTime.total_seconds()) + ' seconds and ' + str(failureCount) + ' times')
            Daemon.Restart()

    @staticmethod
    def Reset(component):
        """Reset failure count for component"""
        startFailure[component] = 0
        failureCount[component] = 0

    @staticmethod
    def Restart():
        """Restart the agent daemon"""
        try:
            info('Daemon restarting myDevices' )
            (output, returncode) = executeCommand('sudo service myDevices restart')
            debug(str(output) + ' ' + str(returncode))
            del output
        except:
            exception("Daemon::Restart enexpected error")
            Daemon.Exit()

    @staticmethod
    def Exit():
        """Stop the agent daemon"""
        info('Critical failure. Closing myDevices process...')
        exit('Daemon::Exit closing agent. Critical failure.')




