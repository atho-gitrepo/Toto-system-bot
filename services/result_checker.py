from typing import Dict, Optional
from .result_service import ResultService
from .match_engine import MatchEngine
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ResultChecker:
    def __init__(self):
        self.result_service = ResultService()
        self.match_engine = MatchEngine()
    
    def check_generation(self, generation_data: Dict) -> Optional[Dict]:
        """Check a specific generation against draw results"""
        try:
            numbers = generation_data.get('numbers')
            draw_no = generation_data.get('draw_no')
            
            if not numbers:
                logger.error("No numbers in generation")
                return None
            
            # Get draw results
            draw_result = self.result_service.get_draw_result(draw_no) if draw_no else self.result_service.fetch_latest_results()
            
            if not draw_result:
                logger.warning(f"No draw results available for draw {draw_no}")
                return None
            
            winning_numbers = draw_result.get('winning_numbers', [])
            if not winning_numbers:
                logger.warning("No winning numbers in draw result")
                return None
            
            # Check matches
            match_result = self.match_engine.check_matches(numbers, winning_numbers)
            
            return {
                'generation_id': generation_data.get('id'),
                'draw_no': draw_no or draw_result.get('draw_no'),
                'draw_date': draw_result.get('draw_date'),
                'numbers': numbers,
                'winning_numbers': winning_numbers,
                'additional_number': draw_result.get('additional_number', 0),
                'matches': match_result['matches'],
                'prize_group': match_result['prize_group'],
                'prize_amount': match_result['prize_amount']
            }
            
        except Exception as e:
            logger.error(f"Error checking generation: {e}")
            return None