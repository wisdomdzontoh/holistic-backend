from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

app_name = 'indicators'

# Create router and register viewsets
router = DefaultRouter()
router.register(r'indicators', views.TrackedIndicatorViewSet, basename='indicator')
router.register(r'categories', views.IndicatorCategoryViewSet, basename='category')
router.register(r'category-mappings', views.IndicatorCategoryMappingViewSet, basename='category-mapping')
router.register(r'thresholds', views.IndicatorThresholdViewSet, basename='threshold')

urlpatterns = [
    # Include router URLs
    path('', include(router.urls)),
] 