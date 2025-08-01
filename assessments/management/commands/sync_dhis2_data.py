from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from assessments.services import DataSyncService
from configurations.models import AssessmentPeriod


class Command(BaseCommand):
    help = 'Sync data from DHIS2 and calculate scores'

    def add_arguments(self, parser):
        parser.add_argument(
            '--instance-url',
            type=str,
            help='DHIS2 instance URL'
        )
        parser.add_argument(
            '--username',
            type=str,
            help='DHIS2 username'
        )
        parser.add_argument(
            '--password',
            type=str,
            help='DHIS2 password'
        )
        parser.add_argument(
            '--period-start',
            type=str,
            help='Start date for data sync (YYYY-MM-DD)'
        )
        parser.add_argument(
            '--period-end',
            type=str,
            help='End date for data sync (YYYY-MM-DD)'
        )
        parser.add_argument(
            '--org-unit-ids',
            nargs='+',
            help='List of org unit IDs to sync'
        )
        parser.add_argument(
            '--indicator-uids',
            nargs='+',
            help='List of indicator UIDs to sync'
        )
        parser.add_argument(
            '--sync-type',
            choices=['full', 'incremental', 'indicator', 'period'],
            default='full',
            help='Type of sync to perform'
        )
        parser.add_argument(
            '--no-calculate-scores',
            action='store_true',
            help='Skip score calculation after data sync'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be synced without actually doing it'
        )

    def handle(self, *args, **options):
        if options['dry_run']:
            self.stdout.write('DRY RUN MODE - No changes will be made')
        
        # Build sync request
        sync_request = {
            'sync_type': options['sync_type'],
            'dhis2_instance_url': options['instance_url'],
            'period_start': options['period_start'],
            'period_end': options['period_end'],
            'org_unit_ids': options['org_unit_ids'] or [],
            'indicator_uids': options['indicator_uids'] or [],
            'calculate_scores': not options['no_calculate_scores']
        }
        
        try:
            # Initialize sync service
            sync_service = DataSyncService()
            
            if options['dry_run']:
                self.stdout.write('Would perform sync with the following parameters:')
                self.stdout.write(f"  Sync type: {sync_request['sync_type']}")
                self.stdout.write(f"  Instance URL: {sync_request['dhis2_instance_url'] or 'From session'}")
                self.stdout.write(f"  Period start: {sync_request['period_start'] or 'Current period'}")
                self.stdout.write(f"  Period end: {sync_request['period_end'] or 'Current period'}")
                self.stdout.write(f"  Org units: {len(sync_request['org_unit_ids'])} specified")
                self.stdout.write(f"  Indicators: {len(sync_request['indicator_uids'])} specified")
                self.stdout.write(f"  Calculate scores: {sync_request['calculate_scores']}")
                return
            
            # Perform the sync
            self.stdout.write('Starting DHIS2 data sync...')
            sync_log = sync_service.sync_data(sync_request)
            
            # Display results
            self.stdout.write('\n' + '='*50)
            self.stdout.write('SYNC RESULTS')
            self.stdout.write('='*50)
            self.stdout.write(f"Sync ID: {sync_log.id}")
            self.stdout.write(f"Status: {sync_log.get_status_display()}")
            self.stdout.write(f"Total indicators: {sync_log.total_indicators}")
            self.stdout.write(f"Successful: {sync_log.successful_indicators}")
            self.stdout.write(f"Failed: {sync_log.failed_indicators}")
            self.stdout.write(f"Total data points: {sync_log.total_data_points}")
            
            if sync_log.duration_seconds:
                minutes = sync_log.duration_seconds // 60
                seconds = sync_log.duration_seconds % 60
                self.stdout.write(f"Duration: {minutes}m {seconds}s")
            
            if sync_log.error_message:
                self.stdout.write(f"Error: {sync_log.error_message}")
            
            if sync_log.status == 'completed':
                self.stdout.write(
                    self.style.SUCCESS('\nData sync completed successfully!')
                )
            elif sync_log.status == 'partial':
                self.stdout.write(
                    self.style.WARNING('\nData sync completed with some failures.')
                )
            else:
                self.stdout.write(
                    self.style.ERROR('\nData sync failed!')
                )
                
        except Exception as e:
            raise CommandError(f'Failed to sync data: {str(e)}') 