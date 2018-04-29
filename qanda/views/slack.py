from qanda.slack import SlackSlashcommandSchema, SlackSlashcommandResponseSchema
from qanda import g_model, app
from flask_apispec import use_kwargs, marshal_with
from flask import request, redirect, url_for
import requests
from slackclient import SlackClient


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


@app.route('/slack/install', methods=['GET'])
def slack_install():
    """Begin OAuth flow for install."""
    url = url_for(
        'https://slack.com/oauth/authorize',
        client_id=['SLACK_OAUTH_CLIENT_ID'],
        scope='commands',
        redirect_uri=app.config['OAUTH_REDIRECT_URL'],
    )
    return redirect(url)


@app.route('/slack/oauth', methods=['GET'])
def slack_oauth():
    """Handle Slack oauth.

    Exchange code for auth token. Save in auth_token.
    """
    code = request.args.code
    print(f"code; {code}")
    # get auth token
    print(f"OAUTH_CLIENT_ID: {app.config.get('SLACK_OAUTH_CLIENT_ID')}")
    sc = SlackClient("")
    auth_response = sc.api_call(
        "oauth.access",
        client_id=app.config['SLACK_OAUTH_CLIENT_ID'],
        client_secret=app.config['SLACK_OAUTH_CLIENT_SECRET'],
        redirect_uri=app.config['SLACK_OAUTH_REDIRECT_URI'],
        code=code,
    )
    g_model.save_slack_tokens(auth_response)
    return redirect(url_for('https://github.com/revmischa/qanda'))
