from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from decimal import Decimal
import json

from indicators.models import TrackedIndicator
from configurations.models import Objective, AssessmentPeriod, ScoringRule
from dhis2_auth.models import DHIS2User


class DataSyncLog(models.Model):
    """
    Model to track data synchronization from DHIS2
    """
    class SyncStatus(models.TextChoices):
        PENDING = 'pending', _('Pending')
        IN_PROGRESS = 'in_progress', _('In Progress')
        COMPLETED = 'completed', _('Completed')
        FAILED = 'failed', _('Failed')
        PARTIAL = 'partial', _('Partial Success')
    
    class SyncType(models.TextChoices):
        FULL = 'full', _('Full Sync')
        INCREMENTAL = 'incremental', _('Incremental Sync')
        INDICATOR = 'indicator', _('Single Indicator')
        PERIOD = 'period', _('Period Sync')
    
    # Sync metadata
    sync_type = models.CharField(
        max_length=20,
        choices=SyncType.choices,
        default=SyncType.FULL
    )
    status = models.CharField(
        max_length=20,
        choices=SyncStatus.choices,
        default=SyncStatus.PENDING
    )
    
    # DHIS2 connection info
    dhis2_instance_url = models.URLField()
    dhis2_user = models.ForeignKey(
        DHIS2User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='sync_logs'
    )
    
    # Sync parameters
    period_start = models.DateField(null=True, blank=True)
    period_end = models.DateField(null=True, blank=True)
    org_unit_ids = models.JSONField(default=list, blank=True)
    indicator_uids = models.JSONField(default=list, blank=True)
    
    # Results
    total_indicators = models.PositiveIntegerField(default=0)
    successful_indicators = models.PositiveIntegerField(default=0)
    failed_indicators = models.PositiveIntegerField(default=0)
    total_data_points = models.PositiveIntegerField(default=0)
    
    # Error tracking
    error_message = models.TextField(blank=True)
    error_details = models.JSONField(default=dict, blank=True)
    
    # Timing
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    duration_seconds = models.PositiveIntegerField(null=True, blank=True)
    
    class Meta:
        db_table = 'data_sync_logs'
        verbose_name = 'Data Sync Log'
        verbose_name_plural = 'Data Sync Logs'
        ordering = ['-started_at']
    
    def __str__(self):
        return f"Sync {self.id} - {self.sync_type} ({self.status})"
    
    def mark_completed(self, success_count=0, failure_count=0, total_points=0):
        """Mark sync as completed"""
        self.status = self.SyncStatus.COMPLETED
        self.completed_at = timezone.now()
        self.successful_indicators = success_count
        self.failed_indicators = failure_count
        self.total_data_points = total_points
        
        if self.started_at:
            self.duration_seconds = int((self.completed_at - self.started_at).total_seconds())
        
        self.save()
    
    def mark_failed(self, error_message="", error_details=None):
        """Mark sync as failed"""
        self.status = self.SyncStatus.FAILED
        self.completed_at = timezone.now()
        self.error_message = error_message
        self.error_details = error_details or {}
        
        if self.started_at:
            self.duration_seconds = int((self.completed_at - self.started_at).total_seconds())
        
        self.save()
    
    def mark_partial(self, success_count=0, failure_count=0, total_points=0):
        """Mark sync as partially successful"""
        self.status = self.SyncStatus.PARTIAL
        self.completed_at = timezone.now()
        self.successful_indicators = success_count
        self.failed_indicators = failure_count
        self.total_data_points = total_points
        
        if self.started_at:
            self.duration_seconds = int((self.completed_at - self.started_at).total_seconds())
        
        self.save()


class IndicatorData(models.Model):
    """
    Model to store raw indicator data from DHIS2
    """
    indicator = models.ForeignKey(
        TrackedIndicator,
        on_delete=models.CASCADE,
        related_name='data_points'
    )
    
    # DHIS2 metadata
    org_unit_id = models.CharField(max_length=255, db_index=True)
    org_unit_name = models.CharField(max_length=255, blank=True)
    period = models.CharField(max_length=20, db_index=True)  # e.g., "2024Q1"
    
    # Data values
    value = models.DecimalField(
        max_digits=15,
        decimal_places=4,
        null=True,
        blank=True
    )
    numerator = models.DecimalField(
        max_digits=15,
        decimal_places=4,
        null=True,
        blank=True
    )
    denominator = models.DecimalField(
        max_digits=15,
        decimal_places=4,
        null=True,
        blank=True
    )
    
    # Metadata
    sync_log = models.ForeignKey(
        DataSyncLog,
        on_delete=models.CASCADE,
        related_name='data_points'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # DHIS2 response metadata
    dhis2_response = models.JSONField(default=dict, blank=True)
    
    class Meta:
        db_table = 'indicator_data'
        verbose_name = 'Indicator Data'
        verbose_name_plural = 'Indicator Data'
        unique_together = ['indicator', 'org_unit_id', 'period']
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['indicator', 'org_unit_id', 'period']),
            models.Index(fields=['period']),
            models.Index(fields=['org_unit_id']),
        ]
    
    def __str__(self):
        return f"{self.indicator.name} - {self.org_unit_name} ({self.period})"
    
    @property
    def calculated_value(self):
        """Calculate the final value based on indicator type and formula"""
        if self.indicator.indicator_type == TrackedIndicator.IndicatorType.CALCULATED:
            # For calculated indicators, use the formula
            if self.indicator.formula and self.numerator and self.denominator:
                try:
                    # Simple formula evaluation (replace with more sophisticated parser)
                    formula = self.indicator.formula.replace('numerator', str(self.numerator))
                    formula = formula.replace('denominator', str(self.denominator))
                    return eval(formula)  # Note: In production, use a safer formula parser
                except:
                    return self.value
            return self.value
        else:
            return self.value


class IndicatorScore(models.Model):
    """
    Model to store calculated indicator scores
    """
    indicator = models.ForeignKey(
        TrackedIndicator,
        on_delete=models.CASCADE,
        related_name='scores'
    )
    objective = models.ForeignKey(
        Objective,
        on_delete=models.CASCADE,
        related_name='indicator_scores'
    )
    
    # Assessment context
    org_unit_id = models.CharField(max_length=255, db_index=True)
    org_unit_name = models.CharField(max_length=255, blank=True)
    assessment_period = models.ForeignKey(
        AssessmentPeriod,
        on_delete=models.CASCADE,
        related_name='indicator_scores'
    )
    
    # Data values
    current_value = models.DecimalField(
        max_digits=15,
        decimal_places=4,
        null=True,
        blank=True
    )
    previous_value = models.DecimalField(
        max_digits=15,
        decimal_places=4,
        null=True,
        blank=True
    )
    target_value = models.DecimalField(
        max_digits=15,
        decimal_places=4,
        null=True,
        blank=True
    )
    
    # Calculated metrics
    target_gap = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Percentage gap to target"
    )
    percent_change = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Percentage change from previous period"
    )
    
    # Scoring
    score = models.IntegerField(
        validators=[MinValueValidator(-5), MaxValueValidator(5)],
        null=True,
        blank=True
    )
    score_color = models.CharField(max_length=7, blank=True)
    score_label = models.CharField(max_length=50, blank=True)
    
    # Metadata
    scoring_rule = models.ForeignKey(
        ScoringRule,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='applied_scores'
    )
    weight = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=1.0,
        help_text="Weight of this indicator in the objective"
    )
    
    # Status
    is_manual_override = models.BooleanField(default=False)
    override_reason = models.TextField(blank=True)
    override_user = models.ForeignKey(
        DHIS2User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='score_overrides'
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_calculated = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'indicator_scores'
        verbose_name = 'Indicator Score'
        verbose_name_plural = 'Indicator Scores'
        unique_together = ['indicator', 'org_unit_id', 'assessment_period']
        ordering = ['objective__order', 'indicator__name']
        indexes = [
            models.Index(fields=['indicator', 'org_unit_id', 'assessment_period']),
            models.Index(fields=['objective', 'org_unit_id', 'assessment_period']),
            models.Index(fields=['org_unit_id', 'assessment_period']),
        ]
    
    def __str__(self):
        return f"{self.indicator.name} - {self.org_unit_name} ({self.assessment_period.name})"
    
    def calculate_score(self):
        """Calculate the score based on performance metrics"""
        if self.is_manual_override:
            return  # Don't recalculate manual overrides
        
        # Determine which metric to use for scoring
        if self.indicator.target_value is not None:
            # Use target gap
            if self.current_value is not None and self.target_value > 0:
                gap = abs(self.current_value - self.target_value) / self.target_value * 100
                self.target_gap = gap
                self.percent_change = None
                metric_value = gap
                performance_type = 'gap'
            else:
                return
        elif self.previous_value is not None and self.previous_value > 0:
            # Use percent change
            if self.current_value is not None:
                change = ((self.current_value - self.previous_value) / self.previous_value) * 100
                self.percent_change = change
                self.target_gap = None
                metric_value = change
                performance_type = 'change'
            else:
                return
        else:
            return  # No data to calculate score
        
        # Find matching scoring rule
        matching_rule = None
        rules = ScoringRule.objects.filter(
            performance_type=performance_type,
            is_active=True
        ).order_by('-priority', 'min_value')
        
        for rule in rules:
            if rule.matches_value(metric_value):
                matching_rule = rule
                break
        
        # Apply score
        if matching_rule:
            self.score = matching_rule.score
            self.score_color = matching_rule.color
            self.score_label = matching_rule.label
            self.scoring_rule = matching_rule
        else:
            self.score = 0
            self.score_color = '#6c757d'
            self.score_label = 'No Match'
            self.scoring_rule = None
        
        self.last_calculated = timezone.now()
        self.save()


class ObjectiveScore(models.Model):
    """
    Model to store calculated objective scores
    """
    objective = models.ForeignKey(
        Objective,
        on_delete=models.CASCADE,
        related_name='scores'
    )
    
    # Assessment context
    org_unit_id = models.CharField(max_length=255, db_index=True)
    org_unit_name = models.CharField(max_length=255, blank=True)
    assessment_period = models.ForeignKey(
        AssessmentPeriod,
        on_delete=models.CASCADE,
        related_name='objective_scores'
    )
    
    # Calculated scores
    median_score = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Median of weighted indicator scores"
    )
    weighted_score = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Weighted average of indicator scores"
    )
    final_score = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Final objective score"
    )
    
    # Scoring metadata
    score_color = models.CharField(max_length=7, blank=True)
    score_label = models.CharField(max_length=50, blank=True)
    
    # Statistics
    total_indicators = models.PositiveIntegerField(default=0)
    scored_indicators = models.PositiveIntegerField(default=0)
    total_weight = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_calculated = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'objective_scores'
        verbose_name = 'Objective Score'
        verbose_name_plural = 'Objective Scores'
        unique_together = ['objective', 'org_unit_id', 'assessment_period']
        ordering = ['objective__order']
        indexes = [
            models.Index(fields=['objective', 'org_unit_id', 'assessment_period']),
            models.Index(fields=['org_unit_id', 'assessment_period']),
        ]
    
    def __str__(self):
        return f"{self.objective.name} - {self.org_unit_name} ({self.assessment_period.name})"
    
    def calculate_score(self):
        """Calculate the objective score from indicator scores"""
        indicator_scores = IndicatorScore.objects.filter(
            objective=self.objective,
            org_unit_id=self.org_unit_id,
            assessment_period=self.assessment_period,
            score__isnull=False
        ).select_related('indicator')
        
        if not indicator_scores.exists():
            return
        
        self.total_indicators = indicator_scores.count()
        self.scored_indicators = indicator_scores.filter(score__isnull=False).count()
        
        # Calculate weighted score
        total_weight = sum(score.weight for score in indicator_scores)
        self.total_weight = total_weight
        
        if total_weight > 0:
            weighted_sum = sum(score.score * score.weight for score in indicator_scores if score.score is not None)
            self.weighted_score = weighted_sum / total_weight
        
        # Calculate median score
        scores = [score.score for score in indicator_scores if score.score is not None]
        if scores:
            scores.sort()
            mid = len(scores) // 2
            if len(scores) % 2 == 0:
                self.median_score = (scores[mid - 1] + scores[mid]) / 2
            else:
                self.median_score = scores[mid]
        
        # Use weighted score as final score
        self.final_score = self.weighted_score
        
        # Determine color and label based on final score
        if self.final_score is not None:
            if self.final_score >= 1.5:
                self.score_color = '#28a745'
                self.score_label = 'Excellent'
            elif self.final_score >= 0.5:
                self.score_color = '#17a2b8'
                self.score_label = 'Good'
            elif self.final_score >= -0.5:
                self.score_color = '#ffc107'
                self.score_label = 'Sustained'
            elif self.final_score >= -1.5:
                self.score_color = '#fd7e14'
                self.score_label = 'Underperforming'
            else:
                self.score_color = '#dc3545'
                self.score_label = 'Poor'
        
        self.last_calculated = timezone.now()
        self.save()


class SectorScore(models.Model):
    """
    Model to store calculated sector (overall) scores
    """
    # Assessment context
    org_unit_id = models.CharField(max_length=255, db_index=True)
    org_unit_name = models.CharField(max_length=255, blank=True)
    assessment_period = models.ForeignKey(
        AssessmentPeriod,
        on_delete=models.CASCADE,
        related_name='sector_scores'
    )
    
    # Calculated scores
    overall_score = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Weighted average of objective scores"
    )
    
    # Scoring metadata
    score_color = models.CharField(max_length=7, blank=True)
    score_label = models.CharField(max_length=50, blank=True)
    
    # Statistics
    total_objectives = models.PositiveIntegerField(default=0)
    scored_objectives = models.PositiveIntegerField(default=0)
    total_indicators = models.PositiveIntegerField(default=0)
    scored_indicators = models.PositiveIntegerField(default=0)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_calculated = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'sector_scores'
        verbose_name = 'Sector Score'
        verbose_name_plural = 'Sector Scores'
        unique_together = ['org_unit_id', 'assessment_period']
        ordering = ['-assessment_period__start_date', 'org_unit_name']
        indexes = [
            models.Index(fields=['org_unit_id', 'assessment_period']),
            models.Index(fields=['assessment_period']),
        ]
    
    def __str__(self):
        return f"Sector Score - {self.org_unit_name} ({self.assessment_period.name})"
    
    def calculate_score(self):
        """Calculate the sector score from objective scores"""
        objective_scores = ObjectiveScore.objects.filter(
            org_unit_id=self.org_unit_id,
            assessment_period=self.assessment_period,
            final_score__isnull=False
        ).select_related('objective')
        
        if not objective_scores.exists():
            return
        
        self.total_objectives = objective_scores.count()
        self.scored_objectives = objective_scores.filter(final_score__isnull=False).count()
        
        # Calculate total indicators
        total_indicators = sum(score.total_indicators for score in objective_scores)
        scored_indicators = sum(score.scored_indicators for score in objective_scores)
        self.total_indicators = total_indicators
        self.scored_indicators = scored_indicators
        
        # Calculate weighted average (assuming equal weights for objectives)
        scores = [score.final_score for score in objective_scores if score.final_score is not None]
        if scores:
            self.overall_score = sum(scores) / len(scores)
            
            # Determine color and label based on overall score
            if self.overall_score >= 1.5:
                self.score_color = '#28a745'
                self.score_label = 'Excellent'
            elif self.overall_score >= 0.5:
                self.score_color = '#17a2b8'
                self.score_label = 'Good'
            elif self.overall_score >= -0.5:
                self.score_color = '#ffc107'
                self.score_label = 'Sustained'
            elif self.overall_score >= -1.5:
                self.score_color = '#fd7e14'
                self.score_label = 'Underperforming'
            else:
                self.score_color = '#dc3545'
                self.score_label = 'Poor'
        
        self.last_calculated = timezone.now()
        self.save()


class SavedAssessment(models.Model):
    """
    Model to store user-generated holistic assessments
    """
    name = models.CharField(max_length=255, help_text="Name of the assessment")
    org_unit_id = models.CharField(max_length=255, db_index=True)
    org_unit_name = models.CharField(max_length=255, blank=True)
    
    # Assessment metadata
    periods = models.JSONField(default=list, help_text="List of periods used in the assessment")
    user_notes = models.TextField(blank=True, help_text="User notes and comments")
    
    # Assessment data
    indicator_data = models.JSONField(default=dict, help_text="Indicator data with values for each period")
    calculated_scores = models.JSONField(default=dict, help_text="Calculated scores and grades")
    metadata = models.JSONField(default=dict, help_text="Additional metadata about the assessment")
    
    # User and session info
    created_by = models.ForeignKey(
        'dhis2_auth.DHIS2User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='saved_assessments'
    )
    session_key = models.CharField(max_length=255, blank=True, help_text="DHIS2 session key")
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'saved_assessments'
        verbose_name = 'Saved Assessment'
        verbose_name_plural = 'Saved Assessments'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['org_unit_id']),
            models.Index(fields=['created_at']),
            models.Index(fields=['created_by']),
        ]
    
    def __str__(self):
        return f"{self.name} - {self.org_unit_name} ({self.created_at.strftime('%Y-%m-%d')})"
    
    @property
    def total_indicators(self):
        """Get total number of indicators in the assessment"""
        return self.metadata.get('total_indicators', 0)
    
    @property
    def total_objectives(self):
        """Get total number of objectives in the assessment"""
        return self.metadata.get('total_objectives', 0)
    
    @property
    def assessment_type(self):
        """Get assessment type"""
        return self.metadata.get('assessment_type', 'holistic')
