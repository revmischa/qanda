import awsgi
from flask import request, Flask, jsonify
import boto3
import copy
import time

app = Flask(__name__)

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
    import pprint
    pprint.pprint(data)
    return jsonify(data)

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
