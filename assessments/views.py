from django.shortcuts import render
from rest_framework import status, viewsets, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from django.db import transaction
from django.utils import timezone

from .models import (
    DataSyncLog, IndicatorData, IndicatorScore, ObjectiveScore, SectorScore
)
from .serializers import (
    DataSyncLogSerializer, DataSyncLogCreateSerializer,
    IndicatorDataSerializer,
    IndicatorScoreSerializer, IndicatorScoreCreateSerializer,
    ObjectiveScoreSerializer, ObjectiveScoreCreateSerializer,
    SectorScoreSerializer, SectorScoreCreateSerializer,
    BulkScoreCalculationSerializer, DataSyncRequestSerializer,
    ScoreOverrideSerializer, DashboardSummarySerializer,
    ObjectiveDashboardSerializer, IndicatorDashboardSerializer,
    AssessmentReportSerializer
)
from .services import DataSyncService, ScoreCalculationService, DashboardService
from dhis2_auth.session import get_dhis2_user


class DataSyncLogViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing data sync logs
    """
    queryset = DataSyncLog.objects.all()
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['sync_type', 'status', 'dhis2_user']
    search_fields = ['dhis2_instance_url', 'error_message']
    ordering_fields = ['started_at', 'completed_at', 'duration_seconds']
    ordering = ['-started_at']
    
    def get_serializer_class(self):
        """Return appropriate serializer class based on action"""
        if self.action == 'create':
            return DataSyncLogCreateSerializer
        return DataSyncLogSerializer
    
    @action(detail=False, methods=['post'])
    def trigger_sync(self, request):
        """
        Trigger a new data sync from DHIS2
        """
        serializer = DataSyncRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            # Get current DHIS2 user
            dhis2_user = get_dhis2_user(request)
            
            # Initialize sync service
            sync_service = DataSyncService()
            
            # Perform the sync
            sync_log = sync_service.sync_data(serializer.validated_data, dhis2_user)
            
            return Response({
                'success': True,
                'message': f'Data sync initiated successfully. Sync ID: {sync_log.id}',
                'sync_log': DataSyncLogSerializer(sync_log).data
            })
            
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=True, methods=['get'])
    def data_points(self, request, pk=None):
        """
        Get data points for a specific sync log
        """
        sync_log = self.get_object()
        data_points = sync_log.data_points.all()
        
        page = self.paginate_queryset(data_points)
        if page is not None:
            serializer = IndicatorDataSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = IndicatorDataSerializer(data_points, many=True)
        return Response(serializer.data)


class IndicatorDataViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for viewing indicator data (read-only)
    """
    queryset = IndicatorData.objects.all()
    serializer_class = IndicatorDataSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['indicator', 'org_unit_id', 'period', 'sync_log']
    search_fields = ['org_unit_name']
    ordering_fields = ['created_at', 'updated_at', 'period']
    ordering = ['-created_at']


class IndicatorScoreViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing indicator scores
    """
    queryset = IndicatorScore.objects.all()
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['indicator', 'objective', 'org_unit_id', 'assessment_period', 'is_manual_override']
    search_fields = ['indicator__name', 'objective__name', 'org_unit_name']
    ordering_fields = ['score', 'created_at', 'last_calculated']
    ordering = ['objective__order', 'indicator__name']
    
    def get_serializer_class(self):
        """Return appropriate serializer class based on action"""
        if self.action == 'create':
            return IndicatorScoreCreateSerializer
        return IndicatorScoreSerializer
    
    @action(detail=True, methods=['post'])
    def override_score(self, request, pk=None):
        """
        Manually override an indicator score
        """
        score = self.get_object()
        serializer = ScoreOverrideSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            data = serializer.validated_data
            dhis2_user = get_dhis2_user(request)
            
            with transaction.atomic():
                score.is_manual_override = True
                score.score = data['score']
                score.override_reason = data['reason']
                score.override_user = dhis2_user
                
                if data.get('score_color'):
                    score.score_color = data['score_color']
                if data.get('score_label'):
                    score.score_label = data['score_label']
                
                score.save()
                
                # Recalculate objective and sector scores
                self._recalculate_higher_level_scores(score)
            
            return Response({
                'success': True,
                'message': 'Score override applied successfully',
                'score': IndicatorScoreSerializer(score).data
            })
            
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=True, methods=['post'])
    def recalculate(self, request, pk=None):
        """
        Recalculate an indicator score
        """
        score = self.get_object()
        
        try:
            # Remove manual override
            score.is_manual_override = False
            score.override_reason = ''
            score.override_user = None
            score.save()
            
            # Recalculate the score
            score.calculate_score()
            
            # Recalculate higher level scores
            self._recalculate_higher_level_scores(score)
            
            return Response({
                'success': True,
                'message': 'Score recalculated successfully',
                'score': IndicatorScoreSerializer(score).data
            })
            
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def _recalculate_higher_level_scores(self, indicator_score):
        """Recalculate objective and sector scores after indicator score change"""
        # Recalculate objective score
        objective_score = ObjectiveScore.objects.filter(
            objective=indicator_score.objective,
            org_unit_id=indicator_score.org_unit_id,
            assessment_period=indicator_score.assessment_period
        ).first()
        
        if objective_score:
            objective_score.calculate_score()
        
        # Recalculate sector score
        sector_score = SectorScore.objects.filter(
            org_unit_id=indicator_score.org_unit_id,
            assessment_period=indicator_score.assessment_period
        ).first()
        
        if sector_score:
            sector_score.calculate_score()


class ObjectiveScoreViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing objective scores
    """
    queryset = ObjectiveScore.objects.all()
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['objective', 'org_unit_id', 'assessment_period']
    search_fields = ['objective__name', 'org_unit_name']
    ordering_fields = ['final_score', 'created_at', 'last_calculated']
    ordering = ['objective__order']
    
    def get_serializer_class(self):
        """Return appropriate serializer class based on action"""
        if self.action == 'create':
            return ObjectiveScoreCreateSerializer
        return ObjectiveScoreSerializer
    
    @action(detail=True, methods=['post'])
    def recalculate(self, request, pk=None):
        """
        Recalculate an objective score
        """
        score = self.get_object()
        
        try:
            score.calculate_score()
            
            # Recalculate sector score
            sector_score = SectorScore.objects.filter(
                org_unit_id=score.org_unit_id,
                assessment_period=score.assessment_period
            ).first()
            
            if sector_score:
                sector_score.calculate_score()
            
            return Response({
                'success': True,
                'message': 'Objective score recalculated successfully',
                'score': ObjectiveScoreSerializer(score).data
            })
            
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class SectorScoreViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing sector scores
    """
    queryset = SectorScore.objects.all()
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['org_unit_id', 'assessment_period']
    search_fields = ['org_unit_name']
    ordering_fields = ['overall_score', 'created_at', 'last_calculated']
    ordering = ['-assessment_period__start_date', 'org_unit_name']
    
    def get_serializer_class(self):
        """Return appropriate serializer class based on action"""
        if self.action == 'create':
            return SectorScoreCreateSerializer
        return SectorScoreSerializer
    
    @action(detail=True, methods=['post'])
    def recalculate(self, request, pk=None):
        """
        Recalculate a sector score
        """
        score = self.get_object()
        
        try:
            score.calculate_score()
            
            return Response({
                'success': True,
                'message': 'Sector score recalculated successfully',
                'score': SectorScoreSerializer(score).data
            })
            
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class AssessmentDashboardViewSet(viewsets.ViewSet):
    """
    ViewSet for assessment dashboard data
    """
    permission_classes = [IsAuthenticated]
    
    @action(detail=False, methods=['get'])
    def summary(self, request):
        """
        Get dashboard summary for current user's org unit
        """
        # Get user's org unit from session
        session_data = get_dhis2_session_data(request)
        if not session_data or not session_data.get('org_units'):
            return Response({
                'error': 'No org units found in session'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Use the first org unit (could be enhanced to support multiple)
        org_unit_id = session_data['org_units'][0]
        
        # Get assessment period from query params or use current
        assessment_period_id = request.query_params.get('assessment_period_id')
        if assessment_period_id:
            from configurations.models import AssessmentPeriod
            assessment_period = AssessmentPeriod.objects.get(id=assessment_period_id)
        else:
            assessment_period = None
        
        # Get dashboard summary
        dashboard_service = DashboardService()
        summary = dashboard_service.get_dashboard_summary(org_unit_id, assessment_period)
        
        if not summary:
            return Response({
                'error': 'No assessment data found for this org unit'
            }, status=status.HTTP_404_NOT_FOUND)
        
        serializer = DashboardSummarySerializer(summary)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def objectives(self, request):
        """
        Get objective dashboard data
        """
        # Get user's org unit from session
        session_data = get_dhis2_session_data(request)
        if not session_data or not session_data.get('org_units'):
            return Response({
                'error': 'No org units found in session'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        org_unit_id = session_data['org_units'][0]
        
        # Get assessment period from query params or use current
        assessment_period_id = request.query_params.get('assessment_period_id')
        if assessment_period_id:
            from configurations.models import AssessmentPeriod
            assessment_period = AssessmentPeriod.objects.get(id=assessment_period_id)
        else:
            assessment_period = None
        
        # Get objective dashboard data
        dashboard_service = DashboardService()
        objectives = dashboard_service.get_objective_dashboard(org_unit_id, assessment_period)
        
        serializer = ObjectiveDashboardSerializer(objectives, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def indicators(self, request):
        """
        Get indicator dashboard data
        """
        # Get user's org unit from session
        session_data = get_dhis2_session_data(request)
        if not session_data or not session_data.get('org_units'):
            return Response({
                'error': 'No org units found in session'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        org_unit_id = session_data['org_units'][0]
        
        # Get assessment period from query params or use current
        assessment_period_id = request.query_params.get('assessment_period_id')
        if assessment_period_id:
            from configurations.models import AssessmentPeriod
            assessment_period = AssessmentPeriod.objects.get(id=assessment_period_id)
        else:
            assessment_period = None
        
        # Get indicator dashboard data
        dashboard_service = DashboardService()
        indicators = dashboard_service.get_indicator_dashboard(org_unit_id, assessment_period)
        
        serializer = IndicatorDashboardSerializer(indicators, many=True)
        return Response(serializer.data)


class AssessmentManagementViewSet(viewsets.ViewSet):
    """
    ViewSet for assessment management operations
    """
    permission_classes = [IsAuthenticated]
    
    @action(detail=False, methods=['post'])
    def calculate_scores(self, request):
        """
        Bulk calculate scores
        """
        serializer = BulkScoreCalculationSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            calculation_service = ScoreCalculationService()
            results = calculation_service.bulk_calculate_scores(serializer.validated_data)
            
            return Response({
                'success': True,
                'message': f'Score calculation completed. Processed {results["processed_org_units"]} org units.',
                'results': results
            })
            
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['get'])
    def assessment_report(self, request):
        """
        Generate assessment report
        """
        # Get parameters
        org_unit_id = request.query_params.get('org_unit_id')
        assessment_period_id = request.query_params.get('assessment_period_id')
        
        if not org_unit_id:
            return Response({
                'error': 'org_unit_id is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Get assessment period
        if assessment_period_id:
            from configurations.models import AssessmentPeriod
            assessment_period = AssessmentPeriod.objects.get(id=assessment_period_id)
        else:
            assessment_period = AssessmentPeriod.objects.filter(is_current=True).first()
        
        if not assessment_period:
            return Response({
                'error': 'No assessment period found'
            }, status=status.HTTP_404_NOT_FOUND)
        
        try:
            # Get sector score
            sector_score = SectorScore.objects.filter(
                org_unit_id=org_unit_id,
                assessment_period=assessment_period
            ).first()
            
            if not sector_score:
                return Response({
                    'error': 'No assessment data found for this org unit and period'
                }, status=status.HTTP_404_NOT_FOUND)
            
            # Get objective scores
            objective_scores = ObjectiveScore.objects.filter(
                org_unit_id=org_unit_id,
                assessment_period=assessment_period
            ).select_related('objective')
            
            # Get indicator scores
            indicator_scores = IndicatorScore.objects.filter(
                org_unit_id=org_unit_id,
                assessment_period=assessment_period
            ).select_related('indicator', 'objective')
            
            # Build report data
            report_data = {
                'report_id': f"ASSESSMENT_{org_unit_id}_{assessment_period.name}_{timezone.now().strftime('%Y%m%d_%H%M%S')}",
                'org_unit_id': org_unit_id,
                'org_unit_name': sector_score.org_unit_name,
                'assessment_period_name': assessment_period.name,
                'sector_score': sector_score.overall_score,
                'sector_color': sector_score.score_color,
                'sector_label': sector_score.score_label,
                'objectives': [],
                'indicators': [],
                'generated_at': timezone.now(),
                'generated_by': get_dhis2_user(request).dhis2_username if get_dhis2_user(request) else 'System'
            }
            
            # Add objective data
            for obj_score in objective_scores:
                report_data['objectives'].append({
                    'objective_id': obj_score.objective.id,
                    'objective_name': obj_score.objective.name,
                    'objective_code': obj_score.objective.code,
                    'objective_color': obj_score.objective.color,
                    'score': obj_score.final_score,
                    'score_color': obj_score.score_color,
                    'score_label': obj_score.score_label,
                    'indicator_count': obj_score.total_indicators,
                    'trend_direction': 'stable'  # Could be enhanced
                })
            
            # Add indicator data
            for ind_score in indicator_scores:
                report_data['indicators'].append({
                    'indicator_id': ind_score.indicator.id,
                    'indicator_name': ind_score.indicator.name,
                    'indicator_uid': ind_score.indicator.dhis2_uid,
                    'objective_name': ind_score.objective.name,
                    'current_value': ind_score.current_value,
                    'target_value': ind_score.target_value,
                    'score': ind_score.score,
                    'score_color': ind_score.score_color,
                    'score_label': ind_score.score_label,
                    'trend_direction': 'stable',  # Could be enhanced
                    'weight': ind_score.weight
                })
            
            serializer = AssessmentReportSerializer(report_data)
            return Response(serializer.data)
            
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
