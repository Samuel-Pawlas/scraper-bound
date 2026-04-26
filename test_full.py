from scraper import BoundScraper
from product_scraper import ProductDetailScraper
from embeddings import EmbeddingGenerator
from importer import SupabaseImporter
import json
import time

print("Starting full test...")

scraper = BoundScraper()
product_urls = scraper.get_product_listings(1)
print(f"Found {len(product_urls)} products on page 1")

# Test with 3 products
test_urls = [p['product_url'] for p in product_urls[:3]]
print(f"Testing with {len(test_urls)} products")

detail_scraper = ProductDetailScraper()
embed_gen = EmbeddingGenerator()

products = []
for i, url in enumerate(test_urls):
    print(f"Processing {i+1}/{len(test_urls)}: {url[-40:]}")
    p = detail_scraper.scrape_product(url)
    if p:
        # Generate embeddings
        if p.get('image_url'):
            p['image_embedding'] = embed_gen.get_image_embedding(p['image_url'])
        info_text = embed_gen.generate_info_text(p)
        p['info_embedding'] = embed_gen.get_text_embedding(info_text)
        products.append(p)
    
    time.sleep(0.5)

embed_gen.close()
print(f"Scraped {len(products)} products")

# Test import to Supabase
if products:
    print("Testing Supabase import...")
    importer = SupabaseImporter()
    result = importer.import_products(products)
    print(f"Import result: {result}")
else:
    print("No products to import")