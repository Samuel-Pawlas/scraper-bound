#!/usr/bin/env python3
import json
import csv
import time
from datetime import datetime
from typing import List, Dict, Any
import sys
import os
import config
from scraper import BoundScraper
from product_scraper import ProductDetailScraper
from embeddings import EmbeddingGenerator
from importer import SupabaseImporter

def save_products(products: List[Dict[str, Any]], json_file: str, csv_file: str):
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(products, f, indent=2, ensure_ascii=False)
    print(f"Saved {len(products)} products to {json_file}")
    
    if products:
        fieldnames = ['id', 'source', 'brand', 'product_url', 'title', 'category', 'gender', 
                    'price', 'sale', 'description', 'image_url', 'second_hand']
        with open(csv_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
            writer.writeheader()
            for p in products:
                writer.writerow({k: p.get(k) for k in fieldnames})
        print(f"Saved {len(products)} products to {csv_file}")

def run_scraper(limit: int = None, use_cache: bool = True, batch_size: int = 50):
    print("="*60)
    print(f"Starting Bound Scraper at {datetime.now().isoformat()}")
    print("="*60)
    
    cache_file = "scraped_products.json"
    json_output = "products.json"
    csv_output = "products.csv"
    
    if use_cache and os.path.exists(cache_file):
        print(f"Loading cached products from {cache_file}...")
        with open(cache_file, 'r', encoding='utf-8') as f:
            products = json.load(f)
        print(f"Loaded {len(products)} cached products")
    else:
        print("\n[Step 1] Scraper product URLs...")
        scraper = BoundScraper()
        product_urls = scraper.scrape_all_product_urls()
        
        if limit:
            product_urls = product_urls[:limit]
        
        print(f"\n[Step 2] Scraping product details...")
        detail_scraper = ProductDetailScraper()
        products = []
        
        total = len(product_urls)
        for i, url in enumerate(product_urls, 1):
            print(f"Scraping product {i}/{total}: {url}")
            product = detail_scraper.scrape_product(url)
            if product:
                products.append(product)
            if i % 50 == 0:
                print(f"Progress: {i}/{total} products scraped")
            time.sleep(config.RATE_LIMIT_DELAY)
        
        print(f"\nScraped {len(products)} products")
        save_products(products, cache_file, csv_output.replace('.csv', '_raw.csv'))
    
    all_products = products
    total_products = len(all_products)
    
    print(f"\n[Step 3] Generating embeddings...")
    embed_gen = EmbeddingGenerator()
    
    products_with_embeddings = []
    for i, product in enumerate(all_products[:total_products], 1):
        image_url = product.get('image_url')
        
        if image_url:
            print(f"Generating image embedding {i}/{total_products}...")
            try:
                product['image_embedding'] = embed_gen.get_image_embedding(image_url)
            except Exception as e:
                print(f"Failed image embedding for {i}: {e}")
                product['image_embedding'] = None
        
        info_text = embed_gen.generate_info_text(product)
        if info_text:
            print(f"Generating info embedding {i}/{total_products}...")
            try:
                product['info_embedding'] = embed_gen.get_text_embedding(info_text)
            except Exception as e:
                print(f"Failed info embedding for {i}: {e}")
                product['info_embedding'] = None
        
        products_with_embeddings.append(product)
        
        if i % batch_size == 0 or i == total_products:
            print(f"Processing embedding batch {i//batch_size + 1}...")
        
        time.sleep(config.RATE_LIMIT_DELAY * 0.5)
    
    embed_gen.close()
    
    print(f"\n[Step 4] Saving to files...")
    save_products(products_with_embeddings, json_output, csv_output)
    
    print(f"\n[Step 5] Importing to Supabase...")
    importer = SupabaseImporter()
    result = importer.import_products(products_with_embeddings, batch_size=batch_size)
    
    print("\n" + "="*60)
    print("SCRAPING COMPLETE")
    print(f"Total products: {len(products_with_embeddings)}")
    print(f"Imported: {result.get('imported', 0)}")
    print(f"Failed: {result.get('failed', 0)}")
    print("="*60)
    
    return result

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='Bound Fashion Scraper')
    parser.add_argument('--limit', type=int, default=None)
    parser.add_argument('--no-cache', action='store_true')
    parser.add_argument('--batch-size', type=int, default=50)
    args = parser.parse_args()
    
    run_scraper(limit=args.limit, use_cache=not args.no_cache, batch_size=args.batch_size)