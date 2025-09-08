#!/usr/bin/env python3
"""
Test script to verify that the API endpoint returns scores correctly.
"""

import os
import sys
import django
import requests
import json

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

def test_api_scores():
    """Test the API endpoint to verify scores are being returned"""
    print("\n" + "="*60)
    print("TESTING API SCORE CALCULATION")
    print("="*60)
    
    # Test data for the API request
    test_request_data = {
        "org_unit_ids": ["test_org_unit"],
        "periods": ["2022", "2023", "2024"],
        "indicator_uids": []  # Empty to use all active indicators
    }
    
    print(f"Test request data: {json.dumps(test_request_data, indent=2)}")
    
    # Test the API endpoint
    try:
        # Note: This would require authentication in a real scenario
        # For testing, we'll use the service directly
        from assessments.services import RealTimeDHIS2Service
        from django.test import RequestFactory
        from django.contrib.auth.models import User
        
        # Create a mock request
        factory = RequestFactory()
        request = factory.post('/api/assessments/holistic/fetch_data/', 
                              data=json.dumps(test_request_data),
                              content_type='application/json')
        
        # Mock authentication (in real scenario, this would be handled by middleware)
        request.user = User.objects.first() or User.objects.create_user('testuser', 'test@example.com', 'password')
        
        # Mock session
        request.session = {}
        
        # Initialize service
        service = RealTimeDHIS2Service()
        
        print("\nCalling fetch_holistic_assessment_data...")
        
        # This will fail without proper DHIS2 setup, but we can see the structure
        try:
            assessment_data = service.fetch_holistic_assessment_data(request, test_request_data)
            
            print("\n✓ API call successful!")
            print(f"Response structure: {type(assessment_data)}")
            
            # Check if objectives are present
            if 'objectives' in assessment_data:
                print(f"✓ Found {len(assessment_data['objectives'])} objectives")
                
                for i, objective in enumerate(assessment_data['objectives']):
                    print(f"\nObjective {i+1}: {objective.get('name', 'Unknown')}")
                    
                    if 'indicators' in objective:
                        print(f"  - {len(objective['indicators'])} indicators")
                        
                        for j, indicator in enumerate(objective['indicators']):
                            score_data = indicator.get('score', {})
                            score_value = score_data.get('score')
                            score_label = score_data.get('score_label')
                            
                            print(f"    Indicator {j+1}: {indicator.get('name', 'Unknown')}")
                            print(f"      - Score: {score_value}")
                            print(f"      - Label: {score_label}")
                            print(f"      - Percent Change: {score_data.get('percent_change')}")
                            print(f"      - Target Gap: {score_data.get('target_gap')}")
                            
                            # Verify score is not None
                            if score_value is not None:
                                print(f"      ✓ Score is calculated: {score_value}")
                            else:
                                print(f"      ✗ Score is None - this is the issue!")
                    else:
                        print("  - No indicators found")
            else:
                print("✗ No objectives found in response")
                
        except Exception as e:
            print(f"✗ API call failed: {str(e)}")
            print("This is expected without proper DHIS2 setup")
            
            # Let's check if we can at least verify the scoring logic works
            print("\nTesting scoring logic directly...")
            test_scoring_logic()
            
    except Exception as e:
        print(f"✗ Test setup failed: {str(e)}")

def test_scoring_logic():
    """Test the scoring logic directly"""
    from assessments.services import RealTimeDHIS2Service
    
    service = RealTimeDHIS2Service()
    
    # Test cases
    test_cases = [
        {
            'name': 'Positive change > 5%',
            'percent_change': 10.0,
            'target_gap': 20.0,
            'current_value': 80.0,
            'target_value': 60.0,
            'target_type': 'increase'
        },
        {
            'name': 'Negative change < -5%',
            'percent_change': -8.0,
            'target_gap': 15.0,
            'current_value': 45.0,
            'target_value': 60.0,
            'target_type': 'increase'
        },
        {
            'name': 'Small positive change',
            'percent_change': 2.0,
            'target_gap': 5.0,
            'current_value': 65.0,
            'target_value': 60.0,
            'target_type': 'increase'
        }
    ]
    
    print("\nTesting scoring logic with sample data:")
    
    for test_case in test_cases:
        print(f"\n{test_case['name']}:")
        
        # Test the scoring methods
        change_cat = service._classify_change_category(test_case['percent_change'])
        gap_cat = service._classify_gap_category(test_case['target_gap'])
        
        # Determine if current and previous meet targets
        current_meets = False
        previous_meets = False
        
        if test_case['current_value'] is not None and test_case['target_value'] is not None:
            if test_case['target_type'] == 'increase':
                current_meets = float(test_case['current_value']) >= float(test_case['target_value'])
                # Assume previous was slightly lower
                previous_meets = float(test_case['current_value']) * 0.95 >= float(test_case['target_value'])
            else:
                current_meets = float(test_case['current_value']) <= float(test_case['target_value'])
                previous_meets = float(test_case['current_value']) * 1.05 <= float(test_case['target_value'])
        
        # Calculate score
        has_data = test_case['percent_change'] is not None or test_case['target_gap'] is not None
        score = service._compute_trend_score(has_data, current_meets, previous_meets, change_cat, gap_cat)
        color, label = service._score_color_label(score)
        
        print(f"  - Percent Change: {test_case['percent_change']}% -> Category: {change_cat}")
        print(f"  - Target Gap: {test_case['target_gap']}% -> Category: {gap_cat}")
        print(f"  - Current Meets Target: {current_meets}")
        print(f"  - Previous Meets Target: {previous_meets}")
        print(f"  - Calculated Score: {score}")
        print(f"  - Score Color: {color}")
        print(f"  - Score Label: {label}")
        
        if score is not None:
            print(f"  ✓ Score calculation working!")
        else:
            print(f"  ✗ Score calculation failed!")

if __name__ == '__main__':
    test_api_scores()
