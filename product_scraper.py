import requests
from bs4 import BeautifulSoup
import json
import time
import re
from typing import Dict, Any, Optional, List
from urllib.parse import urljoin, urlparse
import config

class ProductDetailScraper:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
        })
    
    def _request_with_retry(self, url: str, max_retries: int = 3) -> Optional[BeautifulSoup]:
        for attempt in range(max_retries):
            try:
                response = self.session.get(url, timeout=config.REQUEST_TIMEOUT)
                response.raise_for_status()
                return BeautifulSoup(response.text, 'lxml')
            except Exception as e:
                print(f"Attempt {attempt + 1} failed for {url}: {e}")
                if attempt < max_retries - 1:
                    time.sleep(config.RATE_LIMIT_DELAY * (attempt + 1))
        return None
    
    def _clean_text(self, text: str) -> str:
        text = re.sub(r'\s+', ' ', text)
        return text.strip()
    
    def _extract_price(self, price_text: str) -> Dict[str, str]:
        price_text = price_text.strip()
        
        patterns = [
            (r'(\d+[\d,\.]*)\s*(USD|usd|\$)', 'USD'),
            (r'(\d+[\d,\.]*)\s*(EUR|eur|€)', 'EUR'),
            (r'(\d+[\d,\.]*)\s*(GBP|gbp|£)', 'GBP'),
            (r'(\d+[\d,\.]*)\s*(CZK|czk|Kč)', 'CZK'),
            (r'(\d+[\d,\.]*)\s*(PLN|pln|zł)', 'PLN'),
            (r'(\d+[\d,\.]*)\s*(SEK|sek|kr)', 'SEK'),
            (r'(\d+[\d,\.]*)\s*(DKK|dkk|kr)', 'DKK'),
            (r'(\d+[\d,\.]*)\s*(NOK|nok|kr)', 'NOK'),
            (r'(\d+[\d,\.]*)\s*(CHF|chf|fr)', 'CHF'),
            (r'(\d+[\d,\.]*)\s*(JPY|jpy|¥)', 'JPY'),
            (r'(\d+[\d,\.]*)\s*(AUD|aud|\$)', 'AUD'),
            (r'(\d+[\d,\.]*)\s*(NZD|nzd|\$)', 'NZD'),
        ]
        
        result = {}
        for pattern, currency in patterns:
            match = re.search(pattern, price_text)
            if match:
                amount = match.group(1).replace(',', '')
                result[currency] = amount
        
        if not result:
            match = re.search(r'(\d+[\d,\.]*)', price_text)
            if match:
                result['USD'] = match.group(1).replace(',', '')
        
        return result
    
    def _format_prices(self, prices: Dict[str, str]) -> str:
        formatted = []
        for currency in ['EUR', 'USD', 'GBP', 'CZK', 'PLN', 'SEK', 'DKK', 'NOK', 'CHF', 'JPY', 'AUD', 'NZD']:
            if currency in prices:
                amount = prices[currency]
                try:
                    if float(amount) == int(float(amount)):
                        amount = str(int(float(amount)))
                    else:
                        amount = str(float(amount))
                except:
                    pass
                formatted.append(f"{amount}{currency}")
        return ", ".join(formatted)
    
    def _get_product_type_from_title(self, title: str) -> Optional[str]:
        title_lower = title.lower()
        
        type_keywords = {
            'sweater': 'Sweaters',
            'knit': 'Knitwear',
            'cardigan': 'Cardigans',
            'jacket': 'Jackets & Coats',
            'coat': 'Jackets & Coats',
            'parka': 'Jackets & Coats',
            'puffer': 'Jackets & Coats',
            'overshirt': 'Overshirts',
            'shirt': 'Shirts',
            'polo': 'Polos',
            'tshirt': 'T-Shirts',
            'tee': 'T-Shirts',
            'trouser': 'Trousers',
            'pant': 'Trousers',
            'jeans': 'Jeans',
            'short': 'Shorts',
            'jogger': 'Joggers',
            'hoodie': 'Hoodies',
            'sweatshirt': 'Sweatshirts',
            'fleece': 'Fleeces',
            'beanie': 'Beanies',
            'cap': 'Caps',
            'hat': 'Hats',
            'sunglasses': 'Sunglasses',
            'accessories': 'Accessories',
            'socks': 'Socks',
            'gift card': 'Gift Card'
        }
        
        for keyword, category in type_keywords.items():
            if keyword in title_lower:
                return category
        
        return None
    
    def parse_product(self, url: str) -> Optional[Dict[str, Any]]:
        soup = self._request_with_retry(url)
        
        if not soup:
            print(f"Failed to fetch product: {url}")
            return None
        
        title = ''
        description = ''
        image_urls = []
        prices = {}
        sale_prices = {}
        categories = []
        sizes = []
        colors = []
        gender = 'UNISEX'
        
        title_elem = soup.select_one('h1[class*="title"], h1.title, [class*="product-title"], [data-testid="product-title"], h1')
        if title_elem:
            title = self._clean_text(title_elem.get_text())
            title = re.sub(r'\s*[-–—]\s*bound\s*$', '', title, flags=re.IGNORECASE).strip()
        
        if not title:
            title_elem = soup.select_one('title')
            if title_elem:
                title = title_elem.get_text(strip=True).split('|')[0].strip()
        
        price_match = soup.select_one('[class*="price"]')
        if price_match:
            price_text = self._clean_text(price_match.get_text())
            
            regular_match = re.search(r'[Rr]egular\s*price\s*[\$\£€]?\s*([\d,\.]+)', price_text)
            sale_match = re.search(r'[Ss]ale\s*price\s*[\$\£€]?\s*([\d,\.]+)', price_text)
            
            if regular_match:
                prices['USD'] = regular_match.group(1).replace(',', '')
            
            if sale_match:
                sale_prices['USD'] = sale_match.group(1).replace(',', '')
                if not prices:
                    prices['USD'] = sale_match.group(1).replace(',', '')
        
        meta_img = soup.find_all('meta', property='og:image')
        for meta in meta_img:
            content = meta.get('content')
            if content:
                if content.startswith('//'):
                    content = 'https:' + content
                elif content.startswith('/'):
                    content = 'https://wearebound.com' + content
                if 'LOGO' not in content.upper() and content not in image_urls:
                    image_urls.append(content)
        
        for img in soup.select('[class*="media"] img, [class*="gallery"] img, .slick-slide img'):
            src = img.get('src') or img.get('data-src') or ''
            if src:
                if src.startswith('//'):
                    src = 'https:' + src
                elif src.startswith('/'):
                    src = 'https://wearebound.com' + src
                
                if ('/products/' in src or '/files/' in src) and 'LOGO' not in src.upper():
                    if src not in image_urls:
                        image_urls.append(src)
        
        size_container = soup.select_one('[class*="size"], fieldset, [data-testid="size-selector"]')
        if size_container:
            for option in size_container.select('label, button, option'):
                text = self._clean_text(option.get_text())
                if text and not text.lower().startswith('choose') and not text.lower().startswith('size'):
                    if text not in sizes:
                        sizes.append(text)
        
        for swatch in soup.select('[class*="swatch"], [class*="color-swatch"]'):
            color = swatch.get('aria-label') or swatch.get('title') or ''
            if color and color not in colors:
                colors.append(color)
        
        color_match = re.search(r'([A-Za-z\s]+)\s*-\s*\$', ' '.join(sizes))
        if not colors and color_match:
            colors.append(color_match.group(1).strip())
        
        product_type = self._get_product_type_from_title(title)
        if product_type:
            categories.append(product_type)
        
        is_sale = False
        for badge in soup.select('[class*="sale"], [class*="badge"], .sale-badge'):
            if badge.get_text(strip=True).lower() == 'sale':
                is_sale = True
                break
        
        if 'Sale' in soup.get_text():
            is_sale = True
        
        primary_image = image_urls[0] if image_urls else ''
        
        image_urls = list(dict.fromkeys(image_urls))
        primary_image = image_urls[0] if image_urls else ''
        
        formatted_price = self._format_prices(prices)
        
        if is_sale and sale_prices:
            formatted_sale = self._format_prices(sale_prices)
        else:
            formatted_sale = None
        
        category_str = categories[0] if categories else None
        
        metadata = {
            'title': title,
            'description': description[:500] if description else '',
            'colors': colors[:10],
            'sizes': sizes[:10],
            'categories': categories,
            'gender': gender,
            'all_prices': prices,
            'sale_prices': sale_prices,
            'url': url,
            'is_sale': is_sale,
        }
        
        result = {
            'source': config.SOURCE,
            'brand': config.BRAND,
            'product_url': url,
            'title': title,
            'image_url': primary_image,
            'additional_images': ", ".join(image_urls[1:6]) if len(image_urls) > 1 else None,
            'image_embedding': None,
            'info_embedding': None,
            'category': category_str,
            'gender': gender,
            'price': formatted_price,
            'sale': formatted_sale,
            'second_hand': False,
            'metadata': json.dumps(metadata),
            'description': description[:1000] if description else None,
            'created_at': None,
            'size': ", ".join(sizes[:15]) if sizes else None,
            'country': 'GB',
            'tags': None,
            'affiliate_url': None,
            'compressed_image_url': None,
        }
        
        return result
    
    def scrape_product(self, url: str) -> Optional[Dict[str, Any]]:
        return self.parse_product(url)