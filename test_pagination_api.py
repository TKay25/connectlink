#!/usr/bin/env python3
"""
Test script for pagination API endpoints
Run after starting the Flask app
"""

import requests
import json
from pprint import pprint

BASE_URL = "http://localhost:5000"

def test_pagination_endpoints():
    """Test all pagination endpoints"""
    
    print("=" * 80)
    print("Testing Pagination API Endpoints")
    print("=" * 80)
    
    endpoints = [
        ('/api/projects/paginated', 'Projects'),
        ('/api/enquiries/paginated', 'Enquiries'),
        ('/api/users/paginated', 'Users'),
        ('/api/admins/paginated', 'Admins'),
    ]
    
    for endpoint, name in endpoints:
        print(f"\n{'='*80}")
        print(f"Testing: {name} ({endpoint})")
        print(f"{'='*80}")
        
        url = f"{BASE_URL}{endpoint}?page=1"
        
        try:
            response = requests.get(url, timeout=10)
            print(f"✅ HTTP Status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Response format: valid JSON")
                print(f"   - Status: {data.get('status')}")
                print(f"   - Page: {data.get('page')}")
                print(f"   - Per page: {data.get('per_page')}")
                print(f"   - Total: {data.get('total')}")
                print(f"   - Total pages: {data.get('total_pages')}")
                print(f"   - Records returned: {len(data.get('data', []))}")
                
                if data.get('data'):
                    print(f"   - Sample record keys: {list(data['data'][0].keys())}")
                    print(f"   ✅ First record preview:")
                    for key in list(data['data'][0].keys())[:3]:
                        val = data['data'][0][key]
                        if isinstance(val, str) and len(val) > 50:
                            print(f"      {key}: {val[:50]}...")
                        else:
                            print(f"      {key}: {val}")
            else:
                print(f"❌ Unexpected status: {response.status_code}")
                print(response.text[:500])
                
        except requests.ConnectionError:
            print(f"❌ Connection error - is Flask running on {BASE_URL}?")
        except Exception as e:
            print(f"❌ Error: {str(e)}")
    
    # Test with search parameter
    print(f"\n{'='*80}")
    print(f"Testing: Search functionality")
    print(f"{'='*80}")
    
    search_tests = [
        ('/api/projects/paginated', 'Projects', 'search=kitchen'),
        ('/api/enquiries/paginated', 'Enquiries', 'search=test'),
        ('/api/users/paginated', 'Users', 'search=admin'),
    ]
    
    for endpoint, name, query in search_tests:
        print(f"\n{name} with {query}:")
        url = f"{BASE_URL}{endpoint}?page=1&{query}"
        
        try:
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                data = response.json()
                print(f"   ✅ Total results: {data.get('total')}")
            else:
                print(f"   ❌ Status: {response.status_code}")
        except Exception as e:
            print(f"   ❌ Error: {str(e)}")
    
    print(f"\n{'='*80}")
    print("✅ Pagination API tests complete!")
    print(f"{'='*80}\n")

if __name__ == "__main__":
    test_pagination_endpoints()
