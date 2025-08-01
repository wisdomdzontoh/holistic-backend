from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views
from . import dashboard_views

app_name = 'assessments'

# Create router and register viewsets
router = DefaultRouter()
router.register(r'sync-logs', views.DataSyncLogViewSet, basename='sync-log')
router.register(r'indicator-data', views.IndicatorDataViewSet, basename='indicator-data')
router.register(r'indicator-scores', views.IndicatorScoreViewSet, basename='indicator-score')
router.register(r'objective-scores', views.ObjectiveScoreViewSet, basename='objective-score')
router.register(r'sector-scores', views.SectorScoreViewSet, basename='sector-score')
router.register(r'dashboard', views.AssessmentDashboardViewSet, basename='dashboard')
router.register(r'management', views.AssessmentManagementViewSet, basename='management')

# Dashboard router
dashboard_router = DefaultRouter()
dashboard_router.register(r'dashboard', dashboard_views.DashboardViewSet, basename='dashboard')

urlpatterns = [
    # Include router URLs
    path('', include(router.urls)),
    
    # Include dashboard URLs
    path('', include(dashboard_router.urls)),
] 