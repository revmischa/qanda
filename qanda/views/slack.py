from qanda.slack import SlackSlashcommandSchema, SlackSlashcommandResponseSchema
from qanda import model, app
from flask_apispec import use_kwargs, marshal_with


@app.route('/slack/slash_ask', methods=['POST'])
@use_kwargs(SlackSlashcommandSchema(strict=True))
@marshal_with(SlackSlashcommandResponseSchema)
def slack_slash_ask(**kwargs):
    # save question
    model.new_question_from_slack(**kwargs)
    return {'text': "Your question has been asked. Please wait for random humans to answer it."}
