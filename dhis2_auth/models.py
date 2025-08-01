from django.db import models
from django.contrib.auth.models import AbstractUser
import json


class DHIS2User(models.Model):
    """
    Model to track DHIS2 user metadata and usage statistics.
    This is optional but useful for analytics and audit trails.
    """
    dhis2_username = models.CharField(max_length=255)
    dhis2_instance_url = models.URLField()
    dhis2_user_id = models.CharField(max_length=255, blank=True, null=True)
    dhis2_org_units = models.JSONField(default=list, blank=True)
    dhis2_authorities = models.JSONField(default=list, blank=True)
    dhis2_user_groups = models.JSONField(default=list, blank=True)
    
    # Usage tracking
    first_login = models.DateTimeField(auto_now_add=True)
    last_login = models.DateTimeField(auto_now=True)
    login_count = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    
    # Session metadata
    current_session_key = models.CharField(max_length=255, blank=True, null=True)
    
    class Meta:
        db_table = 'dhis2_users'
        verbose_name = 'DHIS2 User'
        verbose_name_plural = 'DHIS2 Users'
        unique_together = ['dhis2_username', 'dhis2_instance_url']
    
    def __str__(self):
        return f"{self.dhis2_username}@{self.dhis2_instance_url}"
    
    def update_login_stats(self, session_key=None):
        """Update login statistics and session info"""
        self.login_count += 1
        if session_key:
            self.current_session_key = session_key
        self.save(update_fields=['login_count', 'current_session_key', 'last_login'])
    
    def get_org_unit_tree(self):
        """Get the user's accessible org unit tree"""
        return self.dhis2_org_units
    
    def has_authority(self, authority):
        """Check if user has a specific DHIS2 authority"""
        return authority in self.dhis2_authorities
    
    def get_user_groups(self):
        """Get user's DHIS2 user groups"""
        return self.dhis2_user_groups


class DHIS2Session(models.Model):
    """
    Model to track active DHIS2 sessions for audit and management.
    """
    user = models.ForeignKey(DHIS2User, on_delete=models.CASCADE, related_name='sessions')
    session_key = models.CharField(max_length=255, unique=True)
    dhis2_instance_url = models.URLField()
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    is_active = models.BooleanField(default=True)
    
    # Session metadata
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    user_agent = models.TextField(blank=True)
    
    class Meta:
        db_table = 'dhis2_sessions'
        verbose_name = 'DHIS2 Session'
        verbose_name_plural = 'DHIS2 Sessions'
    
    def __str__(self):
        return f"Session {self.session_key} for {self.user.dhis2_username}"
    
    def is_expired(self):
        """Check if session has expired"""
        from django.utils import timezone
        return timezone.now() > self.expires_at
    
    def deactivate(self):
        """Deactivate the session"""
        self.is_active = False
        self.save(update_fields=['is_active'])
