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

urlpatterns = [
    path('', include(router.urls)),
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