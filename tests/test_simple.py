#!/usr/bin/env python
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from configurations.models import Objective
from indicators.models import TrackedIndicator

def test_simple():
    """Simple test to verify Django is working"""
    try:
        # Count objectives
        objective_count = Objective.objects.filter(is_active=True).count()
        print(f"✅ Active objectives: {objective_count}")
        
        # Count indicators
        indicator_count = TrackedIndicator.objects.count()
        print(f"✅ Total indicators: {indicator_count}")
        
        # Test the relationship
        first_objective = Objective.objects.filter(is_active=True).first()
        if first_objective:
            indicator_count_for_obj = TrackedIndicator.objects.filter(
                objective_weights__objective=first_objective
            ).count()
            print(f"✅ Indicators for first objective: {indicator_count_for_obj}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return False

if __name__ == "__main__":
    test_simple()

