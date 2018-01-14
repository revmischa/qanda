import uuid
from qanda.slack import SlackSlashcommandSchema
import boto3
import time
from qanda import app

class Model:
    def __init__(self):
        dynamodb: boto3.resources.factory.dynamodb.ServiceResource = boto3.resource('dynamodb')
        self.message: boto3.resources.factory.dynamodb.Table = dynamodb.Table('message')
        self.question: boto3.resources.factory.dynamodb.Table = dynamodb.Table('question')
        self.answer: boto3.resources.factory.dynamodb.Table = dynamodb.Table('answer')
        self.subscriber: boto3.resources.factory.dynamodb.Table = dynamodb.Table('subscriber')

    def make_id(self):
        return str(uuid.uuid4())

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
        res = self.message.put_item(
            Item=msg
        )

    def new_question_from_slack(self, text: str, user_name: str, channel_id: str, channel_name, **kwargs):
        q: dict = {
            'text': text,
            'user_name': user_name,
            'channel_id': channel_id,
            'channel_name': channel_name,
            'created_ts': int(time.time()),
            'id': self.make_id(),
        }
        self.question.put_item(
            Item=q
        )

        # send out messages
        subscribers = self.subscriber.scan()  # NB only returns 1MB of results
        for sub in subscribers['Items']:
            print(f"sub: {sub}")
            phone: str = sub['phone']
            if not phone:
                continue
