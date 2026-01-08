#!/bin/bash
# Quick migration script for SQLite to PostgreSQL
# Usage: ./quick_migrate.sh

set -e  # Exit on error

echo "=========================================="
echo "SQLite to PostgreSQL Migration"
echo "=========================================="

# Load .env file if it exists
if [ -f .env ]; then
    export $(grep -v '^#' .env | xargs)
    echo "✓ Loaded .env file"
fi

# Check if DATABASE_URL is set (from .env or environment)
if [ -z "$DATABASE_URL" ]; then
    echo "ERROR: DATABASE_URL not found"
    echo ""
    echo "Please set it in one of these ways:"
    echo "  1. Add to .env file: DATABASE_URL=postgresql://..."
    echo "  2. Set environment variable: export DATABASE_URL='postgresql://...'"
    echo ""
    echo "Get your DATABASE_URL from Render dashboard:"
    echo "  Render Dashboard > PostgreSQL Service > Info > Internal Database URL"
    exit 1
fi

echo "✓ DATABASE_URL found"
echo ""

# Step 1: Export from SQLite
echo "Step 1: Exporting data from SQLite..."
python manage.py dumpdata \
    --exclude=contenttypes \
    --exclude=auth.permission \
    --exclude=sessions \
    --natural-foreign \
    --natural-primary \
    --indent 2 \
    > data_export_$(date +%Y%m%d_%H%M%S).json

if [ $? -eq 0 ]; then
    echo "✓ Data exported successfully"
else
    echo "✗ Export failed"
    exit 1
fi

echo ""

# Step 2: Run migrations on PostgreSQL
echo "Step 2: Running migrations on PostgreSQL..."
python manage.py migrate

if [ $? -eq 0 ]; then
    echo "✓ Migrations completed"
else
    echo "✗ Migrations failed"
    exit 1
fi

echo ""

# Step 3: Import to PostgreSQL
echo "Step 3: Importing data to PostgreSQL..."
LATEST_EXPORT=$(ls -t data_export_*.json | head -1)
python manage.py loaddata "$LATEST_EXPORT"

if [ $? -eq 0 ]; then
    echo "✓ Data imported successfully"
else
    echo "✗ Import failed"
    echo ""
    echo "You can retry the import manually:"
    echo "  python manage.py loaddata $LATEST_EXPORT"
    exit 1
fi

echo ""
echo "=========================================="
echo "Migration completed successfully!"
echo "=========================================="
echo ""
echo "Backup file: $LATEST_EXPORT"
echo "You can delete this file after verifying the migration."

