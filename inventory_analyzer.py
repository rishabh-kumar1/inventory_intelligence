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

class InventoryAnalyzer:
    def __init__(self):
        self.retail_price_cache = {}
        self.upc_cache = {}

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
            return self.upc_cache[upc]

        try:
            # Free UPC lookup API
            url = f"https://api.upcitemdb.com/prod/trial/lookup?upc={upc}"
            headers = {'User-Agent': 'InventoryAnalyzer/1.0'}

            response = requests.get(url, headers=headers, timeout=5)
            if response.status_code == 200:
                data = response.json()
                if data.get('items'):
                    product_info = data['items'][0]
                    self.upc_cache[upc] = product_info
                    return product_info

            # Rate limiting
            time.sleep(0.1)

        except Exception as e:
            print(f"UPC lookup failed for {upc}: {e}")

        self.upc_cache[upc] = None
        return None

    def get_mock_retail_price(self, product_name: str, upc: str = None) -> Tuple[float, str]:
        """
        Mock retail price lookup - in production this would hit Walmart/Target APIs.
        Returns (price, source_url)
        """
        # Create realistic mock prices based on product type and description
        product_lower = product_name.lower()

        # Extract brand and product type for realistic pricing
        if 'cheez' in product_lower and 'it' in product_lower:
            return (4.49, "https://walmart.com/ip/mock-cheez-it")
        elif 'pop' in product_lower and 'tart' in product_lower:
            return (3.98, "https://walmart.com/ip/mock-pop-tarts")
        elif 'halls' in product_lower:
            return (2.97, "https://walmart.com/ip/mock-halls")
        elif 'mccormick' in product_lower:
            if 'extract' in product_lower:
                return (5.47, "https://walmart.com/ip/mock-mccormick-extract")
            else:
                return (1.98, "https://walmart.com/ip/mock-mccormick-spice")
        elif 'allrecipes' in product_lower:
            return (1.97, "https://walmart.com/ip/mock-allrecipes-spice")
        elif 'knorr' in product_lower:
            return (2.48, "https://walmart.com/ip/mock-knorr")
        elif 'kool' in product_lower and 'aid' in product_lower:
            return (1.87, "https://walmart.com/ip/mock-kool-aid")
        elif 'tootsie' in product_lower:
            return (2.99, "https://walmart.com/ip/mock-tootsie")
        elif 'sour patch' in product_lower:
            return (3.47, "https://walmart.com/ip/mock-sour-patch")
        elif 'swedish fish' in product_lower:
            return (3.47, "https://walmart.com/ip/mock-swedish-fish")
        elif 'love corn' in product_lower:
            return (8.97, "https://walmart.com/ip/mock-love-corn")
        elif 'nutri' in product_lower and 'grain' in product_lower:
            return (4.98, "https://walmart.com/ip/mock-nutri-grain")
        elif 'jose cuervo' in product_lower:
            return (4.97, "https://walmart.com/ip/mock-jose-cuervo")
        elif 'french' in product_lower and 'ketchup' in product_lower:
            return (6.98, "https://walmart.com/ip/mock-frenchs-ketchup")
        elif 'kamenstein' in product_lower:
            if 'grinder' in product_lower:
                return (24.97, "https://walmart.com/ip/mock-kamenstein-grinder")
            else:
                return (12.97, "https://walmart.com/ip/mock-kamenstein")
        elif 'frankford' in product_lower or 'elf on' in product_lower:
            return (1.97, "https://walmart.com/ip/mock-hot-chocolate")
        elif 'transformers' in product_lower:
            return (2.97, "https://walmart.com/ip/mock-transformers-sauce")
        elif 'zatarain' in product_lower:
            return (1.87, "https://walmart.com/ip/mock-zatarains")
        else:
            # Default pricing based on supplier price
            supplier_price = self.extract_price_from_description(product_name)
            if supplier_price > 0:
                # Estimate retail price as 3-5x supplier price
                return (supplier_price * 4, "https://walmart.com/ip/mock-generic")
            else:
                return (2.97, "https://walmart.com/ip/mock-generic")

    def extract_price_from_description(self, description: str) -> float:
        """Extract price hints from product description."""
        # Look for price patterns in description (this is a fallback)
        price_match = re.search(r'\$(\d+\.?\d*)', description)
        if price_match:
            return float(price_match.group(1))
        return 0.0

    def calculate_discount_percentage(self, supplier_price: float, retail_price: float) -> float:
        """Calculate discount percentage: (retail - supplier) / retail * 100"""
        if retail_price <= 0:
            return 0.0
        return ((retail_price - supplier_price) / retail_price) * 100

    def categorize_price(self, discount_percentage: float) -> str:
        """Categorize price based on discount thresholds."""
        if discount_percentage >= 75:
            return "Good Price"
        elif discount_percentage >= 60:
            return "Okay Price"
        else:
            return "Bad Price"

    def analyze_inventory(self, csv_file: str) -> pd.DataFrame:
        """Main analysis function."""
        print("Loading inventory data...")
        df = pd.read_csv(csv_file)

        # Clean supplier prices
        df['Supplier_Price'] = df['Default Price'].apply(self.clean_price)

        # Initialize new columns
        df['Market_Comp'] = ''
        df['Retail_Price'] = 0.0
        df['Discount_Percentage'] = 0.0
        df['Price_Category'] = ''

        print(f"Analyzing {len(df)} inventory items...")

        for index, row in df.iterrows():
            print(f"Processing item {index + 1}/{len(df)}: {row['Inventory ID']}")

            # First try UPC lookup for exact product match
            upc = str(row['ITEM UPC']).strip() if pd.notna(row['ITEM UPC']) else None
            product_info = None

            if upc and upc != 'nan':
                product_info = self.lookup_upc_product_info(upc)

            # Get retail price (mock for demo)
            retail_price, market_url = self.get_mock_retail_price(row['Description'], upc)

            # Calculate discount and categorize
            supplier_price = row['Supplier_Price']
            discount_pct = self.calculate_discount_percentage(supplier_price, retail_price)
            category = self.categorize_price(discount_pct)

            # Update dataframe
            df.at[index, 'Market_Comp'] = market_url
            df.at[index, 'Retail_Price'] = retail_price
            df.at[index, 'Discount_Percentage'] = round(discount_pct, 1)
            df.at[index, 'Price_Category'] = category

            # Rate limiting for API calls
            time.sleep(0.05)

        return df

    def generate_report(self, df: pd.DataFrame) -> None:
        """Generate summary report."""
        print("\n" + "="*60)
        print("INVENTORY ANALYSIS REPORT")
        print("="*60)

        total_items = len(df)
        good_items = len(df[df['Price_Category'] == 'Good Price'])
        okay_items = len(df[df['Price_Category'] == 'Okay Price'])
        bad_items = len(df[df['Price_Category'] == 'Bad Price'])

        print(f"Total Items Analyzed: {total_items}")
        print(f"Good Price (>75% off): {good_items} ({good_items/total_items*100:.1f}%)")
        print(f"Okay Price (60-75% off): {okay_items} ({okay_items/total_items*100:.1f}%)")
        print(f"Bad Price (<60% off): {bad_items} ({bad_items/total_items*100:.1f}%)")

        print("\nTop 10 Best Deals (Highest Discount %):")
        top_deals = df.nlargest(10, 'Discount_Percentage')[['Inventory ID', 'Description', 'Supplier_Price', 'Retail_Price', 'Discount_Percentage', 'Price_Category']]
        for _, item in top_deals.iterrows():
            print(f"  {item['Inventory ID']}: {item['Discount_Percentage']:.1f}% off - {item['Price_Category']}")

        print("\nWorst Deals (Lowest Discount %):")
        worst_deals = df.nsmallest(5, 'Discount_Percentage')[['Inventory ID', 'Description', 'Supplier_Price', 'Retail_Price', 'Discount_Percentage', 'Price_Category']]
        for _, item in worst_deals.iterrows():
            print(f"  {item['Inventory ID']}: {item['Discount_Percentage']:.1f}% off - {item['Price_Category']}")

def main():
    analyzer = InventoryAnalyzer()

    # Analyze inventory
    df = analyzer.analyze_inventory('inventory_data.csv')

    # Generate report
    analyzer.generate_report(df)

    # Save results
    output_columns = [
        'Inventory ID', 'Description', 'Qty. Available', 'ITEM UPC',
        'Default Price', 'Supplier_Price', 'Market_Comp', 'Retail_Price',
        'Discount_Percentage', 'Price_Category'
    ]

    output_df = df[output_columns]
    output_df.to_csv('inventory_analysis_results.csv', index=False)
    print(f"\nResults saved to: inventory_analysis_results.csv")

if __name__ == "__main__":
    main()