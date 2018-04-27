import uuid
from qanda.slack import SlackSlashcommandSchema
import boto3
import time
from qanda import app, g_twil
import os
from typing import Any

message_table_name: str = os.getenv('MESSAGE_TABLE_NAME')
print(f"message_table_name: {message_table_name}")
print(f"foo: {os.getenv('FOO')}")


class Model:
    def __init__(self):
        dynamodb: boto3.resources.factory.dynamodb.ServiceResource = boto3.resource(
            'dynamodb')
        self.message: boto3.resources.factory.dynamodb.Table = dynamodb.Table(
            'qanda.message')
        self.question: boto3.resources.factory.dynamodb.Table = dynamodb.Table(
            'qanda.question')
        self.answer: boto3.resources.factory.dynamodb.Table = dynamodb.Table(
            'qanda.answer')
        self.subscriber: boto3.resources.factory.dynamodb.Table = dynamodb.Table(
            'qanda.subscriber')

    def make_id(self):
        return str(uuid.uuid4())

    def new_message(self,
                    from_: str,
                    to_: Any,
                    body: str,
                    sid: str = None,
                    question_id: int = None,
                    answer_id: int = None,
                    **kwargs):
        msg: dict = {
            'from': from_,
            'to': to_,
            'sid': sid,
            'body': body,
            'created_ts': int(time.time()),
            **kwargs,
        }
        if question_id:
            msg['question_id'] = question_id
        if answer_id:
            msg['answer_id'] = answer_id
        res = self.message.put_item(Item=msg)

    def new_question_from_slack(self, text: str, user_name: str,
                                channel_id: str, channel_name, **kwargs):
        # record question
        q: dict = {
            'text': text,
            'user_name': user_name,
            'channel_id': channel_id,
            'channel_name': channel_name,
            'created_ts': int(time.time()),
            'id': self.make_id(),
        }
        self.question.put_item(Item=q)

        # record the message
        self.new_message(
            from_=user_name,
            to_={
                'channel_id': channel_id,
                'channel_name': channel_name,
                'source': 'slack',
            },
            body=text,
            question_id=q['id'],
            sid=self.make_id(),
        )

        # send out messages
        subscribers = self.subscriber.scan()  # NB only returns 1MB of results
        for sub in subscribers['Items']:
            print(f"sub: {sub}")
            phone: str = sub['phone']
            if not phone:
                continue

            # text question
            sms = g_twil.send_sms(
                to=phone,
                body=f"{user_name} asks:\n\"{text}\"\n\nReply with answer",
            )

            # self.new_message()
