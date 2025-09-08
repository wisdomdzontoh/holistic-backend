#!/usr/bin/env python3
"""
Test script to verify the scoring fix works correctly
"""
import os
import sys
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from indicators.models import TrackedIndicator
from assessments.services import HolisticScoringService

def test_scoring_fix():
    """Test the scoring fix for the problematic case"""
    
    print("=== Testing Scoring Fix ===")
    
    # Find Indicator 1.1
    indicator = TrackedIndicator.objects.filter(
        name__icontains="Average revenue per OPD patient"
    ).first()
    
    if not indicator:
        print("Indicator 1.1 not found")
        return
    
    print(f"Testing Indicator: {indicator.name}")
    print(f"Target Type: {indicator.target_type}")
    print(f"Target Operator: {indicator.target_operator}")
    print(f"Target Value: {indicator.target_value}")
    
    # Test the problematic case from the user's response
    current_value = 60.0
    previous_value = 10.0
    
    print(f"\nTest Case:")
    print(f"Current Value: {current_value}")
    print(f"Previous Value: {previous_value}")
    
    # Use the scoring service
    scoring_service = HolisticScoringService()
    result = scoring_service.calculate_indicator_score(
        indicator=indicator,
        current_value=current_value,
        previous_value=previous_value,
        data_provided=True
    )
    
    print(f"\nScoring Result:")
    print(f"Score: {result['score']}")
    print(f"Target Achieved: {result['target_achieved']}")
    print(f"Change Category: {result['change_category']}")
    print(f"Gap Category: {result['gap_category']}")
    print(f"Percent Change: {result['percent_change']}%")
    print(f"Target Gap: {result['target_gap']}%")
    
    # Verify the fix
    expected_score = -2  # Should be -2 for large decline
    if result['score'] == expected_score:
        print(f"\n✅ FIX VERIFIED: Score is {result['score']} (expected {expected_score})")
    else:
        print(f"\n❌ FIX FAILED: Score is {result['score']} (expected {expected_score})")

if __name__ == "__main__":
    test_scoring_fix()
