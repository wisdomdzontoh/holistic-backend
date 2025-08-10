#!/usr/bin/env python
"""
Test script to check milestone logic directly
"""

import os
import sys
import django

# Add the project directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from configurations.models import Objective, Milestone
from assessments.models import MilestoneScore, AssessmentPeriod
import json

def test_milestone_logic():
    """Test milestone logic directly"""
    
    print("Testing Milestone Logic Directly")
    print("=" * 50)
    
    # Check if we have objectives with milestones
    objectives_with_milestones = Objective.objects.filter(milestone__isnull=False)
    print(f"Found {objectives_with_milestones.count()} objectives with milestones")
    
    if not objectives_with_milestones.exists():
        print("No objectives with milestones found!")
        return
    
    # Get the first objective with a milestone
    objective = objectives_with_milestones.first()
    print(f"Testing with objective: {objective.name} (ID: {objective.id})")
    print(f"Milestone: {objective.milestone.name} (ID: {objective.milestone.id})")
    
    # Check if we have any assessment periods
    assessment_periods = AssessmentPeriod.objects.all()
    if not assessment_periods.exists():
        print("No assessment periods found!")
        return
    
    assessment_period = assessment_periods.first()
    print(f"Using assessment period: {assessment_period.name} (ID: {assessment_period.id})")
    
    # Test the milestone logic that would be used in the view
    print("\nTesting milestone logic...")
    
    # Simulate the objective data structure that would be created in the view
    objective_data = {
        'id': objective.id,
        'name': objective.name,
        'code': objective.code,
        'description': objective.description,
        'color': objective.color,
        'order': objective.order,
        'indicators': [],
        'score': None,
        'milestone': None
    }
    
    # Add milestone information if it exists (this is the key logic from the view)
    if objective.milestone:
        # Get milestone score for this assessment
        milestone_score = MilestoneScore.objects.filter(
            milestone=objective.milestone,
            org_unit_id='test_org_unit',  # Use a test org unit
            assessment_period=assessment_period
        ).first()
        
        objective_data['milestone'] = {
            'id': objective.milestone.id,
            'name': objective.milestone.name,
            'code': objective.milestone.code,
            'color': objective.milestone.color,
            'score': milestone_score.score if milestone_score else -2,  # Default score
            'score_color': milestone_score.score_color if milestone_score else '#dc3545',
            'score_label': milestone_score.score_label if milestone_score else 'Severely Underperforming'
        }
        
        print(f"✓ Milestone data added to objective")
        print(f"  Milestone ID: {objective_data['milestone']['id']}")
        print(f"  Milestone Name: {objective_data['milestone']['name']}")
        print(f"  Milestone Score: {objective_data['milestone']['score']}")
        print(f"  Milestone Color: {objective_data['milestone']['score_color']}")
        print(f"  Milestone Label: {objective_data['milestone']['score_label']}")
    else:
        print("✗ No milestone found for this objective")
    
    # Test with all objectives
    print(f"\nTesting all objectives...")
    all_objectives = Objective.objects.filter(is_active=True).order_by('order')
    
    objectives_with_milestones_count = 0
    objectives_without_milestones_count = 0
    
    for obj in all_objectives[:10]:  # Test first 10 objectives
        if obj.milestone:
            objectives_with_milestones_count += 1
            print(f"  ✓ Objective '{obj.name}' has milestone: {obj.milestone.name}")
        else:
            objectives_without_milestones_count += 1
            print(f"  ✗ Objective '{obj.name}' has no milestone")
    
    print(f"\nSummary:")
    print(f"  Objectives with milestones: {objectives_with_milestones_count}")
    print(f"  Objectives without milestones: {objectives_without_milestones_count}")
    
    # Test the conditional logic that would be used in the frontend
    print(f"\nTesting frontend conditional logic...")
    
    # Simulate what the frontend would receive
    if objective_data['milestone']:
        print("✓ Frontend would render milestone dropdown")
        print(f"  Milestone ID available: {objective_data['milestone']['id']}")
        print(f"  Milestone score available: {objective_data['milestone']['score']}")
    else:
        print("✗ Frontend would render 'N/A' placeholder")
    
    # Test the specific case that was causing the error
    print(f"\nTesting the specific error case...")
    
    # Simulate an objective without a milestone
    objective_without_milestone = Objective.objects.filter(milestone__isnull=True).first()
    if objective_without_milestone:
        print(f"Testing objective without milestone: {objective_without_milestone.name}")
        
        objective_data_no_milestone = {
            'id': objective_without_milestone.id,
            'name': objective_without_milestone.name,
            'milestone': None  # This is the key - milestone is None
        }
        
        # Test the frontend conditional logic
        if objective_data_no_milestone['milestone']:
            print("✗ This should not happen - milestone is None but condition passed")
        else:
            print("✓ Frontend would correctly show 'N/A' for this objective")
    else:
        print("No objectives without milestones found to test")

if __name__ == "__main__":
    test_milestone_logic()
