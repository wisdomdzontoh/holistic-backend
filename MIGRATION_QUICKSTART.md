# Quick Start: Migrate SQLite to PostgreSQL

## 🚀 Fastest Method (Recommended)

### Step 1: Get Your PostgreSQL Connection String

1. Go to your Render dashboard
2. Select your PostgreSQL database service
3. Go to the "Info" tab
4. Copy the **"Internal Database URL"** (for Render services) or **"External Database URL"** (for local access)

It should look like:
```
postgresql://user:password@host:port/database
```

### Step 2: Set Environment Variable

**Windows PowerShell:**
```powershell
$env:DATABASE_URL="postgresql://user:password@host:port/database"
```

**Windows CMD:**
```cmd
set DATABASE_URL=postgresql://user:password@host:port/database
```

**Linux/Mac:**
```bash
export DATABASE_URL="postgresql://user:password@host:port/database"
```

### Step 3: Run Migration

**Option A: Use the simple script (Easiest)**
```bash
python simple_migrate.py
```

**Option B: Use PowerShell script (Windows)**
```powershell
.\quick_migrate.ps1
```

**Option C: Use Bash script (Linux/Mac)**
```bash
chmod +x quick_migrate.sh
./quick_migrate.sh
```

**Option D: Manual commands**
```bash
# 1. Export from SQLite
python manage.py dumpdata --exclude=contenttypes --exclude=auth.permission --exclude=sessions --natural-foreign --natural-primary --indent 2 > data_export.json

# 2. Run migrations on PostgreSQL
python manage.py migrate

# 3. Import to PostgreSQL
python manage.py loaddata data_export.json
```

## ✅ Verification

After migration, verify your data:

```bash
python manage.py shell
```

```python
from indicators.models import TrackedIndicator
from configurations.models import Objective
from assessments.models import IndicatorScore

print(f"Tracked Indicators: {TrackedIndicator.objects.count()}")
print(f"Objectives: {Objective.objects.count()}")
print(f"Indicator Scores: {IndicatorScore.objects.count()}")
```

## 🔧 Troubleshooting

### "DATABASE_URL not set"
- Make sure you've set the environment variable in your current terminal session
- Verify the connection string format is correct

### "Connection refused" or "Connection timeout"
- Use the "Internal Database URL" if running on Render
- Check firewall settings
- Verify database credentials

### "Foreign key constraint errors"
- The scripts use `--natural-foreign` to handle this automatically
- If issues persist, try exporting/importing in smaller batches

### "Duplicate key errors"
- The PostgreSQL database might already have some data
- Clear it first: `python manage.py flush` (⚠️ This deletes all data!)

## 📝 What Gets Migrated

✅ All your application data:
- DHIS2 Users
- Tracked Indicators
- Objectives and Milestones
- Assessment Scores
- Configuration data
- All other model data

❌ Excluded (regenerated automatically):
- Content types
- Auth permissions
- Sessions

## 🎯 After Migration

1. **Test your application** - Make sure everything works
2. **Verify data** - Check record counts match
3. **Update production** - Ensure `DATABASE_URL` is set in Render
4. **Keep backup** - Don't delete `db.sqlite3` or export files until verified

## 📚 More Details

See `migration_guide.md` for detailed instructions and advanced options.

