"""
This module provides classes for retrieving process and service info, as well as managing processes and services.
"""
from subprocess import Popen, PIPE
from enum import Enum, unique
from threading import RLock
from psutil import Process, process_iter, virtual_memory, cpu_percent
from myDevices.utils.logger import exception, info, warn, error, debug

class ProcessInfo:
    """Class for getting process info and killing processes"""

    def __init__(self):
        """Initialize process information"""
        self.Name = None
        self.Pid = None
        self.Username = None
        self.Cmdline = None

    def Terminate(self):
        """Terminate the process"""
        info('ProcessManager::Terminate Name:' + self.Name + ' PID:' + str(self.Pid))
        try:
            process = Process(self.Pid)
            process.terminate()
        except Exception as ex:
            error('ProcessInfo::Terminate failed Name:' + self.Name + ' PID:'  + str(self.Pid) + ' Exception:' + str(ex))
            return False
        return True

    @staticmethod
    def IsRunning(pid):
        """Return True if process with specified pid is running"""
        try:
            process = Process(pid)
        except Exception as ex:
            debug('Exception on pid:' + str(pid) + ' ' + str(ex))
            return False
        return True

class ProcessManager:
    """Class for retrieving running processes and processor usage info"""

    def __init__(self):
        """Initialize process and processor info"""
        debug('')
        self.mapProcesses = {}
        self.VisibleMemory = 0
        self.AvailableMemory =  0
        self.PercentProcessorTime = 0
        self.AverageProcessorUsage = 0
        self.PeakProcessorUsage = 0
        self.AverageMemoryUsage = 0
        self.PeakMemoryUsage = 0
        self.totalMemoryCount = 0
        self.totalProcessorCount = 0
        self.mutex = RLock()

    def Run(self):
        """Get running process info"""
        debug('')
        try:
            running_processes = []
            with self.mutex:
                for p in process_iter():
                    running_processes.append(p.pid)
                    try:
                        if p.pid not in self.mapProcesses or self.mapProcesses[p.pid].Name != p.name:
                            processInfo = ProcessInfo()
                            processInfo.Pid = p.pid
                            processInfo.Name = p.name() if callable(p.name) else p.name
                            processInfo.Username = p.username() if callable(p.username) else p.username
                            processInfo.Cmdline = p.cmdline() if callable(p.cmdline) else p.cmdline
                            self.mapProcesses[p.pid] = processInfo
                    except Exception:
                        pass
                remove = [key for key in self.mapProcesses.keys() if key not in running_processes]
                for key in remove:
                    del self.mapProcesses[key]
                debug('ProcessManager::Run retrieved {} processes'.format(len(self.mapProcesses)))
        except:
            exception('ProcessManager::Run failed')
        debug('ProcessManager::Run retrieved {} processes'.format(len(self.mapProcesses)))

    def GetProcessList(self):
        """Return list of running processes"""
        process_list = []
        with self.mutex:
            for key, value in self.mapProcesses.items():
                process = {}
                process['processName'] = value.Name
                if len(value.Cmdline) >= 1:
                    process['description'] = value.Cmdline[0]
                else:
                    process['description'] = value.Name
                process['companyName'] = value.Username
                process['pid'] = value.Pid
                process_list.append(process)
        return process_list

    def KillProcess(self, pid):
        """Kill the process specified by pid"""
        retVal = False
        with self.mutex:
            process = self.mapProcesses.get(pid)
            if process:
                try:
                    p = Process(pid)
                    if p.name == process.Name and p.username == process.Username and p.getcwd() == process.Cwd:
                        retVal = process.Terminate()
                except Exception as e:
                    debug('KillProcess: {}'.format(e))
                    pass
        return retVal

    def RefreshProcessManager(self):
        """Refresh processor usage and memory info"""
        try:
            if self.VisibleMemory:
                del self.VisibleMemory
                self.VisibleMemory = None
            memory = virtual_memory()
            self.VisibleMemory = memory.total
            if self.AvailableMemory:
                del self.AvailableMemory
                self.AvailableMemory = None
            self.AvailableMemory = memory.available
            del memory
            if self.PercentProcessorTime:
                del self.PercentProcessorTime
                self.PercentProcessorTime = None
            self.PercentProcessorTime = cpu_percent()
            self.totalMemoryCount += 1
            self.totalProcessorCount += 1
            self.AverageProcessorUsage = (self.AverageProcessorUsage * (self.totalProcessorCount - 1) + self.PercentProcessorTime) / self.totalProcessorCount
            if self.PeakProcessorUsage < self.PercentProcessorTime:
                self.PeakProcessorUsage = self.PercentProcessorTime
            self.AverageMemoryUsage = (self.AverageMemoryUsage * (self.totalMemoryCount - 1) + self.AvailableMemory) / self.totalMemoryCount
            if self.PeakMemoryUsage < self.AvailableMemory:
                self.PeakMemoryUsage = self.AvailableMemory
        except:
            exception('ProcessManager::RefreshProcessManager failed')

@unique
class ServiceState(Enum):
    Unknown = 0
    Running = 1
    NotRunning = 2
    NotAvailable = 3

class ServiceManager:
    """Class for retrieving service info and managing services"""

    def __init__(self):
        """Initialize service info"""
        self.Init = True
        self.mapServices = {}
        self.mutex = RLock()

    def Run(self):
        """Get info about services"""
        debug('ServiceManager::Run')
        with self.mutex:
            (output, returnCode) = ServiceManager.ExecuteCommand("service --status-all")
            servicesList = output.split("\n")
            service_names = []
            for line in servicesList:
                splitLine = line.strip().split(' ')
                if len(splitLine) == 5:
                    name = splitLine[4]
                    status = None
                    if splitLine[1] == '?':
                        status = ServiceState.NotAvailable.value
                    if splitLine[1] == '+':
                        status = ServiceState.Running.value
                    if splitLine[1] == '-':
                        status = ServiceState.NotRunning.value
                    self.mapServices[name] = status
                    service_names.append(name)
            remove = [key for key in self.mapServices.keys() if key not in service_names]
            for key in remove:
                del self.mapServices[key]
        debug('ServiceManager::Run retrieved ' + str(len(self.mapServices)) + ' services')
        del output

    def GetServiceList(self):
        """Return list of services"""
        service_list = []
        with self.mutex:
            for key, value in self.mapServices.items():
                process = {}
                process['ProcessName'] = str(key)
                process['ProcessDescription'] = str(value)
                process['CompanyName'] = str(key)
                service_list.append(process)
        return service_list

    def Start(self, serviceName):
        """Start the named service"""
        debug('ServiceManager::Start')
        command = "sudo service " + serviceName + " start"
        (output, returnCode) = ServiceManager.ExecuteCommand(command)
        debug('ServiceManager::Start command:' + command + " output: " + output)
        del output
        return returnCode

    def Stop(self, serviceName):
        """Stop the named service"""
        debug('ServiceManager::Stop')
        command = "sudo service " + serviceName + " stop"
        (output, returnCode) = ServiceManager.ExecuteCommand(command)
        debug('ServiceManager::Stop command:' + command + " output: " + output)
        del output
        return returnCode

    def Status(self, serviceName):
        """Get the status of the named service"""
        debug('ServiceManager::Status')
        command = "service " + serviceName + " status"
        (output, returnCode) = ServiceManager.ExecuteCommand(command)
        debug('ServiceManager::Stop command:' + command + " output: " + output)
        del output
        return returnCode

    @staticmethod
    def SetMemoryLimits():
        """Set memory limit when launching a process to the default maximum"""
        try:
            from resource import getrlimit, setrlimit, RLIMIT_AS
            soft, hard = getrlimit(RLIMIT_AS)
            setrlimit(RLIMIT_AS, (hard, hard))
        except:
            pass

    @staticmethod
    def ExecuteCommand(command, increaseMemoryLimit=False):
        """Execute a specified command, increasing the processes memory limits if specified"""
        debug('ServiceManager::ExecuteCommand: ' +  command)
        output = ""
        returncode = 1
        try:
            setLimit = None
            if increaseMemoryLimit:
                setLimit = ServiceManager.SetMemoryLimits
            process = Popen(command, stdout=PIPE, shell=True, preexec_fn=setLimit)
            processOutput = process.communicate()
            returncode = process.wait()
            returncode = process.returncode
            debug('ServiceManager::ExecuteCommand: ' + str(processOutput))
            if processOutput and processOutput[0]:
                output = str(processOutput[0].decode('utf-8'))
                processOutput = None
        except OSError as oserror:
            warn('ServiceManager::ExecuteCommand handled: ' + command + ' Exception:' + str(traceback.format_exc()))
            from myDevices.utils.daemon import Daemon
            Daemon.OnFailure('services', oserror.errno)
        except:
            exception('ServiceManager::ExecuteCommand failed: ' + command)
        debug('ServiceManager::ExecuteCommand: ' +  command + ' ' + str(output))
        retOut = str(output)
        del output
        return (retOut, returncode)
