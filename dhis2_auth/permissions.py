from rest_framework import permissions


class DHIS2AuthenticatedOrReadOnly(permissions.BasePermission):
    """
    Custom permission class that allows read-only access to unauthenticated users
    and full access to authenticated DHIS2 users.
    """
    
    def has_permission(self, request, view):
        # Allow read-only access to unauthenticated users
        if request.method in permissions.SAFE_METHODS:
            return True
        
        # Require authentication for write operations
        return request.user and request.user.is_authenticated


class DHIS2AuthenticatedOnly(permissions.BasePermission):
    """
    Permission class that requires DHIS2 authentication for all operations.
    """
    
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated 