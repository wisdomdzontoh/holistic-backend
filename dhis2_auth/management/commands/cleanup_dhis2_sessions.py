from django.core.management.base import BaseCommand
from django.utils import timezone
from dhis2_auth.session import cleanup_expired_sessions
from dhis2_auth.models import DHIS2Session


class Command(BaseCommand):
    help = 'Clean up expired DHIS2 sessions'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be cleaned up without actually doing it',
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force cleanup even if sessions are not expired',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        force = options['force']
        
        if dry_run:
            self.stdout.write('DRY RUN MODE - No changes will be made')
        
        # Get expired sessions
        if force:
            expired_sessions = DHIS2Session.objects.filter(is_active=True)
            self.stdout.write(f'Found {expired_sessions.count()} active sessions')
        else:
            expired_sessions = DHIS2Session.objects.filter(
                expires_at__lt=timezone.now(),
                is_active=True
            )
            self.stdout.write(f'Found {expired_sessions.count()} expired sessions')
        
        if expired_sessions.exists():
            self.stdout.write('Sessions to be cleaned up:')
            for session in expired_sessions[:10]:  # Show first 10
                self.stdout.write(
                    f'  - {session.session_key} ({session.user.dhis2_username}) - '
                    f'Expires: {session.expires_at}'
                )
            
            if expired_sessions.count() > 10:
                self.stdout.write(f'  ... and {expired_sessions.count() - 10} more')
            
            if not dry_run:
                # Perform cleanup
                cleanup_expired_sessions()
                self.stdout.write(
                    self.style.SUCCESS(f'Successfully cleaned up {expired_sessions.count()} sessions')
                )
            else:
                self.stdout.write('DRY RUN: Would clean up the above sessions')
        else:
            self.stdout.write(self.style.SUCCESS('No sessions to clean up')) 