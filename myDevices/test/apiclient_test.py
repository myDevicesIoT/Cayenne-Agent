import unittest
from myDevices.utils.logger import exception, setDebug, info, debug, error, logToFile, setInfo
from myDevices.cloud.apiclient import CayenneApiClient
from json import loads


class ApiClientTest(unittest.TestCase):
    def testMessageBody(self):
        cayenneApiClient = CayenneApiClient('https://api.mydevices.com')
        message = loads(cayenneApiClient.getMessageBody('invite_code'))
        self.assertIn('id', message)
        self.assertIn('type', message)
        self.assertIn('hardware_id', message)
        self.assertIn('properties', message)
        self.assertIn('sysinfo', message['properties'])
        self.assertIn('pinmap', message['properties'])


if __name__ == '__main__':
    setInfo()
    unittest.main()
