import requests
from bs4 import BeautifulSoup
from typing import List, Dict, Optional
from datetime import datetime, timedelta
import re
import json
import logging
import time

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ResultService:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'application/json, text/plain, */*',
        })
        
        # Cache for results
        self.cache = {}
        self.last_fetch_time = None
        
    def fetch_latest_results(self) -> Optional[Dict]:
        """Hybrid fetch: tries multiple methods and falls back gracefully"""
        
        # Method 1: Official JSON Archive (Most reliable)
        result = self._fetch_from_json_archive()
        if result:
            logger.info("✅ Fetched from official JSON archive")
            return result
        
        # Method 2: Mobile API endpoint
        result = self._fetch_from_mobile_api()
        if result:
            logger.info("✅ Fetched from mobile API")
            return result
        
        # Method 3: Web scraping (Backup)
        result = self._fetch_from_web_scrape()
        if result:
            logger.info("✅ Fetched via web scraping")
            return result
        
        # Method 4: Cache (if available and recent)
        result = self._fetch_from_cache()
        if result:
            logger.info("✅ Using cached results")
            return result
        
        logger.warning("⚠️ All automatic methods failed. Manual entry required.")
        return None
    
    def _fetch_from_json_archive(self) -> Optional[Dict]:
        """Method 1: Official JSON data archive"""
        try:
            # Singapore Pools official data archive
            urls = [
                "https://www.singaporepools.com.sg/DataFileArchive/Lottery/Output/toto_draw_history.json",
                "https://www.singaporepools.com.sg/DataFile/Results/toto.json",
                "https://www.singaporepools.com.sg/mobile/lottery/latestResults.json?gametype=TOTO"
            ]
            
            for url in urls:
                try:
                    response = self.session.get(url, timeout=15)
                    if response.status_code == 200:
                        data = response.json()
                        
                        # Parse different formats
                        if isinstance(data, list) and len(data) > 0:
                            latest = data[0]
                            return {
                                'draw_no': str(latest.get('DrawNo', latest.get('drawNo', ''))),
                                'draw_date': latest.get('DrawDate', latest.get('drawDate', '')),
                                'winning_numbers': latest.get('WinningNumbers', latest.get('winningNumbers', [])),
                                'additional_number': latest.get('AdditionalNumber', latest.get('additionalNumber', 0)),
                                'source': 'json_archive'
                            }
                        elif 'results' in data and len(data['results']) > 0:
                            latest = data['results'][0]
                            return {
                                'draw_no': str(latest.get('drawNo', '')),
                                'draw_date': latest.get('drawDate', ''),
                                'winning_numbers': latest.get('winningNumbers', []),
                                'additional_number': latest.get('additionalNumber', 0),
                                'source': 'mobile_api'
                            }
                except:
                    continue
            
            return None
            
        except Exception as e:
            logger.error(f"JSON archive fetch error: {e}")
            return None
    
    def _fetch_from_mobile_api(self) -> Optional[Dict]:
        """Method 2: Mobile API endpoints"""
        try:
            # Alternative mobile APIs
            apis = [
                "https://sg-lottery-api.herokuapp.com/api/toto/latest",
                "https://toto-result-api.vercel.app/api/latest"
            ]
            
            for api_url in apis:
                try:
                    response = self.session.get(api_url, timeout=10)
                    if response.status_code == 200:
                        data = response.json()
                        return {
                            'draw_no': str(data.get('drawNo', data.get('id', 'Unknown'))),
                            'draw_date': data.get('drawDate', data.get('date', '')),
                            'winning_numbers': data.get('winningNumbers', data.get('numbers', [])),
                            'additional_number': data.get('additionalNumber', data.get('additional', 0)),
                            'source': 'third_party_api'
                        }
                except:
                    continue
            
            return None
            
        except Exception as e:
            logger.error(f"Mobile API fetch error: {e}")
            return None
    
    def _fetch_from_web_scrape(self) -> Optional[Dict]:
        """Method 3: Web scraping as backup"""
        try:
            url = "https://www.singaporepools.com.sg/en/product/Pages/toto_results.aspx"
            response = self.session.get(url, timeout=20)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Look for JSON data in script tags
            scripts = soup.find_all('script')
            for script in scripts:
                if script.string and ('winningNumbers' in script.string or 'WinningNumbers' in script.string):
                    # Extract numbers using regex
                    numbers_match = re.search(r'\[(\d{1,2},\s*\d{1,2},\s*\d{1,2},\s*\d{1,2},\s*\d{1,2},\s*\d{1,2})\]', script.string)
                    if numbers_match:
                        numbers_str = numbers_match.group(1)
                        numbers = [int(n.strip()) for n in numbers_str.split(',')]
                        
                        additional_match = re.search(r'additionalNumber["\']?\s*:\s*(\d+)', script.string)
                        additional = int(additional_match.group(1)) if additional_match else 0
                        
                        draw_match = re.search(r'drawNo["\']?\s*:\s*["\']?(\d+)', script.string)
                        draw_no = draw_match.group(1) if draw_match else 'Unknown'
                        
                        return {
                            'draw_no': draw_no,
                            'draw_date': datetime.now().strftime('%Y-%m-%d'),
                            'winning_numbers': numbers[:6],
                            'additional_number': additional,
                            'source': 'web_scrape'
                        }
            
            # Try table scraping
            tables = soup.find_all('table')
            for table in tables:
                rows = table.find_all('tr')
                for row in rows[:3]:  # First few rows
                    cells = row.find_all('td')
                    if len(cells) >= 3:
                        numbers_text = cells[1].get_text()
                        numbers = re.findall(r'\d{1,2}', numbers_text)
                        if len(numbers) >= 6:
                            return {
                                'draw_no': cells[0].get_text().strip(),
                                'draw_date': datetime.now().strftime('%Y-%m-%d'),
                                'winning_numbers': [int(n) for n in numbers[:6]],
                                'additional_number': int(numbers[6]) if len(numbers) > 6 else 0,
                                'source': 'table_scrape'
                            }
            
            return None
            
        except Exception as e:
            logger.error(f"Web scrape error: {e}")
            return None
    
    def _fetch_from_cache(self) -> Optional[Dict]:
        """Method 4: Use cached results if available and recent"""
        if self.cache and self.last_fetch_time:
            # Cache valid for 4 hours
            if datetime.now() - self.last_fetch_time < timedelta(hours=4):
                return self.cache
        return None
    
    def manual_update_results(self, draw_no: str, winning_numbers: List[int], additional: int) -> Dict:
        """Manual result entry (used by /declare command)"""
        result = {
            'draw_no': draw_no,
            'draw_date': datetime.now().strftime('%Y-%m-%d'),
            'winning_numbers': winning_numbers,
            'additional_number': additional,
            'source': 'manual_entry'
        }
        
        # Update cache
        self.cache = result
        self.last_fetch_time = datetime.now()
        
        logger.info(f"✅ Manual results entered for draw {draw_no}: {winning_numbers} + {additional}")
        return result
    
    def get_draw_result(self, draw_no: str) -> Optional[Dict]:
        """Get specific draw result with retry logic"""
        
        # Check cache first
        if self.cache and self.cache.get('draw_no') == draw_no:
            return self.cache
        
        # Try to fetch automatically
        result = self.fetch_latest_results()
        
        if result and result.get('draw_no') == draw_no:
            self.cache = result
            self.last_fetch_time = datetime.now()
            return result
        
        return None
    
    def wait_for_results(self, draw_no: str, max_wait_hours: int = 6) -> Optional[Dict]:
        """Wait for results to become available (for after-draw waiting)"""
        
        logger.info(f"Waiting for results for draw {draw_no}...")
        
        # Check every 30 minutes for up to max_wait_hours
        for attempt in range(max_wait_hours * 2):
            result = self.get_draw_result(draw_no)
            if result and result.get('winning_numbers'):
                logger.info(f"Results found after {attempt * 30} minutes")
                return result
            
            logger.info(f"Results not yet available. Waiting 30 minutes... (Attempt {attempt + 1}/{max_wait_hours * 2})")
            time.sleep(1800)  # 30 minutes
        
        logger.warning(f"No results found for draw {draw_no} after {max_wait_hours} hours")
        return None