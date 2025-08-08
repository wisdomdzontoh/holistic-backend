#!/usr/bin/env python
"""
Simple connection test for DHIS2 instance
"""
import requests
import sys

def test_connection():
    """Test basic connection to DHIS2 instance"""
    url = "https://dhims.chimgh.org/dhims"
    
    print(f"Testing connection to: {url}")
    
    try:
        # Test basic connection
        response = requests.get(f"{url}/api/system/info", timeout=30)
        print(f"Status code: {response.status_code}")
        print(f"Response headers: {dict(response.headers)}")
        
        if response.status_code == 200:
            print("✅ Connection successful")
            return True
        else:
            print(f"❌ Connection failed with status: {response.status_code}")
            return False
            
    except requests.exceptions.Timeout:
        print("❌ Connection timeout")
        return False
    except requests.exceptions.ConnectionError as e:
        print(f"❌ Connection error: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

if __name__ == "__main__":
    test_connection()
