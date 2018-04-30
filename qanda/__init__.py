import os
import sys
vendor_path = os.path.abspath(os.path.join(__file__, '..', '..', 'vendor'))
lib_path = os.path.abspath(os.path.join(__file__, '..', '..'))
sys.path.append(lib_path)
sys.path.append(vendor_path)
from flask import Flask
import logging

log = logging.getLogger(__name__)


def boto_setup():
    import boto3
    # boto_session = boto3.session.Session()
    # print(f"REGION: {boto_session.region_name}")
    # boto3.setup_default_session(region_name=os.getenv('TEST_REGION', 'eu-central-1'))
    boto3.set_stream_logger('botocore', level=logging.INFO)


# init AWS
boto_setup()

# init logging
logging.basicConfig(level=logging.INFO)
logging.getLogger('botocore.vendored.requests.packages.urllib3.connectionpool').setLevel(logging.WARNING)
logging.getLogger('botocore.credentials').setLevel(logging.WARNING)

##############

app = Flask(__name__)
# load config
app.config.from_pyfile('config.py', silent=False)
# optional local config
app.config.from_pyfile('local.cfg', silent=True)

from qanda.twil import Twil
g_twil = Twil()

from qanda.notify import Notify
g_notify = Notify()

from qanda.model import Model
g_model = Model()

import qanda.views.index
import qanda.views.slack
import qanda.views.twilio


def invoke_async(func: str, payload=None):
    """Async invoke a lambda, whose name is in app config under `func`."""
    import boto3
    awslambda = boto3.client('lambda')

    # look in app config under func to get name (from cloudformation)
    func_name = app.config.get(func)
    if not func_name:
        log.error(f"can't invoke lambda; don't have {func} configured")
        return

    return awslambda.invoke(
        FunctionName=func_name,
        InvocationType='Event',
        Payload=payload,
    )

__all__ = ('g_twil', 'g_notify', 'g_model', 'app')
