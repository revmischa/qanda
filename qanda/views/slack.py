from qanda.slack import SlackSlashcommandSchema, SlackSlashcommandResponseSchema
from qanda import g_model, app, g_notify
import qanda.table
from flask_apispec import use_kwargs, marshal_with
from flask import request, redirect, url_for
import requests
from slackclient import SlackClient
from urllib.parse import urlencode
import logging

log = logging.getLogger(__name__)

USAGE = """
Get notified of new questions: subscribe
Stop getting notified of new questions: unsubscribe
Ask a private question: ask ....
"""

@app.route('/slack/slash_ask', methods=['POST'])
@use_kwargs(SlackSlashcommandSchema(strict=True))
@marshal_with(SlackSlashcommandResponseSchema)
def slack_slash_ask(**kwargs):
    """Slashcommand handler."""
    g_model.new_question_from_slack(**kwargs)
    return {
        'text':
        "Your question has been asked. Please wait for random humans to answer it."
    }

@app.route('/slack/event', methods=['POST'])
def slack_event():
    evt_callback = request.get_json()

    # check it's really slack and they have our secret
    token = evt_callback['token']
    if token != app.config['SLACK_VERIFICATION_TOKEN']:
        log.error(f"got invalid SLACK_VERIFICATION_TOKEN: {token}")
        return "invalid token", 400

    type = evt_callback['type']

    # subscribe challenge
    if type == 'url_verification':
        return evt_callback['challenge']

    # useful fields
    evt = evt_callback['event']
    team_id = evt_callback['team_id']
    type = evt['type']

    # handle event
    if type == 'message':
        # PM
        handle_im_subscribe(team_id, evt)
        return "ok"

    # unknown event
    import pprint
    pprint.pprint(evt)
    log.error(f"unknown event {type}")
    return "not ok", 500

def get_app_userid(team_id):
    """Find OUR (as in, the bot) userid in this team."""
    auth_token = get_auth_token(team_id)
    if not auth_token:
        return None
    return auth_token['app_user_id']

def get_auth_token(team_id):
    return qanda.table.auth_token.get_item(Key={'id': team_id})['Item']

# move somewhere else
def handle_im_subscribe(team_id, evt):
    client = g_notify.get_slack_bot_client_for_team(team_id)
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
            slack_team_id=team_id,
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
        save_message()
        return

    # now look up what OUR user id is
    app_userid = get_app_userid(team_id)
    if user_id == app_userid:
        # we're getting notified of OUR message that we sent. thanks slack. :/
        return

    bodylc = body.lower()

    if bodylc.startswith('subscribe'):
        # subscribe user
        sub_id = f"{team_id}|{channel_id}"
        qanda.table.subscriber.put_item(Item=dict(
            id=sub_id,
            team_id=team_id,
            channel_id=channel_id,
            user_id=user_id,
            body=body,
        ))
        reply(text=f"Ok! You'll get notifed of new questions. Message me \"unsubscrbe\" at any time to shut me up :face_with_monocle:")

    elif bodylc.startswith('unsubscribe') or bodylc.startswith('stop'):
        # unsubscribe
        sub_id = f"{team_id}|{channel_id}"
        qanda.table.subscriber.delete_item(Key={'id': sub_id})
        reply(text="Ok! I'll shut up now!")
        save_message()

    else:
        # unknown
        save_message()
        log.info(f"got unfamiliar IM command: {body}")
        reply(text=f"So sorry.. not sure what you're asking :face_with_monocle:\nCommands are: {USAGE}")

def get_oauth_redirect_url():
    return url_for('slack_oauth', _external=True)

@app.route('/slack/install', methods=['GET'])
def slack_install():
    """Begin OAuth flow for install."""
    url = 'https://slack.com/oauth/authorize?' + urlencode(
        dict(
            client_id=app.config['SLACK_OAUTH_CLIENT_ID'],
            scope='commands identity.team channels:history im:history chat:write im:write reactions:write',
            redirect_uri=app.config['SLACK_OAUTH_REDIRECT_URL'],
            _external=True,
        ))
    return redirect(url)


@app.route('/slack/oauth', methods=['GET'])
def slack_oauth():
    """Handle Slack oauth.

    Exchange code for auth token. Save in auth_token.
    """
    req = request.args
    if 'error' in req:
        return "im so sorry :("

    # exchange code for access token
    code = req['code']
    sc = SlackClient("")
    auth_response = sc.api_call(
        "oauth.access",
        client_id=app.config['SLACK_OAUTH_CLIENT_ID'],
        client_secret=app.config['SLACK_OAUTH_CLIENT_SECRET'],
        redirect_uri=app.config['SLACK_OAUTH_REDIRECT_URL'].lowercase(),
        code=code,
    )
    if 'error' in auth_response:
        log.error(f"got error in auth response: {auth_response['error']}")
        return auth_response['error']

    # save
    g_model.save_slack_tokens(auth_response)
    return redirect('https://github.com/revmischa/qanda')
