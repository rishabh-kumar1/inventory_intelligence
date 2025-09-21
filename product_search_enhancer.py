#!/usr/bin/env python3
"""
Product Search Enhancer
Provides fuzzy product name matching using Walmart Search API.
"""

import requests
import time
import re
from typing import Dict, Tuple, Optional
import logging
from walmart_auth import WalmartAuth

logger = logging.getLogger(__name__)

class ProductSearchEnhancer:
    def __init__(self, walmart_auth: WalmartAuth = None):
        self.walmart_auth = walmart_auth
        self.search_cache = {}
        
        # Rate limiting
        self.last_walmart_call = 0
        self.walmart_delay = 0.2  # 5 requests per second max
        
        logger.info("ProductSearchEnhancer initialized")
        if walmart_auth:
            logger.info("Walmart Search enabled")

    def clean_product_name(self, product_name: str) -> str:
        """Clean product name for better search results."""
        if not product_name:
            return ""
        
        # Remove common suffixes that might hurt search
        cleaned = re.sub(r'\s+(BEST BY|BB|EXP|EXPIRES).*', '', product_name, flags=re.IGNORECASE)
        cleaned = re.sub(r'\s+\d+/\d+/\d+.*', '', cleaned)  # Remove dates
        cleaned = re.sub(r'\s+\d+CT\s*', ' ', cleaned, flags=re.IGNORECASE)  # Remove count
        cleaned = re.sub(r'\s+\d+(\.\d+)?oz\s*', ' ', cleaned, flags=re.IGNORECASE)  # Keep size but clean
        
        # Clean up extra spaces
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()
        
        return cleaned[:100]  # Limit length for API calls



    def search_walmart_products(self, product_name: str) -> Tuple[float, str]:
        """Search Walmart products using extended Walmart API."""
        if not self.walmart_auth:
            return (0.0, "")
            
        # Rate limiting
        time_since_last = time.time() - self.last_walmart_call
        if time_since_last < self.walmart_delay:
            time.sleep(self.walmart_delay - time_since_last)
        
        cleaned_name = self.clean_product_name(product_name)
        cache_key = f"walmart_{cleaned_name}"
        
        if cache_key in self.search_cache:
            logger.debug(f"Using cached Walmart search result for: {cleaned_name[:30]}...")
            return self.search_cache[cache_key]
        
        try:
            logger.debug(f"Searching Walmart for: {cleaned_name}")
            
            # Use Walmart Search API endpoint
            url = "https://developer.api.walmart.com/api-proxy/service/affil/product/v2/search"
            headers = self.walmart_auth.get_headers()
            
            params = {
                'query': cleaned_name,
                'numItems': 5,
                'format': 'json'
            }
            
            response = requests.get(url, headers=headers, params=params, timeout=10)
            self.last_walmart_call = time.time()
            
            if response.status_code == 200:
                data = response.json()
                items = data.get('items', [])
                
                if items:
                    # Find best match by name similarity and reasonable price
                    best_match = None
                    best_score = 0
                    
                    for item in items:
                        price = item.get('salePrice', 0)
                        name = item.get('name', '').lower()
                        item_id = item.get('itemId')
                        
                        if price > 0:
                            # Simple similarity scoring
                            cleaned_lower = cleaned_name.lower()
                            words_in_search = set(cleaned_lower.split())
                            words_in_result = set(name.split())
                            
                            # Calculate word overlap score
                            common_words = words_in_search.intersection(words_in_result)
                            score = len(common_words) / max(len(words_in_search), 1)
                            
                            if score > best_score and score > 0.3:  # At least 30% word overlap
                                best_score = score
                                url = f"https://walmart.com/ip/{item_id}" if item_id else "https://walmart.com"
                                best_match = (float(price), url)
                    
                    if best_match:
                        self.search_cache[cache_key] = best_match
                        logger.info(f"Found Walmart search match: ${best_match[0]:.2f} for '{cleaned_name[:30]}...' (score: {best_score:.2f})")
                        return best_match
                
                logger.debug(f"No Walmart search results for: {cleaned_name}")
            else:
                logger.debug(f"Walmart search API error {response.status_code} for: {cleaned_name}")
                
        except Exception as e:
            logger.warning(f"Walmart search failed for '{cleaned_name}': {e}")
        
        # Cache negative result
        self.search_cache[cache_key] = (0.0, "")
        return (0.0, "")

    def search_product_price(self, product_name: str, supplier_price: float = None) -> Tuple[float, str]:
        """
        Main search method: uses Walmart search for fuzzy product matching.
        Returns (price, source_url)
        """
        if not product_name or not product_name.strip():
            return (0.0, "")
        
        logger.debug(f"Starting fuzzy search for: {product_name[:50]}...")
        
        # Try Walmart search
        price, url = self.search_walmart_products(product_name)
        if price > 0:
            return (price, url)
        
        logger.debug(f"No fuzzy match found for: {product_name[:50]}...")
        return (0.0, "")

    def get_cache_stats(self) -> Dict:
        """Return cache statistics for monitoring."""
        total = len(self.search_cache)
        hits = sum(1 for v in self.search_cache.values() if v[0] > 0)
        misses = total - hits
        
        return {
            'total_searches': total,
            'cache_hits': hits,
            'cache_misses': misses,
            'hit_rate': hits / total if total > 0 else 0
        } 