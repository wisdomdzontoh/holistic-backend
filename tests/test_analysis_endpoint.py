#!/usr/bin/env python
"""
Test script to verify the analysis endpoint is working
"""

import os
import sys
import django

# Add the project directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from assessments.models import SavedAssessment
from dhis2_auth.models import DHIS2User

def test_analysis_endpoint():
    """Test the analysis endpoint data"""
    
    print("Testing analysis endpoint data")
    print("=" * 50)
    
    # Check if there are any saved assessments
    saved_assessments = SavedAssessment.objects.all()
    print(f"Total saved assessments: {saved_assessments.count()}")
    
    if saved_assessments.exists():
        for assessment in saved_assessments:
            print(f"\nAssessment: {assessment.name}")
            print(f"  - ID: {assessment.id}")
            print(f"  - Org Unit: {assessment.org_unit_name}")
            print(f"  - Created by: {assessment.created_by}")
            print(f"  - Created at: {assessment.created_at}")
            print(f"  - Total indicators: {assessment.total_indicators}")
            print(f"  - Total objectives: {assessment.total_objectives}")
            
            # Check calculated scores
            calculated_scores = assessment.calculated_scores or {}
            print(f"  - Has calculated scores: {bool(calculated_scores)}")
            
            if calculated_scores:
                objectives = calculated_scores.get('objectives', {})
                sector = calculated_scores.get('sector', {})
                print(f"  - Objectives with scores: {len(objectives)}")
                print(f"  - Sector score: {sector.get('overall_score', 'N/A')}")
                
                # Show some objective scores
                for obj_id, obj_data in list(objectives.items())[:3]:
                    if isinstance(obj_data, dict):
                        print(f"    - Objective {obj_id}: {obj_data.get('score', 'N/A')}")
    else:
        print("No saved assessments found!")
        print("You may need to create some assessments first.")
    
    # Check users
    users = DHIS2User.objects.all()
    print(f"\nTotal users: {users.count()}")
    if users.exists():
        for user in users[:3]:
            print(f"  - {user.dhis2_username} (ID: {user.id})")

if __name__ == '__main__':
    test_analysis_endpoint()
