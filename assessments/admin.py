from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.utils import timezone
from .models import (
    DataSyncLog, IndicatorData, IndicatorScore, ObjectiveScore, 
    SectorScore, SavedAssessment, AuditLog, ConflictResolution
)


class IndicatorDataInline(admin.TabularInline):
    """
    Inline admin for indicator data points
    """
    model = IndicatorData
    extra = 0
    readonly_fields = ['indicator', 'org_unit_id', 'org_unit_name', 'period', 'value', 'created_at']
    fields = ['indicator', 'org_unit_id', 'org_unit_name', 'period', 'value', 'created_at']
    can_delete = False


@admin.register(DataSyncLog)
class DataSyncLogAdmin(admin.ModelAdmin):
    """
    Admin interface for data sync logs
    """
    list_display = [
        'id', 'sync_type', 'status', 'dhis2_instance_url', 'total_indicators',
        'successful_indicators', 'failed_indicators', 'total_data_points',
        'duration_formatted', 'started_at'
    ]
    list_filter = ['sync_type', 'status', 'started_at']
    search_fields = ['dhis2_instance_url', 'error_message']
    readonly_fields = [
        'started_at', 'completed_at', 'duration_seconds', 'total_indicators',
        'successful_indicators', 'failed_indicators', 'total_data_points'
    ]
    ordering = ['-started_at']
    
    fieldsets = (
        ('Sync Information', {
            'fields': ('sync_type', 'status', 'dhis2_instance_url', 'dhis2_user')
        }),
        ('Sync Parameters', {
            'fields': ('period_start', 'period_end', 'org_unit_ids', 'indicator_uids')
        }),
        ('Results', {
            'fields': ('total_indicators', 'successful_indicators', 'failed_indicators', 'total_data_points')
        }),
        ('Error Information', {
            'fields': ('error_message', 'error_details'),
            'classes': ('collapse',)
        }),
        ('Timing', {
            'fields': ('started_at', 'completed_at', 'duration_seconds'),
            'classes': ('collapse',)
        }),
    )
    
    inlines = [IndicatorDataInline]
    
    def duration_formatted(self, obj):
        """Format duration in human-readable format"""
        if obj.duration_seconds is None:
            return '-'
        
        minutes = obj.duration_seconds // 60
        seconds = obj.duration_seconds % 60
        
        if minutes > 0:
            return f"{minutes}m {seconds}s"
        else:
            return f"{seconds}s"
    duration_formatted.short_description = 'Duration'
    
    actions = ['retry_failed_syncs', 'mark_as_completed']
    
    def retry_failed_syncs(self, request, queryset):
        """Retry failed syncs"""
        failed_syncs = queryset.filter(status=DataSyncLog.SyncStatus.FAILED)
        count = failed_syncs.count()
        
        for sync_log in failed_syncs:
            sync_log.status = DataSyncLog.SyncStatus.PENDING
            sync_log.error_message = ''
            sync_log.error_details = {}
            sync_log.completed_at = None
            sync_log.duration_seconds = None
            sync_log.save()
        
        self.message_user(request, f'{count} failed syncs have been queued for retry.')
    retry_failed_syncs.short_description = "Retry failed syncs"
    
    def mark_as_completed(self, request, queryset):
        """Mark syncs as completed"""
        count = queryset.update(status=DataSyncLog.SyncStatus.COMPLETED)
        self.message_user(request, f'{count} syncs have been marked as completed.')
    mark_as_completed.short_description = "Mark as completed"


@admin.register(IndicatorData)
class IndicatorDataAdmin(admin.ModelAdmin):
    """
    Admin interface for indicator data
    """
    list_display = [
        'indicator', 'org_unit_name', 'period', 'value', 'calculated_value',
        'sync_log', 'created_at'
    ]
    list_filter = ['indicator__is_active', 'period', 'created_at', 'sync_log__sync_type']
    search_fields = ['indicator__name', 'org_unit_name', 'period']
    readonly_fields = ['created_at', 'updated_at', 'calculated_value']
    ordering = ['-created_at']
    
    fieldsets = (
        ('Data Information', {
            'fields': ('indicator', 'org_unit_id', 'org_unit_name', 'period')
        }),
        ('Values', {
            'fields': ('value', 'numerator', 'denominator', 'calculated_value')
        }),
        ('Metadata', {
            'fields': ('sync_log', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
        ('DHIS2 Response', {
            'fields': ('dhis2_response',),
            'classes': ('collapse',)
        }),
    )


@admin.register(IndicatorScore)
class IndicatorScoreAdmin(admin.ModelAdmin):
    """
    Admin interface for indicator scores
    """
    list_display = [
        'indicator', 'objective', 'org_unit_name', 'assessment_period',
        'current_value', 'score', 'score_label', 'is_manual_override',
        'last_calculated'
    ]
    list_filter = [
        'objective__is_active', 'assessment_period', 'is_manual_override',
        'score', 'created_at'
    ]
    search_fields = ['indicator__name', 'objective__name', 'org_unit_name']
    readonly_fields = [
        'created_at', 'updated_at', 'last_calculated', 'target_gap',
        'percent_change', 'score_color', 'score_label'
    ]
    ordering = ['objective__order', 'indicator__name']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('indicator', 'objective', 'org_unit_id', 'org_unit_name', 'assessment_period')
        }),
        ('Data Values', {
            'fields': ('current_value', 'previous_value', 'target_value')
        }),
        ('Calculated Metrics', {
            'fields': ('target_gap', 'percent_change'),
            'classes': ('collapse',)
        }),
        ('Scoring', {
            'fields': ('score', 'score_color', 'score_label', 'scoring_rule', 'weight')
        }),
        ('Manual Override', {
            'fields': ('is_manual_override', 'override_reason', 'override_user'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at', 'last_calculated'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['recalculate_scores', 'clear_manual_overrides']
    
    def recalculate_scores(self, request, queryset):
        """Recalculate selected indicator scores"""
        count = 0
        for score in queryset:
            try:
                score.calculate_score()
                count += 1
            except Exception as e:
                self.message_user(request, f'Error recalculating score {score.id}: {str(e)}', level='ERROR')
        
        self.message_user(request, f'{count} indicator scores have been recalculated.')
    recalculate_scores.short_description = "Recalculate scores"
    
    def clear_manual_overrides(self, request, queryset):
        """Clear manual overrides for selected scores"""
        count = queryset.filter(is_manual_override=True).update(
            is_manual_override=False,
            override_reason='',
            override_user=None
        )
        self.message_user(request, f'{count} manual overrides have been cleared.')
    clear_manual_overrides.short_description = "Clear manual overrides"


@admin.register(ObjectiveScore)
class ObjectiveScoreAdmin(admin.ModelAdmin):
    """
    Admin interface for objective scores
    """
    list_display = [
        'objective', 'org_unit_name', 'assessment_period', 'final_score',
        'score_label', 'total_indicators', 'scored_indicators', 'last_calculated'
    ]
    list_filter = ['objective__is_active', 'assessment_period', 'created_at']
    search_fields = ['objective__name', 'org_unit_name']
    readonly_fields = [
        'created_at', 'updated_at', 'last_calculated', 'median_score',
        'weighted_score', 'final_score', 'score_color', 'score_label',
        'total_indicators', 'scored_indicators', 'total_weight'
    ]
    ordering = ['objective__order']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('objective', 'org_unit_id', 'org_unit_name', 'assessment_period')
        }),
        ('Calculated Scores', {
            'fields': ('median_score', 'weighted_score', 'final_score')
        }),
        ('Scoring Metadata', {
            'fields': ('score_color', 'score_label'),
            'classes': ('collapse',)
        }),
        ('Statistics', {
            'fields': ('total_indicators', 'scored_indicators', 'total_weight'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at', 'last_calculated'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['recalculate_scores']
    
    def recalculate_scores(self, request, queryset):
        """Recalculate selected objective scores"""
        count = 0
        for score in queryset:
            try:
                score.calculate_score()
                count += 1
            except Exception as e:
                self.message_user(request, f'Error recalculating score {score.id}: {str(e)}', level='ERROR')
        
        self.message_user(request, f'{count} objective scores have been recalculated.')
    recalculate_scores.short_description = "Recalculate scores"


@admin.register(SectorScore)
class SectorScoreAdmin(admin.ModelAdmin):
    """
    Admin interface for sector scores
    """
    list_display = [
        'org_unit_name', 'assessment_period', 'overall_score', 'score_label',
        'total_objectives', 'scored_objectives', 'total_indicators',
        'scored_indicators', 'last_calculated'
    ]
    list_filter = ['assessment_period', 'created_at']
    search_fields = ['org_unit_name']
    readonly_fields = [
        'created_at', 'updated_at', 'last_calculated', 'overall_score',
        'score_color', 'score_label', 'total_objectives', 'scored_objectives',
        'total_indicators', 'scored_indicators'
    ]
    ordering = ['-assessment_period__start_date', 'org_unit_name']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('org_unit_id', 'org_unit_name', 'assessment_period')
        }),
        ('Score Information', {
            'fields': ('overall_score', 'score_color', 'score_label')
        }),
        ('Statistics', {
            'fields': ('total_objectives', 'scored_objectives', 'total_indicators', 'scored_indicators'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at', 'last_calculated'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['recalculate_scores']
    
    def recalculate_scores(self, request, queryset):
        """Recalculate selected sector scores"""
        count = 0
        for score in queryset:
            try:
                score.calculate_score()
                count += 1
            except Exception as e:
                self.message_user(request, f'Error recalculating score {score.id}: {str(e)}', level='ERROR')
        
        self.message_user(request, f'{count} sector scores have been recalculated.')
    recalculate_scores.short_description = "Recalculate scores"


@admin.register(SavedAssessment)
class SavedAssessmentAdmin(admin.ModelAdmin):
    """
    Admin interface for saved assessments
    """
    list_display = [
        'name', 'org_unit_name', 'created_by', 'created_at', 
        'total_indicators', 'total_objectives', 'assessment_type'
    ]
    list_filter = ['created_at', 'created_by']
    search_fields = ['name', 'org_unit_name', 'org_unit_id']
    readonly_fields = [
        'created_at', 'updated_at', 'total_indicators', 
        'total_objectives'
    ]
    ordering = ['-created_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'org_unit_id', 'org_unit_name', 'created_by')
        }),
        ('Assessment Data', {
            'fields': ('periods', 'user_notes', 'indicator_data', 'calculated_scores', 'metadata'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def total_indicators(self, obj):
        return obj.total_indicators
    total_indicators.short_description = 'Total Indicators'
    
    def total_objectives(self, obj):
        return obj.total_objectives
    total_objectives.short_description = 'Total Objectives'
    
    def assessment_type(self, obj):
        return obj.assessment_type
    assessment_type.short_description = 'Assessment Type'


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    """
    Admin interface for audit logs
    """
    list_display = [
        'id', 'action_type', 'entity_type', 'entity_id', 'user', 
        'change_reason', 'created_at', 'org_unit_name', 'assessment_period'
    ]
    list_filter = [
        'action_type', 'entity_type', 'change_reason', 'is_conflict_resolution',
        'created_at', 'org_unit_id'
    ]
    search_fields = [
        'entity_id', 'user__username', 'user__email', 'org_unit_name',
        'change_description', 'indicator_id', 'objective_id'
    ]
    readonly_fields = [
        'created_at', 'old_values', 'new_values', 'changed_fields',
        'session_key', 'ip_address', 'user_agent'
    ]
    ordering = ['-created_at']
    
    fieldsets = (
        ('Audit Information', {
            'fields': ('action_type', 'entity_type', 'entity_id', 'change_reason')
        }),
        ('User Information', {
            'fields': ('user', 'session_key', 'ip_address', 'user_agent')
        }),
        ('Change Details', {
            'fields': ('change_description', 'old_values', 'new_values', 'changed_fields')
        }),
        ('Context', {
            'fields': ('org_unit_id', 'org_unit_name', 'assessment_period', 'indicator_id', 'objective_id')
        }),
        ('Conflict Resolution', {
            'fields': ('is_conflict_resolution', 'conflict_type', 'resolution_method'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )
    
    def has_add_permission(self, request):
        """Audit logs should not be manually created"""
        return False
    
    def has_change_permission(self, request, obj=None):
        """Audit logs should not be modified"""
        return False
    
    def has_delete_permission(self, request, obj=None):
        """Audit logs should not be deleted"""
        return False
    
    actions = ['export_audit_logs']
    
    def export_audit_logs(self, request, queryset):
        """Export selected audit logs to CSV"""
        import csv
        from django.http import HttpResponse
        
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="audit_logs.csv"'
        
        writer = csv.writer(response)
        writer.writerow([
            'ID', 'Action Type', 'Entity Type', 'Entity ID', 'User', 
            'Change Reason', 'Description', 'Org Unit', 'Assessment Period',
            'Created At', 'Old Values', 'New Values', 'Changed Fields'
        ])
        
        for log in queryset:
            writer.writerow([
                log.id, log.action_type, log.entity_type, log.entity_id,
                log.user.username if log.user else 'System',
                log.change_reason, log.change_description, log.org_unit_name,
                log.assessment_period, log.created_at,
                str(log.old_values), str(log.new_values), str(log.changed_fields)
            ])
        
        return response
    export_audit_logs.short_description = "Export selected audit logs to CSV"


@admin.register(ConflictResolution)
class ConflictResolutionAdmin(admin.ModelAdmin):
    """
    Admin interface for conflict resolutions
    """
    list_display = [
        'id', 'conflict_type', 'entity_type', 'entity_id', 'resolution_status',
        'resolution_method', 'resolved_by', 'detected_at'
    ]
    list_filter = [
        'conflict_type', 'entity_type', 'resolution_status', 'resolution_method',
        'detected_at', 'resolved_at', 'org_unit_id'
    ]
    search_fields = [
        'entity_id', 'resolved_by__username', 'org_unit_name', 
        'resolution_notes', 'assessment_period'
    ]
    readonly_fields = [
        'detected_at', 'manual_data', 'dhis2_data', 'conflict_fields'
    ]
    ordering = ['-detected_at']
    
    fieldsets = (
        ('Conflict Information', {
            'fields': ('conflict_type', 'entity_type', 'entity_id')
        }),
        ('Data Involved', {
            'fields': ('manual_data', 'dhis2_data', 'conflict_fields')
        }),
        ('Resolution', {
            'fields': ('resolution_method', 'resolution_status', 'resolved_by', 'resolution_notes')
        }),
        ('Context', {
            'fields': ('org_unit_id', 'org_unit_name', 'assessment_period')
        }),
        ('Timestamps', {
            'fields': ('detected_at', 'resolved_at'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['mark_as_resolved', 'escalate_conflicts', 'export_conflicts']
    
    def mark_as_resolved(self, request, queryset):
        """Mark selected conflicts as resolved"""
        updated = queryset.update(
            resolution_status=ConflictResolution.ResolutionStatus.RESOLVED,
            resolved_at=timezone.now(),
            resolved_by=request.user
        )
        self.message_user(request, f"{updated} conflicts marked as resolved.")
    mark_as_resolved.short_description = "Mark selected conflicts as resolved"
    
    def escalate_conflicts(self, request, queryset):
        """Escalate selected conflicts to admin"""
        updated = queryset.update(
            resolution_status=ConflictResolution.ResolutionStatus.ESCALATED,
            resolution_method=ConflictResolution.ResolutionMethod.ESCALATE
        )
        self.message_user(request, f"{updated} conflicts escalated to admin.")
    escalate_conflicts.short_description = "Escalate selected conflicts to admin"
    
    def export_conflicts(self, request, queryset):
        """Export selected conflicts to CSV"""
        import csv
        from django.http import HttpResponse
        
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="conflict_resolutions.csv"'
        
        writer = csv.writer(response)
        writer.writerow([
            'ID', 'Conflict Type', 'Entity Type', 'Entity ID', 'Resolution Status',
            'Resolution Method', 'Resolved By', 'Org Unit', 'Assessment Period',
            'Detected At', 'Resolved At', 'Notes'
        ])
        
        for conflict in queryset:
            writer.writerow([
                conflict.id, conflict.conflict_type, conflict.entity_type, conflict.entity_id,
                conflict.resolution_status, conflict.resolution_method,
                conflict.resolved_by.username if conflict.resolved_by else 'Unresolved',
                conflict.org_unit_name, conflict.assessment_period,
                conflict.detected_at, conflict.resolved_at, conflict.resolution_notes
            ])
        
        return response
    export_conflicts.short_description = "Export selected conflicts to CSV"
