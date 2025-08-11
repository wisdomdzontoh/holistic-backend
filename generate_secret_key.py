#!/usr/bin/env python3
"""
Script to generate a Django secret key for production deployment
"""

from django.core.management.utils import get_random_secret_key

if __name__ == "__main__":
    secret_key = get_random_secret_key()
    print("Generated Django Secret Key:")
    print(secret_key)
    print("\nCopy this key and set it as the SECRET_KEY environment variable on Render.")
