from django.urls import path
from . import views

app_name = 'dhis2_auth'

urlpatterns = [
    # Authentication endpoints
    path('login/', views.LoginView.as_view(), name='login'),
    path('logout/', views.LogoutView.as_view(), name='logout'),
    path('session/status/', views.SessionStatusView.as_view(), name='session_status'),
    
    # Organisation units and authorities
    path('org-units/', views.OrgUnitsView.as_view(), name='org_units'),
    path('org-units/<str:org_unit_id>/descendants/', views.OrgUnitDescendantsView.as_view(), name='org_unit_descendants'),
    path('org-units/<str:org_unit_id>/children/', views.OrgUnitChildrenView.as_view(), name='org_unit_children'),
    path('authorities/check/', views.AuthorityCheckView.as_view(), name='authority_check'),
    
    # Health check
    path('health/', views.health_check, name='health_check'),
    
    # Debug endpoint
    path('debug-session/', views.debug_session, name='debug_session'),
    
    # Test authentication endpoint
    path('test-auth/', views.test_auth, name='test_auth'),
] 