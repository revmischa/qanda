import twilio.rest
from qanda import app

class Twil(twilio.rest.Client):
    def __init__(self, sid=None, secret=None):
        if not sid and not secret:
            sid = app.config.get('TWILIO_API_SID')
            secret = app.config.get('TWILIO_API_SECRET')
        super().__init__(sid, secret)
