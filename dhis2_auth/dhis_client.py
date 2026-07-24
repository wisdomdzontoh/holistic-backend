import requests
import json
import logging
from typing import Optional, Dict, Any, List
from urllib.parse import urljoin
from django.contrib.sessions.models import Session
from django.core.cache import cache
from django.utils import timezone
from datetime import datetime, timedelta

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
        self.session.timeout = 60  # Increased timeout for analytics requests
        
        # Set authentication if provided
        if username and password:
            self.session.auth = (username, password)
    
    def authenticate_user(self) -> Dict[str, Any]:
        """
        Authenticate user using Basic Auth and get user information
        
        Returns:
            User information dictionary
        """
        try:
            api_url = f"{self.instance_url}/api/me"
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
            logger.error(f"Error authenticating user: {str(e)}")
            raise
    
    def test_connection(self) -> bool:
        """
        Test connection to DHIS2 instance using the /api/me endpoint.
        
        Returns:
            True if connection successful, False otherwise
        """
        try:
            # Use the /api/me endpoint to test connection
            api_url = f"{self.instance_url}/api/me"
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

    def get_user_org_units(self) -> list:
        """
        Get user's assigned organisation units from DHIS2 /api/me endpoint.
        This is typically used after successful authentication.
        """
        try:
            user_info = self.authenticate_user()
            return user_info.get('organisationUnits', [])
        except requests.RequestException as e:
            logger.error(f"Error getting user organization units: {str(e)}")
            raise

    def get_user_accessible_org_units(self) -> List[Dict[str, Any]]:
        """
        Fetches all organization units accessible by the authenticated user from /api/me.
        """
        try:
            user_info = self.authenticate_user()
            return user_info.get('organisationUnits', [])
        except requests.RequestException as e:
            logger.error(f"Error fetching user accessible organization units: {str(e)}")
            raise

    def get_periods(self, period_type: str = None) -> List[Dict[str, Any]]:
        """
        Get periods from DHIS2 instance using the correct endpoint
        Try multiple possible endpoints for compatibility
        
        Args:
            period_type: Filter by period type (e.g., 'Monthly', 'Quarterly')
            
        Returns:
            List of period dictionaries
        """
        try:
            # Try different possible endpoints for periods
            endpoints_to_try = [
                "api/periods",
                "api/periodTypes/periods", 
                "api/periodTypes",
                "api/metadata?class=Period"
            ]
            
            for endpoint in endpoints_to_try:
                try:
                    logger.debug(f"Trying endpoint: {endpoint}")
                    params = {
                        "fields": "id,name,displayName,startDate,endDate,periodType,code",
                        "paging": "false",
                        "pageSize": 1000
                    }
                    if period_type:
                        params["filter"] = f"periodType:eq:{period_type}"
                    
                    data = self._make_request("GET", endpoint, params=params)
                    
                    # Handle different response structures
                    if 'periods' in data:
                        return data.get('periods', [])
                    elif 'periodTypes' in data:
                        # If we got period types, we can generate periods
                        return self._generate_periods_from_types(data.get('periodTypes', []))
                    elif 'objects' in data:
                        return data.get('objects', [])
                    else:
                        # Return the data as is if it's a list
                        if isinstance(data, list):
                            return data
                        elif isinstance(data, dict):
                            # Try to find periods in the response
                            for key in ['periods', 'data', 'objects']:
                                if key in data:
                                    return data[key]
                    
                    logger.debug(f"Successfully got periods from {endpoint}")
                    return data.get('periods', [])
                    
                except requests.RequestException as e:
                    logger.warning(f"Endpoint {endpoint} failed: {str(e)}")
                    continue
            
            # If all endpoints failed, return empty list
            logger.error("All period endpoints failed")
            return []
            
        except Exception as e:
            logger.error(f"Error getting periods: {str(e)}")
            raise

    def _generate_periods_from_types(self, period_types: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Generate periods from period types when direct periods endpoint is not available
        """
        periods = []
        current_year = datetime.now().year
        
        for period_type in period_types:
            period_type_name = period_type.get('name', '')
            
            if 'Monthly' in period_type_name:
                # Generate monthly periods for current year
                for month in range(1, 13):
                    period = {
                        'id': f"{current_year}{month:02d}",
                        'name': f"{current_year} {period_type_name} {month}",
                        'displayName': f"{current_year} {period_type_name} {month}",
                        'startDate': f"{current_year}-{month:02d}-01",
                        'endDate': f"{current_year}-{month:02d}-{self._get_last_day_of_month(current_year, month)}",
                        'periodType': period_type_name,
                        'code': f"{current_year}{month:02d}"
                    }
                    periods.append(period)
            
            elif 'Quarterly' in period_type_name:
                # Generate quarterly periods for current year
                quarters = [
                    ('Q1', 1, 3),
                    ('Q2', 4, 6),
                    ('Q3', 7, 9),
                    ('Q4', 10, 12)
                ]
                
                for quarter_name, start_month, end_month in quarters:
                    period = {
                        'id': f"{current_year}{quarter_name}",
                        'name': f"{current_year} {quarter_name}",
                        'displayName': f"{current_year} {quarter_name}",
                        'startDate': f"{current_year}-{start_month:02d}-01",
                        'endDate': f"{current_year}-{end_month:02d}-{self._get_last_day_of_month(current_year, end_month)}",
                        'periodType': period_type_name,
                        'code': f"{current_year}{quarter_name}"
                    }
                    periods.append(period)
        
        return periods

    def _get_last_day_of_month(self, year: int, month: int) -> int:
        """Get the last day of a given month"""
        if month == 12:
            next_month = datetime(year + 1, 1, 1)
        else:
            next_month = datetime(year, month + 1, 1)
        return (next_month - timedelta(days=1)).day

    def get_relative_periods(self) -> List[Dict[str, Any]]:
        """
        Get relative periods from DHIS2 instance using the correct endpoint
        According to DHIS2 API docs: /api/periodTypes/relativePeriodTypes
        
        Returns:
            List of relative period dictionaries
        """
        try:
            # Try different possible endpoints for relative periods
            endpoints_to_try = [
                "api/periodTypes/relativePeriodTypes",
                "api/periodTypes/relativePeriods",
                "api/relativePeriods",
                "api/metadata?class=RelativePeriod"
            ]
            
            for endpoint in endpoints_to_try:
                try:
                    logger.debug(f"Trying relative periods endpoint: {endpoint}")
                    params = {
                        "fields": "id,name,displayName,periodType,code",
                        "paging": "false"
                    }
                    data = self._make_request("GET", endpoint, params=params)
                    
                    # Handle different response structures
                    if 'relativePeriodTypes' in data:
                        return data.get('relativePeriodTypes', [])
                    elif 'relativePeriods' in data:
                        return data.get('relativePeriods', [])
                    elif 'objects' in data:
                        return data.get('objects', [])
                    else:
                        # Return the data as is if it's a list
                        if isinstance(data, list):
                            return data
                        elif isinstance(data, dict):
                            # Try to find relative periods in the response
                            for key in ['relativePeriodTypes', 'relativePeriods', 'data', 'objects']:
                                if key in data:
                                    return data[key]
                    
                    logger.debug(f"Successfully got relative periods from {endpoint}")
                    return data.get('relativePeriodTypes', [])
                    
                except requests.RequestException as e:
                    logger.warning(f"Relative periods endpoint {endpoint} failed: {str(e)}")
                    continue
            
            # If all endpoints failed, return common relative periods
            logger.warning("All relative period endpoints failed, returning common periods")
            return self._get_common_relative_periods()
            
        except Exception as e:
            logger.error(f"Error getting relative periods: {str(e)}")
            raise

    def _get_common_relative_periods(self) -> List[Dict[str, Any]]:
        """
        Return common relative periods when the endpoint is not available
        """
        common_periods = [
            {
                'id': 'THIS_YEAR',
                'name': 'This Year',
                'displayName': 'This Year',
                'periodType': 'Yearly',
                'code': 'THIS_YEAR'
            },
            {
                'id': 'LAST_YEAR',
                'name': 'Last Year',
                'displayName': 'Last Year',
                'periodType': 'Yearly',
                'code': 'LAST_YEAR'
            },
            {
                'id': 'THIS_QUARTER',
                'name': 'This Quarter',
                'displayName': 'This Quarter',
                'periodType': 'Quarterly',
                'code': 'THIS_QUARTER'
            },
            {
                'id': 'LAST_QUARTER',
                'name': 'Last Quarter',
                'displayName': 'Last Quarter',
                'periodType': 'Quarterly',
                'code': 'LAST_QUARTER'
            },
            {
                'id': 'THIS_MONTH',
                'name': 'This Month',
                'displayName': 'This Month',
                'periodType': 'Monthly',
                'code': 'THIS_MONTH'
            },
            {
                'id': 'LAST_MONTH',
                'name': 'Last Month',
                'displayName': 'Last Month',
                'periodType': 'Monthly',
                'code': 'LAST_MONTH'
            }
        ]
        return common_periods

    def get_org_units(self, level: int = None, parent_id: str = None, include_children: bool = False) -> List[Dict[str, Any]]:
        """
        Get organisation units from DHIS2 instance with optional hierarchical children
        
        Args:
            level: Filter by organisation unit level
            parent_id: Filter by parent organisation unit ID
            include_children: Whether to include nested children in the response
            
        Returns:
            List of organisation unit dictionaries with optional children
        """
        try:
            # Build fields parameter based on requirements
            fields = "id,name,displayName,level,path,code,parent[id,name,displayName]"
            if include_children:
                # Include nested children up to 3 levels deep for optimization
                fields += ",children[id,name,displayName,level,path,code,parent[id,name,displayName],children[id,name,displayName,level,path,code,parent[id,name,displayName],children[id,name,displayName,level,path,code,parent[id,name,displayName]]]]"
            
            # Try different possible endpoints for org units
            endpoints_to_try = [
                "api/organisationUnits",
                "api/organisationUnits.json",
                "api/organisationUnits?paging=false",
                "api/metadata?class=OrganisationUnit"
            ]
            
            for endpoint in endpoints_to_try:
                try:
                    logger.debug(f"Trying org units endpoint: {endpoint}")
                    params = {
                        "fields": fields,
                        "paging": "false",
                        "pageSize": 1000
                    }
                    if level:
                        params["filter"] = f"level:eq:{level}"
                    if parent_id:
                        params["filter"] = f"parent.id:eq:{parent_id}"
                    
                    data = self._make_request("GET", endpoint, params=params)
                    
                    # Handle different response structures
                    if 'organisationUnits' in data:
                        return data.get('organisationUnits', [])
                    elif 'objects' in data:
                        return data.get('objects', [])
                    else:
                        # Return the data as is if it's a list
                        if isinstance(data, list):
                            return data
                        elif isinstance(data, dict):
                            # Try to find org units in the response
                            for key in ['organisationUnits', 'data', 'objects']:
                                if key in data:
                                    return data[key]
                    
                    logger.debug(f"Successfully got org units from {endpoint}")
                    return data.get('organisationUnits', [])
                    
                except requests.RequestException as e:
                    logger.warning(f"Org units endpoint {endpoint} failed: {str(e)}")
                    continue
            
            # If all endpoints failed, return empty list
            logger.error("All org unit endpoints failed")
            return []
            
        except Exception as e:
            logger.error(f"Error getting organization units: {str(e)}")
            raise

    def get_org_unit_by_id(self, org_unit_id: str) -> Dict[str, Any]:
        """
        Get a single organisation unit by ID
        
        Args:
            org_unit_id: The organisation unit ID
            
        Returns:
            Organisation unit dictionary or None if not found
        """
        try:
            endpoint = f"api/organisationUnits/{org_unit_id}"
            params = {
                "fields": "id,name,displayName,level,path,code,parent[id,name,displayName]"
            }
            
            data = self._make_request("GET", endpoint, params=params)
            return data
            
        except Exception as e:
            logger.error(f"Error getting organization unit {org_unit_id}: {str(e)}")
            return None

    def get_org_unit_hierarchy(self, root_id: str = None, max_depth: int = 3) -> List[Dict[str, Any]]:
        """
        Get organisation unit hierarchy with nested children for tree structure
        
        Args:
            root_id: Root organisation unit ID (if None, gets all root units)
            max_depth: Maximum depth of children to fetch (default: 3 for performance)
            
        Returns:
            List of organisation unit dictionaries with nested children
        """
        try:
            # First, get ALL org units with their parent information to build the complete hierarchy.
            # Page through the results explicitly instead of relying on a single
            # pageSize=1000 request, which silently truncates instances with >1000 org units.
            endpoint = "api/organisationUnits"
            org_units: List[Dict[str, Any]] = []
            page = 1
            page_size = 1000
            while True:
                params = {
                    "fields": "id,name,displayName,level,path,code,parent[id,name,displayName]",
                    "paging": "true",
                    "pageSize": page_size,
                    "page": page,
                }
                data = self._make_request("GET", endpoint, params=params)

                if 'organisationUnits' in data:
                    page_units = data.get('organisationUnits', [])
                elif isinstance(data, list):
                    # Some DHIS2 responses omit the pager wrapper entirely - treat as the final page.
                    org_units.extend(data)
                    break
                else:
                    break

                org_units.extend(page_units)

                pager = data.get('pager') or {}
                page_count = pager.get('pageCount')
                if page_count is not None:
                    if page >= page_count:
                        break
                elif len(page_units) < page_size:
                    # No pager metadata - fall back to detecting a short page.
                    break

                page += 1

            # Now build the hierarchy manually by organizing units by parent-child relationships
            hierarchy = self._build_hierarchy_from_flat_list(org_units, root_id, max_depth)
            
            # If a specific root_id was requested, filter to only return that root and its descendants
            if root_id:
                # Find the specific root unit in the hierarchy
                for unit in hierarchy:
                    if unit['id'] == root_id:
                        return [unit]
                # If root_id not found, return empty list
                return []
            
            return hierarchy
                
        except Exception as e:
            logger.error(f"Error getting organization unit hierarchy: {str(e)}")
            raise

    def _build_hierarchy_from_flat_list(self, org_units: List[Dict[str, Any]], root_id: str = None, max_depth: int = 3) -> List[Dict[str, Any]]:
        """
        Build hierarchical structure from flat list of org units
        
        Args:
            org_units: Flat list of organisation units
            root_id: Root organisation unit ID
            max_depth: Maximum depth to build
            
        Returns:
            Hierarchical list of organisation units
        """
        # Create a map for quick lookup
        unit_map = {unit['id']: unit.copy() for unit in org_units}
        
        # Initialize children arrays
        for unit in unit_map.values():
            unit['children'] = []
        
        # Build parent-child relationships
        root_units = []
        for unit in org_units:
            unit_id = unit['id']
            parent_id = unit.get('parent', {}).get('id') if unit.get('parent') else None
            
            if parent_id and parent_id in unit_map:
                # Add to parent's children
                unit_map[parent_id]['children'].append(unit_map[unit_id])
            else:
                # This is a root unit (no parent or parent not in our dataset)
                root_units.append(unit_map[unit_id])
        
        # If a specific root_id was requested, we need to find that unit and all its descendants
        if root_id:
            # First, check if the root_id exists in our dataset
            if root_id not in unit_map:
                return []
            
            # Find the root unit and return it with all its descendants
            root_unit = unit_map[root_id]
            # The root unit already has all its descendants in its children array
            # due to the parent-child relationship building above
            return [root_unit]
        
        # Limit depth if needed
        if max_depth < 3:
            self._limit_depth(root_units, max_depth)
        
        return root_units
    
    def _limit_depth(self, units: List[Dict[str, Any]], max_depth: int, current_depth: int = 0):
        """
        Recursively limit the depth of the hierarchy
        
        Args:
            units: List of organisation units
            max_depth: Maximum allowed depth
            current_depth: Current depth level
        """
        if current_depth >= max_depth:
            # Remove children at this level
            for unit in units:
                unit['children'] = []
            return
        
        # Recursively limit depth for children
        for unit in units:
            if unit.get('children'):
                self._limit_depth(unit['children'], max_depth, current_depth + 1)

    def get_org_unit_descendants(self, org_unit_id: str) -> List[Dict[str, Any]]:
        """
        Get all descendants of an organisation unit using the /descendants endpoint
        
        Args:
            org_unit_id: Organisation unit ID to get descendants for
            
        Returns:
            List of organisation unit dictionaries with all descendants
        """
        try:
            endpoint = f"api/organisationUnits/{org_unit_id}/descendants"
            params = {
                "fields": "id,name,displayName,level,path,code,parent[id,name,displayName]",
                "paging": "false",
                "pageSize": 1000
            }
            
            data = self._make_request("GET", endpoint, params=params)
            
            # Handle response structure
            if 'organisationUnits' in data:
                return data.get('organisationUnits', [])
            elif isinstance(data, list):
                return data
            else:
                return []
                
        except Exception as e:
            logger.error(f"Error getting organization unit descendants: {str(e)}")
            raise

    def get_org_unit_children(self, org_unit_id: str) -> List[Dict[str, Any]]:
        """
        Get immediate children of an organisation unit
        
        Args:
            org_unit_id: Organisation unit ID to get children for
            
        Returns:
            List of organisation unit dictionaries with immediate children
        """
        try:
            endpoint = "api/organisationUnits"
            params = {
                "fields": "id,name,displayName,level,path,code,parent[id,name,displayName]",
                "filter": f"parent.id:eq:{org_unit_id}",
                "paging": "false",
                "pageSize": 1000
            }
            
            data = self._make_request("GET", endpoint, params=params)
            
            # Handle response structure
            if 'organisationUnits' in data:
                return data.get('organisationUnits', [])
            elif isinstance(data, list):
                return data
            else:
                return []
                
        except Exception as e:
            logger.error(f"Error getting organization unit children: {str(e)}")
            raise

    def get_period_types(self) -> List[Dict[str, Any]]:
        """
        Get available period types from DHIS2 instance.
        """
        try:
            endpoint = "api/periodTypes"
            params = {
                "fields": "id,name,displayName,frequencyOrder",
                "paging": "false"
            }
            data = self._make_request("GET", endpoint, params=params)
            return data.get('periodTypes', [])
        except requests.RequestException as e:
            logger.error(f"Error getting period types: {str(e)}")
            raise

    def get_system_info(self) -> Dict[str, Any]:
        """
        Get DHIS2 system info
        
        Returns:
            System info dictionary
        """
        try:
            api_url = f"{self.instance_url}/api/system/info"
            logger.debug(f"Fetching system info from: {api_url}")
            
            response = self.session.get(api_url, timeout=10)
            
            if response.status_code == 200:
                system_info = response.json()
                logger.info("System info retrieved successfully")
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
            system_info = self.get_system_info()
            return system_info.get('version', 'Unknown')
        except requests.RequestException as e:
            logger.error(f"Error getting API version: {str(e)}")
            return "Unknown"

    def get_api_capabilities(self) -> Dict[str, Any]:
        """
        Get DHIS2 API capabilities
        
        Returns:
            API capabilities dictionary
        """
        try:
            api_url = f"{self.instance_url}/api/capabilities"
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
    
    def _make_request(self, method: str, endpoint: str, timeout: int = None, **kwargs) -> Dict[str, Any]:
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
            
            # Handle multiple dimension parameters correctly
            if 'params' in kwargs and 'dimension' in kwargs['params']:
                dimension_values = kwargs['params']['dimension']
                if isinstance(dimension_values, list):
                    # Convert list of dimensions to separate dimension parameters
                    params = kwargs['params'].copy()
                    del params['dimension']
                    
                    # Build URL manually with multiple dimension parameters
                    import urllib.parse
                    query_parts = []
                    
                    # Add dimension parameters
                    for dim_value in dimension_values:
                        query_parts.append(f"dimension={urllib.parse.quote(dim_value)}")
                    
                    # Add other parameters
                    for key, value in params.items():
                        query_parts.append(f"{key}={urllib.parse.quote(str(value))}")
                    
                    if query_parts:
                        url += "?" + "&".join(query_parts)
                    
                    # Remove params from kwargs since we built the URL manually
                    kwargs = {k: v for k, v in kwargs.items() if k != 'params'}
            
            # Use custom timeout if provided, otherwise use session default
            request_kwargs = kwargs.copy()
            if timeout is not None:
                request_kwargs['timeout'] = timeout
            
            response = self.session.request(method, url, **request_kwargs)
            
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
            elif response.status_code == 409:
                logger.error(f"Conflict error for {method} {url}: {response.text}")
                raise requests.RequestException(f"Conflict error (invalid parameters): {response.text}")
            elif response.status_code >= 500:
                logger.error(f"Server error for {method} {url}: {response.text}")
                raise requests.RequestException(f"Server error: {response.text}")
            
            response.raise_for_status()
            
            # Try to parse JSON response
            try:
                return response.json()
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse JSON response from {url}: {str(e)}")
                logger.error(f"Response status code: {response.status_code}")
                logger.error(f"Response headers: {dict(response.headers)}")
                logger.error(f"Response content (first 500 chars): {response.text[:500]}")
                
                # Check if response is HTML (login page)
                if response.text.strip().startswith('<!DOCTYPE html>') or '<html' in response.text.lower():
                    logger.error("DHIS2 returned HTML instead of JSON - authentication may have failed")
                    raise requests.RequestException("Authentication failed - DHIS2 returned login page instead of JSON")
                
                raise requests.RequestException(f"Invalid JSON response: {str(e)}")
            
        except requests.RequestException as e:
            logger.error(f"DHIS2 API request failed: {method} {url} - {str(e)}")
            if hasattr(e, 'response') and e.response:
                logger.error(f"Response status: {e.response.status_code}")
                logger.error(f"Response headers: {dict(e.response.headers)}")
                logger.error(f"Response content (first 500 chars): {e.response.text[:500]}")
            raise

    def get_analytics_data(self, data_elements: List[str] = None, indicators: List[str] = None, 
                      periods: List[str] = None, org_units: List[str] = None,
                      data_sets: List[str] = None, program_indicators: List[str] = None,
                      skip_data: bool = False, skip_meta: bool = False,
                      skip_rounding: bool = False, show_hierarchy: bool = True,
                      include_num_den: bool = True, output_type: str = "EVENT") -> Dict[str, Any]:
        """
        Get analytics data from DHIS2 using the /api/analytics endpoint
        FIXED: Using correct DHIS2 analytics API format with dimension parameters
        
        Args:
            data_elements: List of data element UIDs
            indicators: List of indicator UIDs
            periods: List of period identifiers (fixed or relative)
            org_units: List of org unit UIDs
            program_indicators: List of program indicator UIDs
            skip_data: Skip data rows in response
            skip_meta: Skip metadata in response
            skip_rounding: Skip rounding of values
            show_hierarchy: Show org unit hierarchy
            include_num_den: Include numerator/denominator
            output_type: Output type (EVENT, ENROLLMENT, TRACKED_ENTITY_INSTANCE)
            
        Returns:
            Analytics data dictionary
        """
        try:
            endpoint = "api/analytics"
            
            # FIXED: Build parameters according to DHIS2 Analytics API specification
            params = {}
            dimensions = []
            
            # Build dx dimension (data dimension) correctly
            # According to DHIS2 docs, all data items go into the dx dimension
            dx_items = []
            
            if data_elements:
                dx_items.extend(data_elements)
            
            if indicators:
                dx_items.extend(indicators)
            
            if program_indicators:
                dx_items.extend(program_indicators)
            
            # FIXED: Only add dx dimension if we have actual data items
            if dx_items:
                dimensions.append(f"dx:{';'.join(dx_items)}")
            
            # Add period dimension
            if periods:
                dimensions.append(f"pe:{';'.join(periods)}")
            
            # Add org unit dimension
            if org_units:
                dimensions.append(f"ou:{';'.join(org_units)}")
            
            # FIXED: Only add dimension parameter if we have dimensions
            if dimensions:
                params["dimension"] = dimensions
            
            # Additional parameters
            if skip_data:
                params["skipData"] = "true"
            if skip_meta:
                params["skipMeta"] = "true"
            if skip_rounding:
                params["skipRounding"] = "true"
            if not show_hierarchy:
                params["showHierarchy"] = "false"
            if not include_num_den:
                params["includeNumDen"] = "false"
            if output_type != "EVENT":
                params["outputType"] = output_type
            
            # Add displayProperty parameter for better response format
            params["displayProperty"] = "NAME"
            
            logger.info(f"Making DHIS2 analytics request to {endpoint}")
            logger.info(f"Request parameters: {params}")
            logger.info(f"Data elements: {data_elements}")
            logger.info(f"Indicators: {indicators}")
            logger.info(f"Program indicators: {program_indicators}")
            logger.info(f"Periods: {periods}")
            logger.info(f"Org units: {org_units}")
            logger.info(f"Dimensions: {dimensions}")
            
            # Use longer timeout for analytics requests
            data = self._make_request("GET", endpoint, params=params, timeout=120)
            
            logger.info(f"DHIS2 analytics response received. Response type: {type(data)}")
            if isinstance(data, dict):
                logger.info(f"Response keys: {list(data.keys())}")
                if 'rows' in data:
                    logger.info(f"Number of rows in response: {len(data['rows'])}")
                if 'headers' in data:
                    logger.info(f"Number of headers in response: {len(data['headers'])}")
                    header_names = [h.get('name', 'Unknown') for h in data['headers']]
                    logger.info(f"Header names: {header_names}")
            else:
                logger.warning(f"Unexpected response type: {type(data)}")
            
            return data
            
        except requests.RequestException as e:
            logger.error(f"Error getting analytics data: {str(e)}")
            raise

    # FIXED: Add new method for data set reports
    def get_data_set_report(self, data_set_id: str, periods: List[str] = None, 
                       org_units: List[str] = None, **kwargs) -> Dict[str, Any]:
        """
        Get data set report from DHIS2 using the /api/dataSetReport endpoint
        This is used for data sets that cannot be queried via analytics endpoint
        
        Args:
            data_set_id: DHIS2 UID of the data set
            periods: List of period identifiers
            org_units: List of org unit UIDs
            **kwargs: Additional parameters
            
        Returns:
            Data set report dictionary
        """
        try:
            endpoint = "api/dataSetReport"
            
            params = {
                "ds": data_set_id
            }
            
            if periods:
                params["pe"] = ";".join(periods)
            
            if org_units:
                params["ou"] = ";".join(org_units)
            
            # Add additional parameters
            for key, value in kwargs.items():
                params[key] = value
            
            logger.info(f"Making DHIS2 data set report request to {endpoint}")
            logger.info(f"Request parameters: {params}")
            
            data = self._make_request("GET", endpoint, params=params)
            
            logger.info(f"DHIS2 data set report response received")
            return data
            
        except requests.RequestException as e:
            logger.error(f"Error getting data set report: {str(e)}")
            raise

    def get_analytics_data_enhanced(self, data_items: List[Dict[str, str]], periods: List[str], 
                                  org_units: List[str] = None, **kwargs) -> Dict[str, Any]:
        """
        Enhanced analytics data fetching with support for different data item types
        
        Args:
            data_items: List of dictionaries with 'uid' and 'type' keys
                       type can be: 'dataElement', 'indicator', 'dataSet', 'programIndicator'
            periods: List of period identifiers
            org_units: List of org unit UIDs (optional)
            **kwargs: Additional parameters for analytics endpoint
            
        Returns:
            Analytics data dictionary
        """
        try:
            # Separate data items by type
            data_elements = [item['uid'] for item in data_items if item.get('type') == 'dataElement']
            indicators = [item['uid'] for item in data_items if item.get('type') == 'indicator']
            data_sets = [item['uid'] for item in data_items if item.get('type') == 'dataSet']
            program_indicators = [item['uid'] for item in data_items if item.get('type') == 'programIndicator']
            
            return self.get_analytics_data(
                data_elements=data_elements,
                indicators=indicators,
                data_sets=data_sets,
                program_indicators=program_indicators,
                periods=periods,
                org_units=org_units,
                **kwargs
            )
            
        except Exception as e:
            logger.error(f"Error in enhanced analytics data fetching: {str(e)}")
            raise

    def get_data_set_metadata(self, data_set_id: str = None) -> Dict[str, Any]:
        """
        Get data set metadata including data elements and indicators
        
        Args:
            data_set_id: Specific data set ID (optional)
            
        Returns:
            Data set metadata dictionary
        """
        try:
            if data_set_id:
                endpoint = f"api/dataSets/{data_set_id}/metadata"
            else:
                endpoint = "api/dataSetMetadata"
            
            data = self._make_request("GET", endpoint)
            return data
            
        except requests.RequestException as e:
            logger.error(f"Error getting data set metadata: {str(e)}")
            raise

    def get_indicator_group_indicators(self, indicator_group_uid: str, 
                                     fields: List[str] = None) -> List[Dict[str, Any]]:
        """
        Get indicators belonging to a specific indicator group
        
        Args:
            indicator_group_uid: Indicator group UID
            fields: List of fields to include in response
            
        Returns:
            List of indicator dictionaries
        """
        try:
            endpoint = f"api/indicatorGroups/{indicator_group_uid}"
            
            params = {}
            if fields:
                params["fields"] = f"indicators[{','.join(fields)}]"
            else:
                params["fields"] = "indicators[id,name,description,shortName,displayName,code,indicatorType]"
            
            data = self._make_request("GET", endpoint, params=params)
            return data.get('indicators', [])
            
        except requests.RequestException as e:
            logger.error(f"Error getting indicator group indicators: {str(e)}")
            raise

    def get_data_element_group_elements(self, data_element_group_uid: str,
                                       fields: List[str] = None) -> List[Dict[str, Any]]:
        """
        Get data elements belonging to a specific data element group
        
        Args:
            data_element_group_uid: Data element group UID
            fields: List of fields to include in response
            
        Returns:
            List of data element dictionaries
        """
        try:
            endpoint = f"api/dataElementGroups/{data_element_group_uid}"
            
            params = {}
            if fields:
                params["fields"] = f"dataElements[{','.join(fields)}]"
            else:
                params["fields"] = "dataElements[id,name,description,shortName,displayName,code,valueType,aggregationType]"
            
            data = self._make_request("GET", endpoint, params=params)
            return data.get('dataElements', [])
            
        except requests.RequestException as e:
            logger.error(f"Error getting data element group elements: {str(e)}")
            raise

    def get_indicators(self, limit: int = 50, fields: List[str] = None, 
                      filter_query: str = None, indicator_type: str = None) -> List[Dict[str, Any]]:
        """
        Get indicators from DHIS2 with enhanced filtering
        
        Args:
            limit: Maximum number of indicators to return
            fields: List of fields to include in response
            filter_query: Filter query string (e.g., "name:ilike:immunization")
            indicator_type: Filter by indicator type
            
        Returns:
            List of indicator dictionaries
        """
        try:
            endpoint = "api/indicators"
            
            params = {
                "paging": "false",
                "pageSize": limit
            }
            
            if fields:
                params["fields"] = ",".join(fields)
            else:
                # Enhanced default fields for indicators
                params["fields"] = "id,name,description,shortName,displayName,code,indicatorType,denominator,denominatorDescription,numerator,numeratorDescription,annualized,indicatorGroups[id,name]"
            
            # Add filters
            filters = []
            if filter_query:
                filters.append(filter_query)
            if indicator_type:
                filters.append(f"indicatorType:eq:{indicator_type}")
            
            if filters:
                params["filter"] = filters
            
            data = self._make_request("GET", endpoint, params=params)
            return data.get('indicators', [])
            
        except requests.RequestException as e:
            logger.error(f"Error getting indicators: {str(e)}")
            raise

    def get_data_elements(self, limit: int = 50, fields: List[str] = None,
                         filter_query: str = None, value_type: str = None,
                         domain_type: str = None) -> List[Dict[str, Any]]:
        """
        Get data elements from DHIS2 with enhanced filtering
        
        Args:
            limit: Maximum number of data elements to return
            fields: List of fields to include in response
            filter_query: Filter query string (e.g., "name:ilike:immunization")
            value_type: Filter by value type
            domain_type: Filter by domain type
            
        Returns:
            List of data element dictionaries
        """
        try:
            endpoint = "api/dataElements"
            
            params = {
                "paging": "false",
                "pageSize": limit
            }
            
            if fields:
                params["fields"] = ",".join(fields)
            else:
                # Enhanced default fields for data elements
                params["fields"] = "id,name,description,shortName,displayName,code,valueType,aggregationType,domainType,dataElementGroups[id,name],categoryCombo[id,name]"
            
            # Add filters
            filters = []
            if filter_query:
                filters.append(filter_query)
            if value_type:
                filters.append(f"valueType:eq:{value_type}")
            if domain_type:
                filters.append(f"domainType:eq:{domain_type}")
            
            if filters:
                params["filter"] = filters
            
            data = self._make_request("GET", endpoint, params=params)
            return data.get('dataElements', [])
            
        except requests.RequestException as e:
            logger.error(f"Error getting data elements: {str(e)}")
            raise

    def search_indicators(self, query: str, limit: int = 20, 
                         search_fields: List[str] = None) -> List[Dict[str, Any]]:
        """
        Search indicators by name, description, or code with enhanced search
        
        Args:
            query: Search query string
            limit: Maximum number of results
            search_fields: Fields to search in (name, description, code)
            
        Returns:
            List of matching indicators
        """
        try:
            endpoint = "api/indicators"
            
            params = {
                "paging": "false",
                "pageSize": limit
            }
            
            # Build search filter
            if search_fields:
                search_filters = []
                for field in search_fields:
                    search_filters.append(f"{field}:ilike:{query}")
                params["filter"] = search_filters
            else:
                # Default search in name and description
                params["filter"] = [f"name:ilike:{query}", f"description:ilike:{query}"]
            
            data = self._make_request("GET", endpoint, params=params)
            return data.get('indicators', [])
            
        except requests.RequestException as e:
            logger.error(f"Error searching indicators: {str(e)}")
            raise

    def search_data_elements(self, query: str, limit: int = 20,
                            search_fields: List[str] = None) -> List[Dict[str, Any]]:
        """
        Search data elements by name, description, or code with enhanced search
        
        Args:
            query: Search query string
            limit: Maximum number of results
            search_fields: Fields to search in (name, description, code)
            
        Returns:
            List of matching data elements
        """
        try:
            endpoint = "api/dataElements"
            
            params = {
                "paging": "false",
                "pageSize": limit
            }
            
            # Build search filter
            if search_fields:
                search_filters = []
                for field in search_fields:
                    search_filters.append(f"{field}:ilike:{query}")
                params["filter"] = search_filters
            else:
                # Default search in name and description
                params["filter"] = [f"name:ilike:{query}", f"description:ilike:{query}"]
            
            data = self._make_request("GET", endpoint, params=params)
            return data.get('dataElements', [])
            
        except requests.RequestException as e:
            logger.error(f"Error searching data elements: {str(e)}")
            raise

    def get_analytics_data_batch(self, data_items: List[Dict[str, str]], periods: List[str],
                                org_units: List[str] = None, batch_size: int = 50) -> List[Dict[str, Any]]:
        """
        Fetch analytics data in batches to handle large datasets
        
        Args:
            data_items: List of data item dictionaries
            periods: List of period identifiers
            org_units: List of org unit UIDs (optional)
            batch_size: Number of data items per batch
            
        Returns:
            List of analytics data dictionaries
        """
        try:
            results = []
            
            # Split data items into batches
            for i in range(0, len(data_items), batch_size):
                batch = data_items[i:i + batch_size]
                
                logger.info(f"Processing batch {i//batch_size + 1} of {(len(data_items) + batch_size - 1)//batch_size}")
                
                batch_result = self.get_analytics_data_enhanced(
                    data_items=batch,
                    periods=periods,
                    org_units=org_units
                )
                
                results.append(batch_result)
                
                # Add small delay between batches to avoid overwhelming the server
                import time
                time.sleep(0.1)
            
            return results
            
        except Exception as e:
            logger.error(f"Error in batch analytics data fetching: {str(e)}")
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
    
    @staticmethod
    def create_client_from_session(instance_url: str, session_key: str) -> DHIS2Client:
        """
        Create a DHIS2Client instance using existing session data
        
        Args:
            instance_url: DHIS2 instance URL
            session_key: Django session key
            
        Returns:
            DHIS2Client instance
        """
        # Get the Django session and retrieve stored credentials
        try:
            session = Session.objects.get(session_key=session_key)
            session_data = session.get_decoded()
            
            # Try to get stored credentials from session data
            username = None
            password = None
            
            if 'dhis2_auth' in session_data:
                auth_data = session_data['dhis2_auth']
                username = auth_data.get('dhis2_username')
                password = auth_data.get('dhis2_password')
                
                if username and password:
                    logger.debug(f"Retrieved DHIS2 credentials from session {session_key}")
                    return DHIS2Client(instance_url, username, password)
                else:
                    logger.warning(f"No DHIS2 credentials found in session {session_key}")
            
            # Fallback: try to get credentials from cache
            cache_key = f"dhis2_session_{session_key}"
            cached_data = cache.get(cache_key)
            
            if cached_data:
                username = cached_data.get('dhis2_username')
                password = cached_data.get('dhis2_password')
                
                if username and password:
                    logger.debug(f"Retrieved DHIS2 credentials from cache for session {session_key}")
                    return DHIS2Client(instance_url, username, password)
            
            logger.warning(f"No DHIS2 credentials found for session {session_key}")
            return DHIS2Client(instance_url)
                
        except Session.DoesNotExist:
            logger.warning(f"Session {session_key} not found")
            return DHIS2Client(instance_url)