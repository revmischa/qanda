import os, sys
vendor_path = os.path.abspath(os.path.join(__file__, '..', '..', 'vendor'))
lib_path = os.path.abspath(os.path.join(__file__, '..', '..'))
sys.path.append(lib_path)
sys.path.append(vendor_path)
from flask import Flask

app = Flask(__name__)
# load config
app.config.from_pyfile('config.py', silent=False)
# optional local config
app.config.from_pyfile('local.cfg', silent=True)

from qanda.model import Model
from qanda.twil import Twil
model: Model = Model()
twil: Twil = Twil()

import qanda.views.slack
import qanda.views.twilio


import boto3
boto_session = boto3.session.Session()
print(f"REGION: {boto_session.region_name}")
print(f"RETSTESTT: {os.getenv('TEST_REGION')}")
boto3.setup_default_session(region_name=os.getenv('TEST_REGION', 'eu-central-1'))
