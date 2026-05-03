import requests
from typing import List, Dict
from config import config

class TelegramService:
    def __init__(self):
        self.token = config.TELEGRAM_TOKEN
        self.base_url = f"https://api.telegram.org/bot{self.token}"
        self.chat_id = config.TELEGRAM_CHAT_ID
    
    def send_message(self, text: str) -> bool:
        if not self.chat_id:
            return False
        try:
            response = requests.post(f"{self.base_url}/sendMessage", json={
                'chat_id': self.chat_id,
                'text': text,
                'parse_mode': 'HTML'
            }, timeout=10)
            return response.status_code == 200
        except Exception as e:
            print(f"Error: {e}")
            return False
    
    def send_numbers(self, numbers: List[int]) -> bool:
        numbers_str = ' '.join(map(str, numbers))
        message = f"🎯 TOTO System 8\n🔢 Numbers: <code>{numbers_str}</code>\n💰 Cost: $28\nGood luck! 🍀"
        return self.send_message(message)
    
    def send_result_notification(self, result_data: Dict) -> bool:
        message = f"📊 Result Update\n🎟️ Numbers: {result_data.get('numbers', [])}\n✅ Winning: {result_data.get('winning_numbers', [])}\n🎯 Matches: {result_data.get('matches', 0)}\n🏆 Prize: ${result_data.get('prize_amount', 0):,}"
        return self.send_message(message)
    
    def send_history(self, history: List[Dict]) -> bool:
        if not history:
            return self.send_message("No history available.")
        message = "<b>📜 Last 5 Generations</b>\n\n"
        for i, entry in enumerate(history[:5], 1):
            date = entry.get('date', 'Unknown')[:10]
            numbers = ' '.join(map(str, entry.get('numbers', [])))
            message += f"{i}. {date}: <code>{numbers}</code>\n"
        return self.send_message(message)
