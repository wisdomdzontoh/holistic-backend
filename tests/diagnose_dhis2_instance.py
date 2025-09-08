#!/usr/bin/env python
"""
Diagnostic script to check DHIS2 instance availability
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

def diagnose_dhis2_instance():
    """Diagnose what's available in the DHIS2 instance"""
    print("=== DHIS2 Instance Diagnosis ===")
    
    # Create DHIS2 client with user credentials
    dhis2_client = DHIS2Client(
        instance_url='https://dhims.chimgh.org/dhims',
        username='Demo',
        password='Ghana@2020'
    )
    
    # Initialize variables
    org_units = []
    periods = []
    indicators = []
    
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
        try:
            system_info = dhis2_client.get_system_info()
            print(f"System: {system_info.get('systemName', 'Unknown')}")
            print(f"Version: {system_info.get('version', 'Unknown')}")
            print(f"Date: {system_info.get('date', 'Unknown')}")
        except Exception as e:
            print(f"Error getting system info: {e}")
        
        # Get available periods
        print("\n3. Getting available periods...")
        try:
            periods = dhis2_client.get_periods()
            print(f"Found {len(periods)} period types")
            
            # Show some recent periods
            recent_periods = periods[:10] if len(periods) > 10 else periods
            for period in recent_periods:
                print(f"  - {period.get('name', 'Unknown')} ({period.get('id', 'Unknown')})")
                
            # Test if 202401 exists
            period_202401 = next((p for p in periods if p.get('id') == '202401'), None)
            if period_202401:
                print(f"  ✓ Period 202401 found: {period_202401.get('name')}")
            else:
                print(f"  ✗ Period 202401 NOT found")
                
        except Exception as e:
            print(f"Error getting periods: {e}")
        
        # Get org units
        print("\n4. Getting org units...")
        try:
            org_units = dhis2_client.get_org_units(limit=10)
            print(f"Found {len(org_units)} org units (showing first 10)")
            
            for org_unit in org_units:
                print(f"  - {org_unit.get('name', 'Unknown')} ({org_unit.get('id', 'Unknown')})")
                
            # Test if ImspTQPwCqd exists
            org_unit_demo = next((ou for ou in org_units if ou.get('id') == 'ImspTQPwCqd'), None)
            if org_unit_demo:
                print(f"  ✓ Org unit ImspTQPwCqd found: {org_unit_demo.get('name')}")
            else:
                print(f"  ✗ Org unit ImspTQPwCqd NOT found")
                
        except Exception as e:
            print(f"Error getting org units: {e}")
        
        # Get indicators
        print("\n5. Getting indicators...")
        try:
            indicators = dhis2_client.get_indicators(limit=10)
            print(f"Found {len(indicators)} indicators (showing first 10)")
            
            for indicator in indicators:
                print(f"  - {indicator.get('name', 'Unknown')} ({indicator.get('id', 'Unknown')})")
                
            # Test if XLn1cZZTA0H exists
            indicator_test = next((ind for ind in indicators if ind.get('id') == 'XLn1cZZTA0H'), None)
            if indicator_test:
                print(f"  ✓ Indicator XLn1cZZTA0H found: {indicator_test.get('name')}")
            else:
                print(f"  ✗ Indicator XLn1cZZTA0H NOT found")
                
        except Exception as e:
            print(f"Error getting indicators: {e}")
        
        # Test analytics with valid data
        print("\n6. Testing analytics with valid data...")
        if org_units and periods:
            # Use first available org unit and period
            test_org_unit = org_units[0]['id']
            test_period = periods[0]['id']
            
            print(f"Testing with org unit: {org_units[0].get('name')} ({test_org_unit})")
            print(f"Testing with period: {periods[0].get('name')} ({test_period})")
            
            if indicators:
                test_indicator = indicators[0]['id']
                print(f"Testing with indicator: {indicators[0].get('name')} ({test_indicator})")
                
                try:
                    response = dhis2_client.get_analytics_data(
                        indicators=[test_indicator],
                        periods=[test_period],
                        org_units=[test_org_unit]
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
                        
                except Exception as e:
                    print(f"Error testing analytics: {e}")
        
        # Test with different period formats
        print("\n7. Testing with different period formats...")
        test_periods = [
            "2024",    # Year 2024
            "2023",    # Year 2023
            "2024Q1",  # Quarter 1 2024
            "2023Q4",  # Quarter 4 2023
            "THIS_YEAR",  # Relative period
            "LAST_YEAR"   # Relative period
        ]
        
        if org_units and indicators:
            test_org_unit = org_units[0]['id']
            test_indicator = indicators[0]['id']
            
            for period in test_periods:
                print(f"\nTesting period: {period}")
                try:
                    response = dhis2_client.get_analytics_data(
                        indicators=[test_indicator],
                        periods=[period],
                        org_units=[test_org_unit]
                    )
                    
                    if isinstance(response, dict) and 'rows' in response:
                        print(f"  ✓ Rows returned: {len(response['rows'])}")
                        if response['rows']:
                            print(f"  Sample data: {response['rows'][0]}")
                    else:
                        print(f"  ✗ No data returned")
                        
                except Exception as e:
                    print(f"  ✗ Error: {str(e)}")
        
    except Exception as e:
        print(f"Error during diagnosis: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    diagnose_dhis2_instance() 