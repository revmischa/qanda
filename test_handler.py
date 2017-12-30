import unittest
import index

class HandlerTestCase(unittest.TestCase):
    def test_app(self):
        self.assertTrue(index.handler(None, None))
