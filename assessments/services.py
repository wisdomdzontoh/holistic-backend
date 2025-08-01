from django.db import transaction
from django.utils import timezone
from django.db.models import Q, Avg, Count, Sum, Max, Min
from decimal import Decimal
import logging

from .models import (
    DataSyncLog, IndicatorData, IndicatorScore, ObjectiveScore, SectorScore
)
from indicators.models import TrackedIndicator
from configurations.models import Objective, AssessmentPeriod, ScoringRule, IndicatorWeight
from organisation.models import OrgUnit
from organisation.services import AccessControlService
from dhis2_auth.dhis_client import DHIS2Client
from dhis2_auth.session import get_dhis2_session_data

logger = logging.getLogger(__name__)


class DataSyncService:
    """
    Service for syncing data from DHIS2
    """
    
    def __init__(self, dhis2_client=None):
        self.client = dhis2_client
    
    def sync_data(self, sync_request, dhis2_user=None):
        """
        Sync data from DHIS2 based on the sync request
        """
        # Create sync log
        sync_log = DataSyncLog.objects.create(
            sync_type=sync_request.get('sync_type', DataSyncLog.SyncType.FULL),
            dhis2_instance_url=sync_request.get('dhis2_instance_url', ''),
            dhis2_user=dhis2_user,
            period_start=sync_request.get('period_start'),
            period_end=sync_request.get('period_end'),
            org_unit_ids=sync_request.get('org_unit_ids', []),
            indicator_uids=sync_request.get('indicator_uids', [])
        )
        
        try:
            # Initialize DHIS2 client if not provided
            if not self.client:
                session_data = get_dhis2_session_data()
                if not session_data:
                    raise Exception("No active DHIS2 session")
                
                self.client = DHIS2Client(
                    instance_url=session_data.get('instance_url'),
                    username=session_data.get('username'),
                    password=session_data.get('password')
                )
            
            # Get indicators to sync
            indicators = self._get_indicators_to_sync(sync_request)
            
            # Get org units to sync
            org_units = self._get_org_units_to_sync(sync_request)
            
            # Get periods to sync
            periods = self._get_periods_to_sync(sync_request)
            
            # Perform the sync
            success_count = 0
            failure_count = 0
            total_points = 0
            
            for indicator in indicators:
                try:
                    points_synced = self._sync_indicator_data(
                        indicator, org_units, periods, sync_log
                    )
                    success_count += 1
                    total_points += points_synced
                    logger.info(f"Synced indicator {indicator.name}: {points_synced} data points")
                    
                except Exception as e:
                    failure_count += 1
                    logger.error(f"Failed to sync indicator {indicator.name}: {str(e)}")
            
            # Mark sync as completed
            if failure_count == 0:
                sync_log.mark_completed(success_count, failure_count, total_points)
            else:
                sync_log.mark_partial(success_count, failure_count, total_points)
            
            # Calculate scores if requested
            if sync_request.get('calculate_scores', True):
                self._trigger_score_calculation(sync_log)
            
            return sync_log
            
        except Exception as e:
            sync_log.mark_failed(str(e))
            logger.error(f"Data sync failed: {str(e)}")
            raise
    
    def _get_indicators_to_sync(self, sync_request):
        """Get indicators to sync based on request"""
        if sync_request.get('indicator_uids'):
            return TrackedIndicator.objects.filter(
                dhis2_uid__in=sync_request['indicator_uids'],
                is_active=True
            )
        else:
            return TrackedIndicator.objects.filter(is_active=True)
    
    def _get_org_units_to_sync(self, sync_request):
        """Get org units to sync based on request"""
        if sync_request.get('org_unit_ids'):
            return OrgUnit.objects.filter(
                dhis2_uid__in=sync_request['org_unit_ids'],
                is_active=True
            )
        else:
            return OrgUnit.objects.filter(is_active=True)
    
    def _get_periods_to_sync(self, sync_request):
        """Get periods to sync based on request"""
        if sync_request.get('period_start') and sync_request.get('period_end'):
            return self._generate_periods_from_dates(
                sync_request['period_start'],
                sync_request['period_end']
            )
        else:
            # Use current assessment period
            current_period = AssessmentPeriod.objects.filter(is_current=True).first()
            if current_period:
                return [current_period.period]
            else:
                return []
    
    def _generate_periods_from_dates(self, start_date, end_date):
        """Generate periods from date range"""
        periods = []
        current_date = start_date
        
        while current_date <= end_date:
            # Generate period in DHIS2 format (YYYYMM)
            period = current_date.strftime('%Y%m')
            periods.append(period)
            
            # Move to next month
            if current_date.month == 12:
                current_date = current_date.replace(year=current_date.year + 1, month=1)
            else:
                current_date = current_date.replace(month=current_date.month + 1)
        
        return periods
    
    def _sync_indicator_data(self, indicator, org_units, periods, sync_log):
        """Sync data for a specific indicator"""
        total_points = 0
        
        for org_unit in org_units:
            for period in periods:
                try:
                    data_value = self._fetch_indicator_data(indicator, org_unit.dhis2_uid, period)
                    
                    if data_value is not None:
                        # Create or update indicator data
                        indicator_data, created = IndicatorData.objects.update_or_create(
                            indicator=indicator,
                            org_unit_id=org_unit.id,
                            period=period,
                            defaults={
                                'value': data_value,
                                'last_synced': timezone.now()
                            }
                        )
                        total_points += 1
                        
                except Exception as e:
                    logger.error(f"Failed to sync data for {indicator.name} at {org_unit.name} for {period}: {str(e)}")
        
        return total_points
    
    def _fetch_indicator_data(self, indicator, org_unit_id, period):
        """Fetch indicator data from DHIS2"""
        try:
            # Build analytics query
            query_params = {
                'dimension': f'dx:{indicator.dhis2_uid}',
                'dimension': f'ou:{org_unit_id}',
                'dimension': f'pe:{period}',
                'displayProperty': 'NAME'
            }
            
            # Make request to DHIS2 analytics API
            response = self.client.get_analytics(query_params)
            
            if response and 'rows' in response:
                for row in response['rows']:
                    if len(row) >= 4:  # dx, ou, pe, value
                        return float(row[3]) if row[3] else None
            
            return None
            
        except Exception as e:
            logger.error(f"Error fetching data for indicator {indicator.dhis2_uid}: {str(e)}")
            return None
    
    def _trigger_score_calculation(self, sync_log):
        """Trigger score calculation for synced data"""
        try:
            calculation_service = ScoreCalculationService()
            
            # Get unique org units and periods from sync log
            org_units = set()
            periods = set()
            
            # Extract org units and periods from synced data
            synced_data = IndicatorData.objects.filter(
                last_synced__gte=sync_log.started_at
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
                # Get scoring rule for this indicator
                scoring_rule = ScoringRule.objects.filter(
                    indicator_type=data.indicator.indicator_type
                ).first()
                
                if not scoring_rule:
                    continue
                
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
                
                # Create or update indicator score
                indicator_score, created = IndicatorScore.objects.update_or_create(
                    indicator=data.indicator,
                    org_unit_id=org_unit_id,
                    assessment_period=assessment_period,
                    defaults={
                        'raw_value': data.value,
                        'score': score,
                        'trend': trend,
                        'color': scoring_rule.get_color_for_score(score),
                        'label': scoring_rule.get_label_for_score(score),
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
                # Get indicator scores for this objective
                indicator_scores = IndicatorScore.objects.filter(
                    org_unit_id=org_unit_id,
                    assessment_period=assessment_period,
                    indicator__objectives=objective
                )
                
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
                    
                    if weight:
                        total_weight += weight.weight
                        weighted_sum += score.score * weight.weight
                
                if total_weight > 0:
                    objective_score_value = weighted_sum / total_weight
                else:
                    # Use median if no weights defined
                    scores = list(indicator_scores.values_list('score', flat=True))
                    scores.sort()
                    objective_score_value = scores[len(scores) // 2] if scores else 0
                
                # Get scoring rule for objectives
                scoring_rule = ScoringRule.objects.filter(
                    rule_type='objective'
                ).first()
                
                if scoring_rule:
                    color = scoring_rule.get_color_for_score(objective_score_value)
                    label = scoring_rule.get_label_for_score(objective_score_value)
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
                color = scoring_rule.get_color_for_score(sector_score_value)
                label = scoring_rule.get_label_for_score(sector_score_value)
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
        
        # Apply scoring rule
        return scoring_rule.evaluate_score(gap_percentage)
    
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
                'raw_value': score.raw_value,
                'score': score.score,
                'trend': score.trend,
                'color': score.color,
                'label': score.label
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
                    'raw_value': score.raw_value,
                    'score': score.score,
                    'trend': score.trend,
                    'color': score.color,
                    'label': score.label
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