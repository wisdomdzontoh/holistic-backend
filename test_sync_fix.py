#!/usr/bin/env python
"""
Test script to test the sync fix with a single indicator
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

def test_sync_fix():
    """Test the sync fix with a single indicator"""
    print("Testing sync fix...")
    
    try:
        # Create DHIS2 client
        dhis2_client = DHIS2Client(
            instance_url='https://dhims.chimgh.org/dhims',
            username='Demo',
            password='Ghana@2020'
        )
        
        # Create sync service
        sync_service = DataSyncService(dhis2_client)
        
        # Test with a single indicator that we know has data
        sync_request = {
            'sync_type': 'indicator',
            'dhis2_instance_url': 'https://dhims.chimgh.org/dhims',
            'org_unit_ids': ['pNf9RX5OfpD'],
            'indicator_uids': ['sJPfP23pR4G'],  # The indicator we tested
            'period_start': '2023-01-01',
            'period_end': '2023-12-31',
            'calculate_scores': False
        }
        
        print("Starting sync with single indicator...")
        sync_log = sync_service.sync_data(sync_request)
        
        print(f"\nSync completed:")
        print(f"  Sync ID: {sync_log.id}")
        print(f"  Status: {sync_log.status}")
        print(f"  Total indicators: {sync_log.total_indicators}")
        print(f"  Successful indicators: {sync_log.successful_indicators}")
        print(f"  Failed indicators: {sync_log.failed_indicators}")
        print(f"  Total data points: {sync_log.total_data_points}")
        
        # Check if data points were created
        data_points = IndicatorData.objects.filter(sync_log=sync_log)
        print(f"\nData points created: {data_points.count()}")
        
        for data_point in data_points:
            print(f"  - {data_point.indicator.name}: {data_point.value} for {data_point.org_unit_name} ({data_point.period})")
        
        # Test the extraction logic directly
        print(f"\nTesting extraction logic directly...")
        
        # Get the indicator object
        from indicators.models import TrackedIndicator
        indicator = TrackedIndicator.objects.get(dhis2_uid='sJPfP23pR4G')
        
        # Test with the same parameters
        value = sync_service._fetch_indicator_data(
            indicator=indicator,
            org_unit_id='pNf9RX5OfpD',
            period='2023'
        )
        
        print(f"Direct extraction result: {value}")
        
    except Exception as e:
        print(f"Error during testing: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    test_sync_fix() 