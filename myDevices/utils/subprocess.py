"""
This module contains functions for launching subprocesses and returning output from them.
"""
from subprocess import Popen, PIPE
from myDevices.utils.logger import debug, info, error, exception

def setMemoryLimits():
    """Set memory limit when launching a process to the default maximum"""
    try:
        from resource import getrlimit, setrlimit, RLIMIT_AS
        soft, hard = getrlimit(RLIMIT_AS)
        setrlimit(RLIMIT_AS, (hard, hard))
    except:
        pass

def executeCommand(command, increaseMemoryLimit=False):
    """Execute a specified command, increasing the processes memory limits if specified"""
    debug('executeCommand: ' +  command)
    output = ''
    returncode = 1
    try:
        setLimit = None
        if increaseMemoryLimit:
            setLimit = setMemoryLimits
        process = Popen(command, stdout=PIPE, shell=True, preexec_fn=setLimit)
        processOutput = process.communicate()
        returncode = process.wait()
        returncode = process.returncode
        debug('executeCommand: ' + str(processOutput))
        if processOutput and processOutput[0]:
            output = str(processOutput[0].decode('utf-8'))
            processOutput = None
    except:
        exception('executeCommand failed: ' + command)
    debug('executeCommand: ' +  command + ' ' + str(output))
    retOut = str(output)
    return (retOut, returncode)
