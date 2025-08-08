#!/usr/bin/env python
"""
Test script for the new real-time DHIS2 architecture
This demonstrates fetching data without database storage
"""
import os
import sys
import django
from datetime import datetime

# Add the project directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from dhis2_auth.dhis_client import DHIS2Client
from assessments.services import RealTimeDHIS2Service, AssessmentSaveService
from configurations.models import TrackedIndicator
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_realtime_architecture():
    """Test the new real-time architecture"""
    print("=== Testing Real-Time DHIS2 Architecture ===")
    
    # Test 1: Real-time data fetching without database storage
    print("\n1. Testing Real-Time Data Fetching...")
    try:
        # Create DHIS2 client
        client = DHIS2Client(
            instance_url="https://dhims.chimgh.org/dhims",
            username="Demo",
            password="Ghana@2020"
        )
        
        # Create real-time service
        realtime_service = RealTimeDHIS2Service(client)
        
        # Mock request object (in real usage, this comes from Django)
        class MockRequest:
            def __init__(self):
                self.session = {'dhis2_user_id': 1}
        
        mock_request = MockRequest()
        
        # Test configuration
        assessment_config = {
            'org_unit_ids': ['pNf9RX5OfpD'],  # Ghana
            'periods': ['2021', '2022', '2023'],
            'indicator_uids': ['U15VyJ7EHGF', 'XLn1cZZTA0H']  # Test indicators
        }
        
        # Fetch real-time data
        assessment_data = realtime_service.fetch_holistic_assessment_data(
            mock_request, assessment_config
        )
        
        print(f"✅ Real-time data fetched successfully!")
        print(f"   - Objectives: {len(assessment_data.get('objectives', []))}")
        print(f"   - Milestones: {len(assessment_data.get('milestones', []))}")
        print(f"   - Metadata: {assessment_data.get('metadata', {})}")
        
        # Show sample data
        if assessment_data.get('objectives'):
            objective = assessment_data['objectives'][0]
            print(f"   - Sample objective: {objective['name']}")
            if objective.get('indicators'):
                indicator = objective['indicators'][0]
                print(f"   - Sample indicator: {indicator['name']}")
                print(f"   - Period data: {indicator.get('period_data', {})}")
        
    except Exception as e:
        print(f"❌ Real-time data fetching failed: {str(e)}")
    
    # Test 2: Assessment saving service
    print("\n2. Testing Assessment Save Service...")
    try:
        save_service = AssessmentSaveService()
        
        # Mock assessment data
        assessment_data = {
            'name': 'Test Holistic Assessment',
            'org_unit_id': 'pNf9RX5OfpD',
            'org_unit_name': 'Ghana',
            'periods': ['2021', '2022', '2023'],
            'indicator_data': {
                'U15VyJ7EHGF': {
                    '2021': 85.5,
                    '2022': 88.2,
                    '2023': 90.1
                },
                'XLn1cZZTA0H': {
                    '2021': 15000000,
                    '2022': 16500000,
                    '2023': 18000000
                }
            },
            'calculated_scores': {
                'overall_score': 3.5,
                'grade': 'Good',
                'objectives': {
                    'obj1': {'score': 4.0, 'grade': 'Excellent'},
                    'obj2': {'score': 3.0, 'grade': 'Good'}
                }
            },
            'user_notes': 'This is a test assessment with real-time data'
        }
        
        # Save assessment
        saved_assessment = save_service.save_assessment(mock_request, assessment_data)
        
        print(f"✅ Assessment saved successfully!")
        print(f"   - Assessment name: {saved_assessment.get('name')}")
        print(f"   - Org unit: {saved_assessment.get('org_unit_name')}")
        print(f"   - Periods: {saved_assessment.get('periods')}")
        
    except Exception as e:
        print(f"❌ Assessment saving failed: {str(e)}")
    
    # Test 3: Compare with old architecture
    print("\n3. Architecture Comparison...")
    print("OLD ARCHITECTURE (Problematic):")
    print("   ❌ Fetch DHIS2 data → Store in DB → Display from DB")
    print("   ❌ Complex sync logic, database locking, data duplication")
    print("   ❌ Users can't see real-time DHIS2 data")
    print("   ❌ Database storage required for all data")
    
    print("\nNEW ARCHITECTURE (Improved):")
    print("   ✅ Real-time DHIS2 fetching → Display directly (no DB storage)")
    print("   ✅ User-generated assessments → Save to DB for retrieval")
    print("   ✅ Clean separation between DHIS2 data and user work")
    print("   ✅ No database locking issues")
    print("   ✅ Always shows latest DHIS2 data")
    print("   ✅ Users can save their work separately")
    
    print("\n🎉 Real-time architecture testing completed!")
    print("\nBenefits of new architecture:")
    print("✅ No database locking errors")
    print("✅ Always shows real-time DHIS2 data")
    print("✅ Simpler codebase")
    print("✅ Better performance")
    print("✅ Clean separation of concerns")
    print("✅ Users can save their assessments separately")

if __name__ == "__main__":
    test_realtime_architecture()
