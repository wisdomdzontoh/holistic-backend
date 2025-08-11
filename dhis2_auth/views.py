import logging
import requests
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from django.utils import timezone
from django.conf import settings
from django.db import IntegrityError, DatabaseError

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
            try:
                if not client.test_connection():
                    return Response(
                        {
                            'success': False,
                            'message': 'Unable to connect to DHIS2 instance. Please check the URL and ensure the server is accessible.'
                        },
                        status=status.HTTP_400_BAD_REQUEST
                    )
            except Exception as e:
                logger.error(f"Connection test failed: {str(e)}")
                return Response(
                    {
                        'success': False,
                        'message': f'Connection test failed: {str(e)}. Please check the DHIS2 instance URL and network connectivity.'
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Authenticate user
            user_info = client.authenticate_user()
            
            # Extract DHIS2 cookies from the client session
            dhis2_cookies = {}
            for cookie in client.session.cookies:
                dhis2_cookies[cookie.name] = cookie.value
            
            logger.info(f"Extracted {len(dhis2_cookies)} DHIS2 cookies from session")
            
            # Create session
            session_key = request.session.session_key
            if not session_key:
                request.session.create()
                session_key = request.session.session_key
            
            try:
                dhis2_session = create_dhis2_session(
                    user_info=user_info,
                    instance_url=instance_url,
                    session_key=session_key,
                    request=request,
                    dhis2_cookies=dhis2_cookies,
                    username=username,
                    password=password
                )
            except IntegrityError as e:
                logger.error(f"Database integrity error during session creation: {str(e)}")
                return Response(
                    {
                        'success': False,
                        'message': 'Session creation failed. Please try again.'
                    },
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
            except DatabaseError as e:
                logger.error(f"Database error during session creation: {str(e)}")
                return Response(
                    {
                        'success': False,
                        'message': 'Database error occurred. Please try again.'
                    },
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
            
            # Prepare response
            user_serializer = UserInfoSerializer(dhis2_session.user)
            response_data = {
                'success': True,
                'message': 'Login successful',
                'user': user_serializer.data,
                'session': {
                    'expiresAt': dhis2_session.expires_at.isoformat(),
                    'dhis2Instance': instance_url
                }
            }
            
            logger.info(f"Successful login for user {username} from {instance_url}")
            return Response(response_data, status=status.HTTP_200_OK)
            
        except requests.RequestException as e:
            logger.error(f"Login failed for user {username} from {instance_url}: {str(e)}")
            if hasattr(e, 'response') and e.response:
                if e.response.status_code == 401:
                    return Response(
                        {
                            'success': False,
                            'message': 'Authentication failed. Please check your username and password.'
                        },
                        status=status.HTTP_401_UNAUTHORIZED
                    )
                elif e.response.status_code == 403:
                    return Response(
                        {
                            'success': False,
                            'message': 'Access forbidden. Your account may not have the required permissions.'
                        },
                        status=status.HTTP_403_FORBIDDEN
                    )
                else:
                    return Response(
                        {
                            'success': False,
                            'message': f'DHIS2 server error: {e.response.status_code} - {e.response.text[:200]}'
                        },
                        status=status.HTTP_502_BAD_GATEWAY
                    )
            else:
                return Response(
                    {
                        'success': False,
                        'message': f'Connection error: {str(e)}. Please check your network connection.'
                    },
                    status=status.HTTP_502_BAD_GATEWAY
                )
        except Exception as e:
            logger.error(f"Login failed for user {username} from {instance_url}: {str(e)}")
            return Response(
                {
                    'success': False,
                    'message': 'Authentication failed. Please check your credentials and try again.'
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
                    'isAuthenticated': False,
                    'message': 'No active session'
                },
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        # Check if DHIS2 session is valid
        if not is_dhis2_authenticated(session_key):
            return Response(
                {
                    'isAuthenticated': False,
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
                    'isAuthenticated': False,
                    'message': 'Session data not found'
                },
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        # Prepare response
        user_serializer = UserInfoSerializer(dhis2_user)
        org_units = get_user_org_units(session_key)
        
        response_data = {
            'isAuthenticated': True,
            'user': user_serializer.data,
            'session': {
                'expiresAt': session_data['expires_at'],
                'dhis2Instance': session_data['instance_url']
            },
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


class OrgUnitDescendantsView(APIView):
    """
    View to get all descendants of an organisation unit.
    """
    
    def get(self, request, org_unit_id):
        """
        Get all descendants of an organisation unit.
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
            session_data = get_dhis2_session_data(session_key)
            
            # Create DHIS2 client
            client = DHIS2Client(
                instance_url=session_data['instance_url'],
                session_key=session_key
            )
            
            # Get descendants
            descendants = client.get_org_unit_descendants(org_unit_id)
            
            return Response(
                {
                    'success': True,
                    'descendants': descendants,
                    'total': len(descendants)
                },
                status=status.HTTP_200_OK
            )
            
        except Exception as e:
            logger.error(f"Error fetching org unit descendants: {str(e)}")
            return Response(
                {
                    'success': False,
                    'message': 'Error fetching organisation unit descendants'
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class OrgUnitChildrenView(APIView):
    """
    View to get immediate children of an organisation unit.
    """
    
    def get(self, request, org_unit_id):
        """
        Get immediate children of an organisation unit.
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
            session_data = get_dhis2_session_data(session_key)
            
            # Create DHIS2 client
            client = DHIS2Client(
                instance_url=session_data['instance_url'],
                session_key=session_key
            )
            
            # Get children
            children = client.get_org_unit_children(org_unit_id)
            
            return Response(
                {
                    'success': True,
                    'children': children,
                    'total': len(children)
                },
                status=status.HTTP_200_OK
            )
            
        except Exception as e:
            logger.error(f"Error fetching org unit children: {str(e)}")
            return Response(
                {
                    'success': False,
                    'message': 'Error fetching organisation unit children'
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


@api_view(['GET'])
def debug_session(request):
    """
    Debug endpoint to check session status and authentication
    """
    session_key = request.session.session_key
    session_data = None
    
    if session_key:
        from .session import get_dhis2_session_data
        session_data = get_dhis2_session_data(session_key)
    
    return Response({
        'session_key': session_key,
        'has_session': bool(session_key),
        'session_data': session_data,
        'is_authenticated': bool(session_data),
        'cookies': dict(request.COOKIES),
        'headers': {
            'origin': request.headers.get('Origin'),
            'referer': request.headers.get('Referer'),
            'user_agent': request.headers.get('User-Agent'),
        }
    })
