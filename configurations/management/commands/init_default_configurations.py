from django.core.management.base import BaseCommand
from configurations.models import Objective, Milestone, ScoringRule, AssessmentPeriod
from indicators.models import TrackedIndicator
from decimal import Decimal
from django.utils import timezone
from datetime import date

class Command(BaseCommand):
    help = 'Initialize default configurations for the holistic assessment system'

    def handle(self, *args, **options):
        self.stdout.write('Initializing default configurations...')
        
        # Create milestones
        milestone1, created = Milestone.objects.get_or_create(
            code='MS1.1',
            defaults={
                'name': 'MS 1.1',
                'description': 'Universal access to better & efficiently managed quality healthcare services',
                'order': 1,
                'color': '#ffc107'
            }
        )
        
        # Create objectives
        objective1, created = Objective.objects.get_or_create(
            code='OBJ1',
            defaults={
                'name': 'Objective 1',
                'description': 'Universal access to better & efficiently managed quality healthcare services',
                'order': 1,
                'color': '#fd7e14',
                'milestone': milestone1
            }
        )
        
        objective2, created = Objective.objects.get_or_create(
            code='OBJ2',
            defaults={
                'name': 'Objective 2',
                'description': 'Reduce avoidable maternal, adolescent & child deaths and disabilities',
                'order': 2,
                'color': '#fd7e14',
                'milestone': milestone1
            }
        )
        
        # Create sample indicators (these are example DHIS2 UIDs - replace with actual ones)
        indicators_data = [
            {
                'name': 'Family Planning Acceptor rate',
                'dhis2_uid': 'FTRrcoaog83',  # Example UID - replace with actual
                'indicator_number': '1.1',
                'display_order': 1,
                'target_value': Decimal('40'),
                'target_type': 'increase',
                'objective': objective1
            },
            {
                'name': 'Long Term couple year protection',
                'dhis2_uid': 'FTRrcoaog84',  # Example UID - replace with actual
                'indicator_number': '1.2',
                'display_order': 2,
                'target_value': Decimal('350000'),
                'target_type': 'increase',
                'objective': objective1
            },
            {
                'name': 'Percentage skilled deliveries',
                'dhis2_uid': 'FTRrcoaog85',  # Example UID - replace with actual
                'indicator_number': '1.3',
                'display_order': 3,
                'target_value': Decimal('65'),
                'target_type': 'increase',
                'objective': objective1
            },
            {
                'name': 'Proportion of facility deaths that are medically certified',
                'dhis2_uid': 'FTRrcoaog86',  # Example UID - replace with actual
                'indicator_number': '2.1',
                'display_order': 4,
                'target_value': Decimal('90'),
                'target_type': 'increase',
                'objective': objective2
            },
            {
                'name': 'Incidence rate of diabetes (using OPD as proxy)',
                'dhis2_uid': 'FTRrcoaog87',  # Example UID - replace with actual
                'indicator_number': '2.2',
                'display_order': 5,
                'target_value': Decimal('5'),
                'target_type': 'decrease',
                'objective': objective2
            }
        ]
        
        for indicator_data in indicators_data:
            indicator, created = TrackedIndicator.objects.get_or_create(
                dhis2_uid=indicator_data['dhis2_uid'],
                defaults={
                    'name': indicator_data['name'],
                    'indicator_number': indicator_data['indicator_number'],
                    'display_order': indicator_data['display_order'],
                    'target_value': indicator_data['target_value'],
                    'target_type': indicator_data['target_type'],
                    'is_active': True,
                    'description': f'Sample indicator: {indicator_data["name"]}'
                }
            )
            
            # Create objective weight mapping
            from configurations.models import IndicatorWeight
            weight, created = IndicatorWeight.objects.get_or_create(
                objective=indicator_data['objective'],
                indicator=indicator,
                defaults={'weight': Decimal('1.0')}
            )
        
        # Create scoring rules
        scoring_rules = [
            {
                'name': 'Excellent Performance',
                'performance_type': 'gap',
                'min_value': Decimal('-10'),
                'max_value': Decimal('10'),
                'score': 2,
                'color': '#28a745',
                'label': 'Excellent',
                'priority': 1
            },
            {
                'name': 'Good Performance',
                'performance_type': 'gap',
                'min_value': Decimal('-20'),
                'max_value': Decimal('-10'),
                'score': 1,
                'color': '#20c997',
                'label': 'Good',
                'priority': 2
            },
            {
                'name': 'Sustained Performance',
                'performance_type': 'gap',
                'min_value': Decimal('-30'),
                'max_value': Decimal('-20'),
                'score': 0,
                'color': '#ffc107',
                'label': 'Sustained',
                'priority': 3
            },
            {
                'name': 'Underperforming',
                'performance_type': 'gap',
                'min_value': Decimal('-50'),
                'max_value': Decimal('-30'),
                'score': -1,
                'color': '#fd7e14',
                'label': 'Underperforming',
                'priority': 4
            },
            {
                'name': 'Severely Underperforming',
                'performance_type': 'gap',
                'min_value': Decimal('-100'),
                'max_value': Decimal('-50'),
                'score': -2,
                'color': '#dc3545',
                'label': 'Severely Underperforming',
                'priority': 5
            }
        ]
        
        for rule_data in scoring_rules:
            rule, created = ScoringRule.objects.get_or_create(
                name=rule_data['name'],
                defaults=rule_data
            )
        
        # Create sample assessment periods
        periods = [
            {
                'name': '2023 Q2',
                'period_type': 'quarterly',
                'start_date': date(2023, 4, 1),
                'end_date': date(2023, 6, 30),
                'is_active': True,
                'is_current': False
            },
            {
                'name': '2024 Q2',
                'period_type': 'quarterly',
                'start_date': date(2024, 4, 1),
                'end_date': date(2024, 6, 30),
                'is_active': True,
                'is_current': True
            },
            {
                'name': '2025 Q2',
                'period_type': 'quarterly',
                'start_date': date(2025, 4, 1),
                'end_date': date(2025, 6, 30),
                'is_active': True,
                'is_current': False
            }
        ]
        
        for period_data in periods:
            period, created = AssessmentPeriod.objects.get_or_create(
                name=period_data['name'],
                defaults=period_data
            )
        
        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully initialized default configurations:\n'
                f'- {Milestone.objects.count()} milestones\n'
                f'- {Objective.objects.count()} objectives\n'
                f'- {TrackedIndicator.objects.count()} indicators\n'
                f'- {ScoringRule.objects.count()} scoring rules\n'
                f'- {AssessmentPeriod.objects.count()} assessment periods'
            )
        ) 