#!/usr/bin/env python
"""
Test script to check DHIS2 credentials and find working ones
"""
import os
import sys
import django
import logging
import requests
from datetime import datetime

# Add the project directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Configure logging to show detailed output
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

def test_dhis2_credentials():
    """Test different DHIS2 credentials to find working ones"""
    print("Testing DHIS2 credentials...")
    
    # DHIS2 instance URL
    instance_url = 'https://dhims.chimgh.org/dhims'
    
    # Test the provided credentials
    credentials_to_test = [
        ('Demo', 'Ghana@2020'),  # User provided credentials
    ]
    
    print(f"Testing connection to: {instance_url}")
    print("=" * 50)
    
    for username, password in credentials_to_test:
        print(f"\nTesting credentials: {username}/{password}")
        
        try:
            # Test basic connection first
            session = requests.Session()
            session.auth = (username, password)
            session.headers.update({
                'User-Agent': 'HolisticAssessment/1.0',
                'Accept': 'application/json',
                'Content-Type': 'application/json'
            })
            
            # Test /api/me endpoint
            api_url = f"{instance_url}/api/me"
            response = session.get(api_url, timeout=10)
            
            print(f"  Status: {response.status_code}")
            
            if response.status_code == 200:
                user_info = response.json()
                print(f"  ✓ SUCCESS! User: {user_info.get('name', 'Unknown')}")
                print(f"  User ID: {user_info.get('id', 'Unknown')}")
                print(f"  Username: {user_info.get('userCredentials', {}).get('username', 'Unknown')}")
                
                # Test analytics endpoint
                print("  Testing analytics endpoint...")
                analytics_url = f"{instance_url}/api/analytics"
                analytics_params = {
                    "dimension": "dx:XLn1cZZTA0H&dimension=pe:2024&dimension=ou:ImspTQPwCqd"
                }
                
                analytics_response = session.get(analytics_url, params=analytics_params, timeout=10)
                print(f"  Analytics status: {analytics_response.status_code}")
                
                if analytics_response.status_code == 200:
                    analytics_data = analytics_response.json()
                    print(f"  ✓ Analytics working! Rows: {len(analytics_data.get('rows', []))}")
                    return username, password
                else:
                    print(f"  ✗ Analytics failed: {analytics_response.text[:200]}")
                    
            elif response.status_code == 401:
                print("  ✗ Unauthorized - wrong credentials")
            elif response.status_code == 403:
                print("  ✗ Forbidden - account disabled or no access")
            else:
                print(f"  ✗ Unexpected status: {response.status_code}")
                print(f"  Response: {response.text[:200]}")
                
        except requests.ConnectionError as e:
            print(f"  ✗ Connection error: {str(e)}")
        except requests.Timeout as e:
            print(f"  ✗ Timeout: {str(e)}")
        except Exception as e:
            print(f"  ✗ Error: {str(e)}")
    
    print("\n" + "=" * 50)
    print("No working credentials found!")
    print("You may need to:")
    print("1. Contact the DHIS2 administrator for valid credentials")
    print("2. Check if the DHIS2 instance is accessible")
    print("3. Verify the instance URL is correct")
    return None, None

if __name__ == '__main__':
    test_dhis2_credentials() 