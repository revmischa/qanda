import uuid
# from qanda.slack import SlackSlashcommandSchema
import time
from qanda import g_twil, g_notify
from typing import Any
from boto3.dynamodb.conditions import Key, Attr
import logging
import qanda.table

log = logging.getLogger(__name__)


class Model:
    def __init__(self):
        # conveniences
        self.message = qanda.table.message
        self.question = qanda.table.question
        self.answer = qanda.table.answer
        self.subscriber = qanda.table.subscriber
        self.auth_token = qanda.table.auth_token

    def make_id(self) -> str:
        return str(uuid.uuid4())

    def id_and_created(self, id_=None):
        if id_ is None:
            id_ = self.make_id()
        return dict(
            id=id_,
            created=int(time.time()),
        )

    def save_slack_tokens(self, token_res):
        """Store OAuth response tokens from finished Slack OAuth flow."""
        # delete existing item if one exists
        team_id = token_res['team_id']
        log.debug(token_res)
        self.auth_token.put_item(Item=dict(
            **token_res,
            **self.id_and_created(id_=team_id),
        ))

    def new_message(self,
                    from_: str,
                    to_: Any,
                    body: str,
                    sid: str = None,
                    question_id: str = None,
                    answer_id: str = None,
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
            'question_id': question['id'],
        }
        self.answer.put_item(Item=answer)
        return answer

    def new_question_from_slack(self, text: str, channel_id: str, channel_name,
                                user_id: str, team_id: str, team_domain: str,
                                user_name: str=None,
                                **kwargs):

        slack_params = dict(
            slack_channel_name=channel_name,
            slack_channel_id=channel_id,
            slack_team_id=team_id,
            slack_team_domain=team_domain,
            slack_user_name=user_name,  # deprecated
            slack_user_id=user_id,
            source='slack',
        )
        # record question
        q = dict(
            body=text,
            **slack_params,
            **self.id_and_created(),
        )
        self.question.put_item(Item=q)

        # record the message
        self.new_message(
            from_=user_id,
            to_=channel_id,
            body=text,
            question_id=q['id'],
            **slack_params,
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
            IndexName='to-created-index',  # FIXME: put in CF
            ScanIndexForward=False,  # give us most recent first
            KeyConditionExpression=Key('to').eq(from_),  # find message sent to this answerer
            FilterExpression=Attr('question_id').exists(),  # should have been for a question
        )

        count = sent_messages_res['Count']
        sent_messages = sent_messages_res['Items']

        if count == 0:
            # we got a SMS but no question has ever been sent to this number...
            # must not be an answer?
            log.warning(f"got SMS but no questions have been asked. from: {from_}. body: {body}")
            return  # disabled for testing
            g_twil.send_sms(
                to=from_,
                body=f"Hey there! Sorry but we don't understand what you're sending us.",
            )
            return

        # get first result
        question_msg = sent_messages[0]

        # look up question that was asked
        question_id = question_msg['question_id']
        assert question_id
        question = self.question.get_item(Key={'id': question_id})['Item']
        assert question

        # record the answer
        answer = self.new_answer(question, answer_msg)

        # notify asker of the answer
        g_notify.notify_of_answer(answer)
