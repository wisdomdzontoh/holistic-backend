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
    path('authorities/check/', views.AuthorityCheckView.as_view(), name='authority_check'),
    
    # Health check
    path('health/', views.health_check, name='health_check'),
] 