"""Process a slack event."""
from pprint import pprint


def lambda_handler(event, context):
    print("got invoked!")
    pprint(event)
    pprint(context)
