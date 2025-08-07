from django.db import transaction
from django.utils import timezone
from django.db.models import Q, Avg, Count, Sum, Max, Min
from django.core.cache import cache
from decimal import Decimal
import logging

from .models import (
    DataSyncLog, IndicatorData, IndicatorScore, ObjectiveScore, SectorScore
)
from indicators.models import TrackedIndicator
from configurations.models import Objective, AssessmentPeriod, ScoringRule, IndicatorWeight
from organisation.models import OrgUnit
from organisation.services import AccessControlService
from dhis2_auth.dhis_client import DHIS2Client, DHIS2ClientFactory
from dhis2_auth.session import get_dhis2_session_data

logger = logging.getLogger(__name__)


class DataSyncService:
    """
    Service for syncing data from DHIS2
    """
    
    def __init__(self, dhis2_client=None):
        self.client = dhis2_client
    
    def sync_data(self, sync_request, dhis2_user=None, session_key=None):
        """
        Sync data from DHIS2 based on the sync request
        """
        try:
            # Initialize DHIS2 client
            if not self.client:
                if dhis2_user:
                    self.client = DHIS2ClientFactory.create_client_from_session(
                        dhis2_user.dhis2_instance_url,  # Fixed: use correct field name
                        session_key or dhis2_user.current_session_key  # Fixed: use correct field name
                    )
                else:
                    raise ValueError("No DHIS2 user or session provided")
            
            # FIXED: Test connection before syncing
            if not self._test_dhis2_connection():
                raise Exception("Failed to connect to DHIS2 instance")
            
            # Create sync log
            sync_log = DataSyncLog.objects.create(
                dhis2_user=dhis2_user,  # Fixed: use correct field name
                sync_type=sync_request.get('sync_type', 'manual'),
                status=DataSyncLog.SyncStatus.IN_PROGRESS,
                started_at=timezone.now()
            )
            
            # Get data to sync
            indicators = self._get_indicators_to_sync(sync_request)
            org_units = self._get_org_units_to_sync(sync_request)
            periods = self._get_periods_to_sync(sync_request)
            
            logger.info(f"Starting sync for {len(indicators)} indicators, {len(org_units)} org units, {len(periods)} periods")
            
            # Validate sync parameters
            if not indicators:
                raise ValueError("No indicators found to sync")
            if not org_units:
                raise ValueError("No org units found to sync")
            if not periods:
                raise ValueError("No periods found to sync")
            
            # Sync data
            success_count = 0
            failure_count = 0
            total_points = 0
            successful_indicator_uids = []
            
            for indicator in indicators:
                try:
                    points = self._sync_indicator_data_enhanced(indicator, org_units, periods, sync_log)
                    if points > 0:
                        success_count += 1
                        successful_indicator_uids.append(indicator.dhis2_uid)
                        total_points += points
                    else:
                        failure_count += 1
                except Exception as e:
                    failure_count += 1
                    logger.error(f"Failed to sync indicator {indicator.name}: {str(e)}")
            
            # Update sync log with results
            sync_log.success_count = success_count
            sync_log.failure_count = failure_count
            sync_log.total_data_points = total_points
            sync_log.successful_indicator_uids = successful_indicator_uids
            sync_log.status = DataSyncLog.SyncStatus.COMPLETED
            sync_log.completed_at = timezone.now()
            sync_log.save()
            
            # Trigger score calculation
            self._trigger_score_calculation(sync_log)
            
            return {
                'success': True,
                'sync_log_id': sync_log.id,
                'success_count': success_count,
                'failure_count': failure_count,
                'total_points': total_points
            }
            
        except Exception as e:
            # Update sync log with error
            if 'sync_log' in locals():
                sync_log.status = DataSyncLog.SyncStatus.FAILED
                sync_log.error_message = str(e)
                sync_log.completed_at = timezone.now()
                sync_log.save()
            
            logger.error(f"Data sync failed: {str(e)}")
            raise
    
    def _test_dhis2_connection(self):
        """Test DHIS2 connection and API endpoints"""
        try:
            logger.info("Testing DHIS2 connection...")
            
            # Test basic connection
            if not self.client.test_connection():
                logger.error("DHIS2 connection test failed")
                return False
            
            # Test analytics endpoint
            try:
                # Try a simple analytics request to test the endpoint
                test_response = self.client.get_analytics_data(
                    indicators=["test"],
                    periods=["202401"],
                    org_units=["test"]
                )
                logger.info("DHIS2 analytics endpoint is accessible")
            except Exception as e:
                if "409" in str(e):
                    logger.info("DHIS2 analytics endpoint is accessible (409 expected for test data)")
                else:
                    logger.warning(f"DHIS2 analytics endpoint test: {str(e)}")
            
            logger.info("DHIS2 connection test passed")
            return True
            
        except Exception as e:
            logger.error(f"DHIS2 connection test failed: {str(e)}")
            return False
    
    def _get_indicators_to_sync(self, sync_request):
        """Get indicators to sync based on request"""
        indicator_uids = sync_request.get('indicator_uids', [])
        
        if indicator_uids:
            # Sync specific indicators
            return TrackedIndicator.objects.filter(
                dhis2_uid__in=indicator_uids,
                is_active=True
            )
        else:
            # Sync all active indicators
            return TrackedIndicator.objects.filter(is_active=True)
    
    def _get_org_units_to_sync(self, sync_request):
        """Get org units to sync based on request"""
        org_unit_ids = sync_request.get('org_unit_ids', [])
        
        if org_unit_ids:
            # Sync specific org units
            return org_unit_ids
        else:
            # For now, sync all org units - this should be enhanced with user permissions
            return ["LEVEL-1"]  # Default to top-level org unit
    
    def _get_periods_to_sync(self, sync_request):
        """Get periods to sync based on request"""
        period_start = sync_request.get('period_start')
        period_end = sync_request.get('period_end')
        
        if period_start and period_end:
            # Generate periods from date range
            return self._generate_periods_from_dates(period_start, period_end)
        else:
            # Use current assessment period
            current_period = AssessmentPeriod.objects.filter(is_current=True).first()
            if current_period:
                return [current_period.period]
            else:
                # Fallback to current year
                from datetime import datetime
                current_year = datetime.now().year
                return [f"{current_year}"]
    
    def _generate_periods_from_dates(self, start_date, end_date):
        """Generate period list from date range"""
        periods = []
        
        # FIXED: Handle both string and datetime.date objects
        from datetime import datetime, date
        
        # Convert start_date to datetime if it's a date object
        if isinstance(start_date, date):
            start = datetime.combine(start_date, datetime.min.time())
        elif isinstance(start_date, str):
            start = datetime.strptime(start_date, '%Y-%m-%d')
        else:
            start = start_date
        
        # Convert end_date to datetime if it's a date object
        if isinstance(end_date, date):
            end = datetime.combine(end_date, datetime.min.time())
        elif isinstance(end_date, str):
            end = datetime.strptime(end_date, '%Y-%m-%d')
        else:
            end = end_date
        
        current = start
        while current <= end:
            # FIXED: Use DHIS2 standard period format (YYYYMM)
            # DHIS2 supports various period formats, but YYYYMM is most common for monthly data
            period = current.strftime('%Y%m')
            periods.append(period)
            
            # Move to next month
            if current.month == 12:
                current = current.replace(year=current.year + 1, month=1)
            else:
                current = current.replace(month=current.month + 1)
        
        return periods
    
    def _sync_indicator_data_enhanced(self, indicator, org_units, periods, sync_log):
        """Enhanced sync for a single indicator"""
        total_points = 0
        
        for org_unit_id in org_units:
            for period in periods:
                try:
                    # Fetch data from DHIS2
                    value = self._fetch_indicator_data(indicator, org_unit_id, period)
                    
                    if value is not None:
                        # Store the data
                        data_point, created = IndicatorData.objects.update_or_create(
                            indicator=indicator,
                            org_unit_id=org_unit_id,
                            period=period,
                            defaults={
                                'value': value,
                                'org_unit_name': self._get_org_unit_name(org_unit_id),
                                'sync_log': sync_log
                            }
                        )
                        total_points += 1
                        logger.info(f"Synced data point for {indicator.name} - {org_unit_id} - {period}: {value}")
                    else:
                        logger.warning(f"No data found for {indicator.name} in period {period}")
                        
                except Exception as e:
                    logger.error(f"Error syncing data for {indicator.name} in period {period}: {str(e)}")
        
        return total_points
    
    def _fetch_indicator_data(self, indicator, org_unit_id, period):
        """Fetch data for a single indicator from DHIS2"""
        try:
            logger.info(f"Fetching data for indicator {indicator.name} ({indicator.dhis2_uid}) for org unit {org_unit_id} and period {period}")
            
            # FIXED: Use correct DHIS2 API based on indicator type
            if indicator.indicator_type == 'indicator':
                logger.info(f"Making analytics request for indicator type 'indicator' with UID: {indicator.dhis2_uid}")
                response = self.client.get_analytics_data(
                    indicators=[indicator.dhis2_uid],
                    periods=[period],
                    org_units=[org_unit_id]
                )
            elif indicator.indicator_type == 'dataElement':
                logger.info(f"Making analytics request for indicator type 'dataElement' with UID: {indicator.dhis2_uid}")
                response = self.client.get_analytics_data(
                    data_elements=[indicator.dhis2_uid],
                    periods=[period],
                    org_units=[org_unit_id]
                )
            elif indicator.indicator_type == 'dataSet':
                logger.info(f"Making data set report request for indicator type 'dataSet' with UID: {indicator.dhis2_uid}")
                response = self.client.get_data_set_report(
                    data_set_id=indicator.dhis2_uid,
                    periods=[period],
                    org_units=[org_unit_id]
                )
            elif indicator.indicator_type == 'programIndicator':
                logger.info(f"Making analytics request for indicator type 'programIndicator' with UID: {indicator.dhis2_uid}")
                response = self.client.get_analytics_data(
                    program_indicators=[indicator.dhis2_uid],
                    periods=[period],
                    org_units=[org_unit_id]
                )
            else:
                # Fallback to data elements
                logger.info(f"Making analytics request for unknown indicator type '{indicator.indicator_type}' with UID: {indicator.dhis2_uid}")
                response = self.client.get_analytics_data(
                    data_elements=[indicator.dhis2_uid],
                    periods=[period],
                    org_units=[org_unit_id]
                )
            
            # FIXED: Enhanced response validation and debugging
            if not response:
                logger.warning(f"Empty response for indicator {indicator.name} ({indicator.dhis2_uid})")
                return None
            
            logger.debug(f"DHIS2 response for {indicator.name}: {response}")
            
            # Extract value based on indicator type
            if indicator.indicator_type == 'dataSet':
                value = self._extract_value_from_dataset_response(response, indicator.dhis2_uid)
            else:
                value = self._extract_value_from_analytics_response(response, indicator.dhis2_uid)
            
            if value is not None:
                logger.info(f"Successfully extracted value {value} for indicator {indicator.name}")
                return value
            else:
                logger.warning(f"No value found for indicator {indicator.name} ({indicator.dhis2_uid})")
                return None
                
        except Exception as e:
            logger.error(f"Error fetching data for indicator {indicator.name}: {str(e)}")
            
            # FIXED: Try alternative period formats if we get a 409 error
            if "409" in str(e) or "Conflict" in str(e):
                logger.info(f"Trying alternative period formats for indicator {indicator.name}")
                return self._try_alternative_period_formats(indicator, org_unit_id, period)
            
            return None

    def _try_alternative_period_formats(self, indicator, org_unit_id, period):
        """Try alternative period formats when 409 error occurs"""
        try:
            # Try different period formats that DHIS2 might accept
            alternative_periods = []
            
            # Original format: YYYYMM
            alternative_periods.append(period)
            
            # Try YYYY-MM format
            if len(period) == 6:
                year = period[:4]
                month = period[4:6]
                alternative_periods.append(f"{year}-{month}")
            
            # Try YYYYMMDD format (first day of month)
            if len(period) == 6:
                year = period[:4]
                month = period[4:6]
                alternative_periods.append(f"{year}{month}01")
            
            # Try relative periods
            alternative_periods.extend([
                "LAST_MONTH",
                "LAST_3_MONTHS", 
                "LAST_6_MONTHS",
                "LAST_12_MONTHS"
            ])
            
            logger.info(f"Trying alternative period formats for {indicator.name}: {alternative_periods}")
            
            for alt_period in alternative_periods:
                try:
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
                    else:
                        continue
                    
                    value = self._extract_value_from_analytics_response(response, indicator.dhis2_uid)
                    if value is not None:
                        logger.info(f"Found data using alternative period format: {alt_period}")
                        return value
                        
                except Exception as e:
                    logger.debug(f"Alternative period {alt_period} failed: {str(e)}")
                    continue
            
            logger.warning(f"All alternative period formats failed for {indicator.name}")
            return None
            
        except Exception as e:
            logger.error(f"Error trying alternative period formats: {str(e)}")
            return None

    def _extract_value_from_analytics_response(self, response, indicator_uid):
        """Extract value from DHIS2 analytics response"""
        try:
            if not response or not isinstance(response, dict):
                logger.warning(f"Invalid response format for indicator {indicator_uid}")
                return None
            
            # Check for rows in response
            rows = response.get('rows', [])
            if not rows:
                logger.warning(f"No rows found in response for indicator {indicator_uid}")
                return None
            
            # Get headers to understand the structure
            headers = response.get('headers', [])
            if not headers:
                logger.warning(f"No headers found in response for indicator {indicator_uid}")
                return None
            
            # FIXED: Enhanced column detection
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
            
            # FIXED: Try alternative parsing if standard parsing fails
            logger.info(f"Standard parsing failed, trying alternative parsing for indicator {indicator_uid}")
            return self._extract_value_alternative_parsing(response, indicator_uid, value_column_index)
            
        except Exception as e:
            logger.error(f"Error extracting value from analytics response for indicator {indicator_uid}: {str(e)}")
            return None

    def _extract_value_alternative_parsing(self, response, indicator_uid, value_column_index):
        """Alternative parsing method for analytics response"""
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
                if len(row) <= value_column_index:
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
                        logger.info(f"Alternative parsing: successfully converted value to float: {value}")
                        return value
                    except (ValueError, TypeError):
                        logger.warning(f"Alternative parsing: could not convert value '{raw_value}' to float for {indicator_uid}")
                        return None
            
            logger.warning(f"Alternative parsing: no value found for {indicator_uid}")
            return None
            
        except Exception as e:
            logger.error(f"Error in alternative parsing for {indicator_uid}: {str(e)}")
            return None

    def _extract_value_from_dataset_response(self, response, indicator_uid):
        """Extract value from DHIS2 data set report response"""
        try:
            if not isinstance(response, dict):
                logger.warning(f"Invalid response type: {type(response)}")
                return None
            
            # Data set reports have a different structure
            # Look for data in various possible locations
            if 'dataValues' in response:
                data_values = response['dataValues']
                if data_values:
                    # Return the first data value
                    return float(data_values[0].get('value', 0))
            
            if 'data' in response:
                data = response['data']
                if isinstance(data, list) and data:
                    # Return the first data point
                    return float(data[0].get('value', 0))
            
            logger.warning(f"No data found in data set report for {indicator_uid}")
            return None
            
        except Exception as e:
            logger.error(f"Error extracting value from data set response: {str(e)}")
            return None

    def _fetch_indicator_data_batch(self, indicators, org_unit_id, period):
        """Fetch data for multiple indicators in a single request for better performance"""
        try:
            logger.info(f"Fetching batch data for {len(indicators)} indicators for org unit {org_unit_id} and period {period}")
            
            # Separate indicators by type
            data_elements = []
            indicators_list = []
            data_sets = []
            program_indicators = []
            
            for indicator in indicators:
                if indicator.indicator_type == 'indicator':
                    indicators_list.append(indicator.dhis2_uid)
                elif indicator.indicator_type == 'dataElement':
                    data_elements.append(indicator.dhis2_uid)
                elif indicator.indicator_type == 'dataSet':
                    data_sets.append(indicator.dhis2_uid)
                elif indicator.indicator_type == 'programIndicator':
                    program_indicators.append(indicator.dhis2_uid)
                else:
                    # Fallback to data elements
                    data_elements.append(indicator.dhis2_uid)
            
            # Make batch request
            response = self.client.get_analytics_data(
                data_elements=data_elements if data_elements else None,
                indicators=indicators_list if indicators_list else None,
                data_sets=data_sets if data_sets else None,
                program_indicators=program_indicators if program_indicators else None,
                periods=[period],
                org_units=[org_unit_id]
            )
            
            logger.debug(f"Batch DHIS2 response: {response}")
            
            # Extract values for each indicator
            results = {}
            for indicator in indicators:
                value = self._extract_value_from_analytics_response(response, indicator.dhis2_uid)
                results[indicator.dhis2_uid] = value
                
                if value is not None:
                    logger.info(f"Found value {value} for indicator {indicator.dhis2_uid}")
                else:
                    logger.warning(f"No data found for indicator {indicator.dhis2_uid}")
            
            return results
            
        except Exception as e:
            logger.error(f"Error fetching batch data: {str(e)}")
            return {}
    
    def _get_org_unit_name(self, org_unit_id):
        """Get organization unit name from cache or DHIS2 API (simplified for DHIS2-only workflow)"""
        try:
            # Try to get from cache first
            cache_key = f"org_unit_name_{org_unit_id}"
            org_unit_name = cache.get(cache_key)
            
            if org_unit_name:
                return org_unit_name
            
            # Since org units come from DHIS2 frontend, we can either:
            # 1. Use the org unit ID as the name (simple approach)
            # 2. Fetch the name from DHIS2 API (more complete but adds API calls)
            
            # Simple approach: Use ID as name for now
            org_unit_name = f"Org Unit {org_unit_id}"
            
            # Optional: Fetch actual name from DHIS2 (uncomment if needed)
            # try:
            #     if self.client:
            #         org_unit_data = self.client._make_request("GET", f"api/organisationUnits/{org_unit_id}", 
            #                                                  params={"fields": "id,name,displayName"})
            #         org_unit_name = org_unit_data.get('displayName') or org_unit_data.get('name') or f"Org Unit {org_unit_id}"
            # except Exception as e:
            #     logger.warning(f"Could not fetch org unit name from DHIS2: {str(e)}")
            #     org_unit_name = f"Org Unit {org_unit_id}"
            
            # Cache the result
            cache.set(cache_key, org_unit_name, timeout=3600)  # Cache for 1 hour
            
            return org_unit_name
            
        except Exception as e:
            logger.warning(f"Error getting org unit name for {org_unit_id}: {str(e)}")
            return f"Org Unit {org_unit_id}"
    
    def _trigger_score_calculation(self, sync_log):
        """Trigger score calculation for synced data"""
        try:
            calculation_service = ScoreCalculationService()
            
            # Get unique org units and periods from sync log
            org_units = set()
            periods = set()
            
            # Extract org units and periods from synced data
            synced_data = IndicatorData.objects.filter(
                sync_log=sync_log
            ).values('org_unit_id', 'period').distinct()
            
            for data in synced_data:
                org_units.add(data['org_unit_id'])
                periods.add(data['period'])
            
            # Calculate scores for each org unit and period combination
            for org_unit_id in org_units:
                for period in periods:
                    calculation_service.calculate_scores_for_org_unit(org_unit_id, period)
            
            logger.info(f"Score calculation triggered for {len(org_units)} org units and {len(periods)} periods")
            
        except Exception as e:
            logger.error(f"Failed to trigger score calculation: {str(e)}")


class ScoreCalculationService:
    """
    Service for calculating scores from indicator data
    """
    
    def calculate_scores_for_org_unit(self, org_unit_id, assessment_period):
        """
        Calculate all scores for a specific org unit and assessment period
        """
        try:
            # Calculate indicator scores
            self._calculate_indicator_scores(org_unit_id, assessment_period)
            
            # Calculate objective scores
            self._calculate_objective_scores(org_unit_id, assessment_period)
            
            # Calculate sector score
            self._calculate_sector_score(org_unit_id, assessment_period)
            
            logger.info(f"Score calculation completed for org unit {org_unit_id} and period {assessment_period}")
            
        except Exception as e:
            logger.error(f"Failed to calculate scores for org unit {org_unit_id}: {str(e)}")
            raise
    
    def _calculate_indicator_scores(self, org_unit_id, assessment_period):
        """Calculate indicator scores"""
        # Get all indicator data for this org unit and period
        indicator_data = IndicatorData.objects.filter(
            org_unit_id=org_unit_id,
            period=assessment_period
        ).select_related('indicator')
        
        for data in indicator_data:
            try:
                # FIXED: Get scoring rule for this indicator - use performance_type instead of indicator_type
                scoring_rule = ScoringRule.objects.filter(
                    performance_type='gap',  # Use gap as default performance type
                    is_active=True
                ).first()
                
                if not scoring_rule:
                    # Create a default scoring rule if none exists
                    scoring_rule = ScoringRule.objects.create(
                        name='Default Gap Rule',
                        performance_type='gap',
                        min_value=Decimal('-100'),
                        max_value=Decimal('100'),
                        score=0,
                        color='#6c757d',
                        label='Default',
                        priority=0
                    )
                
                # Calculate score based on value and target
                score = self._calculate_score(data.value, data.indicator.target_value, scoring_rule)
                
                # Get previous period for trend calculation
                previous_period = self._get_previous_period(assessment_period)
                previous_score = None
                
                if previous_period:
                    prev_data = IndicatorScore.objects.filter(
                        indicator=data.indicator,
                        org_unit_id=org_unit_id,
                        assessment_period=previous_period
                    ).first()
                    if prev_data:
                        previous_score = prev_data.score
                
                # Calculate trend
                trend = self._calculate_trend(score, previous_score) if previous_score is not None else None
                
                # FIXED: Use direct color and label from scoring rule instead of non-existent methods
                color = scoring_rule.color
                label = scoring_rule.label
                
                # Create or update indicator score
                indicator_score, created = IndicatorScore.objects.update_or_create(
                    indicator=data.indicator,
                    org_unit_id=org_unit_id,
                    assessment_period=assessment_period,
                    defaults={
                        'current_value': data.value,  # FIXED: Use current_value instead of raw_value
                        'score': score,
                        'score_color': color,  # FIXED: Use score_color instead of color
                        'score_label': label,  # FIXED: Use score_label instead of label
                        'last_calculated': timezone.now()
                    }
                )
                
            except Exception as e:
                logger.error(f"Failed to calculate score for indicator {data.indicator.name}: {str(e)}")
    
    def _calculate_objective_scores(self, org_unit_id, assessment_period):
        """Calculate objective scores"""
        # Get all objectives
        objectives = Objective.objects.filter(is_active=True)
        
        for objective in objectives:
            try:
                # FIXED: Use correct relationship through IndicatorWeight to get indicator scores for this objective
                # Get all indicators that belong to this objective
                objective_indicators = TrackedIndicator.objects.filter(
                    objective_weights__objective=objective
                )
                
                # Get indicator scores for these indicators
                indicator_scores = IndicatorScore.objects.filter(
                    indicator__in=objective_indicators,
                    org_unit_id=org_unit_id,
                    assessment_period=assessment_period
                ).select_related('indicator')
                
                if not indicator_scores.exists():
                    continue
                
                # Calculate weighted average score
                total_weight = 0
                weighted_sum = 0
                
                for score in indicator_scores:
                    weight = IndicatorWeight.objects.filter(
                        indicator=score.indicator,
                        objective=objective
                    ).first()
                    
                    if weight and score.score is not None:
                        total_weight += weight.weight
                        weighted_sum += score.score * weight.weight
                
                if total_weight > 0:
                    objective_score_value = weighted_sum / total_weight
                else:
                    # Use median if no weights defined
                    scores = list(indicator_scores.values_list('score', flat=True))
                    scores = [s for s in scores if s is not None]
                    if scores:
                        scores.sort()
                        objective_score_value = scores[len(scores) // 2]
                    else:
                        objective_score_value = 0
                
                # Get scoring rule for objectives
                scoring_rule = ScoringRule.objects.filter(
                    performance_type='gap'  # FIXED: Use performance_type instead of rule_type
                ).first()
                
                if scoring_rule:
                    color = scoring_rule.color
                    label = scoring_rule.label
                else:
                    color = '#666666'
                    label = 'Unknown'
                
                # Create or update objective score
                objective_score, created = ObjectiveScore.objects.update_or_create(
                    objective=objective,
                    org_unit_id=org_unit_id,
                    assessment_period=assessment_period,
                    defaults={
                        'score': objective_score_value,
                        'color': color,
                        'label': label,
                        'last_calculated': timezone.now()
                    }
                )
                
            except Exception as e:
                logger.error(f"Failed to calculate objective score for {objective.name}: {str(e)}")
    
    def _calculate_sector_score(self, org_unit_id, assessment_period):
        """Calculate overall sector score"""
        try:
            # Get all objective scores for this org unit and period
            objective_scores = ObjectiveScore.objects.filter(
                org_unit_id=org_unit_id,
                assessment_period=assessment_period
            )
            
            if not objective_scores.exists():
                return
            
            # Calculate weighted average of objective scores
            total_weight = 0
            weighted_sum = 0
            
            for obj_score in objective_scores:
                weight = obj_score.objective.weight if hasattr(obj_score.objective, 'weight') else 1
                total_weight += weight
                weighted_sum += obj_score.score * weight
            
            if total_weight > 0:
                sector_score_value = weighted_sum / total_weight
            else:
                # Use average if no weights defined
                sector_score_value = objective_scores.aggregate(Avg('score'))['score__avg'] or 0
            
            # Get scoring rule for sector scores
            scoring_rule = ScoringRule.objects.filter(
                rule_type='sector'
            ).first()
            
            if scoring_rule:
                color = scoring_rule.color
                label = scoring_rule.label
            else:
                color = '#666666'
                label = 'Unknown'
            
            # Create or update sector score
            sector_score, created = SectorScore.objects.update_or_create(
                org_unit_id=org_unit_id,
                assessment_period=assessment_period,
                defaults={
                    'score': sector_score_value,
                    'color': color,
                    'label': label,
                    'last_calculated': timezone.now()
                }
            )
            
        except Exception as e:
            logger.error(f"Failed to calculate sector score: {str(e)}")
    
    def _get_previous_period(self, assessment_period):
        """Get the previous assessment period"""
        try:
            # Parse period (assuming YYYYMM format)
            year = int(assessment_period[:4])
            month = int(assessment_period[4:])
            
            # Calculate previous month
            if month == 1:
                prev_month = 12
                prev_year = year - 1
            else:
                prev_month = month - 1
                prev_year = year
            
            return f"{prev_year:04d}{prev_month:02d}"
            
        except Exception:
            return None
    
    def _calculate_score(self, value, target, scoring_rule):
        """Calculate score based on value, target, and scoring rule"""
        if value is None or target is None:
            return 0
        
        # Calculate gap to target
        gap = abs(value - target)
        gap_percentage = (gap / target) * 100 if target != 0 else 0
        
        # FIXED: Implement scoring logic directly instead of calling non-existent evaluate_score method
        # Find matching scoring rule based on gap percentage
        matching_rule = ScoringRule.objects.filter(
            performance_type='gap',
            is_active=True
        ).order_by('-priority', 'min_value')
        
        for rule in matching_rule:
            if rule.matches_value(gap_percentage):
                return rule.score
        
        # Return default score if no rule matches
        return 0
    
    def _calculate_trend(self, current_score, previous_score):
        """Calculate trend direction"""
        if previous_score is None:
            return 'stable'
        
        if current_score > previous_score:
            return 'improving'
        elif current_score < previous_score:
            return 'declining'
        else:
            return 'stable'
    
    def bulk_calculate_scores(self, request_data):
        """
        Bulk calculate scores for multiple org units and periods
        """
        org_unit_ids = request_data.get('org_unit_ids', [])
        assessment_periods = request_data.get('assessment_periods', [])
        
        results = {
            'total_org_units': len(org_unit_ids),
            'total_periods': len(assessment_periods),
            'successful_calculations': 0,
            'failed_calculations': 0,
            'errors': []
        }
        
        for org_unit_id in org_unit_ids:
            for period in assessment_periods:
                try:
                    self.calculate_scores_for_org_unit(org_unit_id, period)
                    results['successful_calculations'] += 1
                except Exception as e:
                    results['failed_calculations'] += 1
                    error_msg = f"Failed to calculate scores for org unit {org_unit_id} and period {period}: {str(e)}"
                    results['errors'].append(error_msg)
                    logger.error(error_msg)
        
        return results


class DashboardService:
    """
    Service for generating dashboard data
    """
    
    def __init__(self):
        self.access_service = AccessControlService()
    
    def get_dashboard_summary(self, user, org_unit_id=None, assessment_period=None):
        """
        Get dashboard summary for a user
        """
        # Get user's accessible org units
        accessible_org_units = self.access_service.get_user_accessible_org_units(user)
        
        if org_unit_id:
            # Check if user has access to this specific org unit
            if not accessible_org_units.filter(id=org_unit_id).exists():
                return None
            org_units = [org_unit_id]
        else:
            # Use all accessible org units
            org_units = list(accessible_org_units.values_list('id', flat=True))
        
        # Get current assessment period if not specified
        if not assessment_period:
            current_period = AssessmentPeriod.objects.filter(is_current=True).first()
            assessment_period = current_period.period if current_period else None
        
        if not assessment_period:
            return None
        
        # Get sector scores for accessible org units
        sector_scores = SectorScore.objects.filter(
            org_unit_id__in=org_units,
            assessment_period=assessment_period
        ).select_related('org_unit')
        
        # Calculate summary statistics
        total_org_units = len(org_units)
        org_units_with_scores = sector_scores.count()
        
        if org_units_with_scores > 0:
            avg_score = sector_scores.aggregate(Avg('score'))['score__avg']
            max_score = sector_scores.aggregate(Max('score'))['score__max']
            min_score = sector_scores.aggregate(Min('score'))['score__min']
            
            # Count by performance category
            performance_counts = {}
            for score in sector_scores:
                label = score.label or 'Unknown'
                performance_counts[label] = performance_counts.get(label, 0) + 1
        else:
            avg_score = max_score = min_score = 0
            performance_counts = {}
        
        return {
            'assessment_period': assessment_period,
            'total_org_units': total_org_units,
            'org_units_with_scores': org_units_with_scores,
            'average_score': round(avg_score, 2) if avg_score else 0,
            'max_score': round(max_score, 2) if max_score else 0,
            'min_score': round(min_score, 2) if min_score else 0,
            'performance_distribution': performance_counts,
            'sector_scores': [
                {
                    'org_unit_id': score.org_unit_id,
                    'org_unit_name': score.org_unit.name,
                    'score': score.score,
                    'color': score.color,
                    'label': score.label
                }
                for score in sector_scores
            ]
        }
    
    def get_objective_dashboard(self, user, org_unit_id=None, assessment_period=None):
        """
        Get objective dashboard data
        """
        # Get user's accessible org units
        accessible_org_units = self.access_service.get_user_accessible_org_units(user)
        
        if org_unit_id:
            # Check if user has access to this specific org unit
            if not accessible_org_units.filter(id=org_unit_id).exists():
                return None
            org_units = [org_unit_id]
        else:
            # Use all accessible org units
            org_units = list(accessible_org_units.values_list('id', flat=True))
        
        # Get current assessment period if not specified
        if not assessment_period:
            current_period = AssessmentPeriod.objects.filter(is_current=True).first()
            assessment_period = current_period.period if current_period else None
        
        if not assessment_period:
            return None
        
        # Get objective scores for accessible org units
        objective_scores = ObjectiveScore.objects.filter(
            org_unit_id__in=org_units,
            assessment_period=assessment_period
        ).select_related('objective', 'org_unit')
        
        # Group by objective
        objectives_data = {}
        for score in objective_scores:
            objective_name = score.objective.name
            if objective_name not in objectives_data:
                objectives_data[objective_name] = {
                    'objective_id': score.objective.id,
                    'objective_name': objective_name,
                    'scores': [],
                    'average_score': 0,
                    'performance_distribution': {}
                }
            
            objectives_data[objective_name]['scores'].append({
                'org_unit_id': score.org_unit_id,
                'org_unit_name': score.org_unit.name,
                'score': score.score,
                'color': score.color,
                'label': score.label
            })
        
        # Calculate statistics for each objective
        for objective_name, data in objectives_data.items():
            scores = [score['score'] for score in data['scores']]
            if scores:
                data['average_score'] = round(sum(scores) / len(scores), 2)
                
                # Count by performance category
                for score in data['scores']:
                    label = score['label'] or 'Unknown'
                    data['performance_distribution'][label] = data['performance_distribution'].get(label, 0) + 1
        
        return {
            'assessment_period': assessment_period,
            'objectives': list(objectives_data.values())
        }
    
    def get_indicator_dashboard(self, user, org_unit_id=None, assessment_period=None, objective_id=None):
        """
        Get indicator dashboard data
        """
        # Get user's accessible org units
        accessible_org_units = self.access_service.get_user_accessible_org_units(user)
        
        if org_unit_id:
            # Check if user has access to this specific org unit
            if not accessible_org_units.filter(id=org_unit_id).exists():
                return None
            org_units = [org_unit_id]
        else:
            # Use all accessible org units
            org_units = list(accessible_org_units.values_list('id', flat=True))
        
        # Get current assessment period if not specified
        if not assessment_period:
            current_period = AssessmentPeriod.objects.filter(is_current=True).first()
            assessment_period = current_period.period if current_period else None
        
        if not assessment_period:
            return None
        
        # Build query for indicator scores
        indicator_scores = IndicatorScore.objects.filter(
            org_unit_id__in=org_units,
            assessment_period=assessment_period
        ).select_related('indicator', 'org_unit')
        
        # Filter by objective if specified
        if objective_id:
            indicator_scores = indicator_scores.filter(indicator__objectives__id=objective_id)
        
        # Group by indicator
        indicators_data = {}
        for score in indicator_scores:
            indicator_name = score.indicator.name
            if indicator_name not in indicators_data:
                indicators_data[indicator_name] = {
                    'indicator_id': score.indicator.id,
                    'indicator_name': indicator_name,
                    'indicator_type': score.indicator.indicator_type,
                    'target_value': score.indicator.target_value,
                    'scores': [],
                    'average_score': 0,
                    'performance_distribution': {},
                    'trend_analysis': {
                        'improving': 0,
                        'declining': 0,
                        'stable': 0
                    }
                }
            
            indicators_data[indicator_name]['scores'].append({
                'org_unit_id': score.org_unit_id,
                'org_unit_name': score.org_unit.name,
                'raw_value': score.current_value,
                'score': score.score,
                'trend': score.trend,
                'color': score.score_color,
                'label': score.score_label
            })
        
        # Calculate statistics for each indicator
        for indicator_name, data in indicators_data.items():
            scores = [score['score'] for score in data['scores']]
            if scores:
                data['average_score'] = round(sum(scores) / len(scores), 2)
                
                # Count by performance category and trend
                for score in data['scores']:
                    label = score['label'] or 'Unknown'
                    data['performance_distribution'][label] = data['performance_distribution'].get(label, 0) + 1
                    
                    trend = score['trend'] or 'stable'
                    data['trend_analysis'][trend] = data['trend_analysis'].get(trend, 0) + 1
        
        return {
            'assessment_period': assessment_period,
            'objective_id': objective_id,
            'indicators': list(indicators_data.values())
        }
    
    def get_org_unit_performance(self, user, org_unit_id, assessment_period=None):
        """
        Get detailed performance data for a specific org unit
        """
        # Check if user has access to this org unit
        accessible_org_units = self.access_service.get_user_accessible_org_units(user)
        if not accessible_org_units.filter(id=org_unit_id).exists():
            return None
        
        # Get current assessment period if not specified
        if not assessment_period:
            current_period = AssessmentPeriod.objects.filter(is_current=True).first()
            assessment_period = current_period.period if current_period else None
        
        if not assessment_period:
            return None
        
        # Get org unit details
        org_unit = OrgUnit.objects.get(id=org_unit_id)
        
        # Get sector score
        sector_score = SectorScore.objects.filter(
            org_unit_id=org_unit_id,
            assessment_period=assessment_period
        ).first()
        
        # Get objective scores
        objective_scores = ObjectiveScore.objects.filter(
            org_unit_id=org_unit_id,
            assessment_period=assessment_period
        ).select_related('objective')
        
        # Get indicator scores
        indicator_scores = IndicatorScore.objects.filter(
            org_unit_id=org_unit_id,
            assessment_period=assessment_period
        ).select_related('indicator')
        
        return {
            'org_unit': {
                'id': org_unit.id,
                'name': org_unit.name,
                'level': org_unit.level.name
            },
            'assessment_period': assessment_period,
            'sector_score': {
                'score': sector_score.score if sector_score else None,
                'color': sector_score.color if sector_score else None,
                'label': sector_score.label if sector_score else None
            },
            'objectives': [
                {
                    'objective_id': score.objective.id,
                    'objective_name': score.objective.name,
                    'score': score.score,
                    'color': score.color,
                    'label': score.label
                }
                for score in objective_scores
            ],
            'indicators': [
                {
                    'indicator_id': score.indicator.id,
                    'indicator_name': score.indicator.name,
                    'raw_value': score.current_value,
                    'score': score.score,
                    'trend': score.trend,
                    'color': score.score_color,
                    'label': score.score_label
                }
                for score in indicator_scores
            ]
        }
    
    def get_trend_analysis(self, user, org_unit_id, assessment_period=None, periods_back=3):
        """
        Get trend analysis for an org unit over multiple periods
        """
        # Check if user has access to this org unit
        accessible_org_units = self.access_service.get_user_accessible_org_units(user)
        if not accessible_org_units.filter(id=org_unit_id).exists():
            return None
        
        # Get current assessment period if not specified
        if not assessment_period:
            current_period = AssessmentPeriod.objects.filter(is_current=True).first()
            assessment_period = current_period.period if current_period else None
        
        if not assessment_period:
            return None
        
        # Generate list of periods to analyze
        periods = self._generate_periods_back(assessment_period, periods_back)
        
        # Get sector scores for all periods
        sector_scores = SectorScore.objects.filter(
            org_unit_id=org_unit_id,
            assessment_period__in=periods
        ).order_by('assessment_period')
        
        # Get objective scores for all periods
        objective_scores = ObjectiveScore.objects.filter(
            org_unit_id=org_unit_id,
            assessment_period__in=periods
        ).select_related('objective').order_by('objective__name', 'assessment_period')
        
        # Build trend data
        sector_trend = []
        objectives_trend = {}
        
        for period in periods:
            # Sector score for this period
            period_sector_score = sector_scores.filter(assessment_period=period).first()
            sector_trend.append({
                'period': period,
                'score': period_sector_score.score if period_sector_score else None,
                'color': period_sector_score.color if period_sector_score else None,
                'label': period_sector_score.label if period_sector_score else None
            })
            
            # Objective scores for this period
            period_objective_scores = objective_scores.filter(assessment_period=period)
            for score in period_objective_scores:
                objective_name = score.objective.name
                if objective_name not in objectives_trend:
                    objectives_trend[objective_name] = []
                
                objectives_trend[objective_name].append({
                    'period': period,
                    'score': score.score,
                    'color': score.color,
                    'label': score.label
                })
        
        return {
            'org_unit_id': org_unit_id,
            'periods': periods,
            'sector_trend': sector_trend,
            'objectives_trend': objectives_trend
        }
    
    def _generate_periods_back(self, current_period, periods_back):
        """
        Generate list of periods going back from current period
        """
        periods = [current_period]
        
        for i in range(1, periods_back):
            # Parse current period (assuming YYYYMM format)
            year = int(current_period[:4])
            month = int(current_period[4:])
            
            # Calculate previous month
            if month == 1:
                prev_month = 12
                prev_year = year - 1
            else:
                prev_month = month - 1
                prev_year = year
            
            prev_period = f"{prev_year:04d}{prev_month:02d}"
            periods.append(prev_period)
            
            # Update for next iteration
            current_period = prev_period
        
        return periods[::-1]  # Reverse to get chronological order
    
    def _calculate_trend_direction(self, scores):
        """
        Calculate overall trend direction from a list of scores
        """
        if len(scores) < 2:
            return 'stable'
        
        # Calculate trend based on recent scores
        recent_scores = scores[-3:]  # Last 3 scores
        if len(recent_scores) >= 2:
            if recent_scores[-1] > recent_scores[0]:
                return 'improving'
            elif recent_scores[-1] < recent_scores[0]:
                return 'declining'
        
        return 'stable' 