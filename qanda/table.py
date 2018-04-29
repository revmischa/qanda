import boto3

dynamodb = boto3.resource('dynamodb')

message = dynamodb.Table('qanda.message')
question = dynamodb.Table('qanda.question')
answer = dynamodb.Table('qanda.answer')
subscriber = dynamodb.Table('qanda.subscriber')
auth_token = dynamodb.Table('qanda.auth_token')

__all__ = ('message', 'question', 'answer', 'subscriber')
