import unittest
import warnings
import myDevices.cloud.cayennemqtt as cayennemqtt
import paho.mqtt.client as mqtt
from time import sleep
from json import dumps, loads

TEST_USERNAME = "user"
TEST_PASSWORD = "password"
TEST_CLIENT_ID = "id"
TEST_HOST = "localhost"
TEST_PORT = 1883

class CayenneMQTTTest(unittest.TestCase):
    def setUp(self):
        # print('setUp')
        self.mqttClient = cayennemqtt.CayenneMQTTClient()
        self.mqttClient.on_message = self.OnMessage
        self.mqttClient.begin(TEST_USERNAME, TEST_PASSWORD, TEST_CLIENT_ID, TEST_HOST, TEST_PORT)
        self.mqttClient.loop_start()
        self.testClient = mqtt.Client("testID")
        self.testClient.on_message = self.OnTestMessage
        # self.testClient.on_log = self.OnTestLog
        self.testClient.username_pw_set("testClient", "testClientPass")
        self.testClient.connect(TEST_HOST, TEST_PORT, 60)
        (result, messageID) = self.testClient.subscribe(self.mqttClient.get_topic_string(cayennemqtt.DATA_TOPIC))      
        self.assertEqual(result, mqtt.MQTT_ERR_SUCCESS)
        self.testClient.loop_start()

    def tearDown(self):
        # print('tearDown')
        self.mqttClient.loop_stop()
        self.mqttClient.disconnect()
        self.testClient.loop_stop()
        self.testClient.disconnect()

    def OnMessage(self, message):
        self.receivedMessage = message
        # print('OnMessage: {}'.format(self.receivedMessage))

    def OnTestMessage(self, client, userdata, message):
        self.receivedTopic = message.topic
        self.receivedMessage = message.payload.decode()
        # print('OnTestMessage: {} {}'.format(self.receivedTopic, self.receivedMessage))

    def OnTestLog(self, client, userdata, level, buf):
        print('OnTestLog: {}'.format(buf))
                
    def testPublish(self):
       #Ignore warning caused by paho mqtt not closing some sockets in the destructor
        with warnings.catch_warnings():
            warnings.simplefilter('ignore', ResourceWarning)
            sentTopic = self.mqttClient.get_topic_string(cayennemqtt.DATA_TOPIC)
            sentMessage = '{"publish_test":"data"}'
            self.mqttClient.publish_packet(cayennemqtt.DATA_TOPIC, sentMessage)
            sleep(0.5)
            self.assertEqual(sentTopic, self.receivedTopic)
            self.assertEqual(sentMessage, self.receivedMessage)

    def testCommand(self):
        sentTopic = self.mqttClient.get_topic_string(cayennemqtt.COMMAND_TOPIC + '/' + cayennemqtt.SYS_POWER)
        sentMessage = 'reset' #'{"command_test":"data"}'
        self.testClient.publish(sentTopic, sentMessage)
        sleep(0.5)
        # sentMessage = loads(sentMessage)
        self.assertEqual(cayennemqtt.SYS_POWER, self.receivedMessage['channel'])
        self.assertEqual(sentMessage, self.receivedMessage['payload'])


if __name__ == "__main__":
    unittest.main()
