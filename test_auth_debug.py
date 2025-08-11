#!/usr/bin/env python3
"""
Test script to debug authentication issues
"""

import requests
import json

# Configuration
BACKEND_URL = "https://holistic-backend-y7gp.onrender.com/api"
FRONTEND_URL = "https://holistic-assessment.vercel.app"  # Update with your actual frontend URL

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
    except Exception as e:
        print(f"Error testing debug endpoint: {e}")

def test_cors_headers():
    """Test CORS headers"""
    print("\nTesting CORS headers...")
    
    session = requests.Session()
    
    # Test with Origin header
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

def test_login_flow():
    """Test the login flow"""
    print("\nTesting login flow...")
    
    session = requests.Session()
    
    # Test login endpoint
    login_data = {
        "username": "test_user",  # Replace with actual test credentials
        "password": "test_password",
        "instanceUrl": "https://dhims.chimgh.org/dhims"
    }
    
    try:
        response = session.post(
            f"{BACKEND_URL}/dhis2-auth/login/",
            json=login_data,
            headers={'Content-Type': 'application/json'}
        )
        print(f"Login status: {response.status_code}")
        print(f"Login response: {json.dumps(response.json(), indent=2)}")
        
        if response.status_code == 200:
            # Test session status after login
            response2 = session.get(f"{BACKEND_URL}/dhis2-auth/session/status/")
            print(f"Session status after login: {response2.status_code}")
            print(f"Session response: {json.dumps(response2.json(), indent=2)}")
            
    except Exception as e:
        print(f"Error testing login: {e}")

if __name__ == "__main__":
    print("DHIS2 Authentication Debug Test")
    print("=" * 40)
    
    test_session_debug()
    test_cors_headers()
    test_login_flow()
    
    print("\nDebug test completed!")
