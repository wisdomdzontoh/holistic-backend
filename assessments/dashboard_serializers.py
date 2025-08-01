from rest_framework import serializers
from .models import IndicatorScore, ObjectiveScore, SectorScore
from indicators.models import TrackedIndicator
from configurations.models import Objective, AssessmentPeriod
from organisation.models import OrgUnit


class DashboardSummarySerializer(serializers.Serializer):
    """
    Serializer for dashboard summary data
    """
    assessment_period = serializers.CharField()
    total_org_units = serializers.IntegerField()
    org_units_with_scores = serializers.IntegerField()
    average_score = serializers.FloatField()
    max_score = serializers.FloatField()
    min_score = serializers.FloatField()
    performance_distribution = serializers.DictField()
    sector_scores = serializers.ListField(child=serializers.DictField())


class ObjectiveDashboardSerializer(serializers.Serializer):
    """
    Serializer for objective dashboard data
    """
    assessment_period = serializers.CharField()
    objectives = serializers.ListField(child=serializers.DictField())


class IndicatorDashboardSerializer(serializers.Serializer):
    """
    Serializer for indicator dashboard data
    """
    assessment_period = serializers.CharField()
    objective_id = serializers.IntegerField(required=False, allow_null=True)
    indicators = serializers.ListField(child=serializers.DictField())


class OrgUnitPerformanceSerializer(serializers.Serializer):
    """
    Serializer for org unit performance data
    """
    org_unit = serializers.DictField()
    assessment_period = serializers.CharField()
    sector_score = serializers.DictField()
    objectives = serializers.ListField(child=serializers.DictField())
    indicators = serializers.ListField(child=serializers.DictField())


class TrendAnalysisSerializer(serializers.Serializer):
    """
    Serializer for trend analysis data
    """
    org_unit_id = serializers.IntegerField()
    periods = serializers.ListField(child=serializers.CharField())
    sector_trend = serializers.ListField(child=serializers.DictField())
    objectives_trend = serializers.DictField()


class PerformanceCategorySerializer(serializers.Serializer):
    """
    Serializer for performance category data
    """
    category = serializers.CharField()
    count = serializers.IntegerField()
    percentage = serializers.FloatField()
    color = serializers.CharField()


class ScoreTrendSerializer(serializers.Serializer):
    """
    Serializer for score trend data
    """
    period = serializers.CharField()
    score = serializers.FloatField(allow_null=True)
    color = serializers.CharField(allow_null=True)
    label = serializers.CharField(allow_null=True)
    trend_direction = serializers.CharField(allow_null=True)


class DashboardFilterSerializer(serializers.Serializer):
    """
    Serializer for dashboard filter parameters
    """
    org_unit_id = serializers.IntegerField(required=False, allow_null=True)
    assessment_period = serializers.CharField(required=False, allow_null=True)
    objective_id = serializers.IntegerField(required=False, allow_null=True)
    indicator_id = serializers.IntegerField(required=False, allow_null=True)
    performance_category = serializers.CharField(required=False, allow_null=True)
    trend_direction = serializers.CharField(required=False, allow_null=True)
    limit = serializers.IntegerField(default=50, min_value=1, max_value=1000)


class DashboardExportSerializer(serializers.Serializer):
    """
    Serializer for dashboard export requests
    """
    dashboard_type = serializers.ChoiceField(choices=[
        'summary', 'objectives', 'indicators', 'performance', 'trend'
    ])
    format = serializers.ChoiceField(choices=['excel', 'csv', 'pdf'], default='excel')
    filters = DashboardFilterSerializer()
    include_charts = serializers.BooleanField(default=True)
    include_details = serializers.BooleanField(default=True)


class DashboardComparisonSerializer(serializers.Serializer):
    """
    Serializer for dashboard comparison data
    """
    comparison_type = serializers.ChoiceField(choices=[
        'org_units', 'periods', 'objectives', 'indicators'
    ])
    primary_data = serializers.DictField()
    comparison_data = serializers.ListField(child=serializers.DictField())
    differences = serializers.ListField(child=serializers.DictField())


class DashboardAlertSerializer(serializers.Serializer):
    """
    Serializer for dashboard alerts
    """
    alert_type = serializers.ChoiceField(choices=[
        'underperforming', 'improving', 'declining', 'threshold_breach'
    ])
    org_unit_id = serializers.IntegerField()
    org_unit_name = serializers.CharField()
    metric_type = serializers.CharField()  # 'sector', 'objective', 'indicator'
    metric_name = serializers.CharField()
    current_score = serializers.FloatField()
    threshold_score = serializers.FloatField()
    severity = serializers.ChoiceField(choices=['low', 'medium', 'high', 'critical'])
    message = serializers.CharField()
    created_at = serializers.DateTimeField()


class DashboardKpiSerializer(serializers.Serializer):
    """
    Serializer for dashboard KPIs
    """
    kpi_name = serializers.CharField()
    kpi_value = serializers.FloatField()
    kpi_unit = serializers.CharField(allow_null=True)
    kpi_trend = serializers.CharField(allow_null=True)
    kpi_color = serializers.CharField()
    kpi_label = serializers.CharField()
    kpi_description = serializers.CharField(allow_null=True)


class DashboardHeatmapSerializer(serializers.Serializer):
    """
    Serializer for dashboard heatmap data
    """
    org_units = serializers.ListField(child=serializers.CharField())
    metrics = serializers.ListField(child=serializers.CharField())
    data = serializers.ListField(child=serializers.ListField(child=serializers.FloatField()))
    colors = serializers.ListField(child=serializers.ListField(child=serializers.CharField()))
    labels = serializers.ListField(child=serializers.ListField(child=serializers.CharField()))


class DashboardDrilldownSerializer(serializers.Serializer):
    """
    Serializer for dashboard drilldown data
    """
    drilldown_level = serializers.CharField()  # 'org_unit', 'objective', 'indicator'
    drilldown_id = serializers.IntegerField()
    drilldown_name = serializers.CharField()
    parent_data = serializers.DictField()
    child_data = serializers.ListField(child=serializers.DictField())
    drilldown_path = serializers.ListField(child=serializers.DictField())


class DashboardRealTimeSerializer(serializers.Serializer):
    """
    Serializer for real-time dashboard updates
    """
    update_type = serializers.ChoiceField(choices=[
        'score_update', 'new_data', 'alert', 'sync_complete'
    ])
    org_unit_id = serializers.IntegerField()
    metric_type = serializers.CharField()
    metric_id = serializers.IntegerField()
    old_value = serializers.FloatField(allow_null=True)
    new_value = serializers.FloatField(allow_null=True)
    timestamp = serializers.DateTimeField()
    user = serializers.CharField(allow_null=True)


class DashboardConfigurationSerializer(serializers.Serializer):
    """
    Serializer for dashboard configuration
    """
    dashboard_layout = serializers.DictField()
    visible_widgets = serializers.ListField(child=serializers.CharField())
    default_filters = DashboardFilterSerializer()
    refresh_interval = serializers.IntegerField(default=300)  # seconds
    chart_types = serializers.DictField()
    color_scheme = serializers.CharField(default='default')
    user_preferences = serializers.DictField()


class DashboardWidgetSerializer(serializers.Serializer):
    """
    Serializer for dashboard widget data
    """
    widget_id = serializers.CharField()
    widget_type = serializers.CharField()
    widget_title = serializers.CharField()
    widget_data = serializers.DictField()
    widget_config = serializers.DictField()
    widget_position = serializers.DictField()
    widget_size = serializers.DictField()
    is_visible = serializers.BooleanField(default=True)
    last_updated = serializers.DateTimeField()


class DashboardReportSerializer(serializers.Serializer):
    """
    Serializer for dashboard report generation
    """
    report_type = serializers.ChoiceField(choices=[
        'summary', 'detailed', 'comparative', 'trend', 'custom'
    ])
    report_title = serializers.CharField()
    report_description = serializers.CharField(allow_null=True)
    report_filters = DashboardFilterSerializer()
    report_sections = serializers.ListField(child=serializers.DictField())
    report_format = serializers.ChoiceField(choices=['excel', 'csv', 'pdf', 'html'])
    include_charts = serializers.BooleanField(default=True)
    include_tables = serializers.BooleanField(default=True)
    include_summary = serializers.BooleanField(default=True)
    custom_template = serializers.CharField(allow_null=True)


class DashboardAnalyticsSerializer(serializers.Serializer):
    """
    Serializer for dashboard analytics data
    """
    analytics_type = serializers.ChoiceField(choices=[
        'performance_analysis', 'trend_analysis', 'correlation_analysis', 'predictive_analysis'
    ])
    analysis_period = serializers.CharField()
    analysis_metrics = serializers.ListField(child=serializers.CharField())
    analysis_results = serializers.DictField()
    insights = serializers.ListField(child=serializers.CharField())
    recommendations = serializers.ListField(child=serializers.CharField())
    confidence_level = serializers.FloatField(min_value=0, max_value=1)
    last_updated = serializers.DateTimeField()


class DashboardNotificationSerializer(serializers.Serializer):
    """
    Serializer for dashboard notifications
    """
    notification_id = serializers.CharField()
    notification_type = serializers.ChoiceField(choices=[
        'alert', 'update', 'sync', 'error', 'info'
    ])
    notification_title = serializers.CharField()
    notification_message = serializers.CharField()
    notification_severity = serializers.ChoiceField(choices=[
        'info', 'warning', 'error', 'critical'
    ])
    notification_data = serializers.DictField()
    is_read = serializers.BooleanField(default=False)
    created_at = serializers.DateTimeField()
    expires_at = serializers.DateTimeField(allow_null=True)


class DashboardAccessControlSerializer(serializers.Serializer):
    """
    Serializer for dashboard access control
    """
    user_id = serializers.IntegerField()
    accessible_org_units = serializers.ListField(child=serializers.IntegerField())
    accessible_objectives = serializers.ListField(child=serializers.IntegerField())
    accessible_indicators = serializers.ListField(child=serializers.IntegerField())
    permissions = serializers.DictField()
    access_level = serializers.CharField()
    last_access = serializers.DateTimeField()
    session_expires = serializers.DateTimeField() 