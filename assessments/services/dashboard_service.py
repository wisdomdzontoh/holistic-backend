"""
Dashboard Service

This module handles dashboard functionality and data aggregation.
"""

import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from django.conf import settings
from django.utils import timezone
from django.db.models import Avg, Count, Max, Min, Q

from ..models import SavedAssessment, TrackedIndicator
from .validation_service import ValidationService
from .cache_service import CacheService
from .data_processing_service import DataProcessingService

logger = logging.getLogger(__name__)


class DashboardService:
    """
    Service for dashboard functionality and data aggregation.
    
    This service handles dashboard metrics, trends, comparisons,
    and data visualization for assessments.
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.validation_service = ValidationService()
        self.cache_service = CacheService()
        self.data_processor = DataProcessingService()
    
    async def get_dashboard_overview(self, user_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Get dashboard overview with key metrics.
        
        Args:
            user_id: Optional user ID to filter by
            
        Returns:
            Dashboard overview data
        """
        try:
            # Get basic metrics
            metrics = await self._get_basic_metrics(user_id)
            
            # Get recent activity
            recent_activity = await self._get_recent_activity(user_id)
            
            # Get performance trends
            performance_trends = await self._get_performance_trends(user_id)
            
            # Get top performers
            top_performers = await self._get_top_performers(user_id)
            
            return {
                'metrics': metrics,
                'recent_activity': recent_activity,
                'performance_trends': performance_trends,
                'top_performers': top_performers,
                'generated_at': timezone.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Error getting dashboard overview: {str(e)}")
            raise
    
    async def _get_basic_metrics(self, user_id: Optional[int] = None) -> Dict[str, Any]:
        """Get basic dashboard metrics."""
        try:
            queryset = SavedAssessment.objects
            
            if user_id:
                queryset = queryset.filter(created_by_id=user_id)
            
            # Total assessments
            total_assessments = await queryset.acount()
            
            # Recent assessments (last 30 days)
            recent_assessments = await queryset.filter(
                created_at__gte=timezone.now() - timedelta(days=30)
            ).acount()
            
            # Average score
            avg_score = await self._calculate_average_score(queryset)
            
            # Unique organization units
            unique_org_units = await queryset.values('org_unit_id').distinct().acount()
            
            # Unique periods
            unique_periods = await queryset.values('period').distinct().acount()
            
            return {
                'total_assessments': total_assessments,
                'recent_assessments': recent_assessments,
                'average_score': avg_score,
                'unique_org_units': unique_org_units,
                'unique_periods': unique_periods
            }
            
        except Exception as e:
            self.logger.error(f"Error getting basic metrics: {str(e)}")
            return {
                'total_assessments': 0,
                'recent_assessments': 0,
                'average_score': 0,
                'unique_org_units': 0,
                'unique_periods': 0
            }
    
    async def _calculate_average_score(self, queryset) -> float:
        """Calculate average score from assessments."""
        try:
            # This would need to be implemented based on your data structure
            # For now, return a placeholder
            return 75.5
            
        except Exception as e:
            self.logger.error(f"Error calculating average score: {str(e)}")
            return 0.0
    
    async def _get_recent_activity(self, user_id: Optional[int] = None, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent assessment activity."""
        try:
            queryset = SavedAssessment.objects.select_related('created_by')
            
            if user_id:
                queryset = queryset.filter(created_by_id=user_id)
            
            recent_assessments = await queryset.order_by('-created_at')[:limit].values(
                'id', 'name', 'org_unit_name', 'period', 'created_at', 'created_by__username'
            )
            
            return list(recent_assessments)
            
        except Exception as e:
            self.logger.error(f"Error getting recent activity: {str(e)}")
            return []
    
    async def _get_performance_trends(self, user_id: Optional[int] = None, days: int = 90) -> List[Dict[str, Any]]:
        """Get performance trends over time."""
        try:
            # This would analyze assessment scores over time
            # For now, return placeholder data
            trends = []
            end_date = timezone.now()
            start_date = end_date - timedelta(days=days)
            
            # Generate sample trend data
            current_date = start_date
            while current_date <= end_date:
                trends.append({
                    'date': current_date.strftime('%Y-%m-%d'),
                    'average_score': 70 + (current_date.day % 20),  # Sample variation
                    'assessment_count': 1 + (current_date.day % 5)
                })
                current_date += timedelta(days=7)  # Weekly data points
            
            return trends
            
        except Exception as e:
            self.logger.error(f"Error getting performance trends: {str(e)}")
            return []
    
    async def _get_top_performers(self, user_id: Optional[int] = None, limit: int = 5) -> List[Dict[str, Any]]:
        """Get top performing organization units."""
        try:
            # This would analyze performance across organization units
            # For now, return placeholder data
            return [
                {
                    'org_unit_name': 'Organization A',
                    'average_score': 85.2,
                    'assessment_count': 12
                },
                {
                    'org_unit_name': 'Organization B',
                    'average_score': 82.1,
                    'assessment_count': 8
                },
                {
                    'org_unit_name': 'Organization C',
                    'average_score': 78.9,
                    'assessment_count': 15
                }
            ]
            
        except Exception as e:
            self.logger.error(f"Error getting top performers: {str(e)}")
            return []
    
    async def get_assessment_analytics(self, org_unit_id: Optional[str] = None,
                                    period: Optional[str] = None,
                                    user_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Get detailed analytics for assessments.
        
        Args:
            org_unit_id: Optional organization unit ID to filter by
            period: Optional period to filter by
            user_id: Optional user ID to filter by
            
        Returns:
            Assessment analytics data
        """
        try:
            queryset = SavedAssessment.objects
            
            # Apply filters
            if org_unit_id:
                queryset = queryset.filter(org_unit_id=org_unit_id)
            if period:
                queryset = queryset.filter(period=period)
            if user_id:
                queryset = queryset.filter(created_by_id=user_id)
            
            # Get analytics data
            analytics = {
                'total_assessments': await queryset.acount(),
                'score_distribution': await self._get_score_distribution(queryset),
                'period_analysis': await self._get_period_analysis(queryset),
                'org_unit_analysis': await self._get_org_unit_analysis(queryset),
                'trend_analysis': await self._get_trend_analysis(queryset)
            }
            
            return analytics
            
        except Exception as e:
            self.logger.error(f"Error getting assessment analytics: {str(e)}")
            raise
    
    async def _get_score_distribution(self, queryset) -> Dict[str, Any]:
        """Get score distribution analysis."""
        try:
            # This would analyze score ranges and distribution
            # For now, return placeholder data
            return {
                'excellent': 15,  # 90-100%
                'good': 25,       # 80-89%
                'satisfactory': 35, # 70-79%
                'needs_improvement': 20, # 60-69%
                'poor': 5         # <60%
            }
            
        except Exception as e:
            self.logger.error(f"Error getting score distribution: {str(e)}")
            return {}
    
    async def _get_period_analysis(self, queryset) -> List[Dict[str, Any]]:
        """Get analysis by period."""
        try:
            # This would analyze performance across different periods
            # For now, return placeholder data
            return [
                {
                    'period': '2024Q1',
                    'average_score': 78.5,
                    'assessment_count': 45
                },
                {
                    'period': '2024Q2',
                    'average_score': 82.1,
                    'assessment_count': 52
                },
                {
                    'period': '2024Q3',
                    'average_score': 79.8,
                    'assessment_count': 38
                }
            ]
            
        except Exception as e:
            self.logger.error(f"Error getting period analysis: {str(e)}")
            return []
    
    async def _get_org_unit_analysis(self, queryset) -> List[Dict[str, Any]]:
        """Get analysis by organization unit."""
        try:
            # This would analyze performance across organization units
            # For now, return placeholder data
            return [
                {
                    'org_unit_name': 'Central Region',
                    'average_score': 81.2,
                    'assessment_count': 25
                },
                {
                    'org_unit_name': 'Eastern Region',
                    'average_score': 76.8,
                    'assessment_count': 18
                },
                {
                    'org_unit_name': 'Western Region',
                    'average_score': 79.5,
                    'assessment_count': 22
                }
            ]
            
        except Exception as e:
            self.logger.error(f"Error getting org unit analysis: {str(e)}")
            return []
    
    async def _get_trend_analysis(self, queryset) -> Dict[str, Any]:
        """Get trend analysis over time."""
        try:
            # This would analyze trends in performance over time
            # For now, return placeholder data
            return {
                'overall_trend': 'improving',
                'trend_strength': 'moderate',
                'key_insights': [
                    'Average scores have improved by 5% over the last quarter',
                    'More consistent performance across organization units',
                    'Reduced variance in assessment scores'
                ]
            }
            
        except Exception as e:
            self.logger.error(f"Error getting trend analysis: {str(e)}")
            return {}
    
    async def get_comparison_data(self, org_unit_ids: List[str], 
                                period: str) -> Dict[str, Any]:
        """
        Get comparison data between organization units.
        
        Args:
            org_unit_ids: List of organization unit IDs to compare
            period: Period for comparison
            
        Returns:
            Comparison data
        """
        try:
            comparison_data = {
                'period': period,
                'org_units': [],
                'comparison_metrics': {}
            }
            
            for org_unit_id in org_unit_ids:
                org_unit_data = await self._get_org_unit_comparison_data(org_unit_id, period)
                comparison_data['org_units'].append(org_unit_data)
            
            # Calculate comparison metrics
            comparison_data['comparison_metrics'] = await self._calculate_comparison_metrics(
                comparison_data['org_units']
            )
            
            return comparison_data
            
        except Exception as e:
            self.logger.error(f"Error getting comparison data: {str(e)}")
            raise
    
    async def _get_org_unit_comparison_data(self, org_unit_id: str, period: str) -> Dict[str, Any]:
        """Get comparison data for a single organization unit."""
        try:
            # This would get detailed data for the organization unit
            # For now, return placeholder data
            return {
                'org_unit_id': org_unit_id,
                'org_unit_name': f'Organization {org_unit_id}',
                'average_score': 75 + (hash(org_unit_id) % 20),  # Sample variation
                'assessment_count': 10 + (hash(org_unit_id) % 10),
                'performance_rank': 1 + (hash(org_unit_id) % 5),
                'key_indicators': [
                    {'name': 'Indicator 1', 'score': 80},
                    {'name': 'Indicator 2', 'score': 75},
                    {'name': 'Indicator 3', 'score': 85}
                ]
            }
            
        except Exception as e:
            self.logger.error(f"Error getting org unit comparison data: {str(e)}")
            return {}
    
    async def _calculate_comparison_metrics(self, org_units: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate comparison metrics between organization units."""
        try:
            if not org_units:
                return {}
            
            scores = [unit.get('average_score', 0) for unit in org_units]
            
            return {
                'highest_score': max(scores),
                'lowest_score': min(scores),
                'score_range': max(scores) - min(scores),
                'average_score': sum(scores) / len(scores),
                'performance_gap': max(scores) - min(scores)
            }
            
        except Exception as e:
            self.logger.error(f"Error calculating comparison metrics: {str(e)}")
            return {}
    
    async def get_dashboard_widgets(self, user_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Get dashboard widgets configuration and data.
        
        Args:
            user_id: Optional user ID to filter by
            
        Returns:
            List of dashboard widgets
        """
        try:
            widgets = [
                {
                    'id': 'recent_assessments',
                    'type': 'list',
                    'title': 'Recent Assessments',
                    'data': await self._get_recent_activity(user_id, 5)
                },
                {
                    'id': 'performance_trend',
                    'type': 'chart',
                    'title': 'Performance Trend',
                    'data': await self._get_performance_trends(user_id, 30)
                },
                {
                    'id': 'top_performers',
                    'type': 'ranking',
                    'title': 'Top Performers',
                    'data': await self._get_top_performers(user_id, 3)
                },
                {
                    'id': 'quick_stats',
                    'type': 'metrics',
                    'title': 'Quick Statistics',
                    'data': await self._get_basic_metrics(user_id)
                }
            ]
            
            return widgets
            
        except Exception as e:
            self.logger.error(f"Error getting dashboard widgets: {str(e)}")
            return []
    
    async def get_user_dashboard_preferences(self, user_id: int) -> Dict[str, Any]:
        """
        Get user's dashboard preferences.
        
        Args:
            user_id: User ID
            
        Returns:
            User dashboard preferences
        """
        try:
            # This would retrieve user preferences from the database
            # For now, return default preferences
            return {
                'layout': 'grid',
                'widgets': ['recent_assessments', 'performance_trend', 'top_performers', 'quick_stats'],
                'refresh_interval': 300,  # 5 minutes
                'theme': 'light'
            }
            
        except Exception as e:
            self.logger.error(f"Error getting user dashboard preferences: {str(e)}")
            return {}
    
    async def update_user_dashboard_preferences(self, user_id: int, 
                                              preferences: Dict[str, Any]) -> bool:
        """
        Update user's dashboard preferences.
        
        Args:
            user_id: User ID
            preferences: New preferences
            
        Returns:
            True if update was successful
        """
        try:
            # This would save user preferences to the database
            # For now, just log the action
            self.logger.info(f"Updated dashboard preferences for user {user_id}: {preferences}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error updating user dashboard preferences: {str(e)}")
            return False
    
    async def export_dashboard_data(self, dashboard_type: str, 
                                  filters: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Export dashboard data for reporting.
        
        Args:
            dashboard_type: Type of dashboard data to export
            filters: Optional filters to apply
            
        Returns:
            Exported dashboard data
        """
        try:
            if dashboard_type == 'overview':
                data = await self.get_dashboard_overview(filters.get('user_id'))
            elif dashboard_type == 'analytics':
                data = await self.get_assessment_analytics(
                    filters.get('org_unit_id'),
                    filters.get('period'),
                    filters.get('user_id')
                )
            elif dashboard_type == 'comparison':
                data = await self.get_comparison_data(
                    filters.get('org_unit_ids', []),
                    filters.get('period')
                )
            else:
                raise ValueError(f"Unknown dashboard type: {dashboard_type}")
            
            return {
                'dashboard_type': dashboard_type,
                'filters': filters,
                'data': data,
                'exported_at': timezone.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Error exporting dashboard data: {str(e)}")
            raise
