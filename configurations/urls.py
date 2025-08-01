from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

app_name = 'configurations'

# Create router and register viewsets
router = DefaultRouter()
router.register(r'objectives', views.ObjectiveViewSet, basename='objective')
router.register(r'scoring-rules', views.ScoringRuleViewSet, basename='scoring-rule')
router.register(r'weighting-schemes', views.WeightingSchemeViewSet, basename='weighting-scheme')
router.register(r'objective-weights', views.ObjectiveWeightViewSet, basename='objective-weight')
router.register(r'indicator-weights', views.IndicatorWeightViewSet, basename='indicator-weight')
router.register(r'assessment-periods', views.AssessmentPeriodViewSet, basename='assessment-period')
router.register(r'system-configurations', views.SystemConfigurationViewSet, basename='system-configuration')

urlpatterns = [
    # Include router URLs
    path('', include(router.urls)),
] 