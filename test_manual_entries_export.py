#!/usr/bin/env python
"""
Test script to verify manual entries are properly included in Excel export
"""
import os
import sys
import django
from datetime import datetime

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from assessments.services import RealTimeDHIS2Service
from indicators.models import TrackedIndicator
from configurations.models import Objective

def test_manual_entries_export():
    """Test that manual entries are properly included in Excel export"""
    
    # Create test data structure similar to what the frontend sends
    test_assessment_config = {
        'org_unit_ids': ['test_org_unit'],
        'periods': [
            {'code': '2024Q1', 'name': 'Q1 2024'},
            {'code': '2024Q2', 'name': 'Q2 2024'}
        ],
        'manual_entries': {
            '1': {  # Indicator ID 1
                '2024Q1': 85.5,  # Manual value for Q1
                '2024Q2': 92.3   # Manual value for Q2
            },
            '2': {  # Indicator ID 2
                '2024Q1': 75.0,
                '2024Q2': 78.5
            }
        }
    }
    
    # Create a mock request object
    class MockRequest:
        def __init__(self):
            self.session = {'session_key': 'test_session'}
            self.user = None
    
    mock_request = MockRequest()
    
    # Initialize the service
    service = RealTimeDHIS2Service()
    
    try:
        # Fetch assessment data with manual entries
        print("Fetching assessment data with manual entries...")
        assessment_data = service.fetch_holistic_assessment_data(mock_request, test_assessment_config)
        
        if not assessment_data:
            print("❌ No assessment data returned")
            return False
        
        print(f"✅ Assessment data fetched successfully")
        print(f"   Objectives: {len(assessment_data[0].get('objectives', []))}")
        
        # Check if manual entries were applied
        manual_entries_applied = False
        for objective in assessment_data[0].get('objectives', []):
            for indicator in objective.get('indicators', []):
                indicator_id = str(indicator.get('id'))
                if indicator_id in test_assessment_config['manual_entries']:
                    expected_entries = test_assessment_config['manual_entries'][indicator_id]
                    
                    for period_code, expected_value in expected_entries.items():
                        actual_value = indicator.get('data_values', {}).get(period_code, {}).get('value')
                        manual_override = indicator.get('data_values', {}).get(period_code, {}).get('manual_override')
                        
                        print(f"   Indicator {indicator_id}, Period {period_code}:")
                        print(f"     Expected: {expected_value}")
                        print(f"     Actual: {actual_value}")
                        print(f"     Manual Override: {manual_override}")
                        
                        if actual_value == expected_value and manual_override == expected_value:
                            manual_entries_applied = True
                            print(f"     ✅ Manual entry correctly applied")
                        else:
                            print(f"     ❌ Manual entry not applied correctly")
        
        if manual_entries_applied:
            print("✅ Manual entries were properly applied to assessment data")
            
            # Test Excel export
            print("\nTesting Excel export...")
            try:
                file_path = service.generate_holistic_excel(assessment_data)
                print(f"✅ Excel file generated successfully: {file_path}")
                
                # Check if file exists and has content
                if os.path.exists(file_path):
                    file_size = os.path.getsize(file_path)
                    print(f"   File size: {file_size} bytes")
                    if file_size > 0:
                        print("✅ Excel file has content")
                        return True
                    else:
                        print("❌ Excel file is empty")
                        return False
                else:
                    print("❌ Excel file not found")
                    return False
                    
            except Exception as e:
                print(f"❌ Excel export failed: {e}")
                return False
        else:
            print("❌ Manual entries were not properly applied")
            return False
            
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("Testing manual entries export functionality...")
    success = test_manual_entries_export()
    
    if success:
        print("\n🎉 All tests passed! Manual entries are properly included in Excel export.")
    else:
        print("\n💥 Tests failed! Manual entries are not working correctly.")
        sys.exit(1)
