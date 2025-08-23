"""
Cache Service

This service handles caching of assessment data and other frequently accessed data
to improve performance and reduce database queries.
"""

import logging
import json
import hashlib
from typing import Dict, Any, Optional, List
from django.core.cache import cache
from django.conf import settings
from django.utils import timezone
from datetime import timedelta

logger = logging.getLogger(__name__)


class CacheService:
    """
    Service for managing cache operations for assessment data.
    """
    
    def __init__(self):
        self.default_timeout = getattr(settings, 'ASSESSMENT_CACHE_TIMEOUT', 3600)  # 1 hour default
        self.max_cache_size = getattr(settings, 'ASSESSMENT_MAX_CACHE_SIZE', 100)  # Maximum cache entries
    
    def set_assessment_cache(self, key: str, data: Any, timeout: Optional[int] = None) -> bool:
        """
        Cache assessment data.
        
        Args:
            key: Cache key
            data: Data to cache
            timeout: Cache timeout in seconds (uses default if None)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if timeout is None:
                timeout = self.default_timeout
            
            # Serialize data for caching
            serialized_data = self._serialize_data(data)
            
            # Set cache with timeout
            cache.set(key, serialized_data, timeout=timeout)
            
            logger.debug(f"Assessment data cached with key: {key}")
            return True
            
        except Exception as e:
            logger.error(f"Error caching assessment data: {str(e)}")
            return False
    
    def get_assessment_cache(self, key: str) -> Optional[Any]:
        """
        Retrieve cached assessment data.
        
        Args:
            key: Cache key
            
        Returns:
            Cached data or None if not found
        """
        try:
            cached_data = cache.get(key)
            
            if cached_data is None:
                logger.debug(f"No cached data found for key: {key}")
                return None
            
            # Deserialize data
            data = self._deserialize_data(cached_data)
            
            logger.debug(f"Retrieved cached assessment data for key: {key}")
            return data
            
        except Exception as e:
            logger.error(f"Error retrieving cached assessment data: {str(e)}")
            return None
    
    def delete_assessment_cache(self, key: str) -> bool:
        """
        Delete cached assessment data.
        
        Args:
            key: Cache key to delete
            
        Returns:
            True if successful, False otherwise
        """
        try:
            cache.delete(key)
            logger.debug(f"Deleted cached assessment data for key: {key}")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting cached assessment data: {str(e)}")
            return False
    
    def clear_assessment_cache(self, pattern: str = "assessment_*") -> bool:
        """
        Clear all assessment cache entries matching a pattern.
        
        Args:
            pattern: Cache key pattern to match
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Note: This is a simplified implementation
            # In production, you might want to use a more sophisticated cache clearing mechanism
            # depending on your cache backend
            
            # For now, we'll just log that this was called
            logger.info(f"Assessment cache clear requested for pattern: {pattern}")
            
            # If using Redis, you could do:
            # from django_redis import get_redis_connection
            # redis_client = get_redis_connection("default")
            # keys = redis_client.keys(pattern)
            # if keys:
            #     redis_client.delete(*keys)
            
            return True
            
        except Exception as e:
            logger.error(f"Error clearing assessment cache: {str(e)}")
            return False
    
    def set_org_unit_cache(self, org_unit_id: str, data: Dict[str, Any], timeout: Optional[int] = None) -> bool:
        """
        Cache organization unit data.
        
        Args:
            org_unit_id: Organization unit ID
            data: Organization unit data
            timeout: Cache timeout in seconds
            
        Returns:
            True if successful, False otherwise
        """
        try:
            key = f"org_unit_{org_unit_id}"
            if timeout is None:
                timeout = self.default_timeout
            
            serialized_data = self._serialize_data(data)
            cache.set(key, serialized_data, timeout=timeout)
            
            logger.debug(f"Organization unit data cached for: {org_unit_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error caching organization unit data: {str(e)}")
            return False
    
    def get_org_unit_cache(self, org_unit_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve cached organization unit data.
        
        Args:
            org_unit_id: Organization unit ID
            
        Returns:
            Cached organization unit data or None
        """
        try:
            key = f"org_unit_{org_unit_id}"
            cached_data = cache.get(key)
            
            if cached_data is None:
                return None
            
            data = self._deserialize_data(cached_data)
            logger.debug(f"Retrieved cached organization unit data for: {org_unit_id}")
            return data
            
        except Exception as e:
            logger.error(f"Error retrieving cached organization unit data: {str(e)}")
            return None
    
    def set_indicator_cache(self, indicator_uid: str, data: Dict[str, Any], timeout: Optional[int] = None) -> bool:
        """
        Cache indicator data.
        
        Args:
            indicator_uid: Indicator UID
            data: Indicator data
            timeout: Cache timeout in seconds
            
        Returns:
            True if successful, False otherwise
        """
        try:
            key = f"indicator_{indicator_uid}"
            if timeout is None:
                timeout = self.default_timeout
            
            serialized_data = self._serialize_data(data)
            cache.set(key, serialized_data, timeout=timeout)
            
            logger.debug(f"Indicator data cached for: {indicator_uid}")
            return True
            
        except Exception as e:
            logger.error(f"Error caching indicator data: {str(e)}")
            return False
    
    def get_indicator_cache(self, indicator_uid: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve cached indicator data.
        
        Args:
            indicator_uid: Indicator UID
            
        Returns:
            Cached indicator data or None
        """
        try:
            key = f"indicator_{indicator_uid}"
            cached_data = cache.get(key)
            
            if cached_data is None:
                return None
            
            data = self._deserialize_data(cached_data)
            logger.debug(f"Retrieved cached indicator data for: {indicator_uid}")
            return data
            
        except Exception as e:
            logger.error(f"Error retrieving cached indicator data: {str(e)}")
            return None
    
    def set_period_cache(self, period: str, data: Dict[str, Any], timeout: Optional[int] = None) -> bool:
        """
        Cache period data.
        
        Args:
            period: Period string
            data: Period data
            timeout: Cache timeout in seconds
            
        Returns:
            True if successful, False otherwise
        """
        try:
            key = f"period_{period}"
            if timeout is None:
                timeout = self.default_timeout
            
            serialized_data = self._serialize_data(data)
            cache.set(key, serialized_data, timeout=timeout)
            
            logger.debug(f"Period data cached for: {period}")
            return True
            
        except Exception as e:
            logger.error(f"Error caching period data: {str(e)}")
            return False
    
    def get_period_cache(self, period: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve cached period data.
        
        Args:
            period: Period string
            
        Returns:
            Cached period data or None
        """
        try:
            key = f"period_{period}"
            cached_data = cache.get(key)
            
            if cached_data is None:
                return None
            
            data = self._deserialize_data(cached_data)
            logger.debug(f"Retrieved cached period data for: {period}")
            return data
            
        except Exception as e:
            logger.error(f"Error retrieving cached period data: {str(e)}")
            return None
    
    def set_user_assessments_cache(self, user_id: int, data: List[Dict[str, Any]], timeout: Optional[int] = None) -> bool:
        """
        Cache user assessments list.
        
        Args:
            user_id: User ID
            data: User assessments data
            timeout: Cache timeout in seconds
            
        Returns:
            True if successful, False otherwise
        """
        try:
            key = f"user_assessments_{user_id}"
            if timeout is None:
                timeout = self.default_timeout
            
            serialized_data = self._serialize_data(data)
            cache.set(key, serialized_data, timeout=timeout)
            
            logger.debug(f"User assessments cached for user: {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error caching user assessments: {str(e)}")
            return False
    
    def get_user_assessments_cache(self, user_id: int) -> Optional[List[Dict[str, Any]]]:
        """
        Retrieve cached user assessments.
        
        Args:
            user_id: User ID
            
        Returns:
            Cached user assessments or None
        """
        try:
            key = f"user_assessments_{user_id}"
            cached_data = cache.get(key)
            
            if cached_data is None:
                return None
            
            data = self._deserialize_data(cached_data)
            logger.debug(f"Retrieved cached user assessments for user: {user_id}")
            return data
            
        except Exception as e:
            logger.error(f"Error retrieving cached user assessments: {str(e)}")
            return None
    
    def invalidate_user_assessments_cache(self, user_id: int) -> bool:
        """
        Invalidate user assessments cache when assessments are modified.
        
        Args:
            user_id: User ID
            
        Returns:
            True if successful, False otherwise
        """
        try:
            key = f"user_assessments_{user_id}"
            cache.delete(key)
            
            logger.debug(f"Invalidated user assessments cache for user: {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error invalidating user assessments cache: {str(e)}")
            return False
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.
        
        Returns:
            Dictionary containing cache statistics
        """
        try:
            # This is a simplified implementation
            # In production, you might want to implement more detailed statistics
            # depending on your cache backend
            
            stats = {
                'cache_backend': getattr(settings, 'CACHES', {}).get('default', {}).get('BACKEND', 'unknown'),
                'default_timeout': self.default_timeout,
                'max_cache_size': self.max_cache_size,
                'timestamp': timezone.now().isoformat(),
            }
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting cache stats: {str(e)}")
            return {}
    
    def generate_cache_key(self, *args, **kwargs) -> str:
        """
        Generate a cache key from arguments.
        
        Args:
            *args: Positional arguments
            **kwargs: Keyword arguments
            
        Returns:
            Generated cache key
        """
        try:
            # Create a string representation of the arguments
            key_parts = []
            
            # Add positional arguments
            for arg in args:
                key_parts.append(str(arg))
            
            # Add keyword arguments (sorted for consistency)
            for key, value in sorted(kwargs.items()):
                key_parts.append(f"{key}:{value}")
            
            # Join parts and create hash
            key_string = "_".join(key_parts)
            key_hash = hashlib.md5(key_string.encode()).hexdigest()
            
            return f"assessment_{key_hash}"
            
        except Exception as e:
            logger.error(f"Error generating cache key: {str(e)}")
            # Fallback to a simple key
            return f"assessment_fallback_{hash(str(args) + str(kwargs))}"
    
    def _serialize_data(self, data: Any) -> str:
        """
        Serialize data for caching.
        
        Args:
            data: Data to serialize
            
        Returns:
            Serialized data string
        """
        try:
            # Handle datetime objects
            if isinstance(data, dict):
                data = self._convert_datetime_objects(data)
            elif isinstance(data, list):
                data = [self._convert_datetime_objects(item) if isinstance(item, dict) else item for item in data]
            
            return json.dumps(data, default=str)
            
        except Exception as e:
            logger.error(f"Error serializing data: {str(e)}")
            return json.dumps({})
    
    def _deserialize_data(self, serialized_data: str) -> Any:
        """
        Deserialize cached data.
        
        Args:
            serialized_data: Serialized data string
            
        Returns:
            Deserialized data
        """
        try:
            return json.loads(serialized_data)
            
        except Exception as e:
            logger.error(f"Error deserializing data: {str(e)}")
            return None
    
    def _convert_datetime_objects(self, obj: Any) -> Any:
        """
        Convert datetime objects to strings for JSON serialization.
        
        Args:
            obj: Object that may contain datetime objects
            
        Returns:
            Object with datetime objects converted to strings
        """
        if isinstance(obj, dict):
            converted = {}
            for key, value in obj.items():
                if isinstance(value, (timezone.datetime, timezone.date)):
                    converted[key] = value.isoformat()
                elif isinstance(value, dict):
                    converted[key] = self._convert_datetime_objects(value)
                elif isinstance(value, list):
                    converted[key] = [self._convert_datetime_objects(item) if isinstance(item, dict) else item for item in value]
                else:
                    converted[key] = value
            return converted
        else:
            return obj
    
    def cache_exists(self, key: str) -> bool:
        """
        Check if a cache key exists.
        
        Args:
            key: Cache key to check
            
        Returns:
            True if key exists, False otherwise
        """
        try:
            return cache.get(key) is not None
            
        except Exception as e:
            logger.error(f"Error checking cache existence: {str(e)}")
            return False
    
    def get_assessment_data(self, key: str) -> Optional[Any]:
        """
        Retrieve cached assessment data (alias for get_assessment_cache).
        
        Args:
            key: Cache key
            
        Returns:
            Cached data or None if not found
        """
        return self.get_assessment_cache(key)
    
    def set_assessment_data(self, key: str, data: Any, timeout: Optional[int] = None) -> bool:
        """
        Cache assessment data (alias for set_assessment_cache).
        
        Args:
            key: Cache key
            data: Data to cache
            timeout: Cache timeout in seconds (uses default if None)
            
        Returns:
            True if successful, False otherwise
        """
        return self.set_assessment_cache(key, data, timeout)

    def get_cache_ttl(self, key: str) -> Optional[int]:
        """
        Get time to live for a cache key.
        
        Args:
            key: Cache key
            
        Returns:
            TTL in seconds or None if key doesn't exist
        """
        try:
            # Note: This is a simplified implementation
            # The actual implementation depends on your cache backend
            # For Redis, you could use: redis_client.ttl(key)
            
            # For now, return None as a placeholder
            return None
            
        except Exception as e:
            logger.error(f"Error getting cache TTL: {str(e)}")
            return None
