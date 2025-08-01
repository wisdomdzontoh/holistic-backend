import json
import logging
from typing import Optional
from django.conf import settings
from configurations.models import SystemConfiguration

logger = logging.getLogger(__name__)


def get_default_dhis2_instance_url() -> Optional[str]:
    """
    Get the default DHIS2 instance URL from system configuration or settings.
    
    Returns:
        str: The default DHIS2 instance URL, or None if not configured
    """
    try:
        # First try to get from system configuration
        config = SystemConfiguration.objects.filter(
            key='dhis2_integration',
            is_active=True
        ).first()
        
        if config:
            config_data = config.get_value_as_json()
            if config_data and 'default_instance_url' in config_data:
                return config_data['default_instance_url']
        
        # Fallback to settings.py default
        if hasattr(settings, 'DEFAULT_DHIS2_URL') and settings.DEFAULT_DHIS2_URL:
            logger.info(f"Using default DHIS2 URL from settings: {settings.DEFAULT_DHIS2_URL}")
            return settings.DEFAULT_DHIS2_URL
        
        logger.warning("No default DHIS2 instance URL configured in system settings or Django settings")
        return None
        
    except Exception as e:
        logger.error(f"Error getting default DHIS2 instance URL: {str(e)}")
        # Fallback to settings.py default even if there's an error
        if hasattr(settings, 'DEFAULT_DHIS2_URL') and settings.DEFAULT_DHIS2_URL:
            return settings.DEFAULT_DHIS2_URL
        return None


def get_dhis2_integration_config() -> dict:
    """
    Get the complete DHIS2 integration configuration.
    
    Returns:
        dict: Configuration dictionary with default values if not configured
    """
    default_config = {
        'default_instance_url': getattr(settings, 'DEFAULT_DHIS2_URL', 'https://dhims.chimgh.org/dhims'),
        'timeout_seconds': 30,
        'retry_attempts': 3
    }
    
    try:
        config = SystemConfiguration.objects.filter(
            key='dhis2_integration',
            is_active=True
        ).first()
        
        if config:
            config_data = config.get_value_as_json()
            if config_data:
                default_config.update(config_data)
        
        return default_config
        
    except Exception as e:
        logger.error(f"Error getting DHIS2 integration config: {str(e)}")
        return default_config 