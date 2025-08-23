"""
Data Processing Service

This service handles data cleaning, transformation, and extraction from DHIS2 responses.
It provides utilities for processing indicator data and converting between formats.
"""

import logging
import math
from typing import Dict, Any, Optional, List
from decimal import Decimal

logger = logging.getLogger(__name__)


class DataProcessingService:
    """
    Service for processing and cleaning data from various sources.
    """
    
    def clean_numeric_value(self, value: Any) -> Optional[float]:
        """
        Clean numeric values to ensure JSON compliance.
        
        Args:
            value: Value to clean
            
        Returns:
            Cleaned numeric value or None
        """
        if value is None:
            return None
        
        try:
            # Convert to float if it's a string
            if isinstance(value, str):
                value = float(value)
            
            # Check for NaN, infinity, or other invalid values
            if isinstance(value, (int, float)):
                if math.isnan(value) or math.isinf(value):
                    logger.warning(f"Invalid numeric value detected: {value}, setting to None")
                    return None
                return value
            
            return value
            
        except (ValueError, TypeError) as e:
            logger.warning(f"Error cleaning numeric value {value}: {str(e)}")
            return None
    
    def calculate_percent_change(
        self, 
        current_value: Optional[float], 
        previous_value: Optional[float], 
        indicator
    ) -> Optional[float]:
        """
        Calculate percentage change between current and previous values.
        
        Args:
            current_value: Current period value
            previous_value: Previous period value
            indicator: Indicator instance
            
        Returns:
            Percentage change or None
        """
        if current_value is None or previous_value is None:
            return None
        
        try:
            target_format = getattr(indicator, 'target_format', 'SINGLE')
            
            if target_format == 'RANGE':
                # For range indicators, always use standard formula regardless of target_type
                if previous_value != 0:
                    return round(((current_value - previous_value) / abs(previous_value)) * 100, 2)
            else:
                # For non-range indicators, use target_type specific formula
                if indicator.target_type == 'decrease':
                    # For decrease indicators: (previous_value - current_value) / abs(current_value) * 100
                    if current_value != 0:
                        return round(((previous_value - current_value) / abs(current_value)) * 100, 2)
                    else:
                        # Special case: current value is 0 for decrease indicator
                        return None
                else:
                    # For increase indicators: (current_value - previous_value) / abs(previous_value) * 100
                    if previous_value != 0:
                        return round(((current_value - previous_value) / abs(previous_value)) * 100, 2)
            
            return None
            
        except Exception as e:
            logger.warning(f"Error calculating percent change: {str(e)}")
            return None
    
    def calculate_target_gap(self, current_value: Optional[float], indicator_data: Dict[str, Any], indicator) -> Optional[float]:
        """
        Calculate gap to target.
        
        Args:
            current_value: Current value
            indicator_data: Indicator data dictionary
            indicator: Indicator instance
            
        Returns:
            Target gap percentage or None
        """
        if current_value is None:
            return None
        
        try:
            # Handle different target formats for gap calculation
            if hasattr(indicator, 'target_format') and indicator.target_format == 'RANGE':
                # Range target: calculate gap to the upper limit
                if indicator.target_lower_limit is not None and indicator.target_upper_limit is not None:
                    upper_limit = float(indicator.target_upper_limit)
                    if upper_limit != 0:
                        return round((current_value - upper_limit) / upper_limit * 100, 2)
                else:
                    # Fallback to single target value
                    target_value = indicator_data.get('target_value')
                    if target_value is not None:
                        target_float = float(target_value)
                        if target_float != 0:
                            if indicator.target_type == 'decrease':
                                if current_value != 0:
                                    return round((target_float - current_value) / current_value * 100, 2)
                                else:
                                    return None
                            else:
                                return round((current_value - target_float) / target_float * 100, 2)
            else:
                # Single value target
                target_value = indicator_data.get('target_value')
                if target_value is not None:
                    target_float = float(target_value)
                    if target_float != 0:
                        if indicator.target_type == 'decrease':
                            if current_value != 0:
                                return round((target_float - current_value) / current_value * 100, 2)
                            else:
                                return None
                        else:
                            return round((current_value - target_float) / target_float * 100, 2)
            
            return None
            
        except Exception as e:
            logger.warning(f"Error calculating target gap: {str(e)}")
            return None
    
    def extract_value_from_analytics_response(self, response: Dict[str, Any], indicator_uid: str) -> Optional[float]:
        """
        Extract value from DHIS2 analytics response.
        
        Args:
            response: DHIS2 analytics response
            indicator_uid: Indicator UID
            
        Returns:
            Extracted value or None
        """
        try:
            if not response or not isinstance(response, dict):
                logger.warning(f"Invalid response format for indicator {indicator_uid}")
                return None
            
            # Check for rows in response
            rows = response.get('rows', [])
            if not rows:
                # This is normal - some indicators don't have data for all periods/org units
                logger.info(f"No data available for indicator {indicator_uid} - this is normal if the indicator has no data for the specified period/org unit")
                return None
            
            # Get headers to understand the structure
            headers = response.get('headers', [])
            if not headers:
                logger.warning(f"No headers found in response for indicator {indicator_uid}")
                return None
            
            # Enhanced column detection
            # Look for the indicator UID in the headers
            indicator_column_index = None
            value_column_index = None
            
            for i, header in enumerate(headers):
                header_name = header.get('name', '').lower()
                header_column = header.get('column', '').lower()
                
                # Check if this header contains our indicator UID
                if indicator_uid.lower() in header_name or indicator_uid.lower() in header_column:
                    indicator_column_index = i
                    break
            
            # If we found the indicator column, the value should be in the next column
            if indicator_column_index is not None:
                value_column_index = indicator_column_index + 1
            else:
                # Fallback: look for value columns
                for i, header in enumerate(headers):
                    header_name = header.get('name', '').lower()
                    if 'value' in header_name or 'data' in header_name:
                        value_column_index = i
                        break
            
            # If still no value column found, use the last column
            if value_column_index is None and len(headers) > 1:
                value_column_index = len(headers) - 1
            
            logger.debug(f"Using value column index {value_column_index} for indicator {indicator_uid}")
            
            # Extract value from the first row
            if value_column_index is not None and len(rows) > 0:
                first_row = rows[0]
                if len(first_row) > value_column_index:
                    value = first_row[value_column_index]
                    logger.debug(f"Extracted value {value} from row {first_row}")
                    
                    # Convert to float if possible
                    try:
                        if isinstance(value, str):
                            value = float(value)
                        return value
                    except (ValueError, TypeError):
                        logger.warning(f"Could not convert value '{value}' to float for indicator {indicator_uid}")
                        return None
            
            # Try alternative parsing if standard parsing fails
            logger.info(f"Standard parsing failed, trying alternative parsing for indicator {indicator_uid}")
            return self._extract_value_alternative_parsing(response, indicator_uid, value_column_index)
            
        except Exception as e:
            logger.error(f"Error extracting value from analytics response for indicator {indicator_uid}: {str(e)}")
            return None
    
    def extract_value_from_dataset_response(self, response: Dict[str, Any], indicator_uid: str) -> Optional[float]:
        """
        Extract value from DHIS2 dataset response.
        
        Args:
            response: DHIS2 dataset response
            indicator_uid: Indicator UID
            
        Returns:
            Extracted value or None
        """
        try:
            if not response or not isinstance(response, dict):
                logger.warning(f"Invalid dataset response format for indicator {indicator_uid}")
                return None
            
            # Check if indicator_uid is valid
            if not indicator_uid or indicator_uid == 'None':
                logger.warning(f"Invalid indicator UID: {indicator_uid}")
                return None
            
            # Dataset responses have a different structure
            # Look for the indicator in the response
            if indicator_uid in response:
                value = response[indicator_uid]
                if value is None:
                    logger.debug(f"Dataset value is None for indicator {indicator_uid}")
                    return None
                
                # Handle string 'None' values
                if isinstance(value, str) and value.lower() == 'none':
                    logger.debug(f"Dataset value is string 'None' for indicator {indicator_uid}")
                    return None
                
                try:
                    return float(value)
                except (ValueError, TypeError):
                    logger.warning(f"Could not convert dataset value '{value}' to float for indicator {indicator_uid}")
                    return None
            
            logger.warning(f"Indicator {indicator_uid} not found in dataset response")
            return None
            
        except Exception as e:
            logger.error(f"Error extracting value from dataset response for indicator {indicator_uid}: {str(e)}")
            return None
    
    def _extract_value_alternative_parsing(self, response: Dict[str, Any], indicator_uid: str, value_column_index: Optional[int]) -> Optional[float]:
        """
        Alternative parsing method for analytics response.
        
        Args:
            response: DHIS2 analytics response
            indicator_uid: Indicator UID
            value_column_index: Value column index
            
        Returns:
            Extracted value or None
        """
        try:
            logger.info(f"Starting alternative parsing for {indicator_uid}")
            
            # Try to find the indicator in metadata
            meta_data = response.get('metaData', {})
            items = meta_data.get('items', {})
            
            # Look for the indicator in the items
            if indicator_uid in items:
                item_info = items[indicator_uid]
                logger.info(f"Found indicator info in metadata: {item_info}")
            
            # Process rows with more flexible matching
            rows = response.get('rows', [])
            logger.info(f"Alternative parsing: processing {len(rows)} rows")
            
            for i, row in enumerate(rows):
                if value_column_index is None or len(row) <= value_column_index:
                    logger.debug(f"Alternative parsing: skipping row {i} with insufficient columns")
                    continue
                
                # Try to match by checking if the indicator UID appears anywhere in the row
                row_str = ' '.join(str(cell) for cell in row)
                if indicator_uid in row_str:
                    logger.info(f"Alternative parsing: found indicator {indicator_uid} in row {i}: {row}")
                    raw_value = row[value_column_index]
                    
                    if raw_value is None or raw_value == '':
                        logger.warning(f"Alternative parsing: empty value found for {indicator_uid}")
                        return None
                    
                    try:
                        value = float(raw_value)
                        logger.info(f"Alternative parsing: successfully extracted value {value} for {indicator_uid}")
                        return value
                    except (ValueError, TypeError):
                        logger.warning(f"Alternative parsing: could not convert value '{raw_value}' to float for {indicator_uid}")
                        continue
            
            logger.warning(f"Alternative parsing: no value found for {indicator_uid}")
            return None
            
        except Exception as e:
            logger.error(f"Error in alternative parsing for indicator {indicator_uid}: {str(e)}")
            return None
    
    def parse_decimal(self, value: Any) -> Optional[Decimal]:
        """
        Parse a value to Decimal, handling None and empty strings.
        
        Args:
            value: Value to parse
            
        Returns:
            Decimal value or None
        """
        if value is None or value == '':
            return None
        try:
            return Decimal(str(value))
        except (ValueError, TypeError):
            return None
    
    def format_percentage(self, value: Optional[float], decimal_places: int = 2) -> str:
        """
        Format a value as a percentage string.
        
        Args:
            value: Value to format
            decimal_places: Number of decimal places
            
        Returns:
            Formatted percentage string
        """
        if value is None:
            return ''
        
        try:
            return f"{value:.{decimal_places}f}%"
        except (ValueError, TypeError):
            return ''
    
    def format_number(self, value: Optional[float], decimal_places: int = 2) -> str:
        """
        Format a number with specified decimal places.
        
        Args:
            value: Value to format
            decimal_places: Number of decimal places
            
        Returns:
            Formatted number string
        """
        if value is None:
            return ''
        
        try:
            return f"{value:.{decimal_places}f}"
        except (ValueError, TypeError):
            return ''
    
    def validate_data_consistency(self, data: Dict[str, Any]) -> List[str]:
        """
        Validate data consistency and return any issues found.
        
        Args:
            data: Data to validate
            
        Returns:
            List of validation issues
        """
        issues = []
        
        try:
            # Check for required fields
            required_fields = ['org_unit_id', 'periods']
            for field in required_fields:
                if field not in data:
                    issues.append(f"Missing required field: {field}")
            
            # Check data types
            if 'org_unit_id' in data and not isinstance(data['org_unit_id'], str):
                issues.append("org_unit_id must be a string")
            
            if 'periods' in data and not isinstance(data['periods'], list):
                issues.append("periods must be a list")
            
            # Check for empty values
            if 'org_unit_id' in data and not data['org_unit_id'].strip():
                issues.append("org_unit_id cannot be empty")
            
            if 'periods' in data and len(data['periods']) == 0:
                issues.append("At least one period must be specified")
            
            # Check indicator data structure
            if 'objectives' in data:
                for i, objective in enumerate(data['objectives']):
                    if not isinstance(objective, dict):
                        issues.append(f"Objective {i} must be a dictionary")
                        continue
                    
                    if 'indicators' in objective:
                        for j, indicator in enumerate(objective['indicators']):
                            if not isinstance(indicator, dict):
                                issues.append(f"Indicator {j} in objective {i} must be a dictionary")
                                continue
                            
                            # Check indicator data values
                            if 'data_values' in indicator:
                                for period, value_data in indicator['data_values'].items():
                                    if not isinstance(value_data, dict):
                                        issues.append(f"Data value for period {period} in indicator {j} must be a dictionary")
                                        continue
                                    
                                    # Check if value is numeric
                                    value = value_data.get('value')
                                    if value is not None:
                                        try:
                                            float(value)
                                        except (ValueError, TypeError):
                                            issues.append(f"Value for period {period} in indicator {j} must be numeric")
            
        except Exception as e:
            issues.append(f"Error during validation: {str(e)}")
        
        return issues
    
    def normalize_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalize data structure for consistency.
        
        Args:
            data: Data to normalize
            
        Returns:
            Normalized data
        """
        try:
            normalized = {}
            
            # Normalize basic fields
            for key, value in data.items():
                if key == 'org_unit_id':
                    normalized[key] = str(value).strip() if value else ''
                elif key == 'periods':
                    normalized[key] = [str(p).strip() for p in value] if isinstance(value, list) else []
                elif key == 'name':
                    normalized[key] = str(value).strip() if value else ''
                elif key == 'user_notes':
                    normalized[key] = str(value).strip() if value else ''
                else:
                    normalized[key] = value
            
            # Normalize objectives and indicators
            if 'objectives' in normalized:
                for objective in normalized['objectives']:
                    if isinstance(objective, dict):
                        # Normalize objective fields
                        for key, value in objective.items():
                            if key == 'name':
                                objective[key] = str(value).strip() if value else ''
                            elif key == 'code':
                                objective[key] = str(value).strip() if value else ''
                        
                        # Normalize indicators
                        if 'indicators' in objective:
                            for indicator in objective['indicators']:
                                if isinstance(indicator, dict):
                                    # Normalize indicator fields
                                    for key, value in indicator.items():
                                        if key == 'name':
                                            indicator[key] = str(value).strip() if value else ''
                                        elif key == 'description':
                                            indicator[key] = str(value).strip() if value else ''
                                        elif key == 'indicator_number':
                                            indicator[key] = str(value).strip() if value else ''
                                    
                                    # Normalize data values
                                    if 'data_values' in indicator:
                                        for period, value_data in indicator['data_values'].items():
                                            if isinstance(value_data, dict):
                                                # Ensure value is numeric
                                                value = value_data.get('value')
                                                if value is not None:
                                                    try:
                                                        value_data['value'] = float(value)
                                                    except (ValueError, TypeError):
                                                        value_data['value'] = None
            
            return normalized
            
        except Exception as e:
            logger.error(f"Error normalizing data: {str(e)}")
            return data
    
    def aggregate_indicator_data(self, indicators: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Aggregate indicator data for summary statistics.
        
        Args:
            indicators: List of indicator data
            
        Returns:
            Aggregated statistics
        """
        try:
            stats = {
                'total_indicators': len(indicators),
                'indicators_with_data': 0,
                'indicators_without_data': 0,
                'average_score': 0,
                'score_distribution': {},
                'target_achievement_rate': 0,
                'performance_trends': {
                    'improving': 0,
                    'declining': 0,
                    'stable': 0
                }
            }
            
            total_score = 0
            indicators_with_score = 0
            indicators_achieving_target = 0
            
            for indicator in indicators:
                # Check if indicator has data
                has_data = False
                if 'data_values' in indicator:
                    for period_data in indicator['data_values'].values():
                        if isinstance(period_data, dict) and period_data.get('value') is not None:
                            has_data = True
                            break
                
                if has_data:
                    stats['indicators_with_data'] += 1
                else:
                    stats['indicators_without_data'] += 1
                
                # Check score
                if 'score' in indicator and indicator['score'] is not None:
                    score = indicator['score']
                    if isinstance(score, dict):
                        score_value = score.get('score')
                    else:
                        score_value = score
                    
                    if score_value is not None:
                        total_score += float(score_value)
                        indicators_with_score += 1
                        
                        # Score distribution
                        score_label = 'Unknown'
                        if isinstance(score, dict):
                            score_label = score.get('score_label', 'Unknown')
                        
                        stats['score_distribution'][score_label] = stats['score_distribution'].get(score_label, 0) + 1
                
                # Check target achievement
                if 'score' in indicator and isinstance(indicator['score'], dict):
                    target_achieved = indicator['score'].get('target_achieved')
                    if target_achieved == 'Yes':
                        indicators_achieving_target += 1
                
                # Check performance trend
                if 'score' in indicator and isinstance(indicator['score'], dict):
                    change_category = indicator['score'].get('change_category')
                    if change_category:
                        if '>' in change_category and '5%' in change_category:
                            stats['performance_trends']['improving'] += 1
                        elif '<' in change_category and '-5%' in change_category:
                            stats['performance_trends']['declining'] += 1
                        else:
                            stats['performance_trends']['stable'] += 1
            
            # Calculate averages
            if indicators_with_score > 0:
                stats['average_score'] = round(total_score / indicators_with_score, 2)
            
            if stats['indicators_with_data'] > 0:
                stats['target_achievement_rate'] = round(
                    (indicators_achieving_target / stats['indicators_with_data']) * 100, 2
                )
            
            return stats
            
        except Exception as e:
            logger.error(f"Error aggregating indicator data: {str(e)}")
            return {
                'total_indicators': 0,
                'indicators_with_data': 0,
                'indicators_without_data': 0,
                'average_score': 0,
                'score_distribution': {},
                'target_achievement_rate': 0,
                'performance_trends': {'improving': 0, 'declining': 0, 'stable': 0}
            }
