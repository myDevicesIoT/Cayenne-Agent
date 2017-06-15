"""
This module is the main entry point for the Cayenne agent. It processes any command line parameters and launches the client.
"""
from os import path, getpid, remove
from sys import __excepthook__, argv, maxsize
from threading import Thread
from myDevices.utils.config import Config
from myDevices.cloud.client import CloudServerClient
from myDevices.utils.logger import exception, setDebug, info, debug, error, logToFile, setInfo
from signal import signal, SIGUSR1, SIGINT
from resource import getrlimit, setrlimit, RLIMIT_AS
from myDevices.os.services import ProcessInfo
from myDevices.utils.daemon import Daemon

def setMemoryLimit(rsrc, megs=200):
    """Set the memory usage limit for the agent process"""
    size = megs * 1048576
    soft, hard = getrlimit(rsrc)
    setrlimit(rsrc, (size, hard)) #limit to one kilobyte
    soft, hard = getrlimit(rsrc)

try:
    #Only set memory limit on 32-bit systems
    if maxsize <= 2**32:
        setMemoryLimit(RLIMIT_AS)
except Exception as ex:
    print('Cannot set limit to memory: ' + str(ex))

client = None
pidfile = '/var/run/myDevices/cayenne.pid'
def signal_handler(signal, frame):
    """Handle program interrupt so the agent can exit cleanly"""
    if client:
        if signal == SIGINT:
            info('Program interrupt received, client exiting')
            client.Destroy()
            remove(pidfile)
        else:
            client.Restart()
signal(SIGUSR1, signal_handler)
signal(SIGINT, signal_handler)

def exceptionHook(exc_type, exc_value, exc_traceback):
    """Make sure any uncaught exceptions are logged"""
    debug('Daemon::exceptionHook ')
    if issubclass(exc_type, KeyboardInterrupt):
        __excepthook__(exc_type, exc_value, exc_traceback)
        return
    error("Uncaught exception", exc_info=(exc_type, exc_value, exc_traceback))
   

def threadExceptionHook():
    """Make sure any child threads hook exceptions. This should be called before any threads are created."""
    debug('Daemon::threadExceptionHook')
    init_original = Thread.__init__
    def init(self, *args, **kwargs):
        init_original(self, *args, **kwargs)
        run_original = self.run
        def run_with_except_hook(*args, **kw):
            try:
                run_original(*args, **kw)
            except (KeyboardInterrupt, SystemExit):
                raise
            except:
                exception('Uncaught exception in thread ' + self.name)
        self.run = run_with_except_hook
    Thread.__init__ = init

    
excepthook = exceptionHook
threadExceptionHook()


def displayHelp():
    print("myDevices command-line usage")
    print("myDevices [-h] [-c config] [-l log] [-d]")
    print("")
    print("Options:")
    print("  -h, --help            Display this help")
    print("  -c, --config file     Load config from file")
    print("  -l, --log file        Log to file")
    print("  -d, --debug           Enable DEBUG")
    print("  -t, --test            Enable TEST mode")
    exit()

def writePidToFile(pidfile):
    """Write the process ID to a file to prevent multiple agents from running at the same time"""
    if path.isfile(pidfile):
        info(pidfile + " already exists, exiting")
        with open(pidfile, 'r') as file:
            pid = int(file.read())
            if ProcessInfo.IsRunning(pid) and pid != getpid():
                Daemon.Exit()
                return
    pid = str(getpid())
    with open(pidfile, 'w') as file:
        file.write(pid)

def main(argv):
    """Main entry point for starting the agent client"""
    global pidfile
    configfile = None
    logfile = None
    i = 1
    setInfo()
    while i < len(argv):
        if argv[i] in ["-c", "-C", "--config-file"]:
            configfile = argv[i+1]
            i += 1
        elif argv[i] in ["-l", "-L", "--log-file"]:
            logfile = argv[i+1]
            i += 1
        elif argv[i] in ["-h", "-H", "--help"]:
            displayHelp()
        elif argv[i] in ["-d", "--debug"]:
            setDebug()
        elif argv[i] in ["-P", "--pidfile"]:
            pidfile = argv[i+1]
            i += 1
        i += 1
    if configfile == None:
        configfile = '/etc/myDevices/Network.ini'
    writePidToFile(pidfile)
    logToFile(logfile)
    config = Config(configfile)
    HOST = config.get('CONFIG', 'ServerAddress', 'cloud.mydevices.com')
    PORT = config.getInt('CONFIG', 'ServerPort', 8181)
    CayenneApiHost = config.get('CONFIG', 'CayenneApi', 'https://api.mydevices.com')
    global client
    client = CloudServerClient(HOST, PORT, CayenneApiHost)

if __name__ == "__main__":
    try:
        main(argv)
    except Exception as e:
        exception(e)
