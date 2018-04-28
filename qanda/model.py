import uuid
# from qanda.slack import SlackSlashcommandSchema
import boto3
import time
from qanda import g_twil
from typing import Any
from boto3.dynamodb.conditions import Key, Attr


class Model:
    def __init__(self):
        dynamodb: boto3.resources.factory.dynamodb.ServiceResource = boto3.resource('dynamodb')
        self.message: boto3.resources.factory.dynamodb.Table = dynamodb.Table('qanda.message')
        self.question: boto3.resources.factory.dynamodb.Table = dynamodb.Table('qanda.question')
        self.answer: boto3.resources.factory.dynamodb.Table = dynamodb.Table('qanda.answer')
        self.subscriber: boto3.resources.factory.dynamodb.Table = dynamodb.Table('qanda.subscriber')

    def make_id(self):
        return str(uuid.uuid4())

    def id_and_created(self):
        return dict(
            id=self.make_id(),
            created=int(time.time()),
        )

    def new_message(self,
                    from_: str,
                    to_: Any,
                    body: str,
                    sid: str = None,
                    question_id: int = None,
                    answer_id: int = None,
                    **kwargs):
        msg = {
            'from': from_,
            'to': to_,
            'sid': sid,
            'body': body,
            **self.id_and_created(),
            **kwargs,
        }
        if question_id:
            msg['question_id'] = question_id
        if answer_id:
            msg['answer_id'] = answer_id
        self.message.put_item(Item=msg)
        return msg

    def new_answer(self, question, answer_msg):
        """Record an answer to a question."""
        answer = {
            **self.id_and_created(),
            'body': answer_msg['body'],
            'message_id': answer_msg['id'],
        }
        self.answer.put_item(Item=answer)
        return answer

    def new_question_from_slack(self, text: str, user_name: str,
                                channel_id: str, channel_name, **kwargs):
        # record question
        q = {
            'body': text,
            'user_name': user_name,
            'channel_id': channel_id,
            'channel_name': channel_name,
            **self.id_and_created(),
        }
        self.question.put_item(Item=q)

        # record the message
        self.new_message(
            from_=user_name,
            to_=channel_id,
            source='slack',
            slack_channel_name=channel_name,
            slack_channel_id=channel_id,
            body=text,
            question_id=q['id'],
        )

        # send out messages to subscribers
        subscribers = self.subscriber.scan()  # NB only returns 1MB of results
        for sub in subscribers['Items']:
            phone: str = sub['phone']
            if not phone:
                continue

            # text question
            g_twil.send_sms(
                question_id=q['id'],
                to=phone,
                body=f"{user_name} asks:\n\"{text}\"\n\nReply w/ answer",
            )

    def new_answer_from_sms(self, body: str, sid: str, from_: str, to_: str):
        answer_msg = self.new_message(
            body=body,
            sid=sid,
            from_=from_,
            to_=to_,
        )

        # look for a question that was sent to the sender
        sent_messages_res = self.message.query(
            IndexName='to-created_ts-index',  # FIXME: put in CF
            ScanIndexForward=False,  # give us most recent first
            KeyConditionExpression=Key('to').eq(from_),  # find message sent to this answerer
            FilterExpression=Attr('question_id').exists(),  # should have been for a question
            Limit=1,  # just one is fine
        )

        count = sent_messages_res['Count']
        sent_messages = sent_messages_res['Items']

        if count == 0:
            # we got a SMS but no question has ever been sent to this number...
            # must not be an answer?
            return  # disabled for testing
            g_twil.send_sms(
                to=from_,
                body=f"Hey there! Sorry but we don't understand what you're sending us.",
            )
            return

        # should only have one result
        assert count == 1
        question_msg = sent_messages[0]

        # look up question that was asked
        question_id = question_msg['question_id']
        assert question_id
        question = self.question.get_item(Key={'id': question_id})
        assert question

        # record the answer
        answer = self.new_answer(question, answer_msg)
        import pprint
        pprint.pprint(answer)

        # notify asker of the answer
        ...
