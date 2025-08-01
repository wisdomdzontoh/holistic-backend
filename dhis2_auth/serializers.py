from rest_framework import serializers
from .models import DHIS2User, DHIS2Session


class LoginSerializer(serializers.Serializer):
    """
    Serializer for DHIS2 login credentials.
    """
    instance_url = serializers.URLField(
        help_text="DHIS2 instance URL (e.g., https://dhims.chimgh.org/dhims)"
    )
    username = serializers.CharField(
        max_length=255,
        help_text="DHIS2 username"
    )
    password = serializers.CharField(
        max_length=255,
        write_only=True,
        help_text="DHIS2 password"
    )
    
    def validate_instance_url(self, value):
        """Validate DHIS2 instance URL"""
        if not value.startswith(('http://', 'https://')):
            raise serializers.ValidationError("Instance URL must start with http:// or https://")
        return value.rstrip('/')


class UserInfoSerializer(serializers.ModelSerializer):
    """
    Serializer for DHIS2 user information.
    """
    class Meta:
        model = DHIS2User
        fields = [
            'id', 'dhis2_username', 'dhis2_instance_url', 'dhis2_user_id',
            'dhis2_org_units', 'dhis2_authorities', 'dhis2_user_groups',
            'first_login', 'last_login', 'login_count', 'is_active'
        ]
        read_only_fields = [
            'id', 'dhis2_user_id', 'dhis2_org_units', 'dhis2_authorities',
            'dhis2_user_groups', 'first_login', 'last_login', 'login_count'
        ]


class SessionInfoSerializer(serializers.ModelSerializer):
    """
    Serializer for DHIS2 session information.
    """
    user = UserInfoSerializer(read_only=True)
    
    class Meta:
        model = DHIS2Session
        fields = [
            'id', 'user', 'session_key', 'dhis2_instance_url',
            'created_at', 'expires_at', 'is_active', 'ip_address', 'user_agent'
        ]
        read_only_fields = [
            'id', 'user', 'session_key', 'dhis2_instance_url',
            'created_at', 'expires_at', 'ip_address', 'user_agent'
        ]


class LoginResponseSerializer(serializers.Serializer):
    """
    Serializer for login response.
    """
    success = serializers.BooleanField()
    message = serializers.CharField()
    user = UserInfoSerializer()
    session_key = serializers.CharField()
    expires_at = serializers.DateTimeField()


class LogoutResponseSerializer(serializers.Serializer):
    """
    Serializer for logout response.
    """
    success = serializers.BooleanField()
    message = serializers.CharField()


class OrgUnitSerializer(serializers.Serializer):
    """
    Serializer for organisation unit information.
    """
    id = serializers.CharField()
    name = serializers.CharField()
    level = serializers.IntegerField(required=False)
    parent = serializers.CharField(required=False, allow_null=True)
    children = serializers.ListField(required=False)
    ancestors = serializers.ListField(required=False)


class AuthoritySerializer(serializers.Serializer):
    """
    Serializer for DHIS2 authority information.
    """
    authority = serializers.CharField()
    has_authority = serializers.BooleanField()


class SessionStatusSerializer(serializers.Serializer):
    """
    Serializer for session status check.
    """
    is_authenticated = serializers.BooleanField()
    user = UserInfoSerializer(required=False, allow_null=True)
    session_expires_at = serializers.DateTimeField(required=False, allow_null=True)
    org_units = serializers.ListField(child=OrgUnitSerializer(), required=False)
    authorities = serializers.ListField(required=False) 