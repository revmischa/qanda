from qanda import app
import awsgi


def lambda_handler(event, context):
    """Main entry point for API gateway."""
    return awsgi.response(app, event, context)
