#!/usr/bin/env python
"""
Simple test script to verify that decrease indicators with current value = 0 
automatically score 2
"""

import os
import sys
import django

# Add the project directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from assessments.services import HolisticScoringService

def test_decrease_indicator_zero_case():
    """Test that decrease indicators with current value = 0 automatically score 2"""
    
    # Create a mock decrease indicator
    class MockIndicator:
        def __init__(self):
            self.id = 999
            self.name = "Test Decrease Indicator"
            self.target_type = 'decrease'
            self.target_operator = '<='
            self.target_value = 2.0
            self.target_format = 'SINGLE'
    
    indicator = MockIndicator()
    
    current_value = 0.0
    previous_value = 1.45
    
    print("=== Testing Decrease Indicator with Current Value = 0 ===")
    print(f"Indicator: {indicator.name}")
    print(f"Target Type: {indicator.target_type}")
    print(f"Target Value: {indicator.target_value}")
    print(f"Current Value: {current_value}")
    print(f"Previous Value: {previous_value}")
    print()
    
    # Calculate score
    scoring_service = HolisticScoringService()
    result = scoring_service.calculate_indicator_score(
        indicator=indicator,
        current_value=current_value,
        previous_value=previous_value,
        data_provided=True
    )
    
    print("=== Results ===")
    print(f"Data Provided: {result['data_provided']}")
    print(f"Is First Year: {result['is_first_year']}")
    print(f"Target Achieved: {result['target_achieved']}")
    print(f"Percent Change: {result['percent_change']}")
    print(f"Change Category: {result['change_category']}")
    print(f"Target Gap: {result['target_gap']}")
    print(f"Gap Category: {result['gap_category']}")
    print(f"Final Score: {result['score']}")
    print()
    
    # Verify the result
    expected_score = 2
    actual_score = result['score']
    
    print("=== Verification ===")
    print(f"Expected Score: {expected_score}")
    print(f"Actual Score: {actual_score}")
    print(f"Test Passed: {actual_score == expected_score}")
    
    if actual_score == expected_score:
        print("✅ SUCCESS: Decrease indicator with current value = 0 correctly scores 2!")
    else:
        print("❌ FAILURE: Score is incorrect!")
        print(f"   Expected: {expected_score}, Got: {actual_score}")
    
    return actual_score == expected_score

if __name__ == "__main__":
    success = test_decrease_indicator_zero_case()
    sys.exit(0 if success else 1)
