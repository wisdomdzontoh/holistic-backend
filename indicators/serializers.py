from rest_framework import serializers
from .models import TrackedIndicator, IndicatorCategory, IndicatorCategoryMapping, IndicatorThreshold
from configurations.models import IndicatorWeight


class IndicatorThresholdSerializer(serializers.ModelSerializer):
    """
    Serializer for indicator thresholds
    """
    class Meta:
        model = IndicatorThreshold
        fields = [
            'id', 'min_value', 'max_value', 'score', 'color', 'label'
        ]


class IndicatorCategorySerializer(serializers.ModelSerializer):
    """
    Serializer for indicator categories
    """
    class Meta:
        model = IndicatorCategory
        fields = [
            'id', 'name', 'description', 'color', 'order', 'is_active'
        ]


class IndicatorCategoryMappingSerializer(serializers.ModelSerializer):
    """
    Serializer for indicator category mappings
    """
    category = IndicatorCategorySerializer(read_only=True)
    
    class Meta:
        model = IndicatorCategoryMapping
        fields = [
            'id', 'category', 'weight'
        ]


class IndicatorObjectiveWeightSerializer(serializers.ModelSerializer):
    """
    Serializer for indicator objective weights
    """
    class Meta:
        model = IndicatorWeight
        fields = [
            'id', 'objective', 'weight'
        ]


class TrackedIndicatorSerializer(serializers.ModelSerializer):
    """
    Serializer for tracked indicators
    """
    thresholds = IndicatorThresholdSerializer(many=True, read_only=True)
    category_mappings = IndicatorCategoryMappingSerializer(many=True, read_only=True)
    objective_weights = IndicatorObjectiveWeightSerializer(many=True, read_only=True)
    indicator_type_display = serializers.CharField(source='get_indicator_type_display', read_only=True)
    target_type_display = serializers.CharField(source='get_target_type_display', read_only=True)
    
    class Meta:
        model = TrackedIndicator
        fields = [
            'id', 'name', 'dhis2_uid', 'indicator_type', 'indicator_type_display',
            'indicator_number', 'display_order', 'formula', 'numerator', 'denominator',
            'source_of_data', 'target_value', 'target_display', 'target_type', 'target_type_display',
            'min_score', 'max_score', 'is_active', 'description',
            'dhis2_name', 'dhis2_description', 'created_at', 'updated_at', 'last_sync',
            'thresholds', 'category_mappings', 'objective_weights'
        ]
        read_only_fields = [
            'created_at', 'updated_at', 'last_sync', 'dhis2_name', 'dhis2_description'
        ]


class TrackedIndicatorListSerializer(serializers.ModelSerializer):
    """
    Simplified serializer for listing indicators
    """
    indicator_type_display = serializers.CharField(source='get_indicator_type_display', read_only=True)
    category_count = serializers.SerializerMethodField()
    
    class Meta:
        model = TrackedIndicator
        fields = [
            'id', 'name', 'dhis2_uid', 'indicator_type', 'indicator_type_display',
            'indicator_number', 'display_order', 'numerator', 'denominator',
            'source_of_data', 'is_active', 'target_value', 'target_display', 'target_type', 'category_count',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']
    
    def get_category_count(self, obj):
        return obj.category_mappings.count()


class TrackedIndicatorCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating new indicators
    """
    class Meta:
        model = TrackedIndicator
        fields = [
            'name', 'dhis2_uid', 'indicator_type', 'indicator_number', 'display_order',
            'formula', 'numerator', 'denominator', 'source_of_data', 'target_value',
            'target_display', 'target_type', 'min_score', 'max_score', 'is_active', 'description'
        ]
    
    def validate_dhis2_uid(self, value):
        """Validate DHIS2 UID format"""
        if len(value) != 11:
            raise serializers.ValidationError("DHIS2 UID must be exactly 11 characters long")
        return value
    
    def validate(self, data):
        """Validate indicator data"""
        # Check if formula is provided for calculated indicators
        if data.get('indicator_type') == TrackedIndicator.IndicatorType.CALCULATED:
            if not data.get('formula'):
                raise serializers.ValidationError(
                    "Formula is required for calculated indicators"
                )
        
        # Validate score range
        min_score = data.get('min_score', -2)
        max_score = data.get('max_score', 2)
        if min_score >= max_score:
            raise serializers.ValidationError(
                "min_score must be less than max_score"
            )
        
        return data


class TrackedIndicatorUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer for updating indicators
    """
    class Meta:
        model = TrackedIndicator
        fields = [
            'name', 'indicator_type', 'indicator_number', 'display_order',
            'formula', 'numerator', 'denominator', 'source_of_data', 'target_value',
            'target_display', 'target_type', 'min_score', 'max_score', 'is_active', 'description'
        ]
    
    def validate(self, data):
        """Validate indicator data"""
        # Check if formula is provided for calculated indicators
        if data.get('indicator_type') == TrackedIndicator.IndicatorType.CALCULATED:
            if not data.get('formula'):
                raise serializers.ValidationError(
                    "Formula is required for calculated indicators"
                )
        
        # Validate score range
        min_score = data.get('min_score')
        max_score = data.get('max_score')
        if min_score is not None and max_score is not None:
            if min_score >= max_score:
                raise serializers.ValidationError(
                    "min_score must be less than max_score"
                )
        
        return data


class IndicatorThresholdCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating indicator thresholds
    """
    class Meta:
        model = IndicatorThreshold
        fields = [
            'indicator', 'min_value', 'max_value', 'score', 'color', 'label'
        ]
    
    def validate(self, data):
        """Validate threshold data"""
        min_value = data.get('min_value')
        max_value = data.get('max_value')
        
        if min_value >= max_value:
            raise serializers.ValidationError(
                "min_value must be less than max_value"
            )
        
        # Check for overlapping thresholds
        indicator = data.get('indicator')
        if indicator:
            overlapping = IndicatorThreshold.objects.filter(
                indicator=indicator,
                min_value__lt=max_value,
                max_value__gt=min_value
            )
            if overlapping.exists():
                raise serializers.ValidationError(
                    "This threshold overlaps with existing thresholds for this indicator"
                )
        
        return data


class IndicatorCategoryCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating indicator categories
    """
    class Meta:
        model = IndicatorCategory
        fields = [
            'name', 'description', 'color', 'order', 'is_active'
        ]
    
    def validate_color(self, value):
        """Validate hex color format"""
        if not value.startswith('#') or len(value) != 7:
            raise serializers.ValidationError(
                "Color must be a valid hex color code (e.g., #007bff)"
            )
        return value


class IndicatorCategoryMappingCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating indicator category mappings
    """
    class Meta:
        model = IndicatorCategoryMapping
        fields = [
            'indicator', 'category', 'weight'
        ]
    
    def validate_weight(self, value):
        """Validate weight value"""
        if value <= 0:
            raise serializers.ValidationError("Weight must be greater than 0")
        return value


class IndicatorSyncSerializer(serializers.Serializer):
    """
    Serializer for indicator sync operations
    """
    dhis2_instance_url = serializers.URLField(
        help_text="DHIS2 instance URL to sync from"
    )
    indicator_uids = serializers.ListField(
        child=serializers.CharField(max_length=255),
        required=False,
        help_text="List of specific indicator UIDs to sync (optional)"
    )
    sync_metadata = serializers.BooleanField(
        default=True,
        help_text="Whether to sync indicator metadata from DHIS2"
    ) 