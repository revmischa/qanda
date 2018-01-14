from qanda.model import Model
import boto3
import os

print(f"RETSTESTT: {os.getenv('TEST_REGION')}")
boto3.setup_default_session(region_name=os.getenv('TEST_REGION', 'eu-central-1'))

model: Model = Model()
