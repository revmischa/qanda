from marshmallow import fields, Schema
from flask import request

class SlackSlashcommandSchema(Schema):
    """Request and response marshalling for Slack slashcommands.

    https://api.slack.com/custom-integrations/slash-commands#how_do_commands_work
    """
    text = fields.Str()
    token = fields.Str()
    team_id = fields.Str()
    team_domain = fields.Str()
    channel_id = fields.Str()
    channel_name = fields.Str()
    user_id = fields.Str()
    user_name = fields.Str()
    command = fields.Str()
    response_url = fields.Str()


class SlackSlashcommandResponseSchema(Schema):
    """Marshal a response for returning a slashcommand status.

    https://api.slack.com/custom-integrations/slash-commands#responding_to_a_command
    """
    text = fields.Str(required=False)
    response_type = fields.Str(required=True)
