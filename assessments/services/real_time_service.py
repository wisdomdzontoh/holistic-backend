"""
Real-time DHIS2 Service

This module handles real-time data fetching from DHIS2 without persistent storage.
Uses the same synchronous approach as the working old_services.py
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from django.conf import settings
from django.core.cache import cache
from django.utils import timezone

from ..models import TrackedIndicator
from .validation_service import ValidationService
from .cache_service import CacheService
from .data_processing_service import DataProcessingService
from .period_service import PeriodService
from dhis2_auth.dhis_client import DHIS2ClientFactory
from dhis2_auth.session import get_dhis2_session_data

logger = logging.getLogger(__name__)


class RealTimeDHIS2Service:
    """
    Service for real-time DHIS2 data fetching without database storage
    Uses the same synchronous approach as the working old_services.py
    """
    
    def __init__(self, dhis2_client=None):
        self.client = dhis2_client
        self.logger = logging.getLogger(__name__)
        self.validation_service = ValidationService()
        self.cache_service = CacheService()
        self.data_processor = DataProcessingService()
        self.period_service = PeriodService()
    
    def fetch_holistic_assessment_data(self, request, assessment_config):
        """
        Fetch real-time DHIS2 data for holistic assessment display
        No database storage - just fetch and return for immediate display
        Uses the same approach as the working old_services.py
        """
        try:
            # Get DHIS2 user from session
            from dhis2_auth.session import get_dhis2_user_from_request
            dhis2_user = get_dhis2_user_from_request(request)
            if not dhis2_user:
                raise ValueError("No DHIS2 user found in session")
            
            # Initialize client if not provided
            if not self.client:
                self.client = DHIS2ClientFactory.create_client_from_session(
                    dhis2_user.dhis2_instance_url,
                    request.session.session_key
                )
            
            # Extract configuration
            org_unit_ids = assessment_config.get('org_unit_ids', [])
            org_unit_names = assessment_config.get('org_unit_names', [])
            periods_raw = assessment_config.get('periods', [])
            indicator_uids = assessment_config.get('indicator_uids', [])
            manual_entries = assessment_config.get('manual_entries', {})
            pre_calculated_scores = assessment_config.get('pre_calculated_scores', {})
            self.logger.info(f"Org unit names received: {org_unit_names}")
            
            # Handle periods - they can be strings or objects with 'code' field
            periods = []
            for period in periods_raw:
                if isinstance(period, dict) and 'code' in period:
                    periods.append(period['code'])
                elif isinstance(period, str):
                    periods.append(period)
                else:
                    # Fallback: try to extract code from period object
                    period_code = getattr(period, 'code', str(period))
                    periods.append(period_code)
            
            # Sort periods chronologically to ensure correct change calculation
            periods.sort()
            
            if not org_unit_ids or not periods:
                raise ValueError("Organization units and periods are required")
            
            # Fetch active indicators if not specified
            if not indicator_uids:
                indicators = TrackedIndicator.objects.filter(is_active=True)
                indicator_uids = [ind.dhis2_uid for ind in indicators if ind.dhis2_uid]
            
            # Fetch data for each indicator
            assessment_data = {
                'indicators': [],
                'objectives': [],
                'milestones': [],
                'metadata': {
                    'org_units': org_unit_ids,
                    'periods': periods,
                    'fetched_at': timezone.now().isoformat()
                }
            }
            
            # Group indicators by objective
            from configurations.models import Objective
            objectives = Objective.objects.filter(is_active=True).prefetch_related('indicator_weights__indicator')
            
            # Check if we have indicator weights configured
            total_weights = sum(obj.indicator_weights.count() for obj in objectives)
            
            if total_weights == 0:
                # No indicator weights configured - fetch indicators directly and group them evenly
                all_indicators = list(TrackedIndicator.objects.filter(
                    dhis2_uid__in=indicator_uids,
                    is_active=True
                ))
                
                # Distribute indicators evenly across objectives
                indicators_per_objective = len(all_indicators) // max(len(objectives), 1)
                indicator_list = list(all_indicators)
                
                for i, objective in enumerate(objectives):
                    objective_data = {
                        'id': objective.id,
                        'name': objective.name,
                        'code': objective.code,
                        'color': objective.color,
                        'milestone': None,
                        'indicators': []
                    }
                    
                    # Assign indicators to this objective
                    start_idx = i * indicators_per_objective
                    end_idx = start_idx + indicators_per_objective if i < len(objectives) - 1 else len(indicator_list)
                    objective_indicators = indicator_list[start_idx:end_idx]
                    
                    for indicator in objective_indicators:
                        indicator_data = {
                            'id': indicator.id,
                            'name': indicator.name,
                            'dhis2_uid': indicator.dhis2_uid,
                            'description': indicator.description,
                            'indicator_number': indicator.indicator_number or f"{i+1}",
                            'display_order': indicator.display_order,
                            'target_value': float(indicator.target_value) if indicator.target_value else None,
                            'target_display': indicator.target_display,
                            'target_lower_limit': float(indicator.target_lower_limit) if indicator.target_lower_limit else None,
                            'target_upper_limit': float(indicator.target_upper_limit) if indicator.target_upper_limit else None,
                            'target_format': getattr(indicator, 'target_format', 'SINGLE'),
                            'target_type': indicator.target_type,
                            'weight': 1.0,  # Default weight when no indicator weights configured
                            'data_values': {},
                            'score': None
                        }
                        
                        # Fetch data for each period
                        for period_code in periods:
                            try:
                                if indicator.dhis2_uid:
                                    value = self._fetch_single_indicator_data(
                                        indicator, org_unit_ids[0], period_code
                                    )
                                    clean_value = self._clean_numeric_value(value)
                                    # For DHIS2 data, if no value is found, assign 0 to help with scoring
                                    final_value = clean_value if clean_value is not None else 0
                                    indicator_data['data_values'][period_code] = {
                                        'value': final_value,
                                        'dhis2_value': clean_value,  # Keep original for reference
                                        'manual_override': None
                                    }
                                else:
                                    # Manual indicator – initialize empty value, editable on FE
                                    indicator_data['data_values'][period_code] = {
                                        'value': None,
                                        'dhis2_value': None,
                                        'manual_override': None
                                    }
                            except Exception as e:
                                self.logger.warning(f"Failed to process {indicator.name} for period {period_code}: {str(e)}")
                                indicator_data['data_values'][period_code] = {
                                    'value': None,
                                    'dhis2_value': None,
                                    'manual_override': None
                                }
                        
                        # Apply manual entries if available for this indicator
                        if manual_entries and str(indicator.id) in manual_entries:
                            indicator_manual_entries = manual_entries[str(indicator.id)]
                            logger.info(f"Applying manual entries for indicator {indicator.id}: {indicator_manual_entries}")
                            
                            for period_code, manual_value in indicator_manual_entries.items():
                                if period_code in indicator_data['data_values']:
                                    # Apply manual override - this is the key fix
                                    indicator_data['data_values'][period_code]['value'] = manual_value
                                    indicator_data['data_values'][period_code]['manual_override'] = manual_value
                                    logger.info(f"Applied manual value {manual_value} for indicator {indicator.id} period {period_code}")
                        
                        # Compute percent_change and target_gap for latest vs previous period
                        try:
                            if isinstance(periods, list) and len(periods) >= 1:
                                last_key = periods[-1]  # This is now a period code
                                prev_key = periods[-2] if len(periods) > 1 else None
                                curr_val = indicator_data['data_values'].get(last_key, {}).get('value')
                                prev_val = indicator_data['data_values'].get(prev_key, {}).get('value') if prev_key else None
                                
                                # Calculate percent change and target gap using the same logic as old_services.py
                                change_pct = None
                                gap_pct = None
                                
                                if prev_val not in (None, 0, 0.0) and curr_val is not None:
                                    try:
                                        # For range indicators, always use standard formula regardless of target_type
                                        if indicator_data.get('target_format') == 'RANGE':
                                            change = ((float(curr_val) - float(prev_val)) / abs(float(prev_val))) * 100.0
                                        else:
                                            # For non-range indicators, use target_type specific formula
                                            if indicator.target_type == 'decrease':
                                                # For decrease indicators: (previous_value - current_value) / abs(current_value) * 100
                                                change = ((float(prev_val) - float(curr_val)) / abs(float(curr_val))) * 100.0
                                            else:
                                                # For increase indicators: (current_value - previous_value) / abs(previous_value) * 100
                                                change = ((float(curr_val) - float(prev_val)) / abs(float(prev_val))) * 100.0
                                        
                                        if change == float('inf') or change == float('-inf'):
                                            change_pct = None
                                        else:
                                            change_pct = round(change, 2)
                                    except Exception:
                                        change_pct = None
                                
                                # Calculate target gap
                                if curr_val is not None and curr_val != 0:
                                    try:
                                        tgt = indicator_data.get('target_value')
                                        target_format = indicator_data.get('target_format', 'SINGLE')
                                        target_upper = indicator_data.get('target_upper_limit')
                                        
                                        if target_format == 'RANGE' and target_upper is not None:
                                            # For range indicators: (Target upper limit - Current Value) / Current Value * 100
                                            gap_calc = ((float(target_upper) - float(curr_val)) / float(curr_val)) * 100.0
                                        else:
                                            # For non-range indicators
                                            if tgt not in (None, 0, 0.0):
                                                if indicator.target_type == 'increase':
                                                    # For increase indicators: (Current Value - Target Value) / Target Value * 100
                                                    gap_calc = ((float(curr_val) - float(tgt)) / float(tgt)) * 100.0
                                                else:
                                                    # For decrease indicators: (Target Value - Current Value) / Current Value * 100
                                                    gap_calc = ((float(tgt) - float(curr_val)) / float(curr_val)) * 100.0
                                            else:
                                                gap_calc = None
                                        
                                        if gap_calc is not None and gap_calc != float('inf') and gap_calc != float('-inf'):
                                            gap_pct = round(gap_calc, 2)
                                        else:
                                            gap_pct = None
                                    except Exception:
                                        gap_pct = None
                                
                                # Derive categories and simple threshold flags for M/N
                                change_cat = self._classify_change_category(change_pct, indicator.target_type)
                                gap_cat = self._classify_gap_category(gap_pct)
                                
                                # For M/N we use meet-threshold as curr >= target for increase, curr <= target for decrease
                                current_meets = None
                                previous_meets = None
                                try:
                                    if curr_val is not None and tgt not in (None,):
                                        if indicator.target_type == 'increase':
                                            current_meets = float(curr_val) >= float(tgt)
                                        else:
                                            current_meets = float(curr_val) <= float(tgt)
                                except Exception:
                                    current_meets = None
                                try:
                                    if prev_val is not None and tgt not in (None,):
                                        if indicator.target_type == 'increase':
                                            previous_meets = float(prev_val) >= float(tgt)
                                        else:
                                            previous_meets = float(prev_val) <= float(tgt)
                                except Exception:
                                    previous_meets = None
                                
                                has_data = curr_val is not None
                                trend_score = self._compute_trend_score(has_data, current_meets, previous_meets, change_cat, gap_cat, indicator)
                                # Derive a simple indicator score from categories/trend if not provided by DB
                                derived_score = trend_score
                                color, label = self._score_color_label(derived_score)
                                
                                indicator_data['score'] = {
                                    'percent_change': change_pct,
                                    'target_gap': gap_pct,
                                    'change_category': change_cat,
                                    'gap_category': gap_cat,
                                    'trend_score': trend_score,
                                    'score': derived_score,
                                    'score_color': color,
                                    'score_label': label,
                                    'current_value': curr_val,
                                    'previous_value': prev_val,
                                    'is_manual_override': False
                                }
                        except Exception as e:
                            self.logger.warning(f"Failed computing change/gap for indicator {indicator.id}: {e}")
                        
                        objective_data['indicators'].append(indicator_data)
                    
                    assessment_data['objectives'].append(objective_data)
            
            # Return as array to match frontend expectations  
            return [{
                'org_unit_id': org_unit_ids[0],
                'org_unit_name': self._get_org_unit_name(org_unit_ids[0]),
                'assessment_period': {
                    'id': 1,
                    'name': f"{periods[0]} to {periods[-1]}" if len(periods) > 1 else periods[0],
                    'start_date': periods[0],
                    'end_date': periods[-1]
                },
                'objectives': assessment_data['objectives']
            }]
            
        except Exception as e:
            self.logger.error(f"Error fetching holistic assessment data: {str(e)}")
            raise
    
    async def _ensure_session(self, request=None) -> None:
        """Ensure we have a valid DHIS2 session."""
        try:
            current_time = timezone.now()
            
            # Check if we need to create a new session
            if (self._session is None or 
                self._session_created is None or
                (current_time - self._session_created).seconds > 3600):  # 1 hour timeout
                
                await self._create_session(request)
                
        except Exception as e:
            self.logger.error(f"Error ensuring session: {str(e)}")
            raise
    
    async def _create_session(self, request=None) -> None:
        """Create a new DHIS2 session using session-based authentication."""
        try:
            # Close existing session if any
            if self._session:
                await self._session.close()
            
            # Get DHIS2 client from session using sync_to_async
            if request and hasattr(request, 'session'):
                session_key = request.session.session_key
                if session_key:
                    # Get session data using sync_to_async
                    session_data = await sync_to_async(get_dhis2_session_data)(session_key)
                    if session_data:
                        instance_url = session_data.get('instance_url')
                        if instance_url:
                            # Create DHIS2 client using session with sync_to_async
                            self._dhis2_client = await sync_to_async(
                                DHIS2ClientFactory.create_client_from_session
                            )(instance_url, session_key)
                            
                            # Create aiohttp session with auth from DHIS2 client
                            self._session = aiohttp.ClientSession()
                            
                            # Set auth headers if available
                            if self._dhis2_client.username and self._dhis2_client.password:
                                import base64
                                auth_string = f"{self._dhis2_client.username}:{self._dhis2_client.password}"
                                auth_bytes = auth_string.encode('ascii')
                                auth_b64 = base64.b64encode(auth_bytes).decode('ascii')
                                
                                self._auth_headers = {
                                    'Authorization': f'Basic {auth_b64}',
                                    'User-Agent': 'HolisticAssessment/1.0',
                                    'Accept': 'application/json',
                                    'Content-Type': 'application/json'
                                }
                            else:
                                # Use cookies if available
                                self._auth_headers = {
                                    'User-Agent': 'HolisticAssessment/1.0',
                                    'Accept': 'application/json',
                                    'Content-Type': 'application/json'
                                }
                                
                                # Add cookies if available in session data
                                if 'dhis2_cookies' in session_data:
                                    cookie_string = '; '.join([
                                        f"{name}={value}" for name, value in session_data['dhis2_cookies'].items()
                                    ])
                                    if cookie_string:
                                        self._auth_headers['Cookie'] = cookie_string
                            
                            # Set session creation time
                            self._session_created = timezone.now()
                            self.logger.info("DHIS2 session created successfully using session-based auth")
                            return
            
            # Fallback: create session without authentication
            self._session = aiohttp.ClientSession()
            self._auth_headers = {
                'User-Agent': 'HolisticAssessment/1.0',
                'Accept': 'application/json',
                'Content-Type': 'application/json'
            }
            self._session_created = timezone.now()
            self.logger.warning("Created DHIS2 session without authentication")
            
        except Exception as e:
            self.logger.error(f"Error creating session: {str(e)}")
            raise
    
    async def _get_tracked_indicators(self) -> List[Dict[str, Any]]:
        """Get list of tracked indicators from database."""
        try:
            # Use sync_to_async to call Django ORM
            indicators_queryset = await sync_to_async(
                TrackedIndicator.objects.filter(is_active=True, dhis2_uid__isnull=False).exclude(dhis2_uid='').values
            )(
                'dhis2_uid', 'name', 'description', 'numerator', 'denominator',
                'target_value', 'indicator_type', 'indicator_number'
            )
            
            # Convert queryset to list using sync_to_async
            indicators = await sync_to_async(list)(indicators_queryset)
            
            # Filter out any indicators with None or empty dhis2_uid (just in case)
            indicators = [ind for ind in indicators if ind.get('dhis2_uid')]
            
            return indicators
            
        except Exception as e:
            self.logger.error(f"Error getting tracked indicators: {str(e)}")
            raise
    
    async def _fetch_assessment_data(self, org_unit_id: str, period: str, 
                                   indicators: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Fetch assessment data for all indicators.
        
        Args:
            org_unit_id: Organization unit ID
            period: Assessment period
            indicators: List of indicators to fetch data for
            
        Returns:
            Complete assessment data
        """
        try:
            # Process period for DHIS2
            dhis2_periods = self.period_service.convert_to_dhis2_period(period)
            if dhis2_periods:
                dhis2_periods = [dhis2_periods]  # Convert to list for consistency
            else:
                dhis2_periods = [period]  # Fallback to original period
            
            # Fetch data for each indicator
            indicator_data = []
            total_score = 0
            total_weight = 0
            
            for indicator in indicators:
                try:
                    data = await self._fetch_indicator_data(
                        indicator, org_unit_id, dhis2_periods
                    )
                    
                    if data:
                        # Calculate score
                        score = self._calculate_indicator_score(data)
                        weighted_score = score * indicator.get('weight', 1)
                        
                        data['score'] = score
                        data['weighted_score'] = weighted_score
                        data['weight'] = indicator.get('weight', 1)
                        data['category'] = indicator.get('category', 'Unknown')
                        
                        total_score += weighted_score
                        total_weight += indicator.get('weight', 1)
                        
                        indicator_data.append(data)
                    
                except Exception as e:
                    self.logger.warning(f"Error fetching data for indicator {indicator['dhis2_uid']}: {str(e)}")
                    # Add indicator with no data
                    indicator_data.append({
                        'uid': indicator['dhis2_uid'],
                        'name': indicator['name'],
                        'current_value': None,
                        'previous_value': None,
                        'target_value': indicator.get('target_value'),
                        'score': 0,
                        'weighted_score': 0,
                        'weight': indicator.get('weight', 1),
                        'category': indicator.get('category', 'Unknown'),
                        'percentage_change': 0,
                        'target_gap': 0
                    })
            
            # Calculate overall score
            overall_score = (total_score / total_weight * 100) if total_weight > 0 else 0
            
            return {
                'org_unit_id': org_unit_id,
                'org_unit_name': await self._get_org_unit_name(org_unit_id),
                'period': period,
                'indicators': indicator_data,
                'total_score': round(overall_score, 2),
                'total_indicators': len(indicators),
                'completed_indicators': len([i for i in indicator_data if i.get('current_value') is not None]),
                'generated_at': timezone.now().isoformat(),
                'data_source': 'DHIS2 Real-time'
            }
            
        except Exception as e:
            self.logger.error(f"Error fetching assessment data: {str(e)}")
            raise
    
    async def _fetch_indicator_data(self, indicator: Dict[str, Any], 
                                  org_unit_id: str, periods: List[str]) -> Optional[Dict[str, Any]]:
        """
        Fetch data for a single indicator.
        
        Args:
            indicator: Indicator configuration
            org_unit_id: Organization unit ID
            periods: List of DHIS2 periods
            
        Returns:
            Indicator data with current and previous values
        """
        try:
            current_value = None
            previous_value = None
            
            # Try to fetch current period data
            if len(periods) > 0:
                current_value = await self._fetch_indicator_value(
                    indicator['dhis2_uid'], org_unit_id, periods[0]
                )
            
            # Try to fetch previous period data
            if len(periods) > 1:
                previous_value = await self._fetch_indicator_value(
                    indicator['dhis2_uid'], org_unit_id, periods[1]
                )
            
            if current_value is None and previous_value is None:
                return None
            
            # Calculate derived values
            percentage_change = self.data_processor.calculate_percentage_change(
                current_value, previous_value
            )
            
            target_gap = self.data_processor.calculate_target_gap(
                current_value, indicator.get('target_value')
            )
            
            return {
                'uid': indicator['dhis2_uid'],
                'name': indicator['name'],
                'current_value': current_value,
                'previous_value': previous_value,
                'target_value': indicator.get('target_value'),
                'percentage_change': percentage_change,
                'target_gap': target_gap
            }
            
        except Exception as e:
            self.logger.error(f"Error fetching indicator data: {str(e)}")
            return None
    
    async def _fetch_indicator_value(self, indicator_uid: str, org_unit_id: str, 
                                    period: str) -> Optional[float]:
        """
        Fetch a single indicator value from DHIS2.
        
        Args:
            indicator_uid: Indicator UID
            org_unit_id: Organization unit ID
            period: DHIS2 period
            
        Returns:
            Indicator value or None if not found
        """
        try:
            # Check if indicator_uid is valid
            if not indicator_uid or indicator_uid == 'None':
                self.logger.warning(f"Invalid indicator UID: {indicator_uid}")
                return None
            
            # Try analytics endpoint first
            value = await self._fetch_from_analytics(indicator_uid, org_unit_id, period)
            if value is not None:
                return value
            
            # Try dataset endpoint as fallback
            value = await self._fetch_from_dataset(indicator_uid, org_unit_id, period)
            return value
            
        except Exception as e:
            self.logger.error(f"Error fetching indicator value: {str(e)}")
            return None
    
    async def _fetch_from_analytics(self, indicator_uid: str, org_unit_id: str, 
                                   period: str) -> Optional[float]:
        """Fetch indicator value from DHIS2 analytics endpoint."""
        try:
            # Get instance URL from DHIS2 client
            instance_url = self._dhis2_client.instance_url if self._dhis2_client else getattr(settings, 'DHIS2_URL', '')
            if not instance_url:
                self.logger.error("No DHIS2 instance URL available")
                return None
                
            # Use the same approach as the working old_services.py
            # Make DHIS2 API request based on indicator type
            # Note: DHIS2 client methods are synchronous, so we need to use sync_to_async
            
            self.logger.info(f"Making analytics request for UID: {indicator_uid}")
            
            # Try as indicator first (most common)
            try:
                response = await sync_to_async(self._dhis2_client.get_analytics_data)(
                    indicators=[indicator_uid],
                    periods=[period],
                    org_units=[org_unit_id]
                )
                if response:
                    self.logger.debug(f"Analytics response for {indicator_uid}: {response}")
                    return self.data_processor.extract_value_from_analytics_response(response, indicator_uid)
            except Exception as e:
                self.logger.debug(f"Failed as indicator, trying as data element: {str(e)}")
            
            # Try as data element
            try:
                response = await sync_to_async(self._dhis2_client.get_analytics_data)(
                    data_elements=[indicator_uid],
                    periods=[period],
                    org_units=[org_unit_id]
                )
                if response:
                    self.logger.debug(f"Analytics response for {indicator_uid}: {response}")
                    return self.data_processor.extract_value_from_analytics_response(response, indicator_uid)
            except Exception as e:
                self.logger.debug(f"Failed as data element: {str(e)}")
            
            # Try as program indicator
            try:
                response = await sync_to_async(self._dhis2_client.get_analytics_data)(
                    program_indicators=[indicator_uid],
                    periods=[period],
                    org_units=[org_unit_id]
                )
                if response:
                    self.logger.debug(f"Analytics response for {indicator_uid}: {response}")
                    return self.data_processor.extract_value_from_analytics_response(response, indicator_uid)
            except Exception as e:
                self.logger.debug(f"Failed as program indicator: {str(e)}")
            
            if response:
                self.logger.debug(f"Analytics response for {indicator_uid}: {response}")
                return self.data_processor.extract_value_from_analytics_response(response, indicator_uid)
            else:
                self.logger.warning(f"Empty analytics response for {indicator_uid}")
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error fetching from analytics: {str(e)}")
            return None
    
    async def _fetch_from_dataset(self, indicator_uid: str, org_unit_id: str, 
                                period: str) -> Optional[float]:
        """Fetch indicator value from DHIS2 dataset endpoint."""
        try:
            # Get instance URL from DHIS2 client
            instance_url = self._dhis2_client.instance_url if self._dhis2_client else getattr(settings, 'DHIS2_URL', '')
            if not instance_url:
                self.logger.error("No DHIS2 instance URL available")
                return None
                
            # Use the same approach as the working old_services.py
            # For dataset requests, use the data set report method
            self.logger.info(f"Making dataset request for UID: {indicator_uid}")
            
            response = await sync_to_async(self._dhis2_client.get_data_set_report)(
                data_set_id=indicator_uid,
                periods=[period],
                org_units=[org_unit_id]
            )
            
            if response:
                self.logger.debug(f"Dataset response for {indicator_uid}: {response}")
                return self.data_processor.extract_value_from_dataset_response(response, indicator_uid)
            else:
                self.logger.warning(f"Empty dataset response for {indicator_uid}")
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error fetching from dataset: {str(e)}")
            return None
    
    def _calculate_indicator_score(self, data: Dict[str, Any]) -> float:
        """
        Calculate score for an indicator based on its data.
        
        Args:
            data: Indicator data with current, previous, and target values
            
        Returns:
            Score between 0 and 1
        """
        try:
            current_value = data.get('current_value')
            target_value = data.get('target_value')
            percentage_change = data.get('percentage_change', 0)
            
            if current_value is None:
                return 0.0
            
            # Base score from target achievement
            if target_value and target_value > 0:
                target_achievement = min(current_value / target_value, 1.0)
            else:
                target_achievement = 0.5  # Default if no target
            
            # Adjust score based on percentage change
            change_bonus = 0
            if percentage_change > 0:
                change_bonus = min(percentage_change / 100, 0.2)  # Max 20% bonus
            elif percentage_change < 0:
                change_bonus = max(percentage_change / 100, -0.2)  # Max 20% penalty
            
            # Calculate final score
            final_score = target_achievement + change_bonus
            return max(0.0, min(1.0, final_score))  # Clamp between 0 and 1
            
        except Exception as e:
            self.logger.error(f"Error calculating indicator score: {str(e)}")
            return 0.0
    
    async def _get_org_unit_name(self, org_unit_id: str) -> str:
        """Get organization unit name from DHIS2."""
        try:
            # Get instance URL from DHIS2 client
            instance_url = self._dhis2_client.instance_url if self._dhis2_client else getattr(settings, 'DHIS2_URL', '')
            if not instance_url:
                self.logger.error("No DHIS2 instance URL available")
                return org_unit_id
                
            url = f"{instance_url}/api/organisationUnits/{org_unit_id}"
            response = await self._session.get(url, headers=self._auth_headers)
            
            if response.status == 200:
                data = await response.json()
                return data.get('displayName', org_unit_id)
            
            return org_unit_id
            
        except Exception as e:
            self.logger.error(f"Error getting org unit name: {str(e)}")
            return org_unit_id
    
    async def get_indicator_metadata(self, indicator_uid: str) -> Optional[Dict[str, Any]]:
        """
        Get metadata for a specific indicator.
        
        Args:
            indicator_uid: Indicator UID
            
        Returns:
            Indicator metadata or None if not found
        """
        try:
            await self._ensure_session()
            
            url = f"{self.dhis2_url}/api/indicators/{indicator_uid}"
            response = await self._session.get(url, headers=self._auth_headers)
            
            if response.status == 200:
                return await response.json()
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error getting indicator metadata: {str(e)}")
            return None
    
    async def search_indicators(self, query: str, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Search for indicators in DHIS2.
        
        Args:
            query: Search query
            limit: Maximum number of results
            
        Returns:
            List of matching indicators
        """
        try:
            await self._ensure_session()
            
            url = f"{self.dhis2_url}/api/indicators"
            params = {
                'query': query,
                'fields': 'id,displayName,description,numerator,denominator',
                'paging': 'false'
            }
            
            response = await self._session.get(url, params=params, headers=self._auth_headers)
            
            if response.status == 200:
                data = await response.json()
                return data.get('indicators', [])[:limit]
            
            return []
            
        except Exception as e:
            self.logger.error(f"Error searching indicators: {str(e)}")
            return []
    
    def _compute_objective_trend_from_indicators(self, indicators: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Compute objective-level trend from indicator data.
        
        Args:
            indicators: List of indicator data dictionaries
            
        Returns:
            Dictionary containing trend metadata
        """
        try:
            if not indicators:
                return {}
            
            # Calculate average scores and trends
            total_score = 0.0
            total_trend = 0.0
            valid_indicators = 0
            
            for indicator in indicators:
                if indicator.get('score') is not None:
                    total_score += indicator['score']
                    valid_indicators += 1
                
                # Extract trend information if available
                trend_info = indicator.get('trend', {})
                if isinstance(trend_info, dict) and trend_info.get('score') is not None:
                    total_trend += trend_info['score']
            
            if valid_indicators == 0:
                return {}
            
            avg_score = total_score / valid_indicators
            avg_trend = total_trend / valid_indicators if total_trend > 0 else 0.0
            
            # Determine trend direction
            if avg_trend > 0.5:
                trend_direction = 'improving'
            elif avg_trend < -0.5:
                trend_direction = 'declining'
            else:
                trend_direction = 'stable'
            
            return {
                'average_score': avg_score,
                'trend_score': avg_trend,
                'trend_direction': trend_direction,
                'indicator_count': valid_indicators
            }
            
        except Exception as e:
            self.logger.error(f"Error computing objective trend: {str(e)}")
            return {}
    
    def fetch_holistic_assessment_data(self, request, assessment_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Fetch holistic assessment data from DHIS2.
        
        Args:
            request: Django request object
            assessment_config: Assessment configuration data
            
        Returns:
            Dictionary containing assessment data
        """
        try:
            # Add debug logging
            self.logger.info(f"Received assessment_config: {assessment_config}")
            
            # Get DHIS2 user from session
            from dhis2_auth.session import get_dhis2_user_from_request
            dhis2_user = get_dhis2_user_from_request(request)
            if not dhis2_user:
                raise ValueError("No DHIS2 user found in session")
            
            # Extract configuration - handle both old and new payload formats
            org_unit_id = None
            period = None
            
            # Handle org_unit_ids array format
            if 'org_unit_ids' in assessment_config and assessment_config['org_unit_ids']:
                org_unit_id = assessment_config['org_unit_ids'][0]  # Take first org unit
                self.logger.info(f"Extracted org_unit_id from org_unit_ids: {org_unit_id}")
            
            # Handle org_unit_id string format (backward compatibility)
            elif 'org_unit_id' in assessment_config:
                org_unit_id = assessment_config['org_unit_id']
                self.logger.info(f"Extracted org_unit_id from org_unit_id: {org_unit_id}")
            
            # Handle periods array format
            if 'periods' in assessment_config and assessment_config['periods']:
                period_obj = assessment_config['periods'][0]  # Take first period
                self.logger.info(f"Processing period object: {period_obj}")
                
                # Check if period_obj is already a string (processed by serializer)
                if isinstance(period_obj, str):
                    period = period_obj
                    self.logger.info(f"Using period string directly: {period}")
                else:
                    # Convert period object to string format
                    if 'start_date' in period_obj and 'end_date' in period_obj:
                        # Convert date range to period string (e.g., "2023Q1")
                        start_date = period_obj['start_date']
                        end_date = period_obj['end_date']
                        # Extract year and quarter from dates
                        from datetime import datetime
                        start_dt = datetime.strptime(start_date, '%Y-%m-%d')
                        end_dt = datetime.strptime(end_date, '%Y-%m-%d')
                        
                        # Determine quarter based on end date
                        if end_dt.month <= 3:
                            quarter = "Q1"
                        elif end_dt.month <= 6:
                            quarter = "Q2"
                        elif end_dt.month <= 9:
                            quarter = "Q3"
                        else:
                            quarter = "Q4"
                        
                        period = f"{start_dt.year}{quarter}"
                        self.logger.info(f"Converted date range to period: {period}")
                    elif 'code' in period_obj:
                        period = period_obj['code']
                        self.logger.info(f"Using period code: {period}")
                    elif 'name' in period_obj:
                        period = period_obj['name']
                        self.logger.info(f"Using period name: {period}")
            
            # Handle period string format (backward compatibility)
            elif 'period' in assessment_config:
                period = assessment_config['period']
                self.logger.info(f"Using direct period: {period}")
            
            # If we still don't have a period, try to construct one from the original request data
            if not period and hasattr(request, 'data'):
                original_data = request.data
                self.logger.info(f"Checking original request data: {original_data}")
                
                if 'periods' in original_data and original_data['periods']:
                    original_period = original_data['periods'][0]
                    self.logger.info(f"Found original period: {original_period}")
                    
                    if isinstance(original_period, dict) and 'start_date' in original_period and 'end_date' in original_period:
                        # Convert date range to period string
                        start_date = original_period['start_date']
                        end_date = original_period['end_date']
                        from datetime import datetime
                        start_dt = datetime.strptime(start_date, '%Y-%m-%d')
                        end_dt = datetime.strptime(end_date, '%Y-%m-%d')
                        
                        # Determine quarter based on end date
                        if end_dt.month <= 3:
                            quarter = "Q1"
                        elif end_dt.month <= 6:
                            quarter = "Q2"
                        elif end_dt.month <= 9:
                            quarter = "Q3"
                        else:
                            quarter = "Q4"
                        
                        period = f"{start_dt.year}{quarter}"
                        self.logger.info(f"Constructed period from original data: {period}")
            
            self.logger.info(f"Final extracted values - org_unit_id: {org_unit_id}, period: {period}")
            
            if not org_unit_id or not period:
                raise ValueError(f"org_unit_id and period are required. Received: org_unit_id={org_unit_id}, period={period}")
            
            # Initialize client if not provided
            if not self.client:
                self.client = DHIS2ClientFactory.create_client_from_session(
                    dhis2_user.dhis2_instance_url,
                    request.session.session_key
                )
            
            # Extract configuration
            org_unit_ids = assessment_config.get('org_unit_ids', [])
            org_unit_names = assessment_config.get('org_unit_names', [])
            periods_raw = assessment_config.get('periods', [])
            indicator_uids = assessment_config.get('indicator_uids', [])
            manual_entries = assessment_config.get('manual_entries', {})
            pre_calculated_scores = assessment_config.get('pre_calculated_scores', {})
            self.logger.info(f"Org unit names received: {org_unit_names}")
            
            # Handle periods - they can be strings or objects with 'code' field
            periods = []
            for period in periods_raw:
                if isinstance(period, dict) and 'code' in period:
                    periods.append(period['code'])
                elif isinstance(period, str):
                    periods.append(period)
                else:
                    # Fallback: try to extract code from period object
                    period_code = getattr(period, 'code', str(period))
                    periods.append(period_code)
            
            # Sort periods chronologically to ensure correct change calculation
            periods.sort()
            
            if not org_unit_ids or not periods:
                raise ValueError("Organization units and periods are required")
            
            # Fetch active indicators if not specified; include manual indicators (no dhis2_uid)
            manual_indicators = []
            if not indicator_uids:
                indicators = TrackedIndicator.objects.filter(is_active=True)
                # Only include non-empty UIDs for DHIS2 fetch; keep track of manual ones
                indicator_uids = [ind.dhis2_uid for ind in indicators if ind.dhis2_uid]
                manual_indicators = [ind for ind in indicators if not ind.dhis2_uid]
            
            # Fetch data for each indicator
            assessment_data = {
                'indicators': [],
                'objectives': [],
                'milestones': [],
                'metadata': {
                    'org_units': org_unit_ids,
                    'periods': periods,
                    'fetched_at': timezone.now().isoformat()
                }
            }
            
            # Group indicators by objective
            from configurations.models import Objective
            objectives = Objective.objects.filter(is_active=True).prefetch_related('indicator_weights__indicator')
            
            # Check if we have indicator weights configured
            total_weights = sum(obj.indicator_weights.count() for obj in objectives)
            
            if total_weights == 0:
                # No indicator weights configured - fetch indicators directly and group them evenly
                all_indicators = list(TrackedIndicator.objects.filter(
                    dhis2_uid__in=indicator_uids,
                    is_active=True
                ))
                
                # Distribute indicators evenly across objectives
                indicators_per_objective = len(all_indicators) // max(len(objectives), 1)
                indicator_list = list(all_indicators)
                
                for i, objective in enumerate(objectives):
                    objective_data = {
                        'id': objective.id,
                        'name': objective.name,
                        'code': objective.code,
                        'color': objective.color,
                        'milestone': None,
                        'indicators': []
                    }
                    
                    # Assign indicators to this objective
                    start_idx = i * indicators_per_objective
                    end_idx = start_idx + indicators_per_objective if i < len(objectives) - 1 else len(indicator_list)
                    objective_indicators = indicator_list[start_idx:end_idx]
                    
                    for indicator in objective_indicators:
                        indicator_data = {
                            'id': indicator.id,
                            'name': indicator.name,
                            'dhis2_uid': indicator.dhis2_uid,
                            'description': indicator.description,
                            'indicator_number': indicator.indicator_number or f"{i+1}",
                            'display_order': indicator.display_order,
                            'target_value': float(indicator.target_value) if indicator.target_value else None,
                            'target_display': indicator.target_display,
                            'target_lower_limit': float(indicator.target_lower_limit) if indicator.target_lower_limit else None,
                            'target_upper_limit': float(indicator.target_upper_limit) if indicator.target_upper_limit else None,
                            'target_format': getattr(indicator, 'target_format', 'SINGLE'),
                            'target_type': indicator.target_type,
                            'weight': 1.0,  # Default weight when no indicator weights configured
                            'data_values': {},
                            'score': None
                        }
                        
                        # Fetch data for each period
                        for period_code in periods:
                            try:
                                if indicator.dhis2_uid:
                                    value = self._fetch_single_indicator_data(
                                        indicator, org_unit_ids[0], period_code
                                    )
                                    clean_value = self._clean_numeric_value(value)
                                    # For DHIS2 data, if no value is found, assign 0 to help with scoring
                                    final_value = clean_value if clean_value is not None else 0
                                    indicator_data['data_values'][period_code] = {
                                        'value': final_value,
                                        'dhis2_value': clean_value,  # Keep original for reference
                                        'manual_override': None
                                    }
                                else:
                                    # Manual indicator – initialize empty value, editable on FE
                                    indicator_data['data_values'][period_code] = {
                                        'value': None,
                                        'dhis2_value': None,
                                        'manual_override': None
                                    }
                            except Exception as e:
                                self.logger.warning(f"Failed to process {indicator.name} for period {period_code}: {str(e)}")
                                indicator_data['data_values'][period_code] = {
                                    'value': None,
                                    'dhis2_value': None,
                                    'manual_override': None
                                }
                        
                        # Apply manual entries if available for this indicator
                        if manual_entries and str(indicator.id) in manual_entries:
                            indicator_manual_entries = manual_entries[str(indicator.id)]
                            logger.info(f"Applying manual entries for indicator {indicator.id}: {indicator_manual_entries}")
                            
                            for period_code, manual_value in indicator_manual_entries.items():
                                if period_code in indicator_data['data_values']:
                                    # Apply manual override - this is the key fix
                                    indicator_data['data_values'][period_code]['value'] = manual_value
                                    indicator_data['data_values'][period_code]['manual_override'] = manual_value
                                    logger.info(f"Applied manual value {manual_value} for indicator {indicator.id} period {period_code}")
                        
                        # Compute percent_change and target_gap for latest vs previous period
                        try:
                            if isinstance(periods, list) and len(periods) >= 1:
                                last_key = periods[-1]  # This is now a period code
                                prev_key = periods[-2] if len(periods) > 1 else None
                                curr_val = indicator_data['data_values'].get(last_key, {}).get('value')
                                prev_val = indicator_data['data_values'].get(prev_key, {}).get('value') if prev_key else None
                                
                                # Calculate percent change and target gap using the same logic as old_services.py
                                change_pct = None
                                gap_pct = None
                                
                                if prev_val not in (None, 0, 0.0) and curr_val is not None:
                                    try:
                                        # For range indicators, always use standard formula regardless of target_type
                                        if indicator_data.get('target_format') == 'RANGE':
                                            change = ((float(curr_val) - float(prev_val)) / abs(float(prev_val))) * 100.0
                                        else:
                                            # For non-range indicators, use target_type specific formula
                                            if indicator.target_type == 'decrease':
                                                # For decrease indicators: (previous_value - current_value) / abs(current_value) * 100
                                                change = ((float(prev_val) - float(curr_val)) / abs(float(curr_val))) * 100.0
                                            else:
                                                # For increase indicators: (current_value - previous_value) / abs(previous_value) * 100
                                                change = ((float(curr_val) - float(prev_val)) / abs(float(prev_val))) * 100.0
                                        
                                        if change == float('inf') or change == float('-inf'):
                                            change_pct = None
                                        else:
                                            change_pct = round(change, 2)
                                    except Exception:
                                        change_pct = None
                                
                                # Calculate target gap
                                if curr_val is not None and curr_val != 0:
                                    try:
                                        tgt = indicator_data.get('target_value')
                                        target_format = indicator_data.get('target_format', 'SINGLE')
                                        target_upper = indicator_data.get('target_upper_limit')
                                        
                                        if target_format == 'RANGE' and target_upper is not None:
                                            # For range indicators: (Target upper limit - Current Value) / Current Value * 100
                                            gap_calc = ((float(target_upper) - float(curr_val)) / float(curr_val)) * 100.0
                                        else:
                                            # For non-range indicators
                                            if tgt not in (None, 0, 0.0):
                                                if indicator.target_type == 'increase':
                                                    # For increase indicators: (Current Value - Target Value) / Target Value * 100
                                                    gap_calc = ((float(curr_val) - float(tgt)) / float(tgt)) * 100.0
                                                else:
                                                    # For decrease indicators: (Target Value - Current Value) / Current Value * 100
                                                    gap_calc = ((float(tgt) - float(curr_val)) / float(curr_val)) * 100.0
                                            else:
                                                gap_calc = None
                                        
                                        if gap_calc is not None and gap_calc != float('inf') and gap_calc != float('-inf'):
                                            gap_pct = round(gap_calc, 2)
                                        else:
                                            gap_pct = None
                                    except Exception:
                                        gap_pct = None
                                
                                # Derive categories and simple threshold flags for M/N
                                change_cat = self._classify_change_category(change_pct, indicator.target_type)
                                gap_cat = self._classify_gap_category(gap_pct)
                                
                                # For M/N we use meet-threshold as curr >= target for increase, curr <= target for decrease
                                current_meets = None
                                previous_meets = None
                                try:
                                    if curr_val is not None and tgt not in (None,):
                                        if indicator.target_type == 'increase':
                                            current_meets = float(curr_val) >= float(tgt)
                                        else:
                                            current_meets = float(curr_val) <= float(tgt)
                                except Exception:
                                    current_meets = None
                                try:
                                    if prev_val is not None and tgt not in (None,):
                                        if indicator.target_type == 'increase':
                                            previous_meets = float(prev_val) >= float(tgt)
                                        else:
                                            previous_meets = float(prev_val) <= float(tgt)
                                except Exception:
                                    previous_meets = None
                                
                                has_data = curr_val is not None
                                trend_score = self._compute_trend_score(has_data, current_meets, previous_meets, change_cat, gap_cat, indicator)
                                # Derive a simple indicator score from categories/trend if not provided by DB
                                derived_score = trend_score
                                color, label = self._score_color_label(derived_score)
                                
                                indicator_data['score'] = {
                                    'percent_change': change_pct,
                                    'target_gap': gap_pct,
                                    'change_category': change_cat,
                                    'gap_category': gap_cat,
                                    'trend_score': trend_score,
                                    'score': derived_score,
                                    'score_color': color,
                                    'score_label': label,
                                    'current_value': curr_val,
                                    'previous_value': prev_val,
                                    'is_manual_override': False
                                }
                        except Exception as e:
                            self.logger.warning(f"Failed computing change/gap for indicator {indicator.id}: {e}")
                        
                        objective_data['indicators'].append(indicator_data)
                    
                    assessment_data['objectives'].append(objective_data)
            
            else:
                # Use configured indicator weights
                self.logger.info("Using configured indicator weights")
                for objective in objectives:
                    objective_data = {
                        'id': objective.id,
                        'name': objective.name,
                        'code': objective.code,
                        'color': objective.color,
                        'milestone': None,
                        'indicators': []
                    }
                    
                    # Add milestone information if it exists
                    if objective.milestone:
                        objective_data['milestone'] = {
                            'id': objective.milestone.id,
                            'name': objective.milestone.name,
                            'code': objective.milestone.code,
                            'color': objective.milestone.color,
                            'score': -2,  # Default score for real-time data
                            'score_color': '#dc3545',
                            'score_label': 'Severely Underperforming'
                        }
                    
                    # Get indicators for this objective through indicator_weights relationship
                    objective_indicators = []
                    indicator_weights_map = {}
                    for indicator_weight in objective.indicator_weights.all():
                        indicator = indicator_weight.indicator
                        # Include DHIS2-backed indicators present in list and manual indicators (no UID)
                        if (indicator.dhis2_uid in indicator_uids or not indicator.dhis2_uid) and indicator.is_active:
                            objective_indicators.append(indicator)
                            indicator_weights_map[indicator.id] = indicator_weight.weight
                    
                    self.logger.info(f"Objective {objective.name} has {len(objective_indicators)} indicators")
                    
                    for indicator in objective_indicators:
                        indicator_data = {
                            'id': indicator.id,
                            'name': indicator.name,
                            'dhis2_uid': indicator.dhis2_uid,
                            'description': indicator.description,
                            'indicator_number': indicator.indicator_number or f"{objective.order}.{len(objective_data['indicators'])+1}",
                            'display_order': indicator.display_order,
                            'target_value': float(indicator.target_value) if indicator.target_value else None,
                            'target_display': indicator.target_display,
                            'target_lower_limit': float(indicator.target_lower_limit) if indicator.target_lower_limit else None,
                            'target_upper_limit': float(indicator.target_upper_limit) if indicator.target_upper_limit else None,
                            'target_format': getattr(indicator, 'target_format', 'SINGLE'),
                            'target_type': indicator.target_type,
                            'weight': float(indicator_weights_map.get(indicator.id, 1.0)),
                            'data_values': {},
                            'score': None
                        }
                        
                        # Fetch data for each period
                        for period in periods:
                            try:
                                if indicator.dhis2_uid:
                                    value = self._fetch_single_indicator_data(
                                        indicator, org_unit_ids[0], period
                                    )
                                    clean_value = self._clean_numeric_value(value)
                                    # For DHIS2 data, if no value is found, assign 0 to help with scoring
                                    final_value = clean_value if clean_value is not None else 0
                                    indicator_data['data_values'][period] = {
                                        'value': final_value,
                                        'dhis2_value': clean_value,  # Keep original for reference
                                        'manual_override': None
                                    }
                                else:
                                    indicator_data['data_values'][period] = {
                                        'value': None,
                                        'dhis2_value': None,
                                        'manual_override': None
                                    }
                            except Exception as e:
                                self.logger.warning(f"Failed to process {indicator.name} for period {period}: {str(e)}")
                                indicator_data['data_values'][period] = {
                                    'value': None,
                                    'dhis2_value': None,
                                    'manual_override': None
                                }
                        
                        # Apply manual entries if available for this indicator
                        if manual_entries and str(indicator.id) in manual_entries:
                            indicator_manual_entries = manual_entries[str(indicator.id)]
                            logger.info(f"Applying manual entries for indicator {indicator.id}: {indicator_manual_entries}")
                            
                            for period_code, manual_value in indicator_manual_entries.items():
                                if period_code in indicator_data['data_values']:
                                    # Apply manual override - this is the key fix
                                    indicator_data['data_values'][period_code]['value'] = manual_value
                                    indicator_data['data_values'][period_code]['manual_override'] = manual_value
                                    logger.info(f"Applied manual value {manual_value} for indicator {indicator.id} period {period_code}")
                        
                        # Compute percent_change and target_gap for latest vs previous period
                        try:
                            if isinstance(periods, list) and len(periods) >= 1:
                                last_key = periods[-1]
                                prev_key = periods[-2] if len(periods) > 1 else None
                                curr_val = indicator_data['data_values'].get(last_key, {}).get('value')
                                prev_val = indicator_data['data_values'].get(prev_key, {}).get('value') if prev_key else None
                                
                                # Calculate percent change and target gap using the same logic as old_services.py
                                change_pct = None
                                gap_pct = None
                                
                                if prev_val not in (None, 0, 0.0) and curr_val is not None:
                                    try:
                                        # For range indicators, always use standard formula regardless of target_type
                                        if indicator_data.get('target_format') == 'RANGE':
                                            change = ((float(curr_val) - float(prev_val)) / abs(float(prev_val))) * 100.0
                                        else:
                                            # For non-range indicators, use target_type specific formula
                                            if indicator.target_type == 'decrease':
                                                # For decrease indicators: (previous_value - current_value) / abs(current_value) * 100
                                                change = ((float(prev_val) - float(curr_val)) / abs(float(curr_val))) * 100.0
                                            else:
                                                # For increase indicators: (current_value - previous_value) / abs(previous_value) * 100
                                                change = ((float(curr_val) - float(prev_val)) / abs(float(prev_val))) * 100.0
                                        
                                        if change == float('inf') or change == float('-inf'):
                                            change_pct = None
                                        else:
                                            change_pct = round(change, 2)
                                    except Exception:
                                        change_pct = None
                                
                                # Calculate target gap
                                if curr_val is not None and curr_val != 0:
                                    try:
                                        tgt = indicator_data.get('target_value')
                                        target_format = indicator_data.get('target_format', 'SINGLE')
                                        target_upper = indicator_data.get('target_upper_limit')
                                        
                                        if target_format == 'RANGE' and target_upper is not None:
                                            # For range indicators: (Target upper limit - Current Value) / Current Value * 100
                                            gap_calc = ((float(target_upper) - float(curr_val)) / float(curr_val)) * 100.0
                                        else:
                                            # For non-range indicators
                                            if tgt not in (None, 0, 0.0):
                                                if indicator.target_type == 'increase':
                                                    # For increase indicators: (Current Value - Target Value) / Target Value * 100
                                                    gap_calc = ((float(curr_val) - float(tgt)) / float(tgt)) * 100.0
                                                else:
                                                    # For decrease indicators: (Target Value - Current Value) / Current Value * 100
                                                    gap_calc = ((float(tgt) - float(curr_val)) / float(curr_val)) * 100.0
                                            else:
                                                gap_calc = None
                                        
                                        if gap_calc is not None and gap_calc != float('inf') and gap_calc != float('-inf'):
                                            gap_pct = round(gap_calc, 2)
                                        else:
                                            gap_pct = None
                                    except Exception:
                                        gap_pct = None
                                
                                # Derive categories and simple threshold flags for M/N
                                change_cat = self._classify_change_category(change_pct, indicator.target_type)
                                gap_cat = self._classify_gap_category(gap_pct)
                                
                                # For M/N we use meet-threshold as curr >= target for increase, curr <= target for decrease
                                current_meets = None
                                previous_meets = None
                                try:
                                    if curr_val is not None and tgt not in (None,):
                                        if indicator.target_type == 'increase':
                                            current_meets = float(curr_val) >= float(tgt)
                                        else:
                                            current_meets = float(curr_val) <= float(tgt)
                                except Exception:
                                    current_meets = None
                                try:
                                    if prev_val is not None and tgt not in (None,):
                                        if indicator.target_type == 'increase':
                                            previous_meets = float(prev_val) >= float(tgt)
                                        else:
                                            previous_meets = float(prev_val) <= float(tgt)
                                except Exception:
                                    previous_meets = None
                                
                                has_data = curr_val is not None
                                trend_score = self._compute_trend_score(has_data, current_meets, previous_meets, change_cat, gap_cat, indicator)
                                # Derive a simple indicator score from categories/trend if not provided by DB
                                derived_score = trend_score
                                color, label = self._score_color_label(derived_score)
                                
                                indicator_data['score'] = {
                                    'percent_change': change_pct,
                                    'target_gap': gap_pct,
                                    'change_category': change_cat,
                                    'gap_category': gap_cat,
                                    'trend_score': trend_score,
                                    'score': derived_score,
                                    'score_color': color,
                                    'score_label': label,
                                    'current_value': curr_val,
                                    'previous_value': prev_val,
                                    'is_manual_override': False
                                }
                        except Exception as e:
                            self.logger.warning(f"Failed computing change/gap for indicator {indicator.id}: {e}")
                        
                        objective_data['indicators'].append(indicator_data)
                    
                    assessment_data['objectives'].append(objective_data)
            
            # Return as array to match frontend expectations  
            # Use provided org unit names if available, otherwise fetch from DHIS2
            org_unit_name = None
            if org_unit_names and len(org_unit_names) > 0:
                org_unit_name = org_unit_names[0]
                self.logger.info(f"Using provided org unit name: {org_unit_name}")
            else:
                org_unit_name = self._get_org_unit_name(org_unit_ids[0])
                self.logger.info(f"Fetched org unit name from DHIS2: {org_unit_name}")
            
            return [{
                'org_unit_id': org_unit_ids[0],
                'org_unit_name': org_unit_name,
                'assessment_period': {
                    'id': 1,
                    'name': f"{periods[0]} to {periods[-1]}" if len(periods) > 1 else periods[0],
                    'start_date': periods[0],
                    'end_date': periods[-1]
                },
                'objectives': assessment_data['objectives']
            }]
                
        except Exception as e:
            self.logger.error(f"Error fetching holistic assessment data: {str(e)}")
            raise
    
    def generate_holistic_excel(self, assessment_payload: list, manual_entries: dict = None, pre_calculated_scores: dict = None) -> str:
        """
        Generate Excel file from assessment data.
        
        Args:
            assessment_payload: Assessment data list (format from fetch_holistic_assessment_data)
            manual_entries: Dict of manual entries by indicator ID and period
            pre_calculated_scores: Dict of pre-calculated scores by indicator ID
            
        Returns:
            Path to the generated Excel file
        """
        try:
            from openpyxl import Workbook
            from openpyxl.styles import PatternFill, Font, Alignment, Border, Side
            from openpyxl.utils import get_column_letter
            from openpyxl.formatting.rule import FormulaRule
            import os
            from django.conf import settings
        except Exception as e:
            self.logger.error(f"openpyxl not available: {e}")
            raise

        try:
            # Apply manual entries to the assessment data before generating Excel
            if manual_entries:
                self.logger.info(f"Applying manual entries to Excel export: {manual_entries}")
                for indicator_id, period_entries in manual_entries.items():
                    # Find the indicator in the assessment data
                    for period_data in assessment_payload:
                        for objective in period_data.get('objectives', []):
                            for indicator in objective.get('indicators', []):
                                if str(indicator.get('id')) == str(indicator_id):
                                    # Apply manual entries for each period
                                    for period_code, manual_value in period_entries.items():
                                        if period_code in indicator.get('data_values', {}):
                                            # Update the data_values to include manual override
                                            indicator['data_values'][period_code]['manual_override'] = manual_value
                                            # Also update the main value to ensure it's used in Excel
                                            indicator['data_values'][period_code]['value'] = manual_value
                                            self.logger.info(f"Applied manual entry {manual_value} for indicator {indicator_id} period {period_code}")
                                    break

            wb = Workbook()
            ws = wb.active
            ws.title = 'Table'

            # Styling helpers
            header_fill = PatternFill('solid', fgColor='265380')  # #265380
            header_font = Font(color='FFFFFF', bold=True)
            center = Alignment(horizontal='center', vertical='center')
            left = Alignment(horizontal='left', vertical='center')
            thin = Side(border_style='thin', color='CCCCCC')
            border = Border(left=thin, right=thin, top=thin, bottom=thin)

            orange_fill = PatternFill('solid', fgColor='FDBA74')  # approx #fd7e14 light
            yellow_fill = PatternFill('solid', fgColor='FFF3BF')  # light yellow
            green50 = PatternFill('solid', fgColor='E8F5E9')  # Light green for positive change
            yellow50 = PatternFill('solid', fgColor='FFFDE7')  # Light yellow for neutral change
            red50 = PatternFill('solid', fgColor='FFEBEE')   # Light red for negative change/gap

            def score_fill(score: float | None):
                if score is None:
                    return None
                # New color scheme: 2 (Dark Green), 1 (Light Green), 0 (Yellow), -1 (Light Red), -2 (Red)
                if score >= 2:
                    return PatternFill('solid', fgColor='548235')  # Dark Green for 2
                if score >= 1:
                    return PatternFill('solid', fgColor='A9D08E')  # Light Green for 1
                if score == 0:
                    return PatternFill('solid', fgColor='FFFF00')  # Yellow for 0
                if score == -1:
                    return PatternFill('solid', fgColor='FFC7CE')  # Light Red for -1
                return PatternFill('solid', fgColor='FF0000')  # Red for -2

            data = assessment_payload[0] if assessment_payload else None
            if not data:
                raise ValueError('Empty assessment data')

            periods = []
            # Derive periods by inspecting first objective/indicator
            if data.get('objectives'):
                for obj in data['objectives']:
                    if obj.get('indicators'):
                        first = obj['indicators'][0]
                        periods = list(first.get('data_values', {}).keys())
                        break

            # Header row
            headers = ['#', 'Indicator'] + periods + ['Change', 'P-T Gap Analysis', 'Target', 'Assessed score (-2, -1, 0, +1, +2)', 'Remarks']
            ws.append(headers)
            for idx, _ in enumerate(headers, start=1):
                cell = ws.cell(row=1, column=idx)
                cell.fill = header_fill
                cell.font = header_font
                cell.alignment = center
                cell.border = border
            ws.row_dimensions[1].height = 22

            row = 2
            # Sort objectives by order to match frontend
            sorted_objectives = sorted(data.get('objectives', []), key=lambda x: x.get('order', 0))
            for obj in sorted_objectives:
                # Objective row
                ws.append([None] * len(headers))
                for c in range(1, len(headers) + 1):
                    cell = ws.cell(row=row, column=c)
                    cell.fill = orange_fill
                    cell.border = border
                ws.cell(row=row, column=1, value=None)
                ws.cell(row=row, column=2, value=obj.get('name')).alignment = left
                row += 1

                # Indicator rows - sort by display_order to match frontend
                sorted_indicators = sorted(obj.get('indicators', []), key=lambda x: x.get('display_order', 0))
                for ind in sorted_indicators:
                    row_values = []
                    row_values.append(ind.get('indicator_number'))
                    row_values.append(ind.get('name'))
                    # periods
                    for p in periods:
                        data_value = ind.get('data_values', {}).get(p, {})
                        # Prioritize manual override over DHIS2 value
                        v = data_value.get('manual_override') if data_value.get('manual_override') is not None else data_value.get('value')
                        row_values.append(v)
                    # change/gap - format with % symbol
                    sc = ind.get('score') or {}
                    percent_change = sc.get('percent_change')
                    target_gap = sc.get('target_gap')
                    
                    # Format percentage values with proper handling of None and zero values
                    if percent_change is not None and percent_change != 0:
                        change_str = f"{percent_change:.1f}%" if percent_change != 0 else ""
                    else:
                        change_str = ""
                    
                    if target_gap is not None and target_gap != 0:
                        gap_str = f"{target_gap:.1f}%" if target_gap != 0 else ""
                    else:
                        gap_str = ""
                    
                    row_values.append(change_str)
                    row_values.append(gap_str)
                    row_values.append(ind.get('target_display', ''))
                    
                    # Score with color
                    score_value = sc.get('score')
                    row_values.append(score_value)
                    
                    # Remarks
                    row_values.append(sc.get('remarks', ''))
                    
                    ws.append(row_values)
                    
                    # Apply styling
                    for c in range(1, len(row_values) + 1):
                        cell = ws.cell(row=row, column=c)
                        cell.border = border
                        

                        
                        # Apply score color to score column (second to last column)
                        if c == len(row_values) - 1 and score_value is not None:  # Score column
                            fill = score_fill(score_value)
                            if fill:
                                cell.fill = fill
                        
                        # Apply change colors (Change column - after periods)
                        change_col = 2 + len(periods) + 1  # After indicator name and periods
                        if c == change_col and percent_change is not None and percent_change != 0:
                            if percent_change > 5:
                                cell.fill = green50
                            elif percent_change < -5:
                                cell.fill = red50
                            else:
                                cell.fill = yellow50
                        
                        # Apply gap colors (Gap column - after change column)
                        gap_col = change_col + 1
                        if c == gap_col and target_gap is not None and target_gap != 0:
                            if target_gap > 40:
                                cell.fill = green50
                            elif target_gap <= 10:
                                cell.fill = red50
                            else:
                                cell.fill = yellow50
                    
                    row += 1

                # Add milestone row if objective has a milestone
                if obj.get('milestone'):
                    milestone = obj['milestone']
                    milestone_row = []
                    milestone_row.append('MS')  # Milestone indicator
                    milestone_row.append(milestone.get('name', 'Milestone'))
                    
                    # Add empty values for periods
                    for _ in periods:
                        milestone_row.append('-')
                    
                    # Add empty values for change and gap
                    milestone_row.append('-')
                    milestone_row.append('-')
                    milestone_row.append('-')  # Target
                    
                    # Add milestone score
                    milestone_score = milestone.get('score', 0)
                    milestone_row.append(milestone_score)
                    
                    # Add empty remarks
                    milestone_row.append('')
                    
                    ws.append(milestone_row)
                    
                    # Apply milestone styling (yellow background)
                    for c in range(1, len(milestone_row) + 1):
                        cell = ws.cell(row=row, column=c)
                        cell.fill = yellow_fill
                        cell.border = border
                        if c == 1:  # MS column
                            cell.alignment = center
                        elif c == 2:  # Milestone name
                            cell.alignment = left
                        else:
                            cell.alignment = center
                    
                    # Apply score color to milestone score
                    score_col = 2 + len(periods) + 4  # Score column position
                    if milestone_score is not None:
                        fill = score_fill(milestone_score)
                        if fill:
                            ws.cell(row=row, column=score_col).fill = fill
                            ws.cell(row=row, column=score_col).font = Font(color='FFFFFF', bold=True)
                    
                    row += 1

            # Auto-adjust column widths
            for column in ws.columns:
                max_length = 0
                column_letter = get_column_letter(column[0].column)
                for cell in column:
                    try:
                        if len(str(cell.value)) > max_length:
                            max_length = len(str(cell.value))
                    except:
                        pass
                adjusted_width = min(max_length + 2, 50)
                ws.column_dimensions[column_letter].width = adjusted_width

            # Save file
            import tempfile
            import uuid
            from datetime import datetime
            
            temp_dir = getattr(settings, 'EXCEL_EXPORT_DIR', '/tmp')
            os.makedirs(temp_dir, exist_ok=True)
            
            # Generate filename with org unit name and date
            org_unit_name = data.get('org_unit_name', 'Unknown')
            # Handle None case and clean org unit name for filename (remove special characters)
            if org_unit_name is None:
                org_unit_name = 'Unknown'
            clean_org_name = org_unit_name.replace(' ', '_').replace('/', '_').replace('\\', '_').replace(':', '_')
            current_date = datetime.now().strftime('%d-%m-%Y')
            filename = f"{clean_org_name}_{current_date}.xlsx"
            file_path = os.path.join(temp_dir, filename)
            wb.save(file_path)
            
            return file_path
            
        except Exception as e:
            self.logger.error(f"Error generating holistic Excel: {str(e)}")
            raise
    
    def close(self) -> None:
        """Close the service and clean up resources."""
        try:
            # No session to close in synchronous version
            pass
        except Exception as e:
            self.logger.error(f"Error closing service: {str(e)}")
    
    def _classify_change_category(self, change_pct: float | None, target_type: str = 'increase') -> str | None:
        """Map relative percent change to O category per scoring context."""
        if change_pct is None:
            return None
        
        # Now that we use the correct formulas, we don't need to invert
        # The change_pct passed here is already the correct performance change
        performance_change = change_pct
        
        # Categorize based on performance change - EXACTLY matches flowchart
        if performance_change > 5:
            return '>5%'
        if -5 < performance_change <= 5:
            return '-5%<C<=5%'  # Stagnation category
        if -10 < performance_change <= -5:
            return '-10%<C<=-5%'
        return '<=-10%'

    def _classify_gap_category(self, gap_pct: float | None) -> str | None:
        """Map gap to P category per Excel formula: =IF($I4<=10%,"<=10%",IF(AND($I4>10%,$I4<=40%),"10%<PT<=40%",IF($I4>40%,">40%","")))"""
        if gap_pct is None:
            return None
        # Use signed gap for categorization, matching Excel behavior
        if gap_pct <= 10:
            return '<=10%'
        if 10 < gap_pct <= 40:
            return '10%<PT<=40%'
        if gap_pct > 40:
            return '>40%'
        return None

    def _compute_trend_score(self, has_data: bool, current_meets: bool | None, previous_meets: bool | None,
                              change_cat: str | None, gap_cat: str | None, indicator=None) -> int:
        """Use the updated HolisticScoringService algorithm for real-time scoring."""
        # Step 1: Data provided check
        if not has_data:
            return -2
        
        # Step 2: First year check (simplified - assume not first year if we have previous data)
        is_first_year = previous_meets is None
        
        # Step 3: Target achieved check
        target_achieved = "Yes" if current_meets else "No"
        
        # Simplified version of the Excel outcome formula
        if is_first_year:
            if target_achieved == "Yes":
                return 1
            else:
                return 0
        else:
            # Not first year - use the complex logic
            if target_achieved == "Yes":
                # Target WAS achieved - check performance change
                if change_cat == ">5%":
                    return 2
                elif change_cat == "-5%<C<=5%":
                    # For stagnation, when target is achieved, score should be 2
                    return 2
                elif change_cat == "-10%<C<=-5%":
                    # For negative change, score lower even if target is achieved
                    return 1
                elif change_cat == "<=-10%":
                    return 0
                else:
                    return 0
            else:
                # Target NOT achieved - check performance change
                if change_cat == ">5%":
                    return 1
                elif change_cat == "-5%<C<=5%":
                    # Stagnation - check how close to target
                    if gap_cat == "<=10%":
                        return 1
                    elif gap_cat == "10%<PT<=40%":
                        return 0
                    elif gap_cat == ">40%":
                        return -1
                    else:
                        return 0
                elif change_cat == "-10%<C<=-5%":
                    return -1
                elif change_cat == "<=-10%":
                    return -1
                else:
                    return 0

    def _median(self, numbers: list[float]) -> float | None:
        vals = [float(x) for x in numbers if x is not None and isinstance(x, (int, float))]
        if not vals:
            return None
        vals.sort()
        n = len(vals)
        mid = n // 2
        if n % 2 == 0:
            return (vals[mid-1] + vals[mid]) / 2
        return vals[mid]

    def _score_color_label(self, score: int | None) -> tuple[str, str]:
        if score is None:
            return ('#6c757d', 'N/A')
        if score >= 2:
            return ('#548235', 'Highly Performing')
        if score == 1:
            return ('#A9D08E', 'Moderately Performing')
        if score == 0:
            return ('#FFFF00', 'Sustained')
        if score == -1:
            return ('#FFC7CE', 'Underperforming')
        return ('#FF0000', 'Severely Underperforming')

    def _clean_numeric_value(self, value):
        """Clean numeric values to ensure JSON compliance"""
        import math
        
        if value is None:
            return None
        
        try:
            # Convert to float if it's a string
            if isinstance(value, str):
                value = float(value)
            
            # Check for NaN, infinity, or other invalid values
            if isinstance(value, (int, float)):
                if math.isnan(value) or math.isinf(value):
                    self.logger.warning(f"Invalid numeric value detected: {value}, setting to None")
                    return None
                return value
            
            return value
            
        except (ValueError, TypeError) as e:
            self.logger.warning(f"Error cleaning numeric value {value}: {str(e)}")
            return None

    def _fetch_single_indicator_data(self, indicator, org_unit_id, period):
        """
        Fetch data for a single indicator without storing in database
        Uses the same approach as the working old_services.py
        """
        self.logger.debug(f"Fetching real-time data for {indicator.name} ({indicator.dhis2_uid}) - {org_unit_id} - {period}")
        
        try:
            # Handle reporting rate indicators differently
            if '.REPORTING_RATE' in indicator.dhis2_uid:
                # Convert period to DHIS2 format for reporting rates
                dhis2_period = self._convert_to_dhis2_period(period)
                if not dhis2_period:
                    self.logger.warning(f"Could not convert period {period} to DHIS2 format for reporting rate")
                    return None
                
                self.logger.info(f"Fetching reporting rate for {indicator.dhis2_uid} with period {dhis2_period}")
                
                # For reporting rates, use the full UID including .REPORTING_RATE as a data element
                response = self.client.get_analytics_data(
                    data_elements=[indicator.dhis2_uid],
                    periods=[dhis2_period],
                    org_units=[org_unit_id]
                )
                value = self._extract_value_from_analytics_response(response, indicator.dhis2_uid)
                if value is not None:
                    self.logger.info(f"Successfully fetched reporting rate: {value}")
                    return value
                    
                self.logger.info(f"No reporting rate data found for {indicator.dhis2_uid}")
                return None

            # Convert period to DHIS2 format
            dhis2_period = self._convert_to_dhis2_period(period)
            self.logger.debug(f"Using DHIS2 period format: {dhis2_period}")
            
            # Try different period formats if needed
            periods_to_try = [dhis2_period]
            if '-' in period:  # If it's a date format
                try:
                    from datetime import datetime
                    date_obj = datetime.strptime(period, '%Y-%m-%d')
                    # Add alternative period formats
                    year = date_obj.strftime('%Y')
                    month = date_obj.strftime('%m')
                    quarter = ((int(month) - 1) // 3) + 1
                    semester = 1 if int(month) <= 6 else 2
                    periods_to_try.extend([
                        f"{year}{month}",  # YYYYMM
                        f"{year}Q{quarter}",  # YYYYQ#
                        f"{year}S{semester}",  # YYYY[S]#
                        year  # YYYY
                    ])
                except ValueError:
                    pass

            # Try each period format
            for try_period in periods_to_try:
                try:
                    # Make DHIS2 API request based on indicator type
                    indicator_type = getattr(indicator, 'indicator_type', 'indicator')  # Default to 'indicator' if not set
                    
                    self.logger.info(f"Making API request for {indicator.name} ({indicator.dhis2_uid}) with type '{indicator_type}' and period '{try_period}'")
                    
                    if indicator_type == 'indicator':
                        response = self.client.get_analytics_data(
                            indicators=[indicator.dhis2_uid],
                            periods=[try_period],
                            org_units=[org_unit_id]
                        )
                    elif indicator_type == 'dataElement':
                        response = self.client.get_analytics_data(
                            data_elements=[indicator.dhis2_uid],
                            periods=[try_period],
                            org_units=[org_unit_id]
                        )
                    elif indicator_type == 'dataSet':
                        response = self.client.get_data_set_report(
                            data_set_id=indicator.dhis2_uid,
                            periods=[try_period],
                            org_units=[org_unit_id]
                        )
                    elif indicator_type == 'programIndicator':
                        response = self.client.get_analytics_data(
                            program_indicators=[indicator.dhis2_uid],
                            periods=[try_period],
                            org_units=[org_unit_id]
                        )
                    else:
                        # Fallback - try as indicator first, then data element
                        self.logger.info(f"Unknown indicator type '{indicator_type}', trying as indicator first")
                        try:
                            response = self.client.get_analytics_data(
                                indicators=[indicator.dhis2_uid],
                                periods=[try_period],
                                org_units=[org_unit_id]
                            )
                        except Exception as e:
                            self.logger.info(f"Failed as indicator, trying as data element: {str(e)}")
                            response = self.client.get_analytics_data(
                                data_elements=[indicator.dhis2_uid],
                                periods=[try_period],
                                org_units=[org_unit_id]
                            )
                    
                    # Extract value from response
                    if indicator_type == 'dataSet':
                        value = self._extract_value_from_dataset_response(response, indicator.dhis2_uid)
                    else:
                        value = self._extract_value_from_analytics_response(response, indicator.dhis2_uid)
                    
                    if value is not None:
                        self.logger.info(f"Successfully fetched data for {indicator.name} using period {try_period}: {value}")
                        return value
                except Exception as e:
                    self.logger.debug(f"Error fetching data for period {try_period}: {str(e)}")
                    continue
            
            # If no data found with any period format, try alternative period formats
            self.logger.info(f"No data found for {indicator.name} using any period format, trying alternative formats")
            return self._try_alternative_period_formats(indicator, org_unit_id, period)
                
        except Exception as e:
            self.logger.error(f"Error fetching data for {indicator.name}: {str(e)}")
            return None

    def _convert_to_dhis2_period(self, period):
        """
        Convert period to DHIS2 format
        
        Supported formats:
        - Yearly: 2024 -> 2024
        - Six-monthly: 2024S1, 2024S2
        - Quarterly: 2024Q1, 2024Q2, 2024Q3, 2024Q4
        - Monthly: 202401, 202402, etc.
        - Weekly: 2024W1, 2024W2, etc.
        - Date strings: 2024-01-01 -> 202401
        """
        try:
            if not period or not isinstance(period, (str, dict)):
                self.logger.warning(f"Invalid period format: {period}")
                return None

            # Handle period dict format
            if isinstance(period, dict):
                if 'code' in period:
                    period = period['code']
                else:
                    self.logger.warning(f"Invalid period dict format: {period}")
                    return None

            # Handle relative periods
            relative_periods = {
                'THIS_YEAR': lambda: datetime.now().strftime('%Y'),
                'LAST_YEAR': lambda: str(int(datetime.now().strftime('%Y')) - 1),
                'THIS_QUARTER': lambda: self._get_current_quarter(),
                'LAST_QUARTER': lambda: self._get_last_quarter(),
                'THIS_MONTH': lambda: datetime.now().strftime('%Y%m'),
                'LAST_MONTH': lambda: (datetime.now().replace(day=1) - timedelta(days=1)).strftime('%Y%m'),
            }

            if period in relative_periods:
                return relative_periods[period]()

            # Handle human-readable period formats like "January 2023"
            import re
            month_names = [
                'January', 'February', 'March', 'April', 'May', 'June',
                'July', 'August', 'September', 'October', 'November', 'December'
            ]
            
            # Pattern for "Month Year" format
            month_year_pattern = r'^(' + '|'.join(month_names) + r')\s+(\d{4})$'
            month_match = re.match(month_year_pattern, period, re.IGNORECASE)
            if month_match:
                try:
                    month_name = month_match.group(1)
                    year = month_match.group(2)
                    month_num = month_names.index(month_name.title()) + 1
                    # Convert to quarterly format
                    quarter = ((month_num - 1) // 3) + 1
                    dhis2_period = f"{year}Q{quarter}"
                    self.logger.info(f"Converted '{period}' to quarterly period {dhis2_period}")
                    return dhis2_period
                except (ValueError, IndexError):
                    self.logger.warning(f"Could not parse month from: {period}")
                    return None
            
            # Pattern for "Month, Year" format
            month_year_comma_pattern = r'^(' + '|'.join(month_names) + r'),\s*(\d{4})$'
            month_comma_match = re.match(month_year_comma_pattern, period, re.IGNORECASE)
            if month_comma_match:
                try:
                    month_name = month_comma_match.group(1)
                    year = month_comma_match.group(2)
                    month_num = month_names.index(month_name.title()) + 1
                    # Convert to quarterly format
                    quarter = ((month_num - 1) // 3) + 1
                    dhis2_period = f"{year}Q{quarter}"
                    self.logger.info(f"Converted '{period}' to quarterly period {dhis2_period}")
                    return dhis2_period
                except (ValueError, IndexError):
                    self.logger.warning(f"Could not parse month from: {period}")
                    return None

            # Handle date string format (YYYY-MM-DD)
            if re.match(r'^\d{4}-\d{2}-\d{2}$', period):
                try:
                    date_obj = datetime.strptime(period, '%Y-%m-%d')
                    # For date strings, determine the appropriate period format based on the date
                    # For now, convert to quarterly format since that's commonly used
                    year = date_obj.year
                    month = date_obj.month
                    quarter = ((month - 1) // 3) + 1
                    dhis2_period = f"{year}Q{quarter}"
                    self.logger.info(f"Converted date {period} to quarterly period {dhis2_period}")
                    return dhis2_period
                except ValueError:
                    self.logger.warning(f"Invalid date string format: {period}")
                    return None

            # Handle fixed period formats
            if re.match(r'^\d{4}$', period):  # Yearly: 2024
                return period
            elif re.match(r'^\d{4}S[1-2]$', period):  # Six-monthly: 2024S1
                return period
            elif re.match(r'^\d{4}Q[1-4]$', period):  # Quarterly: 2024Q1
                return period
            elif re.match(r'^\d{6}$', period):  # Monthly: 202401
                return period
            elif re.match(r'^\d{4}W[1-53]$', period):  # Weekly: 2024W1
                return period
            # Handle space-separated formats
            elif re.match(r'^\d{4}\s+S[1-2]$', period):  # Six-monthly: 2024 S1
                return period.replace(' ', '')  # Remove space
            elif re.match(r'^\d{4}\s+Q[1-4]$', period):  # Quarterly: 2024 Q1
                return period.replace(' ', '')  # Remove space
            elif re.match(r'^\d{4}\s+W[1-53]$', period):  # Weekly: 2024 W1
                return period.replace(' ', '')  # Remove space
            else:
                # Try to parse as date if it contains dashes
                if '-' in period:
                    try:
                        date_obj = datetime.strptime(period.split('T')[0], '%Y-%m-%d')
                        return date_obj.strftime('%Y%m')  # Convert to YYYYMM format
                    except ValueError:
                        pass
                self.logger.warning(f"Unrecognized period format: {period}")
                return None

        except Exception as e:
            self.logger.error(f"Error converting period {period}: {str(e)}")
            return None

    def _get_current_quarter(self):
        now = datetime.now()
        year = now.strftime('%Y')
        quarter = ((now.month - 1) // 3) + 1
        return f"{year}Q{quarter}"

    def _get_last_quarter(self):
        now = datetime.now()
        year = now.strftime('%Y')
        quarter = ((now.month - 1) // 3)
        
        if quarter == 0:
            year = str(int(year) - 1)
            quarter = 4
        
        return f"{year}Q{quarter}"

    def _try_alternative_period_formats(self, indicator, org_unit_id, period):
        """Try alternative period formats when no data is found"""
        try:
            # Extract year and period type
            year = period[:4]
            period_type = None
            
            if '-' in period:  # Handle date format like 2022-10-01
                try:
                    from datetime import datetime
                    date_obj = datetime.strptime(period, '%Y-%m-%d')
                    year = date_obj.strftime('%Y')
                    month = date_obj.strftime('%m')
                    period_type = 'monthly'
                    period = f"{year}{month}"  # Convert to YYYYMM format
                except ValueError:
                    self.logger.warning(f"Invalid date format: {period}")
                    return None
            elif 'Q' in period:
                period_type = 'quarterly'
            elif 'S' in period:
                period_type = 'sixmonthly'
            
            alternative_periods = []
            
            if period_type == 'monthly':
                # Try quarterly period for the corresponding month
                quarter = ((int(period[4:6]) - 1) // 3) + 1
                alternative_periods.append(f"{year}Q{quarter}")
                
                # Try six-monthly period
                semester = 1 if int(period[4:6]) <= 6 else 2
                alternative_periods.append(f"{year}S{semester}")
                
            elif period_type == 'quarterly':
                # Try monthly periods for the quarter
                # Extract quarter number properly (e.g., "2023Q1" -> quarter = 1)
                quarter_str = period.split('Q')[1] if 'Q' in period else period[5:]
                try:
                    quarter = int(quarter_str)
                    start_month = (quarter - 1) * 3 + 1
                    for month in range(start_month, start_month + 3):
                        alternative_periods.append(f"{year}{month:02d}")
                except (ValueError, IndexError):
                    self.logger.warning(f"Could not parse quarter from period: {period}")
                    pass
                    
            elif period_type == 'sixmonthly':
                # Try quarterly periods for the semester
                # Extract semester number properly (e.g., "2023S1" -> semester = 1)
                semester_str = period.split('S')[1] if 'S' in period else period[5:]
                try:
                    semester = int(semester_str)
                    start_quarter = (semester - 1) * 2 + 1
                    for quarter in range(start_quarter, start_quarter + 2):
                        alternative_periods.append(f"{year}Q{quarter}")
                except (ValueError, IndexError):
                    self.logger.warning(f"Could not parse semester from period: {period}")
                    pass
            
            # Always try yearly as fallback
            alternative_periods.append(year)
            
            self.logger.info(f"Trying alternative period formats for {indicator.name}: {alternative_periods}")
            
            for alt_period in alternative_periods:
                try:
                    # Make DHIS2 API request based on indicator type
                    if indicator.indicator_type == 'indicator':
                        response = self.client.get_analytics_data(
                            indicators=[indicator.dhis2_uid],
                            periods=[alt_period],
                            org_units=[org_unit_id]
                        )
                    elif indicator.indicator_type == 'dataElement':
                        response = self.client.get_analytics_data(
                            data_elements=[indicator.dhis2_uid],
                            periods=[alt_period],
                            org_units=[org_unit_id]
                        )
                    elif indicator.indicator_type == 'dataSet':
                        response = self.client.get_data_set_report(
                            data_set_id=indicator.dhis2_uid,
                            periods=[alt_period],
                            org_units=[org_unit_id]
                        )
                    else:
                        continue
                    
                    # Extract value from response
                    if indicator.indicator_type == 'dataSet':
                        value = self._extract_value_from_dataset_response(response, indicator.dhis2_uid)
                    else:
                        value = self._extract_value_from_analytics_response(response, indicator.dhis2_uid)
                    
                    if value is not None:
                        self.logger.info(f"Found data using alternative period format: {alt_period}")
                        return value
                        
                except Exception as e:
                    self.logger.debug(f"Alternative period {alt_period} failed: {str(e)}")
                    continue
            
            self.logger.debug(f"All alternative period formats failed for {indicator.name}")
            return None
            
        except Exception as e:
            self.logger.error(f"Error trying alternative period formats for {indicator.name}: {str(e)}")
            return None

    def _extract_value_from_analytics_response(self, response, indicator_uid):
        """Extract value from DHIS2 analytics response - same logic as DataSyncService"""
        try:
            if not response or not isinstance(response, dict):
                self.logger.warning(f"Invalid response format for indicator {indicator_uid}")
                return None
            
            # Check for rows in response
            rows = response.get('rows', [])
            if not rows:
                # This is normal - some indicators don't have data for all periods/org units
                self.logger.info(f"No data available for indicator {indicator_uid} - this is normal if the indicator has no data for the specified period/org unit")
                return None
            
            # Get headers to understand the structure
            headers = response.get('headers', [])
            if not headers:
                self.logger.warning(f"No headers found in response for indicator {indicator_uid}")
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
            
            self.logger.debug(f"Using value column index {value_column_index} for indicator {indicator_uid}")
            
            # Extract value from the first row
            if value_column_index is not None and len(rows) > 0:
                first_row = rows[0]
                if len(first_row) > value_column_index:
                    value = first_row[value_column_index]
                    self.logger.debug(f"Extracted value {value} from row {first_row}")
                    
                    # Convert to float if possible
                    try:
                        if isinstance(value, str):
                            value = float(value)
                        return value
                    except (ValueError, TypeError):
                        self.logger.warning(f"Could not convert value '{value}' to float for indicator {indicator_uid}")
                        return None
            
            # Try alternative parsing if standard parsing fails
            self.logger.info(f"Standard parsing failed, trying alternative parsing for indicator {indicator_uid}")
            return self._extract_value_alternative_parsing(response, indicator_uid, value_column_index)
            
        except Exception as e:
            self.logger.error(f"Error extracting value from analytics response for indicator {indicator_uid}: {str(e)}")
            return None

    def _extract_value_alternative_parsing(self, response, indicator_uid, value_column_index):
        """Alternative parsing method for analytics response - same logic as DataSyncService"""
        try:
            self.logger.info(f"Starting alternative parsing for {indicator_uid}")
            
            # Try to find the indicator in metadata
            meta_data = response.get('metaData', {})
            items = meta_data.get('items', {})
            
            # Look for the indicator in the items
            if indicator_uid in items:
                item_info = items[indicator_uid]
                self.logger.info(f"Found indicator info in metadata: {item_info}")
            
            # Process rows with more flexible matching
            rows = response.get('rows', [])
            self.logger.info(f"Alternative parsing: processing {len(rows)} rows")
            
            for i, row in enumerate(rows):
                if value_column_index is None or len(row) <= value_column_index:
                    self.logger.debug(f"Alternative parsing: skipping row {i} with insufficient columns")
                    continue
                
                # Try to match by checking if the indicator UID appears anywhere in the row
                row_str = ' '.join(str(cell) for cell in row)
                if indicator_uid in row_str:
                    self.logger.info(f"Alternative parsing: found indicator {indicator_uid} in row {i}: {row}")
                    raw_value = row[value_column_index]
                    
                    if raw_value is None or raw_value == '':
                        self.logger.warning(f"Alternative parsing: empty value found for {indicator_uid}")
                        return None
                    
                    try:
                        value = float(raw_value)
                        self.logger.info(f"Alternative parsing: successfully extracted value {value} for {indicator_uid}")
                        return value
                    except (ValueError, TypeError):
                        self.logger.warning(f"Alternative parsing: could not convert value '{raw_value}' to float for {indicator_uid}")
                        continue
            
            self.logger.warning(f"Alternative parsing: no value found for {indicator_uid}")
            return None
            
        except Exception as e:
            self.logger.error(f"Error in alternative parsing for indicator {indicator_uid}: {str(e)}")
            return None

    def _extract_value_from_dataset_response(self, response, indicator_uid):
        """Extract value from DHIS2 dataset response - same logic as DataSyncService"""
        try:
            if not response or not isinstance(response, dict):
                self.logger.warning(f"Invalid dataset response format for indicator {indicator_uid}")
                return None
            
            # Dataset responses have a different structure
            # Look for the indicator in the response
            if indicator_uid in response:
                value = response[indicator_uid]
                if value is None:
                    self.logger.debug(f"Dataset value is None for indicator {indicator_uid}")
                    return None
                try:
                    return float(value)
                except (ValueError, TypeError):
                    self.logger.warning(f"Could not convert dataset value '{value}' to float for indicator {indicator_uid}")
                    return None
            
            self.logger.warning(f"Indicator {indicator_uid} not found in dataset response")
            return None
            
        except Exception as e:
            self.logger.error(f"Error extracting value from dataset response for indicator {indicator_uid}: {str(e)}")
            return None

    def _get_org_unit_name(self, org_unit_id):
        """Get organization unit name from cache or DHIS2 API"""
        try:
            # Try to get from cache first
            cache_key = f"org_unit_name_{org_unit_id}"
            org_unit_name = cache.get(cache_key)
            
            if org_unit_name:
                return org_unit_name
            
            # For real-time service, try to fetch from DHIS2 API if client is available
            try:
                if self.client:
                    org_unit_data = self.client._make_request("GET", f"api/organisationUnits/{org_unit_id}", 
                                                             params={"fields": "id,name,displayName"})
                    org_unit_name = org_unit_data.get('displayName') or org_unit_data.get('name') or f"Org Unit {org_unit_id}"
                else:
                    org_unit_name = f"Org Unit {org_unit_id}"
            except Exception as e:
                self.logger.warning(f"Could not fetch org unit name from DHIS2: {str(e)}")
                org_unit_name = f"Org Unit {org_unit_id}"
            
            # Cache the result
            cache.set(cache_key, org_unit_name, timeout=3600)  # Cache for 1 hour
            
            return org_unit_name
            
        except Exception as e:
            self.logger.warning(f"Error getting org unit name for {org_unit_id}: {str(e)}")
            return f"Org Unit {org_unit_id}"
