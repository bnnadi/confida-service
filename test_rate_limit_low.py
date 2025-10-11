#!/usr/bin/env python3
"""
Test rate limiting with very low limits for quick testing.
"""
import requests
import time

def test_low_rate_limit():
    base_url = "http://localhost:8000"
    
    print("Testing rate limiting with low limits...")
    print("Making 15 rapid requests to trigger rate limit...")
    
    for i in range(15):
        try:
            response = requests.get(f"{base_url}/", timeout=2)
            print(f"Request {i+1}: Status {response.status_code}")
            if response.status_code == 429:
                print(f"✅ Rate limit triggered! Response: {response.text}")
                return True
        except Exception as e:
            print(f"Request {i+1}: Error - {e}")
        time.sleep(0.1)
    
    print("❌ Rate limit not triggered with 15 requests")
    return False

if __name__ == "__main__":
    test_low_rate_limit()
