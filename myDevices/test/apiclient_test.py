import unittest
from myDevices.utils.logger import exception, setDebug, info, debug, error, logToFile, setInfo
from myDevices.cloud.apiclient import CayenneApiClient
from json import loads


class ApiClientTest(unittest.TestCase):
    def testMessageBody(self):
        cayenneApiClient = CayenneApiClient('https://api.mydevices.com')
        message = loads(cayenneApiClient.getMessageBody('invite_code'))
        # info(message)
        self.assertIn('id', message)
        self.assertIn('type', message)
        self.assertIn('hardware_id', message)
        self.assertIn('properties', message)
        self.assertIn('sysinfo', message['properties'])
        channels = [item['channel'] for item in message['properties']['sysinfo']]
        self.assertCountEqual(['sys:hw:make', 'sys:hw:model', 'agent:version', 'sys:ram;capacity', 'sys:storage:/;capacity'], channels)
        self.assertIn('pinmap', message['properties'])


if __name__ == '__main__':
    setInfo()
    unittest.main()
