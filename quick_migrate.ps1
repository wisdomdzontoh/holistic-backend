# Quick migration script for SQLite to PostgreSQL (PowerShell)
# Usage: .\quick_migrate.ps1

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "SQLite to PostgreSQL Migration" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""

# Load .env file if it exists
$envFile = Join-Path $PSScriptRoot ".env"
if (Test-Path $envFile) {
    Get-Content $envFile | ForEach-Object {
        if ($_ -match '^\s*([^#][^=]*)=(.*)$') {
            $key = $matches[1].Trim()
            $value = $matches[2].Trim()
            if (-not [string]::IsNullOrWhiteSpace($key)) {
                [Environment]::SetEnvironmentVariable($key, $value, "Process")
            }
        }
    }
    Write-Host "✓ Loaded .env file" -ForegroundColor Green
}

# Check if DATABASE_URL is set (from .env or environment)
if (-not $env:DATABASE_URL) {
    Write-Host "ERROR: DATABASE_URL not found" -ForegroundColor Red
    Write-Host ""
    Write-Host "Please set it in one of these ways:" -ForegroundColor Yellow
    Write-Host "  1. Add to .env file: DATABASE_URL=postgresql://..." -ForegroundColor Yellow
    Write-Host '  2. Set environment variable: $env:DATABASE_URL="postgresql://..."' -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Get your DATABASE_URL from Render dashboard:" -ForegroundColor Yellow
    Write-Host "  Render Dashboard > PostgreSQL Service > Info > Internal Database URL" -ForegroundColor Yellow
    exit 1
}

Write-Host "✓ DATABASE_URL is set" -ForegroundColor Green
Write-Host ""

# Step 1: Export from SQLite
Write-Host "Step 1: Exporting data from SQLite..." -ForegroundColor Cyan
$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$exportFile = "data_export_$timestamp.json"

python manage.py dumpdata `
    --exclude=contenttypes `
    --exclude=auth.permission `
    --exclude=sessions `
    --natural-foreign `
    --natural-primary `
    --indent 2 `
    | Out-File -FilePath $exportFile -Encoding UTF8

if ($LASTEXITCODE -eq 0) {
    Write-Host "✓ Data exported successfully" -ForegroundColor Green
} else {
    Write-Host "✗ Export failed" -ForegroundColor Red
    exit 1
}

Write-Host ""

# Step 2: Run migrations on PostgreSQL
Write-Host "Step 2: Running migrations on PostgreSQL..." -ForegroundColor Cyan
python manage.py migrate

if ($LASTEXITCODE -eq 0) {
    Write-Host "✓ Migrations completed" -ForegroundColor Green
} else {
    Write-Host "✗ Migrations failed" -ForegroundColor Red
    exit 1
}

Write-Host ""

# Step 3: Import to PostgreSQL
Write-Host "Step 3: Importing data to PostgreSQL..." -ForegroundColor Cyan
python manage.py loaddata $exportFile

if ($LASTEXITCODE -eq 0) {
    Write-Host "✓ Data imported successfully" -ForegroundColor Green
} else {
    Write-Host "✗ Import failed" -ForegroundColor Red
    Write-Host ""
    Write-Host "You can retry the import manually:" -ForegroundColor Yellow
    Write-Host "  python manage.py loaddata $exportFile" -ForegroundColor Yellow
    exit 1
}

Write-Host ""
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "Migration completed successfully!" -ForegroundColor Green
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Backup file: $exportFile" -ForegroundColor Yellow
Write-Host "You can delete this file after verifying the migration." -ForegroundColor Yellow

