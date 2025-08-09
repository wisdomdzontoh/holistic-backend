#!/usr/bin/env python
"""
Test script for the save assessment endpoint
"""
import requests
import json

def test_save_assessment():
    """Test the save assessment endpoint"""
    url = "http://localhost:8000/api/assessments/holistic/save_assessment/"
    
    data = {
        "name": "Test Assessment",
        "org_unit_id": "test123",
        "org_unit_name": "Test Unit",
        "periods": ["2024"],
        "indicator_data": {
            "1": {
                "name": "Test Indicator",
                "dhis2_uid": "test_uid",
                "target_value": 100,
                "data_values": {"2024": {"value": 85}},
                "score": -1
            }
        },
        "calculated_scores": {
            "milestones": {
                "1": {
                    "name": "Test Milestone",
                    "score": -2
                }
            },
            "objectives": [
                {
                    "id": 1,
                    "name": "Test Objective",
                    "score": -1
                }
            ],
            "sector_score": -1.5
        },
        "user_notes": "Test assessment notes",
        "metadata": {
            "total_indicators": 1,
            "total_objectives": 1,
            "assessment_type": "holistic"
        }
    }
    
    headers = {
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.post(url, json=data, headers=headers)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.text}")
        
        if response.status_code == 200:
            print("✅ Save assessment endpoint is working!")
        else:
            print("❌ Save assessment endpoint failed!")
            
    except requests.exceptions.ConnectionError:
        print("❌ Could not connect to server. Make sure Django server is running on localhost:8000")
    except Exception as e:
        print(f"❌ Error: {str(e)}")

if __name__ == "__main__":
    test_save_assessment()
