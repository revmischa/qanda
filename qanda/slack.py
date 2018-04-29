from marshmallow import fields, Schema
from flask import request
import qanda.table
from qanda import app
import logging
from typing import Optional, Dict
from slackclient import SlackClient

log = logging.getLogger(__name__)

LOGO = ":face_with_monocle:"
USAGE = """
:point_right: Get notified of new questions: *subscribe*
:point_right: Stop getting notified of new questions: *unsubscribe*
:point_right: Ask a private question: *ask ....*
"""


class SlackSlashcommandSchema(Schema):
    """Request and response marshalling for Slack slashcommands.

    https://api.slack.com/custom-integrations/slash-commands#how_do_commands_work
    """
    body = fields.Str(load_from='text')
    token = fields.Str()
    team_id = fields.Str()
    team_domain = fields.Str()
    channel_id = fields.Str()
    channel_name = fields.Str()
    user_id = fields.Str()
    user_name = fields.Str()
    command = fields.Str()
    response_url = fields.Str()


class SlackSlashcommandResponseSchema(Schema):
    """Marshal a response for returning a slashcommand status.

    https://api.slack.com/custom-integrations/slash-commands#responding_to_a_command
    """
    text = fields.Str(required=False)
    response_type = fields.Str(required=True)


class SlackApp:
    @classmethod
    def get_client_for_team_id(cls, team_id) -> Optional[SlackClient]:
        slack = SlackApp(team_id=team_id)
        client = slack.get_client()
        return client

    def __init__(self, team_id):
        self.team_id = team_id

    def get_client(self) -> SlackClient:
        # look up auth token for this team so we can reply
        auth_token = qanda.table.auth_token.get_item(Key={'id': self.team_id})
        if 'Item' not in auth_token:
            log.warning(f"can't notify slack team {self.team_id} of response - missing auth token")
            return None
        auth_token = auth_token['Item']
        # now we have an auth token and everything we need to notify the user or channel
        client = self.get_client_for_auth_token(auth_token)
        return client

    def get_client_for_auth_token(self, auth_token):
        # make a client with the bot token
        # in the new slack apps - there is no bot token. it's just access_token and the app is a bot.
        if 'access_token' not in auth_token:
            raise Exception(f"missing access_token in {auth_token}")
        bot_token = auth_token['access_token']
        sc = SlackClient(bot_token)
        return sc

    def get_app_userid(self) -> Optional[str]:
        """Find OUR (as in, the bot) userid in this team."""
        auth_token = self.get_auth_token()
        if not auth_token:
            return None
        return auth_token['app_user_id']

    def get_auth_token(self) -> Optional[Dict]:
        return qanda.table.auth_token.get_item(Key={
            'id': self.team_id
        })['Item']

    def handle_event_callback(self, evt_callback) -> bool:
        """Handle an event webhook."""
        evt = evt_callback['event']
        type = evt['type']

        # handle event
        if type == 'message':
            # PM
            self.handle_im_subscribe(evt)
            return True

        # unknown event
        import pprint
        pprint.pprint(evt)
        log.error(f"unknown event {type}")
        return False

    def handle_im_subscribe(self, evt):
        from qanda import g_model

        client = self.get_client()
        body = evt['text']
        channel_id = evt['channel']
        user_id = evt['user']

        # record message
        def save_message():
            g_model.new_message(
                from_=user_id,
                to_='event_hook',
                body=body,
                slack_channel_id=channel_id,
                slack_team_id=self.team_id,
                source='slack',
            )

        def reply(**kwargs):
            client.api_call(
                "chat.postMessage",
                channel=channel_id,
                **kwargs,
            )

        is_pm = channel_id.startswith('D')  # D for direct message, C for channel
        if not is_pm:
            # in-channel msg; eh just bail
            if app.debug:
                save_message()
            return

        # now look up what OUR user id is
        app_userid = self.get_app_userid()
        if user_id == app_userid:
            # we're getting notified of OUR message that we sent. thanks slack. :/
            return

        bodylc = body.lower()

        if bodylc.startswith('subscribe'):
            # subscribe user
            sub_id = f"{self.team_id}|{channel_id}"
            qanda.table.subscriber.put_item(
                Item=dict(
                    id=sub_id,
                    slack_team_id=self.team_id,
                    slack_channel_id=channel_id,
                    slack_user_id=user_id,
                    body=body,
                ))
            reply(text=f"Ok! You'll get notifed of new questions. Message me \"unsubscrbe\" at any time to shut me up {LOGO}")
            log.info("new slack subscriber!")

        elif bodylc.startswith('unsubscribe') or bodylc.startswith('stop'):
            # unsubscribe
            sub_id = f"{self.team_id}|{channel_id}"
            qanda.table.subscriber.delete_item(Key={'id': sub_id})
            reply(text="Ok! I'll shut up now!")
            log.info("slack user unsubscribed!")
            save_message()

        elif bodylc.startswith('ask '):
            # ask a question
            _, q_text = body.split(None, maxsplit=1)
            notified = g_model.new_question_from_slack(
                body=q_text,
                channel_id=channel_id,
                user_id=user_id,
                team_id=self.team_id,
            )
            reply(text=f"{LOGO} Splendid! Your message has been sent out to {notified} people.\nI'll message you with the answers.")

        elif bodylc.startswith('reply '):
            # submit answer
            _, q_text = body.split(None, maxsplit=1)
            ok = g_model.new_answer_from_slack_pm(
                body=q_text,
                channel_id=channel_id,
                user_id=user_id,
                team_id=self.team_id,
            )
            if ok:
                reply(text=f"{LOGO} Splendid! Your message has been sent out to {notified} people.\nI'll message you with the answers.")
            else:
                reply(text="So sorry... I don't have any record of asking you a question.")

        else:
            # unknown
            save_message()
            log.info(f"got unfamiliar IM command: {body}")
            reply(text=f"So sorry.. not sure what you're asking {LOGO}\nCommands are: {USAGE}")
