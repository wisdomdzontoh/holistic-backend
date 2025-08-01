from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from organisation.services import OrgUnitSyncService


class Command(BaseCommand):
    help = 'Sync org units from DHIS2'

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
            '--sync-levels',
            action='store_true',
            default=True,
            help='Sync org unit levels'
        )
        parser.add_argument(
            '--sync-org-units',
            action='store_true',
            default=True,
            help='Sync org units'
        )
        parser.add_argument(
            '--sync-groups',
            action='store_true',
            default=True,
            help='Sync org unit groups'
        )
        parser.add_argument(
            '--org-unit-ids',
            nargs='+',
            help='Specific org unit IDs to sync'
        )
        parser.add_argument(
            '--level-ids',
            nargs='+',
            help='Specific level IDs to sync'
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
            'dhis2_instance_url': options['instance_url'],
            'sync_levels': options['sync_levels'],
            'sync_org_units': options['sync_org_units'],
            'sync_groups': options['sync_groups'],
            'org_unit_ids': options['org_unit_ids'] or [],
            'level_ids': options['level_ids'] or []
        }
        
        try:
            # Initialize sync service
            sync_service = OrgUnitSyncService()
            
            if options['dry_run']:
                self.stdout.write('Would perform org unit sync with the following parameters:')
                self.stdout.write(f"  Instance URL: {sync_request['dhis2_instance_url'] or 'From session'}")
                self.stdout.write(f"  Sync levels: {sync_request['sync_levels']}")
                self.stdout.write(f"  Sync org units: {sync_request['sync_org_units']}")
                self.stdout.write(f"  Sync groups: {sync_request['sync_groups']}")
                self.stdout.write(f"  Org unit IDs: {len(sync_request['org_unit_ids'])} specified")
                self.stdout.write(f"  Level IDs: {len(sync_request['level_ids'])} specified")
                return
            
            # Perform the sync
            self.stdout.write('Starting org unit sync from DHIS2...')
            sync_log = sync_service.sync_org_units(sync_request)
            
            # Display results
            self.stdout.write('\n' + '='*50)
            self.stdout.write('SYNC RESULTS')
            self.stdout.write('='*50)
            self.stdout.write(f"Sync ID: {sync_log.id}")
            self.stdout.write(f"Status: {sync_log.get_status_display()}")
            self.stdout.write(f"Total org units: {sync_log.total_org_units}")
            self.stdout.write(f"Successful org units: {sync_log.successful_org_units}")
            self.stdout.write(f"Failed org units: {sync_log.failed_org_units}")
            self.stdout.write(f"Total levels: {sync_log.total_levels}")
            self.stdout.write(f"Successful levels: {sync_log.successful_levels}")
            self.stdout.write(f"Failed levels: {sync_log.failed_levels}")
            
            if sync_log.duration_seconds:
                minutes = sync_log.duration_seconds // 60
                seconds = sync_log.duration_seconds % 60
                self.stdout.write(f"Duration: {minutes}m {seconds}s")
            
            if sync_log.error_message:
                self.stdout.write(f"Error: {sync_log.error_message}")
            
            if sync_log.status == 'completed':
                self.stdout.write(
                    self.style.SUCCESS('\nOrg unit sync completed successfully!')
                )
            elif sync_log.status == 'partial':
                self.stdout.write(
                    self.style.WARNING('\nOrg unit sync completed with some failures.')
                )
            else:
                self.stdout.write(
                    self.style.ERROR('\nOrg unit sync failed!')
                )
                
        except Exception as e:
            raise CommandError(f'Failed to sync org units: {str(e)}') 