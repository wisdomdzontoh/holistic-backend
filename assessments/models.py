from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from decimal import Decimal
import json

from indicators.models import TrackedIndicator
from configurations.models import Objective, AssessmentPeriod, ScoringRule, Milestone
from dhis2_auth.models import DHIS2User


class AuditLog(models.Model):
    """
    Model to track all changes and manual overrides for audit purposes
    """
    class ActionType(models.TextChoices):
        CREATE = 'create', _('Create')
        UPDATE = 'update', _('Update')
        DELETE = 'delete', _('Delete')
        MANUAL_OVERRIDE = 'manual_override', _('Manual Override')
        DHIS2_SYNC = 'dhis2_sync', _('DHIS2 Sync')
        SCORE_CALCULATION = 'score_calculation', _('Score Calculation')
        ASSESSMENT_SAVE = 'assessment_save', _('Assessment Save')
        ASSESSMENT_UPDATE = 'assessment_update', _('Assessment Update')
        ASSESSMENT_DELETE = 'assessment_delete', _('Assessment Delete')
    
    class EntityType(models.TextChoices):
        INDICATOR_DATA = 'indicator_data', _('Indicator Data')
        INDICATOR_SCORE = 'indicator_score', _('Indicator Score')
        OBJECTIVE_SCORE = 'objective_score', _('Objective Score')
        SECTOR_SCORE = 'sector_score', _('Sector Score')
        SAVED_ASSESSMENT = 'saved_assessment', _('Saved Assessment')
        DATA_SYNC = 'data_sync', _('Data Sync')
    
    class ChangeReason(models.TextChoices):
        MANUAL_ENTRY = 'manual_entry', _('Manual Entry')
        DHIS2_SYNC = 'dhis2_sync', _('DHIS2 Sync')
        SCORE_OVERRIDE = 'score_override', _('Score Override')
        DATA_CORRECTION = 'data_correction', _('Data Correction')
        SYSTEM_CALCULATION = 'system_calculation', _('System Calculation')
        USER_REQUEST = 'user_request', _('User Request')
    
    # Audit metadata
    action_type = models.CharField(max_length=20, choices=ActionType.choices)
    entity_type = models.CharField(max_length=20, choices=EntityType.choices)
    entity_id = models.CharField(max_length=255, help_text="ID of the affected entity")
    
    # User and session info
    user = models.ForeignKey(
        DHIS2User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='audit_logs'
    )
    session_key = models.CharField(max_length=255, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    
    # Change details
    change_reason = models.CharField(
        max_length=20,
        choices=ChangeReason.choices,
        default=ChangeReason.USER_REQUEST
    )
    change_description = models.TextField(blank=True)
    
    # Data changes
    old_values = models.JSONField(default=dict, blank=True)
    new_values = models.JSONField(default=dict, blank=True)
    changed_fields = models.JSONField(default=list, blank=True)
    
    # Context
    org_unit_id = models.CharField(max_length=255, blank=True)
    org_unit_name = models.CharField(max_length=255, blank=True)
    assessment_period = models.CharField(max_length=50, blank=True)
    indicator_id = models.CharField(max_length=255, blank=True)
    objective_id = models.CharField(max_length=255, blank=True)
    
    # Conflict resolution
    is_conflict_resolution = models.BooleanField(default=False)
    conflict_type = models.CharField(max_length=50, blank=True)
    resolution_method = models.CharField(max_length=50, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'audit_logs'
        verbose_name = 'Audit Log'
        verbose_name_plural = 'Audit Logs'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['action_type', 'created_at']),
            models.Index(fields=['entity_type', 'entity_id']),
            models.Index(fields=['user', 'created_at']),
            models.Index(fields=['org_unit_id', 'assessment_period']),
            models.Index(fields=['is_conflict_resolution', 'created_at']),
        ]
    
    def __str__(self):
        return f"{self.action_type} - {self.entity_type} ({self.entity_id}) by {self.user}"
    
    @classmethod
    def log_change(cls, action_type, entity_type, entity_id, user=None, **kwargs):
        """
        Create an audit log entry for a change
        """
        return cls.objects.create(
            action_type=action_type,
            entity_type=entity_type,
            entity_id=str(entity_id),
            user=user,
            **kwargs
        )
    
    @classmethod
    def log_manual_override(cls, entity_type, entity_id, user, old_values, new_values, 
                          change_reason=ChangeReason.SCORE_OVERRIDE, **kwargs):
        """
        Create an audit log entry for a manual override
        """
        changed_fields = []
        for key in new_values:
            if key in old_values and old_values[key] != new_values[key]:
                changed_fields.append(key)
        
        return cls.objects.create(
            action_type=cls.ActionType.MANUAL_OVERRIDE,
            entity_type=entity_type,
            entity_id=str(entity_id),
            user=user,
            change_reason=change_reason,
            old_values=old_values,
            new_values=new_values,
            changed_fields=changed_fields,
            **kwargs
        )


class ConflictResolution(models.Model):
    """
    Model to track conflict resolution between manual overrides and DHIS2 sync
    """
    class ConflictType(models.TextChoices):
        DATA_CONFLICT = 'data_conflict', _('Data Conflict')
        SCORE_CONFLICT = 'score_conflict', _('Score Conflict')
        TIMESTAMP_CONFLICT = 'timestamp_conflict', _('Timestamp Conflict')
        USER_CONFLICT = 'user_conflict', _('User Conflict')
    
    class ResolutionMethod(models.TextChoices):
        MANUAL_WINS = 'manual_wins', _('Manual Override Wins')
        DHIS2_WINS = 'dhis2_wins', _('DHIS2 Data Wins')
        MERGE = 'merge', _('Merge Data')
        KEEP_BOTH = 'keep_both', _('Keep Both Versions')
        ESCALATE = 'escalate', _('Escalate to Admin')
    
    class ResolutionStatus(models.TextChoices):
        PENDING = 'pending', _('Pending')
        RESOLVED = 'resolved', _('Resolved')
        ESCALATED = 'escalated', _('Escalated')
        IGNORED = 'ignored', _('Ignored')
    
    # Conflict details
    conflict_type = models.CharField(max_length=20, choices=ConflictType.choices)
    entity_type = models.CharField(max_length=20, choices=AuditLog.EntityType.choices)
    entity_id = models.CharField(max_length=255)
    
    # Data involved
    manual_data = models.JSONField(default=dict)
    dhis2_data = models.JSONField(default=dict)
    conflict_fields = models.JSONField(default=list)
    
    # Resolution
    resolution_method = models.CharField(
        max_length=20,
        choices=ResolutionMethod.choices,
        default=ResolutionMethod.MANUAL_WINS
    )
    resolution_status = models.CharField(
        max_length=20,
        choices=ResolutionStatus.choices,
        default=ResolutionStatus.PENDING
    )
    resolved_by = models.ForeignKey(
        DHIS2User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='resolved_conflicts'
    )
    resolution_notes = models.TextField(blank=True)
    
    # Context
    org_unit_id = models.CharField(max_length=255, blank=True)
    assessment_period = models.CharField(max_length=50, blank=True)
    
    # Timestamps
    detected_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'conflict_resolutions'
        verbose_name = 'Conflict Resolution'
        verbose_name_plural = 'Conflict Resolutions'
        ordering = ['-detected_at']
        indexes = [
            models.Index(fields=['conflict_type', 'resolution_status']),
            models.Index(fields=['entity_type', 'entity_id']),
            models.Index(fields=['org_unit_id', 'assessment_period']),
        ]
    
    def __str__(self):
        return f"{self.conflict_type} - {self.entity_type} ({self.entity_id})"
    
    def resolve(self, method, resolved_by, notes=""):
        """Mark conflict as resolved"""
        self.resolution_method = method
        self.resolution_status = self.ResolutionStatus.RESOLVED
        self.resolved_by = resolved_by
        self.resolution_notes = notes
        self.resolved_at = timezone.now()
        self.save()


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
        
        # Log the sync completion
        AuditLog.log_change(
            action_type=AuditLog.ActionType.DHIS2_SYNC,
            entity_type=AuditLog.EntityType.DATA_SYNC,
            entity_id=self.id,
            user=self.dhis2_user,
            change_reason=AuditLog.ChangeReason.DHIS2_SYNC,
            change_description=f"DHIS2 sync completed: {self.successful_indicators} successful, {self.failed_indicators} failed",
            org_unit_id=",".join(self.org_unit_ids) if self.org_unit_ids else "",
            assessment_period=f"{self.period_start} to {self.period_end}" if self.period_start and self.period_end else ""
        )
    
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
    
    # User notes
    remarks = models.TextField(blank=True, help_text="User remarks about this indicator score")
    
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
    
    # Holistic Assessment scoring context
    scoring_context = models.OneToOneField(
        'ScoringContext', 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True
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
        
        # Use Holistic Assessment scoring if available
        try:
            self.calculate_holistic_score()
            return
        except AttributeError:
            pass  # Fall back to regular scoring
        
        # Store old values for audit
        old_score = self.score
        old_values = {
            'score': old_score,
            'score_color': self.score_color,
            'score_label': self.score_label,
            'target_gap': float(self.target_gap) if self.target_gap else None,
            'percent_change': float(self.percent_change) if self.percent_change else None,
            'last_calculated': self.last_calculated.isoformat() if self.last_calculated else None
        }
        
        # Determine which metric to use for scoring
        if self.indicator.target_value is not None:
            # Use target gap
            if self.current_value is not None and self.target_value > 0:
                # Calculate gap based on target type
                if self.indicator.target_type == 'decrease':
                    # For decrease indicators: (target_value - current_value) / current_value * 100
                    gap = (self.target_value - self.current_value) / self.current_value * 100
                else:
                    # For increase indicators: (current_value - target_value) / target_value * 100
                    gap = (self.current_value - self.target_value) / self.target_value * 100
                
                self.target_gap = gap
                self.percent_change = None
                metric_value = abs(gap)  # Use absolute value for scoring rules
                performance_type = 'gap'
            else:
                return
        elif self.previous_value is not None and self.previous_value > 0:
            # Use percent change
            if self.current_value is not None:
                # Calculate change based on target type
                if self.indicator.target_type == 'decrease':
                    # For decrease indicators: (previous_value - current_value) / abs(current_value) * 100
                    change = ((self.previous_value - self.current_value) / abs(self.current_value)) * 100
                else:
                    # For increase indicators: (current_value - previous_value) / abs(previous_value) * 100
                    change = ((self.current_value - self.previous_value) / abs(self.previous_value)) * 100
                
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
        
        # Log the score calculation
        new_values = {
            'score': self.score,
            'score_color': self.score_color,
            'score_label': self.score_label,
            'target_gap': float(self.target_gap) if self.target_gap else None,
            'percent_change': float(self.percent_change) if self.percent_change else None,
            'last_calculated': self.last_calculated.isoformat()
        }
        
        AuditLog.log_change(
            action_type=AuditLog.ActionType.SCORE_CALCULATION,
            entity_type=AuditLog.EntityType.INDICATOR_SCORE,
            entity_id=self.id,
            user=self.override_user if self.is_manual_override else None,
            change_reason=AuditLog.ChangeReason.SYSTEM_CALCULATION if not self.is_manual_override else AuditLog.ChangeReason.SCORE_OVERRIDE,
            change_description=f"Score calculated for {self.indicator.name}",
            old_values=old_values,
            new_values=new_values,
            org_unit_id=self.org_unit_id,
            org_unit_name=self.org_unit_name,
            assessment_period=self.assessment_period.name if self.assessment_period else "",
            indicator_id=str(self.indicator.id),
            objective_id=str(self.objective.id)
        )
    
    def calculate_holistic_score(self):
        """Calculate score using the Holistic Assessment algorithm"""
        from assessments.services import HolisticScoringService
        
        service = HolisticScoringService()
        
        # Get indicator configuration
        indicator = self.indicator
        
        # Determine if this is first year
        is_first_year = self._is_first_year_reporting()
        
        # Calculate score
        result = service.calculate_indicator_score(
            indicator=indicator,
            current_value=float(self.current_value) if self.current_value else None,
            previous_value=float(self.previous_value) if self.previous_value else None,
            data_provided=self.current_value is not None
        )
        
        # Update score
        self.score = result['score']
        
        # Create or update scoring context
        if not self.scoring_context:
            self.scoring_context = ScoringContext.objects.create(
                indicator_score=self
            )
        
        # Map the simplified scoring result to scoring context
        self.scoring_context.data_provided = result['data_provided'] == "Yes"
        self.scoring_context.current_meets_target = result['target_achieved'] == "Yes"
        self.scoring_context.previous_meets_target = None  # Not used in simplified algorithm
        self.scoring_context.change_category = result['change_category']
        self.scoring_context.gap_category = result['gap_category']
        self.scoring_context.percent_change = result['percent_change']
        self.scoring_context.target_gap = result['target_gap']
        self.scoring_context.save()
        
        # Update color and label based on score
        self.score_color = self._get_score_color(result['score'])
        self.score_label = self._get_score_label(result['score'])
        
        self.save()
    
    def _is_first_year_reporting(self) -> bool:
        """Determine if this is the first year of reporting"""
        # Check if there's a previous assessment period
        previous_scores = IndicatorScore.objects.filter(
            indicator=self.indicator,
            org_unit_id=self.org_unit_id,
            assessment_period__start_date__lt=self.assessment_period.start_date
        ).exists()
        
        return not previous_scores
    
    def _get_score_color(self, score: int) -> str:
        """Get color based on score"""
        color_map = {
            2: '#548235',   # Dark Green
            1: '#A9D08E',   # Light Green
            0: '#FFFF00',   # Yellow
            -1: '#FFC7CE',  # Light Red
            -2: '#FF0000'   # Red
        }
        return color_map.get(score, '#6c757d')
    
    def _get_score_label(self, score: int) -> str:
        """Get label based on score"""
        label_map = {
            2: 'Excellent',
            1: 'Good',
            0: 'Satisfactory',
            -1: 'Needs Improvement',
            -2: 'Critical'
        }
        return label_map.get(score, 'No Data')
    
    def apply_manual_override(self, new_score, user, reason=""):
        """
        Apply a manual override to the score with audit logging
        """
        # Store old values for audit
        old_values = {
            'score': self.score,
            'score_color': self.score_color,
            'score_label': self.score_label,
            'is_manual_override': self.is_manual_override,
            'override_reason': self.override_reason,
            'override_user': str(self.override_user.id) if self.override_user else None
        }
        
        # Apply the override
        self.score = new_score
        self.is_manual_override = True
        self.override_reason = reason
        self.override_user = user
        self.last_calculated = timezone.now()
        
        # Update score metadata
        self.score_color = self._get_score_color(new_score)
        self.score_label = self._get_score_label(new_score)
        
        self.save()
        
        # Log the manual override
        new_values = {
            'score': self.score,
            'score_color': self.score_color,
            'score_label': self.score_label,
            'is_manual_override': self.is_manual_override,
            'override_reason': self.override_reason,
            'override_user': str(self.override_user.id) if self.override_user else None
        }
        
        AuditLog.log_manual_override(
            entity_type=AuditLog.EntityType.INDICATOR_SCORE,
            entity_id=self.id,
            user=user,
            old_values=old_values,
            new_values=new_values,
            change_reason=AuditLog.ChangeReason.SCORE_OVERRIDE,
            change_description=f"Manual override applied to {self.indicator.name}: {reason}",
            org_unit_id=self.org_unit_id,
            org_unit_name=self.org_unit_name,
            assessment_period=self.assessment_period.name if self.assessment_period else "",
            indicator_id=str(self.indicator.id),
            objective_id=str(self.objective.id)
        )
    
    def _get_score_color(self, score):
        """Get color for a given score"""
        if score is None:
            return '#6c757d'
        
        if score >= 2:
            return '#548235'  # Dark Green
        elif score >= 1:
            return '#A9D08E'  # Light Green
        elif score == 0:
            return '#FFFF00'  # Yellow
        elif score == -1:
            return '#FFC7CE'  # Light Red
        else:
            return '#FF0000'  # Red
    
    def _get_score_label(self, score):
        """Get label for a given score"""
        if score is None:
            return 'No Data'
        
        if score == 2:
            return 'Excellent'
        elif score == 1:
            return 'Good'
        elif score == 0:
            return 'Satisfactory'
        elif score == -1:
            return 'Needs Improvement'
        elif score == -2:
            return 'Poor'
        else:
            return 'Unknown'
    
    def clear_manual_override(self, user, reason=""):
        """
        Clear a manual override and recalculate the score
        """
        if not self.is_manual_override:
            return
        
        # Store old values for audit
        old_values = {
            'score': self.score,
            'score_color': self.score_color,
            'score_label': self.score_label,
            'is_manual_override': self.is_manual_override,
            'override_reason': self.override_reason,
            'override_user': str(self.override_user.id) if self.override_user else None
        }
        
        # Clear the override
        self.is_manual_override = False
        self.override_reason = ""
        self.override_user = None
        
        # Recalculate the score
        self.calculate_score()
        
        # Log the override clearance
        new_values = {
            'score': self.score,
            'score_color': self.score_color,
            'score_label': self.score_label,
            'is_manual_override': self.is_manual_override,
            'override_reason': self.override_reason,
            'override_user': None
        }
        
        AuditLog.log_change(
            action_type=AuditLog.ActionType.UPDATE,
            entity_type=AuditLog.EntityType.INDICATOR_SCORE,
            entity_id=self.id,
            user=user,
            change_reason=AuditLog.ChangeReason.DATA_CORRECTION,
            change_description=f"Manual override cleared for {self.indicator.name}: {reason}",
            old_values=old_values,
            new_values=new_values,
            org_unit_id=self.org_unit_id,
            org_unit_name=self.org_unit_name,
            assessment_period=self.assessment_period.name if self.assessment_period else "",
            indicator_id=str(self.indicator.id),
            objective_id=str(self.objective.id)
        )


class ScoringContext(models.Model):
    """
    Stores the scoring context for each indicator assessment
    """
    indicator_score = models.OneToOneField('IndicatorScore', on_delete=models.CASCADE)
    
    # Data availability flag (L)
    data_provided = models.BooleanField(default=True)
    
    # Current and previous status flags (M, N)
    current_meets_target = models.BooleanField(null=True)
    previous_meets_target = models.BooleanField(null=True)
    
    # Change categories (O)
    change_category = models.CharField(
        max_length=20, choices=[
            ('>5%', 'Improvement >5%'),
            ('-5%<C<=5%', 'Stable (-5% to +5%)'),
            ('-10%<C<=-5%', 'Small decline (-10% to -5%)'),
            ('<=-10%', 'Large decline (≤-10%)')
        ], null=True
    )
    
    # Gap category (P)
    gap_category = models.CharField(
        max_length=20, choices=[
            ('<=10%', 'Close to target (≤10%)'),
            ('10%<PT<=40%', 'Moderately far (10-40%)'),
            ('>40%', 'Far from target (>40%)')
        ], null=True
    )
    
    # Calculated metrics
    percent_change = models.DecimalField(max_digits=8, decimal_places=2, null=True)
    target_gap = models.DecimalField(max_digits=8, decimal_places=2, null=True)
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'scoring_contexts'
        verbose_name = 'Scoring Context'
        verbose_name_plural = 'Scoring Contexts'
    
    def __str__(self):
        return f"Scoring Context for {self.indicator_score}"


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
                self.score_color = '#548235'
                self.score_label = 'Excellent'
            elif self.final_score >= 0.5:
                self.score_color = '#A9D08E'
                self.score_label = 'Good'
            elif self.final_score >= -0.5:
                self.score_color = '#FFFF00'
                self.score_label = 'Sustained'
            elif self.final_score >= -1.5:
                self.score_color = '#FFC7CE'
                self.score_label = 'Underperforming'
            else:
                self.score_color = '#FF0000'
                self.score_label = 'Poor'
        
        self.last_calculated = timezone.now()
        self.save()


class MilestoneScore(models.Model):
    """
    Model to store milestone scores for assessments
    """
    milestone = models.ForeignKey(
        Milestone,
        on_delete=models.CASCADE,
        related_name='scores'
    )
    objective = models.ForeignKey(
        Objective,
        on_delete=models.CASCADE,
        related_name='milestone_scores'
    )
    
    # Assessment context
    org_unit_id = models.CharField(max_length=255, db_index=True)
    org_unit_name = models.CharField(max_length=255, blank=True)
    assessment_period = models.ForeignKey(
        AssessmentPeriod,
        on_delete=models.CASCADE,
        related_name='milestone_scores'
    )
    
    # Score data
    score = models.IntegerField(
        validators=[MinValueValidator(-2), MaxValueValidator(2)],
        null=True,
        blank=True,
        help_text="Manual score for this milestone (-2 to +2)"
    )
    score_color = models.CharField(max_length=7, blank=True)
    score_label = models.CharField(max_length=50, blank=True)
    
    # User notes
    notes = models.TextField(blank=True, help_text="User notes about this milestone score")
    
    # Status
    is_manual_override = models.BooleanField(default=True, help_text="Milestone scores are always manual")
    override_reason = models.TextField(blank=True)
    override_user = models.ForeignKey(
        DHIS2User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='milestone_score_overrides'
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_calculated = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'milestone_scores'
        verbose_name = 'Milestone Score'
        verbose_name_plural = 'Milestone Scores'
        unique_together = ['milestone', 'org_unit_id', 'assessment_period']
        ordering = ['objective__order', 'milestone__order']
        indexes = [
            models.Index(fields=['org_unit_id', 'assessment_period']),
            models.Index(fields=['objective', 'org_unit_id']),
            models.Index(fields=['milestone', 'org_unit_id']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return f"{self.milestone.name} - {self.org_unit_name} ({self.assessment_period.name})"
    
    def update_score(self, new_score, user, reason=""):
        """
        Update the milestone score
        """
        old_score = self.score
        
        # Update score
        self.score = new_score
        
        # Set color and label based on score
        if self.score is not None:
            if self.score >= 2:
                self.score_color = '#548235'  # Dark Green
                self.score_label = 'Highly Performing'
            elif self.score >= 1:
                self.score_color = '#A9D08E'  # Light Green
                self.score_label = 'Moderately Performing'
            elif self.score >= 0:
                self.score_color = '#FFFF00'  # Yellow
                self.score_label = 'Sustained'
            elif self.score >= -1:
                self.score_color = '#FFC7CE'  # Light Red
                self.score_label = 'Underperforming'
            else:
                self.score_color = '#FF0000'  # Red
                self.score_label = 'Severely Underperforming'
        
        # Update metadata
        self.override_reason = reason
        self.override_user = user
        self.last_calculated = timezone.now()
        self.save()
        
        # Log the change
        AuditLog.log_manual_override(
            entity_type=AuditLog.EntityType.INDICATOR_SCORE,
            entity_id=f"milestone_{self.id}",
            user=user,
            old_values={'score': old_score},
            new_values={'score': new_score},
            change_reason=AuditLog.ChangeReason.SCORE_OVERRIDE,
            change_description=f"Milestone score updated from {old_score} to {new_score}",
            org_unit_id=self.org_unit_id,
            org_unit_name=self.org_unit_name,
            assessment_period=self.assessment_period.name,
            objective_id=self.objective.id
        )


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
                self.score_color = '#548235'
                self.score_label = 'Excellent'
            elif self.overall_score >= 0.5:
                self.score_color = '#A9D08E'
                self.score_label = 'Good'
            elif self.overall_score >= -0.5:
                self.score_color = '#FFFF00'
                self.score_label = 'Sustained'
            elif self.overall_score >= -1.5:
                self.score_color = '#FFC7CE'
                self.score_label = 'Underperforming'
            else:
                self.score_color = '#FF0000'
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
        if not self.metadata:
            return 'holistic'
        return self.metadata.get('assessment_type', 'holistic')


class BulkAssessmentJob(models.Model):
    """
    Tracks a background run that generates one Holistic Assessment per facility
    in a DHIS2 organisation unit group (e.g. "every District Hospital in my
    region"), instead of a user repeating the single-facility flow manually.
    """
    class Status(models.TextChoices):
        PENDING = 'pending', _('Pending')
        IN_PROGRESS = 'in_progress', _('In Progress')
        COMPLETED = 'completed', _('Completed')
        COMPLETED_WITH_ERRORS = 'completed_with_errors', _('Completed with errors')
        FAILED = 'failed', _('Failed')
        CANCELLED = 'cancelled', _('Cancelled')

    name = models.CharField(max_length=255)

    # Target selection
    org_unit_group_id = models.CharField(max_length=255)
    org_unit_group_name = models.CharField(max_length=255, blank=True)
    org_unit_level = models.PositiveSmallIntegerField(null=True, blank=True)
    org_unit_level_name = models.CharField(max_length=255, blank=True)

    # periods holds DHIS2 period codes (e.g. "2024Q1") - what's passed into
    # fetch_holistic_assessment_data. period_labels holds the matching display
    # names with spaces (e.g. "2024 Q1") - what SavedAssessment.periods expects,
    # per the same convention the interactive save flow already uses.
    periods = models.JSONField(default=list)
    period_labels = models.JSONField(default=list)

    status = models.CharField(max_length=25, choices=Status.choices, default=Status.PENDING)

    total_facilities = models.PositiveIntegerField(default=0)
    processed_facilities = models.PositiveIntegerField(default=0)
    succeeded_facilities = models.PositiveIntegerField(default=0)
    failed_facilities = models.PositiveIntegerField(default=0)
    progress_percentage = models.IntegerField(
        default=0, validators=[MinValueValidator(0), MaxValueValidator(100)]
    )

    # Cooperative cancellation - the background thread checks this between
    # facilities rather than being killed outright.
    cancel_requested = models.BooleanField(default=False)

    # Job-level failure only (e.g. target resolution itself failing before any
    # item exists) - per-facility failures live on BulkAssessmentJobItem instead.
    error_message = models.TextField(blank=True)

    created_by = models.ForeignKey(
        DHIS2User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='bulk_assessment_jobs'
    )
    # Needed by the background thread to build its own DHIS2Client after the
    # originating request has already returned.
    session_key = models.CharField(max_length=255, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'bulk_assessment_jobs'
        verbose_name = 'Bulk Assessment Job'
        verbose_name_plural = 'Bulk Assessment Jobs'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['created_by', 'created_at']),
            models.Index(fields=['status']),
        ]

    def __str__(self):
        return f"{self.name} ({self.get_status_display()})"

    def mark_started(self):
        self.status = self.Status.IN_PROGRESS
        self.started_at = timezone.now()
        self.save(update_fields=['status', 'started_at'])

    def update_progress(self):
        if self.total_facilities > 0:
            self.progress_percentage = int(self.processed_facilities / self.total_facilities * 100)
        self.save(update_fields=[
            'processed_facilities', 'succeeded_facilities', 'failed_facilities', 'progress_percentage'
        ])

    def mark_finished(self):
        if self.cancel_requested:
            self.status = self.Status.CANCELLED
        elif self.failed_facilities == 0:
            self.status = self.Status.COMPLETED
        else:
            self.status = self.Status.COMPLETED_WITH_ERRORS
        self.completed_at = timezone.now()
        self.progress_percentage = 100
        self.save(update_fields=['status', 'completed_at', 'progress_percentage'])

    def mark_failed(self, error_message: str):
        self.status = self.Status.FAILED
        self.error_message = error_message[:2000]
        self.completed_at = timezone.now()
        self.save(update_fields=['status', 'error_message', 'completed_at'])


class BulkAssessmentJobItem(models.Model):
    """One facility within a BulkAssessmentJob."""
    class Status(models.TextChoices):
        PENDING = 'pending', _('Pending')
        IN_PROGRESS = 'in_progress', _('In Progress')
        COMPLETED = 'completed', _('Completed')
        FAILED = 'failed', _('Failed')
        SKIPPED = 'skipped', _('Skipped')

    job = models.ForeignKey(BulkAssessmentJob, on_delete=models.CASCADE, related_name='items')
    org_unit_id = models.CharField(max_length=255, db_index=True)
    org_unit_name = models.CharField(max_length=255, blank=True)
    order = models.PositiveIntegerField(default=0)

    status = models.CharField(max_length=15, choices=Status.choices, default=Status.PENDING)
    saved_assessment = models.ForeignKey(
        SavedAssessment, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='bulk_job_items'
    )
    error_message = models.TextField(blank=True)
    attempt_count = models.PositiveIntegerField(default=0)

    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'bulk_assessment_job_items'
        verbose_name = 'Bulk Assessment Job Item'
        verbose_name_plural = 'Bulk Assessment Job Items'
        ordering = ['order', 'id']
        unique_together = [('job', 'org_unit_id')]
        indexes = [
            models.Index(fields=['job', 'status']),
        ]

    def __str__(self):
        return f"{self.org_unit_name} - {self.get_status_display()}"
