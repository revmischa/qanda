import os, sys
vendor_path = os.path.abspath(os.path.join(__file__, '..', '..', 'vendor'))
lib_path = os.path.abspath(os.path.join(__file__, '..', '..'))
sys.path.append(lib_path)
sys.path.append(vendor_path)
from flask import Flask


def boto_setup():
    import boto3
    boto_session = boto3.session.Session()
    print(f"REGION: {boto_session.region_name}")
    # boto3.setup_default_session(region_name=os.getenv('TEST_REGION', 'eu-central-1'))


boto_setup()

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

__all__ = ('g_twil', 'g_notify', 'g_model', 'app')
