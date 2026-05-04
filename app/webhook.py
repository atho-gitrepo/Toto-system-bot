from flask import Flask, request, jsonify
import logging
from config import config
from .bot import TotoBot
import json

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
toto_bot = TotoBot()

@app.route('/', methods=['GET'])
def home():
    """Home endpoint for testing"""
    return jsonify({
        'status': 'running',
        'message': 'Toto System 8 Bot is active',
        'endpoints': {
            'webhook': '/webhook (POST)',
            'health': '/health (GET)',
            'home': '/ (GET)'
        }
    }), 200

@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': __import__('datetime').datetime.now().isoformat(),
        'firebase_initialized': toto_bot.firebase.initialized if hasattr(toto_bot, 'firebase') else False
    }), 200

@app.route('/webhook', methods=['POST'])
def webhook():
    """Handle Telegram webhook - accepts any content type"""
    try:
        # Handle different content types
        if request.is_json:
            data = request.get_json()
        elif request.form:
            # Handle form data
            data = request.form.to_dict()
            # If there's a 'payload' field, try to parse it as JSON
            if 'payload' in data:
                try:
                    data = json.loads(data['payload'])
                except:
                    pass
        else:
            # Try to parse raw data
            raw_data = request.get_data(as_text=True)
            try:
                data = json.loads(raw_data) if raw_data else {}
            except:
                data = {}
        
        logger.info(f"Webhook received: {data}")
        
        # Process update if it's a Telegram update
        if data and 'message' in data:
            message = data['message']
            text = message.get('text', '')
            chat_id = str(message['chat']['id'])
            
            # Respond based on command
            if text == '/start':
                toto_bot.telegram.send_message(
                    "🎯 Toto System 8 Bot Active!\n\nCommands:\n/last - Last numbers\n/history - Last 5 generations\n/roi - ROI statistics",
                    chat_id
                )
            elif text == '/last':
                last = toto_bot.firebase.get_last_generation()
                if last:
                    numbers = ' '.join(map(str, last.get('numbers', [])))
                    date = last.get('date', 'Unknown')[:10]
                    toto_bot.telegram.send_message(f"📅 Last numbers ({date}):\n<code>{numbers}</code>", chat_id)
                else:
                    toto_bot.telegram.send_message("No numbers generated yet.", chat_id)
            elif text == '/history':
                history = toto_bot.get_history(5)
                if history:
                    message = "<b>📜 Last 5 Generations</b>\n\n"
                    for i, entry in enumerate(history, 1):
                        date = entry.get('date', 'Unknown')[:10]
                        numbers = ' '.join(map(str, entry.get('numbers', [])))
                        message += f"{i}. {date}: <code>{numbers}</code>\n"
                    toto_bot.telegram.send_message(message, chat_id)
                else:
                    toto_bot.telegram.send_message("No history available.", chat_id)
            elif text == '/roi':
                report = toto_bot.roi_service.get_roi_report()
                toto_bot.telegram.send_message(report, chat_id)
            elif text == '/generate':
                # Manual generation
                result = toto_bot.generate_weekly_numbers()
                if result.get('saved'):
                    toto_bot.telegram.send_message(f"✅ Numbers generated!\nNumbers: {' '.join(map(str, result['numbers']))}", chat_id)
                else:
                    toto_bot.telegram.send_message("❌ Failed to generate numbers", chat_id)
            else:
                toto_bot.telegram.send_message(
                    "Send /start to see available commands",
                    chat_id
                )
        
        return jsonify({'status': 'ok'}), 200
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)