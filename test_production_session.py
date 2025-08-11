#!/usr/bin/env python3
"""
Test script to debug production session issues
"""

import requests
import json

# Configuration
BACKEND_URL = "https://holistic-backend-y7gp.onrender.com/api"
FRONTEND_URL = "https://holistic-assessment.vercel.app"

def test_production_session():
    """Test session handling in production"""
    print("Testing production session handling...")
    
    # Create a session
    session = requests.Session()
    
    # Test debug endpoint
    try:
        print("1. Testing debug session endpoint...")
        response = session.get(f"{BACKEND_URL}/dhis2-auth/debug-session/")
        print(f"Status: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        print(f"Cookies received: {dict(session.cookies)}")
        print(f"Set-Cookie headers: {response.headers.get('set-cookie', 'None')}")
        
        # Check if session cookie was set
        session_cookie = session.cookies.get('sessionid')
        if session_cookie:
            print(f"✅ Session cookie set: {session_cookie}")
        else:
            print("❌ No session cookie received")
            
    except Exception as e:
        print(f"Error: {e}")

def test_cors_preflight():
    """Test CORS preflight request"""
    print("\n2. Testing CORS preflight...")
    
    session = requests.Session()
    
    headers = {
        'Origin': FRONTEND_URL,
        'Access-Control-Request-Method': 'GET',
        'Access-Control-Request-Headers': 'Content-Type',
    }
    
    try:
        response = session.options(f"{BACKEND_URL}/dhis2-auth/debug-session/", headers=headers)
        print(f"OPTIONS status: {response.status_code}")
        print(f"Access-Control-Allow-Origin: {response.headers.get('Access-Control-Allow-Origin')}")
        print(f"Access-Control-Allow-Credentials: {response.headers.get('Access-Control-Allow-Credentials')}")
        print(f"Access-Control-Allow-Methods: {response.headers.get('Access-Control-Allow-Methods')}")
        print(f"Access-Control-Allow-Headers: {response.headers.get('Access-Control-Allow-Headers')}")
        
    except Exception as e:
        print(f"Error: {e}")

def test_with_credentials():
    """Test with credentials included"""
    print("\n3. Testing with credentials...")
    
    session = requests.Session()
    
    headers = {
        'Origin': FRONTEND_URL,
        'Content-Type': 'application/json',
    }
    
    try:
        response = session.get(
            f"{BACKEND_URL}/dhis2-auth/debug-session/",
            headers=headers
        )
        print(f"Status: {response.status_code}")
        print(f"Cookies sent: {dict(session.cookies)}")
        print(f"Set-Cookie: {response.headers.get('set-cookie', 'None')}")
        
    except Exception as e:
        print(f"Error: {e}")

def test_session_persistence():
    """Test if session persists across requests"""
    print("\n4. Testing session persistence...")
    
    session = requests.Session()
    
    try:
        # First request
        print("First request:")
        response1 = session.get(f"{BACKEND_URL}/dhis2-auth/debug-session/")
        print(f"Status: {response1.status_code}")
        print(f"Session key: {response1.json().get('session_key')}")
        print(f"Cookies: {dict(session.cookies)}")
        
        # Second request with same session
        print("\nSecond request:")
        response2 = session.get(f"{BACKEND_URL}/dhis2-auth/debug-session/")
        print(f"Status: {response2.status_code}")
        print(f"Session key: {response2.json().get('session_key')}")
        print(f"Cookies: {dict(session.cookies)}")
        
        # Check if session persisted
        if response1.json().get('session_key') == response2.json().get('session_key'):
            print("✅ Session persisted correctly")
        else:
            print("❌ Session did not persist")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    print("Production Session Debug Test")
    print("=" * 50)
    
    test_production_session()
    test_cors_preflight()
    test_with_credentials()
    test_session_persistence()
    
    print("\nTest completed!")
    print("\nKey things to check:")
    print("1. Are session cookies being set in responses?")
    print("2. Are cookies being sent in subsequent requests?")
    print("3. Are CORS headers properly configured?")
    print("4. Is SameSite=None working for cross-origin requests?")
