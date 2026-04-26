from product_scraper import ProductDetailScraper
import json

s = ProductDetailScraper()

urls = [
    'https://wearebound.com/products/estate-knit-sky-blue',
    'https://wearebound.com/products/parker-alpaca-cardigan-plum',
    'https://wearebound.com/products/moahir-sweatpants-grey'
]

for url in urls:
    p = s.scrape_product(url)
    if p:
        print(f'Title: {p.get("title", "N/A")[:50]}')
        print(f'  Price: {p.get("price")}')
        print(f'  Image: {str(p.get("image_url", ""))[:80]}')
        print(f'  Category: {p.get("category")}')
        print()