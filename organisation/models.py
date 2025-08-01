from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
import json

from dhis2_auth.models import DHIS2User


class OrgUnitLevel(models.Model):
    """
    Model to store DHIS2 org unit levels
    """
    level = models.PositiveIntegerField(unique=True)
    name = models.CharField(max_length=255)
    display_name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    
    # DHIS2 metadata
    dhis2_uid = models.CharField(max_length=255, unique=True)
    dhis2_code = models.CharField(max_length=50, blank=True)
    
    # Hierarchy info
    parent_level = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='child_levels'
    )
    
    # Access control
    can_view_data = models.BooleanField(default=True)
    can_edit_data = models.BooleanField(default=False)
    can_manage_users = models.BooleanField(default=False)
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_synced = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'org_unit_levels'
        verbose_name = 'Org Unit Level'
        verbose_name_plural = 'Org Unit Levels'
        ordering = ['level']
    
    def __str__(self):
        return f"Level {self.level}: {self.name}"
    
    @property
    def is_national(self):
        """Check if this is the national level"""
        return self.level == 1
    
    @property
    def is_regional(self):
        """Check if this is the regional level"""
        return self.level == 2
    
    @property
    def is_district(self):
        """Check if this is the district level"""
        return self.level == 3
    
    @property
    def is_facility(self):
        """Check if this is the facility level"""
        return self.level >= 4


class OrgUnit(models.Model):
    """
    Model to store DHIS2 org units
    """
    # DHIS2 metadata
    dhis2_uid = models.CharField(max_length=255, unique=True)
    dhis2_code = models.CharField(max_length=50, blank=True)
    name = models.CharField(max_length=255)
    short_name = models.CharField(max_length=100, blank=True)
    display_name = models.CharField(max_length=255, blank=True)
    
    # Hierarchy
    level = models.ForeignKey(
        OrgUnitLevel,
        on_delete=models.CASCADE,
        related_name='org_units'
    )
    parent = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='children'
    )
    
    # Location data
    latitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True
    )
    longitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True
    )
    
    # Status
    is_active = models.BooleanField(default=True)
    is_leaf = models.BooleanField(default=False)
    
    # Access control
    can_view_data = models.BooleanField(default=True)
    can_edit_data = models.BooleanField(default=False)
    can_manage_users = models.BooleanField(default=False)
    
    # DHIS2 metadata
    dhis2_created = models.DateTimeField(null=True, blank=True)
    dhis2_last_updated = models.DateTimeField(null=True, blank=True)
    dhis2_path = models.CharField(max_length=500, blank=True)
    
    # Sync metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_synced = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'org_units'
        verbose_name = 'Org Unit'
        verbose_name_plural = 'Org Units'
        ordering = ['level__level', 'name']
        indexes = [
            models.Index(fields=['dhis2_uid']),
            models.Index(fields=['level', 'parent']),
            models.Index(fields=['is_active']),
        ]
    
    def __str__(self):
        return f"{self.name} ({self.level.name})"
    
    @property
    def full_path(self):
        """Get the full hierarchical path of this org unit"""
        if not self.parent:
            return self.name
        
        return f"{self.parent.full_path} > {self.name}"
    
    @property
    def ancestors(self):
        """Get all ancestor org units"""
        ancestors = []
        current = self.parent
        while current:
            ancestors.append(current)
            current = current.parent
        return ancestors
    
    @property
    def descendants(self):
        """Get all descendant org units"""
        descendants = []
        for child in self.children.all():
            descendants.append(child)
            descendants.extend(child.descendants)
        return descendants
    
    @property
    def all_children(self):
        """Get all direct and indirect children"""
        return self.descendants
    
    @property
    def is_national(self):
        """Check if this is a national org unit"""
        return self.level.is_national
    
    @property
    def is_regional(self):
        """Check if this is a regional org unit"""
        return self.level.is_regional
    
    @property
    def is_district(self):
        """Check if this is a district org unit"""
        return self.level.is_district
    
    @property
    def is_facility(self):
        """Check if this is a facility org unit"""
        return self.level.is_facility
    
    def get_accessible_children(self, user):
        """Get children that the user can access"""
        if not user:
            return self.children.filter(is_active=True)
        
        # Check user's org unit access
        user_access = UserOrgUnitAccess.objects.filter(
            user=user,
            org_unit__in=self.children.all(),
            is_active=True
        ).values_list('org_unit_id', flat=True)
        
        return self.children.filter(
            id__in=user_access,
            is_active=True
        )


class UserOrgUnitAccess(models.Model):
    """
    Model to manage user access to org units
    """
    user = models.ForeignKey(
        DHIS2User,
        on_delete=models.CASCADE,
        related_name='org_unit_access'
    )
    org_unit = models.ForeignKey(
        OrgUnit,
        on_delete=models.CASCADE,
        related_name='user_access'
    )
    
    # Access permissions
    can_view_data = models.BooleanField(default=True)
    can_edit_data = models.BooleanField(default=False)
    can_manage_users = models.BooleanField(default=False)
    can_export_data = models.BooleanField(default=True)
    
    # Access scope
    include_children = models.BooleanField(
        default=True,
        help_text="Whether access includes child org units"
    )
    include_descendants = models.BooleanField(
        default=True,
        help_text="Whether access includes all descendant org units"
    )
    
    # Status
    is_active = models.BooleanField(default=True)
    is_primary = models.BooleanField(
        default=False,
        help_text="Primary org unit for this user"
    )
    
    # Metadata
    granted_by = models.ForeignKey(
        DHIS2User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='granted_access'
    )
    granted_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    
    # Notes
    notes = models.TextField(blank=True)
    
    class Meta:
        db_table = 'user_org_unit_access'
        verbose_name = 'User Org Unit Access'
        verbose_name_plural = 'User Org Unit Access'
        unique_together = ['user', 'org_unit']
        ordering = ['user__dhis2_username', 'org_unit__name']
        indexes = [
            models.Index(fields=['user', 'is_active']),
            models.Index(fields=['org_unit', 'is_active']),
        ]
    
    def __str__(self):
        return f"{self.user.dhis2_username} -> {self.org_unit.name}"
    
    @property
    def is_expired(self):
        """Check if access has expired"""
        if not self.expires_at:
            return False
        return timezone.now() > self.expires_at
    
    @property
    def accessible_org_units(self):
        """Get all org units accessible to this user through this access"""
        if not self.include_descendants:
            return [self.org_unit]
        
        if self.include_children:
            return [self.org_unit] + list(self.org_unit.descendants)
        
        return [self.org_unit]


class OrgUnitSyncLog(models.Model):
    """
    Model to track org unit synchronization from DHIS2
    """
    class SyncStatus(models.TextChoices):
        PENDING = 'pending', _('Pending')
        IN_PROGRESS = 'in_progress', _('In Progress')
        COMPLETED = 'completed', _('Completed')
        FAILED = 'failed', _('Failed')
        PARTIAL = 'partial', _('Partial Success')
    
    # Sync metadata
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
        related_name='org_unit_sync_logs'
    )
    
    # Results
    total_org_units = models.PositiveIntegerField(default=0)
    successful_org_units = models.PositiveIntegerField(default=0)
    failed_org_units = models.PositiveIntegerField(default=0)
    total_levels = models.PositiveIntegerField(default=0)
    successful_levels = models.PositiveIntegerField(default=0)
    failed_levels = models.PositiveIntegerField(default=0)
    
    # Error tracking
    error_message = models.TextField(blank=True)
    error_details = models.JSONField(default=dict, blank=True)
    
    # Timing
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    duration_seconds = models.PositiveIntegerField(null=True, blank=True)
    
    class Meta:
        db_table = 'org_unit_sync_logs'
        verbose_name = 'Org Unit Sync Log'
        verbose_name_plural = 'Org Unit Sync Logs'
        ordering = ['-started_at']
    
    def __str__(self):
        return f"Org Unit Sync {self.id} - {self.status}"
    
    def mark_completed(self, success_count=0, failure_count=0, total_units=0, success_levels=0, failure_levels=0, total_levels=0):
        """Mark sync as completed"""
        self.status = self.SyncStatus.COMPLETED
        self.completed_at = timezone.now()
        self.successful_org_units = success_count
        self.failed_org_units = failure_count
        self.total_org_units = total_units
        self.successful_levels = success_levels
        self.failed_levels = failure_levels
        self.total_levels = total_levels
        
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
    
    def mark_partial(self, success_count=0, failure_count=0, total_units=0, success_levels=0, failure_levels=0, total_levels=0):
        """Mark sync as partially successful"""
        self.status = self.SyncStatus.PARTIAL
        self.completed_at = timezone.now()
        self.successful_org_units = success_count
        self.failed_org_units = failure_count
        self.total_org_units = total_units
        self.successful_levels = success_levels
        self.failed_levels = failure_levels
        self.total_levels = total_levels
        
        if self.started_at:
            self.duration_seconds = int((self.completed_at - self.started_at).total_seconds())
        
        self.save()


class OrgUnitGroup(models.Model):
    """
    Model to store DHIS2 org unit groups
    """
    # DHIS2 metadata
    dhis2_uid = models.CharField(max_length=255, unique=True)
    dhis2_code = models.CharField(max_length=50, blank=True)
    name = models.CharField(max_length=255)
    short_name = models.CharField(max_length=100, blank=True)
    description = models.TextField(blank=True)
    
    # Group properties
    is_active = models.BooleanField(default=True)
    is_system_group = models.BooleanField(
        default=False,
        help_text="Whether this is a system-defined group"
    )
    
    # DHIS2 metadata
    dhis2_created = models.DateTimeField(null=True, blank=True)
    dhis2_last_updated = models.DateTimeField(null=True, blank=True)
    
    # Sync metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_synced = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'org_unit_groups'
        verbose_name = 'Org Unit Group'
        verbose_name_plural = 'Org Unit Groups'
        ordering = ['name']
    
    def __str__(self):
        return self.name


class OrgUnitGroupMembership(models.Model):
    """
    Model to track org unit membership in groups
    """
    org_unit = models.ForeignKey(
        OrgUnit,
        on_delete=models.CASCADE,
        related_name='group_memberships'
    )
    group = models.ForeignKey(
        OrgUnitGroup,
        on_delete=models.CASCADE,
        related_name='memberships'
    )
    
    # Membership metadata
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'org_unit_group_memberships'
        verbose_name = 'Org Unit Group Membership'
        verbose_name_plural = 'Org Unit Group Memberships'
        unique_together = ['org_unit', 'group']
        ordering = ['org_unit__name', 'group__name']
    
    def __str__(self):
        return f"{self.org_unit.name} in {self.group.name}"
