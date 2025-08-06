#!/usr/bin/env python
"""
Test script to verify import/export functionality for TrackedIndicator
"""

import os
import sys
import django
from django.conf import settings

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from indicators.models import TrackedIndicator
from indicators.admin import TrackedIndicatorResource
import tempfile
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_export():
    """Test exporting TrackedIndicator data"""
    print("Testing export functionality...")
    
    # Get all tracked indicators
    indicators = TrackedIndicator.objects.all()
    print(f"Found {indicators.count()} indicators to export")
    
    if indicators.count() == 0:
        print("No indicators found. Please run init_default_configurations first.")
        return False
    
    # Create resource
    resource = TrackedIndicatorResource()
    
    # Export data
    dataset = resource.export(indicators)
    
    # Save to temporary file
    with tempfile.NamedTemporaryFile(mode='w+b', suffix='.xlsx', delete=False) as f:
        f.write(dataset.xlsx)
        temp_file = f.name
    
    print(f"✅ Export successful! File saved to: {temp_file}")
    print(f"Exported {len(dataset)} rows")
    
    # Show sample data
    print("\nSample exported data:")
    for i, row in enumerate(dataset[:3]):
        print(f"  {i+1}. {row[0]} ({row[1]}) - {row[2]}")
    
    return temp_file


def test_import(export_file):
    """Test importing TrackedIndicator data"""
    print("\nTesting import functionality...")
    
    # Count existing indicators
    initial_count = TrackedIndicator.objects.count()
    print(f"Initial indicator count: {initial_count}")
    
    # Create resource
    resource = TrackedIndicatorResource()
    
    # Read the exported file and create dataset
    with open(export_file, 'rb') as f:
        from import_export.formats import base_formats
        dataset = base_formats.XLSX().create_dataset(f.read())
    
    # Import the dataset
    result = resource.import_data(dataset, raise_errors=True)
    
    print(f"✅ Import successful!")
    print(f"Total rows: {result.total_rows}")
    print(f"Invalid rows: {result.invalid_rows}")
    print(f"Valid rows: {result.valid_rows}")
    
    # Count indicators after import
    final_count = TrackedIndicator.objects.count()
    print(f"Final indicator count: {final_count}")
    
    if final_count > initial_count:
        print("✅ New indicators were imported")
    else:
        print("ℹ️ No new indicators imported (existing ones were updated)")


def test_template_export():
    """Test exporting empty template"""
    print("\nTesting template export...")
    
    # Create resource
    resource = TrackedIndicatorResource()
    
    # Export empty dataset (template)
    dataset = resource.export(TrackedIndicator.objects.none())
    
    # Save to temporary file
    with tempfile.NamedTemporaryFile(mode='w+b', suffix='.xlsx', delete=False) as f:
        f.write(dataset.xlsx)
        temp_file = f.name
    
    print(f"✅ Template export successful! File saved to: {temp_file}")
    print(f"Template has {len(dataset)} columns")
    
    return temp_file


def main():
    """Run all tests"""
    print("🧪 Testing TrackedIndicator Import/Export Functionality")
    print("=" * 60)
    
    try:
        # Test template export
        template_file = test_template_export()
        
        # Test data export
        export_file = test_export()
        
        if export_file:
            # Test import
            test_import(export_file)
        
        print("\n✅ All tests completed successfully!")
        print("\n📋 Next steps:")
        print("1. Go to Django Admin > Indicators > Tracked Indicators")
        print("2. Use the 'Download Import Template' button to get a template")
        print("3. Fill in the template with your DHIS2 indicator data")
        print("4. Use the 'Import' button to upload your data")
        print("5. Use the 'Export Current Data' button to backup existing data")
        
    except Exception as e:
        print(f"❌ Test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    
    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 