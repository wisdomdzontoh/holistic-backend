from rest_framework import serializers
from .models import (
    DataSyncLog, IndicatorData, IndicatorScore, ObjectiveScore, 
    SectorScore, SavedAssessment, AuditLog, ConflictResolution, MilestoneScore
)
from indicators.models import TrackedIndicator
from configurations.models import Objective, AssessmentPeriod
from dhis2_auth.models import DHIS2User


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
            'weight', 'remarks', 'is_manual_override', 'override_reason', 'override_user',
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


class MilestoneScoreSerializer(serializers.ModelSerializer):
    """
    Serializer for milestone scores
    """
    milestone_name = serializers.CharField(source='milestone.name', read_only=True)
    objective_name = serializers.CharField(source='objective.name', read_only=True)
    assessment_period_name = serializers.CharField(source='assessment_period.name', read_only=True)
    override_user_name = serializers.CharField(source='override_user.dhis2_username', read_only=True)
    
    class Meta:
        model = MilestoneScore
        fields = [
            'id', 'milestone', 'milestone_name', 'objective', 'objective_name',
            'org_unit_id', 'org_unit_name', 'assessment_period', 'assessment_period_name',
            'score', 'score_color', 'score_label', 'notes', 'is_manual_override',
            'override_reason', 'override_user', 'override_user_name',
            'created_at', 'updated_at', 'last_calculated'
        ]
        read_only_fields = [
            'created_at', 'updated_at', 'last_calculated', 'score_color', 'score_label'
        ]


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
    org_unit_names = serializers.ListField(
        child=serializers.CharField(max_length=255),
        required=False,
        help_text="List of organization unit names (optional - will be fetched from DHIS2 if not provided)"
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
    manual_entries = serializers.DictField(
        required=False,
        default=dict,
        help_text="Manual entries data from frontend"
    )
    pre_calculated_scores = serializers.DictField(
        required=False,
        default=dict,
        help_text="Pre-calculated scores from frontend"
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
    period_codes = serializers.ListField(
        child=serializers.CharField(max_length=20),
        required=False,
        help_text="List of period codes corresponding to the periods"
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
    snapshot = serializers.DictField(
        required=False,
        help_text="Optional snapshot of the Excel-like table to allow precise reload"
    )


class AuditLogSerializer(serializers.ModelSerializer):
    """
    Serializer for audit logs
    """
    user_username = serializers.CharField(source='user.username', read_only=True)
    user_email = serializers.CharField(source='user.email', read_only=True)
    action_type_display = serializers.CharField(source='get_action_type_display', read_only=True)
    entity_type_display = serializers.CharField(source='get_entity_type_display', read_only=True)
    change_reason_display = serializers.CharField(source='get_change_reason_display', read_only=True)
    
    class Meta:
        model = AuditLog
        fields = [
            'id', 'action_type', 'action_type_display', 'entity_type', 'entity_type_display',
            'entity_id', 'user', 'user_username', 'user_email', 'session_key', 'ip_address',
            'user_agent', 'change_reason', 'change_reason_display', 'change_description',
            'old_values', 'new_values', 'changed_fields', 'org_unit_id', 'org_unit_name',
            'assessment_period', 'indicator_id', 'objective_id', 'is_conflict_resolution',
            'conflict_type', 'resolution_method', 'created_at'
        ]
        read_only_fields = [
            'id', 'created_at', 'old_values', 'new_values', 'changed_fields',
            'session_key', 'ip_address', 'user_agent'
        ]


class ConflictResolutionSerializer(serializers.ModelSerializer):
    """
    Serializer for conflict resolutions
    """
    resolved_by_username = serializers.CharField(source='resolved_by.username', read_only=True)
    conflict_type_display = serializers.CharField(source='get_conflict_type_display', read_only=True)
    resolution_method_display = serializers.CharField(source='get_resolution_method_display', read_only=True)
    resolution_status_display = serializers.CharField(source='get_resolution_status_display', read_only=True)
    
    class Meta:
        model = ConflictResolution
        fields = [
            'id', 'conflict_type', 'conflict_type_display', 'entity_type', 'entity_id',
            'manual_data', 'dhis2_data', 'conflict_fields', 'resolution_method',
            'resolution_method_display', 'resolution_status', 'resolution_status_display',
            'resolved_by', 'resolved_by_username', 'resolution_notes', 'org_unit_id',
            'org_unit_name', 'assessment_period', 'detected_at', 'resolved_at'
        ]
        read_only_fields = [
            'id', 'detected_at', 'manual_data', 'dhis2_data', 'conflict_fields'
        ]


class ConflictResolutionCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating conflict resolutions
    """
    class Meta:
        model = ConflictResolution
        fields = [
            'conflict_type', 'entity_type', 'entity_id', 'manual_data', 'dhis2_data',
            'conflict_fields', 'org_unit_id', 'org_unit_name', 'assessment_period'
        ]


class ConflictResolutionUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer for updating conflict resolutions
    """
    class Meta:
        model = ConflictResolution
        fields = [
            'resolution_method', 'resolution_status', 'resolution_notes'
        ]


class ManualOverrideSerializer(serializers.Serializer):
    """
    Serializer for manual override requests
    """
    score = serializers.IntegerField(
        min_value=-5, 
        max_value=5,
        help_text="New score value (-5 to 5)"
    )
    reason = serializers.CharField(
        max_length=500,
        help_text="Reason for the manual override"
    )
    entity_type = serializers.ChoiceField(
        choices=AuditLog.EntityType.choices,
        help_text="Type of entity being overridden"
    )
    entity_id = serializers.CharField(
        help_text="ID of the entity being overridden"
    )


class AuditLogFilterSerializer(serializers.Serializer):
    """
    Serializer for filtering audit logs
    """
    action_type = serializers.ChoiceField(
        choices=AuditLog.ActionType.choices,
        required=False,
        help_text="Filter by action type"
    )
    entity_type = serializers.ChoiceField(
        choices=AuditLog.EntityType.choices,
        required=False,
        help_text="Filter by entity type"
    )
    change_reason = serializers.ChoiceField(
        choices=AuditLog.ChangeReason.choices,
        required=False,
        help_text="Filter by change reason"
    )
    user_id = serializers.IntegerField(
        required=False,
        help_text="Filter by user ID"
    )
    org_unit_id = serializers.CharField(
        required=False,
        help_text="Filter by organization unit ID"
    )
    assessment_period = serializers.CharField(
        required=False,
        help_text="Filter by assessment period"
    )
    start_date = serializers.DateField(
        required=False,
        help_text="Filter by start date"
    )
    end_date = serializers.DateField(
        required=False,
        help_text="Filter by end date"
    )
    is_conflict_resolution = serializers.BooleanField(
        required=False,
        help_text="Filter by conflict resolution status"
    )


class ConflictResolutionFilterSerializer(serializers.Serializer):
    """
    Serializer for filtering conflict resolutions
    """
    conflict_type = serializers.ChoiceField(
        choices=ConflictResolution.ConflictType.choices,
        required=False,
        help_text="Filter by conflict type"
    )
    entity_type = serializers.ChoiceField(
        choices=AuditLog.EntityType.choices,
        required=False,
        help_text="Filter by entity type"
    )
    resolution_status = serializers.ChoiceField(
        choices=ConflictResolution.ResolutionStatus.choices,
        required=False,
        help_text="Filter by resolution status"
    )
    resolution_method = serializers.ChoiceField(
        choices=ConflictResolution.ResolutionMethod.choices,
        required=False,
        help_text="Filter by resolution method"
    )
    org_unit_id = serializers.CharField(
        required=False,
        help_text="Filter by organization unit ID"
    )
    assessment_period = serializers.CharField(
        required=False,
        help_text="Filter by assessment period"
    )
    start_date = serializers.DateField(
        required=False,
        help_text="Filter by start date"
    )
    end_date = serializers.DateField(
        required=False,
        help_text="Filter by end date"
    )


class ManualDataUpdateSerializer(serializers.Serializer):
    """
    Serializer for manual data updates
    """
    indicator_id = serializers.IntegerField(
        required=True,
        help_text="ID of the indicator"
    )
    org_unit_id = serializers.CharField(
        max_length=255,
        required=True,
        help_text="Organization unit ID"
    )
    assessment_period_id = serializers.IntegerField(
        required=True,
        help_text="Assessment period ID"
    )
    data_updates = serializers.DictField(
        required=True,
        help_text="Dictionary containing updates for current_value, previous_value, target_value, percent_change, target_gap, score"
    )
    
    def validate_data_updates(self, value):
        """Validate the data updates dictionary"""
        allowed_fields = ['current_value', 'previous_value', 'target_value', 'percent_change', 'target_gap', 'score']
        
        for field in value.keys():
            if field not in allowed_fields:
                raise serializers.ValidationError(f"Field '{field}' is not allowed. Allowed fields: {allowed_fields}")
        
        # Validate score if provided
        if 'score' in value:
            try:
                score = int(value['score'])
                if not (-5 <= score <= 5):
                    raise serializers.ValidationError("Score must be between -5 and 5")
            except (ValueError, TypeError):
                raise serializers.ValidationError("Score must be a valid integer")
        
        return value


class BulkManualDataUpdateSerializer(serializers.Serializer):
    """
    Serializer for bulk manual data updates
    """
    updates = ManualDataUpdateSerializer(
        many=True,
        required=True,
        help_text="List of manual data updates"
    )


class ManualScoreOverrideSerializer(serializers.Serializer):
    """
    Serializer for manual score overrides
    """
    indicator_id = serializers.IntegerField(
        required=True,
        help_text="ID of the indicator"
    )
    org_unit_id = serializers.CharField(
        max_length=255,
        required=True,
        help_text="Organization unit ID"
    )
    assessment_period_id = serializers.IntegerField(
        required=True,
        help_text="Assessment period ID"
    )
    score = serializers.IntegerField(
        min_value=-5,
        max_value=5,
        required=True,
        help_text="Manual score value (-5 to 5)"
    )
    reason = serializers.CharField(
        max_length=500,
        required=False,
        default="Manual score override",
        help_text="Reason for the override"
    )