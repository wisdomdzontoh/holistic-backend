from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

app_name = 'exports'

# Create router and register viewsets
router = DefaultRouter()
router.register(r'templates', views.ExportTemplateViewSet, basename='export-template')
router.register(r'jobs', views.ExportJobViewSet, basename='export-job')
router.register(r'schedules', views.ExportScheduleViewSet, basename='export-schedule')
router.register(r'logs', views.ExportLogViewSet, basename='export-log')
router.register(r'configurations', views.ExportConfigurationViewSet, basename='export-configuration')

urlpatterns = [
    # Include router URLs
    path('', include(router.urls)),
] 