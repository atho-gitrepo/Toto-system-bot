from datetime import datetime, timedelta
from typing import Dict, List, Optional
import pytz
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DrawManager:
    def __init__(self):
        self.sg_tz = pytz.timezone('Asia/Singapore')
        self.draw_days = ['Monday', 'Thursday']
        self.draw_time = "18:30"
        
        # Known draws with dates
        self.draws = {
            '4180': {'date': '2026-05-04', 'day': 'Monday', 'status': 'completed'},
            '4181': {'date': '2026-05-11', 'day': 'Monday', 'status': 'upcoming'},
            '4182': {'date': '2026-05-14', 'day': 'Thursday', 'status': 'upcoming'},
            '4183': {'date': '2026-05-18', 'day': 'Monday', 'status': 'upcoming'},
            '4184': {'date': '2026-05-21', 'day': 'Thursday', 'status': 'upcoming'},
            '4185': {'date': '2026-05-25', 'day': 'Monday', 'status': 'upcoming'},
            '4186': {'date': '2026-05-28', 'day': 'Thursday', 'status': 'upcoming'},
        }
    
    def get_current_draw(self) -> Dict:
        """Get current or upcoming draw"""
        now = datetime.now(self.sg_tz)
        today = now.date()
        
        for draw_no, draw_info in self.draws.items():
            draw_date = datetime.strptime(draw_info['date'], '%Y-%m-%d').date()
            
            if draw_date >= today:
                days_until = (draw_date - today).days
                
                # Check if draw is today and hasn't happened yet
                is_today = (draw_date == today)
                has_occurred = False
                
                if is_today:
                    draw_datetime = datetime.combine(draw_date, datetime.strptime(self.draw_time, '%H:%M').time())
                    draw_datetime = self.sg_tz.localize(draw_datetime)
                    has_occurred = now > draw_datetime
                
                return {
                    'draw_no': draw_no,
                    'draw_date': draw_info['date'],
                    'draw_day': draw_info['day'],
                    'draw_time': self.draw_time,
                    'status': 'completed' if has_occurred else draw_info['status'],
                    'days_until': days_until,
                    'has_occurred': has_occurred
                }
        
        # If no upcoming draw found, generate next one
        return self._generate_next_draw()
    
    def _generate_next_draw(self) -> Dict:
        """Generate next draw information"""
        now = datetime.now(self.sg_tz)
        next_draw_no = max(int(k) for k in self.draws.keys()) + 1
        
        # Find next draw day
        for i in range(1, 8):
            next_date = now + timedelta(days=i)
            if next_date.strftime('%A') in self.draw_days:
                return {
                    'draw_no': str(next_draw_no),
                    'draw_date': next_date.strftime('%Y-%m-%d'),
                    'draw_day': next_date.strftime('%A'),
                    'draw_time': self.draw_time,
                    'status': 'upcoming',
                    'days_until': i,
                    'has_occurred': False
                }
        
        return {
            'draw_no': str(next_draw_no),
            'draw_date': (now + timedelta(days=3)).strftime('%Y-%m-%d'),
            'draw_day': 'Thursday',
            'draw_time': self.draw_time,
            'status': 'upcoming',
            'days_until': 3,
            'has_occurred': False
        }
    
    def should_generate_numbers(self, draw_info: Dict) -> bool:
        """Determine if we should generate numbers for this draw"""
        # Generate 2 days before draw, but only once
        if draw_info.get('days_until', 999) == 2:
            logger.info(f"Should generate numbers for draw {draw_info['draw_no']}")
            return True
        return False
    
    def should_check_results(self, draw_info: Dict) -> bool:
        """Determine if we should check results after draw"""
        if draw_info.get('has_occurred', False):
            # Check if results are available (2 hours after draw time)
            now = datetime.now(self.sg_tz)
            draw_date = datetime.strptime(draw_info['draw_date'], '%Y-%m-%d')
            draw_datetime = self.sg_tz.localize(draw_date.replace(hour=18, minute=30))
            results_time = draw_datetime + timedelta(hours=2)
            
            if now >= results_time:
                logger.info(f"Should check results for draw {draw_info['draw_no']}")
                return True
        
        return False
    
    def get_next_draw_info(self) -> Dict:
        """Get next draw information for display"""
        draw_info = self.get_current_draw()
        
        return {
            'draw_no': draw_info['draw_no'],
            'draw_date': draw_info['draw_date'],
            'draw_day': draw_info['draw_day'],
            'draw_time': draw_info['draw_time'],
            'days_until': draw_info['days_until'],
            'generation_date': self._get_generation_date(draw_info['draw_date']),
            'check_date': self._get_check_date(draw_info['draw_date'])
        }
    
    def _get_generation_date(self, draw_date: str) -> str:
        """Calculate when numbers should be generated"""
        draw_datetime = datetime.strptime(draw_date, '%Y-%m-%d')
        gen_datetime = draw_datetime - timedelta(days=2)
        return gen_datetime.strftime('%Y-%m-%d')
    
    def _get_check_date(self, draw_date: str) -> str:
        """Calculate when results should be checked"""
        draw_datetime = datetime.strptime(draw_date, '%Y-%m-%d')
        return draw_datetime.strftime('%Y-%m-%d')
    
    def mark_draw_completed(self, draw_no: str, results: Dict):
        """Mark a draw as completed and store results"""
        if draw_no in self.draws:
            self.draws[draw_no]['status'] = 'completed'
            self.draws[draw_no]['results'] = results
            logger.info(f"Draw {draw_no} marked as completed")