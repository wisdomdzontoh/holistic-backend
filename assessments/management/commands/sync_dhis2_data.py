from django.core.management.base import BaseCommand
from django.utils import timezone
from assessments.services import DataSyncService
from indicators.models import TrackedIndicator
from configurations.models import Objective
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Sync data from DHIS2 and calculate scores'

    def add_arguments(self, parser):
        parser.add_argument(
            '--period-start',
            type=str,
            help='Start date for sync (YYYY-MM-DD)'
        )
        parser.add_argument(
            '--period-end',
            type=str,
            help='End date for sync (YYYY-MM-DD)'
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
            '--dhis2-instance-url',
            type=str,
            help='DHIS2 instance URL'
        )
        parser.add_argument(
            '--debug',
            action='store_true',
            help='Enable debug logging'
        )

    def handle(self, *args, **options):
        if options['debug']:
            logging.getLogger().setLevel(logging.DEBUG)
        
        # Check if there are any tracked indicators
        tracked_indicators = TrackedIndicator.objects.filter(is_active=True)
        if not tracked_indicators.exists():
            self.stdout.write(
                self.style.ERROR('No active tracked indicators found. Please configure indicators first.')
            )
            return
        
        self.stdout.write(f"Found {tracked_indicators.count()} active tracked indicators")
        
        # Check if there are any objectives
        objectives = Objective.objects.filter(is_active=True)
        if not objectives.exists():
            self.stdout.write(
                self.style.ERROR('No active objectives found. Please configure objectives first.')
            )
            return
        
        self.stdout.write(f"Found {objectives.count()} active objectives")
        
        # Build sync request
        sync_request = {
            'sync_type': options['sync_type'],
            'period_start': options['period_start'],
            'period_end': options['period_end'],
            'org_unit_ids': options['org_unit_ids'] or [],
            'indicator_uids': options['indicator_uids'] or [],
            'dhis2_instance_url': options['dhis2_instance_url'],
            'calculate_scores': True
        }
        
        self.stdout.write(f"Starting {options['sync_type']} sync...")
        
        try:
            # Create sync service
            sync_service = DataSyncService()
            
            # Perform sync
            sync_log = sync_service.sync_data(sync_request)
            
            if sync_log.status == 'completed':
                self.stdout.write(
                    self.style.SUCCESS(
                        f'Sync completed successfully! '
                        f'Processed {sync_log.total_indicators} indicators, '
                        f'{sync_log.successful_indicators} successful, '
                        f'{sync_log.failed_indicators} failed, '
                        f'{sync_log.total_data_points} data points'
                    )
                )
            elif sync_log.status == 'partial':
                self.stdout.write(
                    self.style.WARNING(
                        f'Sync completed with partial success! '
                        f'Processed {sync_log.total_indicators} indicators, '
                        f'{sync_log.successful_indicators} successful, '
                        f'{sync_log.failed_indicators} failed, '
                        f'{sync_log.total_data_points} data points'
                    )
                )
            else:
                self.stdout.write(
                    self.style.ERROR(f'Sync failed: {sync_log.error_message}')
                )
                
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Sync failed with error: {str(e)}')
            )
            logger.error(f"Sync command failed: {str(e)}", exc_info=True) 