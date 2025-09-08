#!/usr/bin/env python
"""
Test script to verify DHIS2 authentication and API calls
"""
import os
import sys
import django

# Add the project directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from dhis2_auth.dhis_client import DHIS2Client
import logging

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def test_dhis2_auth():
    """
    Test DHIS2 authentication and API calls
    """
    # Test configuration - replace with your actual DHIS2 instance
    instance_url = "https://dhims.chimgh.org/dhims"
    username = "admin"  # Replace with actual username
    password = "district"  # Replace with actual password
    
    print(f"Testing DHIS2 authentication to: {instance_url}")
    print(f"Username: {username}")
    print("-" * 50)
    
    try:
        # Create DHIS2 client
        client = DHIS2Client(instance_url, username, password)
        
        # Test authentication
        print("1. Testing authentication...")
        try:
            user_info = client.authenticate_user()
            print(f"✅ Authentication successful for user: {user_info.get('name', 'Unknown')}")
            print(f"   User ID: {user_info.get('id', 'Unknown')}")
            print(f"   Username: {user_info.get('username', 'Unknown')}")
        except Exception as e:
            print(f"❌ Authentication failed: {str(e)}")
            return
        
        # Test periods endpoint
        print("\n2. Testing periods endpoint...")
        try:
            periods = client.get_periods()
            print(f"✅ Found {len(periods)} periods")
            if periods:
                print(f"   Sample period: {periods[0].get('name', 'Unknown')}")
        except Exception as e:
            print(f"❌ Periods endpoint failed: {str(e)}")
        
        # Test org units endpoint
        print("\n3. Testing organisation units endpoint...")
        try:
            org_units = client.get_org_units()
            print(f"✅ Found {len(org_units)} organisation units")
            if org_units:
                print(f"   Sample org unit: {org_units[0].get('name', 'Unknown')}")
        except Exception as e:
            print(f"❌ Organisation units endpoint failed: {str(e)}")
        
        print("\n" + "=" * 50)
        print("✅ DHIS2 authentication test completed!")
        
    except Exception as e:
        print(f"❌ Test failed with error: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_dhis2_auth() 