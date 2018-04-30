import os
import sys
vendor_path = os.path.abspath(os.path.join(__file__, '..', '..', 'vendor'))
lib_path = os.path.abspath(os.path.join(__file__, '..', '..'))
sys.path.append(lib_path)
sys.path.append(vendor_path)
from flask import Flask
import logging
from slack_logger import SlackHandler, SlackFormatter

log = logging.getLogger(__name__)


def boto_setup():
    import boto3
    # boto_session = boto3.session.Session()
    # print(f"REGION: {boto_session.region_name}")
    # boto3.setup_default_session(region_name=os.getenv('TEST_REGION', 'eu-central-1'))
    boto3.set_stream_logger('botocore', level=logging.INFO)

def log_setup(app):
    slack_log_endpoint = app.config.get('SLACK_LOG_ENDPOINT')
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    handlers = [ch]
    if slack_log_endpoint:
        sh = SlackHandler(slack_log_endpoint)
        sh.setFormatter(SlackFormatter())
        sh.setLevel(logging.WARN)
        handlers.append(sh)

    logging.basicConfig(handlers=handlers)
    logging.getLogger('botocore.vendored.requests.packages.urllib3.connectionpool').setLevel(logging.WARNING)
    logging.getLogger('botocore.credentials').setLevel(logging.WARNING)

# init AWS
boto_setup()

##############

app = Flask(__name__)
# load config
app.config.from_pyfile('config.py', silent=False)
# optional local config
app.config.from_pyfile('local.cfg', silent=True)
log_setup(app)

from qanda.invoker import Invoker
g_invoker = Invoker()

from qanda.twil import Twil
g_twil = Twil()

from qanda.notify import Notify
g_notify = Notify()

from qanda.model import Model
g_model = Model()

import qanda.views.index
import qanda.views.slack
import qanda.views.twilio

__all__ = ('g_twil', 'g_notify', 'g_model', 'g_invoker', 'app')
