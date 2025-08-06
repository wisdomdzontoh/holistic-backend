#!/usr/bin/env python
"""
Check the latest sync log details
"""
import os
import sys
import django

# Add the project directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from assessments.models import DataSyncLog

def check_latest_sync_log():
    """Check the details of the latest sync log"""
    try:
        # Get the latest sync log
        latest_sync_log = DataSyncLog.objects.latest('started_at')
        
        print(f"Latest sync log details:")
        print(f"ID: {latest_sync_log.id}")
        print(f"Started at: {latest_sync_log.started_at}")
        print(f"Completed at: {latest_sync_log.completed_at}")
        print(f"Status: {latest_sync_log.status}")
        print(f"Total indicators: {latest_sync_log.total_indicators}")
        print(f"Successful indicators: {latest_sync_log.successful_indicators}")
        print(f"Failed indicators: {latest_sync_log.failed_indicators}")
        print(f"Total data points: {latest_sync_log.total_data_points}")
        print(f"Indicator UIDs count: {len(latest_sync_log.indicator_uids) if latest_sync_log.indicator_uids else 0}")
        print(f"First 5 indicator UIDs: {latest_sync_log.indicator_uids[:5] if latest_sync_log.indicator_uids else 'None'}")
        
        if latest_sync_log.error_message:
            print(f"Error message: {latest_sync_log.error_message}")
            
        # Check if any IndicatorData was created
        from assessments.models import IndicatorData
        data_points = IndicatorData.objects.filter(sync_log=latest_sync_log)
        print(f"IndicatorData records for this sync: {data_points.count()}")
        
        if data_points.exists():
            print("Sample data points:")
            for i, data_point in enumerate(data_points[:5]):
                print(f"  {i+1}. {data_point.indicator.name}: {data_point.value} (org_unit: {data_point.org_unit_id}, period: {data_point.period})")
        
    except DataSyncLog.DoesNotExist:
        print("No sync logs found")
    except Exception as e:
        print(f"Error: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    check_latest_sync_log() 