from rest_framework import serializers
from .models import (
    Objective, ScoringRule, WeightingScheme, ObjectiveWeight, 
    IndicatorWeight, AssessmentPeriod, SystemConfiguration
)
from indicators.models import TrackedIndicator


class ObjectiveSerializer(serializers.ModelSerializer):
    """
    Serializer for objectives
    """
    total_weight = serializers.SerializerMethodField()
    indicator_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Objective
        fields = [
            'id', 'name', 'description', 'code', 'order', 'is_active',
            'color', 'created_at', 'updated_at', 'total_weight', 'indicator_count'
        ]
        read_only_fields = ['created_at', 'updated_at']
    
    def get_total_weight(self, obj):
        return obj.get_total_weight()
    
    def get_indicator_count(self, obj):
        return obj.indicator_weights.count()


class ScoringRuleSerializer(serializers.ModelSerializer):
    """
    Serializer for scoring rules
    """
    performance_type_display = serializers.CharField(source='get_performance_type_display', read_only=True)
    description = serializers.SerializerMethodField()
    
    class Meta:
        model = ScoringRule
        fields = [
            'id', 'name', 'performance_type', 'performance_type_display',
            'min_value', 'max_value', 'score', 'color', 'label',
            'priority', 'is_active', 'created_at', 'updated_at', 'description'
        ]
        read_only_fields = ['created_at', 'updated_at']
    
    def get_description(self, obj):
        return obj.get_description()
    
    def validate(self, data):
        """Validate scoring rule data"""
        min_value = data.get('min_value')
        max_value = data.get('max_value')
        
        # At least one threshold value must be provided
        if min_value is None and max_value is None:
            raise serializers.ValidationError(
                "At least one threshold value (min_value or max_value) must be provided"
            )
        
        # If both values are provided, min_value must be less than max_value
        if min_value is not None and max_value is not None:
            if min_value >= max_value:
                raise serializers.ValidationError(
                    "min_value must be less than max_value"
                )
        
        return data


class WeightingSchemeSerializer(serializers.ModelSerializer):
    """
    Serializer for weighting schemes
    """
    total_objective_weight = serializers.SerializerMethodField()
    objective_count = serializers.SerializerMethodField()
    
    class Meta:
        model = WeightingScheme
        fields = [
            'id', 'name', 'description', 'is_active', 'is_default',
            'created_at', 'updated_at', 'total_objective_weight', 'objective_count'
        ]
        read_only_fields = ['created_at', 'updated_at']
    
    def get_total_objective_weight(self, obj):
        return obj.get_total_objective_weight()
    
    def get_objective_count(self, obj):
        return obj.objective_weights.count()


class ObjectiveWeightSerializer(serializers.ModelSerializer):
    """
    Serializer for objective weights
    """
    objective = ObjectiveSerializer(read_only=True)
    objective_name = serializers.CharField(source='objective.name', read_only=True)
    
    class Meta:
        model = ObjectiveWeight
        fields = [
            'id', 'scheme', 'objective', 'objective_name', 'weight'
        ]


class IndicatorWeightSerializer(serializers.ModelSerializer):
    """
    Serializer for indicator weights
    """
    indicator_name = serializers.CharField(source='indicator.name', read_only=True)
    objective_name = serializers.CharField(source='objective.name', read_only=True)
    
    class Meta:
        model = IndicatorWeight
        fields = [
            'id', 'objective', 'objective_name', 'indicator', 'indicator_name', 'weight'
        ]


class AssessmentPeriodSerializer(serializers.ModelSerializer):
    """
    Serializer for assessment periods
    """
    period_type_display = serializers.CharField(source='get_period_type_display', read_only=True)
    duration_days = serializers.IntegerField(read_only=True)
    
    class Meta:
        model = AssessmentPeriod
        fields = [
            'id', 'name', 'period_type', 'period_type_display',
            'start_date', 'end_date', 'is_active', 'is_current',
            'created_at', 'updated_at', 'duration_days'
        ]
        read_only_fields = ['created_at', 'updated_at', 'duration_days']
    
    def validate(self, data):
        """Validate assessment period data"""
        start_date = data.get('start_date')
        end_date = data.get('end_date')
        
        if start_date and end_date and start_date >= end_date:
            raise serializers.ValidationError(
                "start_date must be before end_date"
            )
        
        return data


class SystemConfigurationSerializer(serializers.ModelSerializer):
    """
    Serializer for system configurations
    """
    config_type_display = serializers.CharField(source='get_config_type_display', read_only=True)
    value_parsed = serializers.SerializerMethodField()
    
    class Meta:
        model = SystemConfiguration
        fields = [
            'id', 'key', 'value', 'value_parsed', 'config_type', 'config_type_display',
            'description', 'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']
    
    def get_value_parsed(self, obj):
        return obj.get_value_as_json()
    
    def validate_value(self, value):
        """Validate JSON value"""
        import json
        try:
            json.loads(value)
        except json.JSONDecodeError:
            raise serializers.ValidationError("Value must be valid JSON")
        return value


# Create/Update serializers
class ObjectiveCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating objectives
    """
    class Meta:
        model = Objective
        fields = [
            'name', 'description', 'code', 'order', 'is_active', 'color'
        ]
    
    def validate_code(self, value):
        """Validate objective code format"""
        if not value.isalnum():
            raise serializers.ValidationError("Code must contain only letters and numbers")
        return value.upper()


class ScoringRuleCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating scoring rules
    """
    class Meta:
        model = ScoringRule
        fields = [
            'name', 'performance_type', 'min_value', 'max_value',
            'score', 'color', 'label', 'priority', 'is_active'
        ]
    
    def validate_color(self, value):
        """Validate hex color format"""
        if not value.startswith('#') or len(value) != 7:
            raise serializers.ValidationError(
                "Color must be a valid hex color code (e.g., #007bff)"
            )
        return value


class WeightingSchemeCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating weighting schemes
    """
    class Meta:
        model = WeightingScheme
        fields = [
            'name', 'description', 'is_active', 'is_default'
        ]


class ObjectiveWeightCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating objective weights
    """
    class Meta:
        model = ObjectiveWeight
        fields = [
            'scheme', 'objective', 'weight'
        ]
    
    def validate_weight(self, value):
        """Validate weight value"""
        if value <= 0:
            raise serializers.ValidationError("Weight must be greater than 0")
        return value


class IndicatorWeightCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating indicator weights
    """
    class Meta:
        model = IndicatorWeight
        fields = [
            'objective', 'indicator', 'weight'
        ]
    
    def validate_weight(self, value):
        """Validate weight value"""
        if value <= 0:
            raise serializers.ValidationError("Weight must be greater than 0")
        return value


class AssessmentPeriodCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating assessment periods
    """
    class Meta:
        model = AssessmentPeriod
        fields = [
            'name', 'period_type', 'start_date', 'end_date', 'is_active', 'is_current'
        ]


class SystemConfigurationCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating system configurations
    """
    class Meta:
        model = SystemConfiguration
        fields = [
            'key', 'value', 'config_type', 'description', 'is_active'
        ]


# Bulk operation serializers
class BulkObjectiveWeightSerializer(serializers.Serializer):
    """
    Serializer for bulk creating objective weights
    """
    scheme_id = serializers.IntegerField()
    weights = serializers.ListField(
        child=serializers.DictField(),
        help_text="List of {objective_id: weight} pairs"
    )


class BulkIndicatorWeightSerializer(serializers.Serializer):
    """
    Serializer for bulk creating indicator weights
    """
    objective_id = serializers.IntegerField()
    weights = serializers.ListField(
        child=serializers.DictField(),
        help_text="List of {indicator_id: weight} pairs"
    )


# Configuration validation serializers
class ConfigurationValidationSerializer(serializers.Serializer):
    """
    Serializer for validating configuration completeness
    """
    check_objectives = serializers.BooleanField(default=True)
    check_scoring_rules = serializers.BooleanField(default=True)
    check_weighting_schemes = serializers.BooleanField(default=True)
    check_assessment_periods = serializers.BooleanField(default=True)


class ConfigurationSummarySerializer(serializers.Serializer):
    """
    Serializer for configuration summary
    """
    total_objectives = serializers.IntegerField()
    active_objectives = serializers.IntegerField()
    total_scoring_rules = serializers.IntegerField()
    active_scoring_rules = serializers.IntegerField()
    total_weighting_schemes = serializers.IntegerField()
    active_weighting_schemes = serializers.IntegerField()
    default_weighting_scheme = serializers.CharField(allow_null=True)
    current_assessment_period = serializers.CharField(allow_null=True)
    total_indicators = serializers.IntegerField()
    weighted_indicators = serializers.IntegerField() 