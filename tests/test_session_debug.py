#!/usr/bin/env python3
"""
Test script to debug session issues
"""

import requests
import json

# Configuration
BACKEND_URL = "https://holistic-backend-y7gp.onrender.com/api"
FRONTEND_URL = "https://holistic-assessment.vercel.app"

def test_session_debug():
    """Test the debug session endpoint"""
    print("Testing session debug endpoint...")
    
    # Create a session
    session = requests.Session()
    
    # Test debug endpoint without authentication
    try:
        response = session.get(f"{BACKEND_URL}/dhis2-auth/debug-session/")
        print(f"Debug endpoint status: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        print(f"Cookies set: {dict(session.cookies)}")
    except Exception as e:
        print(f"Error testing debug endpoint: {e}")

def test_auth_endpoint():
    """Test the auth endpoint"""
    print("\nTesting auth endpoint...")
    
    session = requests.Session()
    
    try:
        response = session.get(f"{BACKEND_URL}/dhis2-auth/test-auth/")
        print(f"Auth endpoint status: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
    except Exception as e:
        print(f"Error testing auth endpoint: {e}")

def test_login_and_session():
    """Test login and then session persistence"""
    print("\nTesting login and session persistence...")
    
    session = requests.Session()
    
    # Test login (you'll need to provide real credentials)
    login_data = {
        "username": "your_username",  # Replace with actual credentials
        "password": "your_password",
        "instanceUrl": "https://dhims.chimgh.org/dhims"
    }
    
    try:
        # First, test debug endpoint before login
        print("Before login:")
        response = session.get(f"{BACKEND_URL}/dhis2-auth/debug-session/")
        print(f"Debug status: {response.status_code}")
        print(f"Cookies before login: {dict(session.cookies)}")
        
        # Try login
        print("\nAttempting login...")
        login_response = session.post(
            f"{BACKEND_URL}/dhis2-auth/login/",
            json=login_data,
            headers={'Content-Type': 'application/json'}
        )
        print(f"Login status: {login_response.status_code}")
        print(f"Login response: {json.dumps(login_response.json(), indent=2)}")
        print(f"Cookies after login: {dict(session.cookies)}")
        
        if login_response.status_code == 200:
            # Test session persistence
            print("\nAfter login:")
            response2 = session.get(f"{BACKEND_URL}/dhis2-auth/test-auth/")
            print(f"Auth test status: {response2.status_code}")
            print(f"Auth test response: {json.dumps(response2.json(), indent=2)}")
            
    except Exception as e:
        print(f"Error testing login: {e}")

def test_cors_headers():
    """Test CORS headers"""
    print("\nTesting CORS headers...")
    
    session = requests.Session()
    
    headers = {
        'Origin': FRONTEND_URL,
        'Referer': f"{FRONTEND_URL}/",
    }
    
    try:
        response = session.options(f"{BACKEND_URL}/dhis2-auth/debug-session/", headers=headers)
        print(f"OPTIONS request status: {response.status_code}")
        print(f"Access-Control-Allow-Origin: {response.headers.get('Access-Control-Allow-Origin')}")
        print(f"Access-Control-Allow-Credentials: {response.headers.get('Access-Control-Allow-Credentials')}")
        print(f"Access-Control-Allow-Methods: {response.headers.get('Access-Control-Allow-Methods')}")
        print(f"Access-Control-Allow-Headers: {response.headers.get('Access-Control-Allow-Headers')}")
    except Exception as e:
        print(f"Error testing CORS: {e}")

if __name__ == "__main__":
    print("Session Debug Test")
    print("=" * 40)
    
    test_session_debug()
    test_auth_endpoint()
    test_cors_headers()
    
    # Uncomment the line below and provide real credentials to test login
    # test_login_and_session()
    
    print("\nDebug test completed!")
    print("\nTo test login, uncomment the test_login_and_session() line and provide real credentials.")
