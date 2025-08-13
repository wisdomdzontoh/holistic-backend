from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils.translation import gettext_lazy as _


class TrackedIndicator(models.Model):
    """
    Model to track indicators and data elements from DHIS2 that should be used
    in the holistic assessment calculations.
    """
    
    class IndicatorType(models.TextChoices):
        INDICATOR = 'indicator', _('Indicator')
        DATA_ELEMENT = 'dataElement', _('Data Element')
        CALCULATED = 'calculated', _('Calculated')
    
    class TargetType(models.TextChoices):
        INCREASE = 'increase', _('Increase')
        DECREASE = 'decrease', _('Decrease')
    
    # Basic information
    name = models.CharField(max_length=255, help_text="Human-readable name for the indicator")
    dhis2_uid = models.CharField(
        max_length=255,
        unique=True,
        blank=True,
        null=True,
        help_text="DHIS2 UID of the indicator/data element (leave blank for manual entry)"
    )
    indicator_type = models.CharField(
        max_length=20,
        choices=IndicatorType.choices,
        default=IndicatorType.INDICATOR,
        help_text="Type of DHIS2 object"
    )
    
    # Excel structure support
    indicator_number = models.CharField(
        max_length=20,
        blank=True,
        help_text="Indicator number in Excel format (e.g., '1.1', '1.2')"
    )
    display_order = models.PositiveIntegerField(
        default=0,
        help_text="Display order within objective"
    )
    
    # Formula and calculation
    formula = models.TextField(
        blank=True,
        null=True,
        help_text="Optional formula for calculated indicators (e.g., (uid1 / uid2) * 100)"
    )
    
    # Numerator and denominator for indicator definitions
    numerator = models.TextField(
        blank=True,
        null=True,
        help_text="Numerator description for the indicator calculation"
    )
    denominator = models.TextField(
        blank=True,
        null=True,
        help_text="Denominator description for the indicator calculation"
    )
    
    # Source of data
    source_of_data = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="Source of data for this indicator (e.g., DHIS2, Financial Report, etc.)"
    )
    
    # Target display (text field for formatted targets)
    target_display = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Formatted target display (e.g., '20-50', '100%', '85.0')"
    )
    
    # Target and scoring
    target_value = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Target value for this indicator"
    )
    target_type = models.CharField(
        max_length=10,
        choices=TargetType.choices,
        default=TargetType.INCREASE,
        help_text="Whether higher or lower values are better"
    )
    
    # Holistic Assessment target configuration
    target_operator = models.CharField(
        max_length=10,
        choices=[
            ('>', 'Greater than'),
            ('>=', 'Greater than or equal'),
            ('<', 'Less than'),
            ('<=', 'Less than or equal'),
            ('=', 'Equal to')
        ],
        default='>=',
        help_text="Operator for target comparison (e.g., >5%)"
    )
    target_measurement_type = models.CharField(
        max_length=20,
        choices=[
            ('PERCENTAGE', 'Percentage'),
            ('ABSOLUTE', 'Absolute Number'),
            ('RATIO', 'Ratio')
        ],
        default='PERCENTAGE',
        help_text="Type of target measurement"
    )
    
    # Performance thresholds (configurable per indicator)
    improvement_threshold = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=5.0,
        help_text="Threshold for '>5%' improvement (default: 5.0)"
    )
    stability_threshold = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=5.0,
        help_text="Threshold for stable performance (default: 5.0)"
    )
    decline_threshold = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=10.0,
        help_text="Threshold for significant decline (default: 10.0)"
    )
    
    # Gap analysis thresholds
    close_gap_threshold = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=10.0,
        help_text="Threshold for 'close to target' (default: 10.0)"
    )
    far_gap_threshold = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=40.0,
        help_text="Threshold for 'far from target' (default: 40.0)"
    )
    
    # Scoring configuration
    min_score = models.IntegerField(
        default=-2,
        validators=[MinValueValidator(-5), MaxValueValidator(5)],
        help_text="Minimum score for this indicator"
    )
    max_score = models.IntegerField(
        default=2,
        validators=[MinValueValidator(-5), MaxValueValidator(5)],
        help_text="Maximum score for this indicator"
    )
    
    # Status and metadata
    is_active = models.BooleanField(
        default=True,
        help_text="Whether this indicator is active and should be included in calculations"
    )
    description = models.TextField(
        blank=True,
        help_text="Description of what this indicator measures"
    )
    
    # DHIS2 metadata
    dhis2_name = models.CharField(
        max_length=255,
        blank=True,
        help_text="Original name from DHIS2"
    )
    dhis2_description = models.TextField(
        blank=True,
        help_text="Original description from DHIS2"
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_sync = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Last time this indicator was synced from DHIS2"
    )
    
    class Meta:
        db_table = 'tracked_indicators'
        verbose_name = 'Tracked Indicator'
        verbose_name_plural = 'Tracked Indicators'
        ordering = ['display_order', 'name']
    
    def __str__(self):
        return f"{self.indicator_number} - {self.name}" if self.indicator_number else self.name
    
    def get_formula_components(self):
        """
        Extract UIDs from the formula for dependency tracking.
        """
        if not self.formula:
            return []
        
        # Simple extraction of UIDs from formula
        # This is a basic implementation - could be enhanced with proper parsing
        import re
        uid_pattern = r'[A-Za-z0-9]{11}'  # DHIS2 UIDs are typically 11 characters
        return re.findall(uid_pattern, self.formula)
    
    def is_calculated(self):
        """Check if this is a calculated indicator"""
        return self.indicator_type == self.IndicatorType.CALCULATED
    
    def get_target_direction(self):
        """Get the target direction as a string"""
        return "higher" if self.target_type == self.TargetType.INCREASE else "lower"


class IndicatorCategory(models.Model):
    """
    Model to categorize indicators (e.g., by objective, sector, etc.)
    """
    name = models.CharField(max_length=255, unique=True)
    description = models.TextField(blank=True)
    color = models.CharField(
        max_length=7,
        default="#007bff",
        help_text="Hex color code for this category"
    )
    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        db_table = 'indicator_categories'
        verbose_name = 'Indicator Category'
        verbose_name_plural = 'Indicator Categories'
        ordering = ['order', 'name']
    
    def __str__(self):
        return self.name


class IndicatorCategoryMapping(models.Model):
    """
    Many-to-many relationship between indicators and categories
    """
    indicator = models.ForeignKey(
        TrackedIndicator,
        on_delete=models.CASCADE,
        related_name='category_mappings'
    )
    category = models.ForeignKey(
        IndicatorCategory,
        on_delete=models.CASCADE,
        related_name='indicator_mappings'
    )
    weight = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=1.0,
        help_text="Weight of this indicator within the category"
    )
    
    class Meta:
        db_table = 'indicator_category_mappings'
        unique_together = ['indicator', 'category']
        verbose_name = 'Indicator Category Mapping'
        verbose_name_plural = 'Indicator Category Mappings'
    
    def __str__(self):
        return f"{self.indicator.name} in {self.category.name}"


class IndicatorThreshold(models.Model):
    """
    Model to define scoring thresholds for indicators
    """
    indicator = models.ForeignKey(
        TrackedIndicator,
        on_delete=models.CASCADE,
        related_name='thresholds'
    )
    min_value = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Minimum value for this threshold"
    )
    max_value = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Maximum value for this threshold"
    )
    score = models.IntegerField(
        validators=[MinValueValidator(-5), MaxValueValidator(5)],
        help_text="Score assigned to values in this range"
    )
    color = models.CharField(
        max_length=7,
        default="#6c757d",
        help_text="Hex color code for this threshold"
    )
    label = models.CharField(
        max_length=50,
        help_text="Human-readable label for this threshold (e.g., 'Excellent', 'Poor')"
    )
    
    class Meta:
        db_table = 'indicator_thresholds'
        verbose_name = 'Indicator Threshold'
        verbose_name_plural = 'Indicator Thresholds'
        ordering = ['indicator', 'min_value']
        unique_together = ['indicator', 'min_value', 'max_value']
    
    def __str__(self):
        return f"{self.indicator.name}: {self.min_value}-{self.max_value} = {self.score}"
    
    def contains_value(self, value):
        """Check if a value falls within this threshold range"""
        return self.min_value <= value <= self.max_value
