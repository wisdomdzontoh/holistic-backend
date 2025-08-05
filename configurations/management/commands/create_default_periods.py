from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import datetime, timedelta
from configurations.models import AssessmentPeriod


class Command(BaseCommand):
    help = 'Create default assessment periods for testing'

    def handle(self, *args, **options):
        # Create some default assessment periods
        periods_data = [
            {
                'name': '2024 Q1',
                'period_type': 'quarterly',
                'start_date': datetime(2024, 1, 1),
                'end_date': datetime(2024, 3, 31),
                'is_active': True,
                'is_current': False,
            },
            {
                'name': '2024 Q2',
                'period_type': 'quarterly',
                'start_date': datetime(2024, 4, 1),
                'end_date': datetime(2024, 6, 30),
                'is_active': True,
                'is_current': False,
            },
            {
                'name': '2024 Q3',
                'period_type': 'quarterly',
                'start_date': datetime(2024, 7, 1),
                'end_date': datetime(2024, 9, 30),
                'is_active': True,
                'is_current': False,
            },
            {
                'name': '2024 Q4',
                'period_type': 'quarterly',
                'start_date': datetime(2024, 10, 1),
                'end_date': datetime(2024, 12, 31),
                'is_active': True,
                'is_current': True,
            },
            {
                'name': '2025 Q1',
                'period_type': 'quarterly',
                'start_date': datetime(2025, 1, 1),
                'end_date': datetime(2025, 3, 31),
                'is_active': True,
                'is_current': False,
            },
        ]

        created_count = 0
        for period_data in periods_data:
            period, created = AssessmentPeriod.objects.get_or_create(
                name=period_data['name'],
                defaults=period_data
            )
            if created:
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f'Created assessment period: {period.name}')
                )
            else:
                self.stdout.write(
                    self.style.WARNING(f'Assessment period already exists: {period.name}')
                )

        self.stdout.write(
            self.style.SUCCESS(f'Successfully created {created_count} assessment periods')
        ) 