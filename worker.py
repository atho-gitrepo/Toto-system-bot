import schedule
import time
import logging
from datetime import datetime, timedelta
from app.bot import TotoBot
from services.draw_manager import DrawManager
from services.result_service import ResultService
import pytz

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class AutomationWorker:
    def __init__(self):
        self.bot = TotoBot()
        self.draw_manager = DrawManager()
        self.result_service = ResultService()
        self.sg_tz = pytz.timezone('Asia/Singapore')
        logger.info("Automation Worker initialized")
    
    def generate_for_next_draw(self):
        """Generate numbers ONCE for the next upcoming draw"""
        try:
            logger.info("Checking if generation needed for next draw...")
            
            draw_info = self.draw_manager.get_current_draw()
            draw_no = str(draw_info['draw_no'])
            
            # Check if numbers already exist
            existing = self.bot.firebase.get_generation_by_draw(draw_no)
            
            if existing:
                logger.info(f"✅ Numbers already exist for draw {draw_no}")
                return
            
            # Generate if it's time
            if self.draw_manager.should_generate_numbers(draw_info):
                logger.info(f"🎯 Generating numbers for draw {draw_no}")
                
                result = self.bot.generate_weekly_numbers(draw_info)
                
                if result.get('saved'):
                    logger.info(f"✅ Numbers generated: {result['numbers']}")
                    
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

<i>Bot will automatically check results after draw!</i>"""
                    
                    telegram.send_message(message, config.TELEGRAM_CHAT_ID)
            else:
                days = draw_info.get('days_until', '?')
                logger.info(f"⏳ Generation in {days} days")
                
        except Exception as e:
            logger.error(f"Generation error: {e}", exc_info=True)
    
    def check_and_fetch_results(self):
        """Check for draws that need results fetched"""
        try:
            logger.info("Checking for draws needing results...")
            
            # Get all pending generations
            from services.firebase_service import FirebaseService
            from config import config
            
            firebase = FirebaseService(
                credentials_json=config.FIREBASE_CREDENTIALS_JSON,
                project_id=config.FIREBASE_PROJECT_ID
            )
            
            # Get all unchecked generations
            docs = firebase.db.collection('generations')\
                .where('checked', '==', False)\
                .stream()
            
            for doc in docs:
                generation = doc.to_dict()
                generation['id'] = doc.id
                draw_no = generation.get('draw_no')
                draw_date = generation.get('draw_date')
                
                if not draw_no or not draw_date:
                    continue
                
                # Check if draw has occurred
                try:
                    draw_datetime = datetime.strptime(f"{draw_date} 18:30", "%Y-%m-%d %H:%M")
                    draw_datetime = self.sg_tz.localize(draw_datetime)
                    now = datetime.now(self.sg_tz)
                    
                    # Only check if draw has passed + 2 hours
                    check_time = draw_datetime + timedelta(hours=2)
                    
                    if now >= check_time:
                        logger.info(f"Fetching results for Draw {draw_no}")
                        
                        # Try to fetch results
                        results = self.result_service.fetch_latest_results()
                        
                        if results and results.get('draw_no') == draw_no:
                            logger.info(f"✅ Results fetched for Draw {draw_no}")
                            logger.info(f"   Winning: {results['winning_numbers']} + {results['additional_number']}")
                            
                            # Check against user's numbers
                            from services.match_engine import MatchEngine
                            match_engine = MatchEngine()
                            match_result = match_engine.check_matches(
                                generation['numbers'],
                                results['winning_numbers']
                            )
                            
                            # Save results
                            result_data = {
                                'generation_id': generation['id'],
                                'draw_no': draw_no,
                                'numbers': generation['numbers'],
                                'winning_numbers': results['winning_numbers'],
                                'additional_number': results['additional_number'],
                                'matches': match_result['matches'],
                                'prize_group': match_result['prize_group'],
                                'prize_amount': match_result['prize_amount'],
                                'checked': True,
                                'fetched_at': datetime.now().isoformat()
                            }
                            
                            firebase.save_result(generation['id'], result_data)
                            
                            # Update ROI
                            from services.roi_service import ROIService
                            roi_service = ROIService(firebase)
                            roi_service.update_roi(match_result['prize_amount'])
                            
                            # Send notification
                            from services.telegram_service import TelegramService
                            telegram = TelegramService()
                            
                            if match_result['prize_amount'] > 0:
                                message = f"""🎉 <b>RESULT UPDATE - DRAW {draw_no}</b> 🎉

📅 Date: {draw_date}

Your Numbers: {generation['numbers']}
Winning Numbers: {results['winning_numbers']} + {results['additional_number']}

━━━━━━━━━━━━━━━━━━
🎯 <b>YOU WON!</b>
• Matches: {match_result['matches']} numbers
• Prize Group: {match_result['prize_group']}
• Prize Amount: ${match_result['prize_amount']:,}
━━━━━━━━━━━━━━━━━━

Check /roi for updated statistics!"""
                            else:
                                message = f"""📊 <b>RESULT UPDATE - DRAW {draw_no}</b>

📅 Date: {draw_date}

Your Numbers: {generation['numbers']}
Winning Numbers: {results['winning_numbers']} + {results['additional_number']}

━━━━━━━━━━━━━━━━━━
🎯 Matches: {match_result['matches']} numbers
💔 No win this time
━━━━━━━━━━━━━━━━━━

Next draw: Numbers will be generated automatically!"""
                            
                            telegram.send_message(message, config.TELEGRAM_CHAT_ID)
                            
                        else:
                            logger.warning(f"Results not yet available for Draw {draw_no}")
                    else:
                        # Wait time
                        wait_hours = (check_time - now).total_seconds() / 3600
                        if wait_hours < 24:  # Only log if within 24 hours
                            logger.info(f"Results for Draw {draw_no} available in {wait_hours:.1f} hours")
                except Exception as e:
                    logger.error(f"Error processing draw {draw_no}: {e}")
                    continue
            
        except Exception as e:
            logger.error(f"Result check error: {e}", exc_info=True)
    
    def setup_schedules(self):
        """Setup scheduled jobs"""
        
        # Run generation check daily at 10 AM
        schedule.every().day.at("10:00").do(self.generate_for_next_draw)
        
        # Run result checks every 2 hours after draws
        schedule.every(2).hours.do(self.check_and_fetch_results)
        
        # Health check daily
        schedule.every().day.at("09:00").do(self.health_check)
        
        logger.info("✅ Schedules configured:")
        logger.info("  - Generation: Daily at 10:00 AM")
        logger.info("  - Result checking: Every 2 hours")
        logger.info("  - Health check: Daily at 9:00 AM")
    
    def health_check(self):
        """Health check and status report"""
        try:
            from services.firebase_service import FirebaseService
            from config import config
            
            firebase = FirebaseService(
                credentials_json=config.FIREBASE_CREDENTIALS_JSON,
                project_id=config.FIREBASE_PROJECT_ID
            )
            
            stats = firebase.get_roi_stats()
            draw_info = self.draw_manager.get_current_draw()
            
            # Count pending checks
            pending = 0
            docs = firebase.db.collection('generations').where('checked', '==', False).stream()
            for _ in docs:
                pending += 1
            
            logger.info(f"💚 Health - Games: {stats.get('games_played', 0)}, "
                       f"ROI: {stats.get('roi', 0):.1f}%, "
                       f"Pending: {pending}, "
                       f"Next: Draw {draw_info.get('draw_no')} in {draw_info.get('days_until', '?')} days")
        except Exception as e:
            logger.error(f"Health check error: {e}")
    
    def run(self):
        """Run the worker continuously"""
        logger.info("=" * 50)
        logger.info("Starting Toto System 8 Automation Worker")
        logger.info("=" * 50)
        
        # Check for pending results on startup
        self.check_and_fetch_results()
        
        # Generate for next draw if needed
        self.generate_for_next_draw()
        
        # Setup schedules
        self.setup_schedules()
        
        logger.info("Worker running. Waiting for scheduled jobs...")
        
        while True:
            try:
                schedule.run_pending()
                time.sleep(60)
            except KeyboardInterrupt:
                logger.info("\nWorker stopped")
                break
            except Exception as e:
                logger.error(f"Worker error: {e}", exc_info=True)
                time.sleep(60)

if __name__ == "__main__":
    worker = AutomationWorker()
    worker.run()