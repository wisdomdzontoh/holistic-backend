from rest_framework import serializers
from .models import (
    DataSyncLog, IndicatorData, IndicatorScore, ObjectiveScore, SectorScore
)
from indicators.models import TrackedIndicator
from configurations.models import Objective, AssessmentPeriod


class DataSyncLogSerializer(serializers.ModelSerializer):
    """
    Serializer for data sync logs
    """
    sync_type_display = serializers.CharField(source='get_sync_type_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    duration_formatted = serializers.SerializerMethodField()
    
    class Meta:
        model = DataSyncLog
        fields = [
            'id', 'sync_type', 'sync_type_display', 'status', 'status_display',
            'dhis2_instance_url', 'dhis2_user', 'period_start', 'period_end',
            'org_unit_ids', 'indicator_uids', 'total_indicators', 'successful_indicators',
            'failed_indicators', 'total_data_points', 'error_message', 'error_details',
            'started_at', 'completed_at', 'duration_seconds', 'duration_formatted'
        ]
        read_only_fields = [
            'started_at', 'completed_at', 'duration_seconds', 'duration_formatted'
        ]
    
    def get_duration_formatted(self, obj):
        """Format duration in human-readable format"""
        if obj.duration_seconds is None:
            return None
        
        minutes = obj.duration_seconds // 60
        seconds = obj.duration_seconds % 60
        
        if minutes > 0:
            return f"{minutes}m {seconds}s"
        else:
            return f"{seconds}s"


class IndicatorDataSerializer(serializers.ModelSerializer):
    """
    Serializer for indicator data
    """
    indicator_name = serializers.CharField(source='indicator.name', read_only=True)
    indicator_uid = serializers.CharField(source='indicator.dhis2_uid', read_only=True)
    calculated_value = serializers.DecimalField(max_digits=15, decimal_places=4, read_only=True)
    
    class Meta:
        model = IndicatorData
        fields = [
            'id', 'indicator', 'indicator_name', 'indicator_uid', 'org_unit_id',
            'org_unit_name', 'period', 'value', 'numerator', 'denominator',
            'calculated_value', 'sync_log', 'created_at', 'updated_at',
            'dhis2_response'
        ]
        read_only_fields = ['created_at', 'updated_at']


class IndicatorScoreSerializer(serializers.ModelSerializer):
    """
    Serializer for indicator scores
    """
    indicator_name = serializers.CharField(source='indicator.name', read_only=True)
    indicator_uid = serializers.CharField(source='indicator.dhis2_uid', read_only=True)
    objective_name = serializers.CharField(source='objective.name', read_only=True)
    objective_code = serializers.CharField(source='objective.code', read_only=True)
    assessment_period_name = serializers.CharField(source='assessment_period.name', read_only=True)
    scoring_rule_name = serializers.CharField(source='scoring_rule.name', read_only=True)
    override_user_name = serializers.CharField(source='override_user.dhis2_username', read_only=True)
    
    class Meta:
        model = IndicatorScore
        fields = [
            'id', 'indicator', 'indicator_name', 'indicator_uid', 'objective',
            'objective_name', 'objective_code', 'org_unit_id', 'org_unit_name',
            'assessment_period', 'assessment_period_name', 'current_value',
            'previous_value', 'target_value', 'target_gap', 'percent_change',
            'score', 'score_color', 'score_label', 'scoring_rule', 'scoring_rule_name',
            'weight', 'is_manual_override', 'override_reason', 'override_user',
            'override_user_name', 'created_at', 'updated_at', 'last_calculated'
        ]
        read_only_fields = [
            'created_at', 'updated_at', 'last_calculated', 'target_gap',
            'percent_change', 'score', 'score_color', 'score_label'
        ]


class ObjectiveScoreSerializer(serializers.ModelSerializer):
    """
    Serializer for objective scores
    """
    objective_name = serializers.CharField(source='objective.name', read_only=True)
    objective_code = serializers.CharField(source='objective.code', read_only=True)
    assessment_period_name = serializers.CharField(source='assessment_period.name', read_only=True)
    indicator_scores = serializers.SerializerMethodField()
    
    class Meta:
        model = ObjectiveScore
        fields = [
            'id', 'objective', 'objective_name', 'objective_code', 'org_unit_id',
            'org_unit_name', 'assessment_period', 'assessment_period_name',
            'median_score', 'weighted_score', 'final_score', 'score_color',
            'score_label', 'total_indicators', 'scored_indicators', 'total_weight',
            'created_at', 'updated_at', 'last_calculated', 'indicator_scores'
        ]
        read_only_fields = [
            'created_at', 'updated_at', 'last_calculated', 'median_score',
            'weighted_score', 'final_score', 'score_color', 'score_label',
            'total_indicators', 'scored_indicators', 'total_weight'
        ]
    
    def get_indicator_scores(self, obj):
        """Get related indicator scores"""
        indicator_scores = obj.indicator_scores.all()
        return IndicatorScoreSerializer(indicator_scores, many=True).data


class SectorScoreSerializer(serializers.ModelSerializer):
    """
    Serializer for sector scores
    """
    assessment_period_name = serializers.CharField(source='assessment_period.name', read_only=True)
    objective_scores = serializers.SerializerMethodField()
    
    class Meta:
        model = SectorScore
        fields = [
            'id', 'org_unit_id', 'org_unit_name', 'assessment_period',
            'assessment_period_name', 'overall_score', 'score_color', 'score_label',
            'total_objectives', 'scored_objectives', 'total_indicators',
            'scored_indicators', 'created_at', 'updated_at', 'last_calculated',
            'objective_scores'
        ]
        read_only_fields = [
            'created_at', 'updated_at', 'last_calculated', 'overall_score',
            'score_color', 'score_label', 'total_objectives', 'scored_objectives',
            'total_indicators', 'scored_indicators'
        ]
    
    def get_objective_scores(self, obj):
        """Get related objective scores"""
        objective_scores = ObjectiveScore.objects.filter(
            org_unit_id=obj.org_unit_id,
            assessment_period=obj.assessment_period
        )
        return ObjectiveScoreSerializer(objective_scores, many=True).data


# Create/Update serializers
class DataSyncLogCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating data sync logs
    """
    class Meta:
        model = DataSyncLog
        fields = [
            'sync_type', 'dhis2_instance_url', 'dhis2_user', 'period_start',
            'period_end', 'org_unit_ids', 'indicator_uids'
        ]


class IndicatorScoreCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating indicator scores
    """
    class Meta:
        model = IndicatorScore
        fields = [
            'indicator', 'objective', 'org_unit_id', 'org_unit_name',
            'assessment_period', 'current_value', 'previous_value', 'target_value',
            'weight', 'is_manual_override', 'override_reason'
        ]
    
    def validate(self, data):
        """Validate indicator score data"""
        # Check if indicator is assigned to the objective
        indicator = data.get('indicator')
        objective = data.get('objective')
        
        if indicator and objective:
            # Check if there's a weight mapping
            from configurations.models import IndicatorWeight
            weight_mapping = IndicatorWeight.objects.filter(
                indicator=indicator,
                objective=objective
            ).first()
            
            if weight_mapping:
                data['weight'] = weight_mapping.weight
            else:
                # Use default weight if no mapping exists
                data['weight'] = 1.0
        
        return data


class ObjectiveScoreCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating objective scores
    """
    class Meta:
        model = ObjectiveScore
        fields = [
            'objective', 'org_unit_id', 'org_unit_name', 'assessment_period'
        ]


class SectorScoreCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating sector scores
    """
    class Meta:
        model = SectorScore
        fields = [
            'org_unit_id', 'org_unit_name', 'assessment_period'
        ]


# Bulk operation serializers
class BulkScoreCalculationSerializer(serializers.Serializer):
    """
    Serializer for bulk score calculation
    """
    org_unit_ids = serializers.ListField(
        child=serializers.CharField(max_length=255),
        required=False,
        help_text="List of org unit IDs to calculate scores for"
    )
    assessment_period_id = serializers.IntegerField(
        required=False,
        help_text="Assessment period ID"
    )
    objective_ids = serializers.ListField(
        child=serializers.IntegerField(),
        required=False,
        help_text="List of objective IDs to calculate scores for"
    )
    indicator_ids = serializers.ListField(
        child=serializers.IntegerField(),
        required=False,
        help_text="List of indicator IDs to calculate scores for"
    )
    force_recalculate = serializers.BooleanField(
        default=False,
        help_text="Force recalculation of existing scores"
    )


class DataSyncRequestSerializer(serializers.Serializer):
    """
    Serializer for data sync requests
    """
    sync_type = serializers.ChoiceField(
        choices=DataSyncLog.SyncType.choices,
        default=DataSyncLog.SyncType.FULL
    )
    dhis2_instance_url = serializers.URLField(
        required=False,
        help_text="DHIS2 instance URL (uses session default if not provided)"
    )
    period_start = serializers.DateField(
        required=False,
        help_text="Start date for data sync"
    )
    period_end = serializers.DateField(
        required=False,
        help_text="End date for data sync"
    )
    org_unit_ids = serializers.ListField(
        child=serializers.CharField(max_length=255),
        required=False,
        help_text="List of org unit IDs to sync"
    )
    indicator_uids = serializers.ListField(
        child=serializers.CharField(max_length=255),
        required=False,
        help_text="List of indicator UIDs to sync"
    )
    calculate_scores = serializers.BooleanField(
        default=True,
        help_text="Calculate scores after data sync"
    )


class ScoreOverrideSerializer(serializers.Serializer):
    """
    Serializer for manual score overrides
    """
    score = serializers.IntegerField(
        min_value=-5,
        max_value=5,
        help_text="Manual score value"
    )
    reason = serializers.CharField(
        max_length=500,
        help_text="Reason for the override"
    )
    score_color = serializers.CharField(
        max_length=7,
        required=False,
        help_text="Color for the score (hex format)"
    )
    score_label = serializers.CharField(
        max_length=50,
        required=False,
        help_text="Label for the score"
    )


# Dashboard and reporting serializers
class DashboardSummarySerializer(serializers.Serializer):
    """
    Serializer for dashboard summary data
    """
    org_unit_id = serializers.CharField(max_length=255)
    org_unit_name = serializers.CharField(max_length=255)
    assessment_period_name = serializers.CharField(max_length=255)
    sector_score = serializers.DecimalField(max_digits=5, decimal_places=2)
    sector_color = serializers.CharField(max_length=7)
    sector_label = serializers.CharField(max_length=50)
    objective_count = serializers.IntegerField()
    indicator_count = serializers.IntegerField()
    last_updated = serializers.DateTimeField()


class ObjectiveDashboardSerializer(serializers.Serializer):
    """
    Serializer for objective dashboard data
    """
    objective_id = serializers.IntegerField()
    objective_name = serializers.CharField(max_length=255)
    objective_code = serializers.CharField(max_length=50)
    objective_color = serializers.CharField(max_length=7)
    score = serializers.DecimalField(max_digits=5, decimal_places=2)
    score_color = serializers.CharField(max_length=7)
    score_label = serializers.CharField(max_length=50)
    indicator_count = serializers.IntegerField()
    trend_direction = serializers.CharField(max_length=20)  # 'up', 'down', 'stable'


class IndicatorDashboardSerializer(serializers.Serializer):
    """
    Serializer for indicator dashboard data
    """
    indicator_id = serializers.IntegerField()
    indicator_name = serializers.CharField(max_length=255)
    indicator_uid = serializers.CharField(max_length=255)
    objective_name = serializers.CharField(max_length=255)
    current_value = serializers.DecimalField(max_digits=15, decimal_places=4)
    target_value = serializers.DecimalField(max_digits=15, decimal_places=4)
    score = serializers.IntegerField()
    score_color = serializers.CharField(max_length=7)
    score_label = serializers.CharField(max_length=50)
    trend_direction = serializers.CharField(max_length=20)
    weight = serializers.DecimalField(max_digits=5, decimal_places=2)


class AssessmentReportSerializer(serializers.Serializer):
    """
    Serializer for assessment reports
    """
    report_id = serializers.CharField(max_length=255)
    org_unit_id = serializers.CharField(max_length=255)
    org_unit_name = serializers.CharField(max_length=255)
    assessment_period_name = serializers.CharField(max_length=255)
    sector_score = serializers.DecimalField(max_digits=5, decimal_places=2)
    sector_color = serializers.CharField(max_length=7)
    sector_label = serializers.CharField(max_length=50)
    objectives = ObjectiveDashboardSerializer(many=True)
    indicators = IndicatorDashboardSerializer(many=True)
    generated_at = serializers.DateTimeField()
    generated_by = serializers.CharField(max_length=255) 


class HolisticAssessmentRequestSerializer(serializers.Serializer):
    """
    Serializer for holistic assessment data fetch requests
    """
    org_unit_ids = serializers.ListField(
        child=serializers.CharField(max_length=255),
        required=True,
        help_text="List of organization unit IDs"
    )
    periods = serializers.ListField(
        required=True,
        help_text="List of periods (e.g., ['2021', '2022', '2023'])"
    )
    
    def validate_periods(self, value):
        """Validate and normalize periods"""
        normalized_periods = []
        for period in value:
            if isinstance(period, dict):
                # Extract period code from object format
                if 'code' in period:
                    normalized_periods.append(str(period['code']))
                elif 'name' in period:
                    normalized_periods.append(str(period['name']))
                else:
                    raise serializers.ValidationError(f"Period object must contain 'code' or 'name': {period}")
            else:
                # Already a string
                normalized_periods.append(str(period))
        return normalized_periods
    indicator_uids = serializers.ListField(
        child=serializers.CharField(max_length=255),
        required=False,
        help_text="List of indicator UIDs to fetch (optional - uses all active if not provided)"
    )
    include_calculations = serializers.BooleanField(
        default=True,
        help_text="Whether to include score calculations"
    )
    include_targets = serializers.BooleanField(
        default=True,
        help_text="Whether to include target values"
    )

class HolisticAssessmentSaveSerializer(serializers.Serializer):
    """
    Serializer for saving holistic assessments
    """
    name = serializers.CharField(
        max_length=255,
        required=True,
        help_text="Name of the assessment"
    )
    org_unit_id = serializers.CharField(
        max_length=255,
        required=True,
        help_text="Organization unit ID"
    )
    org_unit_name = serializers.CharField(
        max_length=255,
        required=True,
        help_text="Organization unit name"
    )
    periods = serializers.ListField(
        child=serializers.CharField(max_length=20),
        required=True,
        help_text="List of periods used in the assessment"
    )
    indicator_data = serializers.DictField(
        required=True,
        help_text="Indicator data with values for each period"
    )
    calculated_scores = serializers.DictField(
        required=False,
        help_text="Calculated scores and grades"
    )
    user_notes = serializers.CharField(
        required=False,
        allow_blank=True,
        help_text="User notes and comments"
    )
    metadata = serializers.DictField(
        required=False,
        help_text="Additional metadata about the assessment"
    ) 