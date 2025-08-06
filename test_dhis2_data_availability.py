#!/usr/bin/env python
"""
Test script to check DHIS2 data availability
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

def test_dhis2_data_availability():
    """Test what data is available in DHIS2 demo instance"""
    print("Testing DHIS2 data availability...")
    
    # Create DHIS2 client with the actual instance URL used in the application
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
        
        # Get system info
        print("\n2. Getting system info...")
        system_info = dhis2_client.get_system_info()
        print(f"System: {system_info.get('systemName', 'Unknown')}")
        print(f"Version: {system_info.get('version', 'Unknown')}")
        
        # Get available periods
        print("\n3. Getting available periods...")
        periods = dhis2_client.get_periods()
        print(f"Found {len(periods)} period types")
        
        # Show some recent periods
        recent_periods = periods[:10] if len(periods) > 10 else periods
        for period in recent_periods:
            print(f"  - {period.get('name', 'Unknown')} ({period.get('id', 'Unknown')})")
        
        # Get org units
        print("\n4. Getting org units...")
        org_units = dhis2_client.get_org_units()
        print(f"Found {len(org_units)} org units (showing first 5)")
        
        for org_unit in org_units[:5]:
            print(f"  - {org_unit.get('name', 'Unknown')} ({org_unit.get('id', 'Unknown')})")
        
        # Test analytics with a recent period
        if periods:
            recent_period = periods[0]['id']
            print(f"\n5. Testing analytics with period: {recent_period}")
            
            # Test with a sample indicator
            sample_indicator = "XLn1cZZTA0H"  # Grand Total Revenue (NHIS)
            
            if org_units:
                sample_org_unit = org_units[0]['id']
                print(f"Using org unit: {org_units[0].get('name', 'Unknown')} ({sample_org_unit})")
                
                # Make analytics request
                response = dhis2_client.get_analytics_data(
                    indicators=[sample_indicator],
                    periods=[recent_period],
                    org_units=[sample_org_unit]
                )
                
                print(f"Analytics response type: {type(response)}")
                if isinstance(response, dict):
                    print(f"Response keys: {list(response.keys())}")
                    if 'rows' in response:
                        print(f"Number of rows: {len(response['rows'])}")
                        if response['rows']:
                            print(f"Sample row: {response['rows'][0]}")
                    if 'headers' in response:
                        print(f"Headers: {[h.get('name', 'Unknown') for h in response['headers']]}")
                else:
                    print(f"Unexpected response: {response}")
        
        # Test with different period formats
        print("\n6. Testing with different period formats...")
        test_periods = [
            "2024Q1",  # Quarter 1 2024
            "2024",    # Year 2024
            "2023Q4",  # Quarter 4 2023
            "2023",    # Year 2023
            "THIS_YEAR",  # Relative period
            "LAST_YEAR"   # Relative period
        ]
        
        for period in test_periods:
            print(f"\nTesting period: {period}")
            try:
                response = dhis2_client.get_analytics_data(
                    indicators=[sample_indicator],
                    periods=[period],
                    org_units=[sample_org_unit] if org_units else None
                )
                
                if isinstance(response, dict) and 'rows' in response:
                    print(f"  Rows returned: {len(response['rows'])}")
                    if response['rows']:
                        print(f"  Sample data: {response['rows'][0]}")
                else:
                    print(f"  No data returned")
                    
            except Exception as e:
                print(f"  Error: {str(e)}")
        
    except Exception as e:
        print(f"Error during testing: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    test_dhis2_data_availability() 