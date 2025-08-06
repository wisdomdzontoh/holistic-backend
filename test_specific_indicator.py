import os
import sys
import django
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any

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

from dhis2_auth.dhis_client import DHIS2Client, DHIS2ClientFactory

logger = logging.getLogger(__name__)

def test_specific_indicator(indicator_uid: str):
    """
    Tests if a specific indicator exists and can fetch data for it.
    """
    print(f"\n=== Testing specific indicator: {indicator_uid} ===")
    
    # Use the default DHIS2 instance URL from settings
    instance_url = os.getenv('DEFAULT_DHIS2_INSTANCE', 'https://dhims.chimgh.org/dhims')
    
    # Use the provided credentials
    username = 'Demo'
    password = 'Ghana@2020'

    try:
        client = DHIS2ClientFactory.create_client(instance_url, username, password)
        
        # 1. Test basic connection
        print("1. Testing basic connection...")
        if client.test_connection():
            print("   ✓ Connection successful!")
        else:
            print("   ✗ Connection failed.")
            return

        # 2. Authenticate user
        print("2. Authenticating user...")
        user_info = client.authenticate_user()
        if user_info:
            print(f"   ✓ Authentication successful! User: {user_info.get('name')}")
        else:
            print("   ✗ Authentication failed.")
            return

        # 3. Get indicator metadata to confirm its existence and name
        print(f"3. Getting metadata for indicator: {indicator_uid}")
        indicator_metadata = client.get_indicators(filter_query=f"id:eq:{indicator_uid}")
        
        if indicator_metadata and len(indicator_metadata) > 0:
            indicator_name = indicator_metadata[0].get('displayName', 'Unknown Name')
            print(f"   ✓ Indicator found! Name: {indicator_name}")
            print(f"   ✓ Indicator UID: {indicator_uid}")
            print(f"   ✓ Indicator details: {indicator_metadata[0]}")
        else:
            print(f"   ✗ Indicator {indicator_uid} NOT FOUND in the DHIS2 system.")
            print("   This means the indicator either:")
            print("   - Does not exist in this DHIS2 instance")
            print("   - Is not accessible to the current user")
            print("   - Has been deleted or renamed")
            return

        # 4. Attempt to fetch analytics data for the indicator
        print(f"4. Attempting to fetch analytics data for indicator: {indicator_uid}")
        
        # Get a recent period (e.g., last month or current month)
        periods = ["202406"] # Example: June 2024
        
        # Get a sample org unit from the user's accessible org units
        org_units = client.get_user_accessible_org_units()
        if not org_units:
            print("   ✗ No accessible organisation units found for the user.")
            return
        
        # Use the first accessible org unit for testing
        test_org_unit_uid = org_units[0].get('id')
        test_org_unit_name = org_units[0].get('displayName')
        print(f"   Using period: {periods[0]} and org unit: {test_org_unit_name} ({test_org_unit_uid})")

        analytics_data = client.get_analytics_data(
            indicators=[indicator_uid],
            periods=periods,
            org_units=[test_org_unit_uid]
        )

        if analytics_data and 'rows' in analytics_data:
            print(f"   ✓ Successfully fetched analytics data. Number of rows: {len(analytics_data['rows'])}")
            if len(analytics_data['rows']) > 0:
                print("   Sample data row:")
                print(analytics_data['rows'][0])
            else:
                print("   (No data rows returned for this period/org unit, which might be expected)")
        else:
            print("   ✗ Failed to fetch analytics data or unexpected response format.")
            print(f"   Response: {analytics_data}")

    except Exception as e:
        print(f"An unexpected error occurred: {e}")

def search_for_indicator_in_list(indicator_uid: str):
    """
    Search for an indicator in the full list to see if it exists
    """
    print(f"\n=== Searching for indicator {indicator_uid} in full indicator list ===")
    
    instance_url = os.getenv('DEFAULT_DHIS2_INSTANCE', 'https://dhims.chimgh.org/dhims')
    username = 'Demo'
    password = 'Ghana@2020'

    try:
        client = DHIS2ClientFactory.create_client(instance_url, username, password)
        
        # Get all indicators
        print("Fetching all indicators from DHIS2...")
        all_indicators = client.get_indicators()
        
        if not all_indicators:
            print("No indicators found.")
            return
        
        print(f"Total indicators found: {len(all_indicators)}")
        
        # Search for the specific indicator
        found_indicator = None
        for indicator in all_indicators:
            if indicator.get('id') == indicator_uid:
                found_indicator = indicator
                break
        
        if found_indicator:
            print(f"✓ FOUND! Indicator {indicator_uid} exists in the system.")
            print(f"   Name: {found_indicator.get('displayName')}")
            print(f"   UID: {found_indicator.get('id')}")
            print(f"   Description: {found_indicator.get('description', 'No description')}")
        else:
            print(f"✗ NOT FOUND! Indicator {indicator_uid} does not exist in this DHIS2 system.")
            print("This could mean:")
            print("- The indicator ID is incorrect")
            print("- The indicator has been deleted")
            print("- The indicator exists in a different DHIS2 instance")
            print("- The indicator is not accessible to the current user")
            
            # Show some similar indicators (if any)
            print("\nSimilar indicator IDs found:")
            similar_count = 0
            for indicator in all_indicators:
                indicator_id = indicator.get('id', '')
                if indicator_uid.lower() in indicator_id.lower() or indicator_id.lower() in indicator_uid.lower():
                    print(f"   - {indicator.get('displayName')} ({indicator_id})")
                    similar_count += 1
                    if similar_count >= 5:  # Limit to 5 similar results
                        break
            
            if similar_count == 0:
                print("   (No similar indicator IDs found)")

    except Exception as e:
        print(f"Error searching for indicator: {e}")

if __name__ == '__main__':
    indicator_to_test = "sJPfP23pR4G"
    
    # First, search in the full list
    search_for_indicator_in_list(indicator_to_test)
    
    # Then, try to get specific metadata
    test_specific_indicator(indicator_to_test) 