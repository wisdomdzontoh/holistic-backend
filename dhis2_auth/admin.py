from django.contrib import admin
from django.utils.html import format_html
from django.utils import timezone
from .models import DHIS2User, DHIS2Session


@admin.register(DHIS2User)
class DHIS2UserAdmin(admin.ModelAdmin):
    """
    Admin interface for DHIS2 users.
    """
    list_display = [
        'dhis2_username', 'dhis2_instance_url', 'login_count', 
        'first_login', 'last_login', 'is_active', 'session_status'
    ]
    list_filter = [
        'is_active', 'dhis2_instance_url', 'first_login', 'last_login'
    ]
    search_fields = ['dhis2_username', 'dhis2_user_id', 'dhis2_instance_url']
    readonly_fields = [
        'dhis2_user_id', 'dhis2_org_units', 'dhis2_authorities', 
        'dhis2_user_groups', 'first_login', 'last_login', 'login_count'
    ]
    ordering = ['-last_login']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('dhis2_username', 'dhis2_instance_url', 'is_active')
        }),
        ('DHIS2 Data', {
            'fields': ('dhis2_user_id', 'dhis2_org_units', 'dhis2_authorities', 'dhis2_user_groups'),
            'classes': ('collapse',)
        }),
        ('Usage Statistics', {
            'fields': ('first_login', 'last_login', 'login_count', 'current_session_key'),
            'classes': ('collapse',)
        }),
    )
    
    def session_status(self, obj):
        """Display current session status"""
        if obj.current_session_key:
            try:
                session = DHIS2Session.objects.get(
                    session_key=obj.current_session_key,
                    is_active=True
                )
                if session.is_expired():
                    return format_html('<span style="color: red;">Expired</span>')
                else:
                    return format_html('<span style="color: green;">Active</span>')
            except DHIS2Session.DoesNotExist:
                return format_html('<span style="color: orange;">Invalid</span>')
        return format_html('<span style="color: gray;">No Session</span>')
    
    session_status.short_description = 'Session Status'
    
    def get_queryset(self, request):
        """Optimize queryset with related data"""
        return super().get_queryset(request).select_related()
    
    actions = ['deactivate_users', 'activate_users', 'clear_sessions']
    
    def deactivate_users(self, request, queryset):
        """Deactivate selected users"""
        updated = queryset.update(is_active=False)
        self.message_user(request, f'{updated} users have been deactivated.')
    deactivate_users.short_description = "Deactivate selected users"
    
    def activate_users(self, request, queryset):
        """Activate selected users"""
        updated = queryset.update(is_active=True)
        self.message_user(request, f'{updated} users have been activated.')
    activate_users.short_description = "Activate selected users"
    
    def clear_sessions(self, request, queryset):
        """Clear sessions for selected users"""
        session_keys = list(queryset.values_list('current_session_key', flat=True))
        DHIS2Session.objects.filter(session_key__in=session_keys).update(is_active=False)
        queryset.update(current_session_key='')
        self.message_user(request, f'Sessions cleared for {len(session_keys)} users.')
    clear_sessions.short_description = "Clear sessions for selected users"


@admin.register(DHIS2Session)
class DHIS2SessionAdmin(admin.ModelAdmin):
    """
    Admin interface for DHIS2 sessions.
    """
    list_display = [
        'session_key', 'user', 'dhis2_instance_url', 'created_at', 
        'expires_at', 'is_active', 'session_status'
    ]
    list_filter = [
        'is_active', 'dhis2_instance_url', 'created_at', 'expires_at'
    ]
    search_fields = ['session_key', 'user__dhis2_username', 'ip_address']
    readonly_fields = [
        'session_key', 'user', 'dhis2_instance_url', 'created_at', 
        'expires_at', 'ip_address', 'user_agent'
    ]
    ordering = ['-created_at']
    
    fieldsets = (
        ('Session Information', {
            'fields': ('session_key', 'user', 'dhis2_instance_url', 'is_active')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'expires_at'),
            'classes': ('collapse',)
        }),
        ('Request Information', {
            'fields': ('ip_address', 'user_agent'),
            'classes': ('collapse',)
        }),
    )
    
    def session_status(self, obj):
        """Display session status"""
        if obj.is_expired():
            return format_html('<span style="color: red;">Expired</span>')
        elif obj.is_active:
            return format_html('<span style="color: green;">Active</span>')
        else:
            return format_html('<span style="color: orange;">Inactive</span>')
    
    session_status.short_description = 'Status'
    
    def get_queryset(self, request):
        """Optimize queryset with related data"""
        return super().get_queryset(request).select_related('user')
    
    actions = ['deactivate_sessions', 'cleanup_expired_sessions']
    
    def deactivate_sessions(self, request, queryset):
        """Deactivate selected sessions"""
        updated = queryset.update(is_active=False)
        self.message_user(request, f'{updated} sessions have been deactivated.')
    deactivate_sessions.short_description = "Deactivate selected sessions"
    
    def cleanup_expired_sessions(self, request, queryset):
        """Clean up expired sessions"""
        expired_sessions = queryset.filter(expires_at__lt=timezone.now())
        count = expired_sessions.count()
        expired_sessions.update(is_active=False)
        self.message_user(request, f'{count} expired sessions have been cleaned up.')
    cleanup_expired_sessions.short_description = "Clean up expired sessions"
    
    def has_add_permission(self, request):
        """Disable manual session creation"""
        return False
    
    def has_change_permission(self, request, obj=None):
        """Allow only deactivation of sessions"""
        return True
    
    def has_delete_permission(self, request, obj=None):
        """Allow deletion of sessions"""
        return True
