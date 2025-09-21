#!/usr/bin/env python3
"""
Inventory Intelligence Analyzer
Categorizes supplier inventory based on retail price comparisons.
"""

import pandas as pd
import requests
import time
import re
from fuzzywuzzy import fuzz
from typing import Dict, Tuple, Optional
import json
import logging
from walmart_auth import WalmartAuth
from product_search_enhancer import ProductSearchEnhancer

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('inventory_analysis.log')
    ]
)
logger = logging.getLogger(__name__)

class InventoryAnalyzer:
    def __init__(self):
        self.retail_price_cache = {}
        self.upc_cache = {}

        # Initialize Walmart API
        try:
            consumer_id = "bf5182d5-de59-4483-8b42-adf0be373047"
            private_key_path = "/Users/rishabh/WM_IO_private_key.pem"
            self.walmart_api = WalmartAuth(consumer_id, private_key_path)
            logger.info("✓ Walmart API initialized successfully")
        except Exception as e:
            logger.warning(f"⚠ Could not initialize Walmart API: {e}")
            self.walmart_api = None

        # Initialize Product Search Enhancer with Walmart fuzzy search
        self.product_searcher = ProductSearchEnhancer(walmart_auth=self.walmart_api)

    def clean_price(self, price_str: str) -> float:
        """Clean and convert price string to float."""
        if pd.isna(price_str) or price_str == '':
            return 0.0
        # Remove $ and commas, convert to float
        cleaned = re.sub(r'[$,]', '', str(price_str))
        try:
            return float(cleaned)
        except ValueError:
            return 0.0

    def lookup_upc_product_info(self, upc: str) -> Optional[Dict]:
        """Lookup product information using UPC via UPCitemdb API."""
        if not upc or pd.isna(upc):
            return None

        if upc in self.upc_cache:
            logger.debug(f"Using cached UPC data for {upc}")
            return self.upc_cache[upc]

        try:
            logger.debug(f"Looking up UPC {upc} via UPCitemdb...")
            # Free UPC lookup API
            url = f"https://api.upcitemdb.com/prod/trial/lookup?upc={upc}"
            headers = {'User-Agent': 'InventoryAnalyzer/1.0'}

            response = requests.get(url, headers=headers, timeout=5)
            if response.status_code == 200:
                data = response.json()
                if data.get('items'):
                    product_info = data['items'][0]
                    self.upc_cache[upc] = product_info
                    logger.debug(f"Found UPC product info for {upc}")
                    return product_info

            # Rate limiting
            time.sleep(0.1)

        except Exception as e:
            logger.debug(f"UPC lookup failed for {upc}: {e}")

        self.upc_cache[upc] = None
        return None

    def get_retail_price(self, product_name: str, upc: str = None) -> Tuple[float, str]:
        """
        Get retail price from UPCitemdb first (which includes Walmart), then fallback to Walmart API
        Returns (price, source_url)
        """
        if not upc:
            logger.debug(f"No UPC provided for {product_name[:50]}...")
            return (0.0, "")

        # First try UPCitemdb (which includes Walmart pricing in offers)
        product_info = self.lookup_upc_product_info(upc)
        if product_info:
            offers = product_info.get('offers', [])

            # Look for Walmart pricing first
            for offer in offers:
                if offer.get('domain') == 'walmart.com' and offer.get('price', 0) > 0:
                    price = float(offer['price'])
                    url = offer.get('link', f"https://walmart.com/upc/{upc}")
                    logger.info(f"Found Walmart price via UPCitemdb for UPC {upc}: ${price}")
                    return (price, url)

            # If no Walmart offer, use any other retailer as fallback
            for offer in offers:
                if offer.get('price', 0) > 0:
                    price = float(offer['price'])
                    url = offer.get('link', '')
                    merchant = offer.get('merchant', 'Unknown')
                    logger.info(f"Found {merchant} price via UPCitemdb for UPC {upc}: ${price}")
                    return (price, url)

        # Fallback to direct Walmart API if UPCitemdb didn't have pricing
        if self.walmart_api:
            try:
                logger.debug(f"Fallback: Querying Walmart API directly for UPC {upc}")
                walmart_product = self.walmart_api.lookup_product(upc)
                if walmart_product and walmart_product.get('salePrice', 0) > 0:
                    price = float(walmart_product['salePrice'])
                    # Create direct Walmart product URL instead of broken affiliate link
                    item_id = walmart_product.get('itemId')
                    if item_id:
                        url = f"https://walmart.com/ip/{item_id}"
                    else:
                        url = f"https://walmart.com/search?q={upc}"
                    logger.info(f"Found Walmart price via direct API for UPC {upc}: ${price}")
                    return (price, url)
                else:
                    logger.debug(f"No price found on Walmart direct API for UPC {upc}")
            except Exception as e:
                logger.warning(f"Walmart API error for UPC {upc}: {e}")

        # No price found, but try to get a working link from UPCitemdb
        if 'product_info' not in locals() or not product_info:
            product_info = self.lookup_upc_product_info(upc)

        if product_info:
            offers = product_info.get('offers', [])
            # Prefer Walmart link if available
            for offer in offers:
                if offer.get('domain') == 'walmart.com' and offer.get('link'):
                    logger.debug(f"Using UPCitemdb Walmart link for UPC {upc} (no price)")
                    return (0.0, offer['link'])
            # Otherwise use any available link
            for offer in offers:
                if offer.get('link'):
                    merchant = offer.get('merchant', 'Unknown')
                    logger.debug(f"Using UPCitemdb {merchant} link for UPC {upc} (no price)")
                    return (0.0, offer['link'])

        # NEW: Try fuzzy search as final fallback when UPC methods fail
        logger.debug(f"Trying fuzzy search fallback for: {product_name[:50]}...")
        fuzzy_price, fuzzy_url = self.product_searcher.search_product_price(product_name)
        if fuzzy_price > 0:
            logger.info(f"🔍 Found fuzzy match: ${fuzzy_price:.2f} for '{product_name[:30]}...'")
            return (fuzzy_price, fuzzy_url)

        logger.debug(f"No retail price or link found for {product_name[:50]}...")
        return (0.0, "")

    def calculate_discount_percentage(self, supplier_price: float, retail_price: float) -> float:
        """Calculate discount percentage: (retail - supplier) / retail * 100"""
        if retail_price <= 0:
            return 0.0
        return ((retail_price - supplier_price) / retail_price) * 100

    def categorize_price(self, discount_percentage: float, retail_price: float) -> str:
        """Categorize price based on discount thresholds."""
        if retail_price <= 0:
            return "No Price Found"
        elif discount_percentage >= 75:
            return "Good Price"
        elif discount_percentage >= 60:
            return "Okay Price"
        else:
            return "Bad Price"

    def analyze_inventory(self, csv_file: str) -> pd.DataFrame:
        """Main analysis function."""
        logger.info("Starting inventory analysis...")
        logger.info(f"Loading inventory data from {csv_file}")
        df = pd.read_csv(csv_file)
        total_items = len(df)
        logger.info(f"Loaded {total_items} inventory items")

        # Clean supplier prices
        logger.info("Cleaning supplier price data...")
        df['Supplier_Price'] = df['Default Price'].apply(self.clean_price)

        # Initialize new columns
        df['Market_Comp'] = ''
        df['Retail_Price'] = 0.0
        df['Discount_Percentage'] = 0.0
        df['Price_Category'] = ''

        logger.info(f"Beginning analysis of {total_items} items...")

        # Tracking counters
        walmart_found = 0
        upc_found = 0
        no_price_found = 0

        for index, row in df.iterrows():
            item_id = row['Inventory ID']
            progress_pct = ((index + 1) / total_items) * 100

            logger.info(f"[{index + 1}/{total_items}] ({progress_pct:.1f}%) Processing {item_id}")

            # First try UPC lookup for exact product match
            upc = str(row['ITEM UPC']).strip() if pd.notna(row['ITEM UPC']) else None
            if upc and upc != 'nan':
                upc = upc.rstrip('.0')
            product_info = None

            if upc and upc != 'nan':
                logger.debug(f"UPC available: {upc}")
                product_info = self.lookup_upc_product_info(upc)
                if product_info:
                    upc_found += 1

            # Get retail price from Walmart API
            retail_price, market_url = self.get_retail_price(row['Description'], upc)

            if retail_price > 0:
                walmart_found += 1
            else:
                no_price_found += 1

            # Calculate discount and categorize
            supplier_price = row['Supplier_Price']
            discount_pct = self.calculate_discount_percentage(supplier_price, retail_price)
            category = self.categorize_price(discount_pct, retail_price)

            logger.debug(f"💵 Supplier: ${supplier_price:.2f} | Retail: ${retail_price:.2f} | Discount: {discount_pct:.1f}% | Category: {category}")

            # Update dataframe
            df.at[index, 'Market_Comp'] = market_url
            df.at[index, 'Retail_Price'] = retail_price
            df.at[index, 'Discount_Percentage'] = round(discount_pct, 1)
            df.at[index, 'Price_Category'] = category

            # Progress update every 10 items
            if (index + 1) % 10 == 0:
                logger.info(f"Progress: {index + 1}/{total_items} ({progress_pct:.1f}%) - Walmart matches: {walmart_found}")

            # Rate limiting for API calls
            time.sleep(0.05)

        # Final statistics
        logger.info("Analysis complete!")
        logger.info(f"Final Statistics:")
        logger.info(f"   • Total items processed: {total_items}")
        logger.info(f"   • UPC matches found: {upc_found}")
        logger.info(f"   • Walmart prices found: {walmart_found}")
        logger.info(f"   • No prices found: {no_price_found}")
        logger.info(f"   • Success rate: {(walmart_found/total_items)*100:.1f}%")
        
        # Enhanced search statistics
        if hasattr(self, 'product_searcher'):
            search_stats = self.product_searcher.get_cache_stats()
            if search_stats['total_searches'] > 0:
                logger.info(f"   • Fuzzy search attempts: {search_stats['total_searches']}")
                logger.info(f"   • Fuzzy search hits: {search_stats['cache_hits']}")
                logger.info(f"   • Fuzzy search hit rate: {search_stats['hit_rate']*100:.1f}%")

        return df

    def generate_report(self, df: pd.DataFrame) -> None:
        """Generate summary report."""
        logger.info("Generating analysis report...")

        total_items = len(df)
        good_items = len(df[df['Price_Category'] == 'Good Price'])
        okay_items = len(df[df['Price_Category'] == 'Okay Price'])
        bad_items = len(df[df['Price_Category'] == 'Bad Price'])
        no_price_items = len(df[df['Price_Category'] == 'No Price Found'])

        print("\n" + "="*60)
        print("INVENTORY ANALYSIS REPORT")
        print("="*60)
        print(f"Total Items Analyzed: {total_items}")
        print(f"Good Price (>75% off): {good_items} ({good_items/total_items*100:.1f}%)")
        print(f"Okay Price (60-75% off): {okay_items} ({okay_items/total_items*100:.1f}%)")
        print(f"Bad Price (<60% off): {bad_items} ({bad_items/total_items*100:.1f}%)")
        print(f"No Price Found: {no_price_items} ({no_price_items/total_items*100:.1f}%)")

        logger.info(f"Report Summary - Good: {good_items}, Okay: {okay_items}, Bad: {bad_items}, No Price: {no_price_items}")

        print("\nTop 10 Best Deals (Highest Discount %):")
        top_deals = df.nlargest(10, 'Discount_Percentage')[['Inventory ID', 'Description', 'Supplier_Price', 'Retail_Price', 'Discount_Percentage', 'Price_Category']]
        for _, item in top_deals.iterrows():
            print(f"  {item['Inventory ID']}: {item['Discount_Percentage']:.1f}% off - {item['Price_Category']}")

        print("\nWorst Deals (Lowest Discount % - excluding items with no price):")
        # Filter out items with no price found for worst deals calculation
        priced_items = df[df['Price_Category'] != 'No Price Found']
        if len(priced_items) > 0:
            worst_deals = priced_items.nsmallest(5, 'Discount_Percentage')[['Inventory ID', 'Description', 'Supplier_Price', 'Retail_Price', 'Discount_Percentage', 'Price_Category']]
            for _, item in worst_deals.iterrows():
                print(f"  {item['Inventory ID']}: {item['Discount_Percentage']:.1f}% off - {item['Price_Category']}")
        else:
            print("  No priced items available for comparison")

def main():
    logger.info("Starting Inventory Intelligence Analyzer")
    logger.info("🚀 Enhanced mode: UPC + Walmart API + Fuzzy Search enabled")
    
    analyzer = InventoryAnalyzer()

    # Analyze inventory
    logger.info("Beginning inventory analysis...")
    df = analyzer.analyze_inventory('inventory_data.csv')

    # Generate report
    analyzer.generate_report(df)

    # Save results
    logger.info("Saving results to CSV...")
    output_columns = [
        'Inventory ID', 'Description', 'Qty. Available', 'ITEM UPC',
        'Default Price', 'Supplier_Price', 'Market_Comp', 'Retail_Price',
        'Discount_Percentage', 'Price_Category'
    ]

    output_df = df[output_columns]
    output_df.to_csv('inventory_analysis_results.csv', index=False)
    logger.info("Results saved to: inventory_analysis_results.csv")
    logger.info("Analysis complete! Check inventory_analysis.log for detailed logs.")

if __name__ == "__main__":
    main()