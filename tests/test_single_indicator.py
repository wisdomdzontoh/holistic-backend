#!/usr/bin/env python
"""
Test script to debug a single indicator data fetch
"""
import os
import sys
import django
from datetime import datetime

# Add the project directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from assessments.services import DataSyncService
from dhis2_auth.dhis_client import DHIS2Client
from indicators.models import TrackedIndicator

def test_single_indicator():
    """Test fetching data for a single indicator"""
    print("Testing single indicator data fetch...")

    # Create DHIS2 client with default credentials
    dhis2_client = DHIS2Client(
        instance_url='https://dhims.chimgh.org/dhims',
        username='Demo',
        password='Ghana@2020'
    )

    # Get the first active indicator
    try:
        indicator = TrackedIndicator.objects.filter(is_active=True).first()
        if not indicator:
            print("No active indicators found")
            return
        
        print(f"Testing indicator: {indicator.name} ({indicator.dhis2_uid})")
        print(f"Indicator type: {indicator.indicator_type}")
        
        # Test org unit and period
        org_unit_id = "ImspTQPwCqd"  # Demo org unit
        period = "202401"  # January 2024
        
        print(f"Testing with org unit: {org_unit_id}, period: {period}")
        
        # Create sync service
        sync_service = DataSyncService(dhis2_client=dhis2_client)
        
        # Test the fetch directly
        print("\n=== Testing _fetch_indicator_data ===")
        value = sync_service._fetch_indicator_data(indicator, org_unit_id, period)
        print(f"Returned value: {value}")
        
        # Test the DHIS2 client directly
        print("\n=== Testing DHIS2 client directly ===")
        if indicator.indicator_type == 'indicator':
            response = dhis2_client.get_analytics_data(
                indicators=[indicator.dhis2_uid],
                periods=[period],
                org_units=[org_unit_id]
            )
        elif indicator.indicator_type == 'dataElement':
            response = dhis2_client.get_analytics_data(
                data_elements=[indicator.dhis2_uid],
                periods=[period],
                org_units=[org_unit_id]
            )
        else:
            response = dhis2_client.get_analytics_data(
                data_elements=[indicator.dhis2_uid],
                periods=[period],
                org_units=[org_unit_id]
            )
        
        print(f"DHIS2 Response type: {type(response)}")
        if isinstance(response, dict):
            print(f"Response keys: {list(response.keys())}")
            if 'rows' in response:
                print(f"Number of rows: {len(response['rows'])}")
                if response['rows']:
                    print(f"First row: {response['rows'][0]}")
            if 'headers' in response:
                print(f"Headers: {response['headers']}")
        else:
            print(f"Unexpected response: {response}")
        
        # Test value extraction
        print("\n=== Testing value extraction ===")
        extracted_value = sync_service._extract_value_from_analytics_response(response, indicator.dhis2_uid)
        print(f"Extracted value: {extracted_value}")
        
    except Exception as e:
        print(f"Error: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    test_single_indicator() 