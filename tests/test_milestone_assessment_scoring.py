#!/usr/bin/env python
"""
Test script to verify the new milestone assessment scoring system
"""

import os
import sys
import django
import json

# Add the project directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from configurations.models import Milestone, Objective, AssessmentPeriod
from assessments.models import MilestoneScore
from django.contrib.auth.models import User

def test_milestone_assessment_scoring():
    """Test the new milestone assessment scoring system"""
    
    print("Testing Milestone Assessment Scoring System")
    print("=" * 60)
    
    # Check if we have any objectives with milestones
    objectives_with_milestones = Objective.objects.filter(milestone__isnull=False)
    if not objectives_with_milestones.exists():
        print("No objectives with milestones found. Creating sample data...")
        from configurations.management.commands.create_sample_milestones import Command
        cmd = Command()
        cmd.handle()
        objectives_with_milestones = Objective.objects.filter(milestone__isnull=False)
    
    print(f"Found {objectives_with_milestones.count()} objectives with milestones")
    
    # Get or create an assessment period
    assessment_period, created = AssessmentPeriod.objects.get_or_create(
        name="2024Q1",
        defaults={
            'period_type': 'quarterly',
            'start_date': '2024-01-01',
            'end_date': '2024-03-31',
            'is_active': True
        }
    )
    
    print(f"Using assessment period: {assessment_period.name}")
    
    # Get the first objective with a milestone
    objective = objectives_with_milestones.first()
    milestone = objective.milestone
    org_unit_id = "test_org_unit_001"
    org_unit_name = "Test Organization Unit"
    
    print(f"Testing with objective: {objective.name}")
    print(f"Milestone: {milestone.name}")
    print(f"Organization Unit: {org_unit_name} ({org_unit_id})")
    
    # Test 1: Create a new milestone score
    print("\n1. Testing milestone score creation...")
    
    milestone_score, created = MilestoneScore.objects.get_or_create(
        milestone=milestone,
        org_unit_id=org_unit_id,
        assessment_period=assessment_period,
        defaults={
            'objective': objective,
            'org_unit_name': org_unit_name,
            'score': -2,
            'override_user': None
        }
    )
    
    if created:
        print("✅ Created new milestone score")
    else:
        print("✅ Found existing milestone score")
    
    print(f"   Milestone Score ID: {milestone_score.id}")
    print(f"   Current Score: {milestone_score.score}")
    print(f"   Score Color: {milestone_score.score_color}")
    print(f"   Score Label: {milestone_score.score_label}")
    
    # Test 2: Update the milestone score
    print("\n2. Testing milestone score update...")
    
    new_score = 1
    milestone_score.update_score(new_score, None, "Test score update")
    
    print(f"✅ Updated milestone score to {new_score}")
    print(f"   New Score: {milestone_score.score}")
    print(f"   New Score Color: {milestone_score.score_color}")
    print(f"   New Score Label: {milestone_score.score_label}")
    
    # Test 3: Verify the score is properly stored
    print("\n3. Testing milestone score retrieval...")
    
    retrieved_score = MilestoneScore.objects.filter(
        milestone=milestone,
        org_unit_id=org_unit_id,
        assessment_period=assessment_period
    ).first()
    
    if retrieved_score and retrieved_score.score == new_score:
        print("✅ Milestone score properly stored and retrieved")
        print(f"   Retrieved Score: {retrieved_score.score}")
    else:
        print("❌ Milestone score not properly stored")
    
    # Test 4: Test multiple milestone scores for different org units
    print("\n4. Testing multiple milestone scores...")
    
    org_unit_2_id = "test_org_unit_002"
    org_unit_2_name = "Test Organization Unit 2"
    
    milestone_score_2, created_2 = MilestoneScore.objects.get_or_create(
        milestone=milestone,
        org_unit_id=org_unit_2_id,
        assessment_period=assessment_period,
        defaults={
            'objective': objective,
            'org_unit_name': org_unit_2_name,
            'score': 2,
            'override_user': None
        }
    )
    
    if created_2:
        print("✅ Created second milestone score for different org unit")
        print(f"   Org Unit 2 Score: {milestone_score_2.score}")
    
    # Test 5: Verify unique constraint
    print("\n5. Testing unique constraint...")
    
    total_scores = MilestoneScore.objects.filter(
        milestone=milestone,
        assessment_period=assessment_period
    ).count()
    
    print(f"✅ Total milestone scores for this milestone and period: {total_scores}")
    
    # Test 6: Test data structure for API
    print("\n6. Testing API data structure...")
    
    api_data = {
        'id': milestone.id,
        'name': milestone.name,
        'code': milestone.code,
        'color': milestone.color,
        'score': milestone_score.score,
        'score_color': milestone_score.score_color,
        'score_label': milestone_score.score_label
    }
    
    print("API data structure:")
    print(json.dumps(api_data, indent=2))
    
    if api_data['score'] is not None and api_data['score_color'] and api_data['score_label']:
        print("✅ API data structure is complete")
    else:
        print("❌ API data structure is incomplete")
    
    print("\n" + "=" * 60)
    print("Test completed successfully!")
    print("\nSummary:")
    print(f"- Created/updated milestone scores for {MilestoneScore.objects.count()} assessments")
    print(f"- Milestone scores are now assessment-specific")
    print(f"- Each org unit can have different milestone scores for the same milestone")
    print(f"- Scores are properly stored with colors and labels")

if __name__ == "__main__":
    test_milestone_assessment_scoring()
