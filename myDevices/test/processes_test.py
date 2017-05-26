import unittest
from myDevices.os.services import ProcessManager

class ProcessesTest(unittest.TestCase):
    def testProcesses(self):
        processManager = ProcessManager()
        processManager.Run()
        print(processManager.GetProcessList())
        
if __name__ == '__main__':
    unittest.main()