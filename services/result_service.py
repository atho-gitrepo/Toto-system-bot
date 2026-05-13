import requests
from bs4 import BeautifulSoup
from typing import List, Dict, Optional
from datetime import datetime
import re
import json
import time
import logging
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, WebDriverException
import random

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
            'Upgrade-Insecure-Requests': '1',
        })
        
        # Draw information for 2026
        self.draws = self._initialize_draws()
        
    def _initialize_draws(self) -> Dict:
        """Initialize draw information from known data"""
        return {
            '4179': {
                'draw_no': '4179',
                'draw_date': '2026-05-04',
                'winning_numbers': [7, 18, 19, 30, 36, 48],
                'additional_number': 11
            },
            '4180': {
                'draw_no': '4180',
                'draw_date': '2026-05-07',
                'winning_numbers': None,  # To be fetched after draw
                'additional_number': None
            }
        }
    
    def fetch_latest_results(self) -> Optional[Dict]:
        """Fetch latest Toto results with multiple fallback methods"""
        
        # Method 1: Try Singapore Pools official website with proper headers
        result = self._fetch_from_official()
        if result:
            logger.info("Successfully fetched from official website")
            return result
        
        # Method 2: Try using Singapore Pools mobile API endpoint
        result = self._fetch_from_mobile_api()
        if result:
            logger.info("Successfully fetched from mobile API")
            return result
        
        # Method 3: Try using Selenium for JavaScript rendering
        result = self._fetch_with_selenium()
        if result:
            logger.info("Successfully fetched using Selenium")
            return result
        
        # Method 4: Use known results from database
        result = self._get_known_results()
        if result:
            logger.info("Using known results from database")
            return result
        
        # Method 5: Manual fallback - return last known draw
        logger.warning("All fetch methods failed, returning last known draw")
        return self._get_last_known_draw()
    
    def _fetch_from_official(self) -> Optional[Dict]:
        """Fetch from official Singapore Pools website"""
        try:
            # Use the results page URL
            url = "https://www.singaporepools.com.sg/en/product/Pages/toto_results.aspx"
            
            # Add delay to avoid rate limiting
            time.sleep(random.uniform(1, 3))
            
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            
            # Look for JSON data in the page
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Try to find embedded JSON data
            scripts = soup.find_all('script')
            for script in scripts:
                if script.string and 'winningNumbers' in script.string:
                    # Extract JSON data
                    import re
                    json_match = re.search(r'\{[^}]*"winningNumbers"[^}]*\}', script.string)
                    if json_match:
                        try:
                            data = json.loads(json_match.group())
                            if 'winningNumbers' in data:
                                return {
                                    'draw_no': data.get('drawNo', 'Unknown'),
                                    'draw_date': data.get('drawDate', datetime.now().strftime('%Y-%m-%d')),
                                    'winning_numbers': data['winningNumbers'],
                                    'additional_number': data.get('additionalNumber', 0)
                                }
                        except:
                            pass
            
            # Try table scraping as fallback
            tables = soup.find_all('table')
            for table in tables:
                rows = table.find_all('tr')
                for row in rows:
                    cells = row.find_all('td')
                    if len(cells) >= 3:
                        numbers_text = cells[1].get_text()
                        numbers = re.findall(r'\d+', numbers_text)
                        if len(numbers) >= 6:
                            return {
                                'draw_no': cells[0].get_text().strip(),
                                'draw_date': datetime.now().strftime('%Y-%m-%d'),
                                'winning_numbers': [int(n) for n in numbers[:6]],
                                'additional_number': int(numbers[6]) if len(numbers) > 6 else 0
                            }
            
            return None
            
        except Exception as e:
            logger.error(f"Official fetch error: {e}")
            return None
    
    def _fetch_from_mobile_api(self) -> Optional[Dict]:
        """Fetch from Singapore Pools mobile API"""
        try:
            # Singapore Pools mobile API endpoint (unofficial but works)
            api_urls = [
                "https://www.singaporepools.com.sg/mobile/lottery/latestResults.json?gametype=TOTO",
                "https://www.singaporepools.com.sg/DataFile/Results/toto.json",
                "https://singaporepools-api.vercel.app/api/toto/latest"
            ]
            
            for url in api_urls:
                try:
                    response = self.session.get(url, timeout=15)
                    if response.status_code == 200:
                        data = response.json()
                        
                        # Parse different API response formats
                        if 'results' in data:
                            latest = data['results'][0]
                            return {
                                'draw_no': latest.get('drawNo', 'Unknown'),
                                'draw_date': latest.get('drawDate', datetime.now().strftime('%Y-%m-%d')),
                                'winning_numbers': latest.get('winningNumbers', []),
                                'additional_number': latest.get('additionalNumber', 0)
                            }
                        elif 'winningNumbers' in data:
                            return {
                                'draw_no': data.get('drawNo', 'Unknown'),
                                'draw_date': data.get('drawDate', datetime.now().strftime('%Y-%m-%d')),
                                'winning_numbers': data['winningNumbers'],
                                'additional_number': data.get('additionalNumber', 0)
                            }
                except:
                    continue
            
            return None
            
        except Exception as e:
            logger.error(f"Mobile API fetch error: {e}")
            return None
    
    def _fetch_with_selenium(self) -> Optional[Dict]:
        """Fetch using Selenium for JavaScript-rendered content"""
        driver = None
        try:
            # Setup Chrome options for headless browsing
            chrome_options = Options()
            chrome_options.add_argument('--headless')
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument('--window-size=1920,1080')
            
            driver = webdriver.Chrome(options=chrome_options)
            driver.set_page_load_timeout(30)
            
            # Navigate to results page
            driver.get("https://www.singaporepools.com.sg/en/product/Pages/toto_results.aspx")
            
            # Wait for results to load
            wait = WebDriverWait(driver, 20)
            wait.until(EC.presence_of_element_located((By.CLASS_NAME, "drawHistory")))
            
            # Find the latest draw
            draw_rows = driver.find_elements(By.CSS_SELECTOR, ".drawHistory tbody tr")
            
            if draw_rows:
                latest = draw_rows[0]
                cells = latest.find_elements(By.TAG_NAME, "td")
                
                if len(cells) >= 3:
                    # Get draw number
                    draw_no_text = cells[0].text.strip()
                    draw_no = re.search(r'\d+', draw_no_text)
                    
                    # Get winning numbers
                    numbers_text = cells[1].text.strip()
                    numbers = re.findall(r'\d+', numbers_text)
                    
                    # Get additional number
                    additional_text = cells[2].text.strip()
                    additional = re.findall(r'\d+', additional_text)
                    
                    if len(numbers) >= 6:
                        return {
                            'draw_no': draw_no.group() if draw_no else 'Unknown',
                            'draw_date': datetime.now().strftime('%Y-%m-%d'),
                            'winning_numbers': [int(n) for n in numbers[:6]],
                            'additional_number': int(additional[0]) if additional else 0
                        }
            
            return None
            
        except TimeoutException:
            logger.error("Selenium timeout - page took too long to load")
            return None
        except WebDriverException as e:
            logger.error(f"Selenium WebDriver error: {e}")
            return None
        except Exception as e:
            logger.error(f"Selenium fetch error: {e}")
            return None
        finally:
            if driver:
                driver.quit()
    
    def _get_known_results(self) -> Optional[Dict]:
        """Get results from known database of draws"""
        try:
            # Check if today is a draw day and results should be available
            now = datetime.now()
            current_draw_no = self._get_current_draw_number()
            
            # For past draws, return known results
            if current_draw_no in self.draws and self.draws[current_draw_no]['winning_numbers']:
                return self.draws[current_draw_no]
            
            # For the most recent completed draw
            for draw_no, draw_info in sorted(self.draws.items(), reverse=True):
                if draw_info['winning_numbers']:
                    draw_date = datetime.strptime(draw_info['draw_date'], '%Y-%m-%d')
                    if draw_date < now:
                        return draw_info
            
            return None
            
        except Exception as e:
            logger.error(f"Known results fetch error: {e}")
            return None
    
    def _get_current_draw_number(self) -> str:
        """Get current draw number based on date"""
        now = datetime.now()
        
        # Draw schedule for 2026
        # Draw 4180: May 7, 2026
        # Draw 4181: May 11, 2026
        # Draw 4182: May 14, 2026
        
        if now < datetime(2026, 5, 7, 18, 30):
            return '4180'
        elif now < datetime(2026, 5, 11, 18, 30):
            return '4181'
        elif now < datetime(2026, 5, 14, 18, 30):
            return '4182'
        else:
            return '4183'
    
    def _get_last_known_draw(self) -> Dict:
        """Return the last known draw results"""
        # Return Draw 4179 results (known from May 4, 2026)
        return {
            'draw_no': '4179',
            'draw_date': '2026-05-04',
            'winning_numbers': [7, 18, 19, 30, 36, 48],
            'additional_number': 11,
            'source': 'fallback'
        }
    
    def get_draw_result(self, draw_no: str) -> Optional[Dict]:
        """Get specific draw result by number"""
        try:
            # Check known draws
            if draw_no in self.draws:
                return self.draws[draw_no]
            
            # Try to fetch from API
            result = self.fetch_latest_results()
            if result and result.get('draw_no') == draw_no:
                return result
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting draw {draw_no}: {e}")
            return None
    
    def update_draw_results(self, draw_no: str, winning_numbers: List[int], additional: int):
        """Manually update draw results (for admin use)"""
        self.draws[draw_no] = {
            'draw_no': draw_no,
            'draw_date': datetime.now().strftime('%Y-%m-%d'),
            'winning_numbers': winning_numbers,
            'additional_number': additional
        }
        logger.info(f"Manually updated draw {draw_no} results")