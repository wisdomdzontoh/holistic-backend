from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
import json

from dhis2_auth.models import DHIS2User
from organisation.models import OrgUnit


class ExportTemplate(models.Model):
    """
    Model to store export templates
    """
    class ExportFormat(models.TextChoices):
        EXCEL = 'excel', _('Excel')
        CSV = 'csv', _('CSV')
        PDF = 'pdf', _('PDF')
        HTML = 'html', _('HTML')
    
    class ExportType(models.TextChoices):
        DASHBOARD_SUMMARY = 'dashboard_summary', _('Dashboard Summary')
        OBJECTIVE_PERFORMANCE = 'objective_performance', _('Objective Performance')
        INDICATOR_PERFORMANCE = 'indicator_performance', _('Indicator Performance')
        ORG_UNIT_PERFORMANCE = 'org_unit_performance', _('Org Unit Performance')
        TREND_ANALYSIS = 'trend_analysis', _('Trend Analysis')
        COMPARATIVE_ANALYSIS = 'comparative_analysis', _('Comparative Analysis')
        CUSTOM_REPORT = 'custom_report', _('Custom Report')
    
    # Basic information
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    export_format = models.CharField(
        max_length=10,
        choices=ExportFormat.choices,
        default=ExportFormat.EXCEL
    )
    export_type = models.CharField(
        max_length=50,
        choices=ExportType.choices,
        default=ExportType.DASHBOARD_SUMMARY
    )
    
    # Template configuration
    template_config = models.JSONField(
        default=dict,
        help_text="Template configuration including layout, styling, and data mapping"
    )
    
    # Access control
    is_active = models.BooleanField(default=True)
    is_system_template = models.BooleanField(
        default=False,
        help_text="Whether this is a system-defined template"
    )
    is_public = models.BooleanField(
        default=True,
        help_text="Whether this template is available to all users"
    )
    
    # Metadata
    created_by = models.ForeignKey(
        DHIS2User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_export_templates'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'export_templates'
        verbose_name = 'Export Template'
        verbose_name_plural = 'Export Templates'
        ordering = ['name']
    
    def __str__(self):
        return f"{self.name} ({self.get_export_format_display()})"


class ExportJob(models.Model):
    """
    Model to track export jobs
    """
    class ExportStatus(models.TextChoices):
        PENDING = 'pending', _('Pending')
        IN_PROGRESS = 'in_progress', _('In Progress')
        COMPLETED = 'completed', _('Completed')
        FAILED = 'failed', _('Failed')
        CANCELLED = 'cancelled', _('Cancelled')
    
    class ExportPriority(models.TextChoices):
        LOW = 'low', _('Low')
        NORMAL = 'normal', _('Normal')
        HIGH = 'high', _('High')
        URGENT = 'urgent', _('Urgent')
    
    # Job information
    job_id = models.CharField(max_length=100, unique=True)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    
    # Export configuration
    template = models.ForeignKey(
        ExportTemplate,
        on_delete=models.CASCADE,
        related_name='export_jobs'
    )
    export_format = models.CharField(
        max_length=10,
        choices=ExportTemplate.ExportFormat.choices
    )
    export_type = models.CharField(
        max_length=50,
        choices=ExportTemplate.ExportType.choices
    )
    
    # Export parameters
    export_parameters = models.JSONField(
        default=dict,
        help_text="Export parameters including filters, date ranges, etc."
    )
    
    # Job status and priority
    status = models.CharField(
        max_length=20,
        choices=ExportStatus.choices,
        default=ExportStatus.PENDING
    )
    priority = models.CharField(
        max_length=10,
        choices=ExportPriority.choices,
        default=ExportPriority.NORMAL
    )
    
    # Progress tracking
    progress_percentage = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )
    total_records = models.PositiveIntegerField(default=0)
    processed_records = models.PositiveIntegerField(default=0)
    
    # File information
    file_path = models.CharField(max_length=500, blank=True)
    file_size = models.PositiveIntegerField(default=0)
    file_url = models.URLField(blank=True)
    
    # Error handling
    error_message = models.TextField(blank=True)
    error_details = models.JSONField(default=dict, blank=True)
    
    # Timing
    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    duration_seconds = models.PositiveIntegerField(default=0)
    
    # User and access control
    created_by = models.ForeignKey(
        DHIS2User,
        on_delete=models.CASCADE,
        related_name='export_jobs'
    )
    org_unit_scope = models.ForeignKey(
        OrgUnit,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='export_jobs'
    )
    
    # Retention
    expires_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the exported file should be deleted"
    )
    is_archived = models.BooleanField(default=False)
    
    class Meta:
        db_table = 'export_jobs'
        verbose_name = 'Export Job'
        verbose_name_plural = 'Export Jobs'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', 'priority']),
            models.Index(fields=['created_by', 'created_at']),
            models.Index(fields=['export_type', 'export_format']),
        ]
    
    def __str__(self):
        return f"{self.name} ({self.get_status_display()})"
    
    @property
    def is_expired(self):
        """Check if the export job has expired"""
        if not self.expires_at:
            return False
        return timezone.now() > self.expires_at
    
    @property
    def duration_formatted(self):
        """Format duration in human-readable format"""
        if self.duration_seconds == 0:
            return "0s"
        
        minutes = self.duration_seconds // 60
        seconds = self.duration_seconds % 60
        
        if minutes > 0:
            return f"{minutes}m {seconds}s"
        else:
            return f"{seconds}s"
    
    def mark_started(self):
        """Mark job as started"""
        self.status = self.ExportStatus.IN_PROGRESS
        self.started_at = timezone.now()
        self.save()
    
    def mark_completed(self, file_path=None, file_size=0, file_url=None):
        """Mark job as completed"""
        self.status = self.ExportStatus.COMPLETED
        self.completed_at = timezone.now()
        self.progress_percentage = 100
        self.processed_records = self.total_records
        
        if file_path:
            self.file_path = file_path
        if file_size:
            self.file_size = file_size
        if file_url:
            self.file_url = file_url
        
        if self.started_at:
            self.duration_seconds = int((self.completed_at - self.started_at).total_seconds())
        
        self.save()
    
    def mark_failed(self, error_message="", error_details=None):
        """Mark job as failed"""
        self.status = self.ExportStatus.FAILED
        self.completed_at = timezone.now()
        self.error_message = error_message
        self.error_details = error_details or {}
        
        if self.started_at:
            self.duration_seconds = int((self.completed_at - self.started_at).total_seconds())
        
        self.save()
    
    def update_progress(self, processed_count, total_count=None):
        """Update job progress"""
        if total_count:
            self.total_records = total_count
        
        self.processed_records = processed_count
        
        if self.total_records > 0:
            self.progress_percentage = int((processed_count / self.total_records) * 100)
        
        self.save()


class ExportSchedule(models.Model):
    """
    Model to store export schedules for recurring exports
    """
    class ScheduleFrequency(models.TextChoices):
        DAILY = 'daily', _('Daily')
        WEEKLY = 'weekly', _('Weekly')
        MONTHLY = 'monthly', _('Monthly')
        QUARTERLY = 'quarterly', _('Quarterly')
        YEARLY = 'yearly', _('Yearly')
        CUSTOM = 'custom', _('Custom')
    
    class ScheduleStatus(models.TextChoices):
        ACTIVE = 'active', _('Active')
        PAUSED = 'paused', _('Paused')
        DISABLED = 'disabled', _('Disabled')
    
    # Schedule information
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    
    # Schedule configuration
    template = models.ForeignKey(
        ExportTemplate,
        on_delete=models.CASCADE,
        related_name='export_schedules'
    )
    frequency = models.CharField(
        max_length=20,
        choices=ScheduleFrequency.choices,
        default=ScheduleFrequency.MONTHLY
    )
    custom_cron = models.CharField(
        max_length=100,
        blank=True,
        help_text="Custom cron expression for custom frequency"
    )
    
    # Schedule parameters
    schedule_parameters = models.JSONField(
        default=dict,
        help_text="Schedule-specific parameters"
    )
    
    # Status and timing
    status = models.CharField(
        max_length=20,
        choices=ScheduleStatus.choices,
        default=ScheduleStatus.ACTIVE
    )
    next_run = models.DateTimeField(null=True, blank=True)
    last_run = models.DateTimeField(null=True, blank=True)
    
    # Execution tracking
    total_runs = models.PositiveIntegerField(default=0)
    successful_runs = models.PositiveIntegerField(default=0)
    failed_runs = models.PositiveIntegerField(default=0)
    
    # User and access control
    created_by = models.ForeignKey(
        DHIS2User,
        on_delete=models.CASCADE,
        related_name='export_schedules'
    )
    org_unit_scope = models.ForeignKey(
        OrgUnit,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='export_schedules'
    )
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'export_schedules'
        verbose_name = 'Export Schedule'
        verbose_name_plural = 'Export Schedules'
        ordering = ['name']
    
    def __str__(self):
        return f"{self.name} ({self.get_frequency_display()})"
    
    @property
    def success_rate(self):
        """Calculate success rate"""
        if self.total_runs == 0:
            return 0
        return (self.successful_runs / self.total_runs) * 100


class ExportLog(models.Model):
    """
    Model to store export execution logs
    """
    class LogLevel(models.TextChoices):
        DEBUG = 'debug', _('Debug')
        INFO = 'info', _('Info')
        WARNING = 'warning', _('Warning')
        ERROR = 'error', _('Error')
        CRITICAL = 'critical', _('Critical')
    
    # Log information
    export_job = models.ForeignKey(
        ExportJob,
        on_delete=models.CASCADE,
        related_name='logs'
    )
    level = models.CharField(
        max_length=10,
        choices=LogLevel.choices,
        default=LogLevel.INFO
    )
    message = models.TextField()
    details = models.JSONField(default=dict, blank=True)
    
    # Timing
    timestamp = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'export_logs'
        verbose_name = 'Export Log'
        verbose_name_plural = 'Export Logs'
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['export_job', 'timestamp']),
            models.Index(fields=['level', 'timestamp']),
        ]
    
    def __str__(self):
        return f"{self.export_job.name} - {self.level}: {self.message[:50]}"


class ExportConfiguration(models.Model):
    """
    Model to store system-wide export configuration
    """
    class ConfigType(models.TextChoices):
        STORAGE = 'storage', _('Storage')
        FORMATTING = 'formatting', _('Formatting')
        SECURITY = 'security', _('Security')
        PERFORMANCE = 'performance', _('Performance')
        NOTIFICATION = 'notification', _('Notification')
    
    # Configuration information
    config_type = models.CharField(
        max_length=20,
        choices=ConfigType.choices
    )
    config_key = models.CharField(max_length=100)
    config_value = models.JSONField()
    description = models.TextField(blank=True)
    
    # Access control
    is_active = models.BooleanField(default=True)
    is_system_config = models.BooleanField(
        default=False,
        help_text="Whether this is a system configuration that cannot be modified"
    )
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'export_configurations'
        verbose_name = 'Export Configuration'
        verbose_name_plural = 'Export Configurations'
        unique_together = ['config_type', 'config_key']
        ordering = ['config_type', 'config_key']
    
    def __str__(self):
        return f"{self.config_type}.{self.config_key}"
