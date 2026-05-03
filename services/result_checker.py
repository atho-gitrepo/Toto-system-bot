from typing import Dict, Optional
from .result_service import ResultService
from .match_engine import MatchEngine

class ResultChecker:
    def __init__(self):
        self.result_service = ResultService()
        self.match_engine = MatchEngine()
    
    def check_generation(self, generation_data: Dict) -> Optional[Dict]:
        numbers = generation_data.get('numbers')
        if not numbers:
            return None
        
        winning_data = self.result_service.fetch_latest_results()
        if not winning_data:
            return None
        
        match_result = self.match_engine.check_matches(numbers, winning_data.get('winning_numbers', []))
        
        return {
            'generation_id': generation_data.get('id'),
            'numbers': numbers,
            'winning_numbers': winning_data.get('winning_numbers', []),
            'draw_date': winning_data.get('draw_date'),
            'matches': match_result['matches'],
            'prize_group': match_result['prize_group'],
            'prize_amount': match_result['prize_amount']
        }
