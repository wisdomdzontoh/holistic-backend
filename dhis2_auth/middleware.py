import logging
from django.utils import timezone
from django.http import JsonResponse
from django.conf import settings
from .session import is_dhis2_authenticated, get_dhis2_session_data, logout_dhis2_user

logger = logging.getLogger(__name__)


class DHIS2SessionMiddleware:
    """
    Middleware to check DHIS2 session validity and handle session management.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # Process request
        response = self.get_response(request)
        return response
    
    def process_view(self, request, view_func, view_args, view_kwargs):
        """
        Process view to check DHIS2 session validity.
        """
        # Skip middleware for certain paths
        if self._should_skip_middleware(request.path):
            print(f"DEBUG: Skipping middleware for path: {request.path}")
            return None
        
        session_key = request.session.session_key
        
        # If no session key, allow the request to proceed
        if not session_key:
            print(f"DEBUG: No session key for path: {request.path}")
            return None
        
        # Check if DHIS2 session is valid
        if not is_dhis2_authenticated(session_key):
            print(f"DEBUG: DHIS2 session not authenticated for path: {request.path}")
            # Only clear session for API requests that require authentication
            # Don't clear session for debug endpoints or public endpoints
            if request.path.startswith('/api/') and not self._is_public_endpoint(request.path):
                print(f"DEBUG: Clearing session for path: {request.path}")
                # Session is invalid, clear it
                logout_dhis2_user(session_key)
                request.session.flush()
                
                return JsonResponse(
                    {
                        'success': False,
                        'message': 'Session expired. Please login again.',
                        'code': 'SESSION_EXPIRED'
                    },
                    status=401
                )
            else:
                print(f"DEBUG: Not clearing session for public endpoint: {request.path}")
            
            return None
        
        # Add DHIS2 session data to request for easy access
        session_data = get_dhis2_session_data(session_key)
        if session_data:
            request.dhis2_session = session_data
            request.dhis2_user_id = session_data.get('user_id')
            request.dhis2_username = session_data.get('username')
            request.dhis2_instance_url = session_data.get('instance_url')
            request.dhis2_org_units = session_data.get('org_units', [])
            request.dhis2_authorities = session_data.get('authorities', [])
        
        return None
    
    def _should_skip_middleware(self, path):
        """
        Check if middleware should be skipped for this path.
        """
        skip_paths = [
            '/api/dhis2-auth/login/',
            '/api/dhis2-auth/logout/',
            '/api/dhis2-auth/health/',
            '/api/dhis2-auth/debug-session/',
            '/api/dhis2-auth/test-auth/',
            '/admin/',
            '/static/',
            '/media/',
        ]
        
        return any(path.startswith(skip_path) for skip_path in skip_paths)
    
    def _is_public_endpoint(self, path):
        """
        Check if this is a public endpoint that doesn't require authentication.
        """
        public_paths = [
            '/api/dhis2-auth/debug-session/',
            '/api/dhis2-auth/test-auth/',
            '/api/dhis2-auth/health/',
        ]
        
        return any(path.startswith(public_path) for public_path in public_paths)


class DHIS2AuthenticationMiddleware:
    """
    Middleware to add DHIS2 authentication context to requests.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # Add DHIS2 authentication context
        request.is_dhis2_authenticated = False
        request.dhis2_user = None
        
        session_key = request.session.session_key
        if session_key and is_dhis2_authenticated(session_key):
            from .session import get_dhis2_user
            request.is_dhis2_authenticated = True
            request.dhis2_user = get_dhis2_user(session_key)
        
        response = self.get_response(request)
        return response


class DHIS2SessionCleanupMiddleware:
    """
    Middleware to periodically clean up expired sessions.
    """

    # Paths that must never be delayed by a DB-touching cleanup call - notably
    # the health check, which Render (and any free-tier host that spins the
    # service down after idle) polls on every cold start. A fresh worker's
    # last_cleanup is always None, so without this guard the very first
    # request after a cold start - frequently the health check itself -
    # triggers a cleanup query. If the DB (e.g. Neon, which also auto-suspends
    # on the free tier) is cold at that exact moment, the request blocks with
    # no timeout, the health check never responds, and the deploy times out.
    SKIP_PATHS = ('/api/health/', '/static/', '/media/')

    def __init__(self, get_response):
        self.get_response = get_response
        self.last_cleanup = None

    def __call__(self, request):
        # Clean up expired sessions every hour
        if not request.path.startswith(self.SKIP_PATHS) and self._should_cleanup():
            from .session import cleanup_expired_sessions
            try:
                cleanup_expired_sessions()
                self.last_cleanup = timezone.now()
                logger.info("DHIS2 session cleanup completed")
            except Exception as e:
                logger.error(f"Error during DHIS2 session cleanup: {str(e)}")

        response = self.get_response(request)
        return response
    
    def _should_cleanup(self):
        """
        Check if cleanup should be performed.
        """
        if not self.last_cleanup:
            return True
        
        # Clean up every hour
        return (timezone.now() - self.last_cleanup).total_seconds() > 3600 