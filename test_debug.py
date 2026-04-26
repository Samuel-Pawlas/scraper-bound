from product_scraper import ProductDetailScraper
from bs4 import BeautifulSoup
import requests

sess = requests.Session()
sess.headers.update({'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'})
r = sess.get('https://wearebound.com/products/estate-knit-sky-blue', timeout=30)
soup = BeautifulSoup(r.text, 'lxml')

print('Testing different image selectors:')

selectors = [
    'img[src*="cdn/shop/files"]',
    '[class*="media"] img',
    '.gallery img',
    '__all_media__'
]

for sel in selectors:
    imgs = soup.select(sel)
    print(f'{sel}: {len(imgs)} found')
    for img in imgs[:2]:
        src = img.get('src') or img.get('data-src') or 'no src'
        print(f'  {src[:60]}')

print()
print('Meta og:image:')
for meta in soup.find_all('meta', property='og:image'):
    content = meta.get('content', '')
    if content:
        print(f'  {content[:80]}')