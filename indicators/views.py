from django.shortcuts import render
from rest_framework import status, viewsets, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from django.utils import timezone
from django.db import transaction

from .models import TrackedIndicator, IndicatorCategory, IndicatorCategoryMapping, IndicatorThreshold
from .serializers import (
    TrackedIndicatorSerializer, TrackedIndicatorListSerializer,
    TrackedIndicatorCreateSerializer, TrackedIndicatorUpdateSerializer,
    IndicatorCategorySerializer, IndicatorCategoryCreateSerializer,
    IndicatorCategoryMappingSerializer, IndicatorCategoryMappingCreateSerializer,
    IndicatorThresholdSerializer, IndicatorThresholdCreateSerializer,
    IndicatorSyncSerializer
)
from dhis2_auth.dhis_client import DHIS2Client
from dhis2_auth.session import get_dhis2_session_data


class TrackedIndicatorViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing tracked indicators.
    Provides CRUD operations and additional functionality for indicator management.
    """
    queryset = TrackedIndicator.objects.all()
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['indicator_type', 'is_active', 'target_type']
    search_fields = ['name', 'dhis2_uid', 'description', 'dhis2_name']
    ordering_fields = ['name', 'created_at', 'updated_at', 'last_sync']
    ordering = ['name']
    
    def get_serializer_class(self):
        """Return appropriate serializer class based on action"""
        if self.action == 'list':
            return TrackedIndicatorListSerializer
        elif self.action == 'create':
            return TrackedIndicatorCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return TrackedIndicatorUpdateSerializer
        return TrackedIndicatorSerializer
    
    def get_queryset(self):
        """Return filtered queryset"""
        queryset = TrackedIndicator.objects.prefetch_related(
            'thresholds', 'category_mappings__category'
        )
        
        # Filter by active status if specified
        is_active = self.request.query_params.get('is_active')
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active.lower() == 'true')
        
        return queryset
    
    @action(detail=True, methods=['post'])
    def sync_from_dhis2(self, request, pk=None):
        """
        Sync indicator metadata from DHIS2.
        """
        indicator = self.get_object()
        serializer = IndicatorSyncSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # Get DHIS2 session data
            session_key = request.session.session_key
            if not session_key:
                return Response(
                    {'error': 'No active DHIS2 session'},
                    status=status.HTTP_401_UNAUTHORIZED
                )
            
            session_data = get_dhis2_session_data(session_key)
            if not session_data:
                return Response(
                    {'error': 'Invalid DHIS2 session'},
                    status=status.HTTP_401_UNAUTHORIZED
                )
            
            # Create DHIS2 client
            client = DHIS2Client(
                instance_url=session_data['instance_url'],
                session_key=session_key
            )
            
            # Sync indicator metadata
            if indicator.indicator_type == TrackedIndicator.IndicatorType.INDICATOR:
                endpoint = f'/api/indicators/{indicator.dhis2_uid}'
            elif indicator.indicator_type == TrackedIndicator.IndicatorType.DATA_ELEMENT:
                endpoint = f'/api/dataElements/{indicator.dhis2_uid}'
            else:
                return Response(
                    {'error': 'Cannot sync calculated indicators'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Fetch metadata from DHIS2
            metadata = client._make_request('GET', endpoint)
            
            # Update indicator with DHIS2 metadata
            indicator.dhis2_name = metadata.get('name', '')
            indicator.dhis2_description = metadata.get('description', '')
            indicator.last_sync = timezone.now()
            indicator.save()
            
            return Response({
                'success': True,
                'message': 'Indicator metadata synced successfully',
                'indicator': TrackedIndicatorSerializer(indicator).data
            })
            
        except Exception as e:
            return Response(
                {'error': f'Failed to sync indicator: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['post'])
    def bulk_sync(self, request):
        """
        Bulk sync multiple indicators from DHIS2.
        """
        serializer = IndicatorSyncSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # Get DHIS2 session data
            session_key = request.session.session_key
            if not session_key:
                return Response(
                    {'error': 'No active DHIS2 session'},
                    status=status.HTTP_401_UNAUTHORIZED
                )
            
            session_data = get_dhis2_session_data(session_key)
            if not session_data:
                return Response(
                    {'error': 'Invalid DHIS2 session'},
                    status=status.HTTP_401_UNAUTHORIZED
                )
            
            # Create DHIS2 client
            client = DHIS2Client(
                instance_url=session_data['instance_url'],
                session_key=session_key
            )
            
            # Get indicators to sync
            indicator_uids = serializer.validated_data.get('indicator_uids', [])
            if indicator_uids:
                indicators = TrackedIndicator.objects.filter(dhis2_uid__in=indicator_uids)
            else:
                indicators = TrackedIndicator.objects.filter(is_active=True)
            
            synced_count = 0
            errors = []
            
            for indicator in indicators:
                try:
                    if indicator.indicator_type == TrackedIndicator.IndicatorType.INDICATOR:
                        endpoint = f'/api/indicators/{indicator.dhis2_uid}'
                    elif indicator.indicator_type == TrackedIndicator.IndicatorType.DATA_ELEMENT:
                        endpoint = f'/api/dataElements/{indicator.dhis2_uid}'
                    else:
                        continue
                    
                    # Fetch metadata from DHIS2
                    metadata = client._make_request('GET', endpoint)
                    
                    # Update indicator with DHIS2 metadata
                    indicator.dhis2_name = metadata.get('name', '')
                    indicator.dhis2_description = metadata.get('description', '')
                    indicator.last_sync = timezone.now()
                    indicator.save()
                    
                    synced_count += 1
                    
                except Exception as e:
                    errors.append(f"{indicator.name}: {str(e)}")
            
            return Response({
                'success': True,
                'message': f'Successfully synced {synced_count} indicators',
                'synced_count': synced_count,
                'errors': errors
            })
            
        except Exception as e:
            return Response(
                {'error': f'Failed to sync indicators: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['post'])
    def toggle_active(self, request, pk=None):
        """
        Toggle the active status of an indicator.
        """
        indicator = self.get_object()
        indicator.is_active = not indicator.is_active
        indicator.save()
        
        return Response({
            'success': True,
            'message': f'Indicator {"activated" if indicator.is_active else "deactivated"} successfully',
            'is_active': indicator.is_active
        })
    
    @action(detail=True, methods=['get'])
    def formula_components(self, request, pk=None):
        """
        Get the components (UIDs) used in the indicator formula.
        """
        indicator = self.get_object()
        components = indicator.get_formula_components()
        
        return Response({
            'indicator_id': indicator.id,
            'formula': indicator.formula,
            'components': components
        })


class IndicatorCategoryViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing indicator categories.
    """
    queryset = IndicatorCategory.objects.all()
    serializer_class = IndicatorCategorySerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['is_active']
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'order']
    ordering = ['order', 'name']
    
    def get_serializer_class(self):
        """Return appropriate serializer class based on action"""
        if self.action == 'create':
            return IndicatorCategoryCreateSerializer
        return IndicatorCategorySerializer
    
    @action(detail=True, methods=['get'])
    def indicators(self, request, pk=None):
        """
        Get all indicators in this category.
        """
        category = self.get_object()
        indicators = TrackedIndicator.objects.filter(
            category_mappings__category=category
        ).prefetch_related('category_mappings')
        
        serializer = TrackedIndicatorListSerializer(indicators, many=True)
        return Response(serializer.data)


class IndicatorCategoryMappingViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing indicator category mappings.
    """
    queryset = IndicatorCategoryMapping.objects.all()
    serializer_class = IndicatorCategoryMappingSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['indicator', 'category']
    ordering_fields = ['weight']
    ordering = ['category__order', 'weight']
    
    def get_serializer_class(self):
        """Return appropriate serializer class based on action"""
        if self.action == 'create':
            return IndicatorCategoryMappingCreateSerializer
        return IndicatorCategoryMappingSerializer


class IndicatorThresholdViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing indicator thresholds.
    """
    queryset = IndicatorThreshold.objects.all()
    serializer_class = IndicatorThresholdSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['indicator', 'score']
    ordering_fields = ['min_value', 'max_value', 'score']
    ordering = ['indicator__name', 'min_value']
    
    def get_serializer_class(self):
        """Return appropriate serializer class based on action"""
        if self.action == 'create':
            return IndicatorThresholdCreateSerializer
        return IndicatorThresholdSerializer
    
    @action(detail=False, methods=['post'])
    def bulk_create(self, request):
        """
        Bulk create thresholds for an indicator.
        """
        indicator_id = request.data.get('indicator_id')
        thresholds_data = request.data.get('thresholds', [])
        
        if not indicator_id or not thresholds_data:
            return Response(
                {'error': 'indicator_id and thresholds are required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            indicator = TrackedIndicator.objects.get(id=indicator_id)
        except TrackedIndicator.DoesNotExist:
            return Response(
                {'error': 'Indicator not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        created_thresholds = []
        errors = []
        
        with transaction.atomic():
            for threshold_data in thresholds_data:
                threshold_data['indicator'] = indicator_id
                serializer = IndicatorThresholdCreateSerializer(data=threshold_data)
                
                if serializer.is_valid():
                    threshold = serializer.save()
                    created_thresholds.append(threshold)
                else:
                    errors.append({
                        'data': threshold_data,
                        'errors': serializer.errors
                    })
        
        return Response({
            'success': True,
            'created_count': len(created_thresholds),
            'created_thresholds': IndicatorThresholdSerializer(created_thresholds, many=True).data,
            'errors': errors
        })
