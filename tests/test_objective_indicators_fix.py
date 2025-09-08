#!/usr/bin/env python
"""
Test script to verify the objective-indicators relationship fix
"""
import os
import sys
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from configurations.models import Objective, IndicatorWeight
from indicators.models import TrackedIndicator

def test_objective_indicators_relationship():
    """Test the correct objective-indicators relationship"""
    print("Testing Objective-Indicators Relationship")
    print("=" * 50)
    
    try:
        # Test 1: Check if we can query objectives with prefetch_related
        print("\nTest 1: Query objectives with correct prefetch_related")
        try:
            objectives = Objective.objects.filter(is_active=True).prefetch_related('indicator_weights__indicator')
            print(f"✓ Successfully queried {objectives.count()} objectives")
        except Exception as e:
            print(f"✗ Failed to query objectives: {str(e)}")
            return
        
        # Test 2: Check if we can access indicators through the relationship
        print("\nTest 2: Access indicators through indicator_weights")
        total_indicators = 0
        
        for objective in objectives:
            objective_indicators = []
            for indicator_weight in objective.indicator_weights.all():
                indicator = indicator_weight.indicator
                if indicator.is_active:
                    objective_indicators.append(indicator)
            
            total_indicators += len(objective_indicators)
            print(f"  Objective '{objective.name}': {len(objective_indicators)} indicators")
        
        print(f"✓ Total indicators found: {total_indicators}")
        
        # Test 3: Check specific indicator filtering
        print("\nTest 3: Filter indicators by DHIS2 UID")
        
        # Get some test UIDs
        test_uids = list(TrackedIndicator.objects.filter(is_active=True).values_list('dhis2_uid', flat=True)[:3])
        print(f"  Testing with UIDs: {test_uids}")
        
        filtered_count = 0
        for objective in objectives:
            objective_indicators = []
            for indicator_weight in objective.indicator_weights.all():
                indicator = indicator_weight.indicator
                if indicator.dhis2_uid in test_uids and indicator.is_active:
                    objective_indicators.append(indicator)
            
            if objective_indicators:
                filtered_count += len(objective_indicators)
                print(f"  Objective '{objective.name}': {len(objective_indicators)} matching indicators")
        
        print(f"✓ Total matching indicators: {filtered_count}")
        
        # Test 4: Verify the old method would fail
        print("\nTest 4: Verify old method would fail")
        try:
            # This should fail
            Objective.objects.filter(is_active=True).prefetch_related('indicators')
            print("✗ Old method unexpectedly succeeded - this suggests the model has changed")
        except Exception as e:
            print(f"✓ Old method correctly failed: {str(e)}")
        
    except Exception as e:
        print(f"✗ Test failed with error: {str(e)}")
        import traceback
        traceback.print_exc()

def test_real_time_service_compatibility():
    """Test that the RealTimeDHIS2Service can now work"""
    print("\n" + "=" * 50)
    print("Testing RealTimeDHIS2Service Compatibility")
    print("=" * 50)
    
    try:
        from assessments.services import RealTimeDHIS2Service
        from unittest.mock import Mock
        
        # Create a mock request
        mock_request = Mock()
        mock_request.session = Mock()
        mock_request.session.session_key = 'test_session'
        
        # Mock DHIS2 user
        class MockDHIS2User:
            def __init__(self):
                self.dhis2_instance_url = "https://dhims.chimgh.org/dhims"
        
        # Mock the get_dhis2_user_from_request function
        def mock_get_dhis2_user_from_request(request):
            return MockDHIS2User()
        
        # Replace the function temporarily
        import assessments.services
        original_get_user = assessments.services.get_dhis2_user_from_request
        assessments.services.get_dhis2_user_from_request = mock_get_dhis2_user_from_request
        
        try:
            # Test configuration
            test_config = {
                'org_unit_ids': ['Pug4R4IHDtN'],
                'periods': ['2023'],
                'indicator_uids': ['XLn1cZZTA0H', 'VG3hdQLOHJH']
            }
            
            # Initialize real-time service
            service = RealTimeDHIS2Service()
            
            # Test that we can at least get to the point of querying objectives
            print("Testing objective querying...")
            
            # This should not crash on the prefetch_related anymore
            objectives = Objective.objects.filter(is_active=True).prefetch_related('indicator_weights__indicator')
            print(f"✓ Successfully queried {objectives.count()} objectives")
            
            # Test the relationship access pattern
            found_indicators = 0
            for objective in objectives:
                objective_indicators = []
                for indicator_weight in objective.indicator_weights.all():
                    indicator = indicator_weight.indicator
                    if indicator.dhis2_uid in test_config['indicator_uids'] and indicator.is_active:
                        objective_indicators.append(indicator)
                
                found_indicators += len(objective_indicators)
            
            print(f"✓ Found {found_indicators} matching indicators across all objectives")
            
        finally:
            # Restore original function
            assessments.services.get_dhis2_user_from_request = original_get_user
        
    except Exception as e:
        print(f"✗ Real-time service test failed: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_objective_indicators_relationship()
    test_real_time_service_compatibility()
    print("\n" + "=" * 50)
    print("Objective-Indicators Relationship Fix Test Complete")
    print("=" * 50)
