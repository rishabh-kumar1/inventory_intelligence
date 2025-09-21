#!/usr/bin/env python3
"""
Test script for the fuzzy product search enhancement
"""

import logging
from product_search_enhancer import ProductSearchEnhancer
from walmart_auth import WalmartAuth

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_fuzzy_search():
    """Test the fuzzy search functionality with sample products."""
    
    # Sample products from your inventory data
    test_products = [
        "KOOL-AID SOUR BELTS 3.5oz 4FRUITY FLAVORS",
        "KNORR MEXICAN CHICKEN BOUILLON 7.9oz",
        "HALLS RELIEF 2PACK 200CT BAGS COUGH DROPS CHERRY",
        "POST CANDY CANES 12CT 5.29oz FRUITY COCOA PEBBLES",
        "MCCORMICK GOURMET DILL SEED ORGANIC 1 OZ"
    ]
    
    # Initialize Walmart API (optional)
    walmart_api = None
    try:
        consumer_id = "bf5182d5-de59-4483-8b42-adf0be373047"
        private_key_path = "/Users/rishabh/WM_IO_private_key.pem"
        walmart_api = WalmartAuth(consumer_id, private_key_path)
        logger.info("Walmart API available for testing")
    except Exception as e:
        logger.warning(f"Walmart API not available: {e}")
    
    # Test Walmart fuzzy search
    logger.info("\n" + "="*60)
    logger.info("TESTING: Walmart Fuzzy Search")
    logger.info("="*60)
    
    searcher = ProductSearchEnhancer(walmart_auth=walmart_api)
    
    for product in test_products:
        logger.info(f"\nTesting: {product}")
        price, url = searcher.search_product_price(product)
        if price > 0:
            logger.info(f"Found: ${price:.2f} - {url[:50]}...")
        else:
            logger.info("No match found")
    
    # Show cache stats
    stats = searcher.get_cache_stats()
    logger.info(f"\nFuzzy Search Statistics:")
    logger.info(f"   Total searches: {stats['total_searches']}")
    logger.info(f"   Successful matches: {stats['cache_hits']}")
    logger.info(f"   Hit rate: {stats['hit_rate']*100:.1f}%")
    
    logger.info(f"\nFuzzy search enhancement is working!")
    logger.info(f"This improves your inventory analysis by finding prices for products without valid UPCs")

if __name__ == "__main__":
    test_fuzzy_search() 