from typing import List, Dict
from config import config

class MatchEngine:
    @staticmethod
    def check_matches(user_numbers: List[int], winning_numbers: List[int]) -> Dict:
        if not user_numbers or not winning_numbers:
            return {'matches': 0, 'prize_group': None, 'prize_amount': 0}
        
        matches = len(set(user_numbers).intersection(set(winning_numbers)))
        prize_group = None
        prize_amount = 0
        
        if matches >= 3:
            prize_map = {6: 1, 5: 2, 4: 4, 3: 7}
            prize_group = prize_map.get(matches)
            prize_amount = config.PRIZE_TIERS.get(prize_group, 0) if prize_group else 0
        
        return {'matches': matches, 'prize_group': prize_group, 'prize_amount': prize_amount}
