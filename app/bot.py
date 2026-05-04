from services import NumberGenerator, FirebaseService, TelegramService, ResultChecker, ROIService
from config import config
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TotoBot:
    def __init__(self):
        self.firebase = FirebaseService(
            credentials_json=config.FIREBASE_CREDENTIALS_JSON,
            project_id=config.FIREBASE_PROJECT_ID
        )
        self.generator = NumberGenerator(self.firebase)
        self.telegram = TelegramService()
        self.result_checker = ResultChecker()
        self.roi_service = ROIService(self.firebase)
    
    def generate_weekly_numbers(self, draw_info: dict = None) -> dict:
        """Generate System 8 numbers for specific draw"""
        try:
            if not draw_info:
                from services.draw_manager import DrawManager
                draw_manager = DrawManager()
                draw_info = draw_manager.get_current_draw()
            
            prev_numbers = self.generator.get_previous_numbers()
            numbers = self.generator.generate_system8_numbers(prev_numbers)
            
            metadata = {
                'strategy': '70_30_balanced',
                'previous_numbers': prev_numbers,
                'generated_at': datetime.now().isoformat()
            }
            
            # Save with draw information
            doc_id = self.firebase.save_generation(numbers, {
                'draw_no': draw_info['draw_no'],
                'draw_date': draw_info['draw_date'],
                **metadata
            })
            
            if doc_id:
                # Send to Telegram
                self.telegram.send_numbers(numbers, draw_info)
                logger.info(f"Numbers generated for draw {draw_info['draw_no']}")
                return {
                    'numbers': numbers, 
                    'saved': True, 
                    'id': doc_id, 
                    'draw_no': draw_info['draw_no'],
                    'draw_date': draw_info['draw_date']
                }
            
            return {'numbers': numbers, 'saved': False}
            
        except Exception as e:
            logger.error(f"Error generating numbers: {e}")
            return {'error': str(e)}
    
    def check_results_for_draw(self, draw_no: str) -> dict:
        """Check results for specific draw"""
        try:
            # Get generation for this draw
            generation = self.firebase.get_generation_by_draw(draw_no)
            if not generation:
                logger.warning(f"No generation found for draw {draw_no}")
                return {'error': 'No generation found'}
            
            # Get draw results
            draw_result = self.firebase.get_draw_result(draw_no)
            if not draw_result:
                logger.warning(f"No draw results available for {draw_no}")
                return {'error': 'Results not available yet'}
            
            # Check matches
            match_result = self.result_checker.check_matches(
                generation['numbers'], 
                draw_result['winning_numbers']
            )
            
            result_data = {
                'generation_id': generation['id'],
                'draw_no': draw_no,
                'numbers': generation['numbers'],
                'winning_numbers': draw_result['winning_numbers'],
                'additional_number': draw_result.get('additional_number'),
                'matches': match_result['matches'],
                'prize_group': match_result['prize_group'],
                'prize_amount': match_result['prize_amount'],
                'checked': True
            }
            
            # Save result
            self.firebase.save_result(generation['id'], result_data)
            
            # Update ROI
            self.roi_service.update_roi(match_result['prize_amount'])
            
            # Send notification
            self.telegram.send_result_notification(result_data)
            
            return result_data
            
        except Exception as e:
            logger.error(f"Error checking results for draw {draw_no}: {e}")
            return {'error': str(e), 'checked': False}
    
    def get_history(self, limit: int = 5) -> list:
        """Get generation history"""
        return self.firebase.get_history(limit)
    
    def get_roi_summary(self) -> str:
        """Get ROI summary"""
        stats = self.firebase.get_roi_stats()
        return f"ROI: {stats.get('roi', 0):.2f}% | Net: ${stats.get('net_profit', 0):,}"
    
    def get_draw_status(self) -> dict:
        """Get current draw status"""
        from services.draw_manager import DrawManager
        draw_manager = DrawManager()
        return draw_manager.get_next_draw_info()
    
    def manual_trigger_generation(self) -> dict:
        """Manual trigger for generation"""
        from services.draw_manager import DrawManager
        draw_manager = DrawManager()
        draw_info = draw_manager.get_current_draw()
        return self.generate_weekly_numbers(draw_info)
    
    def manual_trigger_result_check(self, draw_no: str = None) -> dict:
        """Manual trigger for result checking"""
        if draw_no:
            return self.check_results_for_draw(draw_no)
        else:
            from services.draw_manager import DrawManager
            draw_manager = DrawManager()
            draw_info = draw_manager.get_current_draw()
            return self.check_results_for_draw(str(draw_info['draw_no']))
