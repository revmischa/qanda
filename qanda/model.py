import uuid
import time
from qanda import g_twil, g_notify
from typing import Any, Optional, Dict
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
                    body: str = None,
                    sid: str = None,
                    question_id: str = None,
                    answer_id: str = None,
                    **kwargs):
        msg = {
            'from': from_,
            'to': to_,
            'sid': sid,
            **self.id_and_created(),
            **kwargs,
        }
        if body:
            msg['body'] = body
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

    def new_question_from_slack(self, body: str, channel_id: str,
                                user_id: str, team_id: str, team_domain: str=None,
                                user_name: str=None, channel_name: str=None,
                                **kwargs) -> int:
        """Record and publish a new question asked from a slack PM or slashcommand.

        :returns: number of people notified.
        """
        slack_params = dict(
            slack_channel_id=channel_id,
            slack_team_id=team_id,
            slack_user_id=user_id,
            source='slack',
        )
        if channel_name:
            slack_params['slack_channel_name'] = channel_name
        if team_domain:
            slack_params['slack_team_domain'] = team_domain
        if user_name:
            slack_params['slack_user_name'] = user_name
        # record question
        q = dict(
            body=body,
            **slack_params,
            **self.id_and_created(),
        )
        self.question.put_item(Item=q)

        # record the message
        self.new_message(
            from_=user_id,
            to_='slack',
            body=body,
            question_id=q['id'],
            is_question=True,
            in_channel=True,  # assuming this is a public question
            **slack_params,
        )

        # notify
        notified = g_notify.notify_of_question(q)
        log.info("new slack question sent to {notified} people")
        return notified

    def _find_question_message_to(self, to, filter_expression=None) -> Optional[Dict]:
        """Look up most recent message that was sent to `to`."""
        if not filter_expression:
            filter_expression = Attr('question_id').exists() & Attr('is_question_notification').exists()
        res = self.message.query(
            IndexName='to-created-index',  # FIXME: put in CF
            ScanIndexForward=False,  # give us most recent first
            KeyConditionExpression=Key('to').eq(to),  # find message sent to this answerer
            FilterExpression=filter_expression,  # should have been for a question
        )

        count = res['Count']
        if count == 0:
            return None

        items = res['Items']
        return items[0]  # should be newest

    def new_answer_from_slack_pm(self, body: str, user_id: str, team_id: str, channel_id: str) -> bool:
        answer_message = self.new_message(
            from_=user_id,
            to_='slack_pm',
            body=body,
            slack_channel_id=channel_id,
            slack_team_id=team_id,
            source='slack',
            is_answer=True,
        )
        # look for a question that was sent to the sender
        filter_expression = Attr('question_id').exists() & \
            Attr('is_question_notification').exists() & \
            Attr('slack_team_id').eq(team_id)
        question_msg = self._find_question_message_to(to=channel_id, filter_expression=filter_expression)
        if not question_msg:
            log.warning(f"got slack response to question but no question found for {channel_id}")
            return False

        self.new_answer_for_message(question_msg, answer_message)
        return True

    def new_answer_from_sms(self, body: str, sid: str, from_: str, to_: str):
        answer_msg = self.new_message(
            body=body,
            sid=sid,
            from_=from_,
            to_=to_,
            is_answer=True,
            source='sms',
        )

        # look for a question that was sent to the sender
        question_msg = self._find_question_message_to(to=from_)

        if not question_msg:
            # we got a SMS but no question has ever been sent to this number...
            # must not be an answer?
            log.warning(f"got SMS but no questions have been asked. from: {from_}. body: {body}")
            return  # disabled for testing
            g_twil.send_sms(
                to=from_,
                body=f"Hey there! Sorry but we don't understand what you're sending us.",
            )
            return False

        self.new_answer_for_message(question_msg, answer_msg)
        return True

    def new_answer_for_message(self, q_msg, a_msg):
        # look up question that was asked
        question_id = q_msg['question_id']
        question = self.question.get_item(Key={'id': question_id})['Item']

        # record the answer
        answer = self.new_answer(question, a_msg)

        # notify asker of the answer
        g_notify.notify_of_answer(answer)
