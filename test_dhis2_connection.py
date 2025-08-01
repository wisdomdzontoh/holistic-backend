#!/usr/bin/env python
"""
Test script to debug DHIS2 connection issues.
Run this script to test the connection to your DHIS2 instance.
"""

import os
import sys
import django
from django.conf import settings

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from dhis2_auth.dhis_client import DHIS2Client
from dhis2_auth.utils import get_default_dhis2_instance_url
import requests


def test_dhis2_connection():
    """Test DHIS2 connection with detailed logging"""
    
    print("=== DHIS2 Connection Test ===\n")
    
    # Get default instance URL
    instance_url = get_default_dhis2_instance_url()
    print(f"Default Instance URL: {instance_url}")
    
    if not instance_url:
        print("❌ No default instance URL configured!")
        return
    
    # Test basic connectivity first
    print(f"\n1. Testing basic connectivity to {instance_url}...")
    try:
        response = requests.get(instance_url, timeout=10)
        print(f"   ✅ Basic connectivity: {response.status_code}")
    except requests.RequestException as e:
        print(f"   ❌ Basic connectivity failed: {e}")
        return
    
    # Test without authentication
    print(f"\n2. Testing API endpoints without authentication...")
    client = DHIS2Client(instance_url)
    
    # Test system info
    try:
        system_info = client.get_system_info()
        print(f"   ✅ System info: {system_info.get('version', 'unknown')}")
    except requests.RequestException as e:
        print(f"   ❌ System info failed: {e}")
    
    # Test API version
    try:
        version_info = client.get_api_version()
        print(f"   ✅ API version: {version_info}")
    except requests.RequestException as e:
        print(f"   ❌ API version failed: {e}")
    
    # Test capabilities
    try:
        capabilities = client.get_api_capabilities()
        print(f"   ✅ API capabilities: {capabilities}")
    except requests.RequestException as e:
        print(f"   ❌ API capabilities failed: {e}")
    
    # Test connection method
    print(f"\n3. Testing connection method...")
    if client.test_connection():
        print("   ✅ Connection test passed")
    else:
        print("   ❌ Connection test failed")
    
    print(f"\n=== Test Complete ===")
    print(f"\nTo test with authentication, run:")
    print(f"python test_dhis2_connection.py --auth <username> <password>")


def test_with_auth(username, password):
    """Test DHIS2 connection with authentication"""
    
    print("=== DHIS2 Authentication Test ===\n")
    
    instance_url = get_default_dhis2_instance_url()
    print(f"Instance URL: {instance_url}")
    print(f"Username: {username}")
    
    client = DHIS2Client(instance_url, username, password)
    
    # Test authentication
    print(f"\n1. Testing authentication...")
    try:
        user_info = client.authenticate_user()
        print(f"   ✅ Authentication successful!")
        print(f"   User: {user_info.get('name', 'Unknown')}")
        print(f"   Username: {user_info.get('username', 'Unknown')}")
        print(f"   User ID: {user_info.get('id', 'Unknown')}")
        
        # Test org units
        print(f"\n2. Testing organisation units...")
        try:
            org_units = client.get_user_org_units()
            print(f"   ✅ Found {len(org_units)} organisation units")
            for ou in org_units[:3]:  # Show first 3
                print(f"   - {ou.get('name', 'Unknown')} ({ou.get('id', 'Unknown')})")
        except requests.RequestException as e:
            print(f"   ❌ Org units failed: {e}")
        
    except requests.RequestException as e:
        print(f"   ❌ Authentication failed: {e}")
        return
    
    print(f"\n=== Authentication Test Complete ===")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--auth":
        if len(sys.argv) != 4:
            print("Usage: python test_dhis2_connection.py --auth <username> <password>")
            sys.exit(1)
        test_with_auth(sys.argv[2], sys.argv[3])
    else:
        test_dhis2_connection() 