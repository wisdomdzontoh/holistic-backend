from django.contrib import admin
from django.utils.html import format_html
from django.utils import timezone
from .models import (
    Milestone, Objective, ScoringRule, WeightingScheme, ObjectiveWeight, 
    IndicatorWeight, AssessmentPeriod, SystemConfiguration
)
from datetime import timedelta


class ObjectiveWeightInline(admin.TabularInline):
    """
    Inline admin for objective weights
    """
    model = ObjectiveWeight
    extra = 0
    fields = ['objective', 'weight']
    autocomplete_fields = ['objective']


class IndicatorWeightInline(admin.TabularInline):
    """
    Inline admin for indicator weights
    """
    model = IndicatorWeight
    extra = 0
    fields = ['indicator', 'weight']
    autocomplete_fields = ['indicator']


@admin.register(Objective)
class ObjectiveAdmin(admin.ModelAdmin):
    """
    Admin interface for objectives
    """
    list_display = [
        'name', 'code', 'order', 'is_active', 'indicator_count', 
        'total_weight', 'milestone', 'color_preview'
    ]
    list_filter = ['is_active', 'created_at', 'milestone']
    search_fields = ['name', 'description', 'code']
    ordering = ['order', 'name']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'description', 'code', 'order', 'is_active')
        }),
        ('Milestone Assignment', {
            'fields': ('milestone',)
        }),
        ('Display Settings', {
            'fields': ('color',)
        }),
    )
    
    inlines = [IndicatorWeightInline]
    
    def indicator_count(self, obj):
        """Count of indicators in this objective"""
        return obj.indicator_weights.count()
    indicator_count.short_description = 'Indicators'
    
    def total_weight(self, obj):
        """Total weight of indicators in this objective"""
        return obj.get_total_weight()
    total_weight.short_description = 'Total Weight'
    
    def color_preview(self, obj):
        """Show color preview"""
        return format_html(
            '<div style="background-color: {}; width: 20px; height: 20px; border: 1px solid #ccc;"></div>',
            obj.color
        )
    color_preview.short_description = 'Color'
    
    actions = ['activate_objectives', 'deactivate_objectives']
    
    def activate_objectives(self, request, queryset):
        """Activate selected objectives"""
        updated = queryset.update(is_active=True)
        self.message_user(request, f'{updated} objectives have been activated.')
    activate_objectives.short_description = "Activate selected objectives"
    
    def deactivate_objectives(self, request, queryset):
        """Deactivate selected objectives"""
        updated = queryset.update(is_active=False)
        self.message_user(request, f'{updated} objectives have been deactivated.')
    deactivate_objectives.short_description = "Deactivate selected objectives"


@admin.register(Milestone)
class MilestoneAdmin(admin.ModelAdmin):
    """
    Admin interface for milestones
    """
    list_display = [
        'name', 'code', 'order', 'score', 'is_active', 'objective_count', 
        'color_preview'
    ]
    list_filter = ['is_active', 'score', 'created_at']
    search_fields = ['name', 'description', 'code']
    ordering = ['order', 'name']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'description', 'code', 'order', 'is_active')
        }),
        ('Scoring', {
            'fields': ('score',)
        }),
        ('Display Settings', {
            'fields': ('color',)
        }),
    )
    
    def objective_count(self, obj):
        """Count of objectives using this milestone"""
        return obj.objectives.count()
    objective_count.short_description = 'Objectives'
    
    def color_preview(self, obj):
        """Show color preview"""
        return format_html(
            '<div style="background-color: {}; width: 20px; height: 20px; border: 1px solid #ccc;"></div>',
            obj.color
        )
    color_preview.short_description = 'Color'
    
    actions = ['activate_milestones', 'deactivate_milestones', 'reset_scores']
    
    def activate_milestones(self, request, queryset):
        """Activate selected milestones"""
        updated = queryset.update(is_active=True)
        self.message_user(request, f'{updated} milestones have been activated.')
    activate_milestones.short_description = "Activate selected milestones"
    
    def deactivate_milestones(self, request, queryset):
        """Deactivate selected milestones"""
        updated = queryset.update(is_active=False)
        self.message_user(request, f'{updated} milestones have been deactivated.')
    deactivate_milestones.short_description = "Deactivate selected milestones"
    
    def reset_scores(self, request, queryset):
        """Reset scores to default (-2)"""
        updated = queryset.update(score=-2)
        self.message_user(request, f'{updated} milestone scores have been reset to -2.')
    reset_scores.short_description = "Reset scores to default"


@admin.register(ScoringRule)
class ScoringRuleAdmin(admin.ModelAdmin):
    """
    Admin interface for scoring rules
    """
    list_display = [
        'name', 'performance_type', 'min_value', 'max_value', 
        'score', 'label', 'priority', 'is_active', 'color_preview'
    ]
    list_filter = ['performance_type', 'is_active', 'score', 'priority']
    search_fields = ['name', 'label']
    ordering = ['performance_type', 'priority', 'min_value']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'performance_type', 'is_active')
        }),
        ('Threshold Values', {
            'fields': ('min_value', 'max_value')
        }),
        ('Scoring', {
            'fields': ('score', 'label', 'color', 'priority')
        }),
    )
    
    def color_preview(self, obj):
        """Show color preview"""
        return format_html(
            '<div style="background-color: {}; width: 20px; height: 20px; border: 1px solid #ccc;"></div>',
            obj.color
        )
    color_preview.short_description = 'Color'
    
    actions = ['activate_rules', 'deactivate_rules', 'duplicate_rules']
    
    def activate_rules(self, request, queryset):
        """Activate selected rules"""
        updated = queryset.update(is_active=True)
        self.message_user(request, f'{updated} scoring rules have been activated.')
    activate_rules.short_description = "Activate selected rules"
    
    def deactivate_rules(self, request, queryset):
        """Deactivate selected rules"""
        updated = queryset.update(is_active=False)
        self.message_user(request, f'{updated} scoring rules have been deactivated.')
    deactivate_rules.short_description = "Deactivate selected rules"
    
    def duplicate_rules(self, request, queryset):
        """Duplicate selected rules"""
        duplicated_count = 0
        
        for rule in queryset:
            # Create a copy with modified values
            new_rule = ScoringRule.objects.create(
                name=f"{rule.name} (Copy)",
                performance_type=rule.performance_type,
                min_value=rule.min_value,
                max_value=rule.max_value,
                score=rule.score,
                color=rule.color,
                label=rule.label,
                priority=rule.priority + 1,
                is_active=False  # Start as inactive
            )
            duplicated_count += 1
        
        self.message_user(request, f'{duplicated_count} scoring rules have been duplicated.')
    duplicate_rules.short_description = "Duplicate selected rules"


@admin.register(WeightingScheme)
class WeightingSchemeAdmin(admin.ModelAdmin):
    """
    Admin interface for weighting schemes
    """
    list_display = [
        'name', 'is_active', 'is_default', 'objective_count', 
        'total_weight', 'created_at'
    ]
    list_filter = ['is_active', 'is_default', 'created_at']
    search_fields = ['name', 'description']
    ordering = ['-is_default', 'name']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'description', 'is_active', 'is_default')
        }),
    )
    
    inlines = [ObjectiveWeightInline]
    
    def objective_count(self, obj):
        """Count of objectives in this scheme"""
        return obj.objective_weights.count()
    objective_count.short_description = 'Objectives'
    
    def total_weight(self, obj):
        """Total weight of objectives in this scheme"""
        return obj.get_total_objective_weight()
    total_weight.short_description = 'Total Weight'
    
    actions = ['activate_schemes', 'deactivate_schemes', 'normalize_weights']
    
    def activate_schemes(self, request, queryset):
        """Activate selected schemes"""
        updated = queryset.update(is_active=True)
        self.message_user(request, f'{updated} weighting schemes have been activated.')
    activate_schemes.short_description = "Activate selected schemes"
    
    def deactivate_schemes(self, request, queryset):
        """Deactivate selected schemes"""
        updated = queryset.update(is_active=False)
        self.message_user(request, f'{updated} weighting schemes have been deactivated.')
    deactivate_schemes.short_description = "Deactivate selected schemes"
    
    def normalize_weights(self, request, queryset):
        """Normalize weights in selected schemes"""
        normalized_count = 0
        
        for scheme in queryset:
            objective_weights = scheme.objective_weights.all()
            if objective_weights.exists():
                total_weight = sum(ow.weight for ow in objective_weights)
                if total_weight > 0:
                    for weight_obj in objective_weights:
                        weight_obj.weight = weight_obj.weight / total_weight
                        weight_obj.save()
                    normalized_count += 1
        
        self.message_user(request, f'Weights normalized for {normalized_count} schemes.')
    normalize_weights.short_description = "Normalize weights in selected schemes"


@admin.register(ObjectiveWeight)
class ObjectiveWeightAdmin(admin.ModelAdmin):
    """
    Admin interface for objective weights
    """
    list_display = ['scheme', 'objective', 'weight']
    list_filter = ['scheme__is_active', 'scheme', 'objective__is_active']
    search_fields = ['scheme__name', 'objective__name']
    ordering = ['scheme__name', 'objective__order']
    
    autocomplete_fields = ['scheme', 'objective']
    
    fieldsets = (
        ('Weight Assignment', {
            'fields': ('scheme', 'objective', 'weight')
        }),
    )


@admin.register(IndicatorWeight)
class IndicatorWeightAdmin(admin.ModelAdmin):
    """
    Admin interface for indicator weights
    """
    list_display = ['objective', 'indicator', 'weight']
    list_filter = ['objective__is_active', 'objective', 'indicator__is_active']
    search_fields = ['objective__name', 'indicator__name']
    ordering = ['objective__order', 'weight']
    
    autocomplete_fields = ['objective', 'indicator']
    
    fieldsets = (
        ('Weight Assignment', {
            'fields': ('objective', 'indicator', 'weight')
        }),
    )


@admin.register(AssessmentPeriod)
class AssessmentPeriodAdmin(admin.ModelAdmin):
    """
    Admin interface for assessment periods
    """
    list_display = [
        'name', 'period_type', 'start_date', 'end_date', 
        'is_active', 'is_current', 'duration_days', 'period_description'
    ]
    list_filter = ['period_type', 'is_active', 'is_current', 'start_date']
    search_fields = ['name', 'description']
    ordering = ['-start_date']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'description', 'period_type', 'is_active', 'is_current')
        }),
        ('Date Range', {
            'fields': ('start_date', 'end_date'),
            'description': 'Set the start and end dates for this assessment period. For quarterly periods, ensure the dates align with calendar quarters.'
        }),
        ('Period Details', {
            'fields': ('fiscal_year', 'quarter', 'month'),
            'description': 'Optional fields to help categorize the period. These are automatically populated based on the date range.',
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ['duration_days', 'period_description']
    
    def duration_days(self, obj):
        """Calculate duration in days"""
        if obj.start_date and obj.end_date:
            return (obj.end_date - obj.start_date).days + 1
        return '-'
    duration_days.short_description = 'Duration (Days)'
    
    def period_description(self, obj):
        """Generate a human-readable description of the period"""
        if obj.period_type == 'Quarterly':
            return f"Q{obj.quarter} {obj.fiscal_year}" if obj.quarter and obj.fiscal_year else f"Quarterly {obj.start_date.year}"
        elif obj.period_type == 'Yearly':
            return f"FY {obj.fiscal_year}" if obj.fiscal_year else f"Year {obj.start_date.year}"
        elif obj.period_type == 'Monthly':
            return f"{obj.start_date.strftime('%B %Y')}"
        return obj.name
    period_description.short_description = 'Period Description'
    
    actions = ['activate_periods', 'deactivate_periods', 'set_as_current', 'duplicate_periods']
    
    def activate_periods(self, request, queryset):
        """Activate selected periods"""
        updated = queryset.update(is_active=True)
        self.message_user(request, f'{updated} assessment periods have been activated.')
    activate_periods.short_description = "Activate selected periods"
    
    def deactivate_periods(self, request, queryset):
        """Deactivate selected periods"""
        updated = queryset.update(is_active=False)
        self.message_user(request, f'{updated} assessment periods have been deactivated.')
    deactivate_periods.short_description = "Deactivate selected periods"
    
    def set_as_current(self, request, queryset):
        """Set selected period as current"""
        if queryset.count() != 1:
            self.message_user(request, 'Please select exactly one period to set as current.', level='ERROR')
            return
        
        # Clear current flag from all other periods
        AssessmentPeriod.objects.filter(is_current=True).update(is_current=False)
        
        period = queryset.first()
        period.is_current = True
        period.save()
        
        self.message_user(request, f'{period.name} has been set as the current assessment period.')
    set_as_current.short_description = "Set as current period"
    
    def duplicate_periods(self, request, queryset):
        """Duplicate selected periods"""
        duplicated_count = 0
        
        for period in queryset:
            # Create a copy with modified dates
            new_period = AssessmentPeriod.objects.create(
                name=f"{period.name} (Copy)",
                description=period.description,
                period_type=period.period_type,
                start_date=period.start_date + timedelta(days=365),  # Add one year
                end_date=period.end_date + timedelta(days=365),
                is_active=False,  # Start as inactive
                is_current=False
            )
            duplicated_count += 1
        
        self.message_user(request, f'{duplicated_count} assessment periods have been duplicated.')
    duplicate_periods.short_description = "Duplicate selected periods"


@admin.register(SystemConfiguration)
class SystemConfigurationAdmin(admin.ModelAdmin):
    """
    Admin interface for system configurations
    """
    list_display = [
        'key', 'config_type', 'is_active', 'value_preview', 'created_at'
    ]
    list_filter = ['config_type', 'is_active', 'created_at']
    search_fields = ['key', 'description']
    ordering = ['config_type', 'key']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('key', 'config_type', 'is_active')
        }),
        ('Configuration', {
            'fields': ('value', 'description')
        }),
    )
    
    def value_preview(self, obj):
        """Show preview of configuration value"""
        value = obj.value
        if len(value) > 50:
            return f"{value[:50]}..."
        return value
    value_preview.short_description = 'Value Preview'
    
    actions = ['activate_configs', 'deactivate_configs']
    
    def activate_configs(self, request, queryset):
        """Activate selected configurations"""
        updated = queryset.update(is_active=True)
        self.message_user(request, f'{updated} configurations have been activated.')
    activate_configs.short_description = "Activate selected configurations"
    
    def deactivate_configs(self, request, queryset):
        """Deactivate selected configurations"""
        updated = queryset.update(is_active=False)
        self.message_user(request, f'{updated} configurations have been deactivated.')
    deactivate_configs.short_description = "Deactivate selected configurations"
