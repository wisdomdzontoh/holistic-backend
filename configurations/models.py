from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils.translation import gettext_lazy as _
from indicators.models import TrackedIndicator, IndicatorCategory


class Milestone(models.Model):
    """
    Model to represent milestones within objectives (e.g., MS 1.1, MS 1.2)
    """
    name = models.CharField(max_length=255, help_text="Milestone name (e.g., 'MS 1.1')")
    description = models.TextField(blank=True, help_text="Detailed description of the milestone")
    score = models.IntegerField(
        validators=[MinValueValidator(-2), MaxValueValidator(2)],
        default=-2,
        help_text="Manual score for this milestone (-2 to +2)"
    )
    code = models.CharField(max_length=50, unique=True, help_text="Short code for the milestone (e.g., 'MS1.1')")
    order = models.PositiveIntegerField(default=0, help_text="Display order within objective")
    is_active = models.BooleanField(default=True, help_text="Whether this milestone is active")
    color = models.CharField(
        max_length=7,
        default="#ffc107",
        help_text="Hex color code for this milestone (yellow for Excel)"
    )
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'milestones'
        verbose_name = 'Milestone'
        verbose_name_plural = 'Milestones'
        ordering = ['order', 'name']
    
    def __str__(self):
        return f"{self.name} ({self.code})"


class Objective(models.Model):
    """
    Model to represent assessment objectives (e.g., Objective 1, 2, 3)
    """
    name = models.CharField(max_length=255, unique=True, help_text="Objective name (e.g., 'Objective 1')")
    description = models.TextField(blank=True, help_text="Detailed description of the objective")
    code = models.CharField(max_length=50, unique=True, help_text="Short code for the objective (e.g., 'OBJ1')")
    order = models.PositiveIntegerField(default=0, help_text="Display order")
    is_active = models.BooleanField(default=True, help_text="Whether this objective is active")
    color = models.CharField(
        max_length=7,
        default="#fd7e14",
        help_text="Hex color code for this objective (orange for Excel)"
    )
    
    # Associated milestone
    milestone = models.ForeignKey(
        Milestone,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='objectives',
        help_text="Associated milestone for this objective"
    )
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'objectives'
        verbose_name = 'Objective'
        verbose_name_plural = 'Objectives'
        ordering = ['order', 'name']
    
    def __str__(self):
        return f"{self.name} ({self.code})"
    
    def get_total_weight(self):
        """Get total weight of all indicators in this objective"""
        return self.indicator_weights.aggregate(
            total=models.Sum('weight')
        )['total'] or 0


class ScoringRule(models.Model):
    """
    Model to define scoring rules for performance ranges
    """
    class PerformanceType(models.TextChoices):
        GAP = 'gap', _('Target Gap')
        CHANGE = 'change', _('Percent Change')
        ABSOLUTE = 'absolute', _('Absolute Value')
    
    class ComparisonOperator(models.TextChoices):
        LESS_THAN = 'lt', _('Less than')
        LESS_EQUAL = 'lte', _('Less than or equal')
        EQUAL = 'eq', _('Equal to')
        GREATER_EQUAL = 'gte', _('Greater than or equal')
        GREATER_THAN = 'gt', _('Greater than')
        BETWEEN = 'between', _('Between')
    
    name = models.CharField(max_length=255, help_text="Rule name (e.g., 'Excellent Performance')")
    performance_type = models.CharField(
        max_length=20,
        choices=PerformanceType.choices,
        default=PerformanceType.GAP,
        help_text="Type of performance measurement"
    )
    
    # Threshold values
    min_value = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Minimum threshold value"
    )
    max_value = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Maximum threshold value"
    )
    
    # Scoring
    score = models.IntegerField(
        validators=[MinValueValidator(-5), MaxValueValidator(5)],
        help_text="Score assigned to this performance range"
    )
    color = models.CharField(
        max_length=7,
        default="#6c757d",
        help_text="Hex color code for this score"
    )
    label = models.CharField(
        max_length=50,
        help_text="Human-readable label (e.g., 'Excellent', 'Poor')"
    )
    
    # Priority for rule matching
    priority = models.PositiveIntegerField(
        default=0,
        help_text="Priority for rule matching (higher = more important)"
    )
    
    # Status
    is_active = models.BooleanField(default=True, help_text="Whether this rule is active")
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'scoring_rules'
        verbose_name = 'Scoring Rule'
        verbose_name_plural = 'Scoring Rules'
        ordering = ['performance_type', 'priority', 'min_value']
        unique_together = ['performance_type', 'min_value', 'max_value']
    
    def __str__(self):
        return f"{self.name}: {self.min_value}-{self.max_value} = {self.score}"
    
    def matches_value(self, value):
        """Check if a value matches this rule"""
        if self.min_value is not None and value < self.min_value:
            return False
        if self.max_value is not None and value > self.max_value:
            return False
        return True
    
    def get_description(self):
        """Get human-readable description of the rule"""
        if self.min_value is not None and self.max_value is not None:
            return f"{self.min_value} to {self.max_value}"
        elif self.min_value is not None:
            return f"≥ {self.min_value}"
        elif self.max_value is not None:
            return f"≤ {self.max_value}"
        else:
            return "Any value"


class WeightingScheme(models.Model):
    """
    Model to define weighting schemes for objectives and indicators
    """
    name = models.CharField(max_length=255, unique=True, help_text="Name of the weighting scheme")
    description = models.TextField(blank=True, help_text="Description of the weighting scheme")
    is_active = models.BooleanField(default=True, help_text="Whether this scheme is active")
    is_default = models.BooleanField(default=False, help_text="Whether this is the default scheme")
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'weighting_schemes'
        verbose_name = 'Weighting Scheme'
        verbose_name_plural = 'Weighting Schemes'
        ordering = ['-is_default', 'name']
    
    def __str__(self):
        default_text = " (Default)" if self.is_default else ""
        return f"{self.name}{default_text}"
    
    def get_total_objective_weight(self):
        """Get total weight of all objectives in this scheme"""
        return self.objective_weights.aggregate(
            total=models.Sum('weight')
        )['total'] or 0
    
    def save(self, *args, **kwargs):
        # Ensure only one default scheme
        if self.is_default:
            WeightingScheme.objects.exclude(id=self.id).update(is_default=False)
        super().save(*args, **kwargs)


class ObjectiveWeight(models.Model):
    """
    Model to define weights for objectives within a weighting scheme
    """
    scheme = models.ForeignKey(
        WeightingScheme,
        on_delete=models.CASCADE,
        related_name='objective_weights'
    )
    objective = models.ForeignKey(
        Objective,
        on_delete=models.CASCADE,
        related_name='scheme_weights'
    )
    weight = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        help_text="Weight of this objective in the scheme"
    )
    
    class Meta:
        db_table = 'objective_weights'
        verbose_name = 'Objective Weight'
        verbose_name_plural = 'Objective Weights'
        unique_together = ['scheme', 'objective']
        ordering = ['scheme', 'objective__order']
    
    def __str__(self):
        return f"{self.objective.name} in {self.scheme.name}: {self.weight}"


class IndicatorWeight(models.Model):
    """
    Model to define weights for indicators within objectives
    """
    objective = models.ForeignKey(
        Objective,
        on_delete=models.CASCADE,
        related_name='indicator_weights'
    )
    indicator = models.ForeignKey(
        TrackedIndicator,
        on_delete=models.CASCADE,
        related_name='objective_weights'
    )
    weight = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        default=1.0,
        help_text="Weight of this indicator within the objective"
    )
    
    class Meta:
        db_table = 'indicator_weights'
        verbose_name = 'Indicator Weight'
        verbose_name_plural = 'Indicator Weights'
        unique_together = ['objective', 'indicator']
        ordering = ['objective__order', 'weight']
    
    def __str__(self):
        return f"{self.indicator.name} in {self.objective.name}: {self.weight}"


class AssessmentPeriod(models.Model):
    """
    Model to define assessment periods (e.g., monthly, quarterly, yearly)
    """
    class PeriodType(models.TextChoices):
        MONTHLY = 'monthly', _('Monthly')
        QUARTERLY = 'quarterly', _('Quarterly')
        YEARLY = 'yearly', _('Yearly')
        CUSTOM = 'custom', _('Custom')
    
    name = models.CharField(max_length=255, unique=True, help_text="Period name (e.g., 'Q1 2024')")
    period_type = models.CharField(
        max_length=20,
        choices=PeriodType.choices,
        default=PeriodType.QUARTERLY
    )
    start_date = models.DateField(help_text="Start date of the assessment period")
    end_date = models.DateField(help_text="End date of the assessment period")
    is_active = models.BooleanField(default=True, help_text="Whether this period is active")
    is_current = models.BooleanField(default=False, help_text="Whether this is the current period")
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'assessment_periods'
        verbose_name = 'Assessment Period'
        verbose_name_plural = 'Assessment Periods'
        ordering = ['-start_date']
    
    def __str__(self):
        return f"{self.name} ({self.start_date} to {self.end_date})"
    
    def save(self, *args, **kwargs):
        # Ensure only one current period
        if self.is_current:
            AssessmentPeriod.objects.exclude(id=self.id).update(is_current=False)
        super().save(*args, **kwargs)
    
    @property
    def duration_days(self):
        """Get duration of the period in days"""
        return (self.end_date - self.start_date).days


class SystemConfiguration(models.Model):
    """
    Model to store system-wide configuration settings
    """
    class ConfigType(models.TextChoices):
        SCORING = 'scoring', _('Scoring Configuration')
        DISPLAY = 'display', _('Display Configuration')
        INTEGRATION = 'integration', _('Integration Configuration')
        NOTIFICATION = 'notification', _('Notification Configuration')
        EXPORT = 'export', _('Export Configuration')
    
    key = models.CharField(max_length=255, unique=True, help_text="Configuration key")
    value = models.TextField(help_text="Configuration value (JSON format)")
    config_type = models.CharField(
        max_length=20,
        choices=ConfigType.choices,
        default=ConfigType.SCORING
    )
    description = models.TextField(blank=True, help_text="Description of this configuration")
    is_active = models.BooleanField(default=True, help_text="Whether this configuration is active")
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'system_configurations'
        verbose_name = 'System Configuration'
        verbose_name_plural = 'System Configurations'
        ordering = ['config_type', 'key']
    
    def __str__(self):
        return f"{self.key} ({self.config_type})"
    
    def get_value_as_json(self):
        """Get value as parsed JSON"""
        import json
        try:
            return json.loads(self.value)
        except json.JSONDecodeError:
            return None
    
    def set_value_from_json(self, data):
        """Set value from JSON data"""
        import json
        self.value = json.dumps(data)
