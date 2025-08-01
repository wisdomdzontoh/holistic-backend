import requests
import json
import logging
from typing import Optional, Dict, Any
from urllib.parse import urljoin

logger = logging.getLogger(__name__)


class DHIS2Client:
    """
    Client for interacting with DHIS2 API
    """
    
    def __init__(self, instance_url: str, username: str = None, password: str = None):
        """
        Initialize DHIS2 client
        
        Args:
            instance_url: DHIS2 instance URL (e.g., https://dhims.chimgh.org/dhims/)
            username: DHIS2 username
            password: DHIS2 password
        """
        # Ensure consistent URL formatting
        self.instance_url = instance_url.rstrip('/')
        self.username = username
        self.password = password
        
        # Create session with proper headers and configuration
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'HolisticAssessment/1.0',
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        })
        
        # Configure session
        self.session.verify = True  # SSL verification
        self.session.timeout = 30
        
        # Set authentication if provided
        if username and password:
            self.session.auth = (username, password)
    
    def test_connection(self) -> bool:
        """
        Test connection to DHIS2 instance using the proven /api/me.json endpoint.
        
        Returns:
            True if connection successful, False otherwise
        """
        try:
            # Use the proven endpoint from the working code
            api_url = f"{self.instance_url}/api/me.json"
            logger.debug(f"Testing connection to: {api_url}")
            
            response = self.session.get(api_url, timeout=10)
            
            # Log response details for debugging
            logger.debug(f"Connection test response: {response.status_code}")
            
            # 200 means successful authentication
            # 401 means endpoint exists but requires auth - connection is working
            # 403 means access forbidden but connection works
            if response.status_code in [200, 401, 403]:
                logger.info(f"Connection test successful: {response.status_code}")
                return True
            else:
                logger.warning(f"Connection test failed with status: {response.status_code}")
                return False
                
        except requests.ConnectionError as e:
            logger.error(f"Connection error: {str(e)}")
            return False
        except requests.Timeout as e:
            logger.error(f"Connection timeout: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Connection test failed: {str(e)}")
            return False
    
    def authenticate_user(self) -> Dict[str, Any]:
        """
        Authenticate user and get user information
        
        Returns:
            User information dictionary
        """
        try:
            api_url = f"{self.instance_url}/api/me.json"
            logger.debug(f"Authenticating user at: {api_url}")
            
            response = self.session.get(api_url, timeout=10)
            
            if response.status_code == 200:
                user_info = response.json()
                logger.info(f"Authentication successful for user: {user_info.get('name', 'Unknown')}")
                return user_info
            else:
                logger.error(f"Authentication failed: {response.status_code} - {response.text}")
                raise requests.RequestException(f"Authentication failed: {response.text}")
                
        except requests.RequestException as e:
            logger.error(f"Authentication error: {str(e)}")
            raise
    
    def get_user_org_units(self) -> list:
        """
        Get user's accessible organisation units
        
        Returns:
            List of organisation units
        """
        try:
            api_url = f"{self.instance_url}/api/me.json?fields=organisationUnits[id,name,level]"
            logger.debug(f"Fetching user org units from: {api_url}")
            
            response = self.session.get(api_url, timeout=10)
            
            if response.status_code == 200:
                user_info = response.json()
                org_units = user_info.get('organisationUnits', [])
                logger.info(f"Found {len(org_units)} organisation units for user")
                return org_units
            else:
                logger.error(f"Failed to get org units: {response.status_code} - {response.text}")
                raise requests.RequestException(f"Failed to get org units: {response.text}")
                
        except requests.RequestException as e:
            logger.error(f"Error getting org units: {str(e)}")
            raise
    
    def get_system_info(self) -> Dict[str, Any]:
        """
        Get DHIS2 system information
        
        Returns:
            System information dictionary
        """
        try:
            api_url = f"{self.instance_url}/api/system/info.json"
            logger.debug(f"Fetching system info from: {api_url}")
            
            response = self.session.get(api_url, timeout=10)
            
            if response.status_code == 200:
                system_info = response.json()
                logger.info(f"System info retrieved: {system_info.get('version', 'Unknown')}")
                return system_info
            else:
                logger.error(f"Failed to get system info: {response.status_code} - {response.text}")
                raise requests.RequestException(f"Failed to get system info: {response.text}")
                
        except requests.RequestException as e:
            logger.error(f"Error getting system info: {str(e)}")
            raise
    
    def get_api_version(self) -> str:
        """
        Get DHIS2 API version
        
        Returns:
            API version string
        """
        try:
            api_url = f"{self.instance_url}/api/version.json"
            logger.debug(f"Fetching API version from: {api_url}")
            
            response = self.session.get(api_url, timeout=10)
            
            if response.status_code == 200:
                version_info = response.json()
                version = version_info.get('version', 'Unknown')
                logger.info(f"API version: {version}")
                return version
            else:
                logger.error(f"Failed to get API version: {response.status_code} - {response.text}")
                raise requests.RequestException(f"Failed to get API version: {response.text}")
                
        except requests.RequestException as e:
            logger.error(f"Error getting API version: {str(e)}")
            raise
    
    def get_api_capabilities(self) -> Dict[str, Any]:
        """
        Get DHIS2 API capabilities
        
        Returns:
            API capabilities dictionary
        """
        try:
            api_url = f"{self.instance_url}/api/capabilities.json"
            logger.debug(f"Fetching API capabilities from: {api_url}")
            
            response = self.session.get(api_url, timeout=10)
            
            if response.status_code == 200:
                capabilities = response.json()
                logger.info("API capabilities retrieved successfully")
                return capabilities
            else:
                logger.error(f"Failed to get API capabilities: {response.status_code} - {response.text}")
                raise requests.RequestException(f"Failed to get API capabilities: {response.text}")
                
        except requests.RequestException as e:
            logger.error(f"Error getting API capabilities: {str(e)}")
            raise
    
    def _make_request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """
        Make a request to the DHIS2 API
        
        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint (e.g., '/api/me')
            **kwargs: Additional request parameters
            
        Returns:
            Response data
        """
        url = urljoin(f"{self.instance_url}/", endpoint.lstrip('/'))
        
        try:
            logger.debug(f"Making {method} request to: {url}")
            response = self.session.request(method, url, **kwargs)
            
            # Log request details for debugging
            logger.debug(f"Response status: {response.status_code}")
            
            # Handle different status codes
            if response.status_code == 204:
                return {}
            elif response.status_code == 401:
                logger.error(f"Authentication failed for {method} {url}")
                raise requests.RequestException(f"Authentication failed: {response.text}")
            elif response.status_code == 403:
                logger.error(f"Access forbidden for {method} {url}")
                raise requests.RequestException(f"Access forbidden: {response.text}")
            elif response.status_code == 404:
                logger.error(f"Endpoint not found: {method} {url}")
                raise requests.RequestException(f"Endpoint not found: {response.text}")
            elif response.status_code >= 500:
                logger.error(f"Server error for {method} {url}: {response.text}")
                raise requests.RequestException(f"Server error: {response.text}")
            
            response.raise_for_status()
            
            # Try to parse JSON response
            try:
                return response.json()
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse JSON response from {url}: {str(e)}")
                logger.error(f"Response content: {response.text[:500]}")
                raise requests.RequestException(f"Invalid JSON response: {str(e)}")
            
        except requests.RequestException as e:
            logger.error(f"DHIS2 API request failed: {method} {url} - {str(e)}")
            if hasattr(e, 'response') and e.response:
                logger.error(f"Response status: {e.response.status_code}")
                logger.error(f"Response headers: {dict(e.response.headers)}")
                logger.error(f"Response content: {e.response.text[:500]}")
            raise


class DHIS2ClientFactory:
    """
    Factory for creating DHIS2Client instances
    """
    
    @staticmethod
    def create_client(instance_url: str, username: str = None, password: str = None) -> DHIS2Client:
        """
        Create a DHIS2Client instance
        
        Args:
            instance_url: DHIS2 instance URL
            username: DHIS2 username
            password: DHIS2 password
            
        Returns:
            DHIS2Client instance
        """
        return DHIS2Client(instance_url, username, password) 