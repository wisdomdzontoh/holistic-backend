from django.core.management.base import BaseCommand
from django.utils import timezone
from dhis2_auth.dhis_client import DHIS2Client
import csv
import os
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Discover indicators and data elements from DHIS2 instance and export to CSV'

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
            '--output-file',
            type=str,
            default='dhis2_discovered_indicators.csv',
            help='Output CSV file name'
        )
        parser.add_argument(
            '--search-query',
            type=str,
            help='Search query to filter indicators and data elements'
        )
        parser.add_argument(
            '--indicator-type',
            type=str,
            choices=['indicator', 'dataElement', 'both'],
            default='both',
            help='Type of items to discover'
        )
        parser.add_argument(
            '--limit',
            type=int,
            default=100,
            help='Maximum number of items to discover'
        )
        parser.add_argument(
            '--include-groups',
            action='store_true',
            help='Include indicator and data element groups'
        )
        parser.add_argument(
            '--debug',
            action='store_true',
            help='Enable debug logging'
        )

    def handle(self, *args, **options):
        if options['debug']:
            logging.getLogger().setLevel(logging.DEBUG)
        
        self.stdout.write("Discovering DHIS2 indicators and data elements...")
        
        try:
            # Initialize DHIS2 client
            client = DHIS2Client(
                instance_url=options['dhis2_instance_url'],
                username=options['username'],
                password=options['password']
            )
            
            # Test connection
            if not client.test_connection():
                self.stdout.write(self.style.ERROR("Failed to connect to DHIS2 instance"))
                return
            
            # Test authentication
            try:
                user_info = client.authenticate_user()
                self.stdout.write(f"Connected as: {user_info.get('name', 'Unknown')}")
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Authentication failed: {str(e)}"))
                return
            
            discovered_items = []
            
            # Discover indicators
            if options['indicator_type'] in ['indicator', 'both']:
                self.stdout.write("Discovering indicators...")
                try:
                    indicators = self._discover_indicators(client, options)
                    discovered_items.extend(indicators)
                    self.stdout.write(f"Found {len(indicators)} indicators")
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"Error discovering indicators: {str(e)}"))
            
            # Discover data elements
            if options['indicator_type'] in ['dataElement', 'both']:
                self.stdout.write("Discovering data elements...")
                try:
                    data_elements = self._discover_data_elements(client, options)
                    discovered_items.extend(data_elements)
                    self.stdout.write(f"Found {len(data_elements)} data elements")
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"Error discovering data elements: {str(e)}"))
            
            # Export to CSV
            if discovered_items:
                self._export_to_csv(discovered_items, options['output_file'])
                self.stdout.write(
                    self.style.SUCCESS(
                        f"Successfully exported {len(discovered_items)} items to {options['output_file']}"
                    )
                )
            else:
                self.stdout.write(self.style.WARNING("No items discovered"))
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error during discovery: {str(e)}"))
            logger.error(f"Error during DHIS2 discovery: {str(e)}")

    def _discover_indicators(self, client, options):
        """Discover indicators from DHIS2"""
        indicators = []
        
        try:
            # Get indicators with enhanced filtering
            if options['search_query']:
                # Use search functionality
                indicators_data = client.search_indicators(
                    query=options['search_query'],
                    limit=options['limit'],
                    search_fields=['name', 'description', 'code']
                )
            else:
                # Get all indicators with filtering
                indicators_data = client.get_indicators(
                    limit=options['limit'],
                    filter_query=options['search_query']
                )
            
            for indicator in indicators_data:
                item = {
                    'uid': indicator.get('id', ''),
                    'name': indicator.get('name', ''),
                    'description': indicator.get('description', ''),
                    'short_name': indicator.get('shortName', ''),
                    'display_name': indicator.get('displayName', ''),
                    'code': indicator.get('code', ''),
                    'indicator_type': 'indicator',
                    'dhis2_type': indicator.get('indicatorType', ''),
                    'numerator': indicator.get('numerator', ''),
                    'denominator': indicator.get('denominator', ''),
                    'numerator_description': indicator.get('numeratorDescription', ''),
                    'denominator_description': indicator.get('denominatorDescription', ''),
                    'annualized': indicator.get('annualized', False),
                    'groups': self._extract_groups(indicator.get('indicatorGroups', [])),
                    'discovered_at': timezone.now().isoformat()
                }
                indicators.append(item)
                
        except Exception as e:
            logger.error(f"Error discovering indicators: {str(e)}")
            raise
        
        return indicators

    def _discover_data_elements(self, client, options):
        """Discover data elements from DHIS2"""
        data_elements = []
        
        try:
            # Get data elements with enhanced filtering
            if options['search_query']:
                # Use search functionality
                elements_data = client.search_data_elements(
                    query=options['search_query'],
                    limit=options['limit'],
                    search_fields=['name', 'description', 'code']
                )
            else:
                # Get all data elements with filtering
                elements_data = client.get_data_elements(
                    limit=options['limit'],
                    filter_query=options['search_query']
                )
            
            for element in elements_data:
                item = {
                    'uid': element.get('id', ''),
                    'name': element.get('name', ''),
                    'description': element.get('description', ''),
                    'short_name': element.get('shortName', ''),
                    'display_name': element.get('displayName', ''),
                    'code': element.get('code', ''),
                    'indicator_type': 'dataElement',
                    'value_type': element.get('valueType', ''),
                    'aggregation_type': element.get('aggregationType', ''),
                    'domain_type': element.get('domainType', ''),
                    'groups': self._extract_groups(element.get('dataElementGroups', [])),
                    'category_combo': element.get('categoryCombo', {}).get('name', ''),
                    'discovered_at': timezone.now().isoformat()
                }
                data_elements.append(item)
                
        except Exception as e:
            logger.error(f"Error discovering data elements: {str(e)}")
            raise
        
        return data_elements

    def _extract_groups(self, groups_data):
        """Extract group names from groups data"""
        if not groups_data:
            return ''
        
        try:
            if isinstance(groups_data, list):
                group_names = [group.get('name', '') for group in groups_data if group.get('name')]
            else:
                group_names = [groups_data.get('name', '')]
            
            return '; '.join(group_names)
        except Exception:
            return ''

    def _export_to_csv(self, items, output_file):
        """Export discovered items to CSV"""
        try:
            if not items:
                return
            
            # Get all unique field names
            fieldnames = set()
            for item in items:
                fieldnames.update(item.keys())
            
            fieldnames = sorted(list(fieldnames))
            
            with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(items)
                
        except Exception as e:
            logger.error(f"Error exporting to CSV: {str(e)}")
            raise 