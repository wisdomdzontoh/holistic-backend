from rest_framework import status, viewsets, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from django.db import transaction
from django.db.models import Count, Sum
from django.utils import timezone

from .models import (
    Milestone, Objective, ScoringRule, WeightingScheme, ObjectiveWeight, 
    IndicatorWeight, AssessmentPeriod, SystemConfiguration
)
from .serializers import (
    MilestoneSerializer, MilestoneCreateSerializer,
    ObjectiveSerializer, ObjectiveCreateSerializer,
    ScoringRuleSerializer, ScoringRuleCreateSerializer,
    WeightingSchemeSerializer, WeightingSchemeCreateSerializer,
    ObjectiveWeightSerializer, ObjectiveWeightCreateSerializer,
    IndicatorWeightSerializer, IndicatorWeightCreateSerializer,
    AssessmentPeriodSerializer, AssessmentPeriodCreateSerializer,
    SystemConfigurationSerializer, SystemConfigurationCreateSerializer,
    BulkObjectiveWeightSerializer, BulkIndicatorWeightSerializer,
    ConfigurationValidationSerializer, ConfigurationSummarySerializer
)
from indicators.models import TrackedIndicator


class MilestoneViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing milestones
    """
    queryset = Milestone.objects.all()
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['is_active', 'score']
    search_fields = ['name', 'description', 'code']
    ordering_fields = ['name', 'order', 'created_at']
    ordering = ['order', 'name']
    
    def get_serializer_class(self):
        """Return appropriate serializer class based on action"""
        if self.action == 'create':
            return MilestoneCreateSerializer
        return MilestoneSerializer
    
    @action(detail=True, methods=['patch'])
    def update_score(self, request, pk=None):
        """
        Update the score of a milestone for a specific assessment
        """
        milestone = self.get_object()
        score = request.data.get('score')
        org_unit_id = request.data.get('org_unit_id')
        assessment_period_id = request.data.get('assessment_period_id')
        
        if score is None:
            return Response(
                {'error': 'Score is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if not org_unit_id:
            return Response(
                {'error': 'org_unit_id is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if not assessment_period_id:
            return Response(
                {'error': 'assessment_period_id is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            score = int(score)
            if score < -2 or score > 2:
                return Response(
                    {'error': 'Score must be between -2 and 2'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
        except (ValueError, TypeError):
            return Response(
                {'error': 'Score must be a valid integer'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get or create the milestone score for this assessment
        from assessments.models import MilestoneScore
        from .models import AssessmentPeriod
        
        try:
            assessment_period = AssessmentPeriod.objects.get(id=assessment_period_id)
        except AssessmentPeriod.DoesNotExist:
            return Response(
                {'error': 'Assessment period not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Get the actual DHIS2User instance from the wrapper
        dhis2_user = None
        if hasattr(request, 'user') and hasattr(request.user, 'dhis2_user'):
            dhis2_user = request.user.dhis2_user
        
        milestone_score, created = MilestoneScore.objects.get_or_create(
            milestone=milestone,
            org_unit_id=org_unit_id,
            assessment_period=assessment_period,
            defaults={
                'objective': milestone.objectives.first(),
                'org_unit_name': request.data.get('org_unit_name', ''),
                'score': score,
                'override_user': dhis2_user
            }
        )
        
        if not created:
            # Update existing milestone score
            milestone_score.update_score(score, dhis2_user)
        else:
            # Set the objective for newly created milestone score
            if milestone.objectives.exists():
                milestone_score.objective = milestone.objectives.first()
                milestone_score.save()
        
        return Response({
            'id': milestone_score.id,
            'milestone_id': milestone.id,
            'milestone_name': milestone.name,
            'score': milestone_score.score,
            'score_color': milestone_score.score_color,
            'score_label': milestone_score.score_label,
            'message': 'Milestone score updated successfully'
        })
    
    @action(detail=True, methods=['post'])
    def toggle_active(self, request, pk=None):
        """
        Toggle the active status of a milestone
        """
        milestone = self.get_object()
        milestone.is_active = not milestone.is_active
        milestone.save()
        
        return Response({
            'success': True,
            'message': f'Milestone {"activated" if milestone.is_active else "deactivated"} successfully',
            'is_active': milestone.is_active
        })


class ObjectiveViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing objectives
    """
    queryset = Objective.objects.all()
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['is_active']
    search_fields = ['name', 'description', 'code']
    ordering_fields = ['name', 'order', 'created_at']
    ordering = ['order', 'name']
    
    def get_serializer_class(self):
        """Return appropriate serializer class based on action"""
        if self.action == 'create':
            return ObjectiveCreateSerializer
        return ObjectiveSerializer
    
    @action(detail=True, methods=['get'])
    def indicators(self, request, pk=None):
        """
        Get all indicators assigned to this objective
        """
        objective = self.get_object()
        indicator_weights = objective.indicator_weights.select_related('indicator')
        
        serializer = IndicatorWeightSerializer(indicator_weights, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def assign_indicators(self, request, pk=None):
        """
        Assign indicators to this objective with weights
        """
        objective = self.get_object()
        indicator_data = request.data.get('indicators', [])
        
        if not indicator_data:
            return Response(
                {'error': 'No indicators provided'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        created_weights = []
        errors = []
        
        with transaction.atomic():
            for data in indicator_data:
                indicator_id = data.get('indicator_id')
                weight = data.get('weight', 1.0)
                
                try:
                    indicator = TrackedIndicator.objects.get(id=indicator_id)
                    
                    # Create or update weight
                    weight_obj, created = IndicatorWeight.objects.update_or_create(
                        objective=objective,
                        indicator=indicator,
                        defaults={'weight': weight}
                    )
                    
                    created_weights.append(weight_obj)
                    
                except TrackedIndicator.DoesNotExist:
                    errors.append(f"Indicator {indicator_id} not found")
                except Exception as e:
                    errors.append(f"Error assigning indicator {indicator_id}: {str(e)}")
        
        return Response({
            'success': True,
            'assigned_count': len(created_weights),
            'errors': errors,
            'weights': IndicatorWeightSerializer(created_weights, many=True).data
        })
    
    @action(detail=True, methods=['post'])
    def toggle_active(self, request, pk=None):
        """
        Toggle the active status of an objective
        """
        objective = self.get_object()
        objective.is_active = not objective.is_active
        objective.save()
        
        return Response({
            'success': True,
            'message': f'Objective {"activated" if objective.is_active else "deactivated"} successfully',
            'is_active': objective.is_active
        })
    
    @action(detail=False, methods=['get'])
    def with_indicators(self, request):
        """
        Get objectives with their indicators for the definitions page
        """
        try:
            from indicators.models import TrackedIndicator
            
            objectives = Objective.objects.filter(is_active=True).order_by('order')
            result = []
            
            for objective in objectives:
                # Get indicators for this objective
                indicators = TrackedIndicator.objects.filter(
                    objective_weights__objective=objective
                ).order_by('display_order', 'name')
                
                objective_data = {
                    'id': objective.id,
                    'name': objective.name,
                    'code': objective.code,
                    'description': objective.description,
                    'color': objective.color,
                    'order': objective.order,
                    'indicators': []
                }
                
                for indicator in indicators:
                    indicator_data = {
                        'id': indicator.id,
                        'name': indicator.name,
                        'dhis2_uid': indicator.dhis2_uid,
                        'indicator_number': indicator.indicator_number,
                        'display_order': indicator.display_order,
                        'description': indicator.description,
                        'numerator': indicator.numerator,
                        'denominator': indicator.denominator,
                        'formula': indicator.formula,
                        'source_of_data': indicator.source_of_data,
                        'target_display': indicator.target_display,
                        'target_value': indicator.target_value,
                        'target_type': indicator.target_type,
                        'is_active': indicator.is_active,
                        'indicator_type': indicator.indicator_type
                    }
                    objective_data['indicators'].append(indicator_data)
                
                result.append(objective_data)
            
            return Response({
                'objectives': result,
                'total_objectives': len(result),
                'total_indicators': sum(len(obj['indicators']) for obj in result)
            })
            
        except Exception as e:
            return Response({
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ScoringRuleViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing scoring rules
    """
    queryset = ScoringRule.objects.all()
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['performance_type', 'is_active', 'score']
    search_fields = ['name', 'label']
    ordering_fields = ['performance_type', 'priority', 'min_value', 'score']
    ordering = ['performance_type', 'priority', 'min_value']
    
    def get_serializer_class(self):
        """Return appropriate serializer class based on action"""
        if self.action == 'create':
            return ScoringRuleCreateSerializer
        return ScoringRuleSerializer
    
    @action(detail=False, methods=['post'])
    def evaluate_value(self, request):
        """
        Evaluate a value against scoring rules
        """
        value = request.data.get('value')
        performance_type = request.data.get('performance_type', 'gap')
        
        if value is None:
            return Response(
                {'error': 'Value is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            value = float(value)
        except (ValueError, TypeError):
            return Response(
                {'error': 'Value must be a number'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Find matching rules
        matching_rules = ScoringRule.objects.filter(
            performance_type=performance_type,
            is_active=True
        ).order_by('-priority', 'min_value')
        
        matched_rule = None
        for rule in matching_rules:
            if rule.matches_value(value):
                matched_rule = rule
                break
        
        if matched_rule:
            return Response({
                'value': value,
                'performance_type': performance_type,
                'matched_rule': ScoringRuleSerializer(matched_rule).data,
                'score': matched_rule.score,
                'color': matched_rule.color,
                'label': matched_rule.label
            })
        else:
            return Response({
                'value': value,
                'performance_type': performance_type,
                'matched_rule': None,
                'score': 0,
                'color': '#6c757d',
                'label': 'No Match'
            })
    
    @action(detail=True, methods=['post'])
    def toggle_active(self, request, pk=None):
        """
        Toggle the active status of a scoring rule
        """
        rule = self.get_object()
        rule.is_active = not rule.is_active
        rule.save()
        
        return Response({
            'success': True,
            'message': f'Scoring rule {"activated" if rule.is_active else "deactivated"} successfully',
            'is_active': rule.is_active
        })


class WeightingSchemeViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing weighting schemes
    """
    queryset = WeightingScheme.objects.all()
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['is_active', 'is_default']
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'created_at']
    ordering = ['-is_default', 'name']
    
    def get_serializer_class(self):
        """Return appropriate serializer class based on action"""
        if self.action == 'create':
            return WeightingSchemeCreateSerializer
        return WeightingSchemeSerializer
    
    @action(detail=True, methods=['get'])
    def objectives(self, request, pk=None):
        """
        Get all objectives in this weighting scheme
        """
        scheme = self.get_object()
        objective_weights = scheme.objective_weights.select_related('objective')
        
        serializer = ObjectiveWeightSerializer(objective_weights, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def assign_objectives(self, request, pk=None):
        """
        Assign objectives to this weighting scheme with weights
        """
        scheme = self.get_object()
        serializer = BulkObjectiveWeightSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST
            )
        
        weights_data = serializer.validated_data['weights']
        created_weights = []
        errors = []
        
        with transaction.atomic():
            for weight_data in weights_data:
                objective_id = weight_data.get('objective_id')
                weight = weight_data.get('weight')
                
                try:
                    objective = Objective.objects.get(id=objective_id)
                    
                    # Create or update weight
                    weight_obj, created = ObjectiveWeight.objects.update_or_create(
                        scheme=scheme,
                        objective=objective,
                        defaults={'weight': weight}
                    )
                    
                    created_weights.append(weight_obj)
                    
                except Objective.DoesNotExist:
                    errors.append(f"Objective {objective_id} not found")
                except Exception as e:
                    errors.append(f"Error assigning objective {objective_id}: {str(e)}")
        
        return Response({
            'success': True,
            'assigned_count': len(created_weights),
            'errors': errors,
            'weights': ObjectiveWeightSerializer(created_weights, many=True).data
        })
    
    @action(detail=True, methods=['post'])
    def normalize_weights(self, request, pk=None):
        """
        Normalize objective weights in this scheme
        """
        scheme = self.get_object()
        objective_weights = scheme.objective_weights.all()
        
        if not objective_weights.exists():
            return Response(
                {'error': 'No objectives assigned to this scheme'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        total_weight = sum(ow.weight for ow in objective_weights)
        
        if total_weight <= 0:
            return Response(
                {'error': 'Total weight must be greater than 0'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        with transaction.atomic():
            for weight_obj in objective_weights:
                weight_obj.weight = weight_obj.weight / total_weight
                weight_obj.save()
        
        return Response({
            'success': True,
            'message': f'Weights normalized for {objective_weights.count()} objectives',
            'total_weight_before': total_weight,
            'total_weight_after': 1.0
        })


class ObjectiveWeightViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing objective weights
    """
    queryset = ObjectiveWeight.objects.all()
    serializer_class = ObjectiveWeightSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['scheme', 'objective']
    ordering_fields = ['weight']
    ordering = ['scheme', 'objective__order']


class IndicatorWeightViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing indicator weights
    """
    queryset = IndicatorWeight.objects.all()
    serializer_class = IndicatorWeightSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['objective', 'indicator']
    ordering_fields = ['weight']
    ordering = ['objective__order', 'weight']


class AssessmentPeriodViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing assessment periods
    """
    queryset = AssessmentPeriod.objects.all()
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['period_type', 'is_active', 'is_current']
    search_fields = ['name']
    ordering_fields = ['start_date', 'end_date', 'created_at']
    ordering = ['-start_date']
    
    def get_serializer_class(self):
        """Return appropriate serializer class based on action"""
        if self.action == 'create':
            return AssessmentPeriodCreateSerializer
        return AssessmentPeriodSerializer
    
    @action(detail=False, methods=['get'])
    def current(self, request):
        """
        Get the current assessment period
        """
        current_period = AssessmentPeriod.objects.filter(is_current=True).first()
        
        if current_period:
            serializer = AssessmentPeriodSerializer(current_period)
            return Response(serializer.data)
        else:
            return Response(
                {'error': 'No current assessment period set'},
                status=status.HTTP_404_NOT_FOUND
            )
    
    @action(detail=True, methods=['post'])
    def set_current(self, request, pk=None):
        """
        Set this period as the current assessment period
        """
        period = self.get_object()
        period.is_current = True
        period.save()
        
        return Response({
            'success': True,
            'message': f'{period.name} set as current assessment period'
        })


class SystemConfigurationViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing system configurations
    """
    queryset = SystemConfiguration.objects.all()
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['config_type', 'is_active']
    search_fields = ['key', 'description']
    ordering_fields = ['config_type', 'key']
    ordering = ['config_type', 'key']
    
    def get_serializer_class(self):
        """Return appropriate serializer class based on action"""
        if self.action == 'create':
            return SystemConfigurationCreateSerializer
        return SystemConfigurationSerializer
    
    @action(detail=False, methods=['get'])
    def by_type(self, request):
        """
        Get configurations by type
        """
        config_type = request.query_params.get('type')
        if not config_type:
            return Response(
                {'error': 'Config type parameter is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        configs = SystemConfiguration.objects.filter(
            config_type=config_type,
            is_active=True
        )
        
        serializer = SystemConfigurationSerializer(configs, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def summary(self, request):
        """
        Get configuration summary
        """
        summary = {
            'total_objectives': Objective.objects.count(),
            'active_objectives': Objective.objects.filter(is_active=True).count(),
            'total_scoring_rules': ScoringRule.objects.count(),
            'active_scoring_rules': ScoringRule.objects.filter(is_active=True).count(),
            'total_weighting_schemes': WeightingScheme.objects.count(),
            'active_weighting_schemes': WeightingScheme.objects.filter(is_active=True).count(),
            'default_weighting_scheme': None,
            'current_assessment_period': None,
            'total_indicators': TrackedIndicator.objects.count(),
            'weighted_indicators': IndicatorWeight.objects.count(),
        }
        
        # Get default weighting scheme
        default_scheme = WeightingScheme.objects.filter(is_default=True).first()
        if default_scheme:
            summary['default_weighting_scheme'] = default_scheme.name
        
        # Get current assessment period
        current_period = AssessmentPeriod.objects.filter(is_current=True).first()
        if current_period:
            summary['current_assessment_period'] = current_period.name
        
        serializer = ConfigurationSummarySerializer(summary)
        return Response(serializer.data)
    
    @action(detail=False, methods=['post'])
    def validate_configuration(self, request):
        """
        Validate configuration completeness
        """
        serializer = ConfigurationValidationSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        validation_results = {}
        data = serializer.validated_data
        
        if data.get('check_objectives'):
            validation_results['objectives'] = {
                'total': Objective.objects.count(),
                'active': Objective.objects.filter(is_active=True).count(),
                'has_objectives': Objective.objects.filter(is_active=True).exists()
            }
        
        if data.get('check_scoring_rules'):
            validation_results['scoring_rules'] = {
                'total': ScoringRule.objects.count(),
                'active': ScoringRule.objects.filter(is_active=True).count(),
                'has_rules': ScoringRule.objects.filter(is_active=True).exists()
            }
        
        if data.get('check_weighting_schemes'):
            validation_results['weighting_schemes'] = {
                'total': WeightingScheme.objects.count(),
                'active': WeightingScheme.objects.filter(is_active=True).count(),
                'has_default': WeightingScheme.objects.filter(is_default=True).exists(),
                'has_schemes': WeightingScheme.objects.filter(is_active=True).exists()
            }
        
        if data.get('check_assessment_periods'):
            validation_results['assessment_periods'] = {
                'total': AssessmentPeriod.objects.count(),
                'active': AssessmentPeriod.objects.filter(is_active=True).count(),
                'has_current': AssessmentPeriod.objects.filter(is_current=True).exists(),
                'has_periods': AssessmentPeriod.objects.filter(is_active=True).exists()
            }
        
        return Response(validation_results)
