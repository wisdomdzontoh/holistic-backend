#!/usr/bin/env python
"""
Direct export script that forces SQLite usage
This script temporarily renames .env file to prevent PostgreSQL connection
"""

import os
import sys
import django
from pathlib import Path
import json
import shutil

# Setup Django
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

# Temporarily rename .env file to prevent django-environ from reading DATABASE_URL
env_file = BASE_DIR / '.env'
env_backup = BASE_DIR / '.env.backup'
env_renamed = False

if env_file.exists():
    try:
        shutil.move(str(env_file), str(env_backup))
        env_renamed = True
        print("[INFO] Temporarily renamed .env to force SQLite usage")
    except Exception as e:
        print(f"[WARNING] Could not rename .env file: {e}")

# Remove DATABASE_URL from environment
original_database_url = os.environ.pop('DATABASE_URL', None)

# Set Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

try:
    # Initialize Django
    django.setup()
    
    # Force SQLite database configuration
    from django.conf import settings
    from django.core.management import call_command
    from django.db import connections
    
    # Force SQLite database configuration
    settings.DATABASES['default'] = {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': str(BASE_DIR / 'db.sqlite3'),
    }
    
    # Close any existing connections and reconnect to SQLite
    connections['default'].close()
    
finally:
    # Restore .env file
    if env_renamed and env_backup.exists():
        try:
            shutil.move(str(env_backup), str(env_file))
            print("[OK] Restored .env file")
        except Exception as e:
            print(f"[WARNING] Could not restore .env file: {e}")
    
    # Restore DATABASE_URL if it was set
    if original_database_url:
        os.environ['DATABASE_URL'] = original_database_url

def export_data(output_file):
    """Export all data from SQLite"""
    print(f"Exporting data from SQLite to {output_file}...")
    print(f"Database: {settings.DATABASES['default']['NAME']}")
    
    # Export data
    with open(output_file, 'w', encoding='utf-8') as f:
        call_command(
            'dumpdata',
            exclude=['contenttypes', 'auth.permission', 'sessions'],
            natural_foreign=True,
            natural_primary=True,
            indent=2,
            stdout=f
        )
    
    # Check results
    if os.path.exists(output_file):
        size = os.path.getsize(output_file)
        print(f"[OK] Export completed: {size:,} bytes ({size / 1024 / 1024:.2f} MB)")
        
        # Verify it's not empty
        with open(output_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            print(f"[OK] Exported {len(data)} records")
            return len(data) > 0
    return False

if __name__ == '__main__':
    from datetime import datetime
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_file = f'data_export_{timestamp}.json'
    
    if export_data(output_file):
        print(f"\n[SUCCESS] Export file: {output_file}")
    else:
        print("\n[ERROR] Export failed or produced empty file")
        sys.exit(1)

