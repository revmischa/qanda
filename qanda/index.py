from qanda import app
import awsgi

def lambda_handler(event, context):
    # pprint(event)
    return awsgi.response(app, event, context)
