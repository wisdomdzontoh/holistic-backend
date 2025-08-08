#!/usr/bin/env python
"""
Demo of Real-Time DHIS2 Architecture
This shows how to fetch data without storing in database
"""
import os
import sys
import django

# Add the project directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from dhis2_auth.dhis_client import DHIS2Client
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def demo_realtime_architecture():
    """Demo the real-time architecture concept"""
    print("=== Real-Time DHIS2 Architecture Demo ===")
    
    try:
        # Create DHIS2 client
        client = DHIS2Client(
            instance_url="https://dhims.chimgh.org/dhims",
            username="Demo",
            password="Ghana@2020"
        )
        
        # Test configuration
        org_unit_id = "pNf9RX5OfpD"  # Ghana
        periods = ["2021", "2022", "2023"]
        test_indicators = ["U15VyJ7EHGF", "XLn1cZZTA0H"]
        
        print(f"\n1. Real-Time Data Fetching (No Database Storage)")
        print(f"   - Org Unit: {org_unit_id}")
        print(f"   - Periods: {periods}")
        print(f"   - Indicators: {test_indicators}")
        
        # Simulate holistic assessment data structure
        assessment_data = {
            'objectives': [
                {
                    'id': 1,
                    'name': 'Maternal Health',
                    'code': 'OBJ1',
                    'indicators': []
                },
                {
                    'id': 2,
                    'name': 'Child Health',
                    'code': 'OBJ2',
                    'indicators': []
                }
            ],
            'metadata': {
                'org_unit': org_unit_id,
                'periods': periods,
                'fetched_at': '2024-01-01T12:00:00Z'
            }
        }
        
        # Fetch real-time data for each indicator
        for indicator_uid in test_indicators:
            print(f"\n   Fetching indicator: {indicator_uid}")
            
            indicator_data = {
                'dhis2_uid': indicator_uid,
                'name': f'Indicator {indicator_uid}',
                'period_data': {}
            }
            
            # Fetch data for each period
            for period in periods:
                try:
                    print(f"     Fetching period {period}...")
                    
                    response = client.get_analytics_data(
                        indicators=[indicator_uid],
                        periods=[period],
                        org_units=[org_unit_id]
                    )
                    
                    if response and 'rows' in response and response['rows']:
                        row = response['rows'][0]
                        if len(row) >= 4:
                            value = row[3]
                            try:
                                indicator_data['period_data'][period] = float(value) if value is not None else None
                                print(f"       ✅ {period}: {value}")
                            except (ValueError, TypeError):
                                indicator_data['period_data'][period] = None
                                print(f"       ❌ {period}: Invalid value")
                        else:
                            indicator_data['period_data'][period] = None
                            print(f"       ❌ {period}: No data")
                    else:
                        indicator_data['period_data'][period] = None
                        print(f"       ❌ {period}: No response")
                        
                except Exception as e:
                    indicator_data['period_data'][period] = None
                    print(f"       ❌ {period}: Error - {str(e)}")
            
            # Add to first objective
            assessment_data['objectives'][0]['indicators'].append(indicator_data)
        
        print(f"\n✅ Real-time data fetching completed!")
        print(f"   - Objectives: {len(assessment_data['objectives'])}")
        print(f"   - Indicators fetched: {len(assessment_data['objectives'][0]['indicators'])}")
        
        # Show results
        print(f"\n📊 Assessment Data (Real-Time from DHIS2):")
        for objective in assessment_data['objectives']:
            print(f"\n   Objective: {objective['name']}")
            for indicator in objective['indicators']:
                print(f"     Indicator: {indicator['name']}")
                for period, value in indicator['period_data'].items():
                    print(f"       {period}: {value}")
        
        return assessment_data
        
    except Exception as e:
        print(f"❌ Demo failed: {str(e)}")
        return None

def compare_architectures():
    """Compare old vs new architecture"""
    print("\n=== Architecture Comparison ===")
    
    print("\nOLD ARCHITECTURE (Problematic):")
    print("   ❌ Fetch DHIS2 data → Store in DB → Display from DB")
    print("   ❌ Complex sync logic, database locking, data duplication")
    print("   ❌ Users can't see real-time DHIS2 data")
    print("   ❌ Database storage required for all data")
    print("   ❌ Database locked errors")
    print("   ❌ Complex retry logic needed")
    print("   ❌ Data can become stale")
    
    print("\nNEW ARCHITECTURE (Improved):")
    print("   ✅ Real-time DHIS2 fetching → Display directly (no DB storage)")
    print("   ✅ User-generated assessments → Save to DB for retrieval")
    print("   ✅ Clean separation between DHIS2 data and user work")
    print("   ✅ No database locking issues")
    print("   ✅ Always shows latest DHIS2 data")
    print("   ✅ Users can save their work separately")
    print("   ✅ Simpler codebase")
    print("   ✅ Better performance")
    print("   ✅ Real-time data always fresh")

def show_workflow():
    """Show the new workflow"""
    print("\n=== New Workflow ===")
    print("\n1. User opens Holistic Assessment page")
    print("2. User selects org unit and periods")
    print("3. System fetches real-time data from DHIS2 (no DB storage)")
    print("4. System displays data immediately")
    print("5. User can edit/add manual data")
    print("6. User saves assessment → stored in local DB")
    print("7. User can retrieve saved assessments from local DB")
    print("8. Real-time DHIS2 data always fresh")

def main():
    """Main demo function"""
    print("=== Real-Time DHIS2 Architecture Demo ===")
    
    # Demo real-time fetching
    assessment_data = demo_realtime_architecture()
    
    # Compare architectures
    compare_architectures()
    
    # Show workflow
    show_workflow()
    
    print("\n🎉 Demo completed!")
    print("\nKey Benefits:")
    print("✅ No database locking errors")
    print("✅ Always shows real-time DHIS2 data")
    print("✅ Simpler codebase")
    print("✅ Better performance")
    print("✅ Clean separation of concerns")
    print("✅ Users can save their assessments separately")
    print("✅ Real-time data always fresh")

if __name__ == "__main__":
    main()
