"""Process a slack event."""
from pprint import pprint
from qanda.slack import SlackApp


def lambda_handler(event, context):
    pprint(event)
    evt_callback = event['slack_event_callback']

    team_id = evt_callback['team_id']
    slack = SlackApp(team_id)
    slack.handle_event_callback(evt_callback)
