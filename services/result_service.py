import requests
from bs4 import BeautifulSoup
from typing import List, Dict, Optional
from datetime import datetime
import re
import time
import logging
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ResultService:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
        })
        
    def fetch_latest_results(self) -> Optional[Dict]:
        """Fetch latest Toto results from Singapore Pools"""
        try:
            # Try multiple sources
            results = self._fetch_from_official()
            if results:
                return results
            
            results = self._fetch_from_alternate()
            if results:
                return results
            
            logger.warning("Could not fetch results from any source")
            return None
            
        except Exception as e:
            logger.error(f"Error fetching results: {e}")
            return None
    
    def _fetch_from_official(self) -> Optional[Dict]:
        """Fetch results from official Singapore Pools website"""
        try:
            url = "https://www.singaporepools.com.sg/en/product/Pages/toto_results.aspx"
            response = self.session.get(url, timeout=15)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Find the draw history table
            tables = soup.find_all('table')
            
            for table in tables:
                if 'drawHistory' in str(table) or 'result' in str(table).lower():
                    rows = table.find_all('tr')
                    
                    if len(rows) > 1:
                        # Get the latest draw (first row after header)
                        latest_row = rows[1]
                        cells = latest_row.find_all('td')
                        
                        if len(cells) >= 3:
                            # Extract draw number and date
                            draw_info = cells[0].get_text(strip=True)
                            draw_no = self._extract_draw_number(draw_info)
                            draw_date = self._extract_draw_date(draw_info)
                            
                            # Extract winning numbers
                            numbers_text = cells[1].get_text(strip=True)
                            winning_numbers = self._extract_numbers(numbers_text)
                            
                            # Extract additional number
                            additional_text = cells[2].get_text(strip=True)
                            additional_number = self._extract_additional_number(additional_text)
                            
                            if winning_numbers and len(winning_numbers) == 6:
                                logger.info(f"Fetched results for Draw {draw_no}: {winning_numbers} + {additional_number}")
                                return {
                                    'draw_no': draw_no,
                                    'draw_date': draw_date,
                                    'winning_numbers': winning_numbers,
                                    'additional_number': additional_number,
                                    'source': 'official'
                                }
            
            return None
            
        except Exception as e:
            logger.error(f"Official source error: {e}")
            return None
    
    def _fetch_from_alternate(self) -> Optional[Dict]:
        """Fetch from alternate source (mobile site or API)"""
        try:
            # Try mobile site
            mobile_url = "https://www.singaporepools.com.sg/mobile/Pages/toto_results.aspx"
            response = self.session.get(mobile_url, timeout=15)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Look for result containers
                result_containers = soup.find_all('div', class_=re.compile('result|draw', re.I))
                
                for container in result_containers:
                    numbers = container.find_all('span', class_=re.compile('number', re.I))
                    if numbers:
                        winning_numbers = []
                        for num in numbers[:6]:
                            try:
                                winning_numbers.append(int(num.get_text(strip=True)))
                            except:
                                pass
                        
                        if len(winning_numbers) == 6:
                            # Try to get additional number
                            additional = 0
                            if len(numbers) > 6:
                                try:
                                    additional = int(numbers[6].get_text(strip=True))
                                except:
                                    pass
                            
                            return {
                                'draw_no': self._get_current_draw_no(),
                                'draw_date': datetime.now().strftime('%Y-%m-%d'),
                                'winning_numbers': winning_numbers,
                                'additional_number': additional,
                                'source': 'alternate'
                            }
            
            return None
            
        except Exception as e:
            logger.error(f"Alternate source error: {e}")
            return None
    
    def fetch_draw_by_number(self, draw_no: str) -> Optional[Dict]:
        """Fetch specific draw results by number"""
        try:
            # This would require accessing historical data
            # For now, fetch latest and check if match
            latest = self.fetch_latest_results()
            if latest and latest.get('draw_no') == draw_no:
                return latest
            return None
            
        except Exception as e:
            logger.error(f"Error fetching draw {draw_no}: {e}")
            return None
    
    def _extract_draw_number(self, text: str) -> str:
        """Extract draw number from text"""
        # Pattern: "Draw No. 4180" or "Draw 4180"
        patterns = [
            r'Draw\s*No\.?\s*(\d+)',
            r'Draw\s*(\d+)',
            r'#(\d+)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1)
        
        return self._get_current_draw_no()
    
    def _extract_draw_date(self, text: str) -> str:
        """Extract draw date from text"""
        # Try to find date pattern
        date_patterns = [
            r'(\d{1,2})\s+(\w+)\s+(\d{4})',  # 4 May 2026
            r'(\d{2})/(\d{2})/(\d{4})',       # 04/05/2026
            r'(\d{4})-(\d{2})-(\d{2})'        # 2026-05-04
        ]
        
        for pattern in date_patterns:
            match = re.search(pattern, text)
            if match:
                groups = match.groups()
                if len(groups) == 3:
                    if groups[0].isdigit() and groups[2].isdigit():
                        day = int(groups[0])
                        month = self._month_to_number(groups[1]) if not groups[1].isdigit() else int(groups[1])
                        year = int(groups[2])
                        return f"{year}-{month:02d}-{day:02d}"
        
        return datetime.now().strftime('%Y-%m-%d')
    
    def _extract_numbers(self, text: str) -> List[int]:
        """Extract winning numbers from text"""
        # Find all numbers
        numbers = re.findall(r'\b(\d{1,2})\b', text)
        winning = []
        
        for num in numbers:
            n = int(num)
            if 1 <= n <= 49 and n not in winning:
                winning.append(n)
                if len(winning) == 6:
                    break
        
        return winning
    
    def _extract_additional_number(self, text: str) -> int:
        """Extract additional number from text"""
        numbers = re.findall(r'\b(\d{1,2})\b', text)
        for num in numbers:
            n = int(num)
            if 1 <= n <= 49:
                return n
        return 0
    
    def _month_to_number(self, month: str) -> int:
        """Convert month name to number"""
        months = {
            'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4, 'may': 5, 'jun': 6,
            'jul': 7, 'aug': 8, 'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12
        }
        return months.get(month.lower()[:3], 1)
    
    def _get_current_draw_no(self) -> str:
        """Get current/next draw number based on schedule"""
        # Calculate based on date
        from datetime import datetime, timedelta
        
        # Reference draw (you can adjust this)
        reference_draw = 4180
        reference_date = datetime(2026, 5, 4)
        
        today = datetime.now()
        days_diff = (today - reference_date).days
        
        # Draws are Monday and Thursday (2 per week, ~104 per year)
        # Approximate calculation
        weeks_diff = days_diff // 7
        draws_per_week = 2
        
        draw_no = reference_draw + (weeks_diff * draws_per_week)
        
        return str(draw_no)
    
    def check_if_draw_occurred(self, draw_date: str, draw_time: str = "18:30") -> bool:
        """Check if a specific draw has occurred"""
        try:
            draw_datetime = datetime.strptime(f"{draw_date} {draw_time}", "%Y-%m-%d %H:%M")
            current_time = datetime.now()
            
            # Add 2 hours buffer for results to be published
            results_available_time = draw_datetime + timedelta(hours=2)
            
            return current_time > results_available_time
            
        except Exception as e:
            logger.error(f"Error checking draw time: {e}")
            return False
    
    def wait_for_results(self, draw_date: str, max_wait_hours: int = 48) -> Optional[Dict]:
        """Wait for results to be available and fetch them"""
        from datetime import timedelta
        import time
        
        start_time = datetime.now()
        draw_datetime = datetime.strptime(f"{draw_date} 18:30", "%Y-%m-%d %H:%M")
        
        # Don't even try until 2 hours after draw
        if datetime.now() < draw_datetime + timedelta(hours=2):
            wait_seconds = (draw_datetime + timedelta(hours=2) - datetime.now()).total_seconds()
            logger.info(f"Waiting {wait_seconds/3600:.1f} hours for results to be available...")
            time.sleep(min(wait_seconds, 3600))  # Max wait 1 hour before checking
        
        # Try to fetch results every hour for max_wait_hours
        for attempt in range(max_wait_hours):
            results = self.fetch_latest_results()
            if results:
                logger.info(f"Results fetched on attempt {attempt + 1}")
                return results
            
            logger.info(f"Results not yet available. Waiting 1 hour... (Attempt {attempt + 1}/{max_wait_hours})")
            time.sleep(3600)  # Wait 1 hour
        
        logger.error(f"Results not available after {max_wait_hours} hours")
        return None

# Add timedelta import
from datetime import timedelta