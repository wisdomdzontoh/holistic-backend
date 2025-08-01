from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from exports.services import ExportService
from exports.models import ExportJob


class Command(BaseCommand):
    help = 'Process pending export jobs'

    def add_arguments(self, parser):
        parser.add_argument(
            '--job-id',
            type=str,
            help='Process specific job by ID'
        )
        parser.add_argument(
            '--limit',
            type=int,
            default=10,
            help='Maximum number of jobs to process (default: 10)'
        )
        parser.add_argument(
            '--priority',
            type=str,
            choices=['low', 'normal', 'high', 'urgent'],
            help='Process jobs with specific priority'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be processed without actually doing it'
        )

    def handle(self, *args, **options):
        if options['dry_run']:
            self.stdout.write('DRY RUN MODE - No jobs will be processed')
        
        # Get jobs to process
        if options['job_id']:
            jobs = ExportJob.objects.filter(
                job_id=options['job_id'],
                status=ExportJob.ExportStatus.PENDING
            )
        else:
            jobs = ExportJob.objects.filter(
                status=ExportJob.ExportStatus.PENDING
            ).order_by('-priority', 'created_at')
            
            if options['priority']:
                jobs = jobs.filter(priority=options['priority'])
            
            jobs = jobs[:options['limit']]
        
        if not jobs.exists():
            self.stdout.write('No pending jobs found to process')
            return
        
        self.stdout.write(f"Found {jobs.count()} jobs to process")
        
        if options['dry_run']:
            for job in jobs:
                self.stdout.write(f"  Would process: {job.job_id} - {job.name}")
            return
        
        # Process jobs
        export_service = ExportService()
        processed_count = 0
        failed_count = 0
        
        for job in jobs:
            try:
                self.stdout.write(f"Processing job {job.job_id}: {job.name}")
                export_service.process_export_job(job)
                processed_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f"Successfully processed job {job.job_id}")
                )
                
            except Exception as e:
                failed_count += 1
                self.stdout.write(
                    self.style.ERROR(f"Failed to process job {job.job_id}: {str(e)}")
                )
        
        # Summary
        self.stdout.write('\n' + '='*50)
        self.stdout.write('PROCESSING SUMMARY')
        self.stdout.write('='*50)
        self.stdout.write(f"Total jobs: {jobs.count()}")
        self.stdout.write(f"Successfully processed: {processed_count}")
        self.stdout.write(f"Failed: {failed_count}")
        
        if failed_count == 0:
            self.stdout.write(
                self.style.SUCCESS('\nAll jobs processed successfully!')
            )
        else:
            self.stdout.write(
                self.style.WARNING(f'\n{failed_count} jobs failed to process.')
            ) 