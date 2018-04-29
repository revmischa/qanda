import logging
import qanda.table
from qanda import g_twil
from qanda.slack import SlackApp

log = logging.getLogger(__name__)


class Notify:
    def notify_of_question(self, question):
        # send out messages to subscribers
        # FIXME: paginate
        subscribers = qanda.table.subscriber.scan()  # NB only returns 1MB of results
        for sub in subscribers['Items']:
            if 'phone' in sub:
                self.notify_sms_of_question(sub, question)
            elif 'slack_channel_id' in sub:
                self.notify_slack_of_question(sub, question)
            else:
                log.error("got subscriber but no phone or slack_channel_id")

    def notify_of_answer(self, answer):
        # get question
        question_id = answer['question_id']
        question = qanda.table.question.get_item(Key={'id': question_id})['Item']
        assert question
        source = question['source']
        # notify
        if source == 'slack':
            self.notify_slack_of_answer(question, answer)
        elif source == 'sms':
            self.notify_sms_of_answer(question, answer)
        else:
            log.error(f"unknown question source {question}")

    def notify_sms_of_question(self, subscriber, question):
        # text question
        question_body: str = question['body']
        phone: str = subscriber['phone']
        g_twil.send_sms(
            question_id=question['id'],
            to=phone,
            body=f"Question:\n\"{question_body}\"\n\nReply w/ answer",
        )

    def notify_slack_of_question(self, subscriber, question):
        question_body = question['body']
        channel_id: str = subscriber['slack_channel_id']
        team_id: str = subscriber['team_id']
        client = SlackApp.get_client_for_team_id(team_id)
        # post question
        client.api_call(
            "chat.postMessage",
            channel=channel_id,
            text=f"""New question "{question_body}"\nType A: ... to reply""",
        )

    def notify_sms_of_answer(self, question, answer):
        pass

    def notify_slack_of_answer(self, question, answer):
        """Post answer to asker in channel or PM."""
        channel_id = question['slack_channel_id']
        team_id = question['slack_team_id']
        user_id = question['slack_user_id']
        question_body = question['body']
        answer_body = answer['body']

        # these should all be set
        assert team_id
        assert user_id
        assert question_body
        assert channel_id
        assert answer_body

        client = SlackApp.get_client_for_team_id(team_id)
        if not client:
            return

        # COULD start/reply to a thread instead of just posting a response in channel...
        # but fuck threads.
        client.api_call(
            "chat.postMessage",
            channel=channel_id,
            text=f"""New answer for question "{question_body}": {answer_body}""",
        )
