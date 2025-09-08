#!/usr/bin/env python
"""
Test script to check API response for milestones
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

def test_api_response():
    """Test the API response to see if milestones are included"""
    
    print("Testing API Response for Milestones")
    print("=" * 50)
    
    # Test the API endpoint
    base_url = "http://localhost:8000"
    api_url = f"{base_url}/api/assessments/management/holistic-assessment-data/"
    
    print(f"Testing API endpoint: {api_url}")
    
    try:
        response = requests.get(api_url, timeout=10)
        print(f"Response status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
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
                    
                    for i, objective in enumerate(objectives[:5]):  # Check first 5 objectives
                        print(f"\nObjective {i+1}: {objective.get('name', 'Unknown')}")
                        print(f"  Milestone: {objective.get('milestone', 'None')}")
                        
                        if objective.get('milestone'):
                            objectives_with_milestones += 1
                            milestone = objective['milestone']
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
            print(f"Error response: {response.text}")
            
    except requests.exceptions.ConnectionError:
        print("Connection error - make sure Django server is running")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_api_response()
