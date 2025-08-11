# DHIS2 API Timeout Fix - Deployment Guide

## Problem
The application was experiencing **WORKER TIMEOUT** errors when fetching data from DHIS2. The analytics requests were taking longer than the default Gunicorn timeout (30 seconds), causing workers to be killed.

## Root Cause
1. **Slow DHIS2 API responses** - Analytics requests taking >30 seconds
2. **Insufficient timeout settings** - Both Gunicorn and DHIS2 client timeouts too short
3. **Memory issues** - Long-running requests consuming too much memory

## Solution Applied

### 1. **Increased DHIS2 Client Timeout**
- Updated default session timeout from 30s to 60s
- Added specific 120s timeout for analytics requests
- Enhanced timeout handling in `_make_request` method

### 2. **Updated Gunicorn Configuration**
- Increased worker timeout to 120 seconds
- Reduced number of workers to prevent memory issues
- Added request limits and jitter

## Files Modified
- `dhis2_auth/dhis_client.py` - Enhanced timeout handling

## Deployment Steps

### 1. Update Render Start Command
In your Render dashboard, update the start command to:
```bash
gunicorn config.wsgi:application --timeout 120 --workers 2 --worker-class sync --max-requests 1000 --max-requests-jitter 100
```

### 2. Environment Variables
Make sure these are set:
```
DEBUG=False
GUNICORN_TIMEOUT=120
GUNICORN_WORKERS=2
```

### 3. Redeploy
After updating the start command, redeploy your application.

## What This Fixes
- ✅ **No more worker timeouts** - Longer timeout allows slow DHIS2 requests to complete
- ✅ **Better error handling** - Proper timeout management prevents hanging requests
- ✅ **Memory optimization** - Fewer workers with request limits prevent memory issues
- ✅ **Improved reliability** - Analytics data fetching will be more stable

## Monitoring
After deployment, monitor:
- Request completion times
- Memory usage
- Worker restarts
- DHIS2 API response times

## Alternative Solutions (if issues persist)
1. **Implement request caching** for frequently accessed data
2. **Add request queuing** for heavy analytics requests
3. **Implement pagination** for large data sets
4. **Use background tasks** for data fetching

## Testing
Test the fix by:
1. Making multiple analytics requests
2. Monitoring request completion times
3. Checking for timeout errors in logs
4. Verifying data is fetched correctly
