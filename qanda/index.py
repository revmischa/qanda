import os, sys
lib_path = os.path.abspath(os.path.join(__file__, '..', '..', 'vendor'))
sys.path.append(lib_path)

import awsgi
from flask import request, Flask, jsonify
import copy
from pprint import pprint
from flask_apispec import use_kwargs, marshal_with
from marshmallow import fields, Schema
import logging
from typing import Dict
from qanda import model
import boto3
from qanda.slack import SlackSlashcommandSchema, SlackSlashcommandResponseSchema

log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)
boto3.set_stream_logger(level=logging.WARNING)

boto_session = boto3.session.Session()
print(f"REGION: {boto_session.region_name}")

app = Flask(__name__)


def lambda_handler(event, context):
    # pprint(event)
    return awsgi.response(app, event, context)


@app.route('/test', methods=['GET', 'POST'])
def test():
    data = {
        'form': request.form.copy(),
        'args': request.args.copy(),
        'json': request.json
    }
    return jsonify(data)


@app.route('/slack/slash_ask', methods=['POST'])
@use_kwargs(SlackSlashcommandSchema(strict=True))
@marshal_with(SlackSlashcommandResponseSchema)
def slack_slash_ask(**kwargs):
    # save question
    model.new_question_from_slack(**kwargs)
    return {'text': "Your question has been asked. Please wait for random humans to answer it."}


class AskQuestionSchema(Schema):
    question = fields.Str(required=True)
    name = fields.Str(required=False)
    channel = fields.Str(required=False)


@app.route('/twilio/sms/mo', methods=['POST'])
def twilio_sms_mo():
    """Handle incoming SMS."""
    vals: dict = request.form
    sid: str = vals['MessageSid']
    model.new_message(
        body=vals['Body'],
        sid=sid,
        from_=vals['From'],
        to_=vals['To'],
    )
    return "ok"


if __name__ == '__main__':
    app.run(debug=True)
