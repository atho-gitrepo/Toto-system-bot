import schedule
import time
import logging
from datetime import datetime
from app.bot import TotoBot
from services.draw_manager import DrawManager
import pytz
import sys

# Setup logging
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
        """Generate numbers for the next upcoming draw"""
        try:
            logger.info("Checking if generation needed for next draw...")
            
            # Get current draw info
            draw_info = self.draw_manager.get_current_draw()
            
            # Check if we should generate
            if self.draw_manager.should_generate_numbers(draw_info):
                logger.info(f"Generating numbers for draw {draw_info['draw_no']}")
                
                # Check if numbers already generated for this draw
                existing = self.bot.firebase.get_generation_by_draw(str(draw_info['draw_no']))
                if existing:
                    logger.info(f"Numbers already generated for draw {draw_info['draw_no']}")
                    return
                
                # Generate new numbers
                result = self.bot.generate_weekly_numbers(draw_info)
                
                if result.get('saved'):
                    logger.info(f"✅ Numbers generated successfully for draw {draw_info['draw_no']}")
                    logger.info(f"Numbers: {result['numbers']}")
                else:
                    logger.error(f"❌ Failed to generate numbers: {result.get('error', 'Unknown error')}")
            else:
                logger.info(f"Not time to generate yet. Next draw in {draw_info.get('days_until', '?')} days")
                
        except Exception as e:
            logger.error(f"Error in generation job: {e}", exc_info=True)
    
    def check_pending_results(self):
        """Check results for pending draws"""
        try:
            logger.info("Checking for pending results...")
            
            # Get all pending generations
            pending = self.bot.firebase.get_pending_generations()
            
            if not pending:
                logger.info("No pending generations to check")
                return
            
            logger.info(f"Found {len(pending)} pending generation(s) to check")
            
            for generation in pending:
                draw_no = generation.get('draw_no')
                logger.info(f"Checking results for draw {draw_no}")
                
                # Check results
                result = self.bot.check_results_for_draw(draw_no)
                
                if result and result.get('checked'):
                    logger.info(f"✅ Results checked for draw {draw_no}")
                    logger.info(f"Matches: {result.get('matches', 0)}")
                    if result.get('prize_amount', 0) > 0:
                        logger.info(f"🎉 WIN! Prize: ${result['prize_amount']:,}")
                else:
                    logger.warning(f"Results not yet available for draw {draw_no}")
                    
        except Exception as e:
            logger.error(f"Error in result check job: {e}", exc_info=True)
    
    def auto_generation_job(self):
        """Automatic generation job (runs daily)"""
        logger.info("=== Running auto-generation check ===")
        self.generate_for_next_draw()
    
    def auto_result_check_job(self):
        """Automatic result check job (runs after draws)"""
        logger.info("=== Running auto-result check ===")
        self.check_pending_results()
    
    def health_check_job(self):
        """Health check and status report"""
        try:
            stats = self.bot.firebase.get_roi_stats()
            pending = len(self.bot.firebase.get_pending_generations())
            draw_info = self.draw_manager.get_current_draw()
            
            logger.info(f"Health Status - Games: {stats.get('games_played', 0)}, "
                       f"Pending: {pending}, "
                       f"Next Draw: {draw_info.get('draw_no')} in {draw_info.get('days_until', '?')} days")
        except Exception as e:
            logger.error(f"Health check error: {e}")
    
    def setup_schedules(self):
        """Setup all scheduled jobs"""
        
        # Run generation check every 6 hours (to ensure we don't miss)
        schedule.every(6).hours.do(self.auto_generation_job)
        
        # Run result check every hour (after draws)
        schedule.every(1).hours.do(self.auto_result_check_job)
        
        # Run health check every day at 9 AM
        schedule.every().day.at("09:00").do(self.health_check_job)
        
        # Specific times for better precision
        schedule.every().day.at("10:00").do(self.auto_generation_job)
        schedule.every().day.at("14:00").do(self.auto_generation_job)
        schedule.every().day.at("20:00").do(self.auto_result_check_job)
        schedule.every().day.at("21:00").do(self.auto_result_check_job)
        
        logger.info("Schedules configured:")
        logger.info("  - Generation check: Every 6 hours (10 AM, 4 PM, 10 PM)")
        logger.info("  - Result check: Every hour after draws")
        logger.info("  - Health check: Daily at 9 AM")
    
    def run_initial_setup(self):
        """Run initial setup checks"""
        logger.info("Running initial setup...")
        
        # Check if we need to generate for next draw
        draw_info = self.draw_manager.get_current_draw()
        
        # Check if any pending results need checking
        pending = self.bot.firebase.get_pending_generations()
        
        if pending:
            logger.info(f"Found {len(pending)} pending results to check")
            self.check_pending_results()
        
        # Generate numbers for next draw if needed
        if self.draw_manager.should_generate_numbers(draw_info):
            existing = self.bot.firebase.get_generation_by_draw(str(draw_info['draw_no']))
            if not existing:
                logger.info("No numbers found for next draw. Generating...")
                self.generate_for_next_draw()
            else:
                logger.info(f"Numbers already exist for draw {draw_info['draw_no']}")
        else:
            logger.info(f"Initial setup complete. Next draw in {draw_info.get('days_until', '?')} days")
    
    def run(self):
        """Run the worker continuously"""
        logger.info("=" * 50)
        logger.info("Starting Toto System 8 Automation Worker")
        logger.info("=" * 50)
        
        # Run initial setup
        self.run_initial_setup()
        
        # Setup schedules
        self.setup_schedules()
        
        logger.info("Worker is running. Waiting for scheduled jobs...")
        logger.info("Press Ctrl+C to stop")
        
        # Main loop
        while True:
            try:
                schedule.run_pending()
                time.sleep(60)  # Check every minute
            except KeyboardInterrupt:
                logger.info("\nWorker stopped by user")
                break
            except Exception as e:
                logger.error(f"Worker error: {e}", exc_info=True)
                time.sleep(60)

if __name__ == "__main__":
    worker = AutomationWorker()
    worker.run()
