#!/usr/bin/env python
"""
Final test script to test the sync with fixed authentication and org unit handling
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

from assessments.services import DataSyncService
from dhis2_auth.dhis_client import DHIS2Client
from assessments.models import DataSyncLog, IndicatorData
from indicators.models import TrackedIndicator

def test_sync_final():
    """Test the final sync with fixed authentication and org unit handling"""
    print("=== Testing Final Sync with Fixed Authentication ===")
    
    # Create DHIS2 client with working credentials
    dhis2_client = DHIS2Client(
        instance_url='https://dhims.chimgh.org/dhims',
        username='Demo',
        password='Ghana@2020'
    )
    
    # Test authentication first
    print("\n1. Testing authentication...")
    try:
        user_info = dhis2_client.authenticate_user()
        print(f"✅ Authentication successful: {user_info.get('name', 'Unknown')}")
    except Exception as e:
        print(f"❌ Authentication failed: {str(e)}")
        return
    
    # Create sync service
    sync_service = DataSyncService(dhis2_client)
    
    # Test sync request
    sync_request = {
        'sync_type': 'period',
        'dhis2_instance_url': 'https://dhims.chimgh.org/dhims',
        'period_start': '2023-01-01',
        'period_end': '2023-12-31',
        'org_unit_ids': ['pNf9RX5OfpD'],  # Use org unit ID directly
        'indicator_uids': ['sJPfP23pR4G'],  # Test with working indicator
        'calculate_scores': False
    }
    
    print("\n2. Testing sync with fixed org unit handling...")
    try:
        sync_log = sync_service.sync_data(sync_request)
        
        print(f"✅ Sync completed successfully!")
        print(f"   Sync ID: {sync_log.id}")
        print(f"   Status: {sync_log.status}")
        print(f"   Total indicators: {sync_log.total_indicators}")
        print(f"   Successful indicators: {sync_log.successful_indicators}")
        print(f"   Failed indicators: {sync_log.failed_indicators}")
        print(f"   Total data points: {sync_log.total_data_points}")
        
        # Check if data points were created
        data_points = IndicatorData.objects.filter(sync_log=sync_log)
        print(f"   Actual data points in DB: {data_points.count()}")
        
        if data_points.exists():
            print("   Sample data points:")
            for dp in data_points[:5]:
                print(f"     - {dp.indicator.name}: {dp.value} ({dp.period})")
        
    except Exception as e:
        print(f"❌ Sync failed: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_sync_final() 