import requests
from bs4 import BeautifulSoup
import json
import time
import re
from typing import List, Dict, Any, Optional
from urllib.parse import urljoin
import config

try:
    import cloudscraper
    HAS_CLOUDSCRAPER = True
except ImportError:
    HAS_CLOUDSCRAPER = False

class BoundScraper:
    def __init__(self):
        if HAS_CLOUDSCRAPER:
            self.session = cloudscraper.create_scraper(
                browser={'browser': 'chrome', 'platform': 'windows', 'mobile': False}
            )
        else:
            self.session = requests.Session()
            self.session.headers.update({
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept-Encoding': 'gzip, deflate, br',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'none',
                'Sec-Fetch-User': '?1',
                'Cache-Control': 'max-age=0',
                'Referer': 'https://www.google.com',
            })
        self.cloudflare_bypass_headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-GB,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
        }
    
    def _request_with_retry(self, url: str, max_retries: int = 3, use_cloudflare_bypass: bool = False) -> Optional[BeautifulSoup]:
        headers = self.cloudflare_bypass_headers if use_cloudflare_bypass else None
        
        for attempt in range(max_retries):
            try:
                response = self.session.get(url, timeout=config.REQUEST_TIMEOUT, headers=headers)
                response.raise_for_status()
                return BeautifulSoup(response.text, 'lxml')
            except Exception as e:
                print(f"Attempt {attempt + 1} failed for {url}: {e}")
                if attempt < max_retries - 1:
                    time.sleep(config.RATE_LIMIT_DELAY * (attempt + 1))
        return None
    
    def get_product_listings(self, page: int = 1) -> List[Dict[str, Any]]:
        url = f"{config.COLLECTIONS_URL}?page={page}" if page > 1 else config.COLLECTIONS_URL
        soup = self._request_with_retry(url)
        
        if not soup:
            print(f"Failed to fetch page {page}")
            return []
        
        products = []
        product_containers = soup.select('[class*="product-item"], .product-item, [class*="Grid__Cell"] a[href*="/products/"]')
        
        if not product_containers:
            product_links = soup.select('a[href*="/products/"]')
            seen = set()
            for link in product_links:
                href = link.get('href', '')
                if href and '/products/' in href and href not in seen:
                    full_url = urljoin(config.BASE_URL, href)
                    if full_url not in seen:
                        seen.add(full_url)
                        title_elem = link.select_one('[class*="title"], h3, h4')
                        title = title_elem.get_text(strip=True) if title_elem else link.get_text(strip=True)
                        if title:
                            products.append({
                                'product_url': full_url,
                                'title': title
                            })
        
        for elem in soup.select('[class*="ProductItem"], .product-card, [data-product-handle]'):
            link = elem.select_one('a[href*="/products/"]')
            if link:
                href = link.get('href', '')
                if href:
                    full_url = urljoin(config.BASE_URL, href)
                    title_elem = elem.select_one('[class*="title"], h3, h4, .product-title')
                    price_elem = elem.select_one('[class*="price"], .price')
                    
                    title = title_elem.get_text(strip=True) if title_elem else ''
                    price = price_elem.get_text(strip=True) if price_elem else ''
                    
                    if full_url and '/products/' in full_url:
                        products.append({
                            'product_url': full_url,
                            'title': title,
                            'price': price
                        })
        
        unique_products = {}
        for p in products:
            if p['product_url'] not in unique_products:
                unique_products[p['product_url']] = p
        
        return list(unique_products.values())
    
    def get_total_pages(self) -> int:
        soup = self._request_with_retry(config.COLLECTIONS_URL)
        if not soup:
            soup = self._request_with_retry(config.COLLECTIONS_URL, use_cloudflare_bypass=True)
        if not soup:
            return 1
        
        page_links = soup.select('a[href*="page="], .pagination a')
        max_page = 1
        
        for link in page_links:
            href = link.get('href', '')
            match = re.search(r'page=(\d+)', href)
            if match:
                page_num = int(match.group(1))
                max_page = max(max_page, page_num)
        
        product_count_elem = soup.select_one('[class*="count"], .product-count, #product-count')
        if product_count_elem:
            text = product_count_elem.get_text(strip=True)
            match = re.search(r'(\d+)\s*products?', text, re.IGNORECASE)
            if match:
                count = int(match.group(1))
                max_page = max(max_page, (count // 48) + 1)
        
        return max_page
    
    def scrape_all_product_urls(self) -> List[str]:
        print("Discovering total pages...")
        total_pages = self.get_total_pages()
        print(f"Found approximately {total_pages} pages")
        
        all_urls = []
        for page in range(1, total_pages + 1):
            print(f"Scraping page {page}/{total_pages}...")
            products = self.get_product_listings(page)
            if not products:
                print(f"No products found on page {page}, stopping...")
                break
            
            for p in products:
                if p['product_url'] not in all_urls:
                    all_urls.append(p['product_url'])
            
            time.sleep(config.RATE_LIMIT_DELAY)
        
        print(f"Found {len(all_urls)} product URLs")
        return all_urls