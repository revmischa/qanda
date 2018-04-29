import logging
import qanda.table
from slackclient import SlackClient
from qanda import g_twil

log = logging.getLogger(__name__)


class Notify:
    def notify_of_question(self, question):
        # send out messages to subscribers
        # FIXME: paginate
        subscribers = self.subscriber.scan()  # NB only returns 1MB of results
        for sub in subscribers['Items']:
            if 'phone' in sub:
                self.notify_sms_of_question(sub, question)
            elif 'slack_channel_id' in sub:
                self.notify_slack_of_question(sub, question)
            else:
                log.error("got subscriber but no phone or slack_channel_id")

    def notify_of_answer(self, answer):
        self.notify_slack_of_answer(answer)

    def get_slack_bot_client(self, auth_token) -> SlackClient:
        # make a client with the bot token
        if 'bot_auth_token' not in auth_token:
            raise Exception(f"missing bot_auth_token in {auth_token}")
        bot_token = auth_token['bot_auth_token']
        sc = SlackClient(bot_token)
        return sc

    def get_slack_bot_client_for_team(self, team_id, team_domain='unknown') -> SlackClient:
        # look up auth token for this team so we can reply
        auth_token = qanda.table.auth_token.get_item(Key={'slack_team_id': team_id})['Item']
        if not auth_token:
            log.warning(f"can't notify slack team {team_id} ({team_domain}) of response - missing auth token")
            return None
        # now we have an auth token and everything we need to notify the user or channel
        client = self.get_slack_bot_client(auth_token)
        return client

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
        team_domain = subscriber['team_domain'] if 'team_domain' in subscriber else None
        client = self.get_slack_bot_client_for_team(team_id=team_id, team_domain=team_domain)
        # post question
        client.api_call(
            "chat.postMessage",
            channel=channel_id,
            text=f"""New question "{question_body}"\nType A: ... to reply""",
        )

    def notify_slack_of_answer(self, answer):
        """Post answer to asker in channel or PM."""
        # look up question info
        question_id = answer['question_id']
        assert question_id
        # get question
        question = qanda.table.question.get_item(Key={'id': question_id})['Item']
        assert question
        source = question['source']
        channel_id = question['slack_channel_id']
        team_domain = question['slack_team_domain']
        team_id = question['slack_team_id']
        user_id = question['slack_user_id']
        question_body = question['body']
        answer_body = answer['body']

        # these should all be set
        assert source == 'slack'
        assert team_domain
        assert team_id
        assert user_id
        assert question_body
        assert channel_id
        assert answer_body

        client = self.get_slack_bot_client_for_team(team_id=team_id, team_domain=team_domain)
        if not client:
            return

        # COULD start/reply to a thread instead of just posting a response in channel...
        # but fuck threads.
        client.api_call(
            "chat.postMessage",
            channel=channel_id,
            text=f"""New answer for question "{question_body}": {answer_body}""",
        )
