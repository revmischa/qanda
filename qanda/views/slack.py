from qanda.slack import SlackSlashcommandSchema, SlackSlashcommandResponseSchema, SlackApp
from qanda import g_model, app, g_notify, g_invoker
import qanda.table
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
    g_invoker.invoke_async(func='SLACK_SLASH_FUNCTION', payload=kwargs)
    g_model.new_question_from_slack(**kwargs)
    return {
        "response_type": "in_channel",
        'text': "Your question has been asked. Please wait for random humans to answer it."
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
    team_id = evt_callback['team_id']

    # handle it
    slack = SlackApp(team_id)

    try:
        if slack.handle_event_callback(evt_callback):
            return "ok", 200
    except Exception as ex:
        log.exception(ex)

    # something bad happened
    # (will retry)
    return "not ok", 500


def get_oauth_redirect_url():
    return url_for('slack_oauth', _external=True)


@app.route('/slack/install', methods=['GET'])
def slack_install():
    """Begin OAuth flow for install."""

    # chat:write:user got changed to chat:write
    if app.config['WORKSPACE_PERMISSIONS']:
        chat_write = 'chat:write'  # new
    else:
        chat_write = 'chat:write:user'  # old

    url = 'https://slack.com/oauth/authorize?' + urlencode(
        dict(
            client_id=app.config['SLACK_OAUTH_CLIENT_ID'],
            scope=f'commands identity.team channels:history im:history {chat_write} im:write reactions:write',
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
        redirect_uri=app.config['SLACK_OAUTH_REDIRECT_URL'],
        code=code,
    )
    if 'error' in auth_response:
        log.error(f"got error in auth response: {auth_response['error']}")
        return auth_response['error']

    # save
    g_model.save_slack_tokens(auth_response)
    return redirect('https://github.com/revmischa/qanda#ask-a-question-answer-a-question')
