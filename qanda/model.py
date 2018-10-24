import uuid
import time
from qanda import g_twil, g_notify
from typing import Any, Optional, Dict, List
from boto3.dynamodb.conditions import Key, Attr
import logging
import qanda.table

log = logging.getLogger(__name__)


Question = Dict


class Model:
    def __init__(self):
        # conveniences
        self.message = qanda.table.message
        self.question = qanda.table.question
        self.answer = qanda.table.answer  # to delete
        self.subscriber = qanda.table.subscriber
        self.auth_token = qanda.table.auth_token
        self.client = qanda.table.dynamodb

    def make_id(self) -> str:
        return str(uuid.uuid4())

    def id_and_created(self, id_=None):
        if id_ is None:
            id_ = self.make_id()
        return dict(
            id=id_,
            created=int(time.time()),
        )

    def get_questions_by_id(self, question_ids: List[str]) -> List[Dict]:
        """Fetch a bunch of questions at once."""
        # FIXME: this is limited to 100 items for now
        # https://boto3.readthedocs.io/en/latest/reference/services/dynamodb.html#DynamoDB.Client.batch_get_item
        keys = [{'id': qid} for qid in question_ids]
        res = self.client.batch_get_item(
            RequestItems={
                'qanda.question': {
                    'Keys': keys,
                }
            }
        )
        questions = res['Responses']['qanda.question']
        # sort by date
        questions = sorted(questions, key=lambda q: q['created'])
        return questions

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
        return self.question_append_answer(question, answer)

    def new_question_from_web(self,
                              body: str,
                              remote_ip: str=None) -> Question:
        """Record and publish question asked from web form."""
        # record question
        q = dict(
            body=body,
            remote_ip=remote_ip,
            **self.id_and_created(),
            source='web',
        )
        self.question.put_item(Item=q)
        return q

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

    def question_append_answer(self, question: Dict, answer: Dict) -> Dict:
        # add answer to 'answers' field
        res = self.question.update_item(
            Key={'id': question['id']},
            AttributeUpdates={
                'answers': {
                    'Value': [answer],
                    'Action': 'ADD',
                }
            },
        )
        return res

    def new_answer_from_web(self, body: str, question: Dict, remote_ip: str=None) -> Dict:
        answer = {
            **self.id_and_created(),
            'body': body,
            'question_id': question['id'],
            'source': 'web',
            'remote_ip': remote_ip,
        }
        updated = self.question_append_answer(question, answer)
        g_notify.notify_of_answer(answer)
        return updated

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

    def get_question(self, id: str) -> Dict:
        question = self.question.get_item(Key={'id': id})['Item']
        return question

    def get_questions(self, source: str=None, start_key: Dict=None) -> Dict:
        """Get latest questions.

        Returns:

        """
        query_params = dict(
            Limit=100,
            IndexName='source-created-index',  # FIXME: put in CF
            ScanIndexForward=False,  # give us most recent first
        )

        if source:
            query_params['KeyConditionExpression'] = Key('source').eq(source)  # filter by source
        else:
            query_params['KeyConditionExpression'] = Key('source').exists()  # any
        if start_key:
            query_params['ExclusiveStartKey'] = start_key

        res = self.question.query(**query_params)

        return res

"""
get_questions:
 'Items': [{'body': 'What are the differences between HTTP and HTTPS ?',
            'created': Decimal('1534024050'),
            'id': '5fa0f742-ca28-44c2-aa67-72b4047d621b',
            'slack_channel_id': 'CC75SLZ4M',
            'slack_channel_name': 'qa-test',
            'slack_team_domain': 'tahmazlar',
            'slack_team_id': 'T7WBBHJ3F',
            'slack_user_id': 'U7W4Z3DJP',
            'slack_user_name': 'sarpdoruk',
            'source': 'slack'},
           {'body': 'what time is it?',
            'created': Decimal('1533753429'),
            'id': 'd74b4a90-1c81-4b1e-b98b-b96951a8961d',
            'slack_channel_id': 'CC577FN5B',
            'slack_channel_name': 'better_than_webex',
            'slack_team_domain': 'newchaterrday',
            'slack_team_id': 'TC4BFUE6L',
            'slack_user_id': 'UC6CJA0DU',
            'slack_user_name': 'jeremiah.belz',
            'source': 'slack'}],
 'LastEvaluatedKey': {'created': Decimal('1533753429'),
                      'id': 'd74b4a90-1c81-4b1e-b98b-b96951a8961d',
                      'source': 'slack'},
 'ResponseMetadata': {'HTTPHeaders': {'connection': 'keep-alive',
                                      'content-length': '916',
                                      'content-type': 'application/x-amz-json-1.0',
                                      'date': 'Sun, 12 Aug 2018 11:28:40 GMT',
                                      'server': 'Server',
                                      'x-amz-crc32': '3304068867',
                                      'x-amzn-requestid': 'LEM3OQISK00BQR3UHD0BLRTUTNVV4KQNSO5AEMVJF66Q9ASUAAJG'},
                      'HTTPStatusCode': 200,
                      'RequestId': 'LEM3OQISK00BQR3UHD0BLRTUTNVV4KQNSO5AEMVJF66Q9ASUAAJG',
                      'RetryAttempts': 0},
 'ScannedCount': 2}


"""
