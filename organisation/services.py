from django.db import transaction
from django.utils import timezone
from django.db.models import Q, Count, Subquery, OuterRef
from django.contrib.auth.models import AnonymousUser
import logging

from .models import (
    OrgUnitLevel, OrgUnit, UserOrgUnitAccess, OrgUnitSyncLog,
    OrgUnitGroup, OrgUnitGroupMembership
)
from dhis2_auth.dhis_client import DHIS2Client
from dhis2_auth.session import get_dhis2_session_data

logger = logging.getLogger(__name__)


class OrgUnitSyncService:
    """
    Service for syncing org units from DHIS2
    """
    
    def __init__(self, dhis2_client=None):
        self.client = dhis2_client
    
    def sync_org_units(self, sync_request, dhis2_user=None):
        """
        Sync org units from DHIS2 based on the sync request
        """
        # Create sync log
        sync_log = OrgUnitSyncLog.objects.create(
            dhis2_instance_url=sync_request.get('dhis2_instance_url', ''),
            dhis2_user=dhis2_user
        )
        
        try:
            # Initialize DHIS2 client if not provided
            if not self.client:
                session_data = get_dhis2_session_data()
                if not session_data:
                    raise Exception("No active DHIS2 session")
                
                self.client = DHIS2Client(
                    instance_url=session_data.get('instance_url'),
                    username=session_data.get('username'),
                    password=session_data.get('password')
                )
            
            success_levels = 0
            failed_levels = 0
            success_org_units = 0
            failed_org_units = 0
            total_levels = 0
            total_org_units = 0
            
            # Sync org unit levels if requested
            if sync_request.get('sync_levels', True):
                levels_result = self._sync_org_unit_levels(sync_log, sync_request)
                success_levels = levels_result['success']
                failed_levels = levels_result['failed']
                total_levels = levels_result['total']
            
            # Sync org units if requested
            if sync_request.get('sync_org_units', True):
                org_units_result = self._sync_org_units(sync_log, sync_request)
                success_org_units = org_units_result['success']
                failed_org_units = org_units_result['failed']
                total_org_units = org_units_result['total']
            
            # Sync org unit groups if requested
            if sync_request.get('sync_groups', True):
                self._sync_org_unit_groups(sync_log, sync_request)
            
            # Mark sync as completed
            total_success = success_levels + success_org_units
            total_failed = failed_levels + failed_org_units
            
            if total_failed == 0:
                sync_log.mark_completed(
                    success_count=success_org_units,
                    failure_count=failed_org_units,
                    total_units=total_org_units,
                    success_levels=success_levels,
                    failure_levels=failed_levels,
                    total_levels=total_levels
                )
            else:
                sync_log.mark_partial(
                    success_count=success_org_units,
                    failure_count=failed_org_units,
                    total_units=total_org_units,
                    success_levels=success_levels,
                    failure_levels=failed_levels,
                    total_levels=total_levels
                )
            
            return sync_log
            
        except Exception as e:
            sync_log.mark_failed(str(e))
            logger.error(f"Org unit sync failed: {str(e)}")
            raise
    
    def _sync_org_unit_levels(self, sync_log, sync_request):
        """Sync org unit levels from DHIS2"""
        try:
            # Fetch org unit levels from DHIS2
            levels_data = self.client.get_org_unit_levels()
            
            success_count = 0
            failed_count = 0
            total_count = len(levels_data.get('organisationUnitLevels', []))
            
            for level_data in levels_data.get('organisationUnitLevels', []):
                try:
                    level, created = OrgUnitLevel.objects.update_or_create(
                        dhis2_uid=level_data['id'],
                        defaults={
                            'level': level_data.get('level', 0),
                            'name': level_data.get('name', ''),
                            'display_name': level_data.get('displayName', ''),
                            'description': level_data.get('description', ''),
                            'dhis2_code': level_data.get('code', ''),
                            'can_view_data': True,
                            'can_edit_data': False,
                            'can_manage_users': False,
                            'last_synced': timezone.now()
                        }
                    )
                    success_count += 1
                    logger.info(f"Synced org unit level: {level.name}")
                    
                except Exception as e:
                    failed_count += 1
                    logger.error(f"Failed to sync org unit level {level_data.get('id')}: {str(e)}")
            
            return {
                'success': success_count,
                'failed': failed_count,
                'total': total_count
            }
            
        except Exception as e:
            logger.error(f"Error syncing org unit levels: {str(e)}")
            return {'success': 0, 'failed': 1, 'total': 0}
    
    def _sync_org_units(self, sync_log, sync_request):
        """Sync org units from DHIS2"""
        try:
            # Get specific org unit IDs if provided
            org_unit_ids = sync_request.get('org_unit_ids', [])
            
            if org_unit_ids:
                # Sync specific org units
                org_units_data = self.client.get_org_units(org_unit_ids)
            else:
                # Sync all org units
                org_units_data = self.client.get_org_units()
            
            success_count = 0
            failed_count = 0
            total_count = len(org_units_data.get('organisationUnits', []))
            
            for org_unit_data in org_units_data.get('organisationUnits', []):
                try:
                    # Get or create the level
                    level = OrgUnitLevel.objects.filter(
                        dhis2_uid=org_unit_data.get('level', {}).get('id')
                    ).first()
                    
                    if not level:
                        logger.warning(f"Level not found for org unit {org_unit_data.get('id')}")
                        continue
                    
                    # Get parent org unit if exists
                    parent = None
                    if org_unit_data.get('parent', {}).get('id'):
                        parent = OrgUnit.objects.filter(
                            dhis2_uid=org_unit_data['parent']['id']
                        ).first()
                    
                    # Create or update org unit
                    org_unit, created = OrgUnit.objects.update_or_create(
                        dhis2_uid=org_unit_data['id'],
                        defaults={
                            'dhis2_code': org_unit_data.get('code', ''),
                            'name': org_unit_data.get('name', ''),
                            'short_name': org_unit_data.get('shortName', ''),
                            'display_name': org_unit_data.get('displayName', ''),
                            'level': level,
                            'parent': parent,
                            'latitude': org_unit_data.get('coordinates', [None, None])[1] if org_unit_data.get('coordinates') else None,
                            'longitude': org_unit_data.get('coordinates', [None, None])[0] if org_unit_data.get('coordinates') else None,
                            'is_active': org_unit_data.get('active', True),
                            'is_leaf': org_unit_data.get('leaf', False),
                            'dhis2_created': org_unit_data.get('created'),
                            'dhis2_last_updated': org_unit_data.get('lastUpdated'),
                            'dhis2_path': org_unit_data.get('path', ''),
                            'last_synced': timezone.now()
                        }
                    )
                    success_count += 1
                    logger.info(f"Synced org unit: {org_unit.name}")
                    
                except Exception as e:
                    failed_count += 1
                    logger.error(f"Failed to sync org unit {org_unit_data.get('id')}: {str(e)}")
            
            return {
                'success': success_count,
                'failed': failed_count,
                'total': total_count
            }
            
        except Exception as e:
            logger.error(f"Error syncing org units: {str(e)}")
            return {'success': 0, 'failed': 1, 'total': 0}
    
    def _sync_org_unit_groups(self, sync_log, sync_request):
        """Sync org unit groups from DHIS2"""
        try:
            # Fetch org unit groups from DHIS2
            groups_data = self.client.get_org_unit_groups()
            
            for group_data in groups_data.get('organisationUnitGroups', []):
                try:
                    group, created = OrgUnitGroup.objects.update_or_create(
                        dhis2_uid=group_data['id'],
                        defaults={
                            'dhis2_code': group_data.get('code', ''),
                            'name': group_data.get('name', ''),
                            'short_name': group_data.get('shortName', ''),
                            'description': group_data.get('description', ''),
                            'is_active': group_data.get('active', True),
                            'is_system_group': group_data.get('system', False),
                            'dhis2_created': group_data.get('created'),
                            'dhis2_last_updated': group_data.get('lastUpdated'),
                            'last_synced': timezone.now()
                        }
                    )
                    logger.info(f"Synced org unit group: {group.name}")
                    
                except Exception as e:
                    logger.error(f"Failed to sync org unit group {group_data.get('id')}: {str(e)}")
            
        except Exception as e:
            logger.error(f"Error syncing org unit groups: {str(e)}")


class AccessControlService:
    """
    Service for managing user access to org units
    """
    
    def get_user_accessible_org_units(self, user):
        """
        Get all org units accessible to a user
        """
        if not user or isinstance(user, AnonymousUser):
            return OrgUnit.objects.none()
        
        # Get user's org unit access
        access_records = UserOrgUnitAccess.objects.filter(
            user=user,
            is_active=True
        ).exclude(
            expires_at__lt=timezone.now()
        )
        
        accessible_org_units = []
        
        for access in access_records:
            if access.include_descendants:
                # Include the org unit and all descendants
                accessible_org_units.extend([access.org_unit] + access.org_unit.descendants)
            elif access.include_children:
                # Include the org unit and direct children
                accessible_org_units.extend([access.org_unit] + list(access.org_unit.children.all()))
            else:
                # Include only the org unit itself
                accessible_org_units.append(access.org_unit)
        
        # Remove duplicates and return queryset
        org_unit_ids = list(set(ou.id for ou in accessible_org_units))
        return OrgUnit.objects.filter(id__in=org_unit_ids, is_active=True)
    
    def get_user_primary_org_unit(self, user):
        """
        Get the primary org unit for a user
        """
        if not user or isinstance(user, AnonymousUser):
            return None
        
        access = UserOrgUnitAccess.objects.filter(
            user=user,
            is_primary=True,
            is_active=True
        ).exclude(
            expires_at__lt=timezone.now()
        ).first()
        
        return access.org_unit if access else None
    
    def can_user_access_org_unit(self, user, org_unit, permission='view'):
        """
        Check if a user can access a specific org unit with given permission
        """
        if not user or isinstance(user, AnonymousUser):
            return False
        
        # Get user's access to this org unit
        access = UserOrgUnitAccess.objects.filter(
            user=user,
            org_unit=org_unit,
            is_active=True
        ).exclude(
            expires_at__lt=timezone.now()
        ).first()
        
        if not access:
            return False
        
        # Check permission
        if permission == 'view':
            return access.can_view_data
        elif permission == 'edit':
            return access.can_edit_data
        elif permission == 'manage_users':
            return access.can_manage_users
        elif permission == 'export':
            return access.can_export_data
        
        return False
    
    def get_org_unit_tree_for_user(self, user, root_org_unit=None):
        """
        Get org unit tree filtered by user access
        """
        if not user or isinstance(user, AnonymousUser):
            return []
        
        # Get user's accessible org units
        accessible_org_units = self.get_user_accessible_org_units(user)
        
        if not accessible_org_units.exists():
            return []
        
        # If root org unit is specified, filter to its descendants
        if root_org_unit:
            accessible_org_units = accessible_org_units.filter(
                dhis2_path__startswith=root_org_unit.dhis2_path
            )
        
        # Build tree structure
        return self._build_org_unit_tree(accessible_org_units)
    
    def _build_org_unit_tree(self, org_units):
        """
        Build tree structure from org units
        """
        # Create a dictionary of org units by ID
        org_units_dict = {ou.id: ou for ou in org_units}
        
        # Find root org units (those without parents in the accessible set)
        root_org_units = []
        for org_unit in org_units:
            if not org_unit.parent or org_unit.parent.id not in org_units_dict:
                root_org_units.append(org_unit)
        
        # Build tree recursively
        def build_subtree(parent_org_unit):
            children = [ou for ou in org_units if ou.parent and ou.parent.id == parent_org_unit.id]
            return {
                'org_unit': parent_org_unit,
                'children': [build_subtree(child) for child in children]
            }
        
        return [build_subtree(root) for root in root_org_units]
    
    def grant_user_access(self, user, org_unit, permissions, granted_by=None, **kwargs):
        """
        Grant access to a user for an org unit
        """
        access, created = UserOrgUnitAccess.objects.update_or_create(
            user=user,
            org_unit=org_unit,
            defaults={
                'can_view_data': permissions.get('can_view_data', True),
                'can_edit_data': permissions.get('can_edit_data', False),
                'can_manage_users': permissions.get('can_manage_users', False),
                'can_export_data': permissions.get('can_export_data', True),
                'include_children': kwargs.get('include_children', True),
                'include_descendants': kwargs.get('include_descendants', True),
                'is_active': kwargs.get('is_active', True),
                'is_primary': kwargs.get('is_primary', False),
                'granted_by': granted_by,
                'expires_at': kwargs.get('expires_at'),
                'notes': kwargs.get('notes', ''),
            }
        )
        
        return access
    
    def revoke_user_access(self, user, org_unit):
        """
        Revoke access for a user to an org unit
        """
        try:
            access = UserOrgUnitAccess.objects.get(user=user, org_unit=org_unit)
            access.is_active = False
            access.save()
            return True
        except UserOrgUnitAccess.DoesNotExist:
            return False
    
    def bulk_grant_access(self, user_ids, org_unit_ids, permissions, **kwargs):
        """
        Bulk grant access to multiple users for multiple org units
        """
        results = {
            'total_grants': len(user_ids) * len(org_unit_ids),
            'successful_grants': 0,
            'failed_grants': 0,
            'errors': []
        }
        
        for user_id in user_ids:
            for org_unit_id in org_unit_ids:
                try:
                    from dhis2_auth.models import DHIS2User
                    user = DHIS2User.objects.get(id=user_id)
                    org_unit = OrgUnit.objects.get(id=org_unit_id)
                    
                    self.grant_user_access(user, org_unit, permissions, **kwargs)
                    results['successful_grants'] += 1
                    
                except Exception as e:
                    results['failed_grants'] += 1
                    error_msg = f"Failed to grant access for user {user_id} to org unit {org_unit_id}: {str(e)}"
                    results['errors'].append(error_msg)
                    logger.error(error_msg)
        
        return results


class OrgUnitHierarchyService:
    """
    Service for managing org unit hierarchy
    """
    
    def get_org_unit_hierarchy(self, root_org_unit=None, max_depth=None):
        """
        Get org unit hierarchy starting from root
        """
        if root_org_unit:
            org_units = OrgUnit.objects.filter(
                dhis2_path__startswith=root_org_unit.dhis2_path,
                is_active=True
            )
        else:
            org_units = OrgUnit.objects.filter(is_active=True)
        
        # Build hierarchy data
        hierarchy_data = []
        for org_unit in org_units:
            depth = len(org_unit.dhis2_path.split('/')) - 1 if org_unit.dhis2_path else 0
            
            if max_depth and depth > max_depth:
                continue
            
            hierarchy_data.append({
                'org_unit_id': org_unit.id,
                'org_unit_name': org_unit.name,
                'level_name': org_unit.level.name,
                'parent_id': org_unit.parent.id if org_unit.parent else None,
                'parent_name': org_unit.parent.name if org_unit.parent else None,
                'children_count': org_unit.children.count(),
                'descendants_count': len(org_unit.descendants),
                'depth': depth,
                'path': org_unit.dhis2_path.split('/') if org_unit.dhis2_path else []
            })
        
        return hierarchy_data
    
    def search_org_units(self, query, filters=None):
        """
        Search org units by name or code
        """
        queryset = OrgUnit.objects.filter(is_active=True)
        
        # Apply search query
        if query:
            queryset = queryset.filter(
                Q(name__icontains=query) |
                Q(dhis2_code__icontains=query) |
                Q(short_name__icontains=query)
            )
        
        # Apply filters
        if filters:
            if filters.get('level_ids'):
                queryset = queryset.filter(level_id__in=filters['level_ids'])
            
            if filters.get('parent_id'):
                queryset = queryset.filter(parent_id=filters['parent_id'])
            
            if filters.get('is_active') is not None:
                queryset = queryset.filter(is_active=filters['is_active'])
        
        # Apply limit
        limit = filters.get('limit', 50) if filters else 50
        return queryset[:limit]
    
    def get_org_unit_statistics(self):
        """
        Get statistics about org units
        """
        stats = {
            'total_org_units': OrgUnit.objects.filter(is_active=True).count(),
            'total_levels': OrgUnitLevel.objects.count(),
            'org_units_by_level': {},
            'org_units_by_region': {},
            'leaf_org_units': OrgUnit.objects.filter(is_active=True, is_leaf=True).count(),
            'non_leaf_org_units': OrgUnit.objects.filter(is_active=True, is_leaf=False).count(),
        }
        
        # Count org units by level
        for level in OrgUnitLevel.objects.all():
            stats['org_units_by_level'][level.name] = level.org_units.filter(is_active=True).count()
        
        # Count org units by region (assuming level 2 is regional)
        regional_level = OrgUnitLevel.objects.filter(level=2).first()
        if regional_level:
            for region in regional_level.org_units.filter(is_active=True):
                stats['org_units_by_region'][region.name] = len(region.descendants) + 1
        
        return stats 