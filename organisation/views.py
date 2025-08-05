from rest_framework import status, viewsets, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from django.db import transaction
from django.utils import timezone

from .models import (
    OrgUnitLevel, OrgUnit, UserOrgUnitAccess, OrgUnitSyncLog,
    OrgUnitGroup, OrgUnitGroupMembership
)
from .serializers import (
    OrgUnitLevelSerializer, OrgUnitLevelCreateSerializer,
    OrgUnitSerializer, OrgUnitCreateSerializer, OrgUnitTreeSerializer,
    UserOrgUnitAccessSerializer, UserOrgUnitAccessCreateSerializer,
    OrgUnitSyncLogSerializer, OrgUnitGroupSerializer, OrgUnitGroupCreateSerializer,
    OrgUnitGroupMembershipSerializer, BulkUserAccessSerializer,
    OrgUnitSyncRequestSerializer, UserAccessSummarySerializer,
    OrgUnitAccessSummarySerializer, OrgUnitHierarchySerializer,
    OrgUnitSearchSerializer
)
from .services import OrgUnitSyncService, AccessControlService, OrgUnitHierarchyService
from dhis2_auth.session import get_dhis2_user


class OrgUnitLevelViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing org unit levels
    """
    queryset = OrgUnitLevel.objects.all()
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['level', 'can_view_data', 'can_edit_data', 'can_manage_users']
    search_fields = ['name', 'display_name', 'description']
    ordering_fields = ['level', 'name', 'created_at']
    ordering = ['level']
    
    def get_serializer_class(self):
        """Return appropriate serializer class based on action"""
        if self.action == 'create':
            return OrgUnitLevelCreateSerializer
        return OrgUnitLevelSerializer


class OrgUnitViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing org units
    """
    queryset = OrgUnit.objects.all()
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['level', 'parent', 'is_active', 'is_leaf', 'can_view_data', 'can_edit_data', 'can_manage_users']
    search_fields = ['name', 'short_name', 'display_name', 'dhis2_code']
    ordering_fields = ['name', 'level__level', 'created_at']
    ordering = ['level__level', 'name']
    
    def get_serializer_class(self):
        """Return appropriate serializer class based on action"""
        if self.action == 'create':
            return OrgUnitCreateSerializer
        return OrgUnitSerializer
    
    @action(detail=False, methods=['get'])
    def tree(self, request):
        """
        Get org unit tree structure
        """
        # Get root org unit from query params
        root_org_unit_id = request.query_params.get('root_org_unit_id')
        root_org_unit = None
        
        if root_org_unit_id:
            try:
                root_org_unit = OrgUnit.objects.get(id=root_org_unit_id)
            except OrgUnit.DoesNotExist:
                return Response(
                    {'error': 'Root org unit not found'},
                    status=status.HTTP_404_NOT_FOUND
                )
        
        # Get org unit tree for current user
        access_service = AccessControlService()
        tree_data = access_service.get_org_unit_tree_for_user(request.user, root_org_unit)
        
        return Response(tree_data)
    
    @action(detail=False, methods=['get'])
    def hierarchy(self, request):
        """
        Get org unit hierarchy data
        """
        # Get parameters
        root_org_unit_id = request.query_params.get('root_org_unit_id')
        max_depth = request.query_params.get('max_depth')
        
        root_org_unit = None
        if root_org_unit_id:
            try:
                root_org_unit = OrgUnit.objects.get(id=root_org_unit_id)
            except OrgUnit.DoesNotExist:
                return Response(
                    {'error': 'Root org unit not found'},
                    status=status.HTTP_404_NOT_FOUND
                )
        
        # Get hierarchy data
        hierarchy_service = OrgUnitHierarchyService()
        hierarchy_data = hierarchy_service.get_org_unit_hierarchy(
            root_org_unit=root_org_unit,
            max_depth=int(max_depth) if max_depth else None
        )
        
        serializer = OrgUnitHierarchySerializer(hierarchy_data, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def search(self, request):
        """
        Search org units
        """
        serializer = OrgUnitSearchSerializer(data=request.query_params)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        data = serializer.validated_data
        
        # Perform search
        hierarchy_service = OrgUnitHierarchyService()
        results = hierarchy_service.search_org_units(
            query=data['query'],
            filters=data
        )
        
        # Apply user access filtering
        access_service = AccessControlService()
        accessible_org_units = access_service.get_user_accessible_org_units(request.user)
        filtered_results = results.filter(id__in=accessible_org_units.values_list('id', flat=True))
        
        page = self.paginate_queryset(filtered_results)
        if page is not None:
            serializer = OrgUnitSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = OrgUnitSerializer(filtered_results, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """
        Get org unit statistics
        """
        hierarchy_service = OrgUnitHierarchyService()
        stats = hierarchy_service.get_org_unit_statistics()
        
        return Response(stats)
    
    @action(detail=True, methods=['get'])
    def children(self, request, pk=None):
        """
        Get children of an org unit
        """
        org_unit = self.get_object()
        
        # Check user access
        access_service = AccessControlService()
        if not access_service.can_user_access_org_unit(request.user, org_unit, 'view'):
            return Response(
                {'error': 'Access denied'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        children = org_unit.get_accessible_children(request.user)
        
        page = self.paginate_queryset(children)
        if page is not None:
            serializer = OrgUnitSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = OrgUnitSerializer(children, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def descendants(self, request, pk=None):
        """
        Get all descendants of an org unit
        """
        org_unit = self.get_object()
        
        # Check user access
        access_service = AccessControlService()
        if not access_service.can_user_access_org_unit(request.user, org_unit, 'view'):
            return Response(
                {'error': 'Access denied'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        descendants = org_unit.descendants
        
        page = self.paginate_queryset(descendants)
        if page is not None:
            serializer = OrgUnitSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = OrgUnitSerializer(descendants, many=True)
        return Response(serializer.data)


class UserOrgUnitAccessViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing user org unit access
    """
    queryset = UserOrgUnitAccess.objects.all()
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['user', 'org_unit', 'is_active', 'is_primary', 'can_view_data', 'can_edit_data', 'can_manage_users']
    search_fields = ['user__dhis2_username', 'org_unit__name', 'notes']
    ordering_fields = ['granted_at', 'expires_at', 'user__dhis2_username', 'org_unit__name']
    ordering = ['user__dhis2_username', 'org_unit__name']
    
    def get_serializer_class(self):
        """Return appropriate serializer class based on action"""
        if self.action == 'create':
            return UserOrgUnitAccessCreateSerializer
        return UserOrgUnitAccessSerializer
    
    @action(detail=False, methods=['post'])
    def bulk_grant(self, request):
        """
        Bulk grant access to multiple users for multiple org units
        """
        serializer = BulkUserAccessSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        data = serializer.validated_data
        
        try:
            access_service = AccessControlService()
            results = access_service.bulk_grant_access(
                user_ids=data['user_ids'],
                org_unit_ids=data['org_unit_ids'],
                permissions=data['permissions'],
                include_children=data.get('include_children', True),
                include_descendants=data.get('include_descendants', True),
                is_primary=data.get('is_primary', False),
                notes=data.get('notes', ''),
                granted_by=get_dhis2_user(request)
            )
            
            return Response({
                'success': True,
                'message': f'Bulk access granted. {results["successful_grants"]} successful, {results["failed_grants"]} failed.',
                'results': results
            })
            
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=True, methods=['post'])
    def revoke(self, request, pk=None):
        """
        Revoke user access to an org unit
        """
        access = self.get_object()
        
        try:
            access_service = AccessControlService()
            success = access_service.revoke_user_access(access.user, access.org_unit)
            
            if success:
                return Response({
                    'success': True,
                    'message': 'Access revoked successfully'
                })
            else:
                return Response({
                    'success': False,
                    'error': 'Access record not found'
                }, status=status.HTTP_404_NOT_FOUND)
                
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class OrgUnitSyncLogViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing org unit sync logs
    """
    queryset = OrgUnitSyncLog.objects.all()
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status', 'dhis2_user']
    search_fields = ['dhis2_instance_url', 'error_message']
    ordering_fields = ['started_at', 'completed_at', 'duration_seconds']
    ordering = ['-started_at']
    
    def get_serializer_class(self):
        return OrgUnitSyncLogSerializer
    
    @action(detail=False, methods=['post'])
    def trigger_sync(self, request):
        """
        Trigger org unit sync from DHIS2
        """
        serializer = OrgUnitSyncRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            # Get current DHIS2 user
            dhis2_user = get_dhis2_user(request)
            
            # Initialize sync service
            sync_service = OrgUnitSyncService()
            
            # Perform the sync
            sync_log = sync_service.sync_org_units(serializer.validated_data, dhis2_user, request.session.session_key)
            
            return Response({
                'success': True,
                'message': f'Org unit sync initiated successfully. Sync ID: {sync_log.id}',
                'sync_log': OrgUnitSyncLogSerializer(sync_log).data
            })
            
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class OrgUnitGroupViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing org unit groups
    """
    queryset = OrgUnitGroup.objects.all()
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['is_active', 'is_system_group']
    search_fields = ['name', 'short_name', 'description']
    ordering_fields = ['name', 'created_at']
    ordering = ['name']
    
    def get_serializer_class(self):
        """Return appropriate serializer class based on action"""
        if self.action == 'create':
            return OrgUnitGroupCreateSerializer
        return OrgUnitGroupSerializer


class OrgUnitGroupMembershipViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing org unit group memberships
    """
    queryset = OrgUnitGroupMembership.objects.all()
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['org_unit', 'group', 'is_active']
    search_fields = ['org_unit__name', 'group__name']
    ordering_fields = ['org_unit__name', 'group__name', 'created_at']
    ordering = ['org_unit__name', 'group__name']
    
    def get_serializer_class(self):
        return OrgUnitGroupMembershipSerializer


class AccessControlViewSet(viewsets.ViewSet):
    """
    ViewSet for access control operations
    """
    permission_classes = [IsAuthenticated]
    
    @action(detail=False, methods=['get'])
    def user_access_summary(self, request):
        """
        Get summary of user access
        """
        # Get user ID from query params
        user_id = request.query_params.get('user_id')
        
        if user_id:
            from dhis2_auth.models import DHIS2User
            try:
                user = DHIS2User.objects.get(id=user_id)
            except DHIS2User.DoesNotExist:
                return Response(
                    {'error': 'User not found'},
                    status=status.HTTP_404_NOT_FOUND
                )
        else:
            user = request.user
        
        # Get access summary
        access_service = AccessControlService()
        accessible_org_units = access_service.get_user_accessible_org_units(user)
        primary_org_unit = access_service.get_user_primary_org_unit(user)
        
        # Get user's access records
        access_records = UserOrgUnitAccess.objects.filter(
            user=user,
            is_active=True
        ).exclude(
            expires_at__lt=timezone.now()
        )
        
        # Determine permissions
        can_view_data = access_records.filter(can_view_data=True).exists()
        can_edit_data = access_records.filter(can_edit_data=True).exists()
        can_manage_users = access_records.filter(can_manage_users=True).exists()
        can_export_data = access_records.filter(can_export_data=True).exists()
        
        summary_data = {
            'user_id': user.id,
            'username': user.dhis2_username,
            'display_name': user.dhis2_display_name,
            'primary_org_unit': primary_org_unit.name if primary_org_unit else None,
            'accessible_org_units_count': accessible_org_units.count(),
            'can_view_data': can_view_data,
            'can_edit_data': can_edit_data,
            'can_manage_users': can_manage_users,
            'can_export_data': can_export_data
        }
        
        serializer = UserAccessSummarySerializer(summary_data)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def org_unit_access_summary(self, request):
        """
        Get summary of org unit access
        """
        # Get org unit ID from query params
        org_unit_id = request.query_params.get('org_unit_id')
        
        if not org_unit_id:
            return Response(
                {'error': 'org_unit_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            org_unit = OrgUnit.objects.get(id=org_unit_id)
        except OrgUnit.DoesNotExist:
            return Response(
                {'error': 'Org unit not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Get access summary for this org unit
        access_records = UserOrgUnitAccess.objects.filter(
            org_unit=org_unit,
            is_active=True
        ).exclude(
            expires_at__lt=timezone.now()
        )
        
        summary_data = {
            'org_unit_id': org_unit.id,
            'org_unit_name': org_unit.name,
            'org_unit_level': org_unit.level.name,
            'user_count': access_records.count(),
            'primary_user_count': access_records.filter(is_primary=True).count(),
            'can_view_data_count': access_records.filter(can_view_data=True).count(),
            'can_edit_data_count': access_records.filter(can_edit_data=True).count(),
            'can_manage_users_count': access_records.filter(can_manage_users=True).count()
        }
        
        serializer = OrgUnitAccessSummarySerializer(summary_data)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def my_accessible_org_units(self, request):
        """
        Get org units accessible to current user
        """
        access_service = AccessControlService()
        accessible_org_units = access_service.get_user_accessible_org_units(request.user)
        
        page = self.paginate_queryset(accessible_org_units)
        if page is not None:
            serializer = OrgUnitSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = OrgUnitSerializer(accessible_org_units, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def my_primary_org_unit(self, request):
        """
        Get primary org unit for current user
        """
        access_service = AccessControlService()
        primary_org_unit = access_service.get_user_primary_org_unit(request.user)
        
        if primary_org_unit:
            serializer = OrgUnitSerializer(primary_org_unit)
            return Response(serializer.data)
        else:
            return Response({'error': 'No primary org unit found'}, status=status.HTTP_404_NOT_FOUND)
    
    @action(detail=False, methods=['post'])
    def check_access(self, request):
        """
        Check if user has access to specific org unit with given permission
        """
        org_unit_id = request.data.get('org_unit_id')
        permission = request.data.get('permission', 'view')
        
        if not org_unit_id:
            return Response(
                {'error': 'org_unit_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            org_unit = OrgUnit.objects.get(id=org_unit_id)
        except OrgUnit.DoesNotExist:
            return Response(
                {'error': 'Org unit not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        access_service = AccessControlService()
        has_access = access_service.can_user_access_org_unit(request.user, org_unit, permission)
        
        return Response({
            'has_access': has_access,
            'org_unit_id': org_unit_id,
            'permission': permission
        })
