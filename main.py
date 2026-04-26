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

def save_to_json(products: List[Dict[str, Any]], filename: str = None):
    filename = filename or config.JSON_OUTPUT
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(products, f, indent=2, ensure_ascii=False)
    print(f"Saved {len(products)} products to {filename}")

def save_to_csv(products: List[Dict[str, Any]], filename: str = None):
    filename = filename or config.CSV_OUTPUT
    
    if not products:
        print("No products to save to CSV")
        return
    
    fieldnames = ['id', 'source', 'brand', 'product_url', 'title', 'category', 'gender', 
                'price', 'sale', 'description', 'image_url', 'second_hand']
    
    with open(filename, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
        writer.writeheader()
        
        for product in products:
            row = {k: product.get(k) for k in fieldnames}
            writer.writerow(row)
    
    print(f"Saved {len(products)} products to {filename}")

def run_full_scraper(limit: int = None, use_cache: bool = True):
    print("="*60)
    print(f"Starting Bound Scraper at {datetime.now().isoformat()}")
    print("="*60)
    
    cache_file = "scraped_products.json"
    
    if use_cache and os.path.exists(cache_file):
        print(f"Loading cached products from {cache_file}...")
        with open(cache_file, 'r', encoding='utf-8') as f:
            products = json.load(f)
        print(f"Loaded {len(products)} cached products")
    else:
        print("\n[Step 1] Scraping product URLs...")
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
            
            if i % 10 == 0:
                print(f"Progress: {i}/{total} products scraped")
            
            time.sleep(config.RATE_LIMIT_DELAY)
        
        print(f"\nScraped {len(products)} products")
        
        save_to_json(products, cache_file)
    
    print(f"\n[Step 3] Generating embeddings...")
    embed_gen = EmbeddingGenerator()
    
    for i, product in enumerate(products, 1):
        image_url = product.get('image_url')
        
        if image_url:
            print(f"Generating image embedding {i}/{len(products)}...")
            image_embedding = embed_gen.get_image_embedding(image_url)
            product['image_embedding'] = image_embedding
        
        time.sleep(config.RATE_LIMIT_DELAY * 0.5)
    
    for i, product in enumerate(products, 1):
        info_text = embed_gen.generate_info_text(product)
        
        if info_text:
            print(f"Generating info embedding {i}/{len(products)}...")
            info_embedding = embed_gen.get_text_embedding(info_text)
            product['info_embedding'] = info_embedding
        
        time.sleep(config.RATE_LIMIT_DELAY * 0.5)
    
    embed_gen.close()
    
    print(f"\n[Step 4] Saving to files...")
    save_to_json(products)
    save_to_csv(products)
    
    print(f"\n[Step 5] Importing to Supabase...")
    importer = SupabaseImporter()
    result = importer.import_products(products)
    
    print("\n" + "="*60)
    print("SCRAPING COMPLETE")
    print(f"Total products: {len(products)}")
    print(f"Imported: {result.get('imported', 0)}")
    print(f"Failed: {result.get('failed', 0)}")
    print("="*60)
    
    return products

def run_incremental():
    print("Running incremental scrape...")
    
    importer = SupabaseImporter()
    existing = importer.check_existing()
    existing_urls = {p.get('product_url') for p in existing if p.get('product_url')}
    
    print(f"Found {len(existing_urls)} existing products")
    
    scraper = BoundScraper()
    product_urls = scraper.scrape_all_product_urls()
    
    new_urls = [url for url in product_urls if url not in existing_urls]
    print(f"Found {len(new_urls)} new products")
    
    if not new_urls:
        print("No new products to scrape")
        return []
    
    detail_scraper = ProductDetailScraper()
    new_products = []
    
    for i, url in enumerate(new_urls, 1):
        print(f"Scraping new product {i}/{len(new_urls)}...")
        product = detail_scraper.scrape_product(url)
        if product:
            new_products.append(product)
        
        time.sleep(config.RATE_LIMIT_DELAY)
    
    if new_products:
        embed_gen = EmbeddingGenerator()
        
        for product in new_products:
            image_url = product.get('image_url')
            if image_url:
                product['image_embedding'] = embed_gen.get_image_embedding(image_url)
        
        for product in new_products:
            info_text = embed_gen.generate_info_text(product)
            if info_text:
                product['info_embedding'] = embed_gen.get_text_embedding(info_text)
        
        embed_gen.close()
        
        importer.import_products(new_products)
    
    return new_products

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Bound Fashion Scraper')
    parser.add_argument('--limit', type=int, default=None, help='Limit number of products to scrape')
    parser.add_argument('--no-cache', action='store_true', help='Ignore cached products and re-scrape')
    parser.add_argument('--incremental', action='store_true', help='Only scrape new products')
    parser.add_argument('--skip-embeddings', action='store_true', help='Skip embedding generation')
    parser.add_argument('--skip-supabase', action='store_true', help='Skip Supabase import')
    
    args = parser.parse_args()
    
    if args.incremental:
        run_incremental()
    else:
        products = run_full_scraper(limit=args.limit, use_cache=not args.no_cache)
        
        if not args.skip_supabase:
            importer = SupabaseImporter()
            importer.import_products(products)

if __name__ == "__main__":
    main()