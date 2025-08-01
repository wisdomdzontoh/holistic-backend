import logging
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from django.utils import timezone
from django.conf import settings

from .serializers import (
    LoginSerializer, LoginResponseSerializer, LogoutResponseSerializer,
    SessionStatusSerializer, UserInfoSerializer, OrgUnitSerializer
)
from .dhis_client import DHIS2Client
from .session import (
    create_dhis2_session, get_dhis2_session_data, logout_dhis2_user,
    is_dhis2_authenticated, get_dhis2_user, get_user_org_units, has_authority
)

logger = logging.getLogger(__name__)


class LoginView(APIView):
    """
    Login view that accepts DHIS2 instance URL, username, and password.
    Authenticates against DHIS2 and creates a session.
    """
    permission_classes = [AllowAny]
    
    def post(self, request):
        """
        Authenticate user with DHIS2 credentials.
        
        Expected payload:
        {
            "instance_url": "https://dhims.chimgh.org/dhims",
            "username": "user@example.com",
            "password": "password123"
        }
        """
        serializer = LoginSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {
                    'success': False,
                    'message': 'Invalid input data',
                    'errors': serializer.errors
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        
        instance_url = serializer.validated_data['instance_url']
        username = serializer.validated_data['username']
        password = serializer.validated_data['password']
        
        try:
            # Create DHIS2 client and authenticate
            client = DHIS2Client(
                instance_url=instance_url,
                username=username,
                password=password
            )
            
            # Test connection and authenticate
            if not client.test_connection():
                return Response(
                    {
                        'success': False,
                        'message': 'Unable to connect to DHIS2 instance. Please check the URL.'
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Authenticate user
            user_info = client.authenticate_user()
            
            # Create session
            session_key = request.session.session_key
            if not session_key:
                request.session.create()
                session_key = request.session.session_key
            
            dhis2_session = create_dhis2_session(
                user_info=user_info,
                instance_url=instance_url,
                session_key=session_key,
                request=request
            )
            
            # Prepare response
            user_serializer = UserInfoSerializer(dhis2_session.user)
            response_data = {
                'success': True,
                'message': 'Login successful',
                'user': user_serializer.data,
                'session_key': session_key,
                'expires_at': dhis2_session.expires_at
            }
            
            logger.info(f"Successful login for user {username} from {instance_url}")
            return Response(response_data, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Login failed for user {username} from {instance_url}: {str(e)}")
            return Response(
                {
                    'success': False,
                    'message': 'Authentication failed. Please check your credentials.'
                },
                status=status.HTTP_401_UNAUTHORIZED
            )


class LogoutView(APIView):
    """
    Logout view to invalidate DHIS2 session.
    """
    
    def post(self, request):
        """
        Logout user and invalidate session.
        """
        session_key = request.session.session_key
        
        if not session_key:
            return Response(
                {
                    'success': False,
                    'message': 'No active session found'
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Logout from DHIS2 session
        logout_success = logout_dhis2_user(session_key)
        
        # Clear Django session
        request.session.flush()
        
        if logout_success:
            return Response(
                {
                    'success': True,
                    'message': 'Logout successful'
                },
                status=status.HTTP_200_OK
            )
        else:
            return Response(
                {
                    'success': False,
                    'message': 'Logout failed'
                },
                status=status.HTTP_400_BAD_REQUEST
            )


class SessionStatusView(APIView):
    """
    View to check current session status and user information.
    """
    
    def get(self, request):
        """
        Get current session status and user information.
        """
        session_key = request.session.session_key
        
        if not session_key:
            return Response(
                {
                    'is_authenticated': False,
                    'message': 'No active session'
                },
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        # Check if DHIS2 session is valid
        if not is_dhis2_authenticated(session_key):
            return Response(
                {
                    'is_authenticated': False,
                    'message': 'Session expired or invalid'
                },
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        # Get session data
        session_data = get_dhis2_session_data(session_key)
        dhis2_user = get_dhis2_user(session_key)
        
        if not session_data or not dhis2_user:
            return Response(
                {
                    'is_authenticated': False,
                    'message': 'Session data not found'
                },
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        # Prepare response
        user_serializer = UserInfoSerializer(dhis2_user)
        org_units = get_user_org_units(session_key)
        
        response_data = {
            'is_authenticated': True,
            'user': user_serializer.data,
            'session_expires_at': session_data['expires_at'],
            'org_units': org_units,
            'authorities': session_data.get('authorities', [])
        }
        
        return Response(response_data, status=status.HTTP_200_OK)


class OrgUnitsView(APIView):
    """
    View to get user's accessible organisation units.
    """
    
    def get(self, request):
        """
        Get organisation units accessible to the authenticated user.
        """
        session_key = request.session.session_key
        
        if not session_key or not is_dhis2_authenticated(session_key):
            return Response(
                {
                    'success': False,
                    'message': 'Authentication required'
                },
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        try:
            org_units = get_user_org_units(session_key)
            session_data = get_dhis2_session_data(session_key)
            
            # Create DHIS2 client to get detailed org unit info
            client = DHIS2Client(
                instance_url=session_data['instance_url'],
                session_key=session_key
            )
            
            # Get detailed org unit tree
            org_unit_tree = client.get_org_unit_tree()
            
            return Response(
                {
                    'success': True,
                    'org_units': org_units,
                    'org_unit_tree': org_unit_tree
                },
                status=status.HTTP_200_OK
            )
            
        except Exception as e:
            logger.error(f"Error fetching org units: {str(e)}")
            return Response(
                {
                    'success': False,
                    'message': 'Error fetching organisation units'
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class AuthorityCheckView(APIView):
    """
    View to check if user has specific DHIS2 authorities.
    """
    
    def post(self, request):
        """
        Check if user has specific authorities.
        
        Expected payload:
        {
            "authorities": ["F_DATASET_ADD", "F_INDICATOR_ADD"]
        }
        """
        session_key = request.session.session_key
        
        if not session_key or not is_dhis2_authenticated(session_key):
            return Response(
                {
                    'success': False,
                    'message': 'Authentication required'
                },
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        authorities = request.data.get('authorities', [])
        if not isinstance(authorities, list):
            return Response(
                {
                    'success': False,
                    'message': 'Authorities must be a list'
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check each authority
        authority_results = []
        for authority in authorities:
            has_auth = has_authority(session_key, authority)
            authority_results.append({
                'authority': authority,
                'has_authority': has_auth
            })
        
        return Response(
            {
                'success': True,
                'authorities': authority_results
            },
            status=status.HTTP_200_OK
        )


@api_view(['GET'])
@permission_classes([AllowAny])
def health_check(request):
    """
    Health check endpoint for DHIS2 authentication service.
    """
    return Response(
        {
            'status': 'healthy',
            'service': 'dhis2_auth',
            'timestamp': timezone.now().isoformat()
        },
        status=status.HTTP_200_OK
    )
