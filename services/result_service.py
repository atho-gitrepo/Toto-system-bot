import requests
from datetime import datetime
from bs4 import BeautifulSoup

def fetch_latest_results():
    url = "https://www.singaporepools.com.sg/en/product/sr/Pages/toto_results.aspx"
    
    res = requests.get(url)
    soup = BeautifulSoup(res.text, "html.parser")

    numbers = []
    
    # ⚠️ You may need to adjust selector if site changes
    balls = soup.select(".winning-numbers span")

    for b in balls[:6]:
        numbers.append(int(b.text.strip()))

    return {
        "numbers": sorted(numbers),
        "date": datetime.utcnow()
    }