import json
import logging
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from django.conf import settings
from django.core.cache import cache
from django.contrib.sessions.models import Session
from django.utils import timezone
from .models import DHIS2User, DHIS2Session

logger = logging.getLogger(__name__)


def create_dhis2_session(user_info: Dict[str, Any], instance_url: str, 
                        session_key: str, request=None) -> DHIS2Session:
    """
    Create a new DHIS2 session and store user metadata.
    
    Args:
        user_info: User information from DHIS2 /api/me endpoint
        instance_url: DHIS2 instance URL
        session_key: Django session key
        request: Django request object (optional)
        
    Returns:
        DHIS2Session instance
    """
    # Extract user data
    username = user_info.get('username')
    user_id = user_info.get('id')
    org_units = user_info.get('organisationUnits', [])
    authorities = user_info.get('userCredentials', {}).get('userAuthorityGroups', [])
    user_groups = user_info.get('userGroups', [])
    
    # Get or create DHIS2User
    dhis2_user, created = DHIS2User.objects.get_or_create(
        dhis2_username=username,
        dhis2_instance_url=instance_url,
        defaults={
            'dhis2_user_id': user_id,
            'dhis2_org_units': org_units,
            'dhis2_authorities': authorities,
            'dhis2_user_groups': user_groups,
        }
    )
    
    # Update user data if not newly created
    if not created:
        dhis2_user.dhis2_user_id = user_id
        dhis2_user.dhis2_org_units = org_units
        dhis2_user.dhis2_authorities = authorities
        dhis2_user.dhis2_user_groups = user_groups
        dhis2_user.save()
    
    # Update login stats
    dhis2_user.update_login_stats(session_key)
    
    # Create session record
    session_expiry = timezone.now() + timedelta(hours=24)  # 24 hour session
    
    session_data = {
        'user_id': dhis2_user.id,
        'username': username,
        'instance_url': instance_url,
        'org_units': org_units,
        'authorities': authorities,
        'user_groups': user_groups,
        'created_at': timezone.now().isoformat(),
        'expires_at': session_expiry.isoformat(),
    }
    
    # Store in Django session
    if request and hasattr(request, 'session'):
        request.session['dhis2_auth'] = session_data
        request.session['dhis2_instance_url'] = instance_url
        request.session.set_expiry(24 * 60 * 60)  # 24 hours
    
    # Store in cache for quick access
    cache_key = f"dhis2_session_{session_key}"
    cache.set(cache_key, session_data, timeout=24 * 60 * 60)  # 24 hours
    
    # Create database session record
    dhis2_session = DHIS2Session.objects.create(
        user=dhis2_user,
        session_key=session_key,
        dhis2_instance_url=instance_url,
        expires_at=session_expiry,
        ip_address=getattr(request, 'META', {}).get('REMOTE_ADDR'),
        user_agent=getattr(request, 'META', {}).get('HTTP_USER_AGENT', ''),
    )
    
    logger.info(f"Created DHIS2 session for user {username} from {instance_url}")
    return dhis2_session


def get_dhis2_session_data(session_key: str) -> Optional[Dict[str, Any]]:
    """
    Get DHIS2 session data from cache or database.
    
    Args:
        session_key: Django session key
        
    Returns:
        Session data dictionary or None if not found/expired
    """
    # Try cache first
    cache_key = f"dhis2_session_{session_key}"
    session_data = cache.get(cache_key)
    
    if session_data:
        # Check if session is expired
        expires_at = datetime.fromisoformat(session_data['expires_at'])
        if timezone.now() > expires_at:
            cache.delete(cache_key)
            return None
        return session_data
    
    # Try database
    try:
        dhis2_session = DHIS2Session.objects.get(
            session_key=session_key,
            is_active=True
        )
        
        if dhis2_session.is_expired():
            dhis2_session.deactivate()
            return None
        
        # Reconstruct session data
        session_data = {
            'user_id': dhis2_session.user.id,
            'username': dhis2_session.user.dhis2_username,
            'instance_url': dhis2_session.dhis2_instance_url,
            'org_units': dhis2_session.user.dhis2_org_units,
            'authorities': dhis2_session.user.dhis2_authorities,
            'user_groups': dhis2_session.user.dhis2_user_groups,
            'created_at': dhis2_session.created_at.isoformat(),
            'expires_at': dhis2_session.expires_at.isoformat(),
        }
        
        # Store in cache for future requests
        cache.set(cache_key, session_data, timeout=24 * 60 * 60)
        
        return session_data
        
    except DHIS2Session.DoesNotExist:
        return None


def is_dhis2_authenticated(session_key: str) -> bool:
    """
    Check if user is authenticated with DHIS2.
    
    Args:
        session_key: Django session key
        
    Returns:
        True if authenticated, False otherwise
    """
    session_data = get_dhis2_session_data(session_key)
    return session_data is not None


def get_dhis2_user(session_key: str) -> Optional[DHIS2User]:
    """
    Get DHIS2User instance from session.
    
    Args:
        session_key: Django session key
        
    Returns:
        DHIS2User instance or None
    """
    session_data = get_dhis2_session_data(session_key)
    if not session_data:
        return None
    
    try:
        return DHIS2User.objects.get(id=session_data['user_id'])
    except DHIS2User.DoesNotExist:
        return None


def logout_dhis2_user(session_key: str) -> bool:
    """
    Logout DHIS2 user by invalidating session.
    
    Args:
        session_key: Django session key
        
    Returns:
        True if logout successful, False otherwise
    """
    # Remove from cache
    cache_key = f"dhis2_session_{session_key}"
    cache.delete(cache_key)
    
    # Deactivate database session
    try:
        dhis2_session = DHIS2Session.objects.get(session_key=session_key)
        dhis2_session.deactivate()
        logger.info(f"Logged out DHIS2 user {dhis2_session.user.dhis2_username}")
        return True
    except DHIS2Session.DoesNotExist:
        return False


def cleanup_expired_sessions():
    """
    Clean up expired DHIS2 sessions.
    This should be run periodically (e.g., via management command or cron).
    """
    expired_sessions = DHIS2Session.objects.filter(
        expires_at__lt=timezone.now(),
        is_active=True
    )
    
    count = expired_sessions.count()
    expired_sessions.update(is_active=False)
    
    logger.info(f"Cleaned up {count} expired DHIS2 sessions")


def get_user_org_units(session_key: str) -> list:
    """
    Get organisation units accessible to the user.
    
    Args:
        session_key: Django session key
        
    Returns:
        List of organisation units
    """
    session_data = get_dhis2_session_data(session_key)
    if not session_data:
        return []
    
    return session_data.get('org_units', [])


def has_authority(session_key: str, authority: str) -> bool:
    """
    Check if user has a specific DHIS2 authority.
    
    Args:
        session_key: Django session key
        authority: Authority to check
        
    Returns:
        True if user has authority, False otherwise
    """
    session_data = get_dhis2_session_data(session_key)
    if not session_data:
        return False
    
    authorities = session_data.get('authorities', [])
    return authority in authorities


def get_session_info(session_key: str) -> Optional[Dict[str, Any]]:
    """
    Get comprehensive session information.
    
    Args:
        session_key: Django session key
        
    Returns:
        Session information dictionary or None
    """
    session_data = get_dhis2_session_data(session_key)
    if not session_data:
        return None
    
    try:
        dhis2_user = DHIS2User.objects.get(id=session_data['user_id'])
        return {
            'session_data': session_data,
            'user': {
                'id': dhis2_user.id,
                'username': dhis2_user.dhis2_username,
                'instance_url': dhis2_user.dhis2_instance_url,
                'login_count': dhis2_user.login_count,
                'first_login': dhis2_user.first_login.isoformat(),
                'last_login': dhis2_user.last_login.isoformat(),
            }
        }
    except DHIS2User.DoesNotExist:
        return None 