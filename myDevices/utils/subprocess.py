"""
This module contains functions for launching subprocesses and returning output from them.
"""
from subprocess import Popen, PIPE, DEVNULL
from myDevices.utils.logger import debug, info, error, exception

def setMemoryLimits():
    """Set memory limit when launching a process to the default maximum"""
    try:
        from resource import getrlimit, setrlimit, RLIMIT_AS
        soft, hard = getrlimit(RLIMIT_AS)
        setrlimit(RLIMIT_AS, (hard, hard))
    except:
        pass

def executeCommand(command, increaseMemoryLimit=False, disablePipe=False):
    """Execute a specified command, increasing the processes memory limits if specified"""
    debug('executeCommand: ' +  command)
    output = ''
    returncode = 1
    try:
        preexec = None
        pipe = PIPE
        if increaseMemoryLimit:
            preexec = setMemoryLimits
        if disablePipe:
            debug('Disable pipe to prevent child exiting when parent exits')
            pipe = DEVNULL
        process = Popen(command, stdout=pipe, stderr=pipe, shell=True, preexec_fn=preexec)
        (stdout_data, stderr_data) = process.communicate()
        returncode = process.wait()
        returncode = process.returncode
        # debug('executeCommand: stdout_data {}, stderr_data {}'.format(stdout_data, stderr_data))
        if stdout_data:
            output = stdout_data.decode('utf-8')
            stdout_data = None
    except:
        exception('executeCommand failed: ' + command)
    return (output, returncode)
