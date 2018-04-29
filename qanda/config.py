import os
import boto3

# AWS SSM encrypted parameter store
ssm = boto3.client('ssm')


def get_ssm_param(param_name: str) -> str:
    """Get an encrypted AWS Systems Manger secret."""
    response = ssm.get_parameters(
        Names=[param_name],
        WithDecryption=True,
    )
    if not response['Parameters'] or not response['Parameters'][0] or not response['Parameters'][0]['Value']:
        raise Exception(
            f"Configuration error: missing AWS SSM parameter: {param_name}")
    return response['Parameters'][0]['Value']


###

TWILIO_API_SID = get_ssm_param('qanda_twilio_account_sid')
TWILIO_API_SECRET = get_ssm_param('qanda_twilio_account_secret')

SLACK_OAUTH_CLIENT_ID = get_ssm_param('qa_slack_oauth_client_id')
SLACK_OAUTH_CLIENT_SECRET = get_ssm_param('qa_slack_oauth_client_secret')
SLACK_VERIFICATION_TOKEN = get_ssm_param('qanda_slack_verification_token')

# maybe don't hardcode?
SLACK_OAUTH_REDIRECT_URL = "https://qanda.llolo.lol/v1/Prod/slack/oauth"
