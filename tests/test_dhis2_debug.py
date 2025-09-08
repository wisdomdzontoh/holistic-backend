#!/usr/bin/env python
"""
Comprehensive DHIS2 debugging script to identify data fetching issues
"""
import os
import sys
import django
import logging
from datetime import datetime

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from django.contrib.sessions.models import Session
from dhis2_auth.dhis_client import DHIS2Client, DHIS2ClientFactory
from dhis2_auth.session import get_dhis2_session_data
from indicators.models import TrackedIndicator
from configurations.models import Objective, AssessmentPeriod
from assessments.models import DataSyncLog, IndicatorData

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_dhis2_connection():
    """Test basic DHIS2 connection"""
    print("=== Testing DHIS2 Connection ===")
    
    # Get the most recent session
    recent_session = Session.objects.filter(expire_date__gt=datetime.now()).order_by('-expire_date').first()
    if not recent_session:
        print("❌ No active sessions found")
        return False
    
    session_data = get_dhis2_session_data(recent_session.session_key)
    if not session_data:
        print("❌ No DHIS2 session data found")
        return False
    
    print(f"✅ Found DHIS2 session for instance: {session_data['instance_url']}")
    
    # Create client
    client = DHIS2ClientFactory.create_client_from_session(
        session_data['instance_url'],
        recent_session.session_key
    )
    
    # Test connection
    if client.test_connection():
        print("✅ DHIS2 connection successful")
        return client
    else:
        print("❌ DHIS2 connection failed")
        return False

def test_user_authentication(client):
    """Test user authentication"""
    print("\n=== Testing User Authentication ===")
    
    try:
        user_info = client.authenticate_user()
        print(f"✅ Authentication successful for user: {user_info.get('name', 'Unknown')}")
        print(f"   User ID: {user_info.get('id', 'Unknown')}")
        print(f"   Username: {user_info.get('username', 'Unknown')}")
        return user_info
    except Exception as e:
        print(f"❌ Authentication failed: {str(e)}")
        return None

def test_org_units(client):
    """Test org unit fetching"""
    print("\n=== Testing Org Units ===")
    
    try:
        org_units = client.get_user_accessible_org_units()
        print(f"✅ Found {len(org_units)} accessible org units")
        
        # Show first few org units
        for i, org_unit in enumerate(org_units[:5]):
            print(f"   {i+1}. {org_unit.get('name', 'Unknown')} (ID: {org_unit.get('id', 'Unknown')})")
        
        if len(org_units) > 5:
            print(f"   ... and {len(org_units) - 5} more")
        
        return org_units
    except Exception as e:
        print(f"❌ Failed to fetch org units: {str(e)}")
        return []

def test_periods(client):
    """Test period fetching"""
    print("\n=== Testing Periods ===")
    
    try:
        periods = client.get_periods()
        print(f"✅ Found {len(periods)} periods")
        
        # Show first few periods
        for i, period in enumerate(periods[:5]):
            print(f"   {i+1}. {period.get('name', 'Unknown')} (ID: {period.get('id', 'Unknown')})")
        
        if len(periods) > 5:
            print(f"   ... and {len(periods) - 5} more")
        
        return periods
    except Exception as e:
        print(f"❌ Failed to fetch periods: {str(e)}")
        return []

def test_tracked_indicators():
    """Test tracked indicators from database"""
    print("\n=== Testing Tracked Indicators ===")
    
    indicators = TrackedIndicator.objects.filter(is_active=True)
    print(f"✅ Found {indicators.count()} active tracked indicators")
    
    # Show first few indicators
    for i, indicator in enumerate(indicators[:5]):
        print(f"   {i+1}. {indicator.name} (UID: {indicator.dhis2_uid}, Type: {indicator.indicator_type})")
    
    if indicators.count() > 5:
        print(f"   ... and {indicators.count() - 5} more")
    
    return indicators

def test_analytics_request(client, indicator, org_unit_id, period):
    """Test analytics request for a specific indicator"""
    print(f"\n=== Testing Analytics Request for {indicator.name} ===")
    
    try:
        print(f"   Indicator: {indicator.name}")
        print(f"   UID: {indicator.dhis2_uid}")
        print(f"   Type: {indicator.indicator_type}")
        print(f"   Org Unit: {org_unit_id}")
        print(f"   Period: {period}")
        
        # Make analytics request
        if indicator.indicator_type == 'indicator':
            response = client.get_analytics_data(
                indicators=[indicator.dhis2_uid],
                periods=[period],
                org_units=[org_unit_id]
            )
        elif indicator.indicator_type == 'dataElement':
            response = client.get_analytics_data(
                data_elements=[indicator.dhis2_uid],
                periods=[period],
                org_units=[org_unit_id]
            )
        elif indicator.indicator_type == 'dataSet':
            response = client.get_data_set_report(
                data_set_id=indicator.dhis2_uid,
                periods=[period],
                org_units=[org_unit_id]
            )
        else:
            response = client.get_analytics_data(
                data_elements=[indicator.dhis2_uid],
                periods=[period],
                org_units=[org_unit_id]
            )
        
        print(f"✅ Analytics request successful")
        print(f"   Response type: {type(response)}")
        
        if isinstance(response, dict):
            print(f"   Response keys: {list(response.keys())}")
            
            if 'rows' in response:
                print(f"   Number of rows: {len(response['rows'])}")
                if response['rows']:
                    print(f"   First row: {response['rows'][0]}")
            
            if 'headers' in response:
                print(f"   Number of headers: {len(response['headers'])}")
                header_names = [h.get('name', 'Unknown') for h in response['headers']]
                print(f"   Header names: {header_names}")
        
        return response
        
    except Exception as e:
        print(f"❌ Analytics request failed: {str(e)}")
        return None

def test_alternative_period_formats(client, indicator, org_unit_id, period):
    """Test alternative period formats"""
    print(f"\n=== Testing Alternative Period Formats for {indicator.name} ===")
    
    # Common DHIS2 period formats
    period_formats = [
        period,  # Original format
        f"{period}Q1",  # Quarterly
        f"{period}Q2",
        f"{period}Q3", 
        f"{period}Q4",
        f"{period}01",  # Monthly
        f"{period}02",
        f"{period}03",
        f"{period}04",
        f"{period}05",
        f"{period}06",
        f"{period}07",
        f"{period}08",
        f"{period}09",
        f"{period}10",
        f"{period}11",
        f"{period}12",
        f"{period}YEAR",  # Yearly
        f"{period}FY",  # Financial year
    ]
    
    for test_period in period_formats:
        try:
            print(f"   Testing period format: {test_period}")
            
            if indicator.indicator_type == 'indicator':
                response = client.get_analytics_data(
                    indicators=[indicator.dhis2_uid],
                    periods=[test_period],
                    org_units=[org_unit_id]
                )
            elif indicator.indicator_type == 'dataElement':
                response = client.get_analytics_data(
                    data_elements=[indicator.dhis2_uid],
                    periods=[test_period],
                    org_units=[org_unit_id]
                )
            else:
                response = client.get_analytics_data(
                    data_elements=[indicator.dhis2_uid],
                    periods=[test_period],
                    org_units=[org_unit_id]
                )
            
            if response and isinstance(response, dict) and response.get('rows'):
                print(f"   ✅ Found data with period format: {test_period}")
                print(f"      Rows: {len(response['rows'])}")
                return test_period, response
            
        except Exception as e:
            if "409" not in str(e):
                print(f"   ❌ Failed with period {test_period}: {str(e)}")
    
    print(f"   ❌ No data found with any period format")
    return None, None

def main():
    """Main debugging function"""
    print("DHIS2 Data Fetching Debug Script")
    print("=" * 50)
    
    # Test connection
    client = test_dhis2_connection()
    if not client:
        return
    
    # Test authentication
    user_info = test_user_authentication(client)
    if not user_info:
        return
    
    # Test org units
    org_units = test_org_units(client)
    if not org_units:
        return
    
    # Test periods
    periods = test_periods(client)
    if not periods:
        return
    
    # Test tracked indicators
    indicators = test_tracked_indicators()
    if not indicators:
        return
    
    # Test analytics requests for first few indicators
    test_org_unit_id = org_units[0]['id'] if org_units else "LEVEL-1"
    test_period = periods
