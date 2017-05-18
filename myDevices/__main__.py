from myDevices.utils.config import Config
from os import path, getpid
from myDevices.cloud.client import CloudServerClient
from myDevices.utils.logger import exception, setDebug, info, debug, error, logToFile, setInfo
from sys import excepthook, __excepthook__, argv
from threading import Thread
from signal import signal, SIGUSR1, SIGINT
from resource import getrlimit, setrlimit, RLIMIT_AS
from myDevices.os.services import ProcessInfo
from myDevices.os.daemon import Daemon

def setMemoryLimit(rsrc, megs = 200):
    size = megs * 1048576
    soft, hard = getrlimit(rsrc)
    setrlimit(rsrc, (size, hard)) #limit to one kilobyte
    soft, hard = getrlimit(rsrc)
    info ('Limit changed to :'+ str( soft))
try:
    #setMemoryLimit(RLIMIT_DATA)
    #setMemoryLimit(RLIMIT_STACK)
    setMemoryLimit(RLIMIT_AS)
except Exception as e:
    error('Cannot set limit to memory: ' + str(e))

client = None
def signal_handler(signal, frame):
    if client:
        if signal == SIGINT:
            info('Program interrupt received, client exiting')
            client.Destroy()
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
    debug('Daemon::threadExceptionHook ')
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
    configfile = None
    scriptfile = None
    logfile = None
    isDebug = False
    i = 1
    setInfo()
    while i < len(argv):
        if argv[i] in ["-c", "-C", "--config-file"]:
            configfile = argv[i+1]
            i+=1
        elif argv[i] in ["-l", "-L", "--log-file"]:
            logfile = argv[i+1]
            i+=1
        elif argv[i] in ["-h", "-H", "--help"]:
            displayHelp()
        elif argv[i] in ["-d", "--debug"]:
            setDebug()
        elif argv[i] in ["-P", "--pidfile"]:
            pidfile = argv[i+1]
            i+=1
            writePidToFile(pidfile)
        i+=1
    if configfile == None:
        configfile = '/etc/myDevices/Network.ini'
    logToFile(logfile)
    # SET HOST AND PORT
    config = Config(configfile)
    HOST = config.get('CONFIG','ServerAddress', 'cloud.mydevices.com')
    PORT = config.getInt('CONFIG','ServerPort', 8181)
    CayenneApiHost = config.get('CONFIG', 'CayenneApi', 'https://api.mydevices.com')
    # CREATE SOCKET
    global client 
    client = CloudServerClient(HOST, PORT, CayenneApiHost)

if __name__ == "__main__":
    try:
        main(argv)
    except Exception as e:
        exception(e)
