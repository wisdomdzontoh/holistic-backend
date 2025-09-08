#!/usr/bin/env python
"""
Test script to verify milestone score update functionality
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

def test_milestone_score_update():
    """Test the milestone score update functionality"""
    
    print("Testing Milestone Score Update Functionality")
    print("=" * 50)
    
    # Check if we have any milestones
    milestones = Milestone.objects.all()
    if not milestones.exists():
        print("No milestones found. Creating sample milestones...")
        from configurations.management.commands.create_sample_milestones import Command
        cmd = Command()
        cmd.handle()
        milestones = Milestone.objects.all()
    
    print(f"Found {milestones.count()} milestones")
    
    # Get the first milestone
    milestone = milestones.first()
    print(f"Testing with milestone: {milestone.name} (ID: {milestone.id})")
    print(f"Current score: {milestone.score}")
    
    # Test the API endpoint
    base_url = "http://localhost:8000"
    api_url = f"{base_url}/api/configurations/milestones/{milestone.id}/update_score/"
    
    # Test data
    new_score = 1  # Change from -2 to 1
    
    print(f"\nUpdating milestone score to {new_score}...")
    
    try:
        # First, we need to authenticate (this is a simplified test)
        # In a real scenario, you'd need to get a proper auth token
        response = requests.patch(
            api_url,
            json={"score": new_score},
            headers={"Content-Type": "application/json"}
        )
        
        print(f"Response status: {response.status_code}")
        print(f"Response body: {response.text}")
        
        if response.status_code == 200:
            print("✅ Milestone score update successful!")
            
            # Verify the change in the database
            milestone.refresh_from_db()
            print(f"Updated score in database: {milestone.score}")
            
            if milestone.score == new_score:
                print("✅ Database update verified!")
            else:
                print("❌ Database update failed!")
                
        else:
            print("❌ Milestone score update failed!")
            
    except requests.exceptions.ConnectionError:
        print("❌ Could not connect to the server. Make sure Django is running on localhost:8000")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    print("\n" + "=" * 50)
    print("Test completed!")

if __name__ == "__main__":
    test_milestone_score_update()
