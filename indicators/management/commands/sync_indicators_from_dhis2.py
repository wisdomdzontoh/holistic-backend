from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from indicators.models import TrackedIndicator
from dhis2_auth.dhis_client import DHIS2Client


class Command(BaseCommand):
    help = 'Sync indicator metadata from DHIS2'

    def add_arguments(self, parser):
        parser.add_argument(
            '--instance-url',
            type=str,
            required=True,
            help='DHIS2 instance URL'
        )
        parser.add_argument(
            '--username',
            type=str,
            required=True,
            help='DHIS2 username'
        )
        parser.add_argument(
            '--password',
            type=str,
            required=True,
            help='DHIS2 password'
        )
        parser.add_argument(
            '--indicator-uid',
            type=str,
            help='Sync specific indicator by UID'
        )
        parser.add_argument(
            '--indicator-type',
            choices=['indicator', 'dataElement'],
            help='Sync only indicators of specific type'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be synced without actually doing it'
        )

    def handle(self, *args, **options):
        instance_url = options['instance_url']
        username = options['username']
        password = options['password']
        indicator_uid = options.get('indicator_uid')
        indicator_type = options.get('indicator_type')
        dry_run = options['dry_run']
        
        if dry_run:
            self.stdout.write('DRY RUN MODE - No changes will be made')
        
        try:
            # Create DHIS2 client
            client = DHIS2Client(
                instance_url=instance_url,
                username=username,
                password=password
            )
            
            # Test connection
            if not client.test_connection():
                raise CommandError('Failed to connect to DHIS2 instance')
            
            self.stdout.write(f'Connected to DHIS2 instance: {instance_url}')
            
            # Get indicators to sync
            if indicator_uid:
                indicators = TrackedIndicator.objects.filter(dhis2_uid=indicator_uid)
                if not indicators.exists():
                    raise CommandError(f'Indicator with UID {indicator_uid} not found')
            else:
                indicators = TrackedIndicator.objects.filter(is_active=True)
                if indicator_type:
                    indicators = indicators.filter(indicator_type=indicator_type)
            
            self.stdout.write(f'Found {indicators.count()} indicators to sync')
            
            synced_count = 0
            errors = []
            
            for indicator in indicators:
                try:
                    self.stdout.write(f'Syncing {indicator.name} ({indicator.dhis2_uid})...')
                    
                    # Determine endpoint based on indicator type
                    if indicator.indicator_type == TrackedIndicator.IndicatorType.INDICATOR:
                        endpoint = f'/api/indicators/{indicator.dhis2_uid}'
                    elif indicator.indicator_type == TrackedIndicator.IndicatorType.DATA_ELEMENT:
                        endpoint = f'/api/dataElements/{indicator.dhis2_uid}'
                    else:
                        self.stdout.write(
                            self.style.WARNING(f'Skipping calculated indicator: {indicator.name}')
                        )
                        continue
                    
                    if not dry_run:
                        # Fetch metadata from DHIS2
                        metadata = client._make_request('GET', endpoint)
                        
                        # Update indicator with DHIS2 metadata
                        indicator.dhis2_name = metadata.get('name', '')
                        indicator.dhis2_description = metadata.get('description', '')
                        indicator.last_sync = timezone.now()
                        indicator.save()
                        
                        synced_count += 1
                        self.stdout.write(
                            self.style.SUCCESS(f'✓ Synced: {indicator.name}')
                        )
                    else:
                        synced_count += 1
                        self.stdout.write(f'Would sync: {indicator.name}')
                    
                except Exception as e:
                    error_msg = f'{indicator.name}: {str(e)}'
                    errors.append(error_msg)
                    self.stdout.write(
                        self.style.ERROR(f'✗ Error syncing {indicator.name}: {str(e)}')
                    )
            
            # Summary
            self.stdout.write('\n' + '='*50)
            self.stdout.write('SYNC SUMMARY')
            self.stdout.write('='*50)
            self.stdout.write(f'Total indicators processed: {indicators.count()}')
            self.stdout.write(f'Successfully synced: {synced_count}')
            self.stdout.write(f'Errors: {len(errors)}')
            
            if errors:
                self.stdout.write('\nErrors:')
                for error in errors:
                    self.stdout.write(f'  - {error}')
            
            if not dry_run:
                self.stdout.write(
                    self.style.SUCCESS(f'\nSuccessfully synced {synced_count} indicators')
                )
            else:
                self.stdout.write(f'\nWould sync {synced_count} indicators')
                
        except Exception as e:
            raise CommandError(f'Failed to sync indicators: {str(e)}') 