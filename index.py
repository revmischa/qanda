import awsgi
from flask import request, Flask, jsonify

app = Flask(__name__)

def lambda_handler(event, context):
    return awsgi.response(app, event, context)

@app.route('/test', methods=['GET', 'POST'])
def test():
    data = {
        'form': request.form.copy(),
        'args': request.args.copy(),
        'json': request.json
    }
    return jsonify(status=200, message="ok")

@app.route('/twilio/sms/mo', methods=['POST'])
def twilio_sms_mo():
    """Handle incoming SMS."""
    return "ok"

if __name__ == '__main__':
    app.run(debug=True)
