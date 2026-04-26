from scraper import BoundScraper
from product_scraper import ProductDetailScraper
from embeddings import EmbeddingGenerator
from importer import SupabaseImporter
import json
import time

scraper = BoundScraper()
product_urls = scraper.get_product_listings(1)

detail_scraper = ProductDetailScraper()
embed_gen = EmbeddingGenerator()

# Get 5 unique products (different from existing)
products = []
for url in product_urls[:5]:
    url = url.get('product_url')
    print(f"Processing: {url}")
    p = detail_scraper.scrape_product(url)
    if p:
        if p.get('image_url'):
            p['image_embedding'] = embed_gen.get_image_embedding(p['image_url'])
        info_text = embed_gen.generate_info_text(p)
        p['info_embedding'] = embed_gen.get_text_embedding(info_text)
        products.append(p)
    time.sleep(0.5)

embed_gen.close()

if products:
    importer = SupabaseImporter()
    result = importer.import_products(products)
    print(f"Result: {result}")
else:
    print("No products")