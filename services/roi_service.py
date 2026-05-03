from typing import Dict
from config import config

class ROIService:
    def __init__(self, firebase_service):
        self.firebase = firebase_service
    
    def update_roi(self, prize_amount: int = 0) -> Dict:
        stats = self.firebase.get_roi_stats()
        stats['total_spent'] = stats.get('total_spent', 0) + config.TICKET_PRICE
        stats['total_return'] = stats.get('total_return', 0) + prize_amount
        stats['games_played'] = stats.get('games_played', 0) + 1
        
        if stats['total_spent'] > 0:
            stats['roi'] = ((stats['total_return'] - stats['total_spent']) / stats['total_spent']) * 100
        else:
            stats['roi'] = 0
        
        stats['net_profit'] = stats['total_return'] - stats['total_spent']
        self.firebase.update_roi_stats(stats)
        return stats
    
    def get_roi_report(self) -> str:
        stats = self.firebase.get_roi_stats()
        return f"📊 ROI Dashboard\nGames: {stats.get('games_played', 0)}\nSpent: ${stats.get('total_spent', 0):,}\nReturns: ${stats.get('total_return', 0):,}\nROI: {stats.get('roi', 0):.2f}%"
