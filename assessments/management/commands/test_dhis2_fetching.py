from django.core.management.base import BaseCommand
from django.utils import timezone
from assessments.services import DataSyncService
from indicators.models import TrackedIndicator
from configurations.models import Objective, AssessmentPeriod
from dhis2_auth.dhis_client import DHIS2Client
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Test improved DHIS2 data fetching functionality'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dhis2-instance-url',
            type=str,
            default='https://dhims.chimgh.org/dhims',
            help='DHIS2 instance URL'
        )
        parser.add_argument(
            '--username',
            type=str,
            default='admin',
            help='DHIS2 username'
        )
        parser.add_argument(
            '--password',
            type=str,
            default='district',
            help='DHIS2 password'
        )
        parser.add_argument(
            '--test-indicators',
            action='store_true',
            help='Test fetching indicators from DHIS2'
        )
        parser.add_argument(
            '--test-data-elements',
            action='store_true',
            help='Test fetching data elements from DHIS2'
        )
        parser.add_argument(
            '--test-analytics',
            action='store_true',
            help='Test analytics data fetching'
        )
        parser.add_argument(
            '--org-unit-id',
            type=str,
            help='Organization unit ID for testing'
        )
        parser.add_argument(
            '--period',
            type=str,
            default='2024',
            help='Period for testing (e.g., 2024, 2024Q1)'
        )
        parser.add_argument(
            '--debug',
            action='store_true',
            help='Enable debug logging'
        )

    def handle(self, *args, **options):
        if options['debug']:
            logging.getLogger().setLevel(logging.DEBUG)
        
        self.stdout.write("Testing improved DHIS2 data fetching functionality...")
        
        # Initialize DHIS2 client
        try:
            client = DHIS2Client(
                instance_url=options['dhis2_instance_url'],
                username=options['username'],
                password=options['password']
            )
            
            # Test connection
            self.stdout.write("Testing DHIS2 connection...")
            if client.test_connection():
                self.stdout.write(self.style.SUCCESS("✓ DHIS2 connection successful"))
            else:
                self.stdout.write(self.style.ERROR("✗ DHIS2 connection failed"))
                return
            
            # Test authentication
            self.stdout.write("Testing DHIS2 authentication...")
            try:
                user_info = client.authenticate_user()
                self.stdout.write(self.style.SUCCESS(f"✓ Authentication successful for user: {user_info.get('name', 'Unknown')}"))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"✗ Authentication failed: {str(e)}"))
                return
            
            # Test indicators fetching
            if options['test_indicators']:
                self.stdout.write("Testing indicators fetching...")
                try:
                    indicators = client.get_indicators(limit=5)
                    self.stdout.write(self.style.SUCCESS(f"✓ Found {len(indicators)} indicators"))
                    for indicator in indicators[:3]:  # Show first 3
                        self.stdout.write(f"  - {indicator.get('name', 'Unknown')} ({indicator.get('id', 'No ID')})")
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"✗ Indicators fetching failed: {str(e)}"))
            
            # Test data elements fetching
            if options['test_data_elements']:
                self.stdout.write("Testing data elements fetching...")
                try:
                    data_elements = client.get_data_elements(limit=5)
                    self.stdout.write(self.style.SUCCESS(f"✓ Found {len(data_elements)} data elements"))
                    for element in data_elements[:3]:  # Show first 3
                        self.stdout.write(f"  - {element.get('name', 'Unknown')} ({element.get('id', 'No ID')})")
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"✗ Data elements fetching failed: {str(e)}"))
            
            # Test analytics data fetching
            if options['test_analytics']:
                self.stdout.write("Testing analytics data fetching...")
                
                # Get some test indicators
                try:
                    indicators = client.get_indicators(limit=2)
                    if not indicators:
                        self.stdout.write(self.style.WARNING("No indicators found for analytics test"))
                        return
                    
                    test_indicator = indicators[0]
                    indicator_uid = test_indicator['id']
                    
                    self.stdout.write(f"Testing analytics with indicator: {test_indicator.get('name', 'Unknown')} ({indicator_uid})")
                    
                    # Test analytics with indicators
                    analytics_response = client.get_analytics_data(
                        indicators=[indicator_uid],
                        periods=[options['period']],
                        org_units=[options['org_unit_id']] if options['org_unit_id'] else None
                    )
                    
                    if analytics_response and 'rows' in analytics_response:
                        self.stdout.write(self.style.SUCCESS(f"✓ Analytics request successful"))
                        self.stdout.write(f"  - Response has {len(analytics_response['rows'])} rows")
                        self.stdout.write(f"  - Headers: {analytics_response.get('headers', [])}")
                        
                        # Show first row if available
                        if analytics_response['rows']:
                            first_row = analytics_response['rows'][0]
                            self.stdout.write(f"  - First row: {first_row}")
                    else:
                        self.stdout.write(self.style.WARNING("Analytics response has no data rows"))
                        
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"✗ Analytics fetching failed: {str(e)}"))
            
            # Test enhanced search functionality
            self.stdout.write("Testing enhanced search functionality...")
            try:
                # Search for immunization-related indicators
                search_results = client.search_indicators("immunization", limit=3)
                self.stdout.write(self.style.SUCCESS(f"✓ Search found {len(search_results)} indicators"))
                
                # Search for immunization-related data elements
                search_results = client.search_data_elements("immunization", limit=3)
                self.stdout.write(self.style.SUCCESS(f"✓ Search found {len(search_results)} data elements"))
                
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"✗ Search functionality failed: {str(e)}"))
            
            # Test data set metadata
            self.stdout.write("Testing data set metadata...")
            try:
                metadata = client.get_data_set_metadata()
                self.stdout.write(self.style.SUCCESS("✓ Data set metadata fetched successfully"))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"✗ Data set metadata failed: {str(e)}"))
            
            self.stdout.write(self.style.SUCCESS("DHIS2 testing completed successfully!"))
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error during testing: {str(e)}"))
            logger.error(f"Error during DHIS2 testing: {str(e)}") 