#!/usr/bin/env python3
"""
Management command to collect static files for production deployment
"""

from django.core.management.base import BaseCommand
from django.core.management import call_command
from django.conf import settings
import os
import shutil

class Command(BaseCommand):
    help = 'Collect static files for production deployment'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear the static files directory before collecting',
        )
        parser.add_argument(
            '--noinput',
            action='store_true',
            help='Do not prompt for user input',
        )

    def handle(self, *args, **options):
        self.stdout.write('Collecting static files...')
        
        # Clear static files directory if requested
        if options['clear']:
            if os.path.exists(settings.STATIC_ROOT):
                shutil.rmtree(settings.STATIC_ROOT)
                self.stdout.write(f'Cleared {settings.STATIC_ROOT}')
        
        # Create static files directory if it doesn't exist
        os.makedirs(settings.STATIC_ROOT, exist_ok=True)
        
        # Collect static files
        call_command('collectstatic', 
                    interactive=not options['noinput'],
                    verbosity=1)
        
        self.stdout.write(
            self.style.SUCCESS(f'Successfully collected static files to {settings.STATIC_ROOT}')
        )
        
        # List collected files
        if os.path.exists(settings.STATIC_ROOT):
            file_count = sum([len(files) for r, d, files in os.walk(settings.STATIC_ROOT)])
            self.stdout.write(f'Total static files collected: {file_count}')
