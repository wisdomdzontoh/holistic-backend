#!/usr/bin/env python
"""
Detailed test to debug the sync process step by step
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

def test_sync_detailed():
    """Test the sync process step by step"""
    print("Testing sync process step by step...")
    
    try:
        # Create DHIS2 client
        dhis2_client = DHIS2Client(
            instance_url='https://dhims.chimgh.org/dhims',
            username='Demo',
            password='Ghana@2020'
        )
        
        # Get the indicator
        indicator = TrackedIndicator.objects.get(dhis2_uid='sJPfP23pR4G')
        print(f"Testing with indicator: {indicator.name} ({indicator.dhis2_uid})")
        
        # Create sync service
        sync_service = DataSyncService(dhis2_client)
        
        # Test the fetch method directly
        print("\n1. Testing _fetch_indicator_data directly...")
        value = sync_service._fetch_indicator_data(
            indicator=indicator,
            org_unit_id='pNf9RX5OfpD',
            period='2023'
        )
        print(f"Fetched value: {value}")
        
        if value is not None:
            print("✓ Value fetched successfully")
            
            # Test creating a data point manually
            print("\n2. Testing manual data point creation...")
            try:
                data_point, created = IndicatorData.objects.get_or_create(
                    indicator=indicator,
                    org_unit_id='pNf9RX5OfpD',
                    period='2023',
                    defaults={
                        'value': value,
                        'org_unit_name': 'Test Org Unit'
                    }
                )
                
                if created:
                    print(f"✓ Data point created successfully: {data_point.id}")
                else:
                    print(f"✓ Data point updated: {data_point.id}")
                    data_point.value = value
                    data_point.save()
                
                print(f"Data point details:")
                print(f"  - ID: {data_point.id}")
                print(f"  - Indicator: {data_point.indicator.name}")
                print(f"  - Org Unit: {data_point.org_unit_id}")
                print(f"  - Period: {data_point.period}")
                print(f"  - Value: {data_point.value}")
                
            except Exception as e:
                print(f"✗ Error creating data point: {str(e)}")
                import traceback
                traceback.print_exc()
        
        # Test the enhanced sync method directly
        print("\n3. Testing _sync_indicator_data_enhanced directly...")
        try:
            # Create a sync log for testing
            sync_log = DataSyncLog.objects.create(
                sync_type='indicator',
                dhis2_instance_url='https://dhims.chimgh.org/dhims',
                status='in_progress'
            )
            
            total_points = sync_service._sync_indicator_data_enhanced(
                indicator=indicator,
                org_units=['pNf9RX5OfpD'],
                periods=['2023'],
                sync_log=sync_log
            )
            
            print(f"Enhanced sync completed: {total_points} data points")
            
            # Check if data points were created
            data_points = IndicatorData.objects.filter(sync_log=sync_log)
            print(f"Data points in sync log: {data_points.count()}")
            
            for dp in data_points:
                print(f"  - {dp.indicator.name}: {dp.value} for {dp.org_unit_name} ({dp.period})")
                
        except Exception as e:
            print(f"✗ Error in enhanced sync: {str(e)}")
            import traceback
            traceback.print_exc()
        
        # Test the full sync process
        print("\n4. Testing full sync process...")
        try:
            sync_request = {
                'sync_type': 'indicator',
                'dhis2_instance_url': 'https://dhims.chimgh.org/dhims',
                'org_unit_ids': ['pNf9RX5OfpD'],
                'indicator_uids': ['sJPfP23pR4G'],
                'period_start': '2023-01-01',
                'period_end': '2023-12-31',
                'calculate_scores': False
            }
            
            sync_log = sync_service.sync_data(sync_request)
            
            print(f"Full sync completed:")
            print(f"  - Sync ID: {sync_log.id}")
            print(f"  - Status: {sync_log.status}")
            print(f"  - Total indicators: {sync_log.total_indicators}")
            print(f"  - Successful indicators: {sync_log.successful_indicators}")
            print(f"  - Failed indicators: {sync_log.failed_indicators}")
            print(f"  - Total data points: {sync_log.total_data_points}")
            
            # Check data points
            data_points = IndicatorData.objects.filter(sync_log=sync_log)
            print(f"Data points created: {data_points.count()}")
            
            for dp in data_points:
                print(f"  - {dp.indicator.name}: {dp.value} for {dp.org_unit_name} ({dp.period})")
                
        except Exception as e:
            print(f"✗ Error in full sync: {str(e)}")
            import traceback
            traceback.print_exc()
        
    except Exception as e:
        print(f"Error during testing: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    test_sync_detailed() 