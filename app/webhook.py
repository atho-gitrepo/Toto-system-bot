from flask import Flask, request, jsonify
import logging
from datetime import datetime
from config import config
from .bot import TotoBot

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
toto_bot = TotoBot()

# Admin chat ID (replace with your Telegram ID)
ADMIN_CHAT_ID = "787922010"  # @oohta2025

@app.route('/', methods=['GET'])
def home():
    """Home endpoint for testing"""
    return jsonify({
        'status': 'running',
        'message': 'Toto System 8 Bot is active',
        'version': '2.0.0',
        'endpoints': {
            'webhook': '/webhook (POST)',
            'health': '/health (GET)',
            'home': '/ (GET)'
        },
        'next_draw': toto_bot.get_draw_status() if hasattr(toto_bot, 'get_draw_status') else 'Not available'
    }), 200

@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    try:
        stats = toto_bot.firebase.get_roi_stats()
        pending = len(toto_bot.firebase.get_pending_generations()) if hasattr(toto_bot.firebase, 'get_pending_generations') else 0
        
        return jsonify({
            'status': 'healthy',
            'timestamp': datetime.now().isoformat(),
            'firebase_initialized': toto_bot.firebase.initialized,
            'stats': {
                'games_played': stats.get('games_played', 0),
                'total_spent': stats.get('total_spent', 0),
                'pending_checks': pending
            }
        }), 200
    except Exception as e:
        logger.error(f"Health check error: {e}")
        return jsonify({'status': 'unhealthy', 'error': str(e)}), 500

@app.route('/webhook', methods=['POST'])
def webhook():
    """Handle Telegram webhook"""
    try:
        data = request.get_json()
        logger.info(f"Webhook received: {data}")
        
        if not data or 'message' not in data:
            return jsonify({'status': 'ok', 'message': 'No message'}), 200
        
        message = data['message']
        text = message.get('text', '')
        chat_id = str(message['chat']['id'])
        username = message.get('from', {}).get('username', 'Unknown')
        first_name = message.get('from', {}).get('first_name', '')
        
        logger.info(f"Command from @{username} ({chat_id}): {text}")
        
        # Process commands
        if text == '/start':
            response = f"""🎯 <b>Toto System 8 Bot Activated!</b>

Welcome {first_name}! Your disciplined lottery system is ready.

<b>📋 Available Commands:</b>
/start - Show this message
/last - Last generated numbers
/history - Last 5 generations
/roi - ROI statistics
/draw - Current draw information
/next - Next draw details
/status - Bot system status
/help - Detailed help

<b>🤖 Automation:</b>
• Numbers generated 2 days before each draw
• Results checked automatically after draws
• Draws every Monday & Thursday at 6:30 PM

<i>Good luck and play responsibly! 🍀</i>"""
            toto_bot.telegram.send_message(response, chat_id)
        
        elif text == '/last':
            last = toto_bot.firebase.get_last_generation()
            if last:
                numbers = ' '.join(map(str, last.get('numbers', [])))
                date = last.get('date', 'Unknown')[:10]
                draw_no = last.get('draw_no', 'Unknown')
                status = last.get('status', 'pending')
                status_emoji = '✅' if status == 'completed' else '⏳'
                
                response = f"""📅 <b>Last Generation</b> {status_emoji}

Draw No: {draw_no}
Date: {date}
Numbers: <code>{numbers}</code>
Status: {status.upper()}

/last - Refresh
/history - View all"""
            else:
                response = "No numbers generated yet. Numbers will be generated before the next draw."
            toto_bot.telegram.send_message(response, chat_id)
        
        elif text == '/history':
            history = toto_bot.firebase.get_history(5)
            if history:
                response = "<b>📜 Last 5 Generations</b>\n\n"
                for i, entry in enumerate(history, 1):
                    date = entry.get('date', 'Unknown')[:10]
                    numbers = ' '.join(map(str, entry.get('numbers', [])))
                    draw_no = entry.get('draw_no', 'N/A')
                    matches = entry.get('matches', 0)
                    prize = entry.get('prize_amount', 0)
                    
                    if prize > 0:
                        response += f"{i}. Draw #{draw_no} ({date}): <code>{numbers}</code>\n   🎉 Won ${prize:,} ({matches} matches)\n\n"
                    else:
                        response += f"{i}. Draw #{draw_no} ({date}): <code>{numbers}</code>\n   No win\n\n"
                
                response += "<i>/roi - View detailed returns</i>"
            else:
                response = "No history available. Numbers will be generated for the next draw."
            toto_bot.telegram.send_message(response, chat_id)
        
        elif text == '/roi':
            stats = toto_bot.firebase.get_roi_stats()
            wins = stats.get('wins', 0)
            games = stats.get('games_played', 0)
            win_rate = (wins / games * 100) if games > 0 else 0
            
            response = f"""📊 <b>ROI Dashboard</b>

━━━━━━━━━━━━━━━━━━
📈 <b>Performance</b>
• Games Played: {games}
• Wins: {wins}
• Win Rate: {win_rate:.1f}%

💰 <b>Financial</b>
• Total Spent: ${stats.get('total_spent', 0):,}
• Total Returns: ${stats.get('total_return', 0):,}
• Net Profit: ${stats.get('net_profit', 0):,}
• ROI: {stats.get('roi', 0):.2f}%

━━━━━━━━━━━━━━━━━━
<i>System 8 Strategy - Long-term Discipline</i>

/status - System status
/history - View history"""
            toto_bot.telegram.send_message(response, chat_id)
        
        elif text == '/draw':
            from services.draw_manager import DrawManager
            draw_manager = DrawManager()
            draw_info = draw_manager.get_current_draw()
            
            response = f"""🎯 <b>Current Draw Information</b>

📅 Draw No: <b>{draw_info['draw_no']}</b>
📆 Date: {draw_info['draw_date']} ({draw_info['draw_day']})
⏰ Time: {draw_info['draw_time']}

⏳ Time remaining: {draw_info.get('days_until', '?')} days

📌 <b>Schedule:</b>
• Numbers Generation: 2 days before draw
• Result Checking: After 8:30 PM on draw day
• Notification: Automatic via Telegram

<i>Draws every Monday & Thursday at 6:30 PM</i>

/next - Next draw details
/status - System status"""
            toto_bot.telegram.send_message(response, chat_id)
        
        elif text == '/next':
            draw_info = toto_bot.get_draw_status()
            from datetime import datetime, timedelta
            
            response = f"""🎯 <b>Next TOTO Draw</b>

━━━━━━━━━━━━━━━━━━
📅 Draw No: <b>{draw_info['draw_no']}</b>
📆 Date: {draw_info['draw_date']} ({draw_info['draw_day']})
⏰ Time: {draw_info['draw_time']}
⏳ Days until draw: {draw_info['days_until']}

━━━━━━━━━━━━━━━━━━
⚙️ <b>Automation Schedule</b>
• Numbers Generated: {draw_info['generation_date']}
• Results Checked: After draw on {draw_info['check_date']}
• Notification: Sent immediately after checking

━━━━━━━━━━━━━━━━━━
📊 <b>Draw History</b>
• Last Draw: 4179 (May 4, 2026)
• Winning: 7-18-19-30-36-48 + 11

<i>Bot will automatically handle everything!</i>

/status - Check bot health"""
            toto_bot.telegram.send_message(response, chat_id)
        
        elif text == '/status':
            try:
                stats = toto_bot.firebase.get_roi_stats()
                pending = len(toto_bot.firebase.get_pending_generations()) if hasattr(toto_bot.firebase, 'get_pending_generations') else 0
                draw_info = toto_bot.get_draw_status()
                
                response = f"""🤖 <b>Bot System Status</b>

━━━━━━━━━━━━━━━━━━
✅ <b>System Health</b>
• Firebase: {'Connected' if toto_bot.firebase.initialized else 'Disconnected'}
• Bot Status: Active
• Uptime: Continuous

━━━━━━━━━━━━━━━━━━
📊 <b>Statistics</b>
• Games Played: {stats.get('games_played', 0)}
• Total Spent: ${stats.get('total_spent', 0):,}
• Total Returns: ${stats.get('total_return', 0):,}
• ROI: {stats.get('roi', 0):.2f}%
• Wins: {stats.get('wins', 0)}

━━━━━━━━━━━━━━━━━━
🎯 <b>Next Draw</b>
• Draw No: {draw_info['draw_no']}
• Date: {draw_info['draw_date']}
• Days Until: {draw_info['days_until']}

━━━━━━━━━━━━━━━━━━
⚙️ <b>Automation</b>
• Pending Checks: {pending}
• Auto-Generation: {'✓ Active' if draw_info['days_until'] <= 2 else '⏳ Waiting'}
• Auto-Checking: {'✓ Active' if pending > 0 else '⏳ Idle'}

<i>Bot is running normally and will handle all future draws automatically!</i>"""
                toto_bot.telegram.send_message(response, chat_id)
            except Exception as e:
                logger.error(f"Status command error: {e}")
                toto_bot.telegram.send_message("Error fetching status. Please try again later.", chat_id)
        
        elif text == '/help':
            response = """<b>📚 Complete Command List</b>

━━━━━━━━━━━━━━━━━━
<b>Basic Commands:</b>
/start - Activate bot and show welcome
/help - Show this help message

━━━━━━━━━━━━━━━━━━
<b>Information Commands:</b>
/last - Show your last generated numbers
/history - Show last 5 generations with results
/roi - Show ROI statistics
/draw - Current draw information
/next - Next draw details
/status - Bot system status

━━━━━━━━━━━━━━━━━━
<b>How It Works:</b>
1️⃣ Bot generates System 8 numbers 2 days before each draw
2️⃣ Numbers are saved to Firebase and sent to you
3️⃣ After draw, bot automatically checks results
4️⃣ You receive win/loss notification with prize amount
5️⃣ ROI is tracked automatically

━━━━━━━━━━━━━━━━━━
<b>Draw Schedule:</b>
• Monday at 6:30 PM
• Thursday at 6:30 PM

━━━━━━━━━━━━━━━━━━
<i>No action needed - bot works automatically!</i>

/status - Check if bot is ready for next draw"""
            toto_bot.telegram.send_message(response, chat_id)
        
        elif text == '/generate' and chat_id == ADMIN_CHAT_ID:
            # Admin only command
            result = toto_bot.manual_trigger_generation()
            if result.get('saved'):
                numbers = result['numbers']
                draw_no = result.get('draw_no', 'Unknown')
                response = f"""🔧 <b>Manual Generation Triggered (Admin)</b>

✅ Numbers generated for Draw #{draw_no}
🔢 Numbers: <code>{' '.join(map(str, numbers))}</code>
📅 Target: {result.get('draw_date', 'Unknown')}

<i>Notification sent to all subscribers</i>"""
            else:
                response = f"❌ Generation failed: {result.get('error', 'Unknown error')}"
            toto_bot.telegram.send_message(response, chat_id)
        
        elif text == '/check' and chat_id == ADMIN_CHAT_ID:
            # Admin only command
            result = toto_bot.manual_trigger_result_check()
            if result and result.get('checked'):
                response = f"""🔧 <b>Manual Result Check (Admin)</b>

✅ Results checked for Draw #{result.get('draw_no')}
🎯 Matches: {result.get('matches', 0)}
💰 Prize: ${result.get('prize_amount', 0):,}

<i>Notification sent to all subscribers</i>"""
            else:
                response = f"❌ Check failed: {result.get('error', 'Results not available')}"
            toto_bot.telegram.send_message(response, chat_id)
        
        else:
            # Unknown command
            response = f"""❓ Unknown command: {text}

Send /help to see all available commands.

<i>Tip: Bot works automatically! No action needed for draws.</i>"""
            toto_bot.telegram.send_message(response, chat_id)
        
        return jsonify({'status': 'ok'}), 200
        
    except Exception as e:
        logger.error(f"Webhook error: {e}", exc_info=True)
        return jsonify({'status': 'error', 'message': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)