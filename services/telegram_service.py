import requests
from typing import List, Dict, Optional
from config import config
import logging

logger = logging.getLogger(__name__)

class TelegramService:
    def __init__(self):
        self.token = config.TELEGRAM_TOKEN
        self.base_url = f"https://api.telegram.org/bot{self.token}"
        self.default_chat_id = config.TELEGRAM_CHAT_ID
    
    def send_message(self, text: str, chat_id: str = None) -> bool:
        """Send a message to Telegram"""
        target_chat = chat_id or self.default_chat_id
        if not target_chat:
            logger.error("No chat_id provided")
            return False
        
        try:
            url = f"{self.base_url}/sendMessage"
            payload = {
                'chat_id': target_chat,
                'text': text,
                'parse_mode': 'HTML'
            }
            response = requests.post(url, json=payload, timeout=10)
            logger.info(f"Telegram response: {response.status_code}")
            if response.status_code != 200:
                logger.error(f"Telegram error: {response.text}")
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Error sending Telegram message: {e}")
            return False
    
    def send_numbers(self, numbers: List[int], chat_id: str = None) -> bool:
        """Format and send generated numbers"""
        numbers_str = ' '.join(map(str, numbers))
        message = f"""
🎯 <b>TOTO System 8 - Weekly Numbers</b>

🔢 Numbers: <code>{numbers_str}</code>
💰 Cost: $28

Good luck! 🍀
        """
        return self.send_message(message.strip(), chat_id)
    
    def send_result_notification(self, result_data: Dict, chat_id: str = None) -> bool:
        """Send result notification"""
        message = f"""
📊 <b>Result Update</b>

🎟️ Your Numbers: {result_data.get('numbers', [])}
✅ Winning Numbers: {result_data.get('winning_numbers', [])}
🎯 Matches: {result_data.get('matches', 0)}
🏆 Prize Group: {result_data.get('prize_group', 'None')}
💰 Prize Amount: ${result_data.get('prize_amount', 0):,}
        """
        return self.send_message(message.strip(), chat_id)
    
    def send_history(self, history: List[Dict], chat_id: str = None) -> bool:
        """Send generation history"""
        if not history:
            return self.send_message("No history available.", chat_id)
        
        message = "<b>📜 Last 5 Generations</b>\n\n"
        for i, entry in enumerate(history[:5], 1):
            date = entry.get('date', 'Unknown')[:10]
            numbers = ' '.join(map(str, entry.get('numbers', [])))
            message += f"{i}. {date}: <code>{numbers}</code>\n"
        
        return self.send_message(message, chat_id)