from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'sync-logs', views.DataSyncLogViewSet)
router.register(r'indicator-data', views.IndicatorDataViewSet)
router.register(r'indicator-scores', views.IndicatorScoreViewSet)
router.register(r'objective-scores', views.ObjectiveScoreViewSet)
router.register(r'sector-scores', views.SectorScoreViewSet)
router.register(r'holistic-assessment', views.HolisticAssessmentViewSet, basename='holistic-assessment')
router.register(r'audit-logs', views.AuditLogViewSet, basename='audit-logs')
router.register(r'conflict-resolutions', views.ConflictResolutionViewSet, basename='conflict-resolutions')
router.register(r'manual-overrides', views.ManualOverrideViewSet, basename='manual-overrides')
router.register(r'manual-data-entry', views.ManualDataEntryViewSet, basename='manual-data-entry')

urlpatterns = [
    path('', include(router.urls)),
    
    # Custom URL patterns for holistic assessment to match frontend expectations
    path('holistic/', include([
        path('save_assessment/', views.HolisticAssessmentViewSet.as_view({'post': 'save_assessment'}), name='holistic-save-assessment'),
        path('get_saved_assessments/', views.HolisticAssessmentViewSet.as_view({'get': 'get_saved_assessments'}), name='holistic-get-saved-assessments'),
        path('get_assessment/<str:pk>/', views.HolisticAssessmentViewSet.as_view({'get': 'get_assessment'}), name='holistic-get-assessment'),
        path('update_assessment/<str:pk>/', views.HolisticAssessmentViewSet.as_view({'put': 'update_assessment'}), name='holistic-update-assessment'),
        path('delete_assessment/<str:pk>/', views.HolisticAssessmentViewSet.as_view({'delete': 'delete_assessment'}), name='holistic-delete-assessment'),
    ])),
    
    # Audit and conflict resolution endpoints
    path('audit/', include([
        path('logs/', views.AuditLogViewSet.as_view({'get': 'list'}), name='audit-logs-list'),
        path('logs/summary/', views.AuditLogViewSet.as_view({'get': 'summary'}), name='audit-logs-summary'),
        path('logs/export/', views.AuditLogViewSet.as_view({'post': 'export'}), name='audit-logs-export'),
        path('conflicts/', views.ConflictResolutionViewSet.as_view({'get': 'list', 'post': 'create'}), name='conflict-resolutions-list'),
        path('conflicts/summary/', views.ConflictResolutionViewSet.as_view({'get': 'summary'}), name='conflict-resolutions-summary'),
        path('conflicts/<str:pk>/resolve/', views.ConflictResolutionViewSet.as_view({'post': 'resolve'}), name='conflict-resolve'),
        path('overrides/apply/', views.ManualOverrideViewSet.as_view({'post': 'apply_override'}), name='manual-override-apply'),
        path('overrides/clear/', views.ManualOverrideViewSet.as_view({'post': 'clear_override'}), name='manual-override-clear'),
    ])),
    
    # Manual data entry endpoints
    path('manual-data/', include([
        path('update-indicator/', views.ManualDataEntryViewSet.as_view({'post': 'update_indicator_data'}), name='manual-update-indicator'),
        path('bulk-update/', views.ManualDataEntryViewSet.as_view({'post': 'bulk_update_data'}), name='manual-bulk-update'),
        path('override-score/', views.ManualDataEntryViewSet.as_view({'post': 'override_score'}), name='manual-override-score'),
        path('calculate-scores/', views.ManualDataEntryViewSet.as_view({'post': 'calculate_scores'}), name='manual-calculate-scores'),
    ])),
    
    path('dashboard/', include([
        path('summary/', views.AssessmentDashboardViewSet.as_view({'get': 'summary'}), name='dashboard-summary'),
        path('objectives/', views.AssessmentDashboardViewSet.as_view({'get': 'objectives'}), name='dashboard-objectives'),
        path('indicators/', views.AssessmentDashboardViewSet.as_view({'get': 'indicators'}), name='dashboard-indicators'),
    ])),
    path('management/', include([
        path('calculate-scores/', views.AssessmentManagementViewSet.as_view({'post': 'calculate_scores'}), name='calculate-scores'),
        path('assessment-report/', views.AssessmentManagementViewSet.as_view({'get': 'assessment_report'}), name='assessment-report'),
        path('holistic-assessment-data/', views.AssessmentManagementViewSet.as_view({'get': 'holistic_assessment_data'}), name='holistic-assessment-data'),
        path('multi-period-assessment-data/', views.AssessmentManagementViewSet.as_view({'post': 'multi_period_assessment_data'}), name='multi-period-assessment-data'),
        path('dhis2-periods/', views.AssessmentManagementViewSet.as_view({'get': 'dhis2_periods'}), name='dhis2-periods'),
        path('dhis2-relative-periods/', views.AssessmentManagementViewSet.as_view({'get': 'dhis2_relative_periods'}), name='dhis2-relative-periods'),
        path('dhis2-org-units/', views.AssessmentManagementViewSet.as_view({'get': 'dhis2_org_units'}), name='dhis2-org-units'),
        path('dhis2-period-types/', views.AssessmentManagementViewSet.as_view({'get': 'dhis2_period_types'}), name='dhis2-period-types'),
        path('test-dhis2-connection/', views.AssessmentManagementViewSet.as_view({'get': 'test_dhis2_connection'}), name='test-dhis2-connection'),
    ])),
] 