#!/usr/bin/env python
"""
Test script to understand DHIS2 response format and debug data extraction issues
"""
import os
import sys
import django
import logging
from datetime import datetime

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from dhis2_auth.dhis_client import DHIS2Client
from assessments.services import DataSyncService
from configurations.models import TrackedIndicator

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def test_dhis2_response_format():
    """Test DHIS2 response format and data extraction"""
    try:
        # Initialize DHIS2 client with test credentials
        client = DHIS2Client(
            instance_url="https://dhims.chimgh.org/dhims",
            username="Demo",
            password="Ghana@2020"
        )
        
        # Test with a specific indicator that was mentioned in the error
        test_indicator_uid = "U15VyJ7EHGF"  # The indicator from the error message
        test_org_unit = "Pug4R4IHDtN"  # Valid org unit we found earlier
        test_period = "2023"  # Yearly period
        
        print(f"Testing DHIS2 response format for:")
        print(f"  Indicator: {test_indicator_uid}")
        print(f"  Org Unit: {test_org_unit}")
        print(f"  Period: {test_period}")
        print("-" * 50)
        
        # Make the analytics request
        response = client.get_analytics_data(
            indicators=[test_indicator_uid],
            periods=[test_period],
            org_units=[test_org_unit]
        )
        
        print("Raw DHIS2 Response:")
        print(f"Type: {type(response)}")
        print(f"Response: {response}")
        print("-" * 50)
        
        if response:
            print("Response Structure Analysis:")
            if isinstance(response, dict):
                print(f"Keys: {list(response.keys())}")
                
                # Check for headers
                headers = response.get('headers', [])
                print(f"Headers count: {len(headers)}")
                for i, header in enumerate(headers):
                    print(f"  Header {i}: {header}")
                
                # Check for rows
                rows = response.get('rows', [])
                print(f"Rows count: {len(rows)}")
                for i, row in enumerate(rows[:3]):  # Show first 3 rows
                    print(f"  Row {i}: {row}")
                
                # Check for metadata
                meta_data = response.get('metaData', {})
                print(f"Metadata keys: {list(meta_data.keys())}")
                
                if 'items' in meta_data:
                    items = meta_data['items']
                    print(f"Items count: {len(items)}")
                    for uid, item in list(items.items())[:3]:  # Show first 3 items
                        print(f"  Item {uid}: {item}")
        
        # Test data extraction
        print("\n" + "=" * 50)
        print("Testing Data Extraction:")
        
        # Create a mock indicator for testing
        class MockIndicator:
            def __init__(self, uid, name):
                self.dhis2_uid = uid
                self.name = name
                self.indicator_type = 'indicator'
        
        mock_indicator = MockIndicator(test_indicator_uid, "Test Indicator")
        
        # Initialize sync service for extraction testing
        sync_service = DataSyncService(client)
        
        # Test the extraction method directly
        value = sync_service._extract_value_from_analytics_response(response, test_indicator_uid)
        print(f"Extracted value: {value}")
        
        if value is None:
            print("Value extraction failed. Trying alternative parsing...")
            value = sync_service._extract_value_alternative_parsing(response, test_indicator_uid, None)
            print(f"Alternative parsing result: {value}")
        
        # Test fetching data through the full method
        print("\n" + "=" * 50)
        print("Testing Full Data Fetching:")
        
        value = sync_service._fetch_indicator_data(mock_indicator, test_org_unit, test_period)
        print(f"Full fetch result: {value}")
        
    except Exception as e:
        print(f"Error during testing: {str(e)}")
        import traceback
        traceback.print_exc()

def test_multiple_indicators():
    """Test multiple indicators to see which ones have data"""
    try:
        # Initialize DHIS2 client
        client = DHIS2Client(
            instance_url="https://dhims.chimgh.org/dhims",
            username="Demo",
            password="Ghana@2020"
        )
        
        # Get some active indicators from the database
        indicators = TrackedIndicator.objects.filter(is_active=True)[:5]
        
        test_org_unit = "Pug4R4IHDtN"
        test_period = "2023"
        
        print(f"Testing {len(indicators)} indicators:")
        print("-" * 50)
        
        for indicator in indicators:
            print(f"\nTesting indicator: {indicator.name} ({indicator.dhis2_uid})")
            
            try:
                response = client.get_analytics_data(
                    indicators=[indicator.dhis2_uid],
                    periods=[test_period],
                    org_units=[test_org_unit]
                )
                
                if response and isinstance(response, dict):
                    rows = response.get('rows', [])
                    print(f"  Rows returned: {len(rows)}")
                    
                    if rows:
                        print(f"  First row: {rows[0]}")
                    else:
                        print("  No data rows found")
                else:
                    print("  No response or invalid response format")
                    
            except Exception as e:
                print(f"  Error: {str(e)}")
        
    except Exception as e:
        print(f"Error during multiple indicator testing: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("DHIS2 Response Format Test")
    print("=" * 50)
    
    # Test single indicator response format
    test_dhis2_response_format()
    
    print("\n" + "=" * 50)
    print("Testing Multiple Indicators")
    print("=" * 50)
    
    # Test multiple indicators
    test_multiple_indicators()
