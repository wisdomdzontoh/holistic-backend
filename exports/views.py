from django.shortcuts import render
from django.db.models import Q, Avg, Sum

# Create your views here.
from rest_framework import status, viewsets, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from django.db import transaction
from django.utils import timezone

from .models import (
    ExportTemplate, ExportJob, ExportSchedule, ExportLog, ExportConfiguration
)
from .serializers import (
    ExportTemplateSerializer, ExportJobSerializer, ExportScheduleSerializer,
    ExportLogSerializer, ExportConfigurationSerializer, ExportRequestSerializer,
    ExportStatusSerializer, ExportDownloadSerializer, BulkExportRequestSerializer,
    ExportTemplateCloneSerializer, ScheduleExecutionSerializer,
    ScheduleStatusUpdateSerializer, ConfigurationUpdateSerializer,
    ExportAnalyticsSerializer, ExportPerformanceSerializer,
    TemplateValidationSerializer, TemplateValidationResultSerializer
)
from .services import ExportService
from organisation.services import AccessControlService
from dhis2_auth.session import get_dhis2_user


class ExportTemplateViewSet(viewsets.ModelViewSet):
    """
    ViewSet for export templates
    """
    queryset = ExportTemplate.objects.all()
    serializer_class = ExportTemplateSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['export_format', 'export_type', 'is_active', 'is_system_template', 'is_public']
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'created_at', 'updated_at']
    ordering = ['name']
    
    def get_queryset(self):
        """Filter templates based on user access"""
        queryset = super().get_queryset()
        
        # Show system templates and public templates
        queryset = queryset.filter(
            Q(is_system_template=True) | Q(is_public=True)
        )
        
        # Also show user's own templates. Filter by created_by_id (a plain PK
        # comparison) rather than created_by=self.request.user - under this app's
        # custom DHIS2SessionAuthentication, request.user is a DHIS2UserWrapper,
        # not a real DHIS2User model instance, so the ORM can't resolve it for a
        # direct FK comparison (raises TypeError: Field 'id' expected a number).
        if hasattr(self.request.user, 'dhis2_username'):
            queryset = queryset | ExportTemplate.objects.filter(
                created_by_id=self.request.user.id
            )
        
        return queryset.distinct()
    
    @action(detail=True, methods=['post'])
    def clone(self, request, pk=None):
        """Clone an export template"""
        template = self.get_object()
        serializer = ExportTemplateCloneSerializer(data=request.data)
        
        if serializer.is_valid():
            try:
                with transaction.atomic():
                    # Create new template
                    new_template = ExportTemplate.objects.create(
                        name=serializer.validated_data['new_name'],
                        description=serializer.validated_data.get('new_description', template.description),
                        export_format=template.export_format,
                        export_type=template.export_type,
                        template_config=template.template_config,
                        is_active=template.is_active,
                        is_system_template=False,
                        is_public=serializer.validated_data.get('is_public', True),
                        created_by_id=request.user.id
                    )
                    
                    return Response({
                        'message': 'Template cloned successfully',
                        'template_id': new_template.id
                    }, status=status.HTTP_201_CREATED)
                    
            except Exception as e:
                return Response({
                    'error': f'Failed to clone template: {str(e)}'
                }, status=status.HTTP_400_BAD_REQUEST)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'])
    def validate(self, request, pk=None):
        """Validate template configuration"""
        template = self.get_object()
        serializer = TemplateValidationSerializer(data=request.data)
        
        if serializer.is_valid():
            # Perform validation (placeholder implementation)
            validation_result = {
                'is_valid': True,
                'errors': [],
                'warnings': [],
                'suggestions': [],
                'estimated_file_size': None,
                'estimated_processing_time': None
            }
            
            result_serializer = TemplateValidationResultSerializer(validation_result)
            return Response(result_serializer.data)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ExportJobViewSet(viewsets.ModelViewSet):
    """
    ViewSet for export jobs
    """
    queryset = ExportJob.objects.all()
    serializer_class = ExportJobSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status', 'priority', 'export_format', 'export_type', 'is_archived']
    search_fields = ['name', 'description', 'job_id']
    ordering_fields = ['created_at', 'started_at', 'completed_at', 'priority']
    ordering = ['-created_at']
    
    def get_queryset(self):
        """Filter jobs based on user access"""
        queryset = super().get_queryset()
        
        # Show user's own jobs. See ExportTemplateViewSet.get_queryset for why
        # this uses created_by_id rather than created_by=self.request.user.
        if hasattr(self.request.user, 'dhis2_username'):
            queryset = queryset.filter(created_by_id=self.request.user.id)

        return queryset
    
    @action(detail=False, methods=['post'])
    def create_export(self, request):
        """Create a new export job"""
        serializer = ExportRequestSerializer(data=request.data)
        
        if serializer.is_valid():
            try:
                export_service = ExportService()
                export_job = export_service.create_export_job(
                    serializer.validated_data, request.user
                )
                
                # Process the job (this would typically be done asynchronously)
                # For now, we'll process it synchronously
                try:
                    export_service.process_export_job(export_job)
                except Exception as e:
                    return Response({
                        'error': f'Export processing failed: {str(e)}'
                    }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
                
                job_serializer = ExportJobSerializer(export_job)
                return Response(job_serializer.data, status=status.HTTP_201_CREATED)
                
            except Exception as e:
                return Response({
                    'error': f'Failed to create export job: {str(e)}'
                }, status=status.HTTP_400_BAD_REQUEST)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['post'])
    def bulk_export(self, request):
        """Create multiple export jobs"""
        serializer = BulkExportRequestSerializer(data=request.data)
        
        if serializer.is_valid():
            try:
                export_service = ExportService()
                created_jobs = []
                
                for export_request in serializer.validated_data['export_requests']:
                    export_job = export_service.create_export_job(
                        export_request, request.user
                    )
                    created_jobs.append(export_job)
                
                jobs_serializer = ExportJobSerializer(created_jobs, many=True)
                return Response({
                    'message': f'Created {len(created_jobs)} export jobs',
                    'jobs': jobs_serializer.data
                }, status=status.HTTP_201_CREATED)
                
            except Exception as e:
                return Response({
                    'error': f'Failed to create bulk export jobs: {str(e)}'
                }, status=status.HTTP_400_BAD_REQUEST)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['get'])
    def status(self, request, pk=None):
        """Get export job status"""
        job = self.get_object()
        
        status_data = {
            'job_id': job.job_id,
            'status': job.status,
            'status_display': job.get_status_display(),
            'progress_percentage': job.progress_percentage,
            'total_records': job.total_records,
            'processed_records': job.processed_records,
            'file_url': job.file_url,
            'error_message': job.error_message,
            'created_at': job.created_at,
            'started_at': job.started_at,
            'completed_at': job.completed_at,
            'duration_formatted': job.duration_formatted
        }
        
        serializer = ExportStatusSerializer(status_data)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def download(self, request, pk=None):
        """Get download information for completed export"""
        job = self.get_object()
        
        if job.status != ExportJob.ExportStatus.COMPLETED:
            return Response({
                'error': 'Export job is not completed'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        if not job.file_url:
            return Response({
                'error': 'No file available for download'
            }, status=status.HTTP_404_NOT_FOUND)
        
        download_data = {
            'job_id': job.job_id,
            'file_url': job.file_url,
            'file_size': job.file_size,
            'file_name': f"export_{job.job_id}.{job.export_format}",
            'expires_at': job.expires_at,
            'download_count': 0  # This would be tracked in a real implementation
        }
        
        serializer = ExportDownloadSerializer(download_data)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """Cancel an export job"""
        job = self.get_object()
        
        if job.status in [ExportJob.ExportStatus.COMPLETED, ExportJob.ExportStatus.FAILED, ExportJob.ExportStatus.CANCELLED]:
            return Response({
                'error': 'Cannot cancel a completed, failed, or cancelled job'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        job.status = ExportJob.ExportStatus.CANCELLED
        job.completed_at = timezone.now()
        job.save()
        
        # Log cancellation
        ExportLog.objects.create(
            export_job=job,
            level=ExportLog.LogLevel.INFO,
            message="Export job cancelled by user"
        )
        
        return Response({
            'message': 'Export job cancelled successfully'
        })
    
    @action(detail=False, methods=['get'])
    def analytics(self, request):
        """Get export analytics"""
        # Get user's jobs
        user_jobs = ExportJob.objects.filter(created_by_id=request.user.id)
        
        # Calculate analytics
        total_jobs = user_jobs.count()
        completed_jobs = user_jobs.filter(status=ExportJob.ExportStatus.COMPLETED).count()
        failed_jobs = user_jobs.filter(status=ExportJob.ExportStatus.FAILED).count()
        pending_jobs = user_jobs.filter(status__in=[
            ExportJob.ExportStatus.PENDING, ExportJob.ExportStatus.IN_PROGRESS
        ]).count()
        
        success_rate = (completed_jobs / total_jobs * 100) if total_jobs > 0 else 0
        average_duration = user_jobs.filter(
            duration_seconds__gt=0
        ).aggregate(avg=Avg('duration_seconds'))['avg'] or 0
        
        total_file_size = user_jobs.filter(
            file_size__gt=0
        ).aggregate(total=Sum('file_size'))['total'] or 0
        
        # Jobs by format
        jobs_by_format = {}
        for job in user_jobs:
            format_name = job.get_export_format_display()
            jobs_by_format[format_name] = jobs_by_format.get(format_name, 0) + 1
        
        # Jobs by type
        jobs_by_type = {}
        for job in user_jobs:
            type_name = job.get_export_type_display()
            jobs_by_type[type_name] = jobs_by_type.get(type_name, 0) + 1
        
        # Jobs by status
        jobs_by_status = {}
        for job in user_jobs:
            status_name = job.get_status_display()
            jobs_by_status[status_name] = jobs_by_status.get(status_name, 0) + 1
        
        # Recent jobs
        recent_jobs = user_jobs.order_by('-created_at')[:10]
        recent_jobs_data = []
        for job in recent_jobs:
            recent_jobs_data.append({
                'job_id': job.job_id,
                'name': job.name,
                'status': job.status,
                'created_at': job.created_at,
                'file_url': job.file_url
            })
        
        analytics_data = {
            'total_jobs': total_jobs,
            'completed_jobs': completed_jobs,
            'failed_jobs': failed_jobs,
            'pending_jobs': pending_jobs,
            'success_rate': round(success_rate, 2),
            'average_duration': round(average_duration, 2),
            'total_file_size': total_file_size,
            'jobs_by_format': jobs_by_format,
            'jobs_by_type': jobs_by_type,
            'jobs_by_status': jobs_by_status,
            'recent_jobs': recent_jobs_data
        }
        
        serializer = ExportAnalyticsSerializer(analytics_data)
        return Response(serializer.data)


class ExportScheduleViewSet(viewsets.ModelViewSet):
    """
    ViewSet for export schedules
    """
    queryset = ExportSchedule.objects.all()
    serializer_class = ExportScheduleSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['frequency', 'status']
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'created_at', 'next_run']
    ordering = ['name']
    
    def get_queryset(self):
        """Filter schedules based on user access"""
        queryset = super().get_queryset()
        
        # Show user's own schedules
        if hasattr(self.request.user, 'dhis2_username'):
            queryset = queryset.filter(created_by_id=self.request.user.id)

        return queryset
    
    @action(detail=True, methods=['post'])
    def execute(self, request, pk=None):
        """Manually execute a schedule"""
        schedule = self.get_object()
        serializer = ScheduleExecutionSerializer(data=request.data)
        
        if serializer.is_valid():
            try:
                # This would typically trigger the schedule execution
                # For now, just update the last run time
                schedule.last_run = timezone.now()
                schedule.total_runs += 1
                schedule.save()
                
                return Response({
                    'message': 'Schedule executed successfully'
                })
                
            except Exception as e:
                return Response({
                    'error': f'Failed to execute schedule: {str(e)}'
                }, status=status.HTTP_400_BAD_REQUEST)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['post'])
    def update_status(self, request):
        """Update status of multiple schedules"""
        serializer = ScheduleStatusUpdateSerializer(data=request.data)
        
        if serializer.is_valid():
            try:
                schedule_ids = serializer.validated_data['schedule_ids']
                new_status = serializer.validated_data['new_status']
                
                schedules = ExportSchedule.objects.filter(
                    id__in=schedule_ids,
                    created_by_id=request.user.id
                )
                
                schedules.update(status=new_status)
                
                return Response({
                    'message': f'Updated {schedules.count()} schedules'
                })
                
            except Exception as e:
                return Response({
                    'error': f'Failed to update schedules: {str(e)}'
                }, status=status.HTTP_400_BAD_REQUEST)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ExportLogViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for export logs (read-only)
    """
    queryset = ExportLog.objects.all()
    serializer_class = ExportLogSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['level', 'export_job']
    search_fields = ['message']
    ordering_fields = ['timestamp', 'level']
    ordering = ['-timestamp']
    
    def get_queryset(self):
        """Filter logs based on user access"""
        queryset = super().get_queryset()
        
        # Show logs for user's own jobs. See ExportTemplateViewSet.get_queryset
        # for why this uses created_by_id rather than created_by=self.request.user.
        if hasattr(self.request.user, 'dhis2_username'):
            queryset = queryset.filter(export_job__created_by_id=self.request.user.id)

        return queryset


class ExportConfigurationViewSet(viewsets.ModelViewSet):
    """
    ViewSet for export configurations
    """
    queryset = ExportConfiguration.objects.all()
    serializer_class = ExportConfigurationSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['config_type', 'is_active', 'is_system_config']
    search_fields = ['config_key', 'description']
    ordering_fields = ['config_type', 'config_key']
    ordering = ['config_type', 'config_key']
    
    def get_queryset(self):
        """Filter configurations based on user access"""
        queryset = super().get_queryset()
        
        # Show system configs and user-modifiable configs
        queryset = queryset.filter(
            Q(is_system_config=True) | Q(is_active=True)
        )
        
        return queryset
    
    @action(detail=False, methods=['post'])
    def update_config(self, request):
        """Update export configuration"""
        serializer = ConfigurationUpdateSerializer(data=request.data)
        
        if serializer.is_valid():
            try:
                config_type = serializer.validated_data['config_type']
                config_key = serializer.validated_data['config_key']
                config_value = serializer.validated_data['config_value']
                description = serializer.validated_data.get('description', '')
                
                # Update or create configuration
                config, created = ExportConfiguration.objects.update_or_create(
                    config_type=config_type,
                    config_key=config_key,
                    defaults={
                        'config_value': config_value,
                        'description': description,
                        'is_active': True
                    }
                )
                
                return Response({
                    'message': f'Configuration {"created" if created else "updated"} successfully',
                    'config_id': config.id
                })
                
            except Exception as e:
                return Response({
                    'error': f'Failed to update configuration: {str(e)}'
                }, status=status.HTTP_400_BAD_REQUEST)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
