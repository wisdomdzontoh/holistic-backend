# Database Migration Guide: SQLite to PostgreSQL

This guide will help you migrate your data from the local SQLite database to the production PostgreSQL database on Render.

## Prerequisites

1. **PostgreSQL Database Setup on Render**
   - Ensure you have a PostgreSQL database service created on Render
   - Note the `DATABASE_URL` from your Render dashboard (Environment tab)

2. **Local Environment Setup**
   - Make sure you have `psycopg2-binary` installed (already in requirements.txt)
   - Make sure you have `dj-database-url` installed (already in requirements.txt)

## Method 1: Using the Migration Script (Recommended)

### Step 1: Set up PostgreSQL Connection

1. Get your `DATABASE_URL` from Render:
   - Go to your Render dashboard
   - Select your PostgreSQL database service
   - Go to "Info" tab
   - Copy the "Internal Database URL" or "External Database URL"

2. Set the environment variable locally:
   ```bash
   # Windows PowerShell
   $env:DATABASE_URL="postgresql://user:password@host:port/database"
   
   # Windows CMD
   set DATABASE_URL=postgresql://user:password@host:port/database
   
   # Linux/Mac
   export DATABASE_URL="postgresql://user:password@host:port/database"
   ```

### Step 2: Update Settings for Migration

Temporarily update `config/settings.py` to support both databases:

```python
# Add this to your settings.py (temporarily)
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    },
    'sqlite': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    },
    'postgres': {
        'ENGINE': 'django.db.backends.postgresql',
    }
}

# Parse DATABASE_URL for PostgreSQL
try:
    import dj_database_url
    if os.getenv('DATABASE_URL'):
        DATABASES['postgres'] = dj_database_url.parse(os.getenv('DATABASE_URL'))
except ImportError:
    pass
```

### Step 3: Run Migrations on PostgreSQL

First, ensure the PostgreSQL database schema is up to date:

```bash
# Set DATABASE_URL
$env:DATABASE_URL="your-postgres-url-here"

# Run migrations on PostgreSQL
python manage.py migrate --database=postgres
```

### Step 4: Run the Migration Script

```bash
python migrate_to_postgres.py
```

The script will:
1. Export all data from SQLite
2. Import it into PostgreSQL
3. Verify the migration

## Method 2: Manual Migration (Alternative)

### Step 1: Export Data from SQLite

```bash
# Export all data (excluding some system tables)
python manage.py dumpdata \
    --exclude=contenttypes \
    --exclude=auth.permission \
    --exclude=sessions \
    --natural-foreign \
    --natural-primary \
    --indent 2 \
    > data_export.json
```

### Step 2: Configure PostgreSQL Connection

Update your `config/settings.py` to use PostgreSQL:

```python
import dj_database_url

DATABASES = {
    'default': dj_database_url.parse(os.getenv('DATABASE_URL'))
}
```

### Step 3: Run Migrations

```bash
# Set DATABASE_URL
$env:DATABASE_URL="your-postgres-url-here"

# Run migrations
python manage.py migrate
```

### Step 4: Import Data

```bash
python manage.py loaddata data_export.json
```

## Method 3: Using Django's Database Router (Advanced)

For a more controlled migration, you can use Django's database routing:

1. Create a database router
2. Export from SQLite
3. Import to PostgreSQL with proper handling of foreign keys

## Troubleshooting

### Issue: Foreign Key Constraint Errors

**Solution:** Export data in the correct order or use `--natural-foreign` flag:
```bash
python manage.py dumpdata --natural-foreign --natural-primary > data.json
```

### Issue: Duplicate Primary Keys

**Solution:** Clear the PostgreSQL database first (BE CAREFUL - this deletes all data):
```bash
python manage.py flush --database=postgres
```

### Issue: Connection Timeout

**Solution:** 
- Use the "Internal Database URL" from Render (if running on Render)
- Check your firewall settings
- Verify database credentials

### Issue: Data Type Mismatches

**Solution:** 
- Ensure all migrations are applied: `python manage.py migrate`
- Check for any custom field types that might need special handling

## Verification Steps

After migration, verify the data:

```bash
# Connect to PostgreSQL
python manage.py shell

# In the shell:
from django.contrib.contenttypes.models import ContentType
from indicators.models import TrackedIndicator
from configurations.models import Objective

# Check record counts
print(f"Tracked Indicators: {TrackedIndicator.objects.count()}")
print(f"Objectives: {Objective.objects.count()}")
```

## Post-Migration Checklist

- [ ] Verify all models have data
- [ ] Test critical functionality
- [ ] Check foreign key relationships
- [ ] Verify user accounts and permissions
- [ ] Test API endpoints
- [ ] Backup the PostgreSQL database
- [ ] Update production settings to use PostgreSQL permanently

## Rollback Plan

If something goes wrong:

1. **Keep your SQLite database** - Don't delete `db.sqlite3` until you're sure
2. **Backup PostgreSQL** - Export from PostgreSQL before making changes
3. **Re-export from SQLite** - You can always re-export if needed

## Production Settings

After successful migration, update your production settings on Render:

1. Set `DATABASE_URL` environment variable in Render dashboard
2. Update `config/settings.py` to use PostgreSQL in production:

```python
# In settings.py
if os.getenv('DATABASE_URL'):
    import dj_database_url
    DATABASES = {
        'default': dj_database_url.parse(os.getenv('DATABASE_URL'))
    }
else:
    # Fallback to SQLite for local development
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }
```

## Notes

- The migration script excludes `contenttypes`, `auth.permission`, and `sessions` as these are typically regenerated
- Large databases may take time to migrate
- Always test the migration on a staging environment first
- Keep backups of both databases during migration

