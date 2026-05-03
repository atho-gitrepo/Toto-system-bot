import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
    TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
    FIREBASE_CREDENTIALS_JSON = os.getenv('FIREBASE_CREDENTIALS_JSON')
    FIREBASE_DB_URL = os.getenv('FIREBASE_DB_URL')
    
    LOTTO_MAX_NUMBER = 49
    SYSTEM_SIZE = 8
    MIN_NUMBER = 1
    GENERATION_WEEKDAY = int(os.getenv('GENERATION_WEEKDAY', 5))
    GENERATION_HOUR = int(os.getenv('GENERATION_HOUR', 10))
    RESULT_CHECK_HOUR = int(os.getenv('RESULT_CHECK_HOUR', 20))
    RESULT_CHECK_DAY = int(os.getenv('RESULT_CHECK_DAY', 6))
    TICKET_PRICE = 28
    
    PRIZE_TIERS = {
        1: 1000000, 2: 500000, 3: 50000,
        4: 2000, 5: 250, 6: 50, 7: 25
    }

config = Config()
