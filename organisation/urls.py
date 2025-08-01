from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

app_name = 'organisation'

# Create router and register viewsets
router = DefaultRouter()
router.register(r'levels', views.OrgUnitLevelViewSet, basename='org-unit-level')
router.register(r'units', views.OrgUnitViewSet, basename='org-unit')
router.register(r'user-access', views.UserOrgUnitAccessViewSet, basename='user-org-unit-access')
router.register(r'sync-logs', views.OrgUnitSyncLogViewSet, basename='org-unit-sync-log')
router.register(r'groups', views.OrgUnitGroupViewSet, basename='org-unit-group')
router.register(r'group-memberships', views.OrgUnitGroupMembershipViewSet, basename='org-unit-group-membership')
router.register(r'access-control', views.AccessControlViewSet, basename='access-control')

urlpatterns = [
    # Include router URLs
    path('', include(router.urls)),
] 