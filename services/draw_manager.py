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
        self.draw_times_sg = datetime.strptime(self.draw_time, '%H:%M').time()
        
        # Track draws
        self.current_draw_no = 4180
        self.draws = self._initialize_draws()
    
    def _initialize_draws(self) -> Dict:
        """Initialize draw schedule"""
        return {
            4180: {
                'date': '2026-05-07',
                'day': 'Thursday',
                'time': '18:30',
                'status': 'upcoming'
            },
            4181: {
                'date': '2026-05-11',
                'day': 'Monday',
                'time': '18:30',
                'status': 'upcoming'
            },
            4182: {
                'date': '2026-05-14',
                'day': 'Thursday',
                'time': '18:30',
                'status': 'upcoming'
            },
            4183: {
                'date': '2026-05-18',
                'day': 'Monday',
                'time': '18:30',
                'status': 'upcoming'
            },
            4184: {
                'date': '2026-05-21',
                'day': 'Thursday',
                'time': '18:30',
                'status': 'upcoming'
            }
        }
    
    def get_current_draw(self) -> Dict:
        """Get current/upcoming draw information"""
        now = datetime.now(self.sg_tz)
        today = now.date()
        current_time = now.time()
        
        # Find next draw
        for draw_no, draw_info in self.draws.items():
            draw_date = datetime.strptime(draw_info['date'], '%Y-%m-%d').date()
            
            if draw_date > today:
                return {
                    'draw_no': draw_no,
                    'draw_date': draw_info['date'],
                    'draw_day': draw_info['day'],
                    'draw_time': draw_info['time'],
                    'status': 'upcoming',
                    'days_until': (draw_date - today).days
                }
            elif draw_date == today and current_time < self.draw_times_sg:
                return {
                    'draw_no': draw_no,
                    'draw_date': draw_info['date'],
                    'draw_day': draw_info['day'],
                    'draw_time': draw_info['time'],
                    'status': 'today',
                    'days_until': 0
                }
        
        # If no upcoming draw found, generate next one
        return self._generate_next_draw()
    
    def _generate_next_draw(self) -> Dict:
        """Generate next draw information"""
        now = datetime.now(self.sg_tz)
        next_draw_no = self.current_draw_no + len(self.draws)
        
        # Find next draw day
        days_ahead = 0
        for i in range(1, 8):
            next_date = now + timedelta(days=i)
            if next_date.strftime('%A') in self.draw_days:
                days_ahead = i
                break
        
        next_date = now + timedelta(days=days_ahead)
        
        return {
            'draw_no': next_draw_no,
            'draw_date': next_date.strftime('%Y-%m-%d'),
            'draw_day': next_date.strftime('%A'),
            'draw_time': self.draw_time,
            'status': 'upcoming',
            'days_until': days_ahead
        }
    
    def should_generate_numbers(self, draw_info: Dict) -> bool:
        """Determine if we should generate numbers for this draw"""
        if draw_info.get('days_until', 999) <= 2:
            logger.info(f"Should generate numbers for draw {draw_info['draw_no']} (in {draw_info['days_until']} days)")
            return True
        return False
    
    def should_check_results(self, draw_info: Dict) -> bool:
        """Determine if we should check results after draw"""
        if draw_info.get('status') == 'today':
            now = datetime.now(self.sg_tz)
            draw_datetime = datetime.strptime(
                f"{draw_info['draw_date']} {draw_info['draw_time']}", 
                '%Y-%m-%d %H:%M'
            )
            draw_datetime = self.sg_tz.localize(draw_datetime)
            
            # Check results 2 hours after draw (at 8:30 PM)
            check_time = draw_datetime + timedelta(hours=2)
            if now >= check_time:
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
    
    def get_draw_history(self, limit: int = 10) -> List[Dict]:
        """Get recent draw history"""
        history = []
        now = datetime.now(self.sg_tz)
        
        for draw_no, draw_info in sorted(self.draws.items(), reverse=True)[:limit]:
            draw_date = datetime.strptime(draw_info['date'], '%Y-%m-%d')
            is_past = draw_date < now
            
            history.append({
                'draw_no': draw_no,
                'draw_date': draw_info['date'],
                'draw_day': draw_info['day'],
                'status': 'completed' if is_past else 'upcoming',
                'result_available': is_past
            })
        
        return history
