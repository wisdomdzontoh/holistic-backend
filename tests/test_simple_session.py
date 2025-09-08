#!/usr/bin/env python3
"""
Simple test to verify basic session functionality
"""

import requests
import json

# Configuration
BACKEND_URL = "https://holistic-backend-y7gp.onrender.com/api"

def test_simple_session():
    """Test basic session functionality"""
    print("Testing basic session functionality...")
    
    session = requests.Session()
    
    try:
        # Test a simple endpoint that should work without authentication
        print("1. Testing health endpoint...")
        response = session.get(f"{BACKEND_URL}/dhis2-auth/health/")
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text}")
        print(f"Cookies: {dict(session.cookies)}")
        
        # Test debug endpoint
        print("\n2. Testing debug endpoint...")
        response2 = session.get(f"{BACKEND_URL}/dhis2-auth/debug-session/")
        print(f"Status: {response2.status_code}")
        print(f"Response: {json.dumps(response2.json(), indent=2)}")
        print(f"Cookies after debug: {dict(session.cookies)}")
        
        # Test debug endpoint again with same session
        print("\n3. Testing debug endpoint again...")
        response3 = session.get(f"{BACKEND_URL}/dhis2-auth/debug-session/")
        print(f"Status: {response3.status_code}")
        print(f"Response: {json.dumps(response3.json(), indent=2)}")
        print(f"Cookies after second debug: {dict(session.cookies)}")
        
        # Check if session persisted
        if response2.json().get('session_key') == response3.json().get('session_key'):
            print("✅ Session persisted correctly")
        else:
            print("❌ Session did not persist")
            print(f"First session: {response2.json().get('session_key')}")
            print(f"Second session: {response3.json().get('session_key')}")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    print("Simple Session Test")
    print("=" * 30)
    
    test_simple_session()
    
    print("\nTest completed!")
