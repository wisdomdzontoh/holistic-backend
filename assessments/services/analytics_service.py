"""
Analytics Service

This module handles advanced analytics and reporting functionality.
"""

import logging
import json
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from django.conf import settings
from django.utils import timezone
from django.db.models import Avg, Count, Max, Min, Q, Sum
from django.db.models.functions import TruncDate, TruncMonth, TruncQuarter

from ..models import SavedAssessment, TrackedIndicator
from .validation_service import ValidationService
from .cache_service import CacheService
from .data_processing_service import DataProcessingService

logger = logging.getLogger(__name__)


class AnalyticsService:
    """
    Service for advanced analytics and reporting functionality.
    
    This service handles complex data analysis, trend detection,
    predictive analytics, and advanced reporting features.
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.validation_service = ValidationService()
        self.cache_service = CacheService()
        self.data_processor = DataProcessingService()
    
    async def generate_comprehensive_report(self, filters: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Generate a comprehensive analytics report.
        
        Args:
            filters: Optional filters to apply to the analysis
            
        Returns:
            Comprehensive report data
        """
        try:
            # Apply filters to base queryset
            base_queryset = self._apply_filters(SavedAssessment.objects, filters)
            
            # Generate different sections of the report
            report = {
                'executive_summary': await self._generate_executive_summary(base_queryset),
                'performance_analysis': await self._generate_performance_analysis(base_queryset),
                'trend_analysis': await self._generate_trend_analysis(base_queryset),
                'comparative_analysis': await self._generate_comparative_analysis(base_queryset),
                'predictive_insights': await self._generate_predictive_insights(base_queryset),
                'recommendations': await self._generate_recommendations(base_queryset),
                'metadata': {
                    'generated_at': timezone.now().isoformat(),
                    'filters_applied': filters or {},
                    'data_points_analyzed': await base_queryset.acount()
                }
            }
            
            return report
            
        except Exception as e:
            self.logger.error(f"Error generating comprehensive report: {str(e)}")
            raise
    
    def _apply_filters(self, queryset, filters: Optional[Dict[str, Any]]):
        """Apply filters to the base queryset."""
        if not filters:
            return queryset
        
        try:
            if filters.get('org_unit_id'):
                queryset = queryset.filter(org_unit_id=filters['org_unit_id'])
            
            if filters.get('period'):
                queryset = queryset.filter(period=filters['period'])
            
            if filters.get('user_id'):
                queryset = queryset.filter(created_by_id=filters['user_id'])
            
            if filters.get('date_from'):
                queryset = queryset.filter(created_at__gte=filters['date_from'])
            
            if filters.get('date_to'):
                queryset = queryset.filter(created_at__lte=filters['date_to'])
            
            return queryset
            
        except Exception as e:
            self.logger.error(f"Error applying filters: {str(e)}")
            return queryset
    
    async def _generate_executive_summary(self, queryset) -> Dict[str, Any]:
        """Generate executive summary section."""
        try:
            total_assessments = await queryset.acount()
            
            # Calculate key metrics
            recent_assessments = await queryset.filter(
                created_at__gte=timezone.now() - timedelta(days=30)
            ).acount()
            
            # Get average score (placeholder)
            avg_score = 78.5
            
            # Get performance trend
            trend = await self._calculate_performance_trend(queryset)
            
            return {
                'total_assessments': total_assessments,
                'recent_assessments': recent_assessments,
                'average_score': avg_score,
                'performance_trend': trend,
                'key_highlights': [
                    f"Total of {total_assessments} assessments analyzed",
                    f"Average performance score: {avg_score}%",
                    f"Performance trend: {trend['direction']}",
                    f"{recent_assessments} assessments in the last 30 days"
                ]
            }
            
        except Exception as e:
            self.logger.error(f"Error generating executive summary: {str(e)}")
            return {}
    
    async def _generate_performance_analysis(self, queryset) -> Dict[str, Any]:
        """Generate detailed performance analysis."""
        try:
            # Score distribution analysis
            score_distribution = await self._analyze_score_distribution(queryset)
            
            # Performance by organization unit
            org_unit_performance = await self._analyze_org_unit_performance(queryset)
            
            # Performance by period
            period_performance = await self._analyze_period_performance(queryset)
            
            # Performance by indicator category
            category_performance = await self._analyze_category_performance(queryset)
            
            return {
                'score_distribution': score_distribution,
                'org_unit_performance': org_unit_performance,
                'period_performance': period_performance,
                'category_performance': category_performance,
                'performance_insights': await self._generate_performance_insights(queryset)
            }
            
        except Exception as e:
            self.logger.error(f"Error generating performance analysis: {str(e)}")
            return {}
    
    async def _analyze_score_distribution(self, queryset) -> Dict[str, Any]:
        """Analyze distribution of scores."""
        try:
            # This would analyze actual score data
            # For now, return placeholder data
            return {
                'excellent': {'count': 15, 'percentage': 15},
                'good': {'count': 25, 'percentage': 25},
                'satisfactory': {'count': 35, 'percentage': 35},
                'needs_improvement': {'count': 20, 'percentage': 20},
                'poor': {'count': 5, 'percentage': 5}
            }
            
        except Exception as e:
            self.logger.error(f"Error analyzing score distribution: {str(e)}")
            return {}
    
    async def _analyze_org_unit_performance(self, queryset) -> List[Dict[str, Any]]:
        """Analyze performance by organization unit."""
        try:
            # This would analyze actual org unit performance data
            # For now, return placeholder data
            return [
                {
                    'org_unit_name': 'Central Region',
                    'average_score': 81.2,
                    'assessment_count': 25,
                    'performance_rank': 1,
                    'trend': 'improving'
                },
                {
                    'org_unit_name': 'Eastern Region',
                    'average_score': 76.8,
                    'assessment_count': 18,
                    'performance_rank': 2,
                    'trend': 'stable'
                },
                {
                    'org_unit_name': 'Western Region',
                    'average_score': 79.5,
                    'assessment_count': 22,
                    'performance_rank': 3,
                    'trend': 'improving'
                }
            ]
            
        except Exception as e:
            self.logger.error(f"Error analyzing org unit performance: {str(e)}")
            return []
    
    async def _analyze_period_performance(self, queryset) -> List[Dict[str, Any]]:
        """Analyze performance by period."""
        try:
            # This would analyze actual period performance data
            # For now, return placeholder data
            return [
                {
                    'period': '2024Q1',
                    'average_score': 78.5,
                    'assessment_count': 45,
                    'trend': 'stable'
                },
                {
                    'period': '2024Q2',
                    'average_score': 82.1,
                    'assessment_count': 52,
                    'trend': 'improving'
                },
                {
                    'period': '2024Q3',
                    'average_score': 79.8,
                    'assessment_count': 38,
                    'trend': 'declining'
                }
            ]
            
        except Exception as e:
            self.logger.error(f"Error analyzing period performance: {str(e)}")
            return []
    
    async def _analyze_category_performance(self, queryset) -> List[Dict[str, Any]]:
        """Analyze performance by indicator category."""
        try:
            # This would analyze actual category performance data
            # For now, return placeholder data
            return [
                {
                    'category': 'Health',
                    'average_score': 82.5,
                    'indicator_count': 15,
                    'performance_rank': 1
                },
                {
                    'category': 'Education',
                    'average_score': 78.2,
                    'indicator_count': 12,
                    'performance_rank': 2
                },
                {
                    'category': 'Infrastructure',
                    'average_score': 75.8,
                    'indicator_count': 10,
                    'performance_rank': 3
                }
            ]
            
        except Exception as e:
            self.logger.error(f"Error analyzing category performance: {str(e)}")
            return []
    
    async def _generate_performance_insights(self, queryset) -> List[str]:
        """Generate insights from performance analysis."""
        try:
            # This would generate insights based on actual analysis
            # For now, return placeholder insights
            return [
                "Central Region shows the highest performance with an average score of 81.2%",
                "Education category has the most indicators but shows room for improvement",
                "Q2 2024 showed the best performance across all regions",
                "Infrastructure indicators consistently score lower than other categories"
            ]
            
        except Exception as e:
            self.logger.error(f"Error generating performance insights: {str(e)}")
            return []
    
    async def _generate_trend_analysis(self, queryset) -> Dict[str, Any]:
        """Generate trend analysis section."""
        try:
            # Time series analysis
            time_series = await self._analyze_time_series(queryset)
            
            # Trend detection
            trends = await self._detect_trends(queryset)
            
            # Seasonal patterns
            seasonal_patterns = await self._analyze_seasonal_patterns(queryset)
            
            return {
                'time_series_analysis': time_series,
                'trend_detection': trends,
                'seasonal_patterns': seasonal_patterns,
                'trend_insights': await self._generate_trend_insights(queryset)
            }
            
        except Exception as e:
            self.logger.error(f"Error generating trend analysis: {str(e)}")
            return {}
    
    async def _analyze_time_series(self, queryset) -> List[Dict[str, Any]]:
        """Analyze time series data."""
        try:
            # This would analyze actual time series data
            # For now, return placeholder data
            time_series = []
            end_date = timezone.now()
            start_date = end_date - timedelta(days=90)
            
            current_date = start_date
            while current_date <= end_date:
                time_series.append({
                    'date': current_date.strftime('%Y-%m-%d'),
                    'average_score': 75 + (current_date.day % 15),
                    'assessment_count': 1 + (current_date.day % 3),
                    'trend': 'stable' if current_date.day % 2 == 0 else 'improving'
                })
                current_date += timedelta(days=7)
            
            return time_series
            
        except Exception as e:
            self.logger.error(f"Error analyzing time series: {str(e)}")
            return []
    
    async def _detect_trends(self, queryset) -> Dict[str, Any]:
        """Detect trends in the data."""
        try:
            # This would implement actual trend detection algorithms
            # For now, return placeholder data
            return {
                'overall_trend': 'improving',
                'trend_strength': 'moderate',
                'trend_duration': '3 months',
                'confidence_level': 0.85,
                'key_trends': [
                    'Gradual improvement in overall performance',
                    'Increasing consistency across regions',
                    'Reduced variance in assessment scores'
                ]
            }
            
        except Exception as e:
            self.logger.error(f"Error detecting trends: {str(e)}")
            return {}
    
    async def _analyze_seasonal_patterns(self, queryset) -> Dict[str, Any]:
        """Analyze seasonal patterns in the data."""
        try:
            # This would implement seasonal pattern analysis
            # For now, return placeholder data
            return {
                'has_seasonal_patterns': True,
                'seasonal_strength': 'moderate',
                'peak_periods': ['Q2', 'Q4'],
                'low_periods': ['Q1', 'Q3'],
                'seasonal_insights': [
                    'Performance peaks in Q2 and Q4',
                    'Lower performance in Q1 and Q3',
                    'Consistent seasonal pattern over multiple years'
                ]
            }
            
        except Exception as e:
            self.logger.error(f"Error analyzing seasonal patterns: {str(e)}")
            return {}
    
    async def _generate_trend_insights(self, queryset) -> List[str]:
        """Generate insights from trend analysis."""
        try:
            # This would generate insights based on actual trend analysis
            # For now, return placeholder insights
            return [
                "Overall performance shows a moderate improving trend over the last 3 months",
                "Seasonal patterns indicate higher performance in Q2 and Q4",
                "Regional performance is becoming more consistent over time",
                "Assessment frequency has increased by 15% in recent months"
            ]
            
        except Exception as e:
            self.logger.error(f"Error generating trend insights: {str(e)}")
            return []
    
    async def _generate_comparative_analysis(self, queryset) -> Dict[str, Any]:
        """Generate comparative analysis section."""
        try:
            # Benchmark analysis
            benchmarks = await self._analyze_benchmarks(queryset)
            
            # Peer comparison
            peer_comparison = await self._analyze_peer_comparison(queryset)
            
            # Historical comparison
            historical_comparison = await self._analyze_historical_comparison(queryset)
            
            return {
                'benchmark_analysis': benchmarks,
                'peer_comparison': peer_comparison,
                'historical_comparison': historical_comparison,
                'comparative_insights': await self._generate_comparative_insights(queryset)
            }
            
        except Exception as e:
            self.logger.error(f"Error generating comparative analysis: {str(e)}")
            return {}
    
    async def _analyze_benchmarks(self, queryset) -> Dict[str, Any]:
        """Analyze performance against benchmarks."""
        try:
            # This would analyze actual benchmark data
            # For now, return placeholder data
            return {
                'industry_average': 75.0,
                'best_practice': 85.0,
                'current_performance': 78.5,
                'gap_to_best_practice': 6.5,
                'benchmark_rank': 'above_average',
                'benchmark_insights': [
                    'Current performance is above industry average',
                    'Gap to best practice is 6.5 percentage points',
                    'Performance ranks in the top 30% of similar organizations'
                ]
            }
            
        except Exception as e:
            self.logger.error(f"Error analyzing benchmarks: {str(e)}")
            return {}
    
    async def _analyze_peer_comparison(self, queryset) -> List[Dict[str, Any]]:
        """Analyze peer comparison data."""
        try:
            # This would analyze actual peer comparison data
            # For now, return placeholder data
            return [
                {
                    'peer_name': 'Peer Organization A',
                    'average_score': 82.1,
                    'performance_rank': 1,
                    'strengths': ['Health indicators', 'Consistent performance'],
                    'areas_for_improvement': ['Infrastructure indicators']
                },
                {
                    'peer_name': 'Peer Organization B',
                    'average_score': 79.8,
                    'performance_rank': 2,
                    'strengths': ['Education indicators', 'Innovation'],
                    'areas_for_improvement': ['Health indicators']
                }
            ]
            
        except Exception as e:
            self.logger.error(f"Error analyzing peer comparison: {str(e)}")
            return []
    
    async def _analyze_historical_comparison(self, queryset) -> Dict[str, Any]:
        """Analyze historical comparison data."""
        try:
            # This would analyze actual historical data
            # For now, return placeholder data
            return {
                'year_over_year_change': 5.2,
                'quarter_over_quarter_change': 2.1,
                'month_over_month_change': 0.8,
                'historical_trend': 'improving',
                'historical_insights': [
                    '5.2% improvement year-over-year',
                    'Consistent quarter-over-quarter growth',
                    'Stable month-over-month performance'
                ]
            }
            
        except Exception as e:
            self.logger.error(f"Error analyzing historical comparison: {str(e)}")
            return {}
    
    async def _generate_comparative_insights(self, queryset) -> List[str]:
        """Generate insights from comparative analysis."""
        try:
            # This would generate insights based on actual comparative analysis
            # For now, return placeholder insights
            return [
                "Performance is above industry average by 3.5 percentage points",
                "Peer comparison shows strong performance in health indicators",
                "Year-over-year improvement of 5.2% indicates positive trajectory",
                "Benchmark analysis suggests focus on infrastructure indicators"
            ]
            
        except Exception as e:
            self.logger.error(f"Error generating comparative insights: {str(e)}")
            return []
    
    async def _generate_predictive_insights(self, queryset) -> Dict[str, Any]:
        """Generate predictive insights section."""
        try:
            # Performance forecasting
            performance_forecast = await self._forecast_performance(queryset)
            
            # Risk assessment
            risk_assessment = await self._assess_risks(queryset)
            
            # Opportunity identification
            opportunities = await self._identify_opportunities(queryset)
            
            return {
                'performance_forecast': performance_forecast,
                'risk_assessment': risk_assessment,
                'opportunities': opportunities,
                'predictive_insights': await self._generate_predictive_insights_list(queryset)
            }
            
        except Exception as e:
            self.logger.error(f"Error generating predictive insights: {str(e)}")
            return {}
    
    async def _forecast_performance(self, queryset) -> Dict[str, Any]:
        """Forecast future performance."""
        try:
            # This would implement actual forecasting algorithms
            # For now, return placeholder data
            return {
                'next_quarter_forecast': 80.5,
                'next_year_forecast': 83.2,
                'forecast_confidence': 0.78,
                'forecast_factors': [
                    'Historical trend analysis',
                    'Seasonal pattern consideration',
                    'Current performance momentum'
                ],
                'forecast_insights': [
                    'Expected 2% improvement in next quarter',
                    'Projected 5% improvement over next year',
                    'High confidence in positive trajectory'
                ]
            }
            
        except Exception as e:
            self.logger.error(f"Error forecasting performance: {str(e)}")
            return {}
    
    async def _assess_risks(self, queryset) -> Dict[str, Any]:
        """Assess potential risks."""
        try:
            # This would implement actual risk assessment
            # For now, return placeholder data
            return {
                'high_risks': [
                    'Declining performance in infrastructure indicators',
                    'Increasing variance in regional performance'
                ],
                'medium_risks': [
                    'Potential seasonal performance decline in Q3',
                    'Resource constraints affecting assessment frequency'
                ],
                'low_risks': [
                    'Minor fluctuations in education indicators',
                    'Temporary data quality issues'
                ],
                'risk_mitigation': [
                    'Focus on infrastructure improvement initiatives',
                    'Implement regional performance monitoring',
                    'Develop seasonal performance strategies'
                ]
            }
            
        except Exception as e:
            self.logger.error(f"Error assessing risks: {str(e)}")
            return {}
    
    async def _identify_opportunities(self, queryset) -> List[Dict[str, Any]]:
        """Identify improvement opportunities."""
        try:
            # This would implement actual opportunity identification
            # For now, return placeholder data
            return [
                {
                    'opportunity': 'Infrastructure improvement',
                    'potential_impact': 'high',
                    'effort_required': 'medium',
                    'timeline': '6 months',
                    'description': 'Focus on infrastructure indicators to improve overall performance'
                },
                {
                    'opportunity': 'Regional collaboration',
                    'potential_impact': 'medium',
                    'effort_required': 'low',
                    'timeline': '3 months',
                    'description': 'Share best practices between regions'
                },
                {
                    'opportunity': 'Assessment optimization',
                    'potential_impact': 'medium',
                    'effort_required': 'low',
                    'timeline': '2 months',
                    'description': 'Optimize assessment processes for better efficiency'
                }
            ]
            
        except Exception as e:
            self.logger.error(f"Error identifying opportunities: {str(e)}")
            return []
    
    async def _generate_predictive_insights_list(self, queryset) -> List[str]:
        """Generate list of predictive insights."""
        try:
            # This would generate insights based on actual predictive analysis
            # For now, return placeholder insights
            return [
                "Performance is expected to improve by 2% in the next quarter",
                "Infrastructure indicators pose the highest risk to overall performance",
                "Regional collaboration opportunities could improve performance by 3-5%",
                "Seasonal patterns suggest Q3 may require additional focus"
            ]
            
        except Exception as e:
            self.logger.error(f"Error generating predictive insights list: {str(e)}")
            return []
    
    async def _generate_recommendations(self, queryset) -> Dict[str, Any]:
        """Generate actionable recommendations."""
        try:
            # Strategic recommendations
            strategic_recommendations = await self._generate_strategic_recommendations(queryset)
            
            # Tactical recommendations
            tactical_recommendations = await self._generate_tactical_recommendations(queryset)
            
            # Operational recommendations
            operational_recommendations = await self._generate_operational_recommendations(queryset)
            
            return {
                'strategic_recommendations': strategic_recommendations,
                'tactical_recommendations': tactical_recommendations,
                'operational_recommendations': operational_recommendations,
                'priority_actions': await self._generate_priority_actions(queryset)
            }
            
        except Exception as e:
            self.logger.error(f"Error generating recommendations: {str(e)}")
            return {}
    
    async def _generate_strategic_recommendations(self, queryset) -> List[Dict[str, Any]]:
        """Generate strategic recommendations."""
        try:
            # This would generate actual strategic recommendations
            # For now, return placeholder data
            return [
                {
                    'recommendation': 'Develop comprehensive infrastructure improvement plan',
                    'rationale': 'Infrastructure indicators consistently underperform',
                    'expected_impact': '5-8% improvement in overall performance',
                    'timeline': '12 months',
                    'priority': 'high'
                },
                {
                    'recommendation': 'Implement regional performance sharing program',
                    'rationale': 'Significant performance variance between regions',
                    'expected_impact': '3-5% improvement in regional consistency',
                    'timeline': '6 months',
                    'priority': 'medium'
                }
            ]
            
        except Exception as e:
            self.logger.error(f"Error generating strategic recommendations: {str(e)}")
            return []
    
    async def _generate_tactical_recommendations(self, queryset) -> List[Dict[str, Any]]:
        """Generate tactical recommendations."""
        try:
            # This would generate actual tactical recommendations
            # For now, return placeholder data
            return [
                {
                    'recommendation': 'Increase assessment frequency for underperforming indicators',
                    'rationale': 'More frequent monitoring can identify issues early',
                    'expected_impact': '2-3% improvement in problem areas',
                    'timeline': '3 months',
                    'priority': 'medium'
                },
                {
                    'recommendation': 'Develop targeted training programs for low-performing regions',
                    'rationale': 'Knowledge gaps identified in certain regions',
                    'expected_impact': '4-6% improvement in regional performance',
                    'timeline': '4 months',
                    'priority': 'medium'
                }
            ]
            
        except Exception as e:
            self.logger.error(f"Error generating tactical recommendations: {str(e)}")
            return []
    
    async def _generate_operational_recommendations(self, queryset) -> List[Dict[str, Any]]:
        """Generate operational recommendations."""
        try:
            # This would generate actual operational recommendations
            # For now, return placeholder data
            return [
                {
                    'recommendation': 'Implement automated data quality checks',
                    'rationale': 'Reduce data quality issues affecting assessment accuracy',
                    'expected_impact': '1-2% improvement in data reliability',
                    'timeline': '2 months',
                    'priority': 'low'
                },
                {
                    'recommendation': 'Optimize assessment scheduling',
                    'rationale': 'Improve assessment frequency and consistency',
                    'expected_impact': '1-3% improvement in assessment coverage',
                    'timeline': '1 month',
                    'priority': 'low'
                }
            ]
            
        except Exception as e:
            self.logger.error(f"Error generating operational recommendations: {str(e)}")
            return []
    
    async def _generate_priority_actions(self, queryset) -> List[Dict[str, Any]]:
        """Generate priority actions."""
        try:
            # This would generate actual priority actions
            # For now, return placeholder data
            return [
                {
                    'action': 'Launch infrastructure improvement initiative',
                    'timeline': 'Immediate',
                    'owner': 'Operations Team',
                    'success_metrics': ['5% improvement in infrastructure scores', 'Reduced variance in regional performance']
                },
                {
                    'action': 'Establish regional performance sharing program',
                    'timeline': 'Next 30 days',
                    'owner': 'Strategy Team',
                    'success_metrics': ['3% improvement in regional consistency', 'Increased knowledge sharing']
                },
                {
                    'action': 'Implement enhanced monitoring for underperforming indicators',
                    'timeline': 'Next 2 weeks',
                    'owner': 'Analytics Team',
                    'success_metrics': ['2% improvement in problem areas', 'Faster issue identification']
                }
            ]
            
        except Exception as e:
            self.logger.error(f"Error generating priority actions: {str(e)}")
            return []
    
    async def _calculate_performance_trend(self, queryset) -> Dict[str, Any]:
        """Calculate overall performance trend."""
        try:
            # This would calculate actual performance trend
            # For now, return placeholder data
            return {
                'direction': 'improving',
                'magnitude': 'moderate',
                'confidence': 0.85,
                'duration': '3 months'
            }
            
        except Exception as e:
            self.logger.error(f"Error calculating performance trend: {str(e)}")
            return {'direction': 'stable', 'magnitude': 'low', 'confidence': 0.5, 'duration': 'unknown'}
    
    async def export_analytics_report(self, report_data: Dict[str, Any], 
                                    format: str = 'json') -> Optional[str]:
        """
        Export analytics report in various formats.
        
        Args:
            report_data: Report data to export
            format: Export format ('json', 'pdf', 'excel')
            
        Returns:
            Exported report or None if failed
        """
        try:
            if format == 'json':
                return json.dumps(report_data, indent=2, default=str)
            elif format == 'pdf':
                return await self._export_to_pdf(report_data)
            elif format == 'excel':
                return await self._export_to_excel(report_data)
            else:
                raise ValueError(f"Unsupported export format: {format}")
                
        except Exception as e:
            self.logger.error(f"Error exporting analytics report: {str(e)}")
            return None
    
    async def _export_to_pdf(self, report_data: Dict[str, Any]) -> str:
        """Export report to PDF format."""
        try:
            # This would use a library like reportlab or weasyprint
            # For now, return a placeholder
            return "PDF export not implemented yet"
            
        except Exception as e:
            self.logger.error(f"Error exporting to PDF: {str(e)}")
            return ""
    
    async def _export_to_excel(self, report_data: Dict[str, Any]) -> str:
        """Export report to Excel format."""
        try:
            # This would use a library like openpyxl
            # For now, return a placeholder
            return "Excel export not implemented yet"
            
        except Exception as e:
            self.logger.error(f"Error exporting to Excel: {str(e)}")
            return ""
