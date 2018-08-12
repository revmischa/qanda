from qanda import app, g_model
from flask import request
from flask_apispec import use_kwargs, marshal_with
from marshmallow import fields, Schema
import simplejson as json  # for handling Decimal types from dynamodb


class QuestionSchema(Schema):
    body = fields.Str(required=True)
    tags = fields.Str(many=True, required=False)
    created = fields.Int(dump_only=True)


class QuestionListSchema(Schema):
    start_key = fields.Str()
    source = fields.Str(missing='web')
    questions = fields.Nested(QuestionSchema, many=True)


@app.route('/api/question/ask', methods=['POST'])
@use_kwargs(QuestionSchema(strict=True))
def api_question_ask(body, tags=[]):
    """Ask a question from the web."""
    g_model.new_question_from_web(body=body, remote_ip=request.remote_addr)
    return f"question asked!"


@app.route('/api/question', methods=['GET'])
@use_kwargs(QuestionListSchema(strict=True))
@marshal_with(QuestionListSchema(strict=True))
def api_list_questions(start_key: str=None, source: str=None):
    """Get a list of recent questions."""
    start_key = json.loads(start_key) if start_key else None
    res = g_model.get_questions(source=source, start_key=start_key)
    return dict(
        questions=res['Items'],
        start_key=json.dumps(res['LastEvaluatedKey']) if 'LastEvaluatedKey' in res else None,
    )
