#!/usr/bin/env python
"""
Test script to verify DHIS2 authentication with default instance URL
"""
import os
import sys
import django
from django.conf import settings

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from dhis2_auth.utils import get_default_dhis2_instance_url
from dhis2_auth.dhis_client import DHIS2Client

def test_default_dhis2_url():
    """Test that the default DHIS2 URL is properly configured"""
    print("Testing DHIS2 configuration...")
    
    # Get default URL
    default_url = get_default_dhis2_instance_url()
    print(f"Default DHIS2 URL: {default_url}")
    
    if not default_url:
        print("ERROR: No default DHIS2 URL configured!")
        return False
    
    # Test connection
    try:
        client = DHIS2Client(instance_url=default_url)
        if client.test_connection():
            print("✅ Connection test successful!")
            return True
        else:
            print("❌ Connection test failed!")
            return False
    except Exception as e:
        print(f"❌ Connection test error: {str(e)}")
        return False

def test_settings():
    """Test that settings are properly configured"""
    print("\nTesting Django settings...")
    
    print(f"DEBUG: {settings.DEBUG}")
    print(f"ALLOWED_HOSTS: {settings.ALLOWED_HOSTS}")
    
    if hasattr(settings, 'DEFAULT_DHIS2_URL'):
        print(f"DEFAULT_DHIS2_URL: {settings.DEFAULT_DHIS2_URL}")
    else:
        print("DEFAULT_DHIS2_URL: Not configured")
    
    return True

if __name__ == "__main__":
    print("=" * 50)
    print("DHIS2 Authentication Test")
    print("=" * 50)
    
    settings_ok = test_settings()
    connection_ok = test_default_dhis2_url()
    
    print("\n" + "=" * 50)
    if settings_ok and connection_ok:
        print("✅ All tests passed!")
        print("The backend is ready for DHIS2 authentication.")
    else:
        print("❌ Some tests failed!")
        print("Please check your configuration.")
    print("=" * 50) 