import awsgi
from qanda import app


def lambda_handler(event, context):
    # pprint(event)
    return awsgi.response(app, event, context)
