import schedule
import time
import logging
from datetime import datetime
from app.bot import TotoBot
from services.draw_scheduler import DrawScheduler
import pytz

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class AutomationWorker:
    def __init__(self):
        self.bot = TotoBot()
        self.scheduler = DrawScheduler()
        self.sg_tz = pytz.timezone('Asia/Singapore')
        logger.info("Hybrid Automation Worker initialized")
    
    def auto_generate_numbers(self):
        """Generate numbers for upcoming draw"""
        try:
            next_draw = self.scheduler.get_next_draw()
            draw_no = str(next_draw['draw_no'])
            
            existing = self.bot.firebase.get_generation_by_draw(draw_no)
            if existing:
                logger.info(f"Numbers already exist for draw {draw_no}")
                return
            
            now = datetime.now(self.sg_tz)
            draw_date = datetime.strptime(next_draw['draw_date'], '%Y-%m-%d')
            days_until = (draw_date - now.date()).days
            
            if days_until <= 2 and days_until >= 0:
                logger.info(f"Generating numbers for draw {draw_no}")
                result = self.bot.generate_weekly_numbers(next_draw)
                
                if result.get('saved'):
                    logger.info(f"✅ Numbers generated: {result['numbers']}")
                    message = f"""🎯 <b>NEW SYSTEM 8 NUMBERS</b>

Draw #{draw_no}
Date: {next_draw['draw_date']} ({next_draw['draw_day']})

Numbers: <code>{' '.join(map(str, result['numbers']))}</code>

<i>Results will be checked automatically after draw.
If auto-fetch fails, use: /declare winning numbers</i>"""
                    self.bot.telegram.send_message(message)
                else:
                    logger.error(f"Generation failed: {result.get('error')}")
                    
        except Exception as e:
            logger.error(f"Auto-generation error: {e}", exc_info=True)
    
    def auto_check_results(self):
        """Check results using hybrid method"""
        try:
            current_draw = self.scheduler.get_current_draw()
            draw_no = str(current_draw['draw_no'])
            
            # Check if we should check results
            if not self.scheduler.should_check_results(int(draw_no)):
                logger.info(f"Not time to check results for draw {draw_no}")
                return
            
            generation = self.bot.firebase.get_generation_by_draw(draw_no)
            if not generation or generation.get('checked'):
                return
            
            # Try to fetch results automatically
            logger.info(f"Attempting to fetch results for draw {draw_no}...")
            draw_result = self.bot.result_service.get_draw_result(draw_no)
            
            if draw_result and draw_result.get('winning_numbers'):
                # Auto-fetch successful
                self._process_results(draw_no, generation, draw_result)
            else:
                # Auto-fetch failed - wait and notify
                logger.warning(f"Could not auto-fetch results for draw {draw_no}")
                message = f"""⚠️ <b>Results Not Auto-Fetched</b>

Draw #{draw_no} has completed, but automatic result retrieval failed.

Please manually declare results using:
/declare 7,18,19,30,36,48 + 11

(Replace with actual winning numbers)"""
                self.bot.telegram.send_message(message)
                
        except Exception as e:
            logger.error(f"Auto-result check error: {e}", exc_info=True)
    
    def _process_results(self, draw_no: str, generation: dict, draw_result: dict):
        """Process and save results"""
        from services.match_engine import MatchEngine
        engine = MatchEngine()
        
        match_result = engine.check_matches(
            generation['numbers'],
            draw_result['winning_numbers']
        )
        
        result_data = {
            'generation_id': generation['id'],
            'draw_no': draw_no,
            'numbers': generation['numbers'],
            'winning_numbers': draw_result['winning_numbers'],
            'additional_number': draw_result.get('additional_number', 0),
            'matches': match_result['matches'],
            'prize_group': match_result['prize_group'],
            'prize_amount': match_result['prize_amount']
        }
        
        self.bot.firebase.save_result(generation['id'], result_data)
        self.bot.roi_service.update_roi(match_result['prize_amount'])
        
        if match_result['prize_amount'] > 0:
            message = f"""🎉 <b>CONGRATULATIONS! YOU WON!</b> 🎉

Draw #{draw_no}
Your Numbers: {generation['numbers']}
Winning: {draw_result['winning_numbers']} + {draw_result.get('additional_number', 0)}

✅ Matches: {match_result['matches']}
💰 Prize: ${match_result['prize_amount']:,}

Check /roi for updated statistics!"""
        else:
            message = f"""📊 <b>Draw Result</b>

Draw #{draw_no}
Your Numbers: {generation['numbers']}
Winning: {draw_result['winning_numbers']} + {draw_result.get('additional_number', 0)}

Matches: {match_result['matches']}
No win this time.

Numbers for next draw will be generated automatically!"""
        
        self.bot.telegram.send_message(message)
        logger.info(f"✅ Results processed for draw {draw_no}")
    
    def health_check(self):
        """Health check"""
        try:
            next_draw = self.scheduler.get_next_draw()
            stats = self.bot.firebase.get_roi_stats()
            logger.info(f"💚 Health - Games: {stats.get('games_played', 0)}, "
                       f"ROI: {stats.get('roi', 0):.1f}%, "
                       f"Next: #{next_draw['draw_no']} on {next_draw['draw_date']}")
        except Exception as e:
            logger.error(f"Health check error: {e}")
    
    def setup_schedules(self):
        """Setup schedules"""
        schedule.every().day.at("08:00").do(self.auto_generate_numbers)
        schedule.every().day.at("12:00").do(self.auto_generate_numbers)
        schedule.every().day.at("16:00").do(self.auto_generate_numbers)
        
        schedule.every(2).hours.do(self.auto_check_results)
        schedule.every().day.at("20:30").do(self.auto_check_results)
        schedule.every().day.at("21:00").do(self.auto_check_results)
        
        schedule.every().day.at("09:00").do(self.health_check)
        
        logger.info("✅ Hybrid schedules configured")
        logger.info("  - Auto-fetch results from 3 sources")
        logger.info("  - Manual /declare command available as backup")
    
    def run(self):
        logger.info("=" * 60)
        logger.info("HYBRID TOTO SYSTEM 8 WORKER")
        logger.info("Auto-fetch + Manual fallback")
        logger.info("=" * 60)
        
        self.auto_generate_numbers()
        self.auto_check_results()
        self.setup_schedules()
        
        logger.info("Worker running. Bot will auto-fetch results.")
        logger.info("If auto-fetch fails, use /declare command.")
        
        while True:
            try:
                schedule.run_pending()
                time.sleep(60)
            except KeyboardInterrupt:
                logger.info("Worker stopped")
                break
            except Exception as e:
                logger.error(f"Worker error: {e}", exc_info=True)
                time.sleep(60)

if __name__ == "__main__":
    worker = AutomationWorker()
    worker.run()