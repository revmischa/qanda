"""Process a slack slashcommand."""
from pprint import pprint
from qanda import g_model


def lambda_handler(event, context):
    pprint(event)
    args = event['slack_args']
    cmd = event['command']

    if cmd == 'ask':
        g_model.new_question_from_slack(**args)

    else:
        raise Exception(f'Unknown command {cmd}')
