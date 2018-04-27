from qanda.slack import SlackSlashcommandSchema, SlackSlashcommandResponseSchema
from qanda import g_model, app
from flask_apispec import use_kwargs, marshal_with
from flask import request, redirect, url_for
import requests


@app.route('/slack/slash_ask', methods=['POST'])
@use_kwargs(SlackSlashcommandSchema(strict=True))
@marshal_with(SlackSlashcommandResponseSchema)
def slack_slash_ask(**kwargs):
    # save question
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

    Exchange code for auth token.
    """
    code = request.args.code
    print(f"code; {code}")
    # get auth token
    print(f"OAUTH_CLIENT_ID: {app.config.get('SLACK_OAUTH_CLIENT_ID')}")
    res = requests.get(
        'https://slack.com/api/oauth.access',
        params={
            'code': code,
            'client_id': app.config['SLACK_OAUTH_CLIENT_ID'],
            'client_secret': app.config['SLACK_OAUTH_CLIENT_SECRET'],
            'redirect_uri': app.config['SLACK_OAUTH_REDIRECT_URI'],
        }).json()

    print(res)
    return redirect(url_for('https://github.com/revmischa/qanda'))
