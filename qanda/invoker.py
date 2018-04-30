import boto3
import logging
import json
from qanda import app

log = logging.getLogger(__name__)


class Invoker:
    def encode_lambda_payload(self, payload):
        if payload is None:
            return None
        return json.dumps(payload)

    def invoke_async(self, func: str, payload=None):
        """Async invoke a lambda, whose name is in app config under `func`."""
        awslambda = boto3.client('lambda')

        # look in app config under func to get name (from cloudformation)
        func_name = app.config.get(func)
        if not func_name:
            log.error(f"can't invoke lambda; don't have {func} configured")
            return

        return awslambda.invoke(
            FunctionName=func_name,
            InvocationType='Event',
            Payload=self.encode_lambda_payload(payload),
        )
