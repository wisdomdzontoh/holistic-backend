#!/usr/bin/env python
"""
Test script to run the sync with detailed logging
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

def test_sync_with_logging():
    """Test the sync process with detailed logging"""
    print("Starting sync test with detailed logging...")
    
    # Create a sync request
    sync_request = {
        'period_start': '2024-01-01',
        'period_end': '2024-12-31'
    }
    
    # Create DHIS2 client with default credentials
    dhis2_client = DHIS2Client(
        instance_url='https://dhis2.org/demo',
        username='admin',
        password='district'
    )
    
    # Create sync service
    sync_service = DataSyncService(dhis2_client=dhis2_client)
    
    try:
        # Run the sync
        print("Running sync...")
        sync_log = sync_service.sync_data(sync_request)
        
        print(f"\nSync completed!")
        print(f"Sync log ID: {sync_log.id}")
        print(f"Started at: {sync_log.started_at}")
        print(f"Completed at: {sync_log.completed_at}")
        print(f"Status: {sync_log.status}")
        print(f"Total indicators: {sync_log.total_indicators}")
        print(f"Successful indicators: {sync_log.successful_indicators}")
        print(f"Failed indicators: {sync_log.failed_indicators}")
        print(f"Total data points: {sync_log.total_data_points}")
        print(f"Indicator UIDs: {sync_log.indicator_uids}")
        
        if sync_log.error_message:
            print(f"Error message: {sync_log.error_message}")
            
    except Exception as e:
        print(f"Error during sync: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    test_sync_with_logging() 