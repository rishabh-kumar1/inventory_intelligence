#!/usr/bin/env python3
"""
Simple Walmart API authentication handler
"""

import time
import base64
import requests
from typing import Dict, Optional
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.backends import default_backend

class WalmartAuth:
    def __init__(self, consumer_id: str, private_key_path: str):
        self.consumer_id = consumer_id
        self.key_version = "1"

        # Load private key from file
        with open(private_key_path, 'r') as f:
            private_key_content = f.read()

        self.private_key = serialization.load_pem_private_key(
            private_key_content.encode('utf-8'),
            password=None,
            backend=default_backend()
        )

    def get_headers(self, url: str = None, method: str = "GET") -> Dict[str, str]:
        """Generate auth headers for Walmart API"""
        timestamp = str(int(time.time() * 1000))

        # Create canonical string - try original format first:
        # consumer_id + "\n" + timestamp + "\n" + key_version + "\n"
        canonical_string = f"{self.consumer_id}\n{timestamp}\n{self.key_version}\n"

        # Generate signature
        signature = self.private_key.sign(
            canonical_string.encode('utf-8'),
            padding.PKCS1v15(),
            hashes.SHA256()
        )

        return {
            "WM_SEC.KEY_VERSION": self.key_version,
            "WM_CONSUMER.ID": self.consumer_id,
            "WM_CONSUMER.INTIMESTAMP": timestamp,
            "WM_SEC.AUTH_SIGNATURE": base64.b64encode(signature).decode('utf-8'),
            "Accept": "application/json"
        }

    def lookup_product(self, upc: str) -> Optional[Dict]:
        """Lookup product by UPC"""
        try:
            url = "https://developer.api.walmart.com/api-proxy/service/affil/product/v2/items"
            headers = self.get_headers()

            response = requests.get(url, headers=headers, params={"upc": upc}, timeout=10)

            if response.status_code == 200:
                data = response.json()
                if data.get('items'):
                    return data['items'][0]
            else:
                print(f"Walmart API error {response.status_code} for UPC {upc}")
                print(f"Response: {response.text}")

        except Exception as e:
            print(f"Walmart lookup failed for UPC {upc}: {e}")

        return None