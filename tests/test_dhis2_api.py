#!/usr/bin/env python
"""
Test script to verify DHIS2 API connectivity and endpoints
"""
import os
import sys
import django
from django.conf import settings

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

def test_dhis2_connection():
    """
    Test DHIS2 connection and API endpoints
    """
    # Test configuration - replace with your actual DHIS2 instance
    instance_url = "https://dhims.chimgh.org/dhims"
    username = "admin"  # Replace with actual username
    password = "district"  # Replace with actual password
    
    print(f"Testing DHIS2 connection to: {instance_url}")
    print(f"Username: {username}")
    print("-" * 50)
    
    try:
        # Create DHIS2 client
        client = DHIS2Client(instance_url, username, password)
        
        # Test connection
        print("1. Testing connection...")
        if client.test_connection():
            print("✅ Connection test successful")
        else:
            print("❌ Connection test failed")
            return
        
        # Test authentication
        print("\n2. Testing authentication...")
        try:
            user_info = client.authenticate_user()
            print(f"✅ Authentication successful for user: {user_info.get('name', 'Unknown')}")
        except Exception as e:
            print(f"❌ Authentication failed: {str(e)}")
            return
        
        # Test periods endpoint
        print("\n3. Testing periods endpoint...")
        try:
            periods = client.get_periods()
            print(f"✅ Found {len(periods)} periods")
            if periods:
                print(f"   Sample period: {periods[0].get('name', 'Unknown')}")
        except Exception as e:
            print(f"❌ Periods endpoint failed: {str(e)}")
        
        # Test relative periods endpoint
        print("\n4. Testing relative periods endpoint...")
        try:
            relative_periods = client.get_relative_periods()
            print(f"✅ Found {len(relative_periods)} relative periods")
            if relative_periods:
                print(f"   Sample relative period: {relative_periods[0].get('name', 'Unknown')}")
        except Exception as e:
            print(f"❌ Relative periods endpoint failed: {str(e)}")
        
        # Test org units endpoint
        print("\n5. Testing organisation units endpoint...")
        try:
            org_units = client.get_org_units()
            print(f"✅ Found {len(org_units)} organisation units")
            if org_units:
                print(f"   Sample org unit: {org_units[0].get('name', 'Unknown')}")
        except Exception as e:
            print(f"❌ Organisation units endpoint failed: {str(e)}")
        
        # Test period types endpoint
        print("\n6. Testing period types endpoint...")
        try:
            period_types = client.get_period_types()
            print(f"✅ Found {len(period_types)} period types")
            if period_types:
                print(f"   Sample period type: {period_types[0].get('name', 'Unknown')}")
        except Exception as e:
            print(f"❌ Period types endpoint failed: {str(e)}")
        
        # Test system info
        print("\n7. Testing system info endpoint...")
        try:
            system_info = client.get_system_info()
            print(f"✅ System info retrieved")
            print(f"   Version: {system_info.get('version', 'Unknown')}")
        except Exception as e:
            print(f"❌ System info endpoint failed: {str(e)}")
        
        print("\n" + "=" * 50)
        print("✅ DHIS2 API test completed successfully!")
        
    except Exception as e:
        print(f"❌ Test failed with error: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_dhis2_connection() 