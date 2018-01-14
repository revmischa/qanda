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
    print(f"RETSTESTT: {os.getenv('TEST_REGION')}")
    boto3.setup_default_session(region_name=os.getenv('TEST_REGION', 'eu-central-1'))

boto_setup()


##############


app = Flask(__name__)
# load config
app.config.from_pyfile('config.py', silent=False)
# optional local config
app.config.from_pyfile('local.cfg', silent=True)

from qanda.twil import Twil
twil: Twil = Twil()

from qanda.model import Model
model: Model = Model()

import qanda.views.slack
import qanda.views.twilio
