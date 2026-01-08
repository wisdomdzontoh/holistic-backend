#!/usr/bin/env python
"""
Migration script to transfer data from SQLite to PostgreSQL

Usage:
    python migrate_to_postgres.py

This script will:
1. Export all data from SQLite database
2. Connect to PostgreSQL database
3. Import all data into PostgreSQL

Make sure you have:
- DATABASE_URL environment variable set for PostgreSQL connection
- PostgreSQL database is accessible
- All migrations are applied to PostgreSQL database
"""

import os
import sys
import django
from pathlib import Path
from dotenv import load_dotenv
import environ

# Load environment variables from .env file
BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / '.env')

# Setup Django
sys.path.insert(0, str(BASE_DIR))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

# Also use django-environ for compatibility
env = environ.Env()
environ.Env.read_env(BASE_DIR / '.env')

from django.core.management import call_command
from django.conf import settings
from django.db import connections
import json
from datetime import datetime


def check_databases():
    """Check if both databases are accessible"""
    print("Checking database connections...")
    
    # Check SQLite
    try:
        # Temporarily switch to SQLite
        original_db = settings.DATABASES['default'].copy()
        settings.DATABASES['default'] = {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
        connections['default'].close()
        
        conn = connections['default']
        with conn.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table'")
            table_count = cursor.fetchone()[0]
        print(f"✓ SQLite database connected ({table_count} tables)")
        
        # Restore original
        settings.DATABASES['default'] = original_db
        connections['default'].close()
    except Exception as e:
        print(f"✗ SQLite connection failed: {e}")
        return False
    
    # Check PostgreSQL
    try:
        database_url = os.getenv('DATABASE_URL')
        if not database_url:
            print("✗ DATABASE_URL environment variable not set")
            return False
        
        import dj_database_url
        postgres_config = dj_database_url.parse(database_url)
        
        # Test connection
        from django.db import connection as test_conn
        test_conn.close()
        test_conn.settings_dict = postgres_config
        
        with test_conn.cursor() as cursor:
            cursor.execute("SELECT version();")
            version = cursor.fetchone()[0]
        print(f"✓ PostgreSQL database connected ({version[:50]}...)")
        test_conn.close()
    except Exception as e:
        print(f"✗ PostgreSQL connection failed: {e}")
        print("\nMake sure you have:")
        print("1. DATABASE_URL environment variable set")
        print("2. PostgreSQL database is accessible")
        print("3. All migrations are applied: python manage.py migrate")
        return False
    
    return True


def export_from_sqlite(output_file='data_export.json'):
    """Export all data from SQLite database"""
    print(f"\nExporting data from SQLite to {output_file}...")
    
    try:
        # Switch to SQLite database
        settings.DATABASES['default'] = {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
        
        # Reconnect to SQLite
        connections['default'].close()
        
        # Export data
        with open(output_file, 'w', encoding='utf-8') as f:
            call_command('dumpdata', 
                        exclude=['contenttypes', 'auth.permission', 'sessions'],
                        natural_foreign=True,
                        natural_primary=True,
                        indent=2,
                        stdout=f)
        
        # Get file size
        file_size = os.path.getsize(output_file) / (1024 * 1024)  # MB
        print(f"✓ Data exported successfully ({file_size:.2f} MB)")
        
        # Count records
        with open(output_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        print(f"✓ Exported {len(data)} records")
        
        return True
    except Exception as e:
        print(f"✗ Export failed: {e}")
        return False


def import_to_postgres(input_file='data_export.json'):
    """Import data into PostgreSQL database"""
    print(f"\nImporting data from {input_file} to PostgreSQL...")
    
    try:
        # Switch to PostgreSQL database
        import dj_database_url
        database_url = os.getenv('DATABASE_URL')
        
        if not database_url:
            print("✗ DATABASE_URL environment variable not set")
            return False
        
        settings.DATABASES['default'] = dj_database_url.parse(database_url)
        
        # Reconnect to PostgreSQL
        connections['default'].close()
        
        # Import data
        with open(input_file, 'r', encoding='utf-8') as f:
            call_command('loaddata', input_file, verbosity=1)
        
        print("✓ Data imported successfully")
        return True
    except Exception as e:
        print(f"✗ Import failed: {e}")
        print("\nCommon issues:")
        print("1. Foreign key constraints - make sure all related data is exported")
        print("2. Duplicate entries - you may need to clear PostgreSQL database first")
        print("3. Data type mismatches - check for any custom field types")
        return False


def verify_migration():
    """Verify that data was migrated correctly"""
    print("\nVerifying migration...")
    
    try:
        import dj_database_url
        database_url = os.getenv('DATABASE_URL')
        settings.DATABASES['default'] = dj_database_url.parse(database_url)
        connections['default'].close()
        
        from django.apps import apps
        from django.db import models
        
        # Count records in key models
        key_models = [
            'dhis2_auth.DHIS2User',
            'indicators.TrackedIndicator',
            'configurations.Objective',
            'assessments.IndicatorScore',
        ]
        
        print("\nRecord counts in PostgreSQL:")
        for model_path in key_models:
            try:
                app_label, model_name = model_path.split('.')
                model = apps.get_model(app_label, model_name)
                count = model.objects.count()
                print(f"  {model_path}: {count} records")
            except Exception as e:
                print(f"  {model_path}: Error - {e}")
        
        return True
    except Exception as e:
        print(f"✗ Verification failed: {e}")
        return False


def main():
    """Main migration function"""
    print("=" * 60)
    print("SQLite to PostgreSQL Migration Script")
    print("=" * 60)
    
    # Check databases
    if not check_databases():
        sys.exit(1)
    
    # Export from SQLite
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_file = f'data_export_{timestamp}.json'
    
    if not export_from_sqlite(output_file):
        sys.exit(1)
    
    # Import to PostgreSQL
    if not import_to_postgres(output_file):
        print("\n⚠ Import failed. You can retry by running:")
        print(f"   python manage.py loaddata {output_file}")
        sys.exit(1)
    
    # Verify
    verify_migration()
    
    print("\n" + "=" * 60)
    print("Migration completed successfully!")
    print("=" * 60)
    print(f"\nBackup file saved as: {output_file}")
    print("You can delete this file after verifying the migration.")


if __name__ == '__main__':
    main()

