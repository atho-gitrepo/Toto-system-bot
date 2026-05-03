from flask import Flask, request, jsonify
import logging
from config import config
from .bot import TotoBot

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
toto_bot = TotoBot()

@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        data = request.get_json()
        if data and 'message' in data:
            message = data['message']
            text = message.get('text', '')
            chat_id = message['chat']['id']
            
            if text == '/start':
                toto_bot.telegram.send_message("🎯 Toto Bot Active!\nCommands: /last, /history, /roi")
            elif text == '/last':
                last = toto_bot.firebase.get_last_generation()
                if last:
                    numbers = ' '.join(map(str, last.get('numbers', [])))
                    toto_bot.telegram.send_message(f"Last: {numbers}")
                else:
                    toto_bot.telegram.send_message("No numbers yet")
            elif text == '/history':
                history = toto_bot.get_history(5)
                toto_bot.telegram.send_history(history)
            elif text == '/roi':
                report = toto_bot.roi_service.get_roi_report()
                toto_bot.telegram.send_message(report)
        
        return jsonify({'status': 'ok'}), 200
    except Exception as e:
        logger.error(f"Error: {e}")
        return jsonify({'status': 'error'}), 500

@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'healthy'}), 200
