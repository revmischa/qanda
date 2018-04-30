from marshmallow import fields, Schema
from flask import request
import qanda.table
from qanda import app, g_invoker
import logging
from typing import Optional, Dict
from slackclient import SlackClient

log = logging.getLogger(__name__)

LOGO = ":face_with_monocle:"
USAGE = """
Commands:
  :mailbox: Get notified of new questions: *subscribe*
  :zipper_mouth_face: Stop getting notified of new questions: *unsubscribe*


  :ear: Ask an anonymous question: "*ask ....*"
  :open_mouth: Answer a question anonymously: "*reply ....*"
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
        # need to use bot access token?
        if app.config['WORKSPACE_PERMISSIONS']:
            bot_token = auth_token['access_token']
        else:
            if 'bot' not in auth_token:
                raise Exception(f"missing bot access_token in {auth_token}")
            bot_token = auth_token['bot']['bot_access_token']
        sc = SlackClient(bot_token)
        return sc

    def get_app_userid(self) -> Optional[str]:
        """Find OUR (as in, the bot) userid in this team."""
        auth_token = self.get_auth_token()
        if not auth_token:
            return None
        if app.config['WORKSPACE_PERMISSIONS']:
            # new
            return auth_token['app_user_id']
        else:
            # legacy
            if 'bot' not in auth_token:
                raise Exception(f"missing bot access_token in {auth_token}")
            return auth_token['bot']['bot_user_id']

    def get_auth_token(self) -> Optional[Dict]:
        return qanda.table.auth_token.get_item(Key={
            'id': self.team_id
        })['Item']

    def handle_event_callback(self, evt_callback) -> None:
        """Handle an event webhook."""
        evt = evt_callback['event']
        type = evt['type']

        # handle event
        if type == 'message':
            self.handle_message_event(evt)
        else:
            # unknown event
            import pprint
            pprint.pprint(evt)
            log.error(f"unknown event {type}")

    def handle_message_event(self, evt):
        from qanda import g_model

        client = self.get_client()
        # some message format we don't know how to handle
        if 'text' not in evt:
            return False

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

        # look up subscription
        subscription = self.get_subscription(channel_id)
        sub_id = f"{self.team_id}|{channel_id}"

        # look up team name
        team_info = self.get_team_info()
        import pprint
        pprint.pprint(team_info)
        team_name = team_info['name'] if 'name' in team_info else 'your team'

        cross_slack_status_msg = ''
        if subscription:
            if subscription['cross_slack']:
                cross_slack_status_msg += f"You're currently set to get questions from anywhere.\nReply *local* to only get questions from {team_name}"
            else:
                cross_slack_status_msg += f"You're currently set to only get questions from {team_name}.\nReply *global* to receive questions from random people all over the world.\nWarning: may contain strange, bizarre, or offensive content."

        if bodylc.startswith('subscribe'):
            if subscription:
                msg = "You're already subscribed to get new questions.\n"
                msg += cross_slack_status_msg
                reply(text=msg)
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
            reply(text=f"Ok! You'll get notifed of new questions. Message me \"unsubscribe\" at any time to shut me up {LOGO}")
            log.info("new slack subscriber!")

        elif bodylc.startswith('global'):
            if not subscription:
                return reply(text="You're not subscribed to receive messages right now.")

            # enable global subscription
            subscription['cross_slack'] = True
            qanda.table.subscriber.put_item(Item=subscription)
            reply(text=f"Awesome! Now you'll get all questions, regardless of their origin.\nBe prepared to see some offensive and terrible things.\nReply *local* to return to the hugbox of {team_name} at any time.")

        elif bodylc.startswith('local'):
            if not subscription:
                return reply(text="You're not subscribed to receive messages right now.")

            # disable global subscription
            subscription['cross_slack'] = False
            qanda.table.subscriber.put_item(Item=subscription)
            reply(text=f"Alrightie! You will now only get questions from {team_name}\nReply *global* to get messages from anywhere.")

        elif bodylc.startswith('unsubscribe') or bodylc.startswith('stop'):
            # unsubscribe
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
            reply(text=f"{LOGO} Splendid! Your anonymous question has been sent out to {notified} people.\nI'll message you with the answers.")

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
                reply(text=f"{LOGO} Thanks! Your answer's been anonymously sent to the asker.")
            else:
                reply(text="So sorry... I don't have any record of asking you a question.")

        else:
            # unknown
            save_message()
            log.info(f"got unfamiliar IM command: {body}")
            reply(text=f"So sorry.. not sure what you're asking {LOGO}\n{USAGE}")

    def get_subscription(self, channel_id):
        sub_id = f"{self.team_id}|{channel_id}"
        res = qanda.table.subscriber.get_item(Key={'id': sub_id})
        return res['Item'] if 'Item' in res else None

    def get_team_info(self, client=None):
        if not client:
            client = self.get_client()
        return client.api_call('team.info')
