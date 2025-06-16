import flask
from flask import request
import os
from bot import Bot, QuoteBot, ImageProcessingBot

import requests
app = flask.Flask(__name__)

TELEGRAM_TOKEN = os.environ['TELEGRAM_TOKEN']
TELEGRAM_CHAT_URL = os.environ['TELEGRAM_CHAT_URL']


@app.route('/', methods=['GET'])
def index():
    return 'Ok'

YOLO_URL = os.environ.get("YOLO_URL", "http://<YOLO_EC2_PRIVATE_IP>:8080")  # from .env

@app.route('/predictions/<prediction_id>', methods=['POST'])
def prediction(prediction_id):
    try:
        # Send request to YoloService endpoint
        response = requests.post(f"{YOLO_URL}/predictions/{prediction_id}")

        if response.status_code == 200:
            prediction = response.json()
            return prediction  # contains 'status', 'labels', 'text'
        else:
            return {"status": "error", "message": "Prediction not found"}, 404

    except Exception as e:
        return {"status": "error", "message": str(e)}, 500

@app.route(f'/{TELEGRAM_TOKEN}/', methods=['POST'])
def webhook():
    req = request.get_json()
    bot.handle_message(req['message'])
    return 'Ok'


if __name__ == "__main__":
    bot = ImageProcessingBot(TELEGRAM_TOKEN, TELEGRAM_CHAT_URL)

    app.run(host='0.0.0.0', port=8443)
