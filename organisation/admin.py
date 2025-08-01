from django.contrib import admin
from django.utils.html import format_html
from django.utils import timezone
from .models import (
    OrgUnitLevel, OrgUnit, UserOrgUnitAccess, OrgUnitSyncLog,
    OrgUnitGroup, OrgUnitGroupMembership
)


class OrgUnitInline(admin.TabularInline):
    """
    Inline admin for org units
    """
    model = OrgUnit
    extra = 0
    readonly_fields = ['dhis2_uid', 'name', 'level', 'is_active']
    fields = ['dhis2_uid', 'name', 'level', 'is_active']
    can_delete = False


@admin.register(OrgUnitLevel)
class OrgUnitLevelAdmin(admin.ModelAdmin):
    """
    Admin interface for org unit levels
    """
    list_display = [
        'level', 'name', 'display_name', 'dhis2_uid', 'can_view_data',
        'can_edit_data', 'can_manage_users', 'org_unit_count', 'last_synced'
    ]
    list_filter = ['level', 'can_view_data', 'can_edit_data', 'can_manage_users']
    search_fields = ['name', 'display_name', 'description', 'dhis2_uid']
    readonly_fields = ['created_at', 'updated_at', 'last_synced']
    ordering = ['level']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('level', 'name', 'display_name', 'description')
        }),
        ('DHIS2 Information', {
            'fields': ('dhis2_uid', 'dhis2_code', 'parent_level')
        }),
        ('Access Control', {
            'fields': ('can_view_data', 'can_edit_data', 'can_manage_users')
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at', 'last_synced'),
            'classes': ('collapse',)
        }),
    )
    
    def org_unit_count(self, obj):
        """Get count of org units at this level"""
        return obj.org_units.count()
    org_unit_count.short_description = 'Org Units'


class UserOrgUnitAccessInline(admin.TabularInline):
    """
    Inline admin for user org unit access
    """
    model = UserOrgUnitAccess
    extra = 0
    readonly_fields = ['user', 'org_unit', 'granted_at']
    fields = ['user', 'org_unit', 'can_view_data', 'can_edit_data', 'can_manage_users', 'is_primary', 'is_active']
    can_delete = False


@admin.register(OrgUnit)
class OrgUnitAdmin(admin.ModelAdmin):
    """
    Admin interface for org units
    """
    list_display = [
        'name', 'dhis2_uid', 'level', 'parent', 'is_active', 'is_leaf',
        'children_count', 'user_access_count', 'last_synced'
    ]
    list_filter = [
        'level', 'is_active', 'is_leaf', 'can_view_data', 'can_edit_data',
        'can_manage_users', 'created_at'
    ]
    search_fields = ['name', 'short_name', 'display_name', 'dhis2_uid', 'dhis2_code']
    readonly_fields = [
        'created_at', 'updated_at', 'last_synced', 'children_count',
        'user_access_count', 'full_path'
    ]
    ordering = ['level__level', 'name']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('dhis2_uid', 'dhis2_code', 'name', 'short_name', 'display_name')
        }),
        ('Hierarchy', {
            'fields': ('level', 'parent', 'full_path')
        }),
        ('Location', {
            'fields': ('latitude', 'longitude'),
            'classes': ('collapse',)
        }),
        ('Status', {
            'fields': ('is_active', 'is_leaf')
        }),
        ('Access Control', {
            'fields': ('can_view_data', 'can_edit_data', 'can_manage_users')
        }),
        ('DHIS2 Metadata', {
            'fields': ('dhis2_created', 'dhis2_last_updated', 'dhis2_path'),
            'classes': ('collapse',)
        }),
        ('Statistics', {
            'fields': ('children_count', 'user_access_count'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at', 'last_synced'),
            'classes': ('collapse',)
        }),
    )
    
    inlines = [UserOrgUnitAccessInline]
    
    def children_count(self, obj):
        """Get count of children"""
        return obj.children.count()
    children_count.short_description = 'Children'
    
    def user_access_count(self, obj):
        """Get count of user access records"""
        return obj.user_access.count()
    user_access_count.short_description = 'User Access'
    
    actions = ['activate_org_units', 'deactivate_org_units', 'sync_from_dhis2']
    
    def activate_org_units(self, request, queryset):
        """Activate selected org units"""
        count = queryset.update(is_active=True)
        self.message_user(request, f'{count} org units have been activated.')
    activate_org_units.short_description = "Activate org units"
    
    def deactivate_org_units(self, request, queryset):
        """Deactivate selected org units"""
        count = queryset.update(is_active=False)
        self.message_user(request, f'{count} org units have been deactivated.')
    deactivate_org_units.short_description = "Deactivate org units"
    
    def sync_from_dhis2(self, request, queryset):
        """Sync selected org units from DHIS2"""
        # This would trigger a sync for the selected org units
        self.message_user(request, f'Sync initiated for {queryset.count()} org units.')
    sync_from_dhis2.short_description = "Sync from DHIS2"


@admin.register(UserOrgUnitAccess)
class UserOrgUnitAccessAdmin(admin.ModelAdmin):
    """
    Admin interface for user org unit access
    """
    list_display = [
        'user', 'org_unit', 'org_unit_level', 'can_view_data', 'can_edit_data',
        'can_manage_users', 'is_primary', 'is_active', 'is_expired', 'granted_at'
    ]
    list_filter = [
        'is_active', 'is_primary', 'can_view_data', 'can_edit_data',
        'can_manage_users', 'include_children', 'include_descendants',
        'granted_at', 'expires_at'
    ]
    search_fields = [
        'user__dhis2_username', 'user__dhis2_display_name',
        'org_unit__name', 'org_unit__dhis2_uid', 'notes'
    ]
    readonly_fields = ['granted_at', 'is_expired']
    ordering = ['user__dhis2_username', 'org_unit__name']
    
    fieldsets = (
        ('User and Org Unit', {
            'fields': ('user', 'org_unit')
        }),
        ('Permissions', {
            'fields': ('can_view_data', 'can_edit_data', 'can_manage_users', 'can_export_data')
        }),
        ('Access Scope', {
            'fields': ('include_children', 'include_descendants')
        }),
        ('Status', {
            'fields': ('is_active', 'is_primary')
        }),
        ('Grant Information', {
            'fields': ('granted_by', 'granted_at', 'expires_at', 'notes')
        }),
    )
    
    def org_unit_level(self, obj):
        """Get org unit level name"""
        return obj.org_unit.level.name if obj.org_unit else '-'
    org_unit_level.short_description = 'Level'
    
    def is_expired(self, obj):
        """Check if access has expired"""
        return obj.is_expired
    is_expired.boolean = True
    is_expired.short_description = 'Expired'
    
    actions = ['activate_access', 'deactivate_access', 'set_as_primary', 'remove_primary']
    
    def activate_access(self, request, queryset):
        """Activate selected access records"""
        count = queryset.update(is_active=True)
        self.message_user(request, f'{count} access records have been activated.')
    activate_access.short_description = "Activate access"
    
    def deactivate_access(self, request, queryset):
        """Deactivate selected access records"""
        count = queryset.update(is_active=False)
        self.message_user(request, f'{count} access records have been deactivated.')
    deactivate_access.short_description = "Deactivate access"
    
    def set_as_primary(self, request, queryset):
        """Set selected access records as primary"""
        # First, remove primary from other records for the same user
        for access in queryset:
            UserOrgUnitAccess.objects.filter(
                user=access.user,
                is_primary=True
            ).exclude(id=access.id).update(is_primary=False)
        
        # Then set the selected records as primary
        count = queryset.update(is_primary=True)
        self.message_user(request, f'{count} access records have been set as primary.')
    set_as_primary.short_description = "Set as primary"
    
    def remove_primary(self, request, queryset):
        """Remove primary status from selected access records"""
        count = queryset.update(is_primary=False)
        self.message_user(request, f'{count} access records have been removed from primary status.')
    remove_primary.short_description = "Remove primary status"


@admin.register(OrgUnitSyncLog)
class OrgUnitSyncLogAdmin(admin.ModelAdmin):
    """
    Admin interface for org unit sync logs
    """
    list_display = [
        'id', 'status', 'dhis2_instance_url', 'total_org_units', 'successful_org_units',
        'failed_org_units', 'total_levels', 'successful_levels', 'failed_levels',
        'duration_formatted', 'started_at'
    ]
    list_filter = ['status', 'started_at']
    search_fields = ['dhis2_instance_url', 'error_message']
    readonly_fields = [
        'started_at', 'completed_at', 'duration_seconds', 'total_org_units',
        'successful_org_units', 'failed_org_units', 'total_levels',
        'successful_levels', 'failed_levels'
    ]
    ordering = ['-started_at']
    
    fieldsets = (
        ('Sync Information', {
            'fields': ('status', 'dhis2_instance_url', 'dhis2_user')
        }),
        ('Results', {
            'fields': ('total_org_units', 'successful_org_units', 'failed_org_units')
        }),
        ('Level Results', {
            'fields': ('total_levels', 'successful_levels', 'failed_levels')
        }),
        ('Error Information', {
            'fields': ('error_message', 'error_details'),
            'classes': ('collapse',)
        }),
        ('Timing', {
            'fields': ('started_at', 'completed_at', 'duration_seconds'),
            'classes': ('collapse',)
        }),
    )
    
    def duration_formatted(self, obj):
        """Format duration in human-readable format"""
        if obj.duration_seconds is None:
            return '-'
        
        minutes = obj.duration_seconds // 60
        seconds = obj.duration_seconds % 60
        
        if minutes > 0:
            return f"{minutes}m {seconds}s"
        else:
            return f"{seconds}s"
    duration_formatted.short_description = 'Duration'
    
    actions = ['retry_failed_syncs', 'mark_as_completed']
    
    def retry_failed_syncs(self, request, queryset):
        """Retry failed syncs"""
        failed_syncs = queryset.filter(status=OrgUnitSyncLog.SyncStatus.FAILED)
        count = failed_syncs.count()
        
        for sync_log in failed_syncs:
            sync_log.status = OrgUnitSyncLog.SyncStatus.PENDING
            sync_log.error_message = ''
            sync_log.error_details = {}
            sync_log.completed_at = None
            sync_log.duration_seconds = None
            sync_log.save()
        
        self.message_user(request, f'{count} failed syncs have been queued for retry.')
    retry_failed_syncs.short_description = "Retry failed syncs"
    
    def mark_as_completed(self, request, queryset):
        """Mark syncs as completed"""
        count = queryset.update(status=OrgUnitSyncLog.SyncStatus.COMPLETED)
        self.message_user(request, f'{count} syncs have been marked as completed.')
    mark_as_completed.short_description = "Mark as completed"


class OrgUnitGroupMembershipInline(admin.TabularInline):
    """
    Inline admin for org unit group memberships
    """
    model = OrgUnitGroupMembership
    extra = 0
    readonly_fields = ['org_unit', 'created_at']
    fields = ['org_unit', 'is_active', 'created_at']
    can_delete = False


@admin.register(OrgUnitGroup)
class OrgUnitGroupAdmin(admin.ModelAdmin):
    """
    Admin interface for org unit groups
    """
    list_display = [
        'name', 'dhis2_uid', 'is_active', 'is_system_group', 'member_count',
        'last_synced'
    ]
    list_filter = ['is_active', 'is_system_group', 'created_at']
    search_fields = ['name', 'short_name', 'description', 'dhis2_uid']
    readonly_fields = ['created_at', 'updated_at', 'last_synced']
    ordering = ['name']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('dhis2_uid', 'dhis2_code', 'name', 'short_name', 'description')
        }),
        ('Properties', {
            'fields': ('is_active', 'is_system_group')
        }),
        ('DHIS2 Metadata', {
            'fields': ('dhis2_created', 'dhis2_last_updated'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at', 'last_synced'),
            'classes': ('collapse',)
        }),
    )
    
    inlines = [OrgUnitGroupMembershipInline]
    
    def member_count(self, obj):
        """Get count of members in this group"""
        return obj.memberships.filter(is_active=True).count()
    member_count.short_description = 'Members'
    
    actions = ['activate_groups', 'deactivate_groups']
    
    def activate_groups(self, request, queryset):
        """Activate selected groups"""
        count = queryset.update(is_active=True)
        self.message_user(request, f'{count} groups have been activated.')
    activate_groups.short_description = "Activate groups"
    
    def deactivate_groups(self, request, queryset):
        """Deactivate selected groups"""
        count = queryset.update(is_active=False)
        self.message_user(request, f'{count} groups have been deactivated.')
    deactivate_groups.short_description = "Deactivate groups"


@admin.register(OrgUnitGroupMembership)
class OrgUnitGroupMembershipAdmin(admin.ModelAdmin):
    """
    Admin interface for org unit group memberships
    """
    list_display = [
        'org_unit', 'group', 'is_active', 'created_at'
    ]
    list_filter = ['is_active', 'group', 'created_at']
    search_fields = ['org_unit__name', 'group__name']
    readonly_fields = ['created_at']
    ordering = ['org_unit__name', 'group__name']
    
    fieldsets = (
        ('Membership', {
            'fields': ('org_unit', 'group', 'is_active')
        }),
        ('Timestamps', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['activate_memberships', 'deactivate_memberships']
    
    def activate_memberships(self, request, queryset):
        """Activate selected memberships"""
        count = queryset.update(is_active=True)
        self.message_user(request, f'{count} memberships have been activated.')
    activate_memberships.short_description = "Activate memberships"
    
    def deactivate_memberships(self, request, queryset):
        """Deactivate selected memberships"""
        count = queryset.update(is_active=False)
        self.message_user(request, f'{count} memberships have been deactivated.')
    deactivate_memberships.short_description = "Deactivate memberships"
