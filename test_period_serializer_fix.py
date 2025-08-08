#!/usr/bin/env python
"""
Test script to verify the period serializer fix
"""
import os
import sys
import django
import logging

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from assessments.serializers import HolisticAssessmentRequestSerializer

def test_period_serializer():
    """Test the period serializer with different formats"""
    print("Testing Period Serializer Fix")
    print("=" * 50)
    
    # Test 1: String periods (original format)
    print("\nTest 1: String periods")
    data1 = {
        'org_unit_ids': ['Pug4R4IHDtN'],
        'periods': ['2023', '2022', '2021'],
        'indicator_uids': ['XLn1cZZTA0H']
    }
    
    try:
        serializer1 = HolisticAssessmentRequestSerializer(data=data1)
        if serializer1.is_valid():
            print("✓ String periods validation passed")
            print(f"  Normalized periods: {serializer1.validated_data['periods']}")
        else:
            print("✗ String periods validation failed")
            print(f"  Errors: {serializer1.errors}")
    except Exception as e:
        print(f"✗ String periods test error: {str(e)}")
    
    # Test 2: Object periods (frontend format)
    print("\nTest 2: Object periods")
    data2 = {
        'org_unit_ids': ['Pug4R4IHDtN'],
        'periods': [
            {
                'name': '2023',
                'period_type': 'custom',
                'start_date': '2023-01-01',
                'end_date': '2023-12-31',
                'code': '2023'
            },
            {
                'name': '2022',
                'period_type': 'custom',
                'start_date': '2022-01-01',
                'end_date': '2022-12-31',
                'code': '2022'
            }
        ],
        'indicator_uids': ['XLn1cZZTA0H']
    }
    
    try:
        serializer2 = HolisticAssessmentRequestSerializer(data=data2)
        if serializer2.is_valid():
            print("✓ Object periods validation passed")
            print(f"  Normalized periods: {serializer2.validated_data['periods']}")
        else:
            print("✗ Object periods validation failed")
            print(f"  Errors: {serializer2.errors}")
    except Exception as e:
        print(f"✗ Object periods test error: {str(e)}")
    
    # Test 3: Mixed format periods
    print("\nTest 3: Mixed format periods")
    data3 = {
        'org_unit_ids': ['Pug4R4IHDtN'],
        'periods': [
            '2023',  # String
            {
                'name': '2022',
                'code': '2022'
            },  # Object
            '2021'   # String
        ],
        'indicator_uids': ['XLn1cZZTA0H']
    }
    
    try:
        serializer3 = HolisticAssessmentRequestSerializer(data=data3)
        if serializer3.is_valid():
            print("✓ Mixed format periods validation passed")
            print(f"  Normalized periods: {serializer3.validated_data['periods']}")
        else:
            print("✗ Mixed format periods validation failed")
            print(f"  Errors: {serializer3.errors}")
    except Exception as e:
        print(f"✗ Mixed format periods test error: {str(e)}")
    
    # Test 4: Invalid period object (missing code/name)
    print("\nTest 4: Invalid period object")
    data4 = {
        'org_unit_ids': ['Pug4R4IHDtN'],
        'periods': [
            {
                'period_type': 'custom',
                'start_date': '2023-01-01',
                'end_date': '2023-12-31'
                # Missing 'code' and 'name'
            }
        ],
        'indicator_uids': ['XLn1cZZTA0H']
    }
    
    try:
        serializer4 = HolisticAssessmentRequestSerializer(data=data4)
        if serializer4.is_valid():
            print("✗ Invalid period object validation should have failed")
        else:
            print("✓ Invalid period object correctly rejected")
            print(f"  Expected error: {serializer4.errors}")
    except Exception as e:
        print(f"✗ Invalid period object test error: {str(e)}")

if __name__ == "__main__":
    test_period_serializer()
    print("\n" + "=" * 50)
    print("Period Serializer Fix Test Complete")
    print("=" * 50)
