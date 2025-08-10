#!/usr/bin/env python
"""
Test script to check milestone functionality in the backend
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
from assessments.views import AssessmentManagementViewSet
from django.test import RequestFactory
from django.contrib.auth.models import User
from rest_framework.test import force_authenticate
import json

def test_milestone_backend():
    """Test milestone functionality in the backend"""
    
    print("Testing Milestone Backend Functionality")
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
    
    # Create a test user
    user, created = User.objects.get_or_create(
        username='testuser',
        defaults={'email': 'test@example.com'}
    )
    if created:
        user.set_password('testpass123')
        user.save()
        print(f"Created test user: {user.username}")
    else:
        print(f"Using existing test user: {user.username}")
    
    # Create a test milestone score
    milestone_score, created = MilestoneScore.objects.get_or_create(
        milestone=objective.milestone,
        objective=objective,
        org_unit_id='test_org_unit',
        assessment_period=assessment_period,
        defaults={
            'score': 1,
            'score_color': '#28a745',
            'score_label': 'Highly Performing',
            'org_unit_name': 'Test Organization Unit'
        }
    )
    
    if created:
        print(f"Created milestone score: {milestone_score.score}")
    else:
        print(f"Using existing milestone score: {milestone_score.score}")
    
    # Test the view directly
    print("\nTesting the view directly...")
    
    # Create a request factory
    factory = RequestFactory()
    
    # Create a request to the holistic_assessment_data endpoint
    request = factory.get('/api/assessments/management/holistic-assessment-data/')
    
    # Authenticate the request
    force_authenticate(request, user=user)
    
    # Create the view instance
    view = AssessmentManagementViewSet()
    view.request = request
    
    # Call the holistic_assessment_data method
    try:
        response = view.holistic_assessment_data(request)
        print(f"Response status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.data
            print(f"Response data type: {type(data)}")
            
            if isinstance(data, list) and len(data) > 0:
                first_item = data[0]
                print(f"First item keys: {list(first_item.keys())}")
                
                if 'objectives' in first_item:
                    objectives = first_item['objectives']
                    print(f"Number of objectives: {len(objectives)}")
                    
                    # Check for milestones in objectives
                    objectives_with_milestones = 0
                    objectives_without_milestones = 0
                    
                    for i, obj in enumerate(objectives[:5]):  # Check first 5 objectives
                        print(f"\nObjective {i+1}: {obj.get('name', 'Unknown')}")
                        print(f"  Milestone: {obj.get('milestone', 'None')}")
                        
                        if obj.get('milestone'):
                            objectives_with_milestones += 1
                            milestone = obj['milestone']
                            print(f"    Milestone ID: {milestone.get('id')}")
                            print(f"    Milestone Name: {milestone.get('name')}")
                            print(f"    Milestone Score: {milestone.get('score')}")
                        else:
                            objectives_without_milestones += 1
                    
                    print(f"\nSummary:")
                    print(f"  Objectives with milestones: {objectives_with_milestones}")
                    print(f"  Objectives without milestones: {objectives_without_milestones}")
                else:
                    print("No 'objectives' key found in response")
            else:
                print("Response is not a list or is empty")
                print(f"Response content: {data}")
        else:
            print(f"Error response: {response.data}")
            
    except Exception as e:
        print(f"Error calling view: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_milestone_backend()
