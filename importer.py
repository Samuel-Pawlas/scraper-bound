import supabase
import json
from typing import List, Dict, Any, Optional
from datetime import datetime
import time
import logging
import config

logger = logging.getLogger(__name__)

class SupabaseImporter:
    def __init__(self, url: str = None, key: str = None):
        self.url = url or config.SUPABASE_URL
        self.key = key or config.SUPABASE_KEY
        self.client = supabase.create_client(self.url, self.key)
        self.batch_size = 50
        print(f"Connected to Supabase at {self.url}")
    
    def _generate_id(self, product_url: str) -> str:
        url_hash = str(abs(hash(product_url)))[:12]
        return f"bound_{url_hash}"
    
    def _get_existing_products(self, source: str, product_urls: List[str]) -> Dict[str, Dict]:
        """Fetch existing products from database in smaller batches"""
        if not product_urls:
            return {}
        
        existing = {}
        batch_size = 100
        
        for i in range(0, len(product_urls), batch_size):
            batch = product_urls[i:i+batch_size]
            try:
                response = self.client.table('products').select('*').eq('source', source).in_('product_url', batch).execute()
                if hasattr(response, 'data') and response.data:
                    for p in response.data:
                        existing[p['product_url']] = p
            except Exception as e:
                logger.warning(f"Failed to fetch products batch {i//batch_size}: {e}")
        
        return existing
    
    def _has_changed(self, existing: Dict, new: Dict) -> bool:
        """Compare if product has actually changed"""
        fields_to_check = ['title', 'price', 'sale', 'image_url', 'additional_images', 'category', 'description', 'size']
        
        for field in fields_to_check:
            existing_val = existing.get(field)
            new_val = new.get(field)
            
            if existing_val != new_val:
                return True
        
        return False
    
    def _prepare_record(self, product: Dict[str, Any]) -> Dict[str, Any]:
        record = {}
        
        record['id'] = product.get('id') or self._generate_id(product.get('product_url', ''))
        record['source'] = product.get('source', config.SOURCE)
        record['brand'] = product.get('brand', config.BRAND)
        record['product_url'] = product.get('product_url')
        record['title'] = product.get('title', '')
        record['image_url'] = product.get('image_url')
        record['additional_images'] = product.get('additional_images')
        record['category'] = product.get('category')
        record['gender'] = product.get('gender')
        record['price'] = product.get('price')
        record['sale'] = product.get('sale')
        record['description'] = product.get('description')
        record['second_hand'] = product.get('second_hand', False)
        
        metadata = product.get('metadata')
        if metadata:
            if isinstance(metadata, str):
                record['metadata'] = metadata
            else:
                record['metadata'] = json.dumps(metadata)
        
        record['size'] = product.get('size')
        record['country'] = product.get('country')
        record['affiliate_url'] = product.get('affiliate_url')
        record['compressed_image_url'] = product.get('compressed_image_url')
        record['tags'] = product.get('tags')
        
        if product.get('image_embedding'):
            record['image_embedding'] = product['image_embedding']
        
        if product.get('info_embedding'):
            record['info_embedding'] = product['info_embedding']
        
        record['created_at'] = product.get('created_at') or datetime.utcnow().isoformat()
        
        return record
    
    def import_products(self, products: List[Dict[str, Any]], batch_size: int = 50) -> Dict[str, Any]:
        if not products:
            return {'imported': 0, 'updated': 0, 'skipped': 0, 'failed': 0, 'total': 0}
        
        self.batch_size = batch_size
        
        source = config.SOURCE
        product_urls = [p.get('product_url') for p in products if p.get('product_url')]
        
        print(f"Fetching existing products from database...")
        existing_products = self._get_existing_products(source, product_urls)
        print(f"Found {len(existing_products)} existing products")
        
        new_count = 0
        updated_count = 0
        skipped_count = 0
        failed_count = 0
        
        records_to_insert = []
        
        for product in products:
            product_url = product.get('product_url')
            existing = existing_products.get(product_url)
            
            if existing:
                has_changed = self._has_changed(existing, product)
                image_changed = existing.get('image_url') != product.get('image_url')
                
                if not has_changed:
                    skipped_count += 1
                    continue
                
                needs_embedding = image_changed or not existing.get('image_embedding')
                
                if not needs_embedding:
                    product['image_embedding'] = existing.get('image_embedding')
                    product['info_embedding'] = existing.get('info_embedding')
                
                record = self._prepare_record(product)
                records_to_insert.append(record)
                updated_count += 1
            else:
                record = self._prepare_record(product)
                records_to_insert.append(record)
                new_count += 1
        
        if not records_to_insert:
            print(f"No products to insert. All {skipped_count} unchanged.")
            return {
                'imported': 0,
                'updated': 0,
                'skipped': skipped_count,
                'failed': 0,
                'total': len(products)
            }
        
        print(f"Inserting {len(records_to_insert)} products ({new_count} new, {updated_count} updated)...")
        
        inserted_batch = 0
        for i in range(0, len(records_to_insert), batch_size):
            batch = records_to_insert[i:i+batch_size]
            batch_num = i // batch_size + 1
            total_batches = (len(records_to_insert) + batch_size - 1) // batch_size
            
            for retry in range(3):
                try:
                    response = self.client.table('products').upsert(
                        batch, 
                        on_conflict='source,product_url'
                    ).execute()
                    
                    if hasattr(response, 'data') and response.data:
                        inserted_batch += len(batch)
                        print(f"Batch {batch_num}/{total_batches}: inserted {len(batch)} products")
                    break
                    
                except Exception as e:
                    if retry < 2:
                        print(f"Batch {batch_num} failed, retry {retry + 1}/3...")
                        time.sleep(1)
                    else:
                        failed_count += len(batch)
                        print(f"Batch {batch_num} failed after 3 retries: {e}")
                        
                        with open('failed_imports.log', 'a') as f:
                            for record in batch:
                                f.write(f"{datetime.now().isoformat()} - Failed: {record.get('product_url')}\n")
        
        return {
            'imported': new_count,
            'updated': updated_count,
            'skipped': skipped_count,
            'failed': failed_count,
            'total': len(products)
        }
    
    def cleanup_stale_products(self, source: str, seen_urls: List[str]) -> int:
        """Remove products not seen in the current scrape"""
        if not seen_urls:
            return 0
        
        try:
            response = self.client.table('products').select('product_url').eq('source', source).execute()
            all_products = response.data if hasattr(response, 'data') else []
            
            stale_urls = [p['product_url'] for p in all_products if p['product_url'] not in seen_urls]
            
            if stale_urls:
                delete_response = self.client.table('products').delete().eq('source', source).in_('product_url', stale_urls).execute()
                count = len(stale_urls)
                print(f"Cleaned up {count} stale products")
                return count
            
            return 0
            
        except Exception as e:
            logger.warning(f"Failed to cleanup stale products: {e}")
            return 0
    
    def check_existing(self, source: str = None, limit: int = 100) -> List[Dict[str, Any]]:
        source = source or config.SOURCE
        try:
            response = self.client.table('products').select('id, title, product_url').eq('source', source).limit(limit).execute()
            return response.data if hasattr(response, 'data') else []
        except Exception as e:
            logger.warning(f"Failed to check existing products: {e}")
            return []
    
    def count_products(self, source: str = None) -> int:
        source = source or config.SOURCE
        try:
            response = self.client.table('products').select('id', count='exact').eq('source', source).execute()
            return response.count if hasattr(response, 'count') else 0
        except Exception as e:
            logger.warning(f"Failed to count products: {e}")
            return 0