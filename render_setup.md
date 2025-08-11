# Render Deployment Setup Guide

## Environment Variables to Set on Render

You need to configure these environment variables in your Render dashboard:

### Required Environment Variables

1. **SECRET_KEY**
   - Generate a new secret key: `python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"`
   - Set this in Render dashboard

2. **DEBUG**
   - Set to: `False` (for production)

3. **ALLOWED_HOSTS**
   - Set to: `localhost,127.0.0.1,0.0.0.0,holistic-backend-y7gp.onrender.com`

4. **DATABASE_URL** (if using PostgreSQL)
   - Render will provide this automatically if you add a PostgreSQL service

5. **DEFAULT_DHIS2_INSTANCE**
   - Set to your DHIS2 instance URL (e.g., `https://dhims.chimgh.org/dhims`)

6. **REDIS_URL** (if using Redis for Celery)
   - Render will provide this if you add a Redis service

### How to Set Environment Variables on Render

1. Go to your Render dashboard
2. Select your web service
3. Go to "Environment" tab
4. Add each variable with its value
5. Save and redeploy

### Example Environment Variables

```
SECRET_KEY=your-generated-secret-key-here
DEBUG=False
ALLOWED_HOSTS=localhost,127.0.0.1,0.0.0.0,holistic-backend-y7gp.onrender.com
DEFAULT_DHIS2_INSTANCE=https://dhims.chimgh.org/dhims
```

### Build Command for Render

Make sure your build command is:
```bash
pip install -r requirements.txt
```

### Start Command for Render

Make sure your start command is:
```bash
python manage.py migrate && python manage.py runserver 0.0.0.0:$PORT
```

### Additional Notes

- The `ALLOWED_HOSTS` setting has been updated to automatically include your Render domain
- Security settings are automatically enabled in production
- HTTPS redirects are enabled for production
- Session cookies are secure in production
