import twilio.rest
from qanda import app


class Twil(twilio.rest.Client):
    def __init__(self, sid=None, secret=None):
        if not sid and not secret:
            sid = app.config.get('TWILIO_API_SID')
            secret = app.config.get('TWILIO_API_SECRET')
        super().__init__(sid, secret)

    def send_sms(self, to: str, body: str, **kwargs):
        from qanda import g_model
        # send
        res = self.messages.create(
            to=to,
            body=body,
            messaging_service_sid=app.config['TWILIO_MSG_SVC_ID'])

        # record message
        g_model.new_message(
            to_=to,
            from_=res.from_,
            body=body,
            **kwargs,
            id=g_model.make_id(),
            sid=res.sid,
        )

        return res
