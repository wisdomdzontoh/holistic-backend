#!/usr/bin/env python
"""
Test script to verify the strptime error fix
"""
import os
import sys
import django
from datetime import date

# Add the project directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from assessments.services import DataSyncService
from django.contrib.auth import get_user_model
from dhis2_auth.session import create_dhis2_session

User = get_user_model()

def test_sync_with_date_objects():
    """Test sync with datetime.date objects"""
    print("Testing sync with datetime.date objects...")
    
    service = DataSyncService()
    sync_request = {
        'period_start': date(2024, 1, 1),
        'period_end': date(2024, 12, 31),
        'sync_type': 'FULL'
    }
    
    try:
        # Test the _get_periods_to_sync method directly
        periods = service._get_periods_to_sync(sync_request)
        print(f"✓ Successfully generated {len(periods)} periods from date objects")
        print(f"  First 5 periods: {periods[:5]}")
        return True
    except Exception as e:
        print(f"✗ Error with date objects: {e}")
        return False

def test_sync_with_strings():
    """Test sync with string dates"""
    print("\nTesting sync with string dates...")
    
    service = DataSyncService()
    sync_request = {
        'period_start': '2024-01-01',
        'period_end': '2024-12-31',
        'sync_type': 'FULL'
    }
    
    try:
        # Test the _get_periods_to_sync method directly
        periods = service._get_periods_to_sync(sync_request)
        print(f"✓ Successfully generated {len(periods)} periods from strings")
        print(f"  First 5 periods: {periods[:5]}")
        return True
    except Exception as e:
        print(f"✗ Error with strings: {e}")
        return False

def test_full_sync_process():
    """Test the full sync process with authentication"""
    print("\nTesting full sync process...")
    
    # Get or create a test user
    user, created = User.objects.get_or_create(
        username='test_user',
        defaults={
            'email': 'test@example.com',
            'is_staff': True
        }
    )
    
    # Create a DHIS2 session for the user
    session_data = {
        'instance_url': 'https://dhims.chimgh.org/dhims',
        'username': 'admin',
        'password': 'district'
    }
    
    session_key = create_dhis2_session(user, session_data)
    print(f"✓ Created DHIS2 session: {session_key}")
    
    service = DataSyncService()
    sync_request = {
        'period_start': date(2024, 1, 1),
        'period_end': date(2024, 12, 31),
        'sync_type': 'FULL'
    }
    
    try:
        # This should not raise the strptime error anymore
        sync_log = service.sync_data(sync_request, user, session_key)
        print(f"✓ Successfully created sync log: {sync_log.id}")
        print(f"  Indicator UIDs: {sync_log.indicator_uids}")
        print(f"  Total indicators: {sync_log.total_indicators}")
        return True
    except Exception as e:
        print(f"✗ Error in full sync process: {e}")
        return False

if __name__ == '__main__':
    print("Testing strptime error fix...")
    
    success1 = test_sync_with_date_objects()
    success2 = test_sync_with_strings()
    success3 = test_full_sync_process()
    
    print(f"\n{'='*50}")
    print("Test Results:")
    print(f"Date objects test: {'✓ PASSED' if success1 else '✗ FAILED'}")
    print(f"String dates test: {'✓ PASSED' if success2 else '✗ FAILED'}")
    print(f"Full sync test: {'✓ PASSED' if success3 else '✗ FAILED'}")
    
    if all([success1, success2, success3]):
        print("\n🎉 All tests passed! The strptime error has been fixed.")
    else:
        print("\n❌ Some tests failed. Please check the errors above.") 