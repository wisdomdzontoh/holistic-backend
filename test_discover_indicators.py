#!/usr/bin/env python
"""
Test script to discover available indicators and data elements in DHIS2
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

def test_discover_indicators():
    """Discover what indicators and data elements are available in DHIS2"""
    print("Discovering available indicators and data elements...")
    
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
        
        # Get indicators
        print("\n2. Getting indicators...")
        try:
            indicators = dhis2_client.get_indicators(limit=10)
            print(f"Found {len(indicators)} indicators (showing first 10)")
            
            for indicator in indicators:
                print(f"  - {indicator.get('name', 'Unknown')} ({indicator.get('id', 'Unknown')})")
                print(f"    Description: {indicator.get('description', 'No description')}")
                print(f"    Numerator: {indicator.get('numerator', 'No numerator')}")
                print(f"    Denominator: {indicator.get('denominator', 'No denominator')}")
                print()
                
        except Exception as e:
            print(f"Error getting indicators: {str(e)}")
        
        # Get data elements
        print("\n3. Getting data elements...")
        try:
            data_elements = dhis2_client.get_data_elements(limit=10)
            print(f"Found {len(data_elements)} data elements (showing first 10)")
            
            for element in data_elements:
                print(f"  - {element.get('name', 'Unknown')} ({element.get('id', 'Unknown')})")
                print(f"    Value Type: {element.get('valueType', 'Unknown')}")
                print(f"    Domain Type: {element.get('domainType', 'Unknown')}")
                print()
                
        except Exception as e:
            print(f"Error getting data elements: {str(e)}")
        
        # Test analytics with a valid indicator if we found any
        if 'indicators' in locals() and indicators:
            sample_indicator = indicators[0]['id']
            print(f"\n4. Testing analytics with indicator: {sample_indicator}")
            print(f"Indicator name: {indicators[0].get('name', 'Unknown')}")
            
            # Get a sample org unit
            org_units = dhis2_client.get_org_units()
            if org_units:
                sample_org_unit = org_units[0]['id']
                print(f"Using org unit: {org_units[0].get('name', 'Unknown')} ({sample_org_unit})")
                
                # Test with a recent period
                test_period = "202501"  # January 2025
                
                try:
                    response = dhis2_client.get_analytics_data(
                        indicators=[sample_indicator],
                        periods=[test_period],
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
                        
                except Exception as e:
                    print(f"Error testing analytics: {str(e)}")
        
        # Test with data elements if we found any
        if 'data_elements' in locals() and data_elements:
            sample_data_element = data_elements[0]['id']
            print(f"\n5. Testing analytics with data element: {sample_data_element}")
            print(f"Data element name: {data_elements[0].get('name', 'Unknown')}")
            
            if org_units:
                sample_org_unit = org_units[0]['id']
                test_period = "202501"
                
                try:
                    response = dhis2_client.get_analytics_data(
                        data_elements=[sample_data_element],
                        periods=[test_period],
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
                        
                except Exception as e:
                    print(f"Error testing analytics with data element: {str(e)}")
        
    except Exception as e:
        print(f"Error during testing: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    test_discover_indicators() 