from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from . import views

app_name = 'configurations'

# Create router and register viewsets
router = DefaultRouter()
router.register(r'milestones', views.MilestoneViewSet, basename='milestone')
router.register(r'objectives', views.ObjectiveViewSet, basename='objective')
router.register(r'scoring-rules', views.ScoringRuleViewSet, basename='scoring-rule')
router.register(r'weighting-schemes', views.WeightingSchemeViewSet, basename='weighting-scheme')
router.register(r'objective-weights', views.ObjectiveWeightViewSet, basename='objective-weight')
router.register(r'indicator-weights', views.IndicatorWeightViewSet, basename='indicator-weight')
router.register(r'assessment-periods', views.AssessmentPeriodViewSet, basename='assessment-period')
router.register(r'system-configurations', views.SystemConfigurationViewSet, basename='system-configuration')

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def indicators_definitions(request):
    """
    Get all indicators with their definitions, grouped by objectives
    """
    try:
        from indicators.models import TrackedIndicator
        
        objectives = views.Objective.objects.filter(is_active=True).order_by('order')
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
        }, status=500)

urlpatterns = [
    # Dedicated endpoint for indicators definitions
    path('indicators-definitions/', indicators_definitions, name='indicators-definitions'),
    # Include router URLs
    path('', include(router.urls)),
] 