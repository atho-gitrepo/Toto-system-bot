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

# Admin chat ID (your Telegram ID)
ADMIN_CHAT_ID = "787922010"

@app.route('/', methods=['GET'])
def home():
    """Home endpoint for testing"""
    return jsonify({
        'status': 'running',
        'message': 'Toto System 8 Bot is active',
        'version': '3.0.0',
        'hybrid_mode': 'enabled',
        'endpoints': {
            'webhook': '/webhook (POST)',
            'health': '/health (GET)',
            'home': '/ (GET)'
        }
    }), 200

@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    try:
        stats = toto_bot.firebase.get_roi_stats()
        return jsonify({
            'status': 'healthy',
            'timestamp': datetime.now().isoformat(),
            'firebase_initialized': toto_bot.firebase.initialized,
            'stats': {
                'games_played': stats.get('games_played', 0),
                'total_spent': stats.get('total_spent', 0),
                'total_return': stats.get('total_return', 0),
                'roi': stats.get('roi', 0)
            }
        }), 200
    except Exception as e:
        logger.error(f"Health check error: {e}")
        return jsonify({'status': 'unhealthy', 'error': str(e)}), 500

@app.route('/webhook', methods=['POST'])
def webhook():
    """Handle Telegram webhook with hybrid commands"""
    try:
        data = request.get_json()
        
        if not data or 'message' not in data:
            return jsonify({'status': 'ok'}), 200
        
        message = data['message']
        text = message.get('text', '')
        chat_id = str(message['chat']['id'])
        username = message.get('from', {}).get('username', 'Unknown')
        
        logger.info(f"Command from @{username} ({chat_id}): {text}")
        
        # Command: /start
        if text == '/start':
            response = """🎯 <b>Toto System 8 Bot Activated!</b>

Welcome to your automated lottery system!

<b>📋 Available Commands:</b>

<u>Information Commands:</u>
/start - Show this message
/last - Last generated numbers
/history - Last 5 generations with results
/roi - ROI statistics
/draw - Current draw information
/next - Next draw details
/status - Bot system status

<u>Hybrid Result Commands:</u>
/declare &lt;numbers&gt; + &lt;additional&gt; - Manually declare winning results
/check - Force check results for current draw

<u>Admin Commands:</u>
/generate - Force generate numbers (admin only)

<b>🤖 Automation:</b>
• Numbers generated 2 days before each draw
• Results auto-fetched from multiple sources
• Manual /declare available as backup

<i>Draws every Monday & Thursday at 6:30 PM</i>

Good luck! 🍀"""
            toto_bot.telegram.send_message(response, chat_id)
        
        # Command: /last
        elif text == '/last':
            last = toto_bot.firebase.get_last_generation()
            if last:
                numbers = ' '.join(map(str, last.get('numbers', [])))
                date = last.get('date', 'Unknown')[:10]
                draw_no = last.get('draw_no', 'Unknown')
                checked = last.get('checked', False)
                prize = last.get('prize_amount', 0)
                
                if checked and prize > 0:
                    status = f"✅ RESULT: Won ${prize:,}!"
                elif checked:
                    status = "❌ No win"
                else:
                    status = "⏳ Pending (draw not yet checked)"
                
                response = f"""📅 <b>Last Generation</b>

Draw #{draw_no} ({date})
Numbers: <code>{numbers}</code>
Status: {status}

/last - Refresh | /history - View all"""
            else:
                response = "No numbers generated yet. Numbers will be generated before the next draw."
            toto_bot.telegram.send_message(response, chat_id)
        
        # Command: /history
        elif text == '/history':
            history = toto_bot.get_history(5)
            if history:
                response = "<b>📜 Last 5 Generations</b>\n\n"
                for i, entry in enumerate(history, 1):
                    date = entry.get('date', 'Unknown')[:10]
                    numbers = ' '.join(map(str, entry.get('numbers', [])))
                    draw_no = entry.get('draw_no', 'N/A')
                    matches = entry.get('matches', 0)
                    prize = entry.get('prize_amount', 0)
                    checked = entry.get('checked', False)
                    
                    if checked and prize > 0:
                        response += f"{i}. Draw #{draw_no} ({date}): <code>{numbers}</code>\n   🎉 Won ${prize:,} ({matches} matches)\n\n"
                    elif checked:
                        response += f"{i}. Draw #{draw_no} ({date}): <code>{numbers}</code>\n   ❌ No win\n\n"
                    else:
                        response += f"{i}. Draw #{draw_no} ({date}): <code>{numbers}</code>\n   ⏳ Pending\n\n"
                
                response += "<i>/roi - View detailed returns</i>"
            else:
                response = "No history available."
            toto_bot.telegram.send_message(response, chat_id)
        
        # Command: /roi
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
<i>System 8 Strategy - Long-term Tracking</i>

/status - System status | /history - View history"""
            toto_bot.telegram.send_message(response, chat_id)
        
        # Command: /draw
        elif text == '/draw':
            try:
                from services.draw_scheduler import DrawScheduler
                scheduler = DrawScheduler()
                draw_info = scheduler.get_current_draw()
                
                response = f"""🎯 <b>Current Draw Information</b>

Draw No: <b>{draw_info['draw_no']}</b>
Date: {draw_info['draw_date']} ({draw_info['draw_day']})
Time: {draw_info['draw_time']} Singapore Time

Status: {draw_info.get('status', 'upcoming').upper()}

📌 <b>Schedule:</b>
• Numbers Generation: 2 days before draw
• Result Checking: After 8:30 PM on draw day

<u>If auto-fetch fails, use:</u>
/declare 7,18,19,30,36,48 + 11

/next - Next draw | /status - System status"""
                toto_bot.telegram.send_message(response, chat_id)
            except Exception as e:
                toto_bot.telegram.send_message(f"Error getting draw info: {e}", chat_id)
        
        # Command: /next
        elif text == '/next':
            try:
                from services.draw_scheduler import DrawScheduler
                scheduler = DrawScheduler()
                draw_info = scheduler.get_next_draw()
                
                response = f"""🎯 <b>Next TOTO Draw</b>

Draw No: <b>{draw_info['draw_no']}</b>
Date: {draw_info['draw_date']} ({draw_info['draw_day']})
Time: {draw_info['draw_time']} Singapore Time

⏳ Days until draw: {draw_info['days_until']}

⚙️ <b>Automation:</b>
• Numbers will be generated automatically
• Results will be checked after draw
• You will receive Telegram notifications

<i>Bot handles everything automatically!</i>

/draw - Current draw | /status - System status"""
                toto_bot.telegram.send_message(response, chat_id)
            except Exception as e:
                toto_bot.telegram.send_message(f"Error getting next draw: {e}", chat_id)
        
        # Command: /status
        elif text == '/status':
            try:
                stats = toto_bot.firebase.get_roi_stats()
                from services.draw_scheduler import DrawScheduler
                scheduler = DrawScheduler()
                draw_info = scheduler.get_next_draw()
                pending = len(toto_bot.firebase.get_pending_generations()) if hasattr(toto_bot.firebase, 'get_pending_generations') else 0
                
                response = f"""🤖 <b>Bot System Status</b>

━━━━━━━━━━━━━━━━━━
✅ <b>System Health</b>
• Firebase: {'Connected' if toto_bot.firebase.initialized else 'Disconnected'}
• Bot Status: Active
• Mode: Hybrid (Auto-fetch + Manual fallback)

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
• Auto-Fetch: Active (4 methods)
• Manual Fallback: Available (/declare)

<i>Bot is running normally in hybrid mode!</i>"""
                toto_bot.telegram.send_message(response, chat_id)
            except Exception as e:
                toto_bot.telegram.send_message(f"Error getting status: {e}", chat_id)
        
        # Command: /help
        elif text == '/help':
            response = """<b>📚 Complete Command Guide</b>

━━━━━━━━━━━━━━━━━━
<b>📖 Information Commands:</b>
/start - Activate bot and show welcome
/help - Show this help message
/last - Show your last generated numbers
/history - Show last 5 generations with results
/roi - Show ROI statistics
/draw - Current draw information
/next - Next draw details
/status - Bot system status

━━━━━━━━━━━━━━━━━━
<b>🎯 Hybrid Result Commands:</b>
/declare &lt;numbers&gt; + &lt;additional&gt; - Manually declare winning results
/check - Force check results for current draw

━━━━━━━━━━━━━━━━━━
<b>🔧 Admin Commands:</b>
/generate - Force generate numbers for next draw

━━━━━━━━━━━━━━━━━━
<b>📝 Usage Examples:</b>
/declare 7,18,19,30,36,48 + 11
/check

━━━━━━━━━━━━━━━━━━
<b>🤖 How It Works:</b>
1️⃣ Bot generates numbers 2 days before each draw
2️⃣ After draw, bot auto-fetches results (4 methods)
3️⃣ If auto-fetch fails, use /declare command
4️⃣ Results are saved and ROI updated automatically

<i>Draws every Monday & Thursday at 6:30 PM</i>

/status - Check bot health"""
            toto_bot.telegram.send_message(response, chat_id)
        
        # Command: /declare (Manual result entry - Hybrid fallback)
        elif text.startswith('/declare'):
            try:
                # Parse the command: /declare 7,18,19,30,36,48 + 11
                content = text.replace('/declare', '').strip()
                
                if not content:
                    response = """❌ <b>Invalid format</b>

Please use: /declare 7,18,19,30,36,48 + 11

Examples:
/declare 7,18,19,30,36,48 + 11
/declare 1,2,3,4,5,6 + 7"""
                    toto_bot.telegram.send_message(response, chat_id)
                    return jsonify({'status': 'ok'}), 200
                
                # Parse numbers
                if '+' in content:
                    numbers_part, additional_part = content.split('+')
                    winning_numbers = [int(x.strip()) for x in numbers_part.split(',')]
                    additional = int(additional_part.strip())
                else:
                    # Assume just numbers
                    parts = content.split(',')
                    winning_numbers = [int(x.strip()) for x in parts[:6]]
                    additional = int(parts[6]) if len(parts) > 6 else 0
                
                # Validate
                if len(winning_numbers) != 6:
                    response = "❌ Please provide exactly 6 winning numbers.\nFormat: /declare 7,18,19,30,36,48 + 11"
                    toto_bot.telegram.send_message(response, chat_id)
                    return jsonify({'status': 'ok'}), 200
                
                if not all(1 <= n <= 49 for n in winning_numbers):
                    response = "❌ Numbers must be between 1 and 49"
                    toto_bot.telegram.send_message(response, chat_id)
                    return jsonify({'status': 'ok'}), 200
                
                # Get current draw
                from services.draw_scheduler import DrawScheduler
                scheduler = DrawScheduler()
                current_draw = scheduler.get_current_draw()
                draw_no = str(current_draw['draw_no'])
                
                # Save results manually
                toto_bot.result_service.manual_update_results(draw_no, winning_numbers, additional)
                toto_bot.firebase.record_draw_result(draw_no, winning_numbers, additional)
                
                # Check against user's numbers
                generation = toto_bot.firebase.get_generation_by_draw(draw_no)
                
                if generation:
                    from services.match_engine import MatchEngine
                    engine = MatchEngine()
                    match_result = engine.check_matches(generation['numbers'], winning_numbers)
                    
                    # Save result
                    result_data = {
                        'generation_id': generation['id'],
                        'draw_no': draw_no,
                        'numbers': generation['numbers'],
                        'winning_numbers': winning_numbers,
                        'additional_number': additional,
                        'matches': match_result['matches'],
                        'prize_group': match_result['prize_group'],
                        'prize_amount': match_result['prize_amount'],
                        'checked': True,
                        'checked_at': datetime.now().isoformat(),
                        'source': 'manual_declare'
                    }
                    toto_bot.firebase.save_result(generation['id'], result_data)
                    toto_bot.roi_service.update_roi(match_result['prize_amount'])
                    
                    if match_result['prize_amount'] > 0:
                        response = f"""🎉 <b>CONGRATULATIONS! YOU WON!</b> 🎉

━━━━━━━━━━━━━━━━━━
Draw #{draw_no}
Your Numbers: {generation['numbers']}
Winning Numbers: {winning_numbers} + {additional}
━━━━━━━━━━━━━━━━━━

✅ Matches: {match_result['matches']}
🏆 Prize Group: {match_result['prize_group']}
💰 Prize Amount: ${match_result['prize_amount']:,}

<i>Results saved and ROI updated!</i>

Check /roi for updated statistics!"""
                    else:
                        response = f"""📊 <b>Results Recorded</b>

━━━━━━━━━━━━━━━━━━
Draw #{draw_no}
Your Numbers: {generation['numbers']}
Winning Numbers: {winning_numbers} + {additional}
━━━━━━━━━━━━━━━━━━

Matches: {match_result['matches']}
No win this time.

<i>Results saved. Numbers for next draw will be generated automatically!</i>

Check /roi for updated statistics."""
                else:
                    response = f"""✅ <b>Results Saved</b>

Draw #{draw_no}
Winning Numbers: {winning_numbers} + {additional}

⚠️ No generation found for this draw.
Numbers will be generated for the next draw."""
                
                toto_bot.telegram.send_message(response, chat_id)
                
            except ValueError as e:
                response = f"❌ Invalid numbers. Please use format: /declare 7,18,19,30,36,48 + 11\nError: {e}"
                toto_bot.telegram.send_message(response, chat_id)
            except Exception as e:
                logger.error(f"Declare command error: {e}")
                response = f"❌ Error processing declaration: {e}"
                toto_bot.telegram.send_message(response, chat_id)
        
        # Command: /check (Force check results)
        elif text == '/check':
            try:
                response = "🔍 Checking for pending results..."
                toto_bot.telegram.send_message(response, chat_id)
                
                from services.draw_scheduler import DrawScheduler
                scheduler = DrawScheduler()
                current_draw = scheduler.get_current_draw()
                draw_no = str(current_draw['draw_no'])
                
                # Try to fetch results
                result = toto_bot.result_service.get_draw_result(draw_no)
                
                if result and result.get('winning_numbers'):
                    # Process results
                    generation = toto_bot.firebase.get_generation_by_draw(draw_no)
                    if generation:
                        from services.match_engine import MatchEngine
                        engine = MatchEngine()
                        match_result = engine.check_matches(generation['numbers'], result['winning_numbers'])
                        
                        result_data = {
                            'generation_id': generation['id'],
                            'draw_no': draw_no,
                            'numbers': generation['numbers'],
                            'winning_numbers': result['winning_numbers'],
                            'additional_number': result.get('additional_number', 0),
                            'matches': match_result['matches'],
                            'prize_group': match_result['prize_group'],
                            'prize_amount': match_result['prize_amount']
                        }
                        toto_bot.firebase.save_result(generation['id'], result_data)
                        toto_bot.roi_service.update_roi(match_result['prize_amount'])
                        
                        if match_result['prize_amount'] > 0:
                            response = f"🎉 WINNER! Matches: {match_result['matches']}, Prize: ${match_result['prize_amount']:,}"
                        else:
                            response = f"Results checked. Matches: {match_result['matches']}. No win."
                    else:
                        response = "No generation found for this draw."
                else:
                    response = "⚠️ Results not yet available. Please try again later or use /declare command."
                
                toto_bot.telegram.send_message(response, chat_id)
                
            except Exception as e:
                response = f"Error checking results: {e}"
                toto_bot.telegram.send_message(response, chat_id)
        
        # Command: /generate (Admin only)
        elif text == '/generate' and chat_id == ADMIN_CHAT_ID:
            try:
                response = "🎯 Generating numbers for next draw..."
                toto_bot.telegram.send_message(response, chat_id)
                
                from services.draw_scheduler import DrawScheduler
                scheduler = DrawScheduler()
                draw_info = scheduler.get_next_draw()
                
                result = toto_bot.generate_weekly_numbers(draw_info)
                
                if result.get('saved'):
                    numbers = ' '.join(map(str, result['numbers']))
                    response = f"""✅ <b>Numbers Generated!</b>

Draw #{draw_info['draw_no']}
Date: {draw_info['draw_date']}
Numbers: <code>{numbers}</code>

Results will be checked automatically after the draw."""
                else:
                    response = f"❌ Generation failed: {result.get('error', 'Unknown error')}"
                
                toto_bot.telegram.send_message(response, chat_id)
                
            except Exception as e:
                response = f"Error generating numbers: {e}"
                toto_bot.telegram.send_message(response, chat_id)
        
        # Unknown command
        else:
            response = f"""❓ Unknown command: {text}

Send /help to see all available commands.

<i>Tip: Bot works automatically! 
If results don't auto-fetch, use:
/declare 7,18,19,30,36,48 + 11</i>"""
            toto_bot.telegram.send_message(response, chat_id)
        
        return jsonify({'status': 'ok'}), 200
        
    except Exception as e:
        logger.error(f"Webhook error: {e}", exc_info=True)
        return jsonify({'status': 'error', 'message': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)