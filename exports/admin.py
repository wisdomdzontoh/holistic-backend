from django.contrib import admin
from django.utils.html import format_html
from django.utils import timezone
from import_export.admin import ImportExportModelAdmin
from .models import (
    ExportTemplate, ExportJob, ExportSchedule, ExportLog, ExportConfiguration
)


class ExportLogInline(admin.TabularInline):
    """
    Inline admin for export logs
    """
    model = ExportLog
    extra = 0
    readonly_fields = ['timestamp']
    fields = ['level', 'message', 'timestamp']
    can_delete = False
    
    def has_add_permission(self, request, obj=None):
        return False


@admin.register(ExportTemplate)
class ExportTemplateAdmin(ImportExportModelAdmin):
    """
    Admin for export templates
    """
    list_display = [
        'name', 'export_format', 'export_type', 'is_active', 
        'is_system_template', 'is_public', 'created_by', 'created_at'
    ]
    list_filter = [
        'export_format', 'export_type', 'is_active', 
        'is_system_template', 'is_public', 'created_at'
    ]
    search_fields = ['name', 'description', 'created_by__dhis2_username']
    readonly_fields = ['created_at', 'updated_at']
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'description', 'export_format', 'export_type')
        }),
        ('Template Configuration', {
            'fields': ('template_config',),
            'classes': ('collapse',)
        }),
        ('Access Control', {
            'fields': ('is_active', 'is_system_template', 'is_public')
        }),
        ('Metadata', {
            'fields': ('created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('created_by')
    
    actions = ['activate_templates', 'deactivate_templates', 'make_public', 'make_private']
    
    def activate_templates(self, request, queryset):
        """Activate selected templates"""
        updated = queryset.update(is_active=True)
        self.message_user(request, f'{updated} templates activated successfully.')
    activate_templates.short_description = "Activate selected templates"
    
    def deactivate_templates(self, request, queryset):
        """Deactivate selected templates"""
        updated = queryset.update(is_active=False)
        self.message_user(request, f'{updated} templates deactivated successfully.')
    deactivate_templates.short_description = "Deactivate selected templates"
    
    def make_public(self, request, queryset):
        """Make selected templates public"""
        updated = queryset.update(is_public=True)
        self.message_user(request, f'{updated} templates made public successfully.')
    make_public.short_description = "Make selected templates public"
    
    def make_private(self, request, queryset):
        """Make selected templates private"""
        updated = queryset.update(is_public=False)
        self.message_user(request, f'{updated} templates made private successfully.')
    make_private.short_description = "Make selected templates private"


@admin.register(ExportJob)
class ExportJobAdmin(ImportExportModelAdmin):
    """
    Admin for export jobs
    """
    list_display = [
        'job_id', 'name', 'export_format', 'export_type', 'status', 
        'priority', 'progress_percentage', 'created_by', 'created_at', 'duration_formatted'
    ]
    list_filter = [
        'status', 'priority', 'export_format', 'export_type', 
        'is_archived', 'created_at'
    ]
    search_fields = [
        'job_id', 'name', 'description', 'created_by__dhis2_username',
        'org_unit_scope__name'
    ]
    readonly_fields = [
        'job_id', 'created_at', 'started_at', 'completed_at', 
        'duration_seconds', 'duration_formatted', 'is_expired'
    ]
    fieldsets = (
        ('Job Information', {
            'fields': ('job_id', 'name', 'description', 'template')
        }),
        ('Export Configuration', {
            'fields': ('export_format', 'export_type', 'export_parameters')
        }),
        ('Status and Priority', {
            'fields': ('status', 'priority', 'progress_percentage', 'total_records', 'processed_records')
        }),
        ('File Information', {
            'fields': ('file_path', 'file_size', 'file_url'),
            'classes': ('collapse',)
        }),
        ('Error Information', {
            'fields': ('error_message', 'error_details'),
            'classes': ('collapse',)
        }),
        ('Timing', {
            'fields': ('created_at', 'started_at', 'completed_at', 'duration_seconds', 'duration_formatted'),
            'classes': ('collapse',)
        }),
        ('User and Access', {
            'fields': ('created_by', 'org_unit_scope', 'expires_at', 'is_archived', 'is_expired')
        }),
    )
    inlines = [ExportLogInline]
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'created_by', 'org_unit_scope', 'template'
        )
    
    actions = ['cancel_jobs', 'archive_jobs', 'unarchive_jobs', 'retry_failed_jobs']
    
    def cancel_jobs(self, request, queryset):
        """Cancel selected jobs"""
        cancellable_jobs = queryset.exclude(status__in=[
            ExportJob.ExportStatus.COMPLETED, 
            ExportJob.ExportStatus.FAILED, 
            ExportJob.ExportStatus.CANCELLED
        ])
        updated = cancellable_jobs.update(
            status=ExportJob.ExportStatus.CANCELLED,
            completed_at=timezone.now()
        )
        self.message_user(request, f'{updated} jobs cancelled successfully.')
    cancel_jobs.short_description = "Cancel selected jobs"
    
    def archive_jobs(self, request, queryset):
        """Archive selected jobs"""
        updated = queryset.update(is_archived=True)
        self.message_user(request, f'{updated} jobs archived successfully.')
    archive_jobs.short_description = "Archive selected jobs"
    
    def unarchive_jobs(self, request, queryset):
        """Unarchive selected jobs"""
        updated = queryset.update(is_archived=False)
        self.message_user(request, f'{updated} jobs unarchived successfully.')
    unarchive_jobs.short_description = "Unarchive selected jobs"
    
    def retry_failed_jobs(self, request, queryset):
        """Retry failed jobs"""
        failed_jobs = queryset.filter(status=ExportJob.ExportStatus.FAILED)
        updated = failed_jobs.update(
            status=ExportJob.ExportStatus.PENDING,
            error_message='',
            error_details={},
            started_at=None,
            completed_at=None,
            duration_seconds=0,
            progress_percentage=0,
            processed_records=0
        )
        self.message_user(request, f'{updated} failed jobs queued for retry.')
    retry_failed_jobs.short_description = "Retry failed jobs"


@admin.register(ExportSchedule)
class ExportScheduleAdmin(ImportExportModelAdmin):
    """
    Admin for export schedules
    """
    list_display = [
        'name', 'template', 'frequency', 'status', 'next_run', 
        'last_run', 'total_runs', 'success_rate', 'created_by'
    ]
    list_filter = ['frequency', 'status', 'created_at']
    search_fields = [
        'name', 'description', 'created_by__dhis2_username',
        'org_unit_scope__name'
    ]
    readonly_fields = [
        'created_at', 'updated_at', 'last_run', 'total_runs', 
        'successful_runs', 'failed_runs', 'success_rate'
    ]
    fieldsets = (
        ('Schedule Information', {
            'fields': ('name', 'description', 'template')
        }),
        ('Schedule Configuration', {
            'fields': ('frequency', 'custom_cron', 'schedule_parameters')
        }),
        ('Status and Timing', {
            'fields': ('status', 'next_run', 'last_run')
        }),
        ('Execution Tracking', {
            'fields': ('total_runs', 'successful_runs', 'failed_runs', 'success_rate'),
            'classes': ('collapse',)
        }),
        ('User and Access', {
            'fields': ('created_by', 'org_unit_scope')
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'created_by', 'org_unit_scope', 'template'
        )
    
    actions = ['activate_schedules', 'deactivate_schedules', 'pause_schedules']
    
    def activate_schedules(self, request, queryset):
        """Activate selected schedules"""
        updated = queryset.update(status=ExportSchedule.ScheduleStatus.ACTIVE)
        self.message_user(request, f'{updated} schedules activated successfully.')
    activate_schedules.short_description = "Activate selected schedules"
    
    def deactivate_schedules(self, request, queryset):
        """Deactivate selected schedules"""
        updated = queryset.update(status=ExportSchedule.ScheduleStatus.DISABLED)
        self.message_user(request, f'{updated} schedules deactivated successfully.')
    deactivate_schedules.short_description = "Deactivate selected schedules"
    
    def pause_schedules(self, request, queryset):
        """Pause selected schedules"""
        updated = queryset.update(status=ExportSchedule.ScheduleStatus.PAUSED)
        self.message_user(request, f'{updated} schedules paused successfully.')
    pause_schedules.short_description = "Pause selected schedules"


@admin.register(ExportLog)
class ExportLogAdmin(ImportExportModelAdmin):
    """
    Admin for export logs
    """
    list_display = [
        'export_job', 'level', 'message_short', 'timestamp'
    ]
    list_filter = ['level', 'timestamp', 'export_job__status']
    search_fields = [
        'message', 'export_job__name', 'export_job__job_id'
    ]
    readonly_fields = ['timestamp']
    fieldsets = (
        ('Log Information', {
            'fields': ('export_job', 'level', 'message', 'details')
        }),
        ('Timing', {
            'fields': ('timestamp',),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('export_job')
    
    def message_short(self, obj):
        """Display shortened message"""
        return obj.message[:100] + '...' if len(obj.message) > 100 else obj.message
    message_short.short_description = 'Message'
    
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False
    
    actions = ['clear_old_logs']
    
    def clear_old_logs(self, request, queryset):
        """Clear logs older than 30 days"""
        from datetime import timedelta
        cutoff_date = timezone.now() - timedelta(days=30)
        old_logs = ExportLog.objects.filter(timestamp__lt=cutoff_date)
        count = old_logs.count()
        old_logs.delete()
        self.message_user(request, f'{count} old logs cleared successfully.')
    clear_old_logs.short_description = "Clear logs older than 30 days"


@admin.register(ExportConfiguration)
class ExportConfigurationAdmin(ImportExportModelAdmin):
    """
    Admin for export configurations
    """
    list_display = [
        'config_type', 'config_key', 'is_active', 'is_system_config', 
        'created_at', 'updated_at'
    ]
    list_filter = ['config_type', 'is_active', 'is_system_config', 'created_at']
    search_fields = ['config_key', 'description']
    readonly_fields = ['created_at', 'updated_at']
    fieldsets = (
        ('Configuration Information', {
            'fields': ('config_type', 'config_key', 'config_value', 'description')
        }),
        ('Access Control', {
            'fields': ('is_active', 'is_system_config')
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['activate_configs', 'deactivate_configs']
    
    def activate_configs(self, request, queryset):
        """Activate selected configurations"""
        updated = queryset.update(is_active=True)
        self.message_user(request, f'{updated} configurations activated successfully.')
    activate_configs.short_description = "Activate selected configurations"
    
    def deactivate_configs(self, request, queryset):
        """Deactivate selected configurations"""
        updated = queryset.update(is_active=False)
        self.message_user(request, f'{updated} configurations deactivated successfully.')
    deactivate_configs.short_description = "Deactivate selected configurations"
