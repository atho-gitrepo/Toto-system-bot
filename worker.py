import schedule
import time
import logging
from datetime import datetime
from app.bot import TotoBot
from services.draw_manager import DrawManager
import pytz
import sys

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class AutomationWorker:
    def __init__(self):
        self.bot = TotoBot()
        self.draw_manager = DrawManager()
        self.sg_tz = pytz.timezone('Asia/Singapore')
        logger.info("Automation Worker initialized")
    
    def generate_for_next_draw(self):
        """Generate numbers ONCE for the next upcoming draw"""
        try:
            logger.info("Checking if generation needed for next draw...")
            
            # Get current draw info
            draw_info = self.draw_manager.get_current_draw()
            draw_no = str(draw_info['draw_no'])
            
            # CRITICAL: Check if numbers already exist for this draw
            existing = self.bot.firebase.get_generation_by_draw(draw_no)
            
            if existing:
                logger.info(f"✅ Numbers already exist for draw {draw_no} - skipping generation")
                logger.info(f"   Existing numbers: {existing['numbers']}")
                return
            
            # Check if we should generate
            if self.draw_manager.should_generate_numbers(draw_info):
                logger.info(f"🎯 Generating numbers for draw {draw_no}")
                
                # Generate new numbers (this will save to Firebase)
                result = self.bot.generate_weekly_numbers(draw_info)
                
                if result.get('saved'):
                    logger.info(f"✅ Numbers generated successfully for draw {draw_no}")
                    logger.info(f"   Numbers: {result['numbers']}")
                    
                    # Send Telegram notification
                    from services.telegram_service import TelegramService
                    from config import config
                    telegram = TelegramService()
                    
                    message = f"""🎯 <b>NEW SYSTEM 8 NUMBERS GENERATED</b>

📅 Draw #{draw_no}
📆 Date: {draw_info['draw_date']} ({draw_info['draw_day']})
⏰ Time: 6:30 PM Singapore Time

🔢 Your Numbers: <code>{' '.join(map(str, result['numbers']))}</code>

💰 Cost: $28
💡 Strategy: 70% stability + 30% variation

<i>Good luck! Bot will automatically check results after draw.</i>"""
                    
                    telegram.send_message(message, config.TELEGRAM_CHAT_ID)
                else:
                    logger.error(f"❌ Failed to generate numbers: {result.get('error', 'Unknown error')}")
            else:
                days = draw_info.get('days_until', '?')
                logger.info(f"⏳ Not time to generate yet. Next draw in {days} days")
                
        except Exception as e:
            logger.error(f"Error in generation job: {e}", exc_info=True)
    
    def check_pending_results(self):
        """Check results for pending draws (ONCE per draw)"""
        try:
            logger.info("Checking for pending results...")
            
            # Get all generations that haven't been checked
            # Using a query for unchecked generations
            from services.firebase_service import FirebaseService
            from config import config
            
            firebase = FirebaseService(
                credentials_json=config.FIREBASE_CREDENTIALS_JSON,
                project_id=config.FIREBASE_PROJECT_ID
            )
            
            # Get all generations (we'll filter in code for simplicity)
            all_gens = firebase.db.collection('generations').where('checked', '==', False).stream()
            
            pending_count = 0
            for doc in all_gens:
                generation = doc.to_dict()
                generation['id'] = doc.id
                draw_no = generation.get('draw_no')
                
                if draw_no and not generation.get('checked', False):
                    pending_count += 1
                    logger.info(f"Checking results for draw {draw_no}")
                    
                    # Check if we should check results (draw has passed)
                    draw_date = generation.get('draw_date')
                    if draw_date:
                        draw_datetime = datetime.strptime(draw_date, '%Y-%m-%d')
                        draw_datetime = self.sg_tz.localize(draw_datetime.replace(hour=18, minute=30))
                        
                        # Only check if draw has passed + 2 hours
                        if datetime.now(self.sg_tz) > draw_datetime:
                            result = self.bot.check_results_for_draw(draw_no)
                            if result and result.get('checked'):
                                logger.info(f"✅ Results checked for draw {draw_no}")
                                logger.info(f"   Matches: {result.get('matches', 0)}")
                                if result.get('prize_amount', 0) > 0:
                                    logger.info(f"   🎉 WIN! Prize: ${result['prize_amount']:,}")
                            else:
                                logger.warning(f"Results not yet available for draw {draw_no}")
            
            if pending_count == 0:
                logger.info("No pending generations to check")
            
        except Exception as e:
            logger.error(f"Error in result check job: {e}", exc_info=True)
    
    def setup_schedules(self):
        """Setup scheduled jobs - less frequent to prevent duplicates"""
        
        # Run generation check once per day at 10 AM
        schedule.every().day.at("10:00").do(self.generate_for_next_draw)
        
        # Run result check twice per day after draws
        schedule.every().day.at("20:30").do(self.check_pending_results)
        schedule.every().day.at("21:00").do(self.check_pending_results)
        
        # Health check daily
        schedule.every().day.at("09:00").do(self.health_check)
        
        logger.info("✅ Schedules configured (duplicate prevention enabled):")
        logger.info("  - Generation check: Daily at 10:00 AM (once per day)")
        logger.info("  - Result check: After draws at 8:30 PM, 9:00 PM")
        logger.info("  - Health check: Daily at 9:00 AM")
    
    def health_check(self):
        """Health check and status report"""
        try:
            stats = self.bot.firebase.get_roi_stats()
            draw_info = self.draw_manager.get_current_draw()
            
            logger.info(f"💚 Health Check - Games: {stats.get('games_played', 0)}, "
                       f"ROI: {stats.get('roi', 0):.1f}%, "
                       f"Next Draw: {draw_info.get('draw_no')} in {draw_info.get('days_until', '?')} days")
        except Exception as e:
            logger.error(f"Health check error: {e}")
    
    def cleanup_duplicate_generations(self):
        """Clean up any existing duplicate generations for the same draw"""
        try:
            logger.info("Running duplicate cleanup...")
            
            from services.firebase_service import FirebaseService
            from config import config
            
            firebase = FirebaseService(
                credentials_json=config.FIREBASE_CREDENTIALS_JSON,
                project_id=config.FIREBASE_PROJECT_ID
            )
            
            # Get all generations
            docs = firebase.db.collection('generations').stream()
            
            draw_generations = {}
            
            for doc in docs:
                data = doc.to_dict()
                draw_no = data.get('draw_no')
                
                if draw_no:
                    if draw_no not in draw_generations:
                        draw_generations[draw_no] = []
                    draw_generations[draw_no].append({'id': doc.id, 'timestamp': data.get('timestamp')})
            
            # Keep only the most recent generation per draw
            total_deleted = 0
            for draw_no, gens in draw_generations.items():
                if len(gens) > 1:
                    # Sort by timestamp (most recent first)
                    gens.sort(key=lambda x: x.get('timestamp', datetime.min), reverse=True)
                    
                    # Keep the first, delete the rest
                    to_keep = gens[0]
                    to_delete = gens[1:]
                    
                    logger.info(f"Draw {draw_no}: Found {len(gens)} generations. Keeping 1, deleting {len(to_delete)}")
                    
                    for gen in to_delete:
                        firebase.db.collection('generations').document(gen['id']).delete()
                        total_deleted += 1
                        logger.info(f"  Deleted duplicate generation {gen['id']}")
            
            if total_deleted > 0:
                logger.info(f"✅ Cleanup complete! Deleted {total_deleted} duplicate generations")
            else:
                logger.info("✅ No duplicates found")
                
        except Exception as e:
            logger.error(f"Cleanup error: {e}")
    
    def run(self):
        """Run the worker continuously"""
        logger.info("=" * 50)
        logger.info("Starting Toto System 8 Automation Worker")
        logger.info("=" * 50)
        
        # Run cleanup first to remove duplicates
        self.cleanup_duplicate_generations()
        
        # Generate for next draw if needed (and no existing)
        self.generate_for_next_draw()
        
        # Setup schedules
        self.setup_schedules()
        
        logger.info("Worker is running. Waiting for scheduled jobs...")
        logger.info("Press Ctrl+C to stop")
        
        while True:
            try:
                schedule.run_pending()
                time.sleep(60)
            except KeyboardInterrupt:
                logger.info("\nWorker stopped by user")
                break
            except Exception as e:
                logger.error(f"Worker error: {e}", exc_info=True)
                time.sleep(60)

if __name__ == "__main__":
    worker = AutomationWorker()
    worker.run()