from rest_framework import serializers
from .models import (
    ExportTemplate, ExportJob, ExportSchedule, ExportLog, ExportConfiguration
)
from dhis2_auth.models import DHIS2User
from organisation.models import OrgUnit


class ExportTemplateSerializer(serializers.ModelSerializer):
    """
    Serializer for export templates
    """
    created_by_username = serializers.CharField(source='created_by.dhis2_username', read_only=True)
    export_format_display = serializers.CharField(source='get_export_format_display', read_only=True)
    export_type_display = serializers.CharField(source='get_export_type_display', read_only=True)
    job_count = serializers.SerializerMethodField()
    
    class Meta:
        model = ExportTemplate
        fields = [
            'id', 'name', 'description', 'export_format', 'export_format_display',
            'export_type', 'export_type_display', 'template_config', 'is_active',
            'is_system_template', 'is_public', 'created_by', 'created_by_username',
            'created_at', 'updated_at', 'job_count'
        ]
        read_only_fields = ['created_at', 'updated_at', 'job_count']


class ExportJobSerializer(serializers.ModelSerializer):
    """
    Serializer for export jobs
    """
    created_by_username = serializers.CharField(source='created_by.dhis2_username', read_only=True)
    org_unit_name = serializers.CharField(source='org_unit_scope.name', read_only=True)
    template_name = serializers.CharField(source='template.name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    priority_display = serializers.CharField(source='get_priority_display', read_only=True)
    export_format_display = serializers.CharField(source='get_export_format_display', read_only=True)
    export_type_display = serializers.CharField(source='get_export_type_display', read_only=True)
    duration_formatted = serializers.CharField(read_only=True)
    is_expired = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = ExportJob
        fields = [
            'id', 'job_id', 'name', 'description', 'template', 'template_name',
            'export_format', 'export_format_display', 'export_type', 'export_type_display',
            'export_parameters', 'status', 'status_display', 'priority', 'priority_display',
            'progress_percentage', 'total_records', 'processed_records', 'file_path',
            'file_size', 'file_url', 'error_message', 'error_details', 'created_at',
            'started_at', 'completed_at', 'duration_seconds', 'duration_formatted',
            'created_by', 'created_by_username', 'org_unit_scope', 'org_unit_name',
            'expires_at', 'is_archived', 'is_expired'
        ]
        read_only_fields = [
            'created_at', 'started_at', 'completed_at', 'duration_seconds',
            'duration_formatted', 'is_expired'
        ]


class ExportScheduleSerializer(serializers.ModelSerializer):
    """
    Serializer for export schedules
    """
    created_by_username = serializers.CharField(source='created_by.dhis2_username', read_only=True)
    org_unit_name = serializers.CharField(source='org_unit_scope.name', read_only=True)
    template_name = serializers.CharField(source='template.name', read_only=True)
    frequency_display = serializers.CharField(source='get_frequency_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    success_rate = serializers.FloatField(read_only=True)
    
    class Meta:
        model = ExportSchedule
        fields = [
            'id', 'name', 'description', 'template', 'template_name', 'frequency',
            'frequency_display', 'custom_cron', 'schedule_parameters', 'status',
            'status_display', 'next_run', 'last_run', 'total_runs', 'successful_runs',
            'failed_runs', 'success_rate', 'created_by', 'created_by_username',
            'org_unit_scope', 'org_unit_name', 'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at', 'success_rate']


class ExportLogSerializer(serializers.ModelSerializer):
    """
    Serializer for export logs
    """
    level_display = serializers.CharField(source='get_level_display', read_only=True)
    export_job_name = serializers.CharField(source='export_job.name', read_only=True)
    
    class Meta:
        model = ExportLog
        fields = [
            'id', 'export_job', 'export_job_name', 'level', 'level_display',
            'message', 'details', 'timestamp'
        ]
        read_only_fields = ['timestamp']


class ExportConfigurationSerializer(serializers.ModelSerializer):
    """
    Serializer for export configurations
    """
    config_type_display = serializers.CharField(source='get_config_type_display', read_only=True)
    
    class Meta:
        model = ExportConfiguration
        fields = [
            'id', 'config_type', 'config_type_display', 'config_key', 'config_value',
            'description', 'is_active', 'is_system_config', 'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']


# Create/Update serializers
class ExportTemplateCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating export templates
    """
    class Meta:
        model = ExportTemplate
        fields = [
            'name', 'description', 'export_format', 'export_type', 'template_config',
            'is_active', 'is_system_template', 'is_public'
        ]


class ExportJobCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating export jobs
    """
    class Meta:
        model = ExportJob
        fields = [
            'name', 'description', 'template', 'export_format', 'export_type',
            'export_parameters', 'priority', 'org_unit_scope', 'expires_at'
        ]


class ExportScheduleCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating export schedules
    """
    class Meta:
        model = ExportSchedule
        fields = [
            'name', 'description', 'template', 'frequency', 'custom_cron',
            'schedule_parameters', 'status', 'org_unit_scope'
        ]


# Export request serializers
class ExportRequestSerializer(serializers.Serializer):
    """
    Serializer for export requests
    """
    export_type = serializers.ChoiceField(
        choices=ExportTemplate.ExportType.choices,
        help_text="Type of export to generate"
    )
    export_format = serializers.ChoiceField(
        choices=ExportTemplate.ExportFormat.choices,
        default=ExportTemplate.ExportFormat.EXCEL,
        help_text="Format of the exported file"
    )
    template_id = serializers.IntegerField(
        required=False,
        help_text="ID of the export template to use"
    )
    export_parameters = serializers.DictField(
        default=dict,
        help_text="Export parameters including filters, date ranges, etc."
    )
    priority = serializers.ChoiceField(
        choices=ExportJob.ExportPriority.choices,
        default=ExportJob.ExportPriority.NORMAL,
        help_text="Priority of the export job"
    )
    org_unit_id = serializers.IntegerField(
        required=False,
        help_text="Org unit scope for the export"
    )
    expires_in_hours = serializers.IntegerField(
        default=24,
        min_value=1,
        max_value=168,  # 1 week
        help_text="Hours until the exported file expires"
    )


class ExportStatusSerializer(serializers.Serializer):
    """
    Serializer for export job status
    """
    job_id = serializers.CharField()
    status = serializers.CharField()
    status_display = serializers.CharField()
    progress_percentage = serializers.IntegerField()
    total_records = serializers.IntegerField()
    processed_records = serializers.IntegerField()
    file_url = serializers.URLField(allow_null=True)
    error_message = serializers.CharField(allow_null=True)
    created_at = serializers.DateTimeField()
    started_at = serializers.DateTimeField(allow_null=True)
    completed_at = serializers.DateTimeField(allow_null=True)
    duration_formatted = serializers.CharField()


class ExportDownloadSerializer(serializers.Serializer):
    """
    Serializer for export download information
    """
    job_id = serializers.CharField()
    file_url = serializers.URLField()
    file_size = serializers.IntegerField()
    file_name = serializers.CharField()
    expires_at = serializers.DateTimeField()
    download_count = serializers.IntegerField()


# Bulk operation serializers
class BulkExportRequestSerializer(serializers.Serializer):
    """
    Serializer for bulk export requests
    """
    export_requests = serializers.ListField(
        child=ExportRequestSerializer(),
        min_length=1,
        max_length=10,
        help_text="List of export requests to process"
    )
    batch_name = serializers.CharField(
        max_length=255,
        help_text="Name for the batch of exports"
    )
    priority = serializers.ChoiceField(
        choices=ExportJob.ExportPriority.choices,
        default=ExportJob.ExportPriority.NORMAL,
        help_text="Priority for all jobs in the batch"
    )


class ExportTemplateCloneSerializer(serializers.Serializer):
    """
    Serializer for cloning export templates
    """
    template_id = serializers.IntegerField(
        help_text="ID of the template to clone"
    )
    new_name = serializers.CharField(
        max_length=255,
        help_text="Name for the cloned template"
    )
    new_description = serializers.CharField(
        required=False,
        help_text="Description for the cloned template"
    )
    is_public = serializers.BooleanField(
        default=True,
        help_text="Whether the cloned template should be public"
    )


# Schedule management serializers
class ScheduleExecutionSerializer(serializers.Serializer):
    """
    Serializer for manual schedule execution
    """
    schedule_id = serializers.IntegerField(
        help_text="ID of the schedule to execute"
    )
    execute_now = serializers.BooleanField(
        default=True,
        help_text="Whether to execute the schedule immediately"
    )
    override_parameters = serializers.DictField(
        required=False,
        help_text="Parameters to override for this execution"
    )


class ScheduleStatusUpdateSerializer(serializers.Serializer):
    """
    Serializer for updating schedule status
    """
    schedule_ids = serializers.ListField(
        child=serializers.IntegerField(),
        help_text="List of schedule IDs to update"
    )
    new_status = serializers.ChoiceField(
        choices=ExportSchedule.ScheduleStatus.choices,
        help_text="New status for the schedules"
    )


# Configuration management serializers
class ConfigurationUpdateSerializer(serializers.Serializer):
    """
    Serializer for updating export configurations
    """
    config_type = serializers.ChoiceField(
        choices=ExportConfiguration.ConfigType.choices,
        help_text="Type of configuration to update"
    )
    config_key = serializers.CharField(
        max_length=100,
        help_text="Configuration key"
    )
    config_value = serializers.JSONField(
        help_text="New configuration value"
    )
    description = serializers.CharField(
        required=False,
        help_text="Description for the configuration"
    )


# Export analytics serializers
class ExportAnalyticsSerializer(serializers.Serializer):
    """
    Serializer for export analytics data
    """
    total_jobs = serializers.IntegerField()
    completed_jobs = serializers.IntegerField()
    failed_jobs = serializers.IntegerField()
    pending_jobs = serializers.IntegerField()
    success_rate = serializers.FloatField()
    average_duration = serializers.FloatField()
    total_file_size = serializers.IntegerField()
    jobs_by_format = serializers.DictField()
    jobs_by_type = serializers.DictField()
    jobs_by_status = serializers.DictField()
    recent_jobs = serializers.ListField(child=serializers.DictField())


class ExportPerformanceSerializer(serializers.Serializer):
    """
    Serializer for export performance metrics
    """
    time_period = serializers.CharField()
    total_exports = serializers.IntegerField()
    successful_exports = serializers.IntegerField()
    failed_exports = serializers.IntegerField()
    average_processing_time = serializers.FloatField()
    peak_processing_time = serializers.FloatField()
    total_data_processed = serializers.IntegerField()
    performance_trend = serializers.ListField(child=serializers.DictField())


# Export template validation serializers
class TemplateValidationSerializer(serializers.Serializer):
    """
    Serializer for template validation
    """
    template_config = serializers.JSONField(
        help_text="Template configuration to validate"
    )
    export_type = serializers.ChoiceField(
        choices=ExportTemplate.ExportType.choices,
        help_text="Export type for validation"
    )
    export_format = serializers.ChoiceField(
        choices=ExportTemplate.ExportFormat.choices,
        help_text="Export format for validation"
    )


class TemplateValidationResultSerializer(serializers.Serializer):
    """
    Serializer for template validation results
    """
    is_valid = serializers.BooleanField()
    errors = serializers.ListField(child=serializers.CharField())
    warnings = serializers.ListField(child=serializers.CharField())
    suggestions = serializers.ListField(child=serializers.CharField())
    estimated_file_size = serializers.IntegerField(allow_null=True)
    estimated_processing_time = serializers.FloatField(allow_null=True) 