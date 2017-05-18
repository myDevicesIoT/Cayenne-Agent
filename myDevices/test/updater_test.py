import unittest
from myDevices.cloud.updater import Updater
from myDevices.utils.config import Config
from myDevices.utils.logger import exception, info, warn, error, debug, setDebug, setInfo

class UpdaterTest(unittest.TestCase):
    def setUp(self):
        setDebug()
        self.config = Config('/etc/myDevices/AppSettings.ini')
        self.updater = Updater(self.config)
    def tearDown(self):
        self.updater = None
    def testCheckUpdate(self):
        self.updater.CheckUpdate()
        print('After CheckUpdate')
    # def testStart(self):
    #     self.updater.start()
    #     print('After Updater')

def main():
    unittest.main()

if __name__ == '__main__':
    main()