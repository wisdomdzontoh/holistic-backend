#!/usr/bin/env python
"""
Comprehensive test script to diagnose and fix DHIS2 data fetching issues
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

from dhis2_auth.dhis_client import DHIS2Client
from indicators.models import TrackedIndicator
from assessments.models import DataSyncLog, IndicatorData

def test_dhis2_comprehensive():
    """Comprehensive test of DHIS2 data fetching"""
    print("=== Comprehensive DHIS2 Data Fetching Test ===")
    
    # Create DHIS2 client
    dhis2_client = DHIS2Client(
        instance_url='https://dhims.chimgh.org/dhims',
        username='Demo',
        password='Ghana@2020'
    )
    
    try:
        # Test 1: Basic connection
        print("\n1. Testing basic connection...")
        if dhis2_client.test_connection():
            print("✓ Connection successful")
        else:
            print("✗ Connection failed")
            return
        
        # Test 2: Get user info
        print("\n2. Testing user authentication...")
        try:
            user_info = dhis2_client.authenticate_user()
            print(f"✓ Authentication successful for user: {user_info.get('name', 'Unknown')}")
            print(f"  User ID: {user_info.get('id', 'Unknown')}")
            print(f"  Username: {user_info.get('userCredentials', {}).get('username', 'Unknown')}")
        except Exception as e:
            print(f"✗ Authentication failed: {str(e)}")
            return
        
        # Test 3: Get org units
        print("\n3. Testing org units...")
        try:
            org_units = dhis2_client.get_user_accessible_org_units()
            print(f"✓ Found {len(org_units)} accessible org units")
            if org_units:
                test_org_unit = org_units[0]
                print(f"  Test org unit: {test_org_unit.get('name')} ({test_org_unit.get('id')})")
            else:
                print("  No org units found")
                return
        except Exception as e:
            print(f"✗ Failed to get org units: {str(e)}")
            return
        
        # Test 4: Get periods
        print("\n4. Testing periods...")
        try:
            periods = dhis2_client.get_periods()
            print(f"✓ Found {len(periods)} periods")
            if periods:
                test_period = periods[0]
                print(f"  Test period: {test_period.get('name')} ({test_period.get('id')})")
            else:
                print("  No periods found")
                return
        except Exception as e:
            print(f"✗ Failed to get periods: {str(e)}")
            return
        
        # Test 5: Get indicators
        print("\n5. Testing indicators...")
        try:
            indicators = dhis2_client.get_indicators(limit=5)
            print(f"✓ Found {len(indicators)} indicators")
            if indicators:
                test_indicator = indicators[0]
                print(f"  Test indicator: {test_indicator.get('name')} ({test_indicator.get('id')})")
            else:
                print("  No indicators found")
                return
        except Exception as e:
            print(f"✗ Failed to get indicators: {str(e)}")
            return
        
        # Test 6: Test analytics with different parameter formats
        print("\n6. Testing analytics with different parameter formats...")
        test_org_unit_id = test_org_unit.get('id')
        test_indicator_id = test_indicator.get('id')
        test_period_id = test_period.get('id')
        
        # Test different parameter combinations
        test_cases = [
            {
                'name': 'Basic analytics with indicators',
                'params': {
                    'indicators': [test_indicator_id],
                    'periods': [test_period_id],
                    'org_units': [test_org_unit_id]
                }
            },
            {
                'name': 'Analytics with data elements (same UID)',
                'params': {
                    'data_elements': [test_indicator_id],
                    'periods': [test_period_id],
                    'org_units': [test_org_unit_id]
                }
            },
            {
                'name': 'Analytics with multiple periods',
                'params': {
                    'indicators': [test_indicator_id],
                    'periods': [test_period_id, '2024', '2023'],
                    'org_units': [test_org_unit_id]
                }
            },
            {
                'name': 'Analytics with relative periods',
                'params': {
                    'indicators': [test_indicator_id],
                    'periods': ['THIS_YEAR', 'LAST_YEAR'],
                    'org_units': [test_org_unit_id]
                }
            }
        ]
        
        for i, test_case in enumerate(test_cases, 1):
            print(f"\n  Test case {i}: {test_case['name']}")
            try:
                response = dhis2_client.get_analytics_data(**test_case['params'])
                
                if isinstance(response, dict):
                    print(f"    ✓ Response received")
                    print(f"    Response keys: {list(response.keys())}")
                    
                    if 'rows' in response:
                        print(f"    Rows: {len(response['rows'])}")
                        if response['rows']:
                            print(f"    Sample row: {response['rows'][0]}")
                        else:
                            print(f"    No data rows returned")
                    
                    if 'headers' in response:
                        print(f"    Headers: {[h.get('name', 'Unknown') for h in response['headers']]}")
                    
                    if 'metaData' in response:
                        print(f"    Metadata items: {len(response['metaData'].get('items', {}))}")
                else:
                    print(f"    ✗ Unexpected response type: {type(response)}")
                    
            except Exception as e:
                print(f"    ✗ Failed: {str(e)}")
                if "409" in str(e):
                    print(f"    This is a 409 Conflict error - parameter format issue")
        
        # Test 7: Test with tracked indicators from database
        print("\n7. Testing with tracked indicators from database...")
        try:
            tracked_indicators = TrackedIndicator.objects.filter(is_active=True)[:3]
            print(f"✓ Found {len(tracked_indicators)} active tracked indicators")
            
            for indicator in tracked_indicators:
                print(f"\n  Testing indicator: {indicator.name} ({indicator.dhis2_uid})")
                print(f"  Type: {indicator.indicator_type}")
                
                try:
                    if indicator.indicator_type == 'indicator':
                        response = dhis2_client.get_analytics_data(
                            indicators=[indicator.dhis2_uid],
                            periods=[test_period_id],
                            org_units=[test_org_unit_id]
                        )
                    elif indicator.indicator_type == 'dataElement':
                        response = dhis2_client.get_analytics_data(
                            data_elements=[indicator.dhis2_uid],
                            periods=[test_period_id],
                            org_units=[test_org_unit_id]
                        )
                    else:
                        print(f"    Skipping unsupported type: {indicator.indicator_type}")
                        continue
                    
                    if isinstance(response, dict) and 'rows' in response:
                        print(f"    ✓ Data rows: {len(response['rows'])}")
                        if response['rows']:
                            print(f"    Sample data: {response['rows'][0]}")
                        else:
                            print(f"    No data returned")
                    else:
                        print(f"    ✗ Unexpected response format")
                        
                except Exception as e:
                    print(f"    ✗ Failed: {str(e)}")
                    if "409" in str(e):
                        print(f"    This is a 409 Conflict error")
        
        # Test 8: Test different period formats
        print("\n8. Testing different period formats...")
        period_formats = [
            "2024",      # Year
            "2024Q1",    # Quarter
            "202401",    # Month
            "2024-01",   # Month with dash
            "THIS_YEAR", # Relative
            "LAST_YEAR", # Relative
            "LAST_MONTH" # Relative
        ]
        
        for period_format in period_formats:
            print(f"\n  Testing period format: {period_format}")
            try:
                response = dhis2_client.get_analytics_data(
                    indicators=[test_indicator_id],
                    periods=[period_format],
                    org_units=[test_org_unit_id]
                )
                
                if isinstance(response, dict) and 'rows' in response:
                    print(f"    ✓ Rows: {len(response['rows'])}")
                else:
                    print(f"    ✗ No data")
                    
            except Exception as e:
                print(f"    ✗ Failed: {str(e)}")
        
        print("\n=== Test completed ===")
        
    except Exception as e:
        print(f"Test failed: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    test_dhis2_comprehensive()
