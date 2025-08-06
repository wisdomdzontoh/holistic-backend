#!/usr/bin/env python
"""
Test script to debug the sync process and data fetching
"""
import os
import sys
import django
import logging
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

from dhis2_auth.dhis_client import DHIS2Client
from indicators.models import TrackedIndicator
from assessments.models import DataSyncLog, IndicatorData

def test_sync_debug():
    """Debug the sync process to understand why no data points are created"""
    print("Testing sync debug...")
    
    # Create DHIS2 client with working credentials
    dhis2_client = DHIS2Client(
        instance_url='https://dhims.chimgh.org/dhims',
        username='Demo',
        password='Ghana@2020'
    )
    
    try:
        # Test connection
        print("\n1. Testing connection...")
        if dhis2_client.test_connection():
            print("✓ Connection successful")
        else:
            print("✗ Connection failed")
            return
        
        # Get a sample indicator that was in the sync
        sample_indicator_uid = "sJPfP23pR4G"  # The one we tested earlier
        print(f"\n2. Testing indicator: {sample_indicator_uid}")
        
        # Test with the same parameters from the sync
        org_unit_id = "pNf9RX5OfpD"  # From the sync log
        period = "2023"  # Year 2023 from the sync
        
        print(f"Testing with org unit: {org_unit_id}")
        print(f"Testing with period: {period}")
        
        # Make analytics request
        response = dhis2_client.get_analytics_data(
            indicators=[sample_indicator_uid],
            periods=[period],
            org_units=[org_unit_id]
        )
        
        print(f"\n3. Analytics response:")
        print(f"Response type: {type(response)}")
        if isinstance(response, dict):
            print(f"Response keys: {list(response.keys())}")
            if 'rows' in response:
                print(f"Number of rows: {len(response['rows'])}")
                if response['rows']:
                    print(f"Sample row: {response['rows'][0]}")
                else:
                    print("No rows returned - this explains why no data points were created!")
            if 'headers' in response:
                print(f"Headers: {[h.get('name', 'Unknown') for h in response['headers']]}")
            if 'metaData' in response:
                print(f"Metadata items: {list(response['metaData'].get('items', {}).keys())}")
        else:
            print(f"Unexpected response: {response}")
        
        # Test with different periods to see if data exists
        print(f"\n4. Testing with different periods...")
        test_periods = [
            "2023",      # Year 2023 (from sync)
            "2023Q1",    # Q1 2023
            "2023Q2",    # Q2 2023
            "2023Q3",    # Q3 2023
            "2023Q4",    # Q4 2023
            "2024",      # Year 2024
            "2024Q1",    # Q1 2024
            "2024Q2",    # Q2 2024
            "2024Q3",    # Q3 2024
            "2024Q4",    # Q4 2024
            "2025",      # Year 2025
            "202501",    # January 2025
            "202502",    # February 2025
        ]
        
        for test_period in test_periods:
            print(f"\nTesting period: {test_period}")
            try:
                test_response = dhis2_client.get_analytics_data(
                    indicators=[sample_indicator_uid],
                    periods=[test_period],
                    org_units=[org_unit_id]
                )
                
                if isinstance(test_response, dict) and 'rows' in test_response:
                    row_count = len(test_response['rows'])
                    print(f"  Rows returned: {row_count}")
                    if row_count > 0:
                        print(f"  Sample data: {test_response['rows'][0]}")
                        print(f"  ✓ Data found for period {test_period}!")
                        break
                else:
                    print(f"  No data returned")
                    
            except Exception as e:
                print(f"  Error: {str(e)}")
        
        # Test with different org units
        print(f"\n5. Testing with different org units...")
        test_org_units = [
            "pNf9RX5OfpD",  # Original from sync
            "ImspTQPwCqd",   # From our earlier test
        ]
        
        for test_org_unit in test_org_units:
            print(f"\nTesting org unit: {test_org_unit}")
            try:
                test_response = dhis2_client.get_analytics_data(
                    indicators=[sample_indicator_uid],
                    periods=["2024"],  # Use a period that might have data
                    org_units=[test_org_unit]
                )
                
                if isinstance(test_response, dict) and 'rows' in test_response:
                    row_count = len(test_response['rows'])
                    print(f"  Rows returned: {row_count}")
                    if row_count > 0:
                        print(f"  Sample data: {test_response['rows'][0]}")
                        print(f"  ✓ Data found for org unit {test_org_unit}!")
                else:
                    print(f"  No data returned")
                    
            except Exception as e:
                print(f"  Error: {str(e)}")
        
        # Check what indicators are available in the system
        print(f"\n6. Checking tracked indicators in database...")
        tracked_indicators = TrackedIndicator.objects.filter(is_active=True)
        print(f"Found {tracked_indicators.count()} active tracked indicators")
        
        # Show some sample indicators
        for indicator in tracked_indicators[:5]:
            print(f"  - {indicator.name} ({indicator.dhis2_uid}) - Type: {indicator.indicator_type}")
        
        # Check recent sync logs
        print(f"\n7. Checking recent sync logs...")
        recent_syncs = DataSyncLog.objects.order_by('-started_at')[:3]
        for sync in recent_syncs:
            print(f"  Sync ID {sync.id}: {sync.sync_type} - {sync.status} - {sync.total_data_points} data points")
        
        # Check if any indicator data exists
        print(f"\n8. Checking existing indicator data...")
        data_count = IndicatorData.objects.count()
        print(f"Total indicator data points in database: {data_count}")
        
        if data_count > 0:
            recent_data = IndicatorData.objects.order_by('-created_at')[:3]
            for data in recent_data:
                print(f"  - {data.indicator.name}: {data.value} for {data.org_unit_name} ({data.period})")
        
    except Exception as e:
        print(f"Error during testing: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    test_sync_debug() 