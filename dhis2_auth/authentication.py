from rest_framework import authentication
from rest_framework import exceptions
from django.contrib.auth.models import AnonymousUser
from .session import is_dhis2_authenticated, get_dhis2_user


class DHIS2SessionAuthentication(authentication.BaseAuthentication):
    """
    Custom authentication class for DHIS2 session-based authentication.
    """
    
    def authenticate(self, request):
        """
        Authenticate the request using DHIS2 session.
        """
        session_key = request.session.session_key
        
        if not session_key:
            return None
        
        # Check if DHIS2 session is valid
        if not is_dhis2_authenticated(session_key):
            return None
        
        # Get DHIS2 user
        dhis2_user = get_dhis2_user(session_key)
        if not dhis2_user:
            return None
        
        # Create a user object that DRF can work with
        user = DHIS2UserWrapper(dhis2_user)
        
        return (user, None)
    
    def authenticate_header(self, request):
        """
        Return a string to be used as the value of the `WWW-Authenticate`
        header in a `401 Unauthenticated` response.
        """
        return 'DHIS2-Session'


class DHIS2UserWrapper:
    """
    Wrapper class to make DHIS2 user compatible with DRF authentication.
    """
    
    def __init__(self, dhis2_user):
        self.dhis2_user = dhis2_user
        self.is_authenticated = True
        self.is_anonymous = False
    
    def __getattr__(self, name):
        # Delegate attribute access to the underlying DHIS2 user
        return getattr(self.dhis2_user, name)
    
    @property
    def id(self):
        return self.dhis2_user.id
    
    @property
    def username(self):
        return self.dhis2_user.dhis2_username
    
    @property
    def is_active(self):
        return True
    
    @property
    def is_staff(self):
        return False
    
    @property
    def is_superuser(self):
        return False
    
    def has_perm(self, perm, obj=None):
        return False
    
    def has_perms(self, perm_list, obj=None):
        return False
    
    def has_module_perms(self, app_label):
        return False
    
    def get_username(self):
        return self.dhis2_user.dhis2_username
    
    def get_full_name(self):
        return self.dhis2_user.dhis2_username
    
    def get_short_name(self):
        return self.dhis2_user.dhis2_username
    
    def __str__(self):
        return self.dhis2_user.dhis2_username
    
    def __repr__(self):
        return f'<DHIS2UserWrapper: {self.dhis2_user.dhis2_username}>' 