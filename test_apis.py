#!/usr/bin/env python3
"""
Test script to debug Walmart and UPCitemdb API responses for specific UPCs
"""

import requests
import json
from walmart_auth import WalmartAuth

def test_upcitemdb(upc):
    """Test UPCitemdb API for a specific UPC"""
    print(f"\nTesting UPCitemdb API for UPC: {upc}")

    try:
        url = f"https://api.upcitemdb.com/prod/trial/lookup?upc={upc}"
        headers = {'User-Agent': 'InventoryAnalyzer/1.0'}

        response = requests.get(url, headers=headers, timeout=10)
        print(f"Status Code: {response.status_code}")
        print(f"Response Headers: {dict(response.headers)}")

        if response.status_code == 200:
            data = response.json()
            print(f"Response Data: {json.dumps(data, indent=2)}")

            if data.get('items'):
                item = data['items'][0]
                print(f"Found product: {item.get('title', 'No title')}")
                print(f"   Brand: {item.get('brand', 'No brand')}")
                print(f"   Description: {item.get('description', 'No description')}")
            else:
                print("No items found in response")
        else:
            print(f"Error response: {response.text}")

    except Exception as e:
        print(f"UPCitemdb API error: {e}")

def test_walmart_api(upc):
    """Test Walmart API for a specific UPC"""
    print(f"\nTesting Walmart API for UPC: {upc}")

    try:
        consumer_id = "bf5182d5-de59-4483-8b42-adf0be373047"
        private_key_path = "/Users/rishabh/WM_IO_private_key.pem"

        walmart_api = WalmartAuth(consumer_id, private_key_path)
        print("Walmart API initialized successfully")

        # Test the product lookup
        result = walmart_api.lookup_product(upc)

        if result:
            print(f"Found Walmart product!")
            print(f"Response Data: {json.dumps(result, indent=2)}")

            print(f"\nKey Fields:")
            print(f"   Name: {result.get('name', 'No name')}")
            print(f"   Sale Price: ${result.get('salePrice', 'No price')}")
            print(f"   MSRP: ${result.get('msrp', 'No MSRP')}")
            print(f"   Brand: {result.get('brandName', 'No brand')}")
            print(f"   Stock: {result.get('stock', 'Unknown')}")
            print(f"   URL: {result.get('productTrackingUrl', 'No URL')}")
        else:
            print("No product found on Walmart")

    except Exception as e:
        print(f"Walmart API error: {e}")

def main():
    # Test with some UPCs from our inventory data
    test_upcs = [
        "83933263155",   # KOOL-AID SOUR BELTS
        "48001711044",   # KNORR MEXICAN CHICKEN BOUILLON
        "312546005747",  # HALLS RELIEF 2PACK
        "24100116669",   # CHEEZ-IT DOUBLE CHEESE
        "38000221675",   # POP-TARTS CHOCOLATE CHIP
    ]

    print("API Testing Script")
    print("=" * 50)

    for upc in test_upcs:
        print(f"\n{'='*60}")
        print(f"TESTING UPC: {upc}")
        print('='*60)

        # Test both APIs
        test_upcitemdb(upc)
        test_walmart_api(upc)

        print("\n" + "-"*60)

if __name__ == "__main__":
    main()