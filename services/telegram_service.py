import requests
from typing import List, Dict, Optional
from config import config
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TelegramService:
    def __init__(self):
        self.token = config.TELEGRAM_TOKEN
        self.base_url = f"https://api.telegram.org/bot{self.token}"
        self.default_chat_id = config.TELEGRAM_CHAT_ID
        logger.info(f"Telegram Service initialized. Default chat ID: {self.default_chat_id}")
    
    def send_message(self, text: str, chat_id: Optional[str] = None) -> bool:
        """Send a message to Telegram"""
        target_chat = chat_id or self.default_chat_id
        
        if not target_chat:
            logger.error("No chat_id provided and no default chat_id set")
            return False
        
        try:
            url = f"{self.base_url}/sendMessage"
            payload = {
                'chat_id': target_chat,
                'text': text,
                'parse_mode': 'HTML'
            }
            response = requests.post(url, json=payload, timeout=10)
            
            if response.status_code == 200:
                logger.info(f"Message sent successfully to {target_chat}")
                return True
            else:
                logger.error(f"Telegram error: {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Error sending Telegram message: {e}")
            return False
    
    def send_numbers(self, numbers: List[int], draw_info: Dict = None, chat_id: Optional[str] = None) -> bool:
        """Format and send generated numbers"""
        numbers_str = ' '.join(map(str, numbers))
        
        if draw_info:
            message = f"""🎯 <b>TOTO System 8 - Weekly Numbers</b>

📅 Draw #{draw_info.get('draw_no', '4180')}
📆 Date: {draw_info.get('draw_date', 'May 7, 2026')} ({draw_info.get('draw_day', 'Thursday')})
⏰ Time: 6:30 PM Singapore Time

🔢 Your Numbers: <code>{numbers_str}</code>

📊 <b>Number Distribution:</b>
• Low (1-16): {len([n for n in numbers if n <= 16])} numbers
• Mid (17-33): {len([n for n in numbers if 17 <= n <= 33])} numbers
• High (34-49): {len([n for n in numbers if n >= 34])} numbers

💰 Cost: $28
💡 Strategy: 70% stability + 30% variation

<i>Good luck! 🍀</i>

/last - Check these numbers
/history - View past generations"""
        else:
            message = f"""🎯 <b>TOTO System 8 - Weekly Numbers</b>

🔢 Numbers: <code>{numbers_str}</code>
💰 Cost: $28

<i>Good luck! 🍀</i>"""
        
        return self.send_message(message.strip(), chat_id)
    
    def send_result_notification(self, result_data: Dict, chat_id: Optional[str] = None) -> bool:
        """Send result notification"""
        matches = result_data.get('matches', 0)
        prize_amount = result_data.get('prize_amount', 0)
        
        if prize_amount > 0:
            # Winning message
            message = f"""🎉 <b>CONGRATULATIONS! YOU WON!</b> 🎉

📊 <b>Result Update</b>

Draw #{result_data.get('draw_no', 'Unknown')}
Date: {result_data.get('draw_date', 'Unknown')}

Your Numbers: {result_data.get('numbers', [])}
Winning Numbers: {result_data.get('winning_numbers', [])}
Additional: {result_data.get('additional_number', 'N/A')}

━━━━━━━━━━━━━━━━━━
🎯 Matches: {matches} numbers
🏆 Prize Group: {result_data.get('prize_group', 'N/A')}
💰 Prize Amount: ${prize_amount:,}
━━━━━━━━━━━━━━━━━━

Check /roi for updated statistics!"""
        else:
            # Loss message
            message = f"""📊 <b>Result Update</b>

Draw #{result_data.get('draw_no', 'Unknown')}
Date: {result_data.get('draw_date', 'Unknown')}

Your Numbers: {result_data.get('numbers', [])}
Winning Numbers: {result_data.get('winning_numbers', [])}
Additional: {result_data.get('additional_number', 'N/A')}

━━━━━━━━━━━━━━━━━━
🎯 Matches: {matches} numbers
💔 No win this time
━━━━━━━━━━━━━━━━━━

Next draw: Numbers will be generated automatically!

Check /roi for updated statistics."""
        
        return self.send_message(message.strip(), chat_id)
    
    def send_history(self, history: List[Dict], chat_id: Optional[str] = None) -> bool:
        """Send generation history"""
        if not history:
            return self.send_message("No history available.", chat_id)
        
        message = "<b>📜 Last 5 Generations</b>\n\n"
        for i, entry in enumerate(history[:5], 1):
            date = entry.get('date', 'Unknown')[:10]
            numbers = ' '.join(map(str, entry.get('numbers', [])))
            draw_no = entry.get('draw_no', 'N/A')
            matches = entry.get('matches', 0)
            prize = entry.get('prize_amount', 0)
            
            if prize > 0:
                message += f"{i}. Draw #{draw_no} ({date}): <code>{numbers}</code>\n   🎉 Won ${prize:,} ({matches} matches)\n\n"
            else:
                message += f"{i}. Draw #{draw_no} ({date}): <code>{numbers}</code>\n   No win\n\n"
        
        message += "<i>/roi - View detailed returns</i>"
        return self.send_message(message, chat_id)