from django.contrib import admin
from django.utils.html import format_html
from django.utils import timezone
from .models import (
    DataSyncLog, IndicatorData, IndicatorScore, ObjectiveScore, SectorScore
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
