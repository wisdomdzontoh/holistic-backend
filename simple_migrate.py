#!/usr/bin/env python
"""
Simple migration script to transfer data from SQLite to PostgreSQL

Usage:
    1. Set DATABASE_URL environment variable
    2. python simple_migrate.py

This script will:
1. Export all data from SQLite database (using current default)
2. Switch to PostgreSQL
3. Run migrations
4. Import all data into PostgreSQL
"""

import os
import sys
import subprocess
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv
import environ

BASE_DIR = Path(__file__).resolve().parent

# Load environment variables from .env file
load_dotenv(BASE_DIR / '.env')

# Also use django-environ for compatibility
env = environ.Env()
environ.Env.read_env(BASE_DIR / '.env')

def run_command(cmd, description):
    """Run a command and handle errors"""
    print(f"\n{description}...")
    print(f"Running: {' '.join(cmd)}")
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode == 0:
        print(f"[OK] {description} completed")
        if result.stdout:
            print(result.stdout)
        return True
    else:
        print(f"[ERROR] {description} failed")
        if result.stderr:
            print("Error:", result.stderr)
        if result.stdout:
            print("Output:", result.stdout)
        return False

def main():
    print("=" * 60)
    print("Simple SQLite to PostgreSQL Migration")
    print("=" * 60)
    
    # Check DATABASE_URL (from .env file or environment)
    database_url = os.getenv('DATABASE_URL') or env('DATABASE_URL', default=None)
    
    if not database_url:
        print("\n[ERROR] DATABASE_URL not found")
        print("\nPlease set it in one of these ways:")
        print("  1. Add to .env file: DATABASE_URL=postgresql://...")
        print("  2. Set environment variable:")
        print("     Windows PowerShell: $env:DATABASE_URL='postgresql://...'")
        print("     Linux/Mac: export DATABASE_URL='postgresql://...'")
        print("\nGet your DATABASE_URL from Render dashboard:")
        print("  Render Dashboard > PostgreSQL Service > Info > Internal Database URL")
        print(f"\nChecked .env file at: {BASE_DIR / '.env'}")
        sys.exit(1)
    
    print(f"[OK] DATABASE_URL found")
    # Show first/last few chars for verification (don't show full password)
    if len(database_url) > 50:
        masked_url = database_url[:30] + "..." + database_url[-20:]
        print(f"  {masked_url}")
    else:
        print(f"  {database_url}")
    
    # Step 1: Export from SQLite
    # Use a separate script that forces SQLite usage
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    export_file = f'data_export_{timestamp}.json'
    
    print("\n[INFO] Using dedicated SQLite export script...")
    export_cmd = [sys.executable, 'export_from_sqlite.py']
    
    # Run the export script (it will create its own file with timestamp)
    result = subprocess.run(export_cmd, capture_output=True, text=True)
    
    if result.returncode == 0:
        print("[OK] Export completed")
        if result.stdout:
            print(result.stdout)
        
        # Find the export file (the script creates it with timestamp)
        # List all recent export files and use the newest one
        export_files = sorted(
            [f for f in BASE_DIR.glob('data_export_*.json')],
            key=lambda x: x.stat().st_mtime,
            reverse=True
        )
        
        if export_files:
            export_file = export_files[0].name
            print(f"  Using export file: {export_file}")
        else:
            print("[ERROR] Could not find export file")
            sys.exit(1)
    else:
        print("[ERROR] Export failed")
        if result.stderr:
            print("Error:", result.stderr)
        if result.stdout:
            print("Output:", result.stdout)
        sys.exit(1)
    
    # Check file size and verify data was exported
    if os.path.exists(export_file):
        size_mb = os.path.getsize(export_file) / (1024 * 1024)
        size_bytes = os.path.getsize(export_file)
        print(f"  Export file size: {size_mb:.2f} MB ({size_bytes:,} bytes)")
        
        # Check if file is empty or just contains empty array
        if size_bytes < 100:  # Less than 100 bytes is suspicious
            import json
            try:
                with open(export_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if not data or len(data) == 0:
                        print("\n[WARNING] Export file appears to be empty!")
                        print("  This might mean:")
                        print("  1. SQLite database is actually empty")
                        print("  2. Export failed silently")
                        print("  3. All data was excluded by filters")
                        print("\n  Checking SQLite database...")
                        
                        # Quick check of SQLite
                        import sqlite3
                        sqlite_db = BASE_DIR / 'db.sqlite3'
                        if sqlite_db.exists():
                            conn = sqlite3.connect(str(sqlite_db))
                            cursor = conn.cursor()
                            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                            tables = cursor.fetchall()
                            print(f"  Found {len(tables)} tables in SQLite")
                            for table in tables[:10]:  # Show first 10 tables
                                try:
                                    cursor.execute(f"SELECT COUNT(*) FROM \"{table[0]}\"")
                                    count = cursor.fetchone()[0]
                                    if count > 0:
                                        print(f"    - {table[0]}: {count} records")
                                except:
                                    pass
                            conn.close()
                            
                            print("\n  [WARNING] Export appears to have failed. Please try:")
                            print("    1. Manually export: python manage.py dumpdata --exclude=contenttypes --exclude=auth.permission --exclude=sessions > manual_export.json")
                            print("    2. Make sure DATABASE_URL is NOT set when exporting")
            except Exception as e:
                print(f"  Could not verify export file: {e}")
    
    # Step 2: Run migrations on PostgreSQL
    # DATABASE_URL is already set, so Django will use it
    migrate_cmd = [sys.executable, 'manage.py', 'migrate']
    
    if not run_command(migrate_cmd, "Running migrations on PostgreSQL"):
        print("\n[WARNING] Migrations failed, but continuing...")
        print("You may need to run migrations manually:")
        print(f"  python manage.py migrate")
    
    # Step 3: Import to PostgreSQL
    loaddata_cmd = [sys.executable, 'manage.py', 'loaddata', export_file]
    
    if not run_command(loaddata_cmd, "Importing data to PostgreSQL"):
        print("\n[WARNING] Import failed. You can retry manually:")
        print(f"  python manage.py loaddata {export_file}")
        sys.exit(1)
    
    # Success
    print("\n" + "=" * 60)
    print("Migration completed successfully!")
    print("=" * 60)
    print(f"\nBackup file: {export_file}")
    print("Keep this file as a backup until you verify the migration.")
    print("\nNext steps:")
    print("1. Verify data in PostgreSQL database")
    print("2. Test your application")
    print("3. Update production settings if needed")
    print("4. Delete the backup file after verification")

if __name__ == '__main__':
    main()

