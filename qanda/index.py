import os, sys
lib_path = os.path.abspath(os.path.join(__file__, '..'))
sys.path.append(lib_path)

import awsgi
from flask import request, Flask, jsonify
import boto3
import copy
import time
from pprint import pprint
from flask_apispec import use_kwargs, marshal_with
from marshmallow import fields, Schema, pre_load
from urllib.parse import parse_qs
import logging
log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)

app = Flask(__name__)


class SlackSlashcommandSchema(Schema):
    """Request and response marshalling for Slack slashcommands."""
    text = fields.Str(load_only=True)

    @pre_load
    def parse_form(self, in_data):
        """Parse URLencoded slash command params.

        https://api.slack.com/custom-integrations/slash-commands#how_do_commands_work
        """
        body: str = request.data  # urlencoded params
        in_data['text'] = parse_qs(body)


class SlackSlashcommandResponseSchema(Schema):
    """Marshal a response for returning a slashcommand status.

    https://api.slack.com/custom-integrations/slash-commands#responding_to_a_command
    """
    text = fields.Str(required=False)
    response_type = fields.Str(required=True)


def lambda_handler(event, context):
    return awsgi.response(app, event, context)


class Model:
    def __init__(self):
        dynamodb: boto3.resources.factory.dynamodb.ServiceResource = boto3.resource('dynamodb')
        self.message: boto3.resources.factory.dynamodb.Table = dynamodb.Table('message')
        self.question: boto3.resources.factory.dynamodb.Table = dynamodb.Table('question')
        self.answer: boto3.resources.factory.dynamodb.Table = dynamodb.Table('answer')

    def new_message(self, sid: str, from_: str, to_: str, body: str, question_id: int=None, answer_id: int=None):
        msg: dict = {
            'from': from_,
            'to': to_,
            'sid': sid,
            'body': body,
            'created_ts': int(time.time()),
        }
        if question_id:
            msg['question_id'] = question_id
        if answer_id:
            msg['answer_id'] = answer_id
        self.message.put_item(
            Item=msg
        )

model: Model = Model()

@app.route('/test', methods=['GET', 'POST'])
def test():
    data = {
        'form': request.form.copy(),
        'args': request.args.copy(),
        'json': request.json
    }
    return jsonify(data)

class AskQuestionSchema(Schema):
    question = fields.Str(required=True)
    name = fields.Str(required=False)
    channel = fields.Str(required=False)


@app.route('/slack/slash_ask', methods=['POST'])
@use_kwargs(SlackSlashcommandSchema)
@marshal_with(SlackSlashcommandResponseSchema)
def question_ask(question: str, name: str=None, channel: str=None):
    return {'text': question}


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
