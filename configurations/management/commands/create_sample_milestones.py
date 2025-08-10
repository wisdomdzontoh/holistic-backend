from django.core.management.base import BaseCommand
from configurations.models import Milestone


class Command(BaseCommand):
    help = 'Create sample milestones for testing'

    def handle(self, *args, **options):
        milestones_data = [
            {
                'name': 'MS 1.1',
                'code': 'MS1.1',
                'description': 'Milestone for Objective 1 - Health Service Delivery',
                'score': -2,
                'order': 1,
                'color': '#ffc107'
            },
            {
                'name': 'MS 2.1',
                'code': 'MS2.1',
                'description': 'Milestone for Objective 2 - Quality of Care',
                'score': -2,
                'order': 2,
                'color': '#ffc107'
            },
            {
                'name': 'MS 3.1',
                'code': 'MS3.1',
                'description': 'Milestone for Objective 3 - Health System Strengthening',
                'score': -2,
                'order': 3,
                'color': '#ffc107'
            },
            {
                'name': 'MS 4.1',
                'code': 'MS4.1',
                'description': 'Milestone for Objective 4 - Community Health',
                'score': -2,
                'order': 4,
                'color': '#ffc107'
            },
            {
                'name': 'MS 5.1',
                'code': 'MS5.1',
                'description': 'Milestone for Objective 5 - Health Information Systems',
                'score': -2,
                'order': 5,
                'color': '#ffc107'
            }
        ]

        created_count = 0
        for milestone_data in milestones_data:
            milestone, created = Milestone.objects.get_or_create(
                code=milestone_data['code'],
                defaults=milestone_data
            )
            if created:
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f'Created milestone: {milestone.name}')
                )
            else:
                self.stdout.write(
                    self.style.WARNING(f'Milestone already exists: {milestone.name}')
                )

        self.stdout.write(
            self.style.SUCCESS(f'Successfully created {created_count} new milestones')
        )
