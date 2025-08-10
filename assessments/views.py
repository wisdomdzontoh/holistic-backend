from django.shortcuts import render
from rest_framework import status, viewsets, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from django.db import transaction
from django.utils import timezone
import logging
from rest_framework.exceptions import ValidationError

from .models import (
    DataSyncLog, IndicatorData, IndicatorScore, ObjectiveScore, SectorScore,
    SavedAssessment, AuditLog, ConflictResolution, MilestoneScore
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
    AssessmentReportSerializer, HolisticAssessmentRequestSerializer,
    HolisticAssessmentSaveSerializer, AuditLogSerializer, ConflictResolutionSerializer,
    ConflictResolutionCreateSerializer, ConflictResolutionUpdateSerializer,
    ManualOverrideSerializer, AuditLogFilterSerializer, ConflictResolutionFilterSerializer
)
from .services import DataSyncService, ScoreCalculationService, DashboardService, RealTimeDHIS2Service, AssessmentSaveService
from dhis2_auth.session import get_dhis2_user, get_dhis2_user_from_request, get_dhis2_session_data
from dhis2_auth.dhis_client import DHIS2ClientFactory

logger = logging.getLogger(__name__)


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
            dhis2_user = get_dhis2_user_from_request(request)
            
            # Initialize sync service
            sync_service = DataSyncService()
            
            # Perform the sync
            sync_log = sync_service.sync_data(serializer.validated_data, dhis2_user, request.session.session_key)
            
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
        Override indicator score manually
        """
        indicator_score = self.get_object()
        serializer = ScoreOverrideSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            data = serializer.validated_data
            indicator_score.score = data['score']
            indicator_score.is_manual_override = True
            indicator_score.override_reason = data['reason']
            indicator_score.override_user = get_dhis2_user_from_request(request)
            
            # Set color and label if provided
            if 'score_color' in data:
                indicator_score.score_color = data['score_color']
            if 'score_label' in data:
                indicator_score.score_label = data['score_label']
            
            indicator_score.save()
            
            # Recalculate higher-level scores
            self._recalculate_higher_level_scores(indicator_score)
            
            return Response({
                'success': True,
                'message': 'Score override applied successfully',
                'indicator_score': IndicatorScoreSerializer(indicator_score).data
            })
            
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=True, methods=['post'])
    def recalculate(self, request, pk=None):
        """
        Recalculate indicator score
        """
        indicator_score = self.get_object()
        
        try:
            # Clear manual override
            indicator_score.is_manual_override = False
            indicator_score.override_reason = ''
            indicator_score.override_user = None
            
            # Recalculate score
            indicator_score.calculate_score()
            indicator_score.save()
            
            # Recalculate higher-level scores
            self._recalculate_higher_level_scores(indicator_score)
            
            return Response({
                'success': True,
                'message': 'Score recalculated successfully',
                'indicator_score': IndicatorScoreSerializer(indicator_score).data
            })
            
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def _recalculate_higher_level_scores(self, indicator_score):
        """
        Recalculate objective and sector scores after indicator score change
        """
        try:
            # Recalculate objective score
            objective_score = ObjectiveScore.objects.filter(
                objective=indicator_score.objective,
                org_unit_id=indicator_score.org_unit_id,
                assessment_period=indicator_score.assessment_period
            ).first()
            
            if objective_score:
                objective_score.calculate_score()
                objective_score.save()
            
            # Recalculate sector score
            sector_score = SectorScore.objects.filter(
                org_unit_id=indicator_score.org_unit_id,
                assessment_period=indicator_score.assessment_period
            ).first()
            
            if sector_score:
                sector_score.calculate_score()
                sector_score.save()
                
        except Exception as e:
            # Log error but don't fail the main operation
            logger.error(f"Error recalculating higher-level scores: {str(e)}")


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
        Recalculate objective score
        """
        objective_score = self.get_object()
        
        try:
            objective_score.calculate_score()
            objective_score.save()
            
            # Recalculate sector score
            sector_score = SectorScore.objects.filter(
                org_unit_id=objective_score.org_unit_id,
                assessment_period=objective_score.assessment_period
            ).first()
            
            if sector_score:
                sector_score.calculate_score()
                sector_score.save()
            
            return Response({
                'success': True,
                'message': 'Objective score recalculated successfully',
                'objective_score': ObjectiveScoreSerializer(objective_score).data
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
        Recalculate sector score
        """
        sector_score = self.get_object()
        
        try:
            sector_score.calculate_score()
            sector_score.save()
            
            return Response({
                'success': True,
                'message': 'Sector score recalculated successfully',
                'sector_score': SectorScoreSerializer(sector_score).data
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
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.dashboard_service = DashboardService()
    
    @action(detail=False, methods=['get'])
    def summary(self, request):
        """
        Get dashboard summary data
        """
        try:
            # Get user's org unit from session
            session_key = request.session.session_key
            session_data = get_dhis2_session_data(session_key)
            if not session_data or not session_data.get('org_units'):
                return Response({
                    'error': 'No org units found in session'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            org_unit_id = session_data['org_units'][0]
            assessment_period = request.query_params.get('assessment_period')
            
            summary_data = self.dashboard_service.get_dashboard_summary(
                request.user, org_unit_id, assessment_period
            )
            
            serializer = DashboardSummarySerializer(summary_data)
            return Response(serializer.data)
            
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['get'])
    def objectives(self, request):
        """
        Get objective dashboard data
        """
        try:
            # Get user's org unit from session
            session_key = request.session.session_key
            session_data = get_dhis2_session_data(session_key)
            if not session_data or not session_data.get('org_units'):
                return Response({
                    'error': 'No org units found in session'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            org_unit_id = session_data['org_units'][0]
            assessment_period = request.query_params.get('assessment_period')
            
            objectives_data = self.dashboard_service.get_objective_dashboard(
                request.user, org_unit_id, assessment_period
            )
            
            serializer = ObjectiveDashboardSerializer(objectives_data, many=True)
            return Response(serializer.data)
            
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['get'])
    def indicators(self, request):
        """
        Get indicator dashboard data
        """
        try:
            # Get user's org unit from session
            session_key = request.session.session_key
            session_data = get_dhis2_session_data(session_key)
            if not session_data or not session_data.get('org_units'):
                return Response({
                    'error': 'No org units found in session'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            org_unit_id = session_data['org_units'][0]
            assessment_period = request.query_params.get('assessment_period')
            objective_id = request.query_params.get('objective_id')
            
            indicators_data = self.dashboard_service.get_indicator_dashboard(
                request.user, org_unit_id, assessment_period, objective_id
            )
            
            serializer = IndicatorDashboardSerializer(indicators_data, many=True)
            return Response(serializer.data)
            
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class AssessmentManagementViewSet(viewsets.ViewSet):
    """
    ViewSet for assessment management operations
    """
    permission_classes = [IsAuthenticated]
    
    @action(detail=False, methods=['post'])
    def calculate_scores(self, request):
        """
        Calculate scores for specified parameters
        """
        serializer = BulkScoreCalculationSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            # Get user's org unit from session if not specified
            session_key = request.session.session_key
            session_data = get_dhis2_session_data(session_key)
            
            if not serializer.validated_data.get('org_unit_ids') and session_data:
                serializer.validated_data['org_unit_ids'] = session_data.get('org_units', [])
            
            # Initialize calculation service
            calculation_service = ScoreCalculationService()
            
            # Perform bulk calculation
            results = calculation_service.bulk_calculate_scores(serializer.validated_data)
            
            return Response({
                'success': True,
                'message': 'Score calculation completed successfully',
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
        try:
            # Get parameters
            org_unit_id = request.query_params.get('org_unit_id')
            assessment_period_id = request.query_params.get('assessment_period_id')
            format_type = request.query_params.get('format', 'excel')
            
            # Get user's org unit from session if not specified
            if not org_unit_id:
                session_key = request.session.session_key
                session_data = get_dhis2_session_data(session_key)
                if session_data and session_data.get('org_units'):
                    org_unit_id = session_data['org_units'][0]
            
            if not org_unit_id:
                return Response({
                    'error': 'No org unit specified'
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
            
            # Generate report data
            from .services import DashboardService
            dashboard_service = DashboardService()
            
            report_data = dashboard_service.get_org_unit_performance(
                request.user, org_unit_id, assessment_period.name
            )
            
            # Add report metadata
            report_data['report_id'] = f"assessment_{org_unit_id}_{assessment_period.id}"
            report_data['generated_at'] = timezone.now()
            report_data['generated_by'] = request.user.username if hasattr(request.user, 'username') else 'System'
            
            serializer = AssessmentReportSerializer(report_data)
            return Response(serializer.data)
            
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['get'])
    def holistic_assessment_data(self, request):
        """
        Get comprehensive data for holistic assessment interface
        """
        try:
            # Get user's org unit from session
            session_key = request.session.session_key
            session_data = get_dhis2_session_data(session_key)
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
                assessment_period = AssessmentPeriod.objects.filter(is_current=True).first()
            
            if not assessment_period:
                return Response({
                    'error': 'No assessment period found'
                }, status=status.HTTP_404_NOT_FOUND)
            
            # Get all objectives with their indicators
            from configurations.models import Objective
            from indicators.models import TrackedIndicator
            
            objectives = Objective.objects.filter(is_active=True).order_by('order')
            
            assessment_data = {
                'org_unit_id': org_unit_id,
                'org_unit_name': session_data.get('org_unit_name', 'Unknown'),
                'assessment_period': {
                    'id': assessment_period.id,
                    'name': assessment_period.name,
                    'start_date': assessment_period.start_date,
                    'end_date': assessment_period.end_date
                },
                'objectives': [],
                'sector_score': None
            }
            
            # Get sector score
            sector_score = SectorScore.objects.filter(
                org_unit_id=org_unit_id,
                assessment_period=assessment_period
            ).first()
            
            if sector_score:
                assessment_data['sector_score'] = {
                    'overall_score': sector_score.overall_score,
                    'score_color': sector_score.score_color,
                    'score_label': sector_score.score_label,
                    'total_objectives': sector_score.total_objectives,
                    'scored_objectives': sector_score.scored_objectives
                }
            
            # Build objectives and indicators structure
            for objective in objectives:
                objective_data = {
                    'id': objective.id,
                    'name': objective.name,
                    'code': objective.code,
                    'description': objective.description,
                    'color': objective.color,
                    'order': objective.order,
                    'indicators': [],
                    'score': None,
                    'milestone': None
                }
                
                # Add milestone information if it exists
                if objective.milestone:
                    # Get milestone score for this assessment
                    milestone_score = MilestoneScore.objects.filter(
                        milestone=objective.milestone,
                        org_unit_id=org_unit_id,
                        assessment_period=assessment_period
                    ).first()
                    
                    objective_data['milestone'] = {
                        'id': objective.milestone.id,
                        'name': objective.milestone.name,
                        'code': objective.milestone.code,
                        'color': objective.milestone.color,
                        'score': milestone_score.score if milestone_score else -2,  # Default score
                        'score_color': milestone_score.score_color if milestone_score else '#dc3545',
                        'score_label': milestone_score.score_label if milestone_score else 'Severely Underperforming'
                    }
                
                # Get objective score
                obj_score = ObjectiveScore.objects.filter(
                    objective=objective,
                    org_unit_id=org_unit_id,
                    assessment_period=assessment_period
                ).first()
                
                if obj_score:
                    objective_data['score'] = {
                        'final_score': obj_score.final_score,
                        'score_color': obj_score.score_color,
                        'score_label': obj_score.score_label,
                        'total_indicators': obj_score.total_indicators,
                        'scored_indicators': obj_score.scored_indicators
                    }
                
                # Get indicators for this objective
                indicators = TrackedIndicator.objects.filter(
                    objective_weights__objective=objective,
                    is_active=True
                ).order_by('name')
                
                for indicator in indicators:
                    indicator_data = {
                        'id': indicator.id,
                        'name': indicator.name,
                        'dhis2_uid': indicator.dhis2_uid,
                        'description': indicator.description,
                        'target_value': indicator.target_value,
                        'target_type': indicator.target_type,
                        'weight': 1.0,  # Default weight
                        'score': None,
                        'data_values': {}
                    }
                    
                    # Get indicator weight
                    weight_mapping = indicator.objective_weights.filter(objective=objective).first()
                    if weight_mapping:
                        indicator_data['weight'] = weight_mapping.weight
                    
                    # Get indicator score
                    ind_score = IndicatorScore.objects.filter(
                        indicator=indicator,
                        objective=objective,
                        org_unit_id=org_unit_id,
                        assessment_period=assessment_period
                    ).first()
                    
                    if ind_score:
                        indicator_data['score'] = {
                            'score': ind_score.score,
                            'score_color': ind_score.score_color,
                            'score_label': ind_score.score_label,
                            'current_value': ind_score.current_value,
                            'previous_value': ind_score.previous_value,
                            'target_gap': ind_score.target_gap,
                            'percent_change': ind_score.percent_change,
                            'is_manual_override': ind_score.is_manual_override
                        }
                    
                    # Get historical data values
                    data_points = IndicatorData.objects.filter(
                        indicator=indicator,
                        org_unit_id=org_unit_id
                    ).order_by('period')
                    
                    for data_point in data_points:
                        indicator_data['data_values'][data_point.period] = {
                            'value': data_point.value,
                            'calculated_value': data_point.calculated_value,
                            'created_at': data_point.created_at
                        }
                    
                    objective_data['indicators'].append(indicator_data)
                
                # Compute objective-level O/P categories and trend score from indicators
                try:
                    trend_meta = self.realtime_service._compute_objective_trend_from_indicators(objective_data['indicators'])
                    if trend_meta:
                        if objective_data.get('score') is None:
                            objective_data['score'] = {}
                        objective_data['score'].update(trend_meta)
                except Exception as ex:
                    logger.warning(f"Objective trend compute failed: {ex}")

                assessment_data['objectives'].append(objective_data)
            
            return Response(assessment_data)
            
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['get'])
    def dhis2_periods(self, request):
        """
        Get periods from DHIS2 instance
        """
        try:
            # Get session data
            session_data = get_dhis2_session_data(request.session.session_key)
            if not session_data:
                return Response(
                    {"error": "Incomplete DHIS2 session data"},
                    status=status.HTTP_401_UNAUTHORIZED
                )
            
            # Create DHIS2 client
            client = DHIS2ClientFactory.create_client_from_session(
                session_data.get('instance_url'),
                request.session.session_key
            )
            
            # Get periods from DHIS2
            periods = client.get_periods()
            
            return Response({
                "success": True,
                "data": periods,
                "total": len(periods)
            })
            
        except Exception as e:
            logger.error(f"Error fetching DHIS2 periods: {str(e)}")
            return Response(
                {"success": False, "error": f"Failed to fetch periods from DHIS2: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['get'])
    def dhis2_relative_periods(self, request):
        """
        Get relative periods from DHIS2 instance using the correct endpoint
        """
        try:
            # Get session data
            session_data = get_dhis2_session_data(request.session.session_key)
            if not session_data:
                return Response(
                    {"error": "Incomplete DHIS2 session data"},
                    status=status.HTTP_401_UNAUTHORIZED
                )
            
            # Create DHIS2 client
            client = DHIS2ClientFactory.create_client_from_session(
                session_data.get('instance_url'),
                request.session.session_key
            )
            
            # Get relative periods from DHIS2 using the correct endpoint
            relative_periods = client.get_relative_periods()
            
            return Response({
                "success": True,
                "data": relative_periods,
                "total": len(relative_periods)
            })
            
        except Exception as e:
            logger.error(f"Error fetching DHIS2 relative periods: {str(e)}")
            return Response(
                {"success": False, "error": f"Failed to fetch relative periods from DHIS2: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['get'])
    def dhis2_org_units(self, request):
        """
        Get organisation units from DHIS2 instance with optional hierarchy
        """
        try:
            # Get session data
            session_data = get_dhis2_session_data(request.session.session_key)
            if not session_data:
                return Response(
                    {"error": "Incomplete DHIS2 session data"},
                    status=status.HTTP_401_UNAUTHORIZED
                )
            
            # Get query parameters
            user_only = request.GET.get('user_only', 'false').lower() == 'true'
            include_children = request.GET.get('include_children', 'false').lower() == 'true'
            hierarchy = request.GET.get('hierarchy', 'false').lower() == 'true'
            root_id = request.GET.get('root_id')
            max_depth = int(request.GET.get('max_depth', '3'))
            
            # Create DHIS2 client
            client = DHIS2ClientFactory.create_client_from_session(
                session_data.get('instance_url'),
                request.session.session_key
            )
            
            # Get org units from DHIS2 based on parameters
            if hierarchy:
                # Get hierarchical structure for tree view
                org_units = client.get_org_unit_hierarchy(root_id, max_depth)
            elif user_only:
                # Get user's accessible org units
                org_units = client.get_user_accessible_org_units()
            else:
                # Get all org units with optional children
                org_units = client.get_org_units(include_children=include_children)
            
            return Response({
                "success": True,
                "org_units": org_units,
                "total": len(org_units)
            })
            
        except Exception as e:
            logger.error(f"Error fetching DHIS2 org units: {str(e)}")
            return Response(
                {"success": False, "error": f"Failed to fetch org units from DHIS2: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['get'])
    def generate_periods(self, request):
        """
        Generate periods for assessment based on period type and year
        This addresses DHIS2 API limitations by generating periods client-side
        """
        try:
            from datetime import datetime, timedelta
            import calendar
            
            # Get parameters
            period_type = request.query_params.get('period_type', 'Yearly')
            year = int(request.query_params.get('year', datetime.now().year))
            count = int(request.query_params.get('count', 10))  # Number of periods to generate
            
            periods = []
            
            if period_type == 'Yearly':
                # Generate yearly periods
                for i in range(count):
                    period_year = year - i
                    period = {
                        'id': str(period_year),
                        'name': str(period_year),
                        'display_name': str(period_year),
                        'period_type': 'Yearly',
                        'start_date': f"{period_year}-01-01",
                        'end_date': f"{period_year}-12-31",
                        'source': 'generated'
                    }
                    periods.append(period)
                    
            elif period_type == 'Quarterly':
                # Generate quarterly periods
                quarters = [
                    ('Q1', 1, 3),
                    ('Q2', 4, 6),
                    ('Q3', 7, 9),
                    ('Q4', 10, 12)
                ]
                
                for i in range(count):
                    period_year = year - (i // 4)
                    quarter_idx = i % 4
                    quarter_name, start_month, end_month = quarters[quarter_idx]
                    
                    # Get last day of end month
                    last_day = calendar.monthrange(period_year, end_month)[1]
                    
                    period = {
                        'id': f"{period_year}{quarter_name}",
                        'name': f"{period_year} {quarter_name}",
                        'display_name': f"{period_year} {quarter_name}",
                        'period_type': 'Quarterly',
                        'start_date': f"{period_year}-{start_month:02d}-01",
                        'end_date': f"{period_year}-{end_month:02d}-{last_day}",
                        'source': 'generated'
                    }
                    periods.append(period)
                    
            elif period_type == 'Monthly':
                # Generate monthly periods
                for i in range(count):
                    period_year = year - (i // 12)
                    month = 12 - (i % 12)
                    if month == 0:
                        month = 12
                        period_year -= 1
                    
                    # Get last day of month
                    last_day = calendar.monthrange(period_year, month)[1]
                    
                    period = {
                        'id': f"{period_year}{month:02d}",
                        'name': f"{period_year} {calendar.month_name[month]}",
                        'display_name': f"{period_year} {calendar.month_name[month]}",
                        'period_type': 'Monthly',
                        'start_date': f"{period_year}-{month:02d}-01",
                        'end_date': f"{period_year}-{month:02d}-{last_day}",
                        'source': 'generated'
                    }
                    periods.append(period)
                    
            elif period_type == 'Half-Yearly':
                # Generate half-yearly periods
                half_years = [
                    ('H1', 1, 6),
                    ('H2', 7, 12)
                ]
                
                for i in range(count):
                    period_year = year - (i // 2)
                    half_year_idx = i % 2
                    half_year_name, start_month, end_month = half_years[half_year_idx]
                    
                    # Get last day of end month
                    last_day = calendar.monthrange(period_year, end_month)[1]
                    
                    period = {
                        'id': f"{period_year}{half_year_name}",
                        'name': f"{period_year} {half_year_name}",
                        'display_name': f"{period_year} {half_year_name}",
                        'period_type': 'Half-Yearly',
                        'start_date': f"{period_year}-{start_month:02d}-01",
                        'end_date': f"{period_year}-{end_month:02d}-{last_day}",
                        'source': 'generated'
                    }
                    periods.append(period)
            
            return Response({
                "success": True,
                "data": periods,
                "total": len(periods),
                "period_type": period_type,
                "year": year
            })
            
        except Exception as e:
            logger.error(f"Error generating periods: {str(e)}")
            return Response(
                {"success": False, "error": f"Failed to generate periods: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['get'])
    def get_period_types(self, request):
        """
        Get available period types for assessment
        """
        try:
            period_types = [
                {
                    'id': 'Yearly',
                    'name': 'Yearly',
                    'display_name': 'Yearly',
                    'description': 'Annual periods (e.g., 2023, 2024, 2025)'
                },
                {
                    'id': 'Half-Yearly',
                    'name': 'Half-Yearly',
                    'display_name': 'Half-Yearly',
                    'description': 'Six-month periods (e.g., H1 2023, H2 2023)'
                },
                {
                    'id': 'Quarterly',
                    'name': 'Quarterly',
                    'display_name': 'Quarterly',
                    'description': 'Three-month periods (e.g., Q1 2023, Q2 2023)'
                },
                {
                    'id': 'Monthly',
                    'name': 'Monthly',
                    'display_name': 'Monthly',
                    'description': 'Monthly periods (e.g., Jan 2023, Feb 2023)'
                }
            ]
            
            return Response({
                "success": True,
                "data": period_types,
                "total": len(period_types)
            })
            
        except Exception as e:
            logger.error(f"Error getting period types: {str(e)}")
            return Response(
                {"success": False, "error": f"Failed to get period types: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['post'])
    def create_assessment_with_periods(self, request):
        """
        Create an assessment with multiple selected periods
        """
        try:
            from configurations.models import AssessmentPeriod
            
            # Get parameters from request
            selected_periods = request.data.get('selected_periods', [])
            org_unit_ids = request.data.get('org_unit_ids', [])
            assessment_name = request.data.get('assessment_name', 'Multi-Period Assessment')
            
            if not selected_periods or len(selected_periods) < 3:
                return Response({
                    'success': False,
                    'error': 'At least 3 periods must be selected for assessment'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            if not org_unit_ids:
                return Response({
                    'success': False,
                    'error': 'At least one organization unit must be selected'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Create assessment periods in database
            created_periods = []
            for period_data in selected_periods:
                period, created = AssessmentPeriod.objects.get_or_create(
                    name=period_data['name'],
                    defaults={
                        'period_type': period_data['period_type'],
                        'start_date': period_data['start_date'],
                        'end_date': period_data['end_date'],
                        'is_active': True
                    }
                )
                created_periods.append(period)
            
            # Trigger data sync for all periods
            sync_service = DataSyncService()
            
            # Get user's org unit from session if not specified
            if not org_unit_ids:
                session_key = request.session.session_key
                session_data = get_dhis2_session_data(session_key)
                if session_data and session_data.get('org_units'):
                    org_unit_ids = session_data.get('org_units')
            
            # Create sync request for all periods
            sync_request = {
                'sync_type': 'period',
                'org_unit_ids': org_unit_ids,
                'period_start': min(p.start_date for p in created_periods),
                'period_end': max(p.end_date for p in created_periods),
                'calculate_scores': True
            }
            
            # Get current DHIS2 user
            dhis2_user = get_dhis2_user_from_request(request)
            
            # Perform the sync
            sync_log = sync_service.sync_data(sync_request, dhis2_user, request.session.session_key)
            
            return Response({
                'success': True,
                'message': f'Assessment created with {len(created_periods)} periods',
                'assessment_name': assessment_name,
                'periods': [
                    {
                        'id': p.id,
                        'name': p.name,
                        'period_type': p.period_type,
                        'start_date': p.start_date,
                        'end_date': p.end_date
                    } for p in created_periods
                ],
                'org_units': org_unit_ids,
                'sync_log_id': sync_log.id
            })
            
        except Exception as e:
            logger.error(f"Error creating assessment with periods: {str(e)}")
            return Response({
                'success': False,
                'error': f'Failed to create assessment: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['get'])
    def dhis2_period_types(self, request):
        """
        Get period types from DHIS2 instance
        """
        try:
            # Get session data
            session_data = get_dhis2_session_data(request.session.session_key)
            if not session_data:
                return Response(
                    {"error": "Incomplete DHIS2 session data"},
                    status=status.HTTP_401_UNAUTHORIZED
                )
            
            # Create DHIS2 client
            client = DHIS2ClientFactory.create_client_from_session(
                session_data.get('instance_url'),
                request.session.session_key
            )
            
            # Get period types from DHIS2
            period_types = client.get_period_types()
            
            return Response({
                "success": True,
                "data": period_types,
                "total": len(period_types)
            })
            
        except Exception as e:
            logger.error(f"Error fetching DHIS2 period types: {str(e)}")
            return Response(
                {"success": False, "error": f"Failed to fetch period types from DHIS2: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['post'])
    def multi_period_assessment_data(self, request):
        """
        Get assessment data for multiple periods
        """
        try:
            from configurations.models import AssessmentPeriod
            
            # Get parameters from request
            org_unit_ids = request.data.get('org_unit_ids', [])
            periods = request.data.get('periods', [])
            include_scores = request.data.get('include_scores', True)
            
            if not org_unit_ids:
                return Response({
                    'success': False,
                    'error': 'No organization units specified'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            if not periods:
                return Response({
                    'success': False,
                    'error': 'No periods specified'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Get user's org unit from session if not specified
            if not org_unit_ids:
                session_key = request.session.session_key
                session_data = get_dhis2_session_data(session_key)
                if session_data and session_data.get('org_units'):
                    org_unit_ids = session_data.get('org_units')
            
            # Get all objectives with their indicators
            from configurations.models import Objective
            from indicators.models import TrackedIndicator
            
            objectives = Objective.objects.filter(is_active=True).order_by('order')
            
            # Build assessment data for each period
            assessment_data_list = []
            
            for period_data in periods:
                # Get or create assessment period
                period, created = AssessmentPeriod.objects.get_or_create(
                    name=period_data['name'],
                    defaults={
                        'period_type': period_data['period_type'],
                        'start_date': period_data['start_date'],
                        'end_date': period_data['end_date'],
                        'is_active': True
                    }
                )
                
                # Build assessment data for this period
                assessment_data = {
                    'org_unit_id': org_unit_ids[0] if org_unit_ids else 'unknown',
                    'org_unit_name': 'Unknown',  # Will be updated from session
                    'assessment_period': {
                        'id': period.id,
                        'name': period.name,
                        'start_date': period.start_date,
                        'end_date': period.end_date
                    },
                    'objectives': [],
                    'sector_score': None
                }
                
                # Get sector score if requested
                if include_scores:
                    sector_score = SectorScore.objects.filter(
                        org_unit_id=org_unit_ids[0],
                        assessment_period=period
                    ).first()
                    
                    if sector_score:
                        assessment_data['sector_score'] = {
                            'overall_score': sector_score.overall_score,
                            'score_color': sector_score.score_color,
                            'score_label': sector_score.score_label,
                            'total_objectives': sector_score.total_objectives,
                            'scored_objectives': sector_score.scored_objectives
                        }
                
                # Build objectives and indicators structure
                for objective in objectives:
                    objective_data = {
                        'id': objective.id,
                        'name': objective.name,
                        'code': objective.code,
                        'description': objective.description,
                        'color': objective.color,
                        'order': objective.order,
                        'milestone': {
                            'id': objective.milestone.id if objective.milestone else None,
                            'name': objective.milestone.name if objective.milestone else None,
                            'code': objective.milestone.code if objective.milestone else None,
                            'color': objective.milestone.color if objective.milestone else None,
                            'score': None  # Will be populated from MilestoneScore
                        } if objective.milestone else None,
                        'indicators': [],
                        'score': None
                    }
                    
                    # Get objective score if requested
                    if include_scores:
                        obj_score = ObjectiveScore.objects.filter(
                            objective=objective,
                            org_unit_id=org_unit_ids[0],
                            assessment_period=period
                        ).first()
                        
                        if obj_score:
                            objective_data['score'] = {
                                'final_score': obj_score.final_score,
                                'score_color': obj_score.score_color,
                                'score_label': obj_score.score_label,
                                'total_indicators': obj_score.total_indicators,
                                'scored_indicators': obj_score.scored_indicators
                            }
                    
                    # Get milestone score if milestone exists
                    if objective.milestone and objective_data['milestone']:
                        milestone_score = MilestoneScore.objects.filter(
                            milestone=objective.milestone,
                            org_unit_id=org_unit_ids[0],
                            assessment_period=period
                        ).first()
                        
                        if milestone_score:
                            objective_data['milestone']['score'] = milestone_score.score
                            objective_data['milestone']['score_color'] = milestone_score.score_color
                            objective_data['milestone']['score_label'] = milestone_score.score_label
                        else:
                            # Set default values if no milestone score exists
                            objective_data['milestone']['score'] = -2
                            objective_data['milestone']['score_color'] = '#dc3545'
                            objective_data['milestone']['score_label'] = 'Severely Underperforming'
                    
                    # Get indicators for this objective
                    indicators = TrackedIndicator.objects.filter(
                        objective_weights__objective=objective,
                        is_active=True
                    ).order_by('display_order', 'indicator_number')
                    
                    for indicator in indicators:
                        indicator_data = {
                            'id': indicator.id,
                            'name': indicator.name,
                            'dhis2_uid': indicator.dhis2_uid,
                            'description': indicator.description,
                            'indicator_number': indicator.indicator_number,
                            'display_order': indicator.display_order,
                            'target_value': indicator.target_value,
                            'target_type': indicator.target_type,
                            'weight': 1.0,  # Default weight
                            'score': None,
                            'data_values': {}
                        }
                        
                        # Get indicator weight
                        weight_mapping = indicator.objective_weights.filter(objective=objective).first()
                        if weight_mapping:
                            indicator_data['weight'] = weight_mapping.weight
                        
                        # Get indicator score if requested
                        if include_scores:
                            ind_score = IndicatorScore.objects.filter(
                                indicator=indicator,
                                objective=objective,
                                org_unit_id=org_unit_ids[0],
                                assessment_period=period
                            ).first()
                            
                            if ind_score:
                                indicator_data['score'] = {
                                    'score': ind_score.score,
                                    'score_color': ind_score.score_color,
                                    'score_label': ind_score.score_label,
                                    'current_value': ind_score.current_value,
                                    'previous_value': ind_score.previous_value,
                                    'target_gap': ind_score.target_gap,
                                    'percent_change': ind_score.percent_change,
                                    'is_manual_override': ind_score.is_manual_override
                                }
                        
                        # Get data values for the specific period
                        data_point = IndicatorData.objects.filter(
                            indicator=indicator,
                            org_unit_id=org_unit_ids[0],
                            period=period.name
                        ).first()
                        
                        if data_point:
                            indicator_data['data_values'][period.name] = {
                                'value': data_point.value,
                                'calculated_value': data_point.calculated_value,
                                'created_at': data_point.created_at.isoformat() if data_point.created_at else None
                            }
                        else:
                            # Initialize empty data for the period
                            indicator_data['data_values'][period.name] = {
                                'value': None,
                                'calculated_value': None,
                                'created_at': None
                            }
                        
                        objective_data['indicators'].append(indicator_data)
                    
                    assessment_data['objectives'].append(objective_data)
                
                assessment_data_list.append(assessment_data)
            
            return Response(assessment_data_list)
            
        except Exception as e:
            logger.error(f"Error getting multi-period assessment data: {str(e)}")
            return Response({
                'success': False,
                'error': f'Failed to get assessment data: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['get'])
    def test_dhis2_connection(self, request):
        """
        Test DHIS2 connection and get system info
        """
        try:
            # Get session data
            session_data = get_dhis2_session_data(request.session.session_key)
            if not session_data:
                return Response(
                    {"error": "Incomplete DHIS2 session data"},
                    status=status.HTTP_401_UNAUTHORIZED
                )
            
            # Create DHIS2 client
            client = DHIS2ClientFactory.create_client_from_session(
                session_data.get('instance_url'),
                request.session.session_key
            )
            
            # Test connection
            connection_ok = client.test_connection()
            
            # Get system info
            system_info = client.get_system_info()
            api_version = client.get_api_version()
            
            # Get counts
            periods_count = len(client.get_periods())
            org_units_count = len(client.get_org_units())
            period_types_count = len(client.get_period_types())
            
            return Response({
                "success": True,
                "connection": {
                    "status": "connected" if connection_ok else "failed",
                    "instance_url": session_data.get('instance_url'),
                    "api_version": api_version
                },
                "system_info": system_info,
                "counts": {
                    "periods": periods_count,
                    "org_units": org_units_count,
                    "period_types": period_types_count
                }
            })
            
        except Exception as e:
            logger.error(f"Error testing DHIS2 connection: {str(e)}")
            return Response(
                {"success": False, "error": f"Failed to test DHIS2 connection: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class HolisticAssessmentViewSet(viewsets.ViewSet):
    """
    ViewSet for real-time holistic assessment data
    """
    permission_classes = [IsAuthenticated]
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.realtime_service = RealTimeDHIS2Service()
        self.save_service = AssessmentSaveService()
    
    @action(detail=False, methods=['post'])
    def fetch_data(self, request):
        """
        Fetch real-time DHIS2 data for holistic assessment
        No database storage - just fetch and return for immediate display
        """
        try:
            # Validate request data
            serializer = HolisticAssessmentRequestSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            
            assessment_config = serializer.validated_data
            
            # Fetch real-time data
            assessment_data = self.realtime_service.fetch_holistic_assessment_data(
                request, assessment_config
            )
            
            return Response(assessment_data)
            
        except ValidationError as e:
            return Response({
                'status': 'error',
                'message': str(e)
            }, status=400)
        except Exception as e:
            logger.error(f"Error fetching holistic assessment data: {str(e)}")
            return Response({
                'status': 'error',
                'message': 'Failed to fetch assessment data'
            }, status=500)
    
    @action(detail=False, methods=['post'])
    def export_excel(self, request):
        """Generate and return a path/URL for a formatted Excel export that mirrors the UI."""
        try:
            # Reuse the fetch logic to get payload (no DB write)
            serializer = HolisticAssessmentRequestSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            payload = self.realtime_service.fetch_holistic_assessment_data(request, serializer.validated_data)
            file_path = self.realtime_service.generate_holistic_excel(payload)
            from django.conf import settings
            media_url = getattr(settings, 'MEDIA_URL', '/media/')
            # Build absolute URL so the frontend can open the file directly
            rel_path = file_path.split('media')[-1].lstrip('\\/')
            absolute_url = request.build_absolute_uri(f"{media_url}{rel_path.replace('\\', '/')}")
            return Response({
                'status': 'success',
                'file_path': file_path,
                'file_url': absolute_url
            })
        except ValidationError as e:
            return Response({'status': 'error', 'message': str(e)}, status=400)
        except Exception as e:
            logger.error(f"Error exporting holistic excel: {e}")
            return Response({'status': 'error', 'message': 'Failed to export Excel'}, status=500)

    @action(detail=False, methods=['post'])
    def save_assessment(self, request):
        """
        Save a user-generated holistic assessment
        """
        try:
            # Validate request data
            serializer = HolisticAssessmentSaveSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            
            assessment_data = serializer.validated_data
            
            # Save assessment
            saved_assessment = self.save_service.save_assessment(request, assessment_data)
            
            return Response({
                'status': 'success',
                'message': 'Assessment saved successfully',
                'assessment_id': saved_assessment.get('id')
            })
            
        except Exception as e:
            logger.error(f"Error saving assessment: {str(e)}")
            return Response({
                'status': 'error',
                'message': 'Failed to save assessment'
            }, status=500)
    
    @action(detail=False, methods=['get'])
    def get_saved_assessments(self, request):
        """
        Get saved assessments for the current user
        """
        try:
            org_unit_id = request.query_params.get('org_unit_id')
            payload = self.save_service.get_user_assessments(request, org_unit_id)
            if isinstance(payload, dict) and 'results' in payload:
                return Response({ 'status': 'success', **payload })
            # Backward compatibility if service returns list
            return Response({ 'status': 'success', 'results': payload, 'count': len(payload), 'page': 1, 'size': len(payload) })
            
        except Exception as e:
            logger.error(f"Error retrieving saved assessments: {str(e)}")
            return Response({
                'status': 'error',
                'message': 'Failed to retrieve assessments'
            }, status=500)
    
    @action(detail=True, methods=['get'])
    def get_assessment(self, request, pk=None):
        """
        Get a specific saved assessment
        """
        try:
            assessment = self.save_service.get_assessment_by_id(request, pk)
            
            if not assessment:
                return Response({
                    'status': 'error',
                    'message': 'Assessment not found'
                }, status=404)
            
            return Response({
                'status': 'success',
                'assessment': assessment
            })
            
        except Exception as e:
            logger.error(f"Error retrieving assessment {pk}: {str(e)}")
            return Response({
                'status': 'error',
                'message': 'Failed to retrieve assessment'
            }, status=500)

    @action(detail=True, methods=['put'])
    def update_assessment(self, request, pk=None):
        """
        Update a specific saved assessment
        """
        try:
            # Validate request data
            serializer = HolisticAssessmentSaveSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            
            assessment_data = serializer.validated_data
            
            # Update assessment
            updated_assessment = self.save_service.update_assessment(request, pk, assessment_data)
            
            if not updated_assessment:
                return Response({
                    'status': 'error',
                    'message': 'Assessment not found or you are not authorized to update it'
                }, status=404)
            
            return Response({
                'status': 'success',
                'message': 'Assessment updated successfully',
                'assessment': updated_assessment
            })
            
        except ValidationError as e:
            return Response({
                'status': 'error',
                'message': str(e)
            }, status=400)
        except Exception as e:
            logger.error(f"Error updating assessment {pk}: {str(e)}")
            return Response({
                'status': 'error',
                'message': 'Failed to update assessment'
            }, status=500)

    @action(detail=True, methods=['delete'])
    def delete_assessment(self, request, pk=None):
        """
        Delete a specific saved assessment
        """
        try:
            deleted = self.save_service.delete_assessment(request, pk)
            if not deleted:
                return Response({'status': 'error', 'message': 'Assessment not found'}, status=404)
            return Response({'status': 'success', 'message': 'Assessment deleted'})
        except Exception as e:
            logger.error(f"Error deleting assessment {pk}: {str(e)}")
            return Response({'status': 'error', 'message': 'Failed to delete assessment'}, status=500)


class AuditLogViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for audit logs - read-only to maintain audit trail integrity
    """
    queryset = AuditLog.objects.all()
    serializer_class = AuditLogSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Filter audit logs based on query parameters"""
        queryset = AuditLog.objects.all()
        
        # Apply filters
        action_type = self.request.query_params.get('action_type')
        if action_type:
            queryset = queryset.filter(action_type=action_type)
        
        entity_type = self.request.query_params.get('entity_type')
        if entity_type:
            queryset = queryset.filter(entity_type=entity_type)
        
        change_reason = self.request.query_params.get('change_reason')
        if change_reason:
            queryset = queryset.filter(change_reason=change_reason)
        
        user_id = self.request.query_params.get('user_id')
        if user_id:
            queryset = queryset.filter(user_id=user_id)
        
        org_unit_id = self.request.query_params.get('org_unit_id')
        if org_unit_id:
            queryset = queryset.filter(org_unit_id=org_unit_id)
        
        assessment_period = self.request.query_params.get('assessment_period')
        if assessment_period:
            queryset = queryset.filter(assessment_period=assessment_period)
        
        start_date = self.request.query_params.get('start_date')
        if start_date:
            queryset = queryset.filter(created_at__date__gte=start_date)
        
        end_date = self.request.query_params.get('end_date')
        if end_date:
            queryset = queryset.filter(created_at__date__lte=end_date)
        
        is_conflict_resolution = self.request.query_params.get('is_conflict_resolution')
        if is_conflict_resolution is not None:
            queryset = queryset.filter(is_conflict_resolution=is_conflict_resolution.lower() == 'true')
        
        return queryset.order_by('-created_at')
    
    @action(detail=False, methods=['get'])
    def summary(self, request):
        """Get audit log summary statistics"""
        queryset = self.get_queryset()
        
        summary = {
            'total_logs': queryset.count(),
            'action_types': {},
            'entity_types': {},
            'change_reasons': {},
            'recent_activity': [],
            'conflict_resolutions': queryset.filter(is_conflict_resolution=True).count()
        }
        
        # Action type distribution
        for action_type, _ in AuditLog.ActionType.choices:
            summary['action_types'][action_type] = queryset.filter(action_type=action_type).count()
        
        # Entity type distribution
        for entity_type, _ in AuditLog.EntityType.choices:
            summary['entity_types'][entity_type] = queryset.filter(entity_type=entity_type).count()
        
        # Change reason distribution
        for change_reason, _ in AuditLog.ChangeReason.choices:
            summary['change_reasons'][change_reason] = queryset.filter(change_reason=change_reason).count()
        
        # Recent activity (last 10 logs)
        recent_logs = queryset[:10]
        summary['recent_activity'] = AuditLogSerializer(recent_logs, many=True).data
        
        return Response(summary)
    
    @action(detail=False, methods=['post'])
    def export(self, request):
        """Export audit logs to CSV"""
        from django.http import HttpResponse
        import csv
        
        queryset = self.get_queryset()
        
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="audit_logs_{timezone.now().strftime("%Y%m%d_%H%M%S")}.csv"'
        
        writer = csv.writer(response)
        writer.writerow([
            'ID', 'Action Type', 'Entity Type', 'Entity ID', 'User', 
            'Change Reason', 'Description', 'Org Unit', 'Assessment Period',
            'Created At', 'Old Values', 'New Values', 'Changed Fields'
        ])
        
        for log in queryset:
            writer.writerow([
                log.id, log.action_type, log.entity_type, log.entity_id,
                log.user.username if log.user else 'System',
                log.change_reason, log.change_description, log.org_unit_name,
                log.assessment_period, log.created_at,
                str(log.old_values), str(log.new_values), str(log.changed_fields)
            ])
        
        return response


class ConflictResolutionViewSet(viewsets.ModelViewSet):
    """
    ViewSet for conflict resolutions
    """
    queryset = ConflictResolution.objects.all()
    serializer_class = ConflictResolutionSerializer
    permission_classes = [IsAuthenticated]
    
    def get_serializer_class(self):
        """Return appropriate serializer based on action"""
        if self.action == 'create':
            return ConflictResolutionCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return ConflictResolutionUpdateSerializer
        return ConflictResolutionSerializer
    
    def get_queryset(self):
        """Filter conflict resolutions based on query parameters"""
        queryset = ConflictResolution.objects.all()
        
        # Apply filters
        conflict_type = self.request.query_params.get('conflict_type')
        if conflict_type:
            queryset = queryset.filter(conflict_type=conflict_type)
        
        entity_type = self.request.query_params.get('entity_type')
        if entity_type:
            queryset = queryset.filter(entity_type=entity_type)
        
        resolution_status = self.request.query_params.get('resolution_status')
        if resolution_status:
            queryset = queryset.filter(resolution_status=resolution_status)
        
        resolution_method = self.request.query_params.get('resolution_method')
        if resolution_method:
            queryset = queryset.filter(resolution_method=resolution_method)
        
        org_unit_id = self.request.query_params.get('org_unit_id')
        if org_unit_id:
            queryset = queryset.filter(org_unit_id=org_unit_id)
        
        assessment_period = self.request.query_params.get('assessment_period')
        if assessment_period:
            queryset = queryset.filter(assessment_period=assessment_period)
        
        start_date = self.request.query_params.get('start_date')
        if start_date:
            queryset = queryset.filter(detected_at__date__gte=start_date)
        
        end_date = self.request.query_params.get('end_date')
        if end_date:
            queryset = queryset.filter(detected_at__date__lte=end_date)
        
        return queryset.order_by('-detected_at')
    
    def perform_create(self, serializer):
        """Create conflict resolution with audit logging"""
        conflict = serializer.save()
        
        # Log the conflict detection
        AuditLog.log_change(
            action_type=AuditLog.ActionType.CREATE,
            entity_type=AuditLog.EntityType.DATA_SYNC,
            entity_id=conflict.id,
            user=self.request.user,
            change_reason=AuditLog.ChangeReason.DATA_CORRECTION,
            change_description=f"Conflict detected: {conflict.conflict_type} for {conflict.entity_type}",
            is_conflict_resolution=True,
            conflict_type=conflict.conflict_type,
            org_unit_id=conflict.org_unit_id,
            assessment_period=conflict.assessment_period
        )
    
    def perform_update(self, serializer):
        """Update conflict resolution with audit logging"""
        old_status = self.get_object().resolution_status
        conflict = serializer.save()
        
        if conflict.resolution_status != old_status:
            # Log the resolution
            AuditLog.log_change(
                action_type=AuditLog.ActionType.UPDATE,
                entity_type=AuditLog.EntityType.DATA_SYNC,
                entity_id=conflict.id,
                user=self.request.user,
                change_reason=AuditLog.ChangeReason.DATA_CORRECTION,
                change_description=f"Conflict resolved: {conflict.resolution_method}",
                is_conflict_resolution=True,
                conflict_type=conflict.conflict_type,
                resolution_method=conflict.resolution_method,
                org_unit_id=conflict.org_unit_id,
                assessment_period=conflict.assessment_period
            )
    
    @action(detail=False, methods=['get'])
    def summary(self, request):
        """Get conflict resolution summary statistics"""
        queryset = self.get_queryset()
        
        summary = {
            'total_conflicts': queryset.count(),
            'conflict_types': {},
            'resolution_statuses': {},
            'resolution_methods': {},
            'pending_conflicts': queryset.filter(resolution_status=ConflictResolution.ResolutionStatus.PENDING).count(),
            'resolved_conflicts': queryset.filter(resolution_status=ConflictResolution.ResolutionStatus.RESOLVED).count(),
            'escalated_conflicts': queryset.filter(resolution_status=ConflictResolution.ResolutionStatus.ESCALATED).count()
        }
        
        # Conflict type distribution
        for conflict_type, _ in ConflictResolution.ConflictType.choices:
            summary['conflict_types'][conflict_type] = queryset.filter(conflict_type=conflict_type).count()
        
        # Resolution status distribution
        for status, _ in ConflictResolution.ResolutionStatus.choices:
            summary['resolution_statuses'][status] = queryset.filter(resolution_status=status).count()
        
        # Resolution method distribution
        for method, _ in ConflictResolution.ResolutionMethod.choices:
            summary['resolution_methods'][method] = queryset.filter(resolution_method=method).count()
        
        return Response(summary)
    
    @action(detail=True, methods=['post'])
    def resolve(self, request, pk=None):
        """Resolve a specific conflict"""
        conflict = self.get_object()
        
        serializer = ConflictResolutionUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # Resolve the conflict
        conflict.resolution_method = serializer.validated_data.get('resolution_method', conflict.resolution_method)
        conflict.resolution_status = ConflictResolution.ResolutionStatus.RESOLVED
        conflict.resolution_notes = serializer.validated_data.get('resolution_notes', '')
        conflict.resolved_by = request.user
        conflict.resolved_at = timezone.now()
        conflict.save()
        
        # Log the resolution
        AuditLog.log_change(
            action_type=AuditLog.ActionType.UPDATE,
            entity_type=AuditLog.EntityType.DATA_SYNC,
            entity_id=conflict.id,
            user=request.user,
            change_reason=AuditLog.ChangeReason.DATA_CORRECTION,
            change_description=f"Conflict resolved: {conflict.resolution_method}",
            is_conflict_resolution=True,
            conflict_type=conflict.conflict_type,
            resolution_method=conflict.resolution_method,
            org_unit_id=conflict.org_unit_id,
            assessment_period=conflict.assessment_period
        )
        
        return Response({
            'status': 'success',
            'message': 'Conflict resolved successfully',
            'conflict': ConflictResolutionSerializer(conflict).data
        })


class ManualOverrideViewSet(viewsets.ViewSet):
    """
    ViewSet for handling manual overrides
    """
    permission_classes = [IsAuthenticated]
    
    @action(detail=False, methods=['post'])
    def apply_override(self, request):
        """Apply a manual override to an indicator score"""
        serializer = ManualOverrideSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        data = serializer.validated_data
        
        try:
            with transaction.atomic():
                # Find the indicator score
                indicator_score = IndicatorScore.objects.get(id=data['entity_id'])
                
                # Apply the manual override
                indicator_score.apply_manual_override(
                    new_score=data['score'],
                    user=request.user,
                    reason=data['reason']
                )
                
                return Response({
                    'status': 'success',
                    'message': 'Manual override applied successfully',
                    'indicator_score': IndicatorScoreSerializer(indicator_score).data
                })
                
        except IndicatorScore.DoesNotExist:
            return Response({
                'status': 'error',
                'message': 'Indicator score not found'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Error applying manual override: {str(e)}")
            return Response({
                'status': 'error',
                'message': 'Failed to apply manual override'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['post'])
    def clear_override(self, request):
        """Clear a manual override from an indicator score"""
        entity_id = request.data.get('entity_id')
        reason = request.data.get('reason', '')
        
        if not entity_id:
            return Response({
                'status': 'error',
                'message': 'Entity ID is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            with transaction.atomic():
                # Find the indicator score
                indicator_score = IndicatorScore.objects.get(id=entity_id)
                
                # Clear the manual override
                indicator_score.clear_manual_override(
                    user=request.user,
                    reason=reason
                )
                
                return Response({
                    'status': 'success',
                    'message': 'Manual override cleared successfully',
                    'indicator_score': IndicatorScoreSerializer(indicator_score).data
                })
                
        except IndicatorScore.DoesNotExist:
            return Response({
                'status': 'error',
                'message': 'Indicator score not found'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Error clearing manual override: {str(e)}")
            return Response({
                'status': 'error',
                'message': 'Failed to clear manual override'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)