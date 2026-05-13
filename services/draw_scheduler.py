from datetime import datetime, timedelta
from typing import Dict, Optional
import pytz
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DrawScheduler:
    def __init__(self):
        self.sg_tz = pytz.timezone('Asia/Singapore')
        self.draw_days = ['Monday', 'Thursday']
        self.draw_time = "18:30"
        
        # Track draws from 4180 onwards
        self.start_draw = 4180
        self.start_date = datetime(2026, 5, 7)
        
        # Known draws database
        self.draws = {
            4179: {
                'draw_no': 4179,
                'draw_date': '2026-05-04',
                'draw_day': 'Monday',
                'draw_time': '18:30',
                'status': 'completed',
                'winning_numbers': [7, 18, 19, 30, 36, 48],
                'additional_number': 11
            },
            4180: {
                'draw_no': 4180,
                'draw_date': '2026-05-07',
                'draw_day': 'Thursday',
                'draw_time': '18:30',
                'status': 'completed',
                'winning_numbers': None,
                'additional_number': None
            },
            4181: {
                'draw_no': 4181,
                'draw_date': '2026-05-11',
                'draw_day': 'Monday',
                'draw_time': '18:30',
                'status': 'completed',
                'winning_numbers': None,
                'additional_number': None
            },
            4182: {
                'draw_no': 4182,
                'draw_date': '2026-05-14',
                'draw_day': 'Thursday',
                'draw_time': '18:30',
                'status': 'upcoming',
                'winning_numbers': None,
                'additional_number': None
            },
            4183: {
                'draw_no': 4183,
                'draw_date': '2026-05-18',
                'draw_day': 'Monday',
                'draw_time': '18:30',
                'status': 'upcoming',
                'winning_numbers': None,
                'additional_number': None
            },
            4184: {
                'draw_no': 4184,
                'draw_date': '2026-05-21',
                'draw_day': 'Thursday',
                'draw_time': '18:30',
                'status': 'upcoming',
                'winning_numbers': None,
                'additional_number': None
            }
        }
    
    def get_current_draw(self) -> Dict:
        """Get the current or most recent draw"""
        now = datetime.now(self.sg_tz)
        today = now.date()
        
        # Find the current draw based on date
        for draw_no, draw_info in sorted(self.draws.items(), reverse=True):
            draw_date = datetime.strptime(draw_info['draw_date'], '%Y-%m-%d').date()
            
            if draw_date <= today:
                # Check if draw has passed
                if draw_date < today:
                    return draw_info
                elif draw_date == today and now.time().hour >= 18:
                    return draw_info
                else:
                    # Today's draw not yet happened
                    return draw_info
        
        # Return next draw if no current found
        return self.get_next_draw()
    
    def get_next_draw(self) -> Dict:
        """Get the next upcoming draw"""
        now = datetime.now(self.sg_tz)
        today = now.date()
        
        # Find next upcoming draw
        for draw_no, draw_info in self.draws.items():
            draw_date = datetime.strptime(draw_info['draw_date'], '%Y-%m-%d').date()
            
            if draw_date > today:
                days_until = (draw_date - today).days
                return {
                    'draw_no': draw_info['draw_no'],
                    'draw_date': draw_info['draw_date'],
                    'draw_day': draw_info['draw_day'],
                    'draw_time': draw_info['draw_time'],
                    'status': draw_info['status'],
                    'days_until': days_until,
                    'timestamp': datetime.strptime(f"{draw_info['draw_date']} {draw_info['draw_time']}", '%Y-%m-%d %H:%M')
                }
            elif draw_date == today and now.time().hour < 18:
                # Today's draw hasn't happened yet
                return {
                    'draw_no': draw_info['draw_no'],
                    'draw_date': draw_info['draw_date'],
                    'draw_day': draw_info['draw_day'],
                    'draw_time': draw_info['draw_time'],
                    'status': 'today',
                    'days_until': 0,
                    'timestamp': datetime.strptime(f"{draw_info['draw_date']} {draw_info['draw_time']}", '%Y-%m-%d %H:%M')
                }
        
        # Generate next draw dynamically
        last_draw = max(self.draws.keys())
        last_draw_info = self.draws[last_draw]
        last_date = datetime.strptime(last_draw_info['draw_date'], '%Y-%m-%d')
        
        # Calculate next draw date (add 3 or 4 days based on day of week)
        if last_draw_info['draw_day'] == 'Monday':
            next_date = last_date + timedelta(days=3)  # Thursday
            next_day = 'Thursday'
        else:
            next_date = last_date + timedelta(days=4)  # Monday
            next_day = 'Monday'
        
        next_draw_no = last_draw + 1
        days_until = (next_date.date() - datetime.now(self.sg_tz).date()).days
        
        return {
            'draw_no': next_draw_no,
            'draw_date': next_date.strftime('%Y-%m-%d'),
            'draw_day': next_day,
            'draw_time': '18:30',
            'status': 'upcoming',
            'days_until': max(0, days_until),
            'timestamp': next_date.replace(hour=18, minute=30)
        }
    
    def get_next_draw_info(self) -> Dict:
        """Get detailed next draw information"""
        return self.get_next_draw()
    
    def should_check_results(self, draw_no: int) -> bool:
        """Determine if we should check results for a draw"""
        if draw_no not in self.draws:
            return False
        
        draw_info = self.draws[draw_no]
        draw_date = datetime.strptime(draw_info['draw_date'], '%Y-%m-%d')
        draw_datetime = self.sg_tz.localize(draw_date.replace(hour=18, minute=30))
        now = datetime.now(self.sg_tz)
        
        # Check results 2 hours after draw (at 8:30 PM)
        check_time = draw_datetime + timedelta(hours=2)
        
        return now >= check_time
    
    def get_draw_by_number(self, draw_no: int) -> Optional[Dict]:
        """Get draw information by draw number"""
        if draw_no in self.draws:
            draw_info = self.draws[draw_no]
            draw_date = datetime.strptime(draw_info['draw_date'], '%Y-%m-%d')
            return {
                'draw_no': draw_info['draw_no'],
                'draw_date': draw_info['draw_date'],
                'draw_day': draw_info['draw_day'],
                'draw_time': draw_info['draw_time'],
                'timestamp': draw_date.replace(hour=18, minute=30)
            }
        return None
    
    def update_draw_result(self, draw_no: int, winning_numbers: list, additional_number: int):
        """Update draw results after checking"""
        if draw_no in self.draws:
            self.draws[draw_no]['winning_numbers'] = winning_numbers
            self.draws[draw_no]['additional_number'] = additional_number
            self.draws[draw_no]['status'] = 'completed'
            logger.info(f"Updated draw {draw_no} with results: {winning_numbers} + {additional_number}")