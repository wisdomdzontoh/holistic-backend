#!/usr/bin/env python
"""
Test script to verify milestone data is properly included in API response
"""

import os
import sys
import django
import requests
import json

# Add the project directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from configurations.models import Milestone, Objective
from django.contrib.auth.models import User

def test_milestone_api_response():
    """Test that milestone data is properly included in API response"""
    
    print("Testing Milestone API Response")
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
    
    # Test the API endpoint
    base_url = "http://localhost:8000"
    api_url = f"{base_url}/api/assessments/holistic-assessment-data/"
    
    print(f"\nTesting API endpoint: {api_url}")
    
    try:
        # This is a simplified test - in a real scenario you'd need proper authentication
        response = requests.get(api_url)
        
        print(f"Response status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print("✅ API response successful!")
            
            # Check if objectives are in the response
            if 'objectives' in data:
                objectives = data['objectives']
                print(f"Found {len(objectives)} objectives in response")
                
                # Look for our test objective
                test_objective = None
                for obj in objectives:
                    if obj['id'] == objective.id:
                        test_objective = obj
                        break
                
                if test_objective:
                    print("✅ Found our test objective in response")
                    
                    # Check if milestone data is included
                    if 'milestone' in test_objective:
                        milestone_data = test_objective['milestone']
                        print("✅ Milestone data is included in response")
                        print(f"   Milestone ID: {milestone_data.get('id')}")
                        print(f"   Milestone Name: {milestone_data.get('name')}")
                        print(f"   Milestone Score: {milestone_data.get('score')}")
                        
                        # Check if milestone ID is not undefined
                        if milestone_data.get('id') is not None:
                            print("✅ Milestone ID is properly set (not undefined)")
                        else:
                            print("❌ Milestone ID is undefined or null")
                    else:
                        print("❌ Milestone data is missing from objective")
                else:
                    print("❌ Test objective not found in response")
            else:
                print("❌ No objectives found in response")
                
        else:
            print(f"❌ API request failed with status {response.status_code}")
            print(f"Response body: {response.text}")
            
    except requests.exceptions.ConnectionError:
        print("❌ Could not connect to the server. Make sure Django is running on localhost:8000")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    print("\n" + "=" * 50)
    print("Test completed!")

if __name__ == "__main__":
    test_milestone_api_response()
