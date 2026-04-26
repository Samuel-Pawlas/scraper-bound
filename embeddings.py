import torch
import numpy as np
from PIL import Image
from io import BytesIO
import requests
from typing import List, Optional
import config

class EmbeddingGenerator:
    def __init__(self, model_name: str = config.EMBEDDING_MODEL):
        self.model_name = model_name
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.processor = None
        self.model = None
        self._load_model()
    
    def _load_model(self):
        print(f"Loading {self.model_name}...")
        from transformers import AutoProcessor, AutoModel
        
        self.processor = AutoProcessor.from_pretrained(self.model_name)
        self.model = AutoModel.from_pretrained(self.model_name)
        self.model.to(self.device)
        self.model.eval()
        print(f"Model loaded on {self.device}")
    
    def _load_image_from_url(self, url: str) -> Optional[Image.Image]:
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            }
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            return Image.open(BytesIO(response.content)).convert('RGB')
        except Exception as e:
            print(f"Failed to load image from {url}: {e}")
            return None
    
    def _mean_pooling(self, model_output, attention_mask):
        token_embeddings = model_output
        input_mask_expanded = attention_mask.unsqueeze(-1).expand(token_embeddings.size()).float()
        return torch.sum(token_embeddings * input_mask_expanded, 1) / torch.clamp(input_mask_expanded.sum(1), min=1e-9)
    
    def get_image_embedding(self, image_url: str) -> Optional[List[float]]:
        image = self._load_image_from_url(image_url)
        if image is None:
            return None
        
        try:
            inputs = self.processor(images=image, return_tensors="pt")
            inputs = {k: v.to(self.device) for k, v in inputs.items()}
            
            with torch.no_grad():
                outputs = self.model.get_image_features(**inputs)
                if hasattr(outputs, 'pooler_output'):
                    embedding = outputs.pooler_output
                elif hasattr(outputs, 'last_hidden_state'):
                    embedding = outputs.last_hidden_state
                else:
                    embedding = outputs.logits if hasattr(outputs, 'logits') else outputs
            
            if len(embedding.shape) == 0:
                return None
            
            if embedding.shape[0] == 1:
                embedding = embedding[0]
            
            if len(embedding.shape) > 1:
                embedding = embedding.mean(dim=1)
            
            return embedding.cpu().numpy().tolist()
        
        except Exception as e:
            print(f"Failed to generate image embedding: {e}")
            return None
    
    def get_text_embedding(self, text: str) -> Optional[List[float]]:
        try:
            inputs = self.processor(text=text, return_tensors="pt")
            inputs = {k: v.to(self.device) for k, v in inputs.items()}
            
            with torch.no_grad():
                outputs = self.model.get_text_features(**inputs)
                if hasattr(outputs, 'pooler_output'):
                    embedding = outputs.pooler_output
                elif hasattr(outputs, 'last_hidden_state'):
                    embedding = outputs.last_hidden_state
                else:
                    embedding = outputs.logits if hasattr(outputs, 'logits') else outputs
            
            if len(embedding.shape) == 0:
                return None
            
            if embedding.shape[0] == 1:
                embedding = embedding[0]
            
            return embedding.cpu().numpy().tolist()
        
        except Exception as e:
            print(f"Failed to generate text embedding: {e}")
            return None
    
    def get_image_embeddings_batch(self, image_urls: List[str], batch_size: int = 8) -> List[Optional[List[float]]]:
        embeddings = []
        
        for i in range(0, len(image_urls), batch_size):
            batch = image_urls[i:i+batch_size]
            print(f"Processing batch {i//batch_size + 1}/{(len(image_urls) + batch_size - 1)//batch_size}...")
            
            for url in batch:
                emb = self.get_image_embedding(url)
                embeddings.append(emb)
        
        return embeddings
    
    def generate_info_text(self, product: dict) -> str:
        parts = []
        
        title = product.get('title', '')
        if title:
            title = title[:50]
        
        parts.extend([
            title,
            product.get('brand', ''),
            product.get('category', ''),
            product.get('gender', ''),
            product.get('price', ''),
            product.get('sale', ''),
        ])
        
        metadata = product.get('metadata')
        if metadata:
            try:
                import json
                meta = json.loads(metadata) if isinstance(metadata, str) else metadata
                
                sizes = meta.get('sizes', [])
                if sizes:
                    sizes_str = ', '.join(sizes[:5])
                    parts.append(f"sizes: {sizes_str}")
                
                colors = meta.get('colors', [])
                if colors:
                    colors_str = ', '.join(colors[:5])
                    parts.append(f"colors: {colors_str}")
                
                description = meta.get('description', '')
                if description:
                    parts.append(description[:80])
            except:
                pass
        
        text = ' | '.join(filter(None, parts))
        text = text[:150]
        
        return text
    
    def close(self):
        if self.model:
            del self.model
        if self.processor:
            del self.processor
        
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        
        print("Model unloaded")