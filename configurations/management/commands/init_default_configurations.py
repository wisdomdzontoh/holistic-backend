from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import date, timedelta
from configurations.models import (
    Objective, ScoringRule, WeightingScheme, AssessmentPeriod, SystemConfiguration
)


class Command(BaseCommand):
    help = 'Initialize default configurations for the holistic assessment system'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force recreation of existing configurations'
        )
        parser.add_argument(
            '--skip-objectives',
            action='store_true',
            help='Skip creating default objectives'
        )
        parser.add_argument(
            '--skip-scoring-rules',
            action='store_true',
            help='Skip creating default scoring rules'
        )
        parser.add_argument(
            '--skip-weighting-schemes',
            action='store_true',
            help='Skip creating default weighting schemes'
        )
        parser.add_argument(
            '--skip-assessment-periods',
            action='store_true',
            help='Skip creating default assessment periods'
        )

    def handle(self, *args, **options):
        force = options['force']
        skip_objectives = options['skip_objectives']
        skip_scoring_rules = options['skip_scoring_rules']
        skip_weighting_schemes = options['skip_weighting_schemes']
        skip_assessment_periods = options['skip_assessment_periods']
        
        self.stdout.write('Initializing default configurations...')
        
        if not skip_objectives:
            self.create_default_objectives(force)
        
        if not skip_scoring_rules:
            self.create_default_scoring_rules(force)
        
        if not skip_weighting_schemes:
            self.create_default_weighting_schemes(force)
        
        if not skip_assessment_periods:
            self.create_default_assessment_periods(force)
        
        self.create_default_system_configurations(force)
        
        self.stdout.write(
            self.style.SUCCESS('Default configurations initialized successfully!')
        )
    
    def create_default_objectives(self, force=False):
        """Create default objectives"""
        self.stdout.write('Creating default objectives...')
        
        default_objectives = [
            {
                'name': 'Objective 1: Service Delivery',
                'code': 'OBJ1',
                'description': 'Improve service delivery and patient care quality',
                'order': 1,
                'color': '#007bff'
            },
            {
                'name': 'Objective 2: Health Outcomes',
                'code': 'OBJ2',
                'description': 'Enhance health outcomes and population health',
                'order': 2,
                'color': '#28a745'
            },
            {
                'name': 'Objective 3: Health Systems Strengthening',
                'code': 'OBJ3',
                'description': 'Strengthen health systems and infrastructure',
                'order': 3,
                'color': '#ffc107'
            },
            {
                'name': 'Objective 4: Governance and Leadership',
                'code': 'OBJ4',
                'description': 'Improve governance, leadership, and accountability',
                'order': 4,
                'color': '#dc3545'
            },
            {
                'name': 'Objective 5: Innovation and Research',
                'code': 'OBJ5',
                'description': 'Promote innovation, research, and evidence-based practice',
                'order': 5,
                'color': '#6f42c1'
            }
        ]
        
        created_count = 0
        for obj_data in default_objectives:
            objective, created = Objective.objects.get_or_create(
                code=obj_data['code'],
                defaults=obj_data
            )
            if created or force:
                if force and not created:
                    for key, value in obj_data.items():
                        setattr(objective, key, value)
                    objective.save()
                created_count += 1
                self.stdout.write(f'  ✓ Created/Updated: {objective.name}')
        
        self.stdout.write(f'  Created/Updated {created_count} objectives')
    
    def create_default_scoring_rules(self, force=False):
        """Create default scoring rules"""
        self.stdout.write('Creating default scoring rules...')
        
        # Target Gap scoring rules
        gap_rules = [
            {'name': 'Excellent Performance', 'min_value': 0, 'max_value': 5, 'score': 2, 'color': '#28a745', 'label': 'Excellent'},
            {'name': 'Good Performance', 'min_value': 5, 'max_value': 15, 'score': 1, 'color': '#17a2b8', 'label': 'Good'},
            {'name': 'Sustained Performance', 'min_value': 15, 'max_value': 25, 'score': 0, 'color': '#ffc107', 'label': 'Sustained'},
            {'name': 'Underperforming', 'min_value': 25, 'max_value': 40, 'score': -1, 'color': '#fd7e14', 'label': 'Underperforming'},
            {'name': 'Severely Underperforming', 'min_value': 40, 'max_value': None, 'score': -2, 'color': '#dc3545', 'label': 'Poor'},
        ]
        
        # Percent Change scoring rules
        change_rules = [
            {'name': 'Significant Improvement', 'min_value': 10, 'max_value': None, 'score': 2, 'color': '#28a745', 'label': 'Excellent'},
            {'name': 'Moderate Improvement', 'min_value': 5, 'max_value': 10, 'score': 1, 'color': '#17a2b8', 'label': 'Good'},
            {'name': 'Stable Performance', 'min_value': -5, 'max_value': 5, 'score': 0, 'color': '#ffc107', 'label': 'Sustained'},
            {'name': 'Moderate Decline', 'min_value': -10, 'max_value': -5, 'score': -1, 'color': '#fd7e14', 'label': 'Underperforming'},
            {'name': 'Significant Decline', 'min_value': None, 'max_value': -10, 'score': -2, 'color': '#dc3545', 'label': 'Poor'},
        ]
        
        created_count = 0
        
        # Create gap rules
        for i, rule_data in enumerate(gap_rules):
            rule_data['performance_type'] = 'gap'
            rule_data['priority'] = i
            rule, created = ScoringRule.objects.get_or_create(
                name=rule_data['name'],
                performance_type='gap',
                defaults=rule_data
            )
            if created or force:
                if force and not created:
                    for key, value in rule_data.items():
                        setattr(rule, key, value)
                    rule.save()
                created_count += 1
                self.stdout.write(f'  ✓ Created/Updated: {rule.name} (Gap)')
        
        # Create change rules
        for i, rule_data in enumerate(change_rules):
            rule_data['performance_type'] = 'change'
            rule_data['priority'] = i
            rule, created = ScoringRule.objects.get_or_create(
                name=rule_data['name'],
                performance_type='change',
                defaults=rule_data
            )
            if created or force:
                if force and not created:
                    for key, value in rule_data.items():
                        setattr(rule, key, value)
                    rule.save()
                created_count += 1
                self.stdout.write(f'  ✓ Created/Updated: {rule.name} (Change)')
        
        self.stdout.write(f'  Created/Updated {created_count} scoring rules')
    
    def create_default_weighting_schemes(self, force=False):
        """Create default weighting schemes"""
        self.stdout.write('Creating default weighting schemes...')
        
        default_schemes = [
            {
                'name': 'Balanced Weighting',
                'description': 'Equal weighting for all objectives',
                'is_default': True
            },
            {
                'name': 'Service Delivery Focus',
                'description': 'Emphasis on service delivery and patient care',
                'is_default': False
            },
            {
                'name': 'Outcomes Focus',
                'description': 'Emphasis on health outcomes and population health',
                'is_default': False
            }
        ]
        
        created_count = 0
        for scheme_data in default_schemes:
            scheme, created = WeightingScheme.objects.get_or_create(
                name=scheme_data['name'],
                defaults=scheme_data
            )
            if created or force:
                if force and not created:
                    for key, value in scheme_data.items():
                        setattr(scheme, key, value)
                    scheme.save()
                created_count += 1
                self.stdout.write(f'  ✓ Created/Updated: {scheme.name}')
        
        self.stdout.write(f'  Created/Updated {created_count} weighting schemes')
    
    def create_default_assessment_periods(self, force=False):
        """Create default assessment periods"""
        self.stdout.write('Creating default assessment periods...')
        
        # Create quarterly periods for current year
        current_year = timezone.now().year
        quarters = [
            ('Q1', date(current_year, 1, 1), date(current_year, 3, 31)),
            ('Q2', date(current_year, 4, 1), date(current_year, 6, 30)),
            ('Q3', date(current_year, 7, 1), date(current_year, 9, 30)),
            ('Q4', date(current_year, 10, 1), date(current_year, 12, 31)),
        ]
        
        created_count = 0
        for quarter_name, start_date, end_date in quarters:
            period_name = f'{quarter_name} {current_year}'
            period, created = AssessmentPeriod.objects.get_or_create(
                name=period_name,
                defaults={
                    'period_type': 'quarterly',
                    'start_date': start_date,
                    'end_date': end_date,
                    'is_current': quarter_name == 'Q4'  # Set Q4 as current
                }
            )
            if created or force:
                if force and not created:
                    period.period_type = 'quarterly'
                    period.start_date = start_date
                    period.end_date = end_date
                    period.is_current = quarter_name == 'Q4'
                    period.save()
                created_count += 1
                self.stdout.write(f'  ✓ Created/Updated: {period.name}')
        
        self.stdout.write(f'  Created/Updated {created_count} assessment periods')
    
    def create_default_system_configurations(self, force=False):
        """Create default system configurations"""
        self.stdout.write('Creating default system configurations...')
        
        default_configs = [
            {
                'key': 'scoring_defaults',
                'config_type': 'scoring',
                'value': '{"default_performance_type": "gap", "score_range": [-2, 2], "color_scheme": "traffic_light"}',
                'description': 'Default scoring configuration'
            },
            {
                'key': 'display_settings',
                'config_type': 'display',
                'value': '{"dashboard_refresh_interval": 300, "chart_colors": ["#007bff", "#28a745", "#ffc107", "#dc3545"], "show_percentages": true}',
                'description': 'Display settings for dashboards and charts'
            },
            {
                'key': 'export_settings',
                'config_type': 'export',
                'value': '{"excel_template": "default", "pdf_template": "default", "include_charts": true, "include_metadata": true}',
                'description': 'Export configuration settings'
            },
            {
                'key': 'notification_settings',
                'config_type': 'notification',
                'value': '{"email_notifications": false, "dashboard_alerts": true, "score_threshold_alerts": [-1, -2]}',
                'description': 'Notification and alert settings'
            }
        ]
        
        created_count = 0
        for config_data in default_configs:
            config, created = SystemConfiguration.objects.get_or_create(
                key=config_data['key'],
                defaults=config_data
            )
            if created or force:
                if force and not created:
                    for key, value in config_data.items():
                        setattr(config, key, value)
                    config.save()
                created_count += 1
                self.stdout.write(f'  ✓ Created/Updated: {config.key}')
        
        self.stdout.write(f'  Created/Updated {created_count} system configurations') 