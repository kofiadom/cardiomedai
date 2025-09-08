#!/usr/bin/env python3
"""
Test script to verify if the Swagger UI fix is working
"""

import requests
import json

def test_endpoints():
    base_url = "https://staging.codinnovations.com/cardiomed"
    
    endpoints_to_test = [
        ("/", "Main API endpoint"),
        ("/health", "Health check endpoint"),
        ("/openapi-test", "OpenAPI test endpoint"),
        ("/openapi.json", "OpenAPI JSON schema")
    ]
    
    print("Testing CardioMed AI endpoints...")
    print("=" * 50)
    
    for endpoint, description in endpoints_to_test:
        url = base_url + endpoint
        print(f"\nTesting {description}")
        print(f"URL: {url}")
        
        try:
            response = requests.get(url, timeout=10)
            print(f"Status Code: {response.status_code}")
            
            if response.status_code == 200:
                print("SUCCESS")
                if endpoint == "/openapi.json":
                    # Validate OpenAPI schema
                    try:
                        schema = response.json()
                        if "openapi" in schema and "paths" in schema:
                            print(f"   OpenAPI Version: {schema.get('openapi', 'Unknown')}")
                            print(f"   API Title: {schema.get('info', {}).get('title', 'Unknown')}")
                            print(f"   Number of paths: {len(schema.get('paths', {}))}")
                        else:
                            print("   WARNING: Invalid OpenAPI schema structure")
                    except json.JSONDecodeError:
                        print("   WARNING: Response is not valid JSON")
                elif endpoint in ["/health", "/openapi-test"]:
                    try:
                        data = response.json()
                        print(f"   Response: {json.dumps(data, indent=2)}")
                    except:
                        print(f"   Response: {response.text[:100]}...")
            else:
                print(f"FAILED - Status: {response.status_code}")
                print(f"   Response: {response.text[:200]}...")
                
        except requests.exceptions.RequestException as e:
            print(f"CONNECTION ERROR: {e}")
    
    print("\n" + "=" * 50)
    print("Test Summary:")
    print("If /openapi.json returns valid JSON but /docs still fails:")
    print("1. Try hard refresh (Ctrl+F5) on the /docs page")
    print("2. Try incognito/private browsing mode")
    print("3. Try ReDoc instead: /redoc")
    print("4. Check browser console for JavaScript errors")

if __name__ == "__main__":
    test_endpoints()