import unittest
from index import app as handler_app
import json

class HandlerTestCase(unittest.TestCase):
    def setUp(self):
        handler_app.testing = True
        self.client = handler_app.test_client()

    def test_sms_mo(self):
        sms = {
            'AccountSid': 'AC08bf090ef6d5c3aa6b0b9046a8054a34',
            'AddOns': '{"status":"successful","message":null,"code":null,"results":{}}',
            'ApiVersion': '2010-04-01',
            'Body': 'Lo siento, número equivocado',
            'From': '+380978743661',
            'FromCity': '',
            'FromCountry': 'UA',
            'FromState': '',
            'FromZip': '',
            'MessageSid': 'SMebbd91df82203f407e8c5897c5f9ee3a',
            'MessagingServiceSid': 'MG0eaf4d6c304c351152d0e272395dd276',
            'NumMedia': '0',
            'NumSegments': '1',
            'SmsMessageSid': 'SMebbd91df82203f407e8c5897c5f9ee3a',
            'SmsSid': 'SMebbd91df82203f407e8c5897c5f9ee3a',
            'SmsStatus': 'received',
            'To': '+13126672691',
            'ToCity': '',
            'ToCountry': 'US',
            'ToState': 'IL',
            'ToZip': ''
        }
        res = self.client.post('/twilio/sms/mo', data=sms)
        self.assertEqual(res.data, b'ok')
