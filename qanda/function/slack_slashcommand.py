"""Process a slack slashcommand."""
from pprint import pprint


def lambda_handler(event, context):
    print("/ got invoked!")
    pprint(event)
    pprint(context)
