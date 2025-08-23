"""
Validation Service

This service handles validation of assessment data, configuration, and user inputs.
It provides centralized validation logic for the assessment module.
"""

import logging
from typing import Dict, Any, List, Optional
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.utils.translation import gettext_lazy as _

logger = logging.getLogger(__name__)


class ValidationService:
    """
    Service for validating assessment data and configuration.
    """
    
    def validate_assessment_config(self, config: Dict[str, Any]) -> None:
        """
        Validate assessment configuration.
        
        Args:
            config: Assessment configuration dictionary
            
        Raises:
            ValidationError: If configuration is invalid
        """
        if not isinstance(config, dict):
            raise ValidationError("Assessment configuration must be a dictionary")
        
        # Validate required fields
        required_fields = ['org_unit_ids', 'periods']
        for field in required_fields:
            if field not in config:
                raise ValidationError(f"Missing required field: {field}")
        
        # Validate org_unit_ids
        org_unit_ids = config.get('org_unit_ids', [])
        if not isinstance(org_unit_ids, list):
            raise ValidationError("org_unit_ids must be a list")
        if not org_unit_ids:
            raise ValidationError("At least one organization unit must be specified")
        
        for org_unit_id in org_unit_ids:
            if not isinstance(org_unit_id, str) or not org_unit_id.strip():
                raise ValidationError("Organization unit IDs must be non-empty strings")
        
        # Validate periods
        periods = config.get('periods', [])
        if not isinstance(periods, list):
            raise ValidationError("periods must be a list")
        if not periods:
            raise ValidationError("At least one period must be specified")
        
        for period in periods:
            if not self._is_valid_period(period):
                raise ValidationError(f"Invalid period format: {period}")
        
        # Validate optional fields
        if 'indicator_uids' in config:
            indicator_uids = config['indicator_uids']
            if not isinstance(indicator_uids, list):
                raise ValidationError("indicator_uids must be a list")
            
            for uid in indicator_uids:
                if not isinstance(uid, str) or not uid.strip():
                    raise ValidationError("Indicator UIDs must be non-empty strings")
        
        if 'manual_entries' in config:
            manual_entries = config['manual_entries']
            if not isinstance(manual_entries, dict):
                raise ValidationError("manual_entries must be a dictionary")
            
            self._validate_manual_entries(manual_entries)
    
    def validate_assessment_data(self, data: Dict[str, Any]) -> None:
        """
        Validate assessment data before saving.
        
        Args:
            data: Assessment data dictionary
            
        Raises:
            ValidationError: If data is invalid
        """
        if not isinstance(data, dict):
            raise ValidationError("Assessment data must be a dictionary")
        
        # Validate required fields
        required_fields = ['org_unit_id']
        for field in required_fields:
            if field not in data:
                raise ValidationError(f"Missing required field: {field}")
        
        # Validate org_unit_id
        org_unit_id = data.get('org_unit_id')
        if not isinstance(org_unit_id, str) or not org_unit_id.strip():
            raise ValidationError("org_unit_id must be a non-empty string")
        
        # Validate name
        name = data.get('name', '')
        if not isinstance(name, str):
            raise ValidationError("name must be a string")
        if len(name.strip()) == 0:
            raise ValidationError("name cannot be empty")
        if len(name) > 255:
            raise ValidationError("name cannot exceed 255 characters")
        
        # Validate periods
        periods = data.get('periods', [])
        if not isinstance(periods, list):
            raise ValidationError("periods must be a list")
        
        for period in periods:
            if not self._is_valid_period(period):
                raise ValidationError(f"Invalid period format: {period}")
        
        # Validate user_notes
        user_notes = data.get('user_notes', '')
        if not isinstance(user_notes, str):
            raise ValidationError("user_notes must be a string")
        if len(user_notes) > 10000:  # 10KB limit
            raise ValidationError("user_notes cannot exceed 10,000 characters")
        
        # Validate indicator_data
        indicator_data = data.get('indicator_data', {})
        if not isinstance(indicator_data, dict):
            raise ValidationError("indicator_data must be a dictionary")
        
        # Validate calculated_scores
        calculated_scores = data.get('calculated_scores', {})
        if not isinstance(calculated_scores, dict):
            raise ValidationError("calculated_scores must be a dictionary")
        
        # Validate metadata
        metadata = data.get('metadata', {})
        if not isinstance(metadata, dict):
            raise ValidationError("metadata must be a dictionary")
    
    def validate_indicator_data(self, indicator_data: Dict[str, Any]) -> None:
        """
        Validate individual indicator data.
        
        Args:
            indicator_data: Indicator data dictionary
            
        Raises:
            ValidationError: If data is invalid
        """
        if not isinstance(indicator_data, dict):
            raise ValidationError("Indicator data must be a dictionary")
        
        # Validate required fields
        required_fields = ['id', 'name']
        for field in required_fields:
            if field not in indicator_data:
                raise ValidationError(f"Missing required field: {field}")
        
        # Validate id
        indicator_id = indicator_data.get('id')
        if not isinstance(indicator_id, (int, str)):
            raise ValidationError("indicator id must be an integer or string")
        
        # Validate name
        name = indicator_data.get('name')
        if not isinstance(name, str) or not name.strip():
            raise ValidationError("indicator name must be a non-empty string")
        
        # Validate target_value
        target_value = indicator_data.get('target_value')
        if target_value is not None:
            if not isinstance(target_value, (int, float, str)):
                raise ValidationError("target_value must be a number or string")
            try:
                float(target_value)
            except (ValueError, TypeError):
                raise ValidationError("target_value must be a valid number")
        
        # Validate data_values
        data_values = indicator_data.get('data_values', {})
        if not isinstance(data_values, dict):
            raise ValidationError("data_values must be a dictionary")
        
        for period, value_data in data_values.items():
            if not isinstance(value_data, dict):
                raise ValidationError(f"data_values[{period}] must be a dictionary")
            
            # Validate value
            value = value_data.get('value')
            if value is not None:
                if not isinstance(value, (int, float, str)):
                    raise ValidationError(f"data_values[{period}].value must be a number or string")
                try:
                    float(value)
                except (ValueError, TypeError):
                    raise ValidationError(f"data_values[{period}].value must be a valid number")
    
    def validate_manual_entries(self, manual_entries: Dict[str, Any]) -> None:
        """
        Validate manual data entries.
        
        Args:
            manual_entries: Manual entries dictionary
            
        Raises:
            ValidationError: If entries are invalid
        """
        self._validate_manual_entries(manual_entries)
    
    def validate_period_format(self, period: str) -> bool:
        """
        Validate period format.
        
        Args:
            period: Period string to validate
            
        Returns:
            True if valid, False otherwise
        """
        return self._is_valid_period(period)
    
    def validate_org_unit_id(self, org_unit_id: str) -> bool:
        """
        Validate organization unit ID format.
        
        Args:
            org_unit_id: Organization unit ID to validate
            
        Returns:
            True if valid, False otherwise
        """
        if not isinstance(org_unit_id, str):
            return False
        
        if not org_unit_id.strip():
            return False
        
        # Check for valid characters (alphanumeric, hyphens, underscores)
        import re
        if not re.match(r'^[a-zA-Z0-9_-]+$', org_unit_id):
            return False
        
        return True
    
    def validate_indicator_uid(self, indicator_uid: str) -> bool:
        """
        Validate indicator UID format.
        
        Args:
            indicator_uid: Indicator UID to validate
            
        Returns:
            True if valid, False otherwise
        """
        if not isinstance(indicator_uid, str):
            return False
        
        if not indicator_uid.strip():
            return False
        
        # Check for valid characters (alphanumeric, hyphens, underscores, dots)
        import re
        if not re.match(r'^[a-zA-Z0-9_.-]+$', indicator_uid):
            return False
        
        return True
    
    def validate_score_value(self, score: Any) -> bool:
        """
        Validate score value.
        
        Args:
            score: Score value to validate
            
        Returns:
            True if valid, False otherwise
        """
        if score is None:
            return True
        
        if not isinstance(score, (int, float)):
            return False
        
        # Check if score is within valid range (-5 to 5)
        if not -5 <= score <= 5:
            return False
        
        return True
    
    def validate_user_permissions(self, user, org_unit_id: str) -> bool:
        """
        Validate user permissions for accessing organization unit.
        
        Args:
            user: User instance
            org_unit_id: Organization unit ID
            
        Returns:
            True if user has permission, False otherwise
        """
        if not user or not user.is_authenticated:
            return False
        
        # Add your permission logic here
        # For now, return True for authenticated users
        return True
    
    def _validate_manual_entries(self, manual_entries: Dict[str, Any]) -> None:
        """
        Validate manual entries structure.
        
        Args:
            manual_entries: Manual entries dictionary
            
        Raises:
            ValidationError: If entries are invalid
        """
        for indicator_id, period_data in manual_entries.items():
            if not isinstance(indicator_id, str):
                raise ValidationError("Indicator ID must be a string")
            
            if not isinstance(period_data, dict):
                raise ValidationError(f"Period data for indicator {indicator_id} must be a dictionary")
            
            for period, value in period_data.items():
                if not isinstance(period, str):
                    raise ValidationError(f"Period must be a string for indicator {indicator_id}")
                
                if not self._is_valid_period(period):
                    raise ValidationError(f"Invalid period format: {period} for indicator {indicator_id}")
                
                if value is not None:
                    if not isinstance(value, (int, float, str)):
                        raise ValidationError(f"Value must be a number or string for indicator {indicator_id}, period {period}")
                    
                    try:
                        float(value)
                    except (ValueError, TypeError):
                        raise ValidationError(f"Value must be a valid number for indicator {indicator_id}, period {period}")
    
    def _is_valid_period(self, period: Any) -> bool:
        """
        Check if period format is valid.
        
        Args:
            period: Period to validate
            
        Returns:
            True if valid, False otherwise
        """
        if not isinstance(period, (str, dict)):
            return False
        
        if isinstance(period, dict):
            # Handle period object format
            if 'code' in period:
                period = period['code']
            else:
                return False
        
        if not isinstance(period, str):
            return False
        
        # Check for valid period formats
        import re
        
        # Yearly: 2024
        if re.match(r'^\d{4}$', period):
            return True
        
        # Six-monthly: 2024S1, 2024S2
        if re.match(r'^\d{4}S[1-2]$', period):
            return True
        
        # Six-monthly with space: 2024 S1, 2024 S2
        if re.match(r'^\d{4}\s+S[1-2]$', period):
            return True
        
        # Quarterly: 2024Q1, 2024Q2, 2024Q3, 2024Q4
        if re.match(r'^\d{4}Q[1-4]$', period):
            return True
        
        # Quarterly with space: 2024 Q1, 2024 Q2, 2024 Q3, 2024 Q4
        if re.match(r'^\d{4}\s+Q[1-4]$', period):
            return True
        
        # Monthly: 202401, 202402, etc.
        if re.match(r'^\d{6}$', period):
            return True
        
        # Weekly: 2024W1, 2024W2, etc.
        if re.match(r'^\d{4}W[1-53]$', period):
            return True
        
        # Weekly with space: 2024 W1, 2024 W2, etc.
        if re.match(r'^\d{4}\s+W[1-53]$', period):
            return True
        
        # Date strings: 2024-01-01
        if re.match(r'^\d{4}-\d{2}-\d{2}$', period):
            return True
        
        # Relative periods
        relative_periods = {
            'THIS_YEAR', 'LAST_YEAR', 'THIS_QUARTER', 'LAST_QUARTER',
            'THIS_MONTH', 'LAST_MONTH', 'THIS_SIX_MONTH', 'LAST_SIX_MONTH'
        }
        if period in relative_periods:
            return True
        
        # Handle human-readable period formats like "January 2023"
        import re
        month_names = [
            'January', 'February', 'March', 'April', 'May', 'June',
            'July', 'August', 'September', 'October', 'November', 'December'
        ]
        
        # Pattern for "Month Year" format
        month_year_pattern = r'^(' + '|'.join(month_names) + r')\s+\d{4}$'
        if re.match(month_year_pattern, period, re.IGNORECASE):
            return True
        
        # Pattern for "Month Year" with comma
        month_year_comma_pattern = r'^(' + '|'.join(month_names) + r'),\s*\d{4}$'
        if re.match(month_year_comma_pattern, period, re.IGNORECASE):
            return True
        
        return False
    
    def sanitize_input(self, input_data: Any) -> Any:
        """
        Sanitize user input to prevent injection attacks.
        
        Args:
            input_data: Input data to sanitize
            
        Returns:
            Sanitized data
        """
        if isinstance(input_data, str):
            # Remove potentially dangerous characters
            import re
            # Remove script tags and other potentially dangerous content
            sanitized = re.sub(r'<script.*?</script>', '', input_data, flags=re.IGNORECASE | re.DOTALL)
            sanitized = re.sub(r'<.*?>', '', sanitized)  # Remove all HTML tags
            return sanitized.strip()
        
        elif isinstance(input_data, dict):
            return {key: self.sanitize_input(value) for key, value in input_data.items()}
        
        elif isinstance(input_data, list):
            return [self.sanitize_input(item) for item in input_data]
        
        else:
            return input_data
    
    def validate_file_upload(self, file_obj, allowed_types: List[str] = None, max_size: int = 10485760) -> None:
        """
        Validate file upload.
        
        Args:
            file_obj: File object to validate
            allowed_types: List of allowed MIME types
            max_size: Maximum file size in bytes (default: 10MB)
            
        Raises:
            ValidationError: If file is invalid
        """
        if not file_obj:
            raise ValidationError("No file provided")
        
        # Check file size
        if hasattr(file_obj, 'size') and file_obj.size > max_size:
            raise ValidationError(f"File size exceeds maximum allowed size of {max_size} bytes")
        
        # Check file type
        if allowed_types and hasattr(file_obj, 'content_type'):
            if file_obj.content_type not in allowed_types:
                raise ValidationError(f"File type {file_obj.content_type} is not allowed. Allowed types: {', '.join(allowed_types)}")
        
        # Check file extension
        if hasattr(file_obj, 'name'):
            import os
            file_extension = os.path.splitext(file_obj.name)[1].lower()
            allowed_extensions = ['.xlsx', '.xls', '.csv', '.json']
            if file_extension not in allowed_extensions:
                raise ValidationError(f"File extension {file_extension} is not allowed. Allowed extensions: {', '.join(allowed_extensions)}")
