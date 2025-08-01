from rest_framework import serializers
from .models import (
    OrgUnitLevel, OrgUnit, UserOrgUnitAccess, OrgUnitSyncLog,
    OrgUnitGroup, OrgUnitGroupMembership
)
from dhis2_auth.models import DHIS2User


class OrgUnitLevelSerializer(serializers.ModelSerializer):
    """
    Serializer for org unit levels
    """
    parent_level_name = serializers.CharField(source='parent_level.name', read_only=True)
    org_unit_count = serializers.SerializerMethodField()
    
    class Meta:
        model = OrgUnitLevel
        fields = [
            'id', 'level', 'name', 'display_name', 'description', 'dhis2_uid',
            'dhis2_code', 'parent_level', 'parent_level_name', 'can_view_data',
            'can_edit_data', 'can_manage_users', 'created_at', 'updated_at',
            'last_synced', 'org_unit_count'
        ]
        read_only_fields = ['created_at', 'updated_at', 'last_synced']
    
    def get_org_unit_count(self, obj):
        """Get count of org units at this level"""
        return obj.org_units.count()


class OrgUnitSerializer(serializers.ModelSerializer):
    """
    Serializer for org units
    """
    level_name = serializers.CharField(source='level.name', read_only=True)
    level_display_name = serializers.CharField(source='level.display_name', read_only=True)
    parent_name = serializers.CharField(source='parent.name', read_only=True)
    full_path = serializers.CharField(read_only=True)
    children_count = serializers.SerializerMethodField()
    user_access_count = serializers.SerializerMethodField()
    
    class Meta:
        model = OrgUnit
        fields = [
            'id', 'dhis2_uid', 'dhis2_code', 'name', 'short_name', 'display_name',
            'level', 'level_name', 'level_display_name', 'parent', 'parent_name',
            'latitude', 'longitude', 'is_active', 'is_leaf', 'can_view_data',
            'can_edit_data', 'can_manage_users', 'dhis2_created', 'dhis2_last_updated',
            'dhis2_path', 'created_at', 'updated_at', 'last_synced', 'full_path',
            'children_count', 'user_access_count'
        ]
        read_only_fields = [
            'created_at', 'updated_at', 'last_synced', 'full_path',
            'children_count', 'user_access_count'
        ]


class OrgUnitTreeSerializer(serializers.ModelSerializer):
    """
    Serializer for org unit tree structure
    """
    level_name = serializers.CharField(source='level.name', read_only=True)
    children = serializers.SerializerMethodField()
    user_access = serializers.SerializerMethodField()
    
    class Meta:
        model = OrgUnit
        fields = [
            'id', 'dhis2_uid', 'name', 'short_name', 'level', 'level_name',
            'parent', 'is_active', 'is_leaf', 'children', 'user_access'
        ]
    
    def get_children(self, obj):
        """Get children of this org unit"""
        children = obj.children.filter(is_active=True)
        return OrgUnitTreeSerializer(children, many=True).data
    
    def get_user_access(self, obj):
        """Get user access for this org unit"""
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return None
        
        access = obj.user_access.filter(
            user__dhis2_username=request.user.dhis2_username,
            is_active=True
        ).first()
        
        if access:
            return {
                'can_view_data': access.can_view_data,
                'can_edit_data': access.can_edit_data,
                'can_manage_users': access.can_manage_users,
                'can_export_data': access.can_export_data,
                'is_primary': access.is_primary
            }
        return None


class UserOrgUnitAccessSerializer(serializers.ModelSerializer):
    """
    Serializer for user org unit access
    """
    user_username = serializers.CharField(source='user.dhis2_username', read_only=True)
    user_display_name = serializers.CharField(source='user.dhis2_display_name', read_only=True)
    org_unit_name = serializers.CharField(source='org_unit.name', read_only=True)
    org_unit_level = serializers.CharField(source='org_unit.level.name', read_only=True)
    granted_by_username = serializers.CharField(source='granted_by.dhis2_username', read_only=True)
    is_expired = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = UserOrgUnitAccess
        fields = [
            'id', 'user', 'user_username', 'user_display_name', 'org_unit',
            'org_unit_name', 'org_unit_level', 'can_view_data', 'can_edit_data',
            'can_manage_users', 'can_export_data', 'include_children',
            'include_descendants', 'is_active', 'is_primary', 'granted_by',
            'granted_by_username', 'granted_at', 'expires_at', 'notes',
            'is_expired'
        ]
        read_only_fields = ['granted_at', 'is_expired']


class OrgUnitSyncLogSerializer(serializers.ModelSerializer):
    """
    Serializer for org unit sync logs
    """
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    duration_formatted = serializers.SerializerMethodField()
    
    class Meta:
        model = OrgUnitSyncLog
        fields = [
            'id', 'status', 'status_display', 'dhis2_instance_url', 'dhis2_user',
            'total_org_units', 'successful_org_units', 'failed_org_units',
            'total_levels', 'successful_levels', 'failed_levels',
            'error_message', 'error_details', 'started_at', 'completed_at',
            'duration_seconds', 'duration_formatted'
        ]
        read_only_fields = [
            'started_at', 'completed_at', 'duration_seconds', 'duration_formatted'
        ]
    
    def get_duration_formatted(self, obj):
        """Format duration in human-readable format"""
        if obj.duration_seconds is None:
            return None
        
        minutes = obj.duration_seconds // 60
        seconds = obj.duration_seconds % 60
        
        if minutes > 0:
            return f"{minutes}m {seconds}s"
        else:
            return f"{seconds}s"


class OrgUnitGroupSerializer(serializers.ModelSerializer):
    """
    Serializer for org unit groups
    """
    member_count = serializers.SerializerMethodField()
    
    class Meta:
        model = OrgUnitGroup
        fields = [
            'id', 'dhis2_uid', 'dhis2_code', 'name', 'short_name', 'description',
            'is_active', 'is_system_group', 'dhis2_created', 'dhis2_last_updated',
            'created_at', 'updated_at', 'last_synced', 'member_count'
        ]
        read_only_fields = ['created_at', 'updated_at', 'last_synced']
    
    def get_member_count(self, obj):
        """Get count of members in this group"""
        return obj.memberships.filter(is_active=True).count()


class OrgUnitGroupMembershipSerializer(serializers.ModelSerializer):
    """
    Serializer for org unit group memberships
    """
    org_unit_name = serializers.CharField(source='org_unit.name', read_only=True)
    org_unit_level = serializers.CharField(source='org_unit.level.name', read_only=True)
    group_name = serializers.CharField(source='group.name', read_only=True)
    
    class Meta:
        model = OrgUnitGroupMembership
        fields = [
            'id', 'org_unit', 'org_unit_name', 'org_unit_level', 'group',
            'group_name', 'is_active', 'created_at'
        ]
        read_only_fields = ['created_at']


# Create/Update serializers
class OrgUnitLevelCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating org unit levels
    """
    class Meta:
        model = OrgUnitLevel
        fields = [
            'level', 'name', 'display_name', 'description', 'dhis2_uid',
            'dhis2_code', 'parent_level', 'can_view_data', 'can_edit_data',
            'can_manage_users'
        ]


class OrgUnitCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating org units
    """
    class Meta:
        model = OrgUnit
        fields = [
            'dhis2_uid', 'dhis2_code', 'name', 'short_name', 'display_name',
            'level', 'parent', 'latitude', 'longitude', 'is_active', 'is_leaf',
            'can_view_data', 'can_edit_data', 'can_manage_users', 'dhis2_created',
            'dhis2_last_updated', 'dhis2_path'
        ]


class UserOrgUnitAccessCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating user org unit access
    """
    class Meta:
        model = UserOrgUnitAccess
        fields = [
            'user', 'org_unit', 'can_view_data', 'can_edit_data',
            'can_manage_users', 'can_export_data', 'include_children',
            'include_descendants', 'is_active', 'is_primary', 'granted_by',
            'expires_at', 'notes'
        ]


class OrgUnitGroupCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating org unit groups
    """
    class Meta:
        model = OrgUnitGroup
        fields = [
            'dhis2_uid', 'dhis2_code', 'name', 'short_name', 'description',
            'is_active', 'is_system_group', 'dhis2_created', 'dhis2_last_updated'
        ]


# Bulk operation serializers
class BulkUserAccessSerializer(serializers.Serializer):
    """
    Serializer for bulk user access operations
    """
    user_ids = serializers.ListField(
        child=serializers.IntegerField(),
        help_text="List of user IDs"
    )
    org_unit_ids = serializers.ListField(
        child=serializers.IntegerField(),
        help_text="List of org unit IDs"
    )
    permissions = serializers.DictField(
        child=serializers.BooleanField(),
        default={
            'can_view_data': True,
            'can_edit_data': False,
            'can_manage_users': False,
            'can_export_data': True
        },
        help_text="Permissions to grant"
    )
    include_children = serializers.BooleanField(default=True)
    include_descendants = serializers.BooleanField(default=True)
    is_primary = serializers.BooleanField(default=False)
    notes = serializers.CharField(max_length=500, required=False)


class OrgUnitSyncRequestSerializer(serializers.Serializer):
    """
    Serializer for org unit sync requests
    """
    dhis2_instance_url = serializers.URLField(
        required=False,
        help_text="DHIS2 instance URL (uses session default if not provided)"
    )
    sync_levels = serializers.BooleanField(
        default=True,
        help_text="Whether to sync org unit levels"
    )
    sync_org_units = serializers.BooleanField(
        default=True,
        help_text="Whether to sync org units"
    )
    sync_groups = serializers.BooleanField(
        default=True,
        help_text="Whether to sync org unit groups"
    )
    org_unit_ids = serializers.ListField(
        child=serializers.CharField(max_length=255),
        required=False,
        help_text="Specific org unit IDs to sync"
    )
    level_ids = serializers.ListField(
        child=serializers.CharField(max_length=255),
        required=False,
        help_text="Specific level IDs to sync"
    )


# Access control serializers
class UserAccessSummarySerializer(serializers.Serializer):
    """
    Serializer for user access summary
    """
    user_id = serializers.IntegerField()
    username = serializers.CharField(max_length=255)
    display_name = serializers.CharField(max_length=255)
    primary_org_unit = serializers.CharField(max_length=255, allow_null=True)
    accessible_org_units_count = serializers.IntegerField()
    can_view_data = serializers.BooleanField()
    can_edit_data = serializers.BooleanField()
    can_manage_users = serializers.BooleanField()
    can_export_data = serializers.BooleanField()


class OrgUnitAccessSummarySerializer(serializers.Serializer):
    """
    Serializer for org unit access summary
    """
    org_unit_id = serializers.IntegerField()
    org_unit_name = serializers.CharField(max_length=255)
    org_unit_level = serializers.CharField(max_length=255)
    user_count = serializers.IntegerField()
    primary_user_count = serializers.IntegerField()
    can_view_data_count = serializers.IntegerField()
    can_edit_data_count = serializers.IntegerField()
    can_manage_users_count = serializers.IntegerField()


# Hierarchy serializers
class OrgUnitHierarchySerializer(serializers.Serializer):
    """
    Serializer for org unit hierarchy data
    """
    org_unit_id = serializers.IntegerField()
    org_unit_name = serializers.CharField(max_length=255)
    level_name = serializers.CharField(max_length=255)
    parent_id = serializers.IntegerField(allow_null=True)
    parent_name = serializers.CharField(max_length=255, allow_null=True)
    children_count = serializers.IntegerField()
    descendants_count = serializers.IntegerField()
    depth = serializers.IntegerField()
    path = serializers.ListField(child=serializers.CharField())


class OrgUnitSearchSerializer(serializers.Serializer):
    """
    Serializer for org unit search
    """
    query = serializers.CharField(
        max_length=255,
        help_text="Search query for org unit name or code"
    )
    level_ids = serializers.ListField(
        child=serializers.IntegerField(),
        required=False,
        help_text="Filter by org unit levels"
    )
    parent_id = serializers.IntegerField(
        required=False,
        help_text="Filter by parent org unit"
    )
    is_active = serializers.BooleanField(
        required=False,
        help_text="Filter by active status"
    )
    limit = serializers.IntegerField(
        default=50,
        min_value=1,
        max_value=1000,
        help_text="Maximum number of results"
    ) 