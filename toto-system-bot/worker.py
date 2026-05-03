import schedule
import time
import logging
from app.bot import TotoBot

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

bot = TotoBot()

def weekly_job():
    logger.info("Generating weekly numbers...")
    bot.generate_weekly_numbers()

def check_job():
    logger.info("Checking results...")
    bot.check_results()

schedule.every().friday.at("10:00").do(weekly_job)
schedule.every().saturday.at("20:00").do(check_job)

if __name__ == "__main__":
    logger.info("Worker started")
    if not bot.firebase.get_last_generation():
        weekly_job()
    
    while True:
        schedule.run_pending()
        time.sleep(60)
