#!/usr/bin/env python3
"""
Generate environment variables for Render deployment
"""

import secrets
import string

def generate_secret_key():
    """Generate a Django secret key"""
    alphabet = string.ascii_letters + string.digits + string.punctuation
    return ''.join(secrets.choice(alphabet) for _ in range(50))

def main():
    print("=== Render Environment Variables ===")
    print()
    
    # Generate secret key
    secret_key = generate_secret_key()
    
    print("SECRET_KEY=" + secret_key)
    print("DEBUG=False")
    print("ALLOWED_HOSTS=holistic-backend-y7gp.onrender.com")
    print("SESSION_COOKIE_SECURE=True")
    print("SESSION_COOKIE_SAMESITE=None")
    print("SESSION_COOKIE_DOMAIN=None")
    print("SESSION_COOKIE_PATH=/")
    print("CORS_ALLOW_CREDENTIALS=True")
    print("CORS_ALLOWED_ORIGINS=https://holistic-assessment.vercel.app")
    print("CORS_ALLOW_HEADERS=accept,accept-encoding,authorization,content-type,dnt,origin,user-agent,x-csrftoken,x-requested-with")
    print("CORS_EXPOSE_HEADERS=set-cookie,access-control-allow-credentials")
    print()
    print("=== Additional Required Variables ===")
    print("DATABASE_URL=<your-postgresql-connection-string>")
    print("DEFAULT_DHIS2_INSTANCE=https://dhims.chimgh.org/dhims")
    print("REDIS_URL=<your-redis-connection-string>")
    print()
    print("=== Instructions ===")
    print("1. Copy these variables to your Render environment variables")
    print("2. Replace <your-postgresql-connection-string> with your actual database URL")
    print("3. Replace <your-redis-connection-string> with your actual Redis URL")
    print("4. Redeploy your application")
    print()
    print("=== Important Notes ===")
    print("- SESSION_COOKIE_SECURE=True is required for HTTPS")
    print("- SESSION_COOKIE_SAMESITE=None allows cross-origin cookies")
    print("- CORS_ALLOW_CREDENTIALS=True enables cookie sending")
    print("- DEBUG=False for production security")

if __name__ == "__main__":
    main()
