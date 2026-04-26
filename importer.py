import supabase
import json
from typing import List, Dict, Any, Optional
from datetime import datetime
import uuid
import re
import config

class SupabaseImporter:
    def __init__(self, url: str = None, key: str = None):
        self.url = url or config.SUPABASE_URL
        self.key = key or config.SUPABASE_KEY
        self.client = supabase.create_client(self.url, self.key)
        print(f"Connected to Supabase at {self.url}")
    
    def _generate_id(self, product_url: str) -> str:
        url_hash = str(abs(hash(product_url)))[:12]
        return f"bound_{url_hash}"
    
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
        
        image_embedding = product.get('image_embedding')
        if image_embedding:
            if isinstance(image_embedding, list):
                record['image_embedding'] = image_embedding
            else:
                record['image_embedding'] = list(image_embedding)
        
        info_embedding = product.get('info_embedding')
        if info_embedding:
            if isinstance(info_embedding, list):
                record['info_embedding'] = info_embedding
            else:
                record['info_embedding'] = list(info_embedding)
        
        if product.get('created_at'):
            try:
                record['created_at'] = product['created_at']
            except:
                record['created_at'] = datetime.utcnow().isoformat()
        else:
            record['created_at'] = datetime.utcnow().isoformat()
        
        return record
    
    def import_products(self, products: List[Dict[str, Any]], batch_size: int = 50) -> Dict[str, Any]:
        imported = 0
        failed = 0
        errors = []
        
        for i in range(0, len(products), batch_size):
            batch = products[i:i+batch_size]
            print(f"Importing batch {i//batch_size + 1}/{(len(products) + batch_size - 1)//batch_size} ({len(batch)} products)...")
            
            records = []
            for product in batch:
                try:
                    record = self._prepare_record(product)
                    records.append(record)
                except Exception as e:
                    failed += 1
                    errors.append(f"Failed to prepare product {product.get('title')}: {e}")
            
            if not records:
                continue
            
            try:
                response = self.client.table('products').upsert(records, on_conflict='source,product_url').execute()
                
                if hasattr(response, 'data') and response.data:
                    imported += len(records)
                    print(f"Imported {len(records)} products")
                else:
                    imported += len(records)
                    print(f"Batch processed ({len(records)} products)")
            
            except Exception as e:
                failed += len(records)
                errors.append(f"Batch import failed: {e}")
                print(f"Batch failed: {e}")
        
        result = {
            'imported': imported,
            'failed': failed,
            'total': len(products),
            'errors': errors[:10]
        }
        
        print(f"Import complete: {imported} imported, {failed} failed of {len(products)} total")
        return result
    
    def check_existing(self, source: str = config.SOURCE, limit: int = 100) -> List[Dict[str, Any]]:
        try:
            response = self.client.table('products').select('id, title, product_url').eq('source', source).limit(limit).execute()
            return response.data if hasattr(response, 'data') else []
        except Exception as e:
            print(f"Failed to check existing products: {e}")
            return []
    
    def delete_by_source(self, source: str = config.SOURCE) -> int:
        try:
            response = self.client.table('products').delete().eq('source', source).execute()
            return len(response.data) if hasattr(response, 'data') else 0
        except Exception as e:
            print(f"Failed to delete products: {e}")
            return 0
    
    def count_products(self, source: str = config.SOURCE) -> int:
        try:
            response = self.client.table('products').select('id', count='exact').eq('source', source).execute()
            return response.count if hasattr(response, 'count') else 0
        except Exception as e:
            print(f"Failed to count products: {e}")
            return 0