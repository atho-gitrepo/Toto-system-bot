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
        """Generate System 8 numbers for specific draw (NO DUPLICATES)"""
        try:
            if not draw_info:
                from services.draw_manager import DrawManager
                draw_manager = DrawManager()
                draw_info = draw_manager.get_current_draw()
            
            draw_no = str(draw_info['draw_no'])
            
            # CRITICAL: Check if generation already exists for this draw
            existing = self.firebase.get_generation_by_draw(draw_no)
            if existing:
                logger.warning(f"Generation already exists for draw {draw_no}. Not generating duplicate.")
                return {
                    'numbers': existing['numbers'], 
                    'saved': True, 
                    'already_exists': True,
                    'id': existing['id']
                }
            
            # Generate new numbers
            prev_numbers = self.generator.get_previous_numbers()
            numbers = self.generator.generate_system8_numbers(prev_numbers)
            
            metadata = {
                'strategy': '70_30_balanced',
                'previous_numbers': prev_numbers,
                'generated_at': datetime.now().isoformat()
            }
            
            # Save with draw information
            doc_id = self.firebase.save_generation(numbers, {
                'draw_no': draw_no,
                'draw_date': draw_info['draw_date'],
                'draw_day': draw_info['draw_day'],
                **metadata
            })
            
            if doc_id:
                logger.info(f"✅ New numbers generated for draw {draw_no}")
                return {
                    'numbers': numbers, 
                    'saved': True, 
                    'id': doc_id, 
                    'draw_no': draw_no,
                    'draw_date': draw_info['draw_date']
                }
            
            return {'numbers': numbers, 'saved': False}
            
        except Exception as e:
            logger.error(f"Error generating numbers: {e}")
            return {'error': str(e)}
    
    def check_results_for_draw(self, draw_no: str) -> dict:
        """Check results for specific draw (ONCE per draw)"""
        try:
            # Get generation for this draw
            generation = self.firebase.get_generation_by_draw(draw_no)
            if not generation:
                logger.warning(f"No generation found for draw {draw_no}")
                return {'error': 'No generation found'}
            
            # Check if already checked
            if generation.get('checked', False):
                logger.info(f"Results already checked for draw {draw_no}")
                return {'error': 'Already checked', 'checked': True}
            
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
        """Get generation history (one per draw)"""
        return self.firebase.get_history(limit)
    
    def get_roi_summary(self) -> str:
        """Get ROI summary"""
        stats = self.firebase.get_roi_stats()
        return f"ROI: {stats.get('roi', 0):.2f}% | Net: ${stats.get('net_profit', 0):,}"
    
    def cleanup_draw_generations(self, draw_no: str) -> int:
        """Clean up all generations for a specific draw"""
        return self.firebase.delete_all_generations_for_draw(draw_no)