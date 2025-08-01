from rest_framework import status, viewsets, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from django.db import transaction
from django.utils import timezone
from django.db.models import Avg

from .models import (
    DataSyncLog, IndicatorData, IndicatorScore, ObjectiveScore, SectorScore
)
from .dashboard_serializers import (
    DashboardSummarySerializer, ObjectiveDashboardSerializer, IndicatorDashboardSerializer,
    OrgUnitPerformanceSerializer, TrendAnalysisSerializer, DashboardFilterSerializer,
    DashboardExportSerializer, DashboardComparisonSerializer, DashboardAlertSerializer,
    DashboardKpiSerializer, DashboardHeatmapSerializer, DashboardDrilldownSerializer,
    DashboardRealTimeSerializer, DashboardConfigurationSerializer, DashboardWidgetSerializer,
    DashboardReportSerializer, DashboardAnalyticsSerializer, DashboardNotificationSerializer,
    DashboardAccessControlSerializer
)
from .services import DashboardService
from organisation.services import AccessControlService
from dhis2_auth.session import get_dhis2_user


class DashboardViewSet(viewsets.ViewSet):
    """
    ViewSet for dashboard operations
    """
    permission_classes = [IsAuthenticated]
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.dashboard_service = DashboardService()
        self.access_service = AccessControlService()
    
    @action(detail=False, methods=['get'])
    def summary(self, request):
        """
        Get dashboard summary data
        """
        # Get filter parameters
        org_unit_id = request.query_params.get('org_unit_id')
        assessment_period = request.query_params.get('assessment_period')
        
        # Get dashboard summary
        summary_data = self.dashboard_service.get_dashboard_summary(
            request.user, org_unit_id, assessment_period
        )
        
        if summary_data is None:
            return Response(
                {'error': 'No data available or access denied'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        serializer = DashboardSummarySerializer(summary_data)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def objectives(self, request):
        """
        Get objective dashboard data
        """
        # Get filter parameters
        org_unit_id = request.query_params.get('org_unit_id')
        assessment_period = request.query_params.get('assessment_period')
        
        # Get objective dashboard data
        objectives_data = self.dashboard_service.get_objective_dashboard(
            request.user, org_unit_id, assessment_period
        )
        
        if objectives_data is None:
            return Response(
                {'error': 'No data available or access denied'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        serializer = ObjectiveDashboardSerializer(objectives_data)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def indicators(self, request):
        """
        Get indicator dashboard data
        """
        # Get filter parameters
        org_unit_id = request.query_params.get('org_unit_id')
        assessment_period = request.query_params.get('assessment_period')
        objective_id = request.query_params.get('objective_id')
        
        # Get indicator dashboard data
        indicators_data = self.dashboard_service.get_indicator_dashboard(
            request.user, org_unit_id, assessment_period, objective_id
        )
        
        if indicators_data is None:
            return Response(
                {'error': 'No data available or access denied'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        serializer = IndicatorDashboardSerializer(indicators_data)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def performance(self, request):
        """
        Get org unit performance data
        """
        # Get org unit ID from query params
        org_unit_id = request.query_params.get('org_unit_id')
        assessment_period = request.query_params.get('assessment_period')
        
        if not org_unit_id:
            return Response(
                {'error': 'org_unit_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get performance data
        performance_data = self.dashboard_service.get_org_unit_performance(
            request.user, org_unit_id, assessment_period
        )
        
        if performance_data is None:
            return Response(
                {'error': 'No data available or access denied'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        serializer = OrgUnitPerformanceSerializer(performance_data)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def trend(self, request):
        """
        Get trend analysis data
        """
        # Get parameters
        org_unit_id = request.query_params.get('org_unit_id')
        assessment_period = request.query_params.get('assessment_period')
        periods_back = int(request.query_params.get('periods_back', 3))
        
        if not org_unit_id:
            return Response(
                {'error': 'org_unit_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get trend analysis data
        trend_data = self.dashboard_service.get_trend_analysis(
            request.user, org_unit_id, assessment_period, periods_back
        )
        
        if trend_data is None:
            return Response(
                {'error': 'No data available or access denied'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        serializer = TrendAnalysisSerializer(trend_data)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def heatmap(self, request):
        """
        Get heatmap data for org units vs objectives/indicators
        """
        # Get parameters
        assessment_period = request.query_params.get('assessment_period')
        metric_type = request.query_params.get('metric_type', 'objectives')  # 'objectives' or 'indicators'
        
        # Get user's accessible org units
        accessible_org_units = self.access_service.get_user_accessible_org_units(request.user)
        
        if not accessible_org_units.exists():
            return Response(
                {'error': 'No accessible org units'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Build heatmap data
        org_units = list(accessible_org_units.values_list('name', flat=True))
        
        if metric_type == 'objectives':
            from configurations.models import Objective
            metrics = list(Objective.objects.filter(is_active=True).values_list('name', flat=True))
            
            # Get objective scores for all accessible org units
            objective_scores = ObjectiveScore.objects.filter(
                org_unit__in=accessible_org_units,
                assessment_period=assessment_period
            ).select_related('objective', 'org_unit')
            
            # Build heatmap data matrix
            data = []
            colors = []
            labels = []
            
            for org_unit_name in org_units:
                org_unit_data = []
                org_unit_colors = []
                org_unit_labels = []
                
                for metric_name in metrics:
                    score = objective_scores.filter(
                        org_unit__name=org_unit_name,
                        objective__name=metric_name
                    ).first()
                    
                    if score:
                        org_unit_data.append(score.score)
                        org_unit_colors.append(score.color)
                        org_unit_labels.append(score.label)
                    else:
                        org_unit_data.append(0)
                        org_unit_colors.append('#cccccc')
                        org_unit_labels.append('No Data')
                
                data.append(org_unit_data)
                colors.append(org_unit_colors)
                labels.append(org_unit_labels)
        
        else:  # indicators
            from indicators.models import TrackedIndicator
            metrics = list(TrackedIndicator.objects.filter(is_active=True).values_list('name', flat=True))
            
            # Get indicator scores for all accessible org units
            indicator_scores = IndicatorScore.objects.filter(
                org_unit__in=accessible_org_units,
                assessment_period=assessment_period
            ).select_related('indicator', 'org_unit')
            
            # Build heatmap data matrix
            data = []
            colors = []
            labels = []
            
            for org_unit_name in org_units:
                org_unit_data = []
                org_unit_colors = []
                org_unit_labels = []
                
                for metric_name in metrics:
                    score = indicator_scores.filter(
                        org_unit__name=org_unit_name,
                        indicator__name=metric_name
                    ).first()
                    
                    if score:
                        org_unit_data.append(score.score)
                        org_unit_colors.append(score.color)
                        org_unit_labels.append(score.label)
                    else:
                        org_unit_data.append(0)
                        org_unit_colors.append('#cccccc')
                        org_unit_labels.append('No Data')
                
                data.append(org_unit_data)
                colors.append(org_unit_colors)
                labels.append(org_unit_labels)
        
        heatmap_data = {
            'org_units': org_units,
            'metrics': metrics,
            'data': data,
            'colors': colors,
            'labels': labels
        }
        
        serializer = DashboardHeatmapSerializer(heatmap_data)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def drilldown(self, request):
        """
        Get drilldown data for a specific level
        """
        # Get parameters
        drilldown_level = request.query_params.get('level')  # 'org_unit', 'objective', 'indicator'
        drilldown_id = request.query_params.get('id')
        assessment_period = request.query_params.get('assessment_period')
        
        if not all([drilldown_level, drilldown_id]):
            return Response(
                {'error': 'level and id are required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Build drilldown data based on level
        if drilldown_level == 'org_unit':
            # Drill down from org unit to objectives
            from organisation.models import OrgUnit
            from configurations.models import Objective
            
            try:
                org_unit = OrgUnit.objects.get(id=drilldown_id)
                objectives = Objective.objects.filter(is_active=True)
                
                child_data = []
                for objective in objectives:
                    score = ObjectiveScore.objects.filter(
                        org_unit=org_unit,
                        objective=objective,
                        assessment_period=assessment_period
                    ).first()
                    
                    if score:
                        child_data.append({
                            'id': objective.id,
                            'name': objective.name,
                            'score': score.score,
                            'color': score.color,
                            'label': score.label
                        })
                
                drilldown_data = {
                    'drilldown_level': drilldown_level,
                    'drilldown_id': drilldown_id,
                    'drilldown_name': org_unit.name,
                    'parent_data': {
                        'type': 'org_unit',
                        'name': org_unit.name,
                        'level': org_unit.level.name
                    },
                    'child_data': child_data,
                    'drilldown_path': [
                        {'level': 'org_unit', 'id': org_unit.id, 'name': org_unit.name}
                    ]
                }
                
            except OrgUnit.DoesNotExist:
                return Response(
                    {'error': 'Org unit not found'},
                    status=status.HTTP_404_NOT_FOUND
                )
        
        elif drilldown_level == 'objective':
            # Drill down from objective to indicators
            from configurations.models import Objective
            from indicators.models import TrackedIndicator
            
            try:
                objective = Objective.objects.get(id=drilldown_id)
                indicators = TrackedIndicator.objects.filter(
                    objectives=objective,
                    is_active=True
                )
                
                child_data = []
                for indicator in indicators:
                    score = IndicatorScore.objects.filter(
                        indicator=indicator,
                        assessment_period=assessment_period
                    ).first()
                    
                    if score:
                        child_data.append({
                            'id': indicator.id,
                            'name': indicator.name,
                            'raw_value': score.raw_value,
                            'score': score.score,
                            'trend': score.trend,
                            'color': score.color,
                            'label': score.label
                        })
                
                drilldown_data = {
                    'drilldown_level': drilldown_level,
                    'drilldown_id': drilldown_id,
                    'drilldown_name': objective.name,
                    'parent_data': {
                        'type': 'objective',
                        'name': objective.name,
                        'description': objective.description
                    },
                    'child_data': child_data,
                    'drilldown_path': [
                        {'level': 'objective', 'id': objective.id, 'name': objective.name}
                    ]
                }
                
            except Objective.DoesNotExist:
                return Response(
                    {'error': 'Objective not found'},
                    status=status.HTTP_404_NOT_FOUND
                )
        
        else:
            return Response(
                {'error': 'Invalid drilldown level'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        serializer = DashboardDrilldownSerializer(drilldown_data)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def kpis(self, request):
        """
        Get key performance indicators
        """
        # Get parameters
        org_unit_id = request.query_params.get('org_unit_id')
        assessment_period = request.query_params.get('assessment_period')
        
        # Get user's accessible org units
        accessible_org_units = self.access_service.get_user_accessible_org_units(request.user)
        
        if org_unit_id:
            if not accessible_org_units.filter(id=org_unit_id).exists():
                return Response(
                    {'error': 'Access denied'},
                    status=status.HTTP_403_FORBIDDEN
                )
            org_units = [org_unit_id]
        else:
            org_units = list(accessible_org_units.values_list('id', flat=True))
        
        # Get current assessment period if not specified
        if not assessment_period:
            from configurations.models import AssessmentPeriod
            current_period = AssessmentPeriod.objects.filter(is_current=True).first()
            assessment_period = current_period.period if current_period else None
        
        if not assessment_period:
            return Response(
                {'error': 'No assessment period available'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Calculate KPIs
        kpis = []
        
        # KPI 1: Average Sector Score
        sector_scores = SectorScore.objects.filter(
            org_unit_id__in=org_units,
            assessment_period=assessment_period
        )
        if sector_scores.exists():
            avg_sector_score = sector_scores.aggregate(avg=Avg('score'))['avg']
            kpis.append({
                'kpi_name': 'Average Sector Score',
                'kpi_value': round(avg_sector_score, 2),
                'kpi_unit': 'points',
                'kpi_trend': 'stable',  # Could be calculated from previous periods
                'kpi_color': '#4CAF50' if avg_sector_score >= 3 else '#FF9800' if avg_sector_score >= 2 else '#F44336',
                'kpi_label': 'Good' if avg_sector_score >= 3 else 'Fair' if avg_sector_score >= 2 else 'Poor',
                'kpi_description': 'Average performance across all org units'
            })
        
        # KPI 2: Org Units with Scores
        total_org_units = len(org_units)
        org_units_with_scores = sector_scores.count()
        coverage_percentage = (org_units_with_scores / total_org_units * 100) if total_org_units > 0 else 0
        
        kpis.append({
            'kpi_name': 'Data Coverage',
            'kpi_value': round(coverage_percentage, 1),
            'kpi_unit': '%',
            'kpi_trend': 'stable',
            'kpi_color': '#4CAF50' if coverage_percentage >= 80 else '#FF9800' if coverage_percentage >= 60 else '#F44336',
            'kpi_label': 'Good' if coverage_percentage >= 80 else 'Fair' if coverage_percentage >= 60 else 'Poor',
            'kpi_description': f'{org_units_with_scores} of {total_org_units} org units have scores'
        })
        
        # KPI 3: Top Performing Objective
        objective_scores = ObjectiveScore.objects.filter(
            org_unit_id__in=org_units,
            assessment_period=assessment_period
        ).select_related('objective')
        
        if objective_scores.exists():
            best_objective = objective_scores.order_by('-score').first()
            kpis.append({
                'kpi_name': 'Best Performing Objective',
                'kpi_value': round(best_objective.score, 2),
                'kpi_unit': 'points',
                'kpi_trend': 'stable',
                'kpi_color': best_objective.color,
                'kpi_label': best_objective.label,
                'kpi_description': f'{best_objective.objective.name}'
            })
        
        # KPI 4: Improvement Rate
        # This would require historical data comparison
        kpis.append({
            'kpi_name': 'Improvement Rate',
            'kpi_value': 0,  # Would be calculated from trend analysis
            'kpi_unit': '%',
            'kpi_trend': 'stable',
            'kpi_color': '#666666',
            'kpi_label': 'No Data',
            'kpi_description': 'Rate of improvement over previous period'
        })
        
        return Response({'kpis': kpis})
    
    @action(detail=False, methods=['get'])
    def alerts(self, request):
        """
        Get dashboard alerts
        """
        # Get parameters
        org_unit_id = request.query_params.get('org_unit_id')
        assessment_period = request.query_params.get('assessment_period')
        alert_type = request.query_params.get('alert_type')
        
        # Get user's accessible org units
        accessible_org_units = self.access_service.get_user_accessible_org_units(request.user)
        
        if org_unit_id:
            if not accessible_org_units.filter(id=org_unit_id).exists():
                return Response(
                    {'error': 'Access denied'},
                    status=status.HTTP_403_FORBIDDEN
                )
            org_units = [org_unit_id]
        else:
            org_units = list(accessible_org_units.values_list('id', flat=True))
        
        # Get current assessment period if not specified
        if not assessment_period:
            from configurations.models import AssessmentPeriod
            current_period = AssessmentPeriod.objects.filter(is_current=True).first()
            assessment_period = current_period.period if current_period else None
        
        if not assessment_period:
            return Response({'alerts': []})
        
        # Generate alerts based on performance thresholds
        alerts = []
        
        # Check for underperforming org units
        if not alert_type or alert_type == 'underperforming':
            sector_scores = SectorScore.objects.filter(
                org_unit_id__in=org_units,
                assessment_period=assessment_period
            ).select_related('org_unit')
            
            for score in sector_scores:
                if score.score < 2:  # Threshold for underperforming
                    alerts.append({
                        'alert_type': 'underperforming',
                        'org_unit_id': score.org_unit_id,
                        'org_unit_name': score.org_unit.name,
                        'metric_type': 'sector',
                        'metric_name': 'Sector Score',
                        'current_score': score.score,
                        'threshold_score': 2.0,
                        'severity': 'high' if score.score < 1 else 'medium',
                        'message': f'{score.org_unit.name} is underperforming with a score of {score.score}',
                        'created_at': timezone.now()
                    })
        
        # Check for improving/declining trends
        if not alert_type or alert_type in ['improving', 'declining']:
            indicator_scores = IndicatorScore.objects.filter(
                org_unit_id__in=org_units,
                assessment_period=assessment_period
            ).select_related('indicator', 'org_unit')
            
            for score in indicator_scores:
                if score.trend == 'declining' and score.score < 2:
                    alerts.append({
                        'alert_type': 'declining',
                        'org_unit_id': score.org_unit_id,
                        'org_unit_name': score.org_unit.name,
                        'metric_type': 'indicator',
                        'metric_name': score.indicator.name,
                        'current_score': score.score,
                        'threshold_score': 2.0,
                        'severity': 'medium',
                        'message': f'{score.indicator.name} at {score.org_unit.name} is declining',
                        'created_at': timezone.now()
                    })
                elif score.trend == 'improving' and score.score > 3:
                    alerts.append({
                        'alert_type': 'improving',
                        'org_unit_id': score.org_unit_id,
                        'org_unit_name': score.org_unit.name,
                        'metric_type': 'indicator',
                        'metric_name': score.indicator.name,
                        'current_score': score.score,
                        'threshold_score': 3.0,
                        'severity': 'low',
                        'message': f'{score.indicator.name} at {score.org_unit.name} is improving',
                        'created_at': timezone.now()
                    })
        
        # Sort alerts by severity and creation time
        severity_order = {'critical': 0, 'high': 1, 'medium': 2, 'low': 3}
        alerts.sort(key=lambda x: (severity_order.get(x['severity'], 4), x['created_at']))
        
        return Response({'alerts': alerts})
    
    @action(detail=False, methods=['post'])
    def export(self, request):
        """
        Export dashboard data
        """
        serializer = DashboardExportSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        data = serializer.validated_data
        
        # This would integrate with the exports app
        # For now, return a placeholder response
        return Response({
            'message': f'Export request received for {data["dashboard_type"]} dashboard',
            'format': data['format'],
            'filters': data['filters'],
            'download_url': None  # Would be generated by export service
        })
    
    @action(detail=False, methods=['get'])
    def configuration(self, request):
        """
        Get user's dashboard configuration
        """
        # This would typically be stored in user preferences
        # For now, return default configuration
        config = {
            'dashboard_layout': {
                'widgets': [
                    {'id': 'summary', 'position': {'x': 0, 'y': 0}, 'size': {'width': 6, 'height': 4}},
                    {'id': 'objectives', 'position': {'x': 6, 'y': 0}, 'size': {'width': 6, 'height': 4}},
                    {'id': 'indicators', 'position': {'x': 0, 'y': 4}, 'size': {'width': 12, 'height': 4}},
                    {'id': 'trend', 'position': {'x': 0, 'y': 8}, 'size': {'width': 12, 'height': 4}}
                ]
            },
            'visible_widgets': ['summary', 'objectives', 'indicators', 'trend'],
            'default_filters': {
                'org_unit_id': None,
                'assessment_period': None,
                'objective_id': None,
                'indicator_id': None
            },
            'refresh_interval': 300,
            'chart_types': {
                'summary': 'gauge',
                'objectives': 'bar',
                'indicators': 'table',
                'trend': 'line'
            },
            'color_scheme': 'default',
            'user_preferences': {}
        }
        
        serializer = DashboardConfigurationSerializer(config)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def access_control(self, request):
        """
        Get user's dashboard access control information
        """
        # Get user's accessible org units
        accessible_org_units = self.access_service.get_user_accessible_org_units(request.user)
        
        # Get user's primary org unit
        primary_org_unit = self.access_service.get_user_primary_org_unit(request.user)
        
        # Get accessible objectives and indicators
        from configurations.models import Objective
        from indicators.models import TrackedIndicator
        
        accessible_objectives = list(Objective.objects.filter(is_active=True).values_list('id', flat=True))
        accessible_indicators = list(TrackedIndicator.objects.filter(is_active=True).values_list('id', flat=True))
        
        # Determine permissions
        permissions = {
            'can_view_data': True,
            'can_edit_data': False,
            'can_manage_users': False,
            'can_export_data': True
        }
        
        # Check specific permissions for primary org unit
        if primary_org_unit:
            access = primary_org_unit.user_access.filter(
                user=request.user,
                is_active=True
            ).first()
            
            if access:
                permissions.update({
                    'can_view_data': access.can_view_data,
                    'can_edit_data': access.can_edit_data,
                    'can_manage_users': access.can_manage_users,
                    'can_export_data': access.can_export_data
                })
        
        access_control_data = {
            'user_id': request.user.id,
            'accessible_org_units': list(accessible_org_units.values_list('id', flat=True)),
            'accessible_objectives': accessible_objectives,
            'accessible_indicators': accessible_indicators,
            'permissions': permissions,
            'access_level': 'user',
            'last_access': timezone.now(),
            'session_expires': timezone.now() + timezone.timedelta(hours=8)
        }
        
        serializer = DashboardAccessControlSerializer(access_control_data)
        return Response(serializer.data) 