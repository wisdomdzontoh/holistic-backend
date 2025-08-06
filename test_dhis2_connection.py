#!/usr/bin/env python
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from dhis2_auth.dhis_client import DHIS2Client
from indicators.models import TrackedIndicator
from configurations.models import AssessmentPeriod
import logging

# Setup logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def test_dhis2_connection():
    """Test DHIS2 connection and data fetching"""
    
    # Test connection
    print("Testing DHIS2 connection...")
    client = DHIS2Client(
        instance_url="https://dhims.chimgh.org/dhims",
        username="admin",
        password="district"
    )
    
    try:
        # Test basic connection
        connection_test = client.test_connection()
        print(f"Connection test result: {connection_test}")
        
        if connection_test:
            print("✅ DHIS2 connection successful!")
            
            # Test authentication
            try:
                user_info = client.authenticate_user()
                print(f"✅ Authentication successful! User: {user_info.get('name', 'Unknown')}")
            except Exception as e:
                print(f"❌ Authentication failed: {str(e)}")
                return False
            
            # Get some tracked indicators
            indicators = TrackedIndicator.objects.filter(is_active=True)[:5]
            print(f"\nTesting data fetch for {indicators.count()} indicators:")
            
            # Get current period
            current_period = AssessmentPeriod.objects.filter(is_current=True).first()
            if current_period:
                period_name = current_period.name.replace(' ', '')
                print(f"Using period: {period_name}")
                
                for indicator in indicators:
                    print(f"\nTesting indicator: {indicator.name} (UID: {indicator.dhis2_uid})")
                    
                    try:
                        # Test analytics data fetch
                        response = client.get_analytics_data(
                            data_elements=[indicator.dhis2_uid],
                            periods=[period_name],
                            org_units=["LEVEL-1"]  # Use a top-level org unit
                        )
                        
                        print(f"Response keys: {list(response.keys()) if response else 'No response'}")
                        
                        if response and 'rows' in response:
                            print(f"Found {len(response['rows'])} data rows")
                            for i, row in enumerate(response['rows'][:3]):  # Show first 3 rows
                                print(f"  Row {i}: {row}")
                        else:
                            print("No data rows found")
                            
                    except Exception as e:
                        print(f"❌ Error fetching data for {indicator.name}: {str(e)}")
                        
            else:
                print("❌ No current assessment period found")
                
        else:
            print("❌ DHIS2 connection failed!")
            return False
            
    except Exception as e:
        print(f"❌ Connection test failed: {str(e)}")
        return False
    
    return True

if __name__ == "__main__":
        test_dhis2_connection() 