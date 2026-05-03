import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Telegram
    TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
    TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
    
    # Firebase (Cloud Firestore - no URL needed)
    FIREBASE_CREDENTIALS_JSON = os.getenv('FIREBASE_CREDENTIALS_JSON')
    # Optional: For Firebase projects with specific config
    FIREBASE_PROJECT_ID = os.getenv('FIREBASE_PROJECT_ID')
    
    # System Settings
    LOTTO_MAX_NUMBER = 49
    SYSTEM_SIZE = 8
    MIN_NUMBER = 1
    GENERATION_WEEKDAY = int(os.getenv('GENERATION_WEEKDAY', 5))  # Friday
    GENERATION_HOUR = int(os.getenv('GENERATION_HOUR', 10))
    RESULT_CHECK_HOUR = int(os.getenv('RESULT_CHECK_HOUR', 20))
    RESULT_CHECK_DAY = int(os.getenv('RESULT_CHECK_DAY', 6))  # Saturday
    TICKET_PRICE = 28
    
    PRIZE_TIERS = {
        1: 1000000,  # Group 1: Jackpot
        2: 500000,   # Group 2: $500k
        3: 50000,    # Group 3: $50k
        4: 2000,     # Group 4: $2k
        5: 250,      # Group 5: $250
        6: 50,       # Group 6: $50
        7: 25        # Group 7: $25
    }

config = Config()