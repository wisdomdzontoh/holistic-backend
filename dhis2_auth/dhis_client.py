import requests
import base64
import json
import logging
from typing import Dict, List, Optional, Any
from urllib.parse import urljoin
from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger(__name__)


class DHIS2Client:
    """
    Central client for making DHIS2 API calls.
    Handles authentication, session management, and common API operations.
    """
    
    def __init__(self, instance_url: str, username: str = None, password: str = None, session_key: str = None):
        """
        Initialize DHIS2 client.
        
        Args:
            instance_url: DHIS2 instance URL (e.g., https://dhims.chimgh.org/dhims)
            username: DHIS2 username for Basic Auth
            password: DHIS2 password for Basic Auth
            session_key: Django session key for authenticated requests
        """
        self.instance_url = instance_url.rstrip('/')
        self.username = username
        self.password = password
        self.session_key = session_key
        self.session = requests.Session()
        
        # Set default headers
        self.session.headers.update({
            'Content-Type': 'application/json',
            'Accept': 'application/json',
        })
        
        # Set up Basic Auth if credentials provided
        if username and password:
            self._setup_basic_auth(username, password)
    
    def _setup_basic_auth(self, username: str, password: str):
        """Set up Basic Authentication headers"""
        credentials = f"{username}:{password}"
        encoded_credentials = base64.b64encode(credentials.encode()).decode()
        self.session.headers.update({
            'Authorization': f'Basic {encoded_credentials}'
        })
    
    def _get_full_url(self, endpoint: str) -> str:
        """Get full URL for an endpoint"""
        return urljoin(self.instance_url, endpoint)
    
    def _make_request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """
        Make HTTP request to DHIS2 API.
        
        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint (e.g., '/api/me')
            **kwargs: Additional request parameters
            
        Returns:
            Response data as dictionary
            
        Raises:
            requests.RequestException: For HTTP errors
        """
        url = self._get_full_url(endpoint)
        
        try:
            response = self.session.request(method, url, **kwargs)
            response.raise_for_status()
            
            # Handle empty responses
            if response.status_code == 204:
                return {}
            
            return response.json()
            
        except requests.RequestException as e:
            logger.error(f"DHIS2 API request failed: {method} {url} - {str(e)}")
            raise
    
    def authenticate_user(self) -> Dict[str, Any]:
        """
        Authenticate user by calling /api/me endpoint.
        
        Returns:
            User information from DHIS2
            
        Raises:
            requests.RequestException: If authentication fails
        """
        return self._make_request('GET', '/api/me')
    
    def get_organisation_units(self, fields: str = None, paging: bool = False) -> Dict[str, Any]:
        """
        Get organisation units from DHIS2.
        
        Args:
            fields: Comma-separated list of fields to return
            paging: Whether to use paging
            
        Returns:
            Organisation units data
        """
        params = {
            'paging': str(paging).lower()
        }
        
        if fields:
            params['fields'] = fields
        
        return self._make_request('GET', '/api/organisationUnits', params=params)
    
    def get_analytics_data(self, dx: List[str], ou: List[str], pe: List[str], 
                          aggregation_type: str = 'SUM', **kwargs) -> Dict[str, Any]:
        """
        Get analytics data from DHIS2.
        
        Args:
            dx: Data dimension (indicators/data elements UIDs)
            ou: Organisation unit UIDs
            pe: Period strings
            aggregation_type: Aggregation type (SUM, AVERAGE, etc.)
            **kwargs: Additional analytics parameters
            
        Returns:
            Analytics data
        """
        params = {
            'dx': dx,
            'ou': ou,
            'pe': pe,
            'aggregationType': aggregation_type,
            'format': 'json'
        }
        params.update(kwargs)
        
        return self._make_request('GET', '/api/analytics.json', params=params)
    
    def get_indicator_data(self, indicator_uid: str, org_unit_uid: str, 
                          period: str) -> Dict[str, Any]:
        """
        Get specific indicator data.
        
        Args:
            indicator_uid: Indicator UID
            org_unit_uid: Organisation unit UID
            period: Period string
            
        Returns:
            Indicator data
        """
        return self.get_analytics_data(
            dx=[indicator_uid],
            ou=[org_unit_uid],
            pe=[period]
        )
    
    def get_user_org_units(self) -> List[Dict[str, Any]]:
        """
        Get organisation units accessible to the authenticated user.
        
        Returns:
            List of organisation units
        """
        # First get user info to find their org units
        user_info = self.authenticate_user()
        
        # Extract org units from user info
        org_units = user_info.get('organisationUnits', [])
        
        # If user has org units, get detailed info for each
        if org_units:
            org_unit_uids = [ou.get('id') for ou in org_units if ou.get('id')]
            if org_unit_uids:
                # Get detailed org unit info
                detailed_org_units = self.get_organisation_units(
                    fields='id,name,level,parent,children,ancestors',
                    paging=False
                )
                
                # Filter to user's accessible org units
                accessible_org_units = []
                for ou in detailed_org_units.get('organisationUnits', []):
                    if ou.get('id') in org_unit_uids:
                        accessible_org_units.append(ou)
                
                return accessible_org_units
        
        return org_units
    
    def get_org_unit_tree(self, root_org_unit_uid: str = None) -> Dict[str, Any]:
        """
        Get organisation unit tree structure.
        
        Args:
            root_org_unit_uid: Root organisation unit UID (optional)
            
        Returns:
            Organisation unit tree
        """
        if root_org_unit_uid:
            endpoint = f'/api/organisationUnits/{root_org_unit_uid}'
            params = {
                'fields': 'id,name,level,parent,children,ancestors',
                'includeDescendants': 'true'
            }
        else:
            endpoint = '/api/organisationUnits'
            params = {
                'fields': 'id,name,level,parent,children,ancestors',
                'paging': 'false'
            }
        
        return self._make_request('GET', endpoint, params=params)
    
    def test_connection(self) -> bool:
        """
        Test connection to DHIS2 instance.
        
        Returns:
            True if connection successful, False otherwise
        """
        try:
            # Try to access system info endpoint
            self._make_request('GET', '/api/system/info')
            return True
        except requests.RequestException:
            return False
    
    def get_system_info(self) -> Dict[str, Any]:
        """
        Get DHIS2 system information.
        
        Returns:
            System information
        """
        return self._make_request('GET', '/api/system/info')


class DHIS2ClientFactory:
    """
    Factory class for creating DHIS2 clients with different configurations.
    """
    
    @staticmethod
    def create_from_session(session_key: str, instance_url: str) -> DHIS2Client:
        """
        Create DHIS2 client from Django session.
        
        Args:
            session_key: Django session key
            instance_url: DHIS2 instance URL
            
        Returns:
            DHIS2Client instance
        """
        from .session import get_dhis2_session_data
        
        session_data = get_dhis2_session_data(session_key)
        if not session_data:
            raise ValueError("No valid DHIS2 session found")
        
        return DHIS2Client(
            instance_url=instance_url,
            session_key=session_key
        )
    
    @staticmethod
    def create_from_credentials(username: str, password: str, instance_url: str) -> DHIS2Client:
        """
        Create DHIS2 client from credentials.
        
        Args:
            username: DHIS2 username
            password: DHIS2 password
            instance_url: DHIS2 instance URL
            
        Returns:
            DHIS2Client instance
        """
        return DHIS2Client(
            instance_url=instance_url,
            username=username,
            password=password
        ) 