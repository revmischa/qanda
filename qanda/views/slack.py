from qanda.slack import SlackSlashcommandSchema, SlackSlashcommandResponseSchema
from qanda import g_model, app
from flask_apispec import use_kwargs, marshal_with
from flask import request, redirect, url_for
import requests
from slackclient import SlackClient
from urllib.parse import urlencode
import logging

log = logging.getLogger(__name__)


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
    evt = request.get_json()
    type = evt['type']
    if type == 'url_verification':
        return evt['challenge']

    import pprint
    pprint.pprint(evt)
    log.error(f"unknown event {type}")

def get_oauth_redirect_url():
    return url_for('slack_oauth', _external=True)

@app.route('/slack/install', methods=['GET'])
def slack_install():
    """Begin OAuth flow for install."""
    url = 'https://slack.com/oauth/authorize?' + urlencode(
        dict(
            client_id=app.config['SLACK_OAUTH_CLIENT_ID'],
            scope='commands identity.team channels:history chat:write im:write reactions:write',
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
