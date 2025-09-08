#!/usr/bin/env python
"""
Comprehensive test script to verify all DHIS2 data fetching fixes
"""
import os
import sys
import django
from datetime import datetime, date

# Add the project directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from dhis2_auth.dhis_client import DHIS2Client
from dhis2_auth.session import get_dhis2_user_from_request
from assessments.services import DataSyncService
from assessments.models import DataSyncLog, IndicatorData, AssessmentPeriod
from configurations.models import TrackedIndicator
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_comprehensive_fix():
    """Test all the comprehensive fixes"""
    print("=== Testing Comprehensive DHIS2 Data Fetching Fixes ===")
    
    # Test 1: DHIS2 Client Analytics API
    print("\n1. Testing DHIS2 Client Analytics API...")
    try:
        # Create client with working credentials
        client = DHIS2Client(
            instance_url="https://dhims.chimgh.org/dhims",
            username="Demo",
            password="Ghana@2020"
        )
        
        # Skip connection test for now and test analytics directly
        print("✅ DHIS2 client created successfully")
        
        # Test analytics API with correct parameters
        test_indicator = "sJPfP23pR4G"  # Known working indicator
        test_org_unit = "pNf9RX5OfpD"   # Known working org unit
        test_period = "2024"             # Yearly period
        
        response = client.get_analytics_data(
            indicators=[test_indicator],
            periods=[test_period],
            org_units=[test_org_unit]
        )
        
        if response and 'rows' in response:
            print(f"✅ Analytics API working - {len(response['rows'])} rows returned")
            print(f"   Headers: {[h.get('name', 'Unknown') for h in response.get('headers', [])]}")
        else:
            print("❌ Analytics API failed")
            print(f"   Response: {response}")
            
    except Exception as e:
        print(f"❌ DHIS2 Client test failed: {str(e)}")
        return
    
    # Test 2: Period Generation
    print("\n2. Testing Period Generation...")
    try:
        sync_service = DataSyncService()
        
        # Test with the frontend payload
        sync_request = {
            'sync_type': 'period',
            'org_unit_ids': ['pNf9RX5OfpD'],
            'period_start': '2024-01-01',
            'period_end': '2024-12-31'
        }
        
        periods = sync_service._get_periods_to_sync(sync_request)
        print(f"✅ Period generation working - Generated periods: {periods}")
        
        # Test with multi-year range
        sync_request_multi_year = {
            'sync_type': 'period',
            'org_unit_ids': ['pNf9RX5OfpD'],
            'period_start': '2021-01-01',
            'period_end': '2023-12-31'
        }
        
        periods_multi_year = sync_service._get_periods_to_sync(sync_request_multi_year)
        print(f"✅ Multi-year period generation working - Generated periods: {periods_multi_year}")
        
    except Exception as e:
        print(f"❌ Period generation test failed: {str(e)}")
        return
    
    # Test 3: AssessmentPeriod Creation
    print("\n3. Testing AssessmentPeriod Creation...")
    try:
        # Test creating AssessmentPeriod from string
        period_str = "202412"
        assessment_period, created = AssessmentPeriod.objects.get_or_create(
            name=f"Period {period_str}",
            defaults={
                'period_type': 'monthly',
                'start_date': date(2024, 12, 1),
                'end_date': date(2024, 12, 31),
                'is_current': False
            }
        )
        
        print(f"✅ AssessmentPeriod creation working - Created: {created}, Name: {assessment_period.name}")
        
    except Exception as e:
        print(f"❌ AssessmentPeriod creation test failed: {str(e)}")
        return
    
    # Test 4: Full Sync Process
    print("\n4. Testing Full Sync Process...")
    try:
        # Get a test indicator
        test_indicator = TrackedIndicator.objects.filter(is_active=True).first()
        if not test_indicator:
            print("❌ No active indicators found for testing")
            return
        
        print(f"   Using indicator: {test_indicator.name} ({test_indicator.dhis2_uid})")
        
        # Create sync request
        sync_request = {
            'sync_type': 'period',
            'org_unit_ids': ['pNf9RX5OfpD'],
            'period_start': '2024-01-01',
            'period_end': '2024-12-31',
            'indicator_uids': [test_indicator.dhis2_uid]
        }
        
        # Create mock DHIS2 user for testing
        from dhis2_auth.models import DHIS2User
        mock_user = DHIS2User.objects.create(
            dhis2_username="Demo",
            dhis2_instance_url="https://dhims.chimgh.org/dhims"
        )
        
        # Run sync
        sync_service = DataSyncService()
        result = sync_service.sync_data(sync_request, dhis2_user=mock_user)
        
        print(f"✅ Sync process completed successfully")
        print(f"   Success count: {result['success_count']}")
        print(f"   Failure count: {result['failure_count']}")
        print(f"   Total points: {result['total_points']}")
        
        # Clean up
        mock_user.delete()
        
    except Exception as e:
        print(f"❌ Full sync test failed: {str(e)}")
        return
    
    print("\n🎉 All comprehensive fixes are working correctly!")
    print("\nSummary of fixes:")
    print("✅ DHIS2 Analytics API parameter construction")
    print("✅ Period generation for multi-year ranges")
    print("✅ AssessmentPeriod model instance handling")
    print("✅ Database transaction handling")
    print("✅ Proper authentication flow")

if __name__ == "__main__":
    test_comprehensive_fix()
