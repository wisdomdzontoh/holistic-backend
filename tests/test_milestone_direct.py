#!/usr/bin/env python
"""
Simple test to verify milestone data directly from the database
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

from configurations.models import Milestone, Objective

def test_milestone_data():
    """Test milestone data directly from the database"""
    
    print("Testing Milestone Data Directly")
    print("=" * 50)
    
    # Check if we have any objectives with milestones
    objectives_with_milestones = Objective.objects.filter(milestone__isnull=False)
    if not objectives_with_milestones.exists():
        print("No objectives with milestones found. Creating sample data...")
        from configurations.management.commands.create_sample_milestones import Command
        cmd = Command()
        cmd.handle()
        objectives_with_milestones = Objective.objects.filter(milestone__isnull=False)
    
    print(f"Found {objectives_with_milestones.count()} objectives with milestones")
    
    # Get the first objective with a milestone
    objective = objectives_with_milestones.first()
    print(f"Testing with objective: {objective.name} (ID: {objective.id})")
    print(f"Milestone: {objective.milestone.name} (ID: {objective.milestone.id})")
    print(f"Milestone score: {objective.milestone.score}")
    
    # Test the data structure that would be sent to frontend
    objective_data = {
        'id': objective.id,
        'name': objective.name,
        'code': objective.code,
        'description': objective.description,
        'color': objective.color,
        'order': objective.order,
        'milestone': None
    }
    
    # Add milestone information if it exists
    if objective.milestone:
        objective_data['milestone'] = {
            'id': objective.milestone.id,
            'name': objective.milestone.name,
            'code': objective.milestone.code,
            'color': objective.milestone.color,
            'score': objective.milestone.score
        }
    
    print("\nObjective data structure:")
    print(json.dumps(objective_data, indent=2))
    
    # Check if milestone ID is properly set
    if objective_data['milestone'] and objective_data['milestone']['id'] is not None:
        print("✅ Milestone ID is properly set")
        print(f"   Milestone ID: {objective_data['milestone']['id']}")
        print(f"   Milestone Score: {objective_data['milestone']['score']}")
    else:
        print("❌ Milestone ID is not properly set")
    
    print("\n" + "=" * 50)
    print("Test completed!")

if __name__ == "__main__":
    test_milestone_data()
