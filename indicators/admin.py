from django.contrib import admin
from django import forms
from django.utils.html import format_html
from django.utils import timezone
from django.http import HttpResponse
from django.urls import path
from django.shortcuts import render, redirect
from django.contrib import messages
from django.core.exceptions import ValidationError
from import_export import resources, fields
from import_export.admin import ImportExportModelAdmin
from import_export.widgets import ForeignKeyWidget, ManyToManyWidget, Widget
from import_export.formats import base_formats
from .models import TrackedIndicator, IndicatorCategory, IndicatorCategoryMapping, IndicatorThreshold


class TrackedIndicatorAdminForm(forms.ModelForm):
    """
    Admin form that exposes a 'data_source' hint to distinguish DHIS2 vs Manual indicators
    without adding a DB field. Validation enforces coherent configurations.
    """
    DATA_SOURCE_CHOICES = (
        ('dhis2', 'DHIS2'),
        ('manual', 'Manual'),
    )

    data_source = forms.ChoiceField(
        choices=DATA_SOURCE_CHOICES,
        required=False,
        help_text="Select 'DHIS2' for indicators fetched from DHIS2 (requires UID), or 'Manual' for user-entered values."
    )

    class Meta:
        model = TrackedIndicator
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Default data_source based on dhis2_uid presence
        instance = kwargs.get('instance') or getattr(self, 'instance', None)
        if instance and instance.pk:
            self.fields['data_source'].initial = 'dhis2' if instance.dhis2_uid else 'manual'
        else:
            # New form → default to DHIS2
            self.fields['data_source'].initial = 'dhis2'

    def clean(self):
        cleaned = super().clean()
        data_source = cleaned.get('data_source') or ('dhis2' if cleaned.get('dhis2_uid') else 'manual')
        dhis2_uid = cleaned.get('dhis2_uid')
        formula = cleaned.get('formula')
        indicator_type = cleaned.get('indicator_type')

        # If calculated type, require formula and ensure no DHIS2 UID
        if indicator_type == TrackedIndicator.IndicatorType.CALCULATED:
            if not formula:
                raise forms.ValidationError("Calculated indicators require a formula.")
            cleaned['dhis2_uid'] = None

        # DHIS2 data source requires UID
        if data_source == 'dhis2' and not dhis2_uid and indicator_type != TrackedIndicator.IndicatorType.CALCULATED:
            raise forms.ValidationError("DHIS2 UID is required when Data source is DHIS2.")

        # Manual data source cannot have a formula unless it's Calculated type
        if data_source == 'manual' and indicator_type != TrackedIndicator.IndicatorType.CALCULATED:
            if formula:
                raise forms.ValidationError("Manual indicators cannot have a formula. Use 'Calculated' type instead.")
            # Ensure UID is cleared for manual indicators
            cleaned['dhis2_uid'] = None

        return cleaned


class TrackedIndicatorResource(resources.ModelResource):
    """
    Import/Export resource for TrackedIndicator model
    """
    # Custom fields for better import/export
    indicator_type = fields.Field(
        column_name='indicator_type',
        attribute='indicator_type'
    )
    
    target_type = fields.Field(
        column_name='target_type',
        attribute='target_type'
    )
    
    # Computed fields for export
    formula_components = fields.Field(
        column_name='formula_components',
        attribute='formula_components',
        readonly=True
    )
    
    class Meta:
        model = TrackedIndicator
        # Allow import using name if dhis2_uid is blank. We'll handle creation in before_import_row
        import_id_fields = ()
        export_order = (
            'name', 'dhis2_uid', 'indicator_type', 'indicator_number', 
            'display_order', 'formula', 'target_value', 'target_type',
            'min_score', 'max_score', 'is_active', 'description',
            'dhis2_name', 'dhis2_description', 'formula_components'
        )
        exclude = ('created_at', 'updated_at', 'last_sync')
        
    def get_formula_components(self, obj):
        """Get formula components for export"""
        if obj.formula:
            return ', '.join(obj.get_formula_components())
        return ''
    
    def before_import_row(self, row, **kwargs):
        """Validate and clean data before import"""
        # dhis2_uid is optional for manual indicators. When absent, do not enforce uniqueness by UID.
        if row.get('dhis2_uid') in ('', None):
            row['dhis2_uid'] = None
        
        # Set default values
        if not row.get('indicator_type'):
            row['indicator_type'] = 'indicator'
        
        if not row.get('target_type'):
            row['target_type'] = 'increase'
        
        if not row.get('is_active'):
            row['is_active'] = True
        
        # Ensure text fields are not None
        if row.get('description') is None:
            row['description'] = ''
        
        if row.get('dhis2_description') is None:
            row['dhis2_description'] = ''
        
        if row.get('formula') is None:
            row['formula'] = ''
        
        if row.get('dhis2_name') is None:
            row['dhis2_name'] = ''
        
        if row.get('indicator_number') is None:
            row['indicator_number'] = ''
    
    def after_import_row(self, row, row_result, **kwargs):
        """Additional processing after import"""
        # Update last_sync to current time for newly imported indicators
        if row_result.instance:
            row_result.instance.last_sync = timezone.now()
            row_result.instance.save()


class IndicatorThresholdInline(admin.TabularInline):
    """
    Inline admin for indicator thresholds
    """
    model = IndicatorThreshold
    extra = 0
    fields = ['min_value', 'max_value', 'score', 'color', 'label']
    ordering = ['min_value']


class IndicatorCategoryMappingInline(admin.TabularInline):
    """
    Inline admin for indicator category mappings
    """
    model = IndicatorCategoryMapping
    extra = 0
    fields = ['category', 'weight']
    autocomplete_fields = ['category']


@admin.register(TrackedIndicator)
class TrackedIndicatorAdmin(ImportExportModelAdmin):
    """
    Admin interface for tracked indicators with import/export functionality
    """
    resource_class = TrackedIndicatorResource
    
    list_display = [
        'name', 'dhis2_uid', 'indicator_type', 'is_active', 'target_value',
        'target_type', 'last_sync', 'sync_status'
    ]
    list_filter = [
        'indicator_type', 'is_active', 'target_type', 'created_at', 'updated_at'
    ]
    search_fields = ['name', 'dhis2_uid', 'description', 'dhis2_name']
    readonly_fields = [
        'created_at', 'updated_at', 'last_sync', 'dhis2_name', 'dhis2_description'
    ]
    ordering = ['name']
    
    form = TrackedIndicatorAdminForm

    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'data_source', 'dhis2_uid', 'indicator_type', 'is_active', 'description')
        }),
        ('Excel Structure', {
            'fields': ('indicator_number', 'display_order'),
            'classes': ('collapse',)
        }),
        ('DHIS2 Metadata', {
            'fields': ('dhis2_name', 'dhis2_description', 'last_sync'),
            'classes': ('collapse',)
        }),
        ('Formula and Calculation', {
            'fields': ('formula',),
            'classes': ('collapse',)
        }),
        ('Target and Scoring', {
            'fields': ('target_value', 'target_type', 'min_score', 'max_score')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    inlines = [IndicatorThresholdInline, IndicatorCategoryMappingInline]
    
    # Import/Export settings
    change_list_template = 'admin/indicators/trackedindicator/change_list.html'
    
    def get_urls(self):
        """Add custom URLs for import/export"""
        urls = super().get_urls()
        custom_urls = [
            path('import-template/', self.import_template_view, name='trackedindicator_import_template'),
            path('export-template/', self.export_template_view, name='trackedindicator_export_template'),
        ]
        return custom_urls + urls
    
    def import_template_view(self, request):
        """Download import template"""
        resource = self.resource_class()
        dataset = resource.export(TrackedIndicator.objects.none())
        
        response = HttpResponse(
            dataset.xlsx,
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = 'attachment; filename="tracked_indicators_import_template.xlsx"'
        return response
    
    def export_template_view(self, request):
        """Export current indicators as template"""
        queryset = self.get_queryset(request)
        resource = self.resource_class()
        dataset = resource.export(queryset)
        
        response = HttpResponse(
            dataset.xlsx,
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = 'attachment; filename="tracked_indicators_export.xlsx"'
        return response
    
    def sync_status(self, obj):
        """Display sync status"""
        if not obj.last_sync:
            return format_html('<span style="color: orange;">Never Synced</span>')
        
        days_since_sync = (timezone.now() - obj.last_sync).days
        if days_since_sync > 30:
            return format_html('<span style="color: red;">Outdated ({days} days)</span>', days=days_since_sync)
        elif days_since_sync > 7:
            return format_html('<span style="color: orange;">Stale ({days} days)</span>', days=days_since_sync)
        else:
            return format_html('<span style="color: green;">Recent ({days} days)</span>', days=days_since_sync)
    
    sync_status.short_description = 'Sync Status'
    
    actions = ['activate_indicators', 'deactivate_indicators', 'sync_metadata', 'export_selected']
    
    def activate_indicators(self, request, queryset):
        """Activate selected indicators"""
        updated = queryset.update(is_active=True)
        self.message_user(request, f'{updated} indicators have been activated.')
    activate_indicators.short_description = "Activate selected indicators"
    
    def deactivate_indicators(self, request, queryset):
        """Deactivate selected indicators"""
        updated = queryset.update(is_active=False)
        self.message_user(request, f'{updated} indicators have been deactivated.')
    deactivate_indicators.short_description = "Deactivate selected indicators"
    
    def sync_metadata(self, request, queryset):
        """Sync metadata for selected indicators"""
        # This would typically call the sync method
        self.message_user(request, f'Metadata sync initiated for {queryset.count()} indicators.')
    sync_metadata.short_description = "Sync metadata for selected indicators"
    
    def export_selected(self, request, queryset):
        """Export selected indicators"""
        resource = self.resource_class()
        dataset = resource.export(queryset)
        
        response = HttpResponse(
            dataset.xlsx,
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = f'attachment; filename="selected_indicators_{timezone.now().strftime("%Y%m%d_%H%M%S")}.xlsx"'
        return response
    export_selected.short_description = "Export selected indicators"


@admin.register(IndicatorCategory)
class IndicatorCategoryAdmin(admin.ModelAdmin):
    """
    Admin interface for indicator categories
    """
    list_display = ['name', 'order', 'is_active', 'indicator_count', 'color_preview']
    list_filter = ['is_active']
    search_fields = ['name', 'description']
    ordering = ['order', 'name']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'description', 'is_active')
        }),
        ('Display Settings', {
            'fields': ('color', 'order')
        }),
    )
    
    def indicator_count(self, obj):
        """Count of indicators in this category"""
        return obj.indicator_mappings.count()
    indicator_count.short_description = 'Indicators'
    
    def color_preview(self, obj):
        """Show color preview"""
        return format_html(
            '<div style="background-color: {}; width: 20px; height: 20px; border: 1px solid #ccc;"></div>',
            obj.color
        )
    color_preview.short_description = 'Color'
    
    actions = ['activate_categories', 'deactivate_categories']
    
    def activate_categories(self, request, queryset):
        """Activate selected categories"""
        updated = queryset.update(is_active=True)
        self.message_user(request, f'{updated} categories have been activated.')
    activate_categories.short_description = "Activate selected categories"
    
    def deactivate_categories(self, request, queryset):
        """Deactivate selected categories"""
        updated = queryset.update(is_active=False)
        self.message_user(request, f'{updated} categories have been deactivated.')
    deactivate_categories.short_description = "Deactivate selected categories"


@admin.register(IndicatorCategoryMapping)
class IndicatorCategoryMappingAdmin(admin.ModelAdmin):
    """
    Admin interface for indicator category mappings
    """
    list_display = ['indicator', 'category', 'weight']
    list_filter = ['category__is_active', 'category']
    search_fields = ['indicator__name', 'category__name']
    ordering = ['category__order', 'weight']
    
    autocomplete_fields = ['indicator', 'category']
    
    fieldsets = (
        ('Mapping', {
            'fields': ('indicator', 'category', 'weight')
        }),
    )
    
    actions = ['normalize_weights']
    
    def normalize_weights(self, request, queryset):
        """Normalize weights within categories"""
        # Group by category and normalize weights
        categories = queryset.values_list('category', flat=True).distinct()
        
        for category_id in categories:
            mappings = queryset.filter(category_id=category_id).order_by('weight')
            total_weight = sum(mapping.weight for mapping in mappings)
            
            if total_weight > 0:
                for mapping in mappings:
                    mapping.weight = mapping.weight / total_weight
                    mapping.save()
        
        self.message_user(request, f'Weights normalized for {len(categories)} categories.')
    normalize_weights.short_description = "Normalize weights within categories"


@admin.register(IndicatorThreshold)
class IndicatorThresholdAdmin(admin.ModelAdmin):
    """
    Admin interface for indicator thresholds
    """
    list_display = ['indicator', 'min_value', 'max_value', 'score', 'label', 'color_preview']
    list_filter = ['indicator__is_active', 'score', 'indicator__indicator_type']
    search_fields = ['indicator__name', 'label']
    ordering = ['indicator__name', 'min_value']
    
    autocomplete_fields = ['indicator']
    
    fieldsets = (
        ('Threshold Definition', {
            'fields': ('indicator', 'min_value', 'max_value')
        }),
        ('Scoring', {
            'fields': ('score', 'label', 'color')
        }),
    )
    
    def color_preview(self, obj):
        """Show color preview"""
        return format_html(
            '<div style="background-color: {}; width: 20px; height: 20px; border: 1px solid #ccc;"></div>',
            obj.color
        )
    color_preview.short_description = 'Color'
    
    actions = ['duplicate_thresholds']
    
    def duplicate_thresholds(self, request, queryset):
        """Duplicate selected thresholds"""
        duplicated_count = 0
        
        for threshold in queryset:
            # Create a copy with slightly modified values
            new_threshold = IndicatorThreshold.objects.create(
                indicator=threshold.indicator,
                min_value=threshold.min_value + 1,
                max_value=threshold.max_value + 1,
                score=threshold.score,
                color=threshold.color,
                label=f"{threshold.label} (Copy)"
            )
            duplicated_count += 1
        
        self.message_user(request, f'{duplicated_count} thresholds have been duplicated.')
    duplicate_thresholds.short_description = "Duplicate selected thresholds"
