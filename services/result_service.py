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
        
        # Known draws database
        self.draws = {
            '4179': {
                'draw_no': '4179',
                'draw_date': '2026-05-04',
                'winning_numbers': [7, 18, 19, 30, 36, 48],
                'additional_number': 11
            }
        }
    
    def fetch_latest_results(self) -> Optional[Dict]:
        """Hybrid fetch: tries multiple methods"""
        
        # Method 1: Official JSON Archive
        result = self._fetch_from_json_archive()
        if result:
            logger.info("✅ Fetched from official JSON archive")
            return result
        
        # Method 2: Mobile API
        result = self._fetch_from_mobile_api()
        if result:
            logger.info("✅ Fetched from mobile API")
            return result
        
        # Method 3: Cache
        result = self._fetch_from_cache()
        if result:
            logger.info("✅ Using cached results")
            return result
        
        logger.warning("⚠️ All automatic methods failed")
        return None
    
    def _fetch_from_json_archive(self) -> Optional[Dict]:
        """Fetch from official JSON archive"""
        try:
            urls = [
                "https://www.singaporepools.com.sg/DataFileArchive/Lottery/Output/toto_draw_history.json",
                "https://www.singaporepools.com.sg/DataFile/Results/toto.json"
            ]
            
            for url in urls:
                try:
                    response = self.session.get(url, timeout=15)
                    if response.status_code == 200:
                        data = response.json()
                        
                        if isinstance(data, list) and len(data) > 0:
                            latest = data[0]
                            return {
                                'draw_no': str(latest.get('DrawNo', latest.get('drawNo', ''))),
                                'draw_date': latest.get('DrawDate', latest.get('drawDate', '')),
                                'winning_numbers': latest.get('WinningNumbers', latest.get('winningNumbers', [])),
                                'additional_number': latest.get('AdditionalNumber', latest.get('additionalNumber', 0)),
                                'source': 'json_archive'
                            }
                except:
                    continue
            
            return None
            
        except Exception as e:
            logger.error(f"JSON archive error: {e}")
            return None
    
    def _fetch_from_mobile_api(self) -> Optional[Dict]:
        """Fetch from mobile API"""
        try:
            url = "https://www.singaporepools.com.sg/mobile/lottery/latestResults.json?gametype=TOTO"
            response = self.session.get(url, timeout=15)
            
            if response.status_code == 200:
                data = response.json()
                if 'results' in data and len(data['results']) > 0:
                    latest = data['results'][0]
                    return {
                        'draw_no': str(latest.get('drawNo', '')),
                        'draw_date': latest.get('drawDate', ''),
                        'winning_numbers': latest.get('winningNumbers', []),
                        'additional_number': latest.get('additionalNumber', 0),
                        'source': 'mobile_api'
                    }
            
            return None
            
        except Exception as e:
            logger.error(f"Mobile API error: {e}")
            return None
    
    def _fetch_from_cache(self) -> Optional[Dict]:
        """Use cached results"""
        if self.cache and self.last_fetch_time:
            if datetime.now() - self.last_fetch_time < timedelta(hours=4):
                return self.cache
        return None
    
    def manual_update_results(self, draw_no: str, winning_numbers: List[int], additional: int) -> Dict:
        """Manual result entry"""
        result = {
            'draw_no': draw_no,
            'draw_date': datetime.now().strftime('%Y-%m-%d'),
            'winning_numbers': winning_numbers,
            'additional_number': additional,
            'source': 'manual_entry'
        }
        
        self.cache = result
        self.last_fetch_time = datetime.now()
        self.draws[draw_no] = result
        
        logger.info(f"✅ Manual results for draw {draw_no}: {winning_numbers} + {additional}")
        return result
    
    def get_draw_result(self, draw_no: str) -> Optional[Dict]:
        """Get specific draw result"""
        # Check cache first
        if self.cache and self.cache.get('draw_no') == draw_no:
            return self.cache
        
        # Check known draws
        if draw_no in self.draws:
            return self.draws[draw_no]
        
        # Try to fetch
        result = self.fetch_latest_results()
        if result and result.get('draw_no') == draw_no:
            self.cache = result
            self.last_fetch_time = datetime.now()
            return result
        
        return None

# Add missing MatchEngine class if not exists
try:
    from services.match_engine import MatchEngine
except ImportError:
    class MatchEngine:
        @staticmethod
        def check_matches(user_numbers, winning_numbers):
            matches = len(set(user_numbers) & set(winning_numbers))
            return {'matches': matches, 'prize_group': None, 'prize_amount': 0}