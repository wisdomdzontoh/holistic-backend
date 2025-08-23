"""
Data Sync Service

This module handles data synchronization between the application and DHIS2.
"""

import logging
import asyncio
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from django.conf import settings
from django.core.cache import cache
from django.utils import timezone
from django.db import transaction

from ..models import TrackedIndicator, SavedAssessment, DataSyncLog
from .validation_service import ValidationService
from .cache_service import CacheService
from .data_processing_service import DataProcessingService
from .period_service import PeriodService

logger = logging.getLogger(__name__)


class DataSyncService:
    """
    Service for synchronizing data between the application and DHIS2.
    
    This service handles bulk data synchronization, incremental updates,
    and conflict resolution for assessment data.
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.validation_service = ValidationService()
        self.cache_service = CacheService()
        self.data_processor = DataProcessingService()
        self.period_service = PeriodService()
        
        # Sync configuration
        self.sync_batch_size = getattr(settings, 'SYNC_BATCH_SIZE', 100)
        self.sync_timeout = getattr(settings, 'SYNC_TIMEOUT', 300)
        self.max_retries = getattr(settings, 'SYNC_MAX_RETRIES', 3)
    
    async def sync_assessment_data(self, org_unit_ids: List[str], periods: List[str], 
                                 user_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Synchronize assessment data for multiple organization units and periods.
        
        Args:
            org_unit_ids: List of organization unit IDs to sync
            periods: List of periods to sync
            user_id: Optional user ID for tracking
            
        Returns:
            Sync results summary
        """
        try:
            # Validate inputs
            for org_unit_id in org_unit_ids:
                self.validation_service.validate_org_unit_id(org_unit_id)
            
            for period in periods:
                self.validation_service.validate_period_format(period)
            
            # Create sync log entry
            sync_log = await self._create_sync_log(org_unit_ids, periods, user_id)
            
            # Get indicators to sync
            indicators = await self._get_indicators_to_sync()
            
            # Perform sync
            sync_results = await self._perform_sync(
                indicators, org_unit_ids, periods, sync_log
            )
            
            # Update sync log
            await self._update_sync_log(sync_log, sync_results)
            
            return sync_results
            
        except Exception as e:
            self.logger.error(f"Error syncing assessment data: {str(e)}")
            raise
    
    async def _create_sync_log(self, org_unit_ids: List[str], periods: List[str], 
                             user_id: Optional[int] = None) -> DataSyncLog:
        """Create a new sync log entry."""
        try:
            sync_log = DataSyncLog.objects.create(
                org_units=org_unit_ids,
                periods=periods,
                user_id=user_id,
                status='IN_PROGRESS',
                started_at=timezone.now()
            )
            
            self.logger.info(f"Created sync log {sync_log.id} for {len(org_unit_ids)} org units and {len(periods)} periods")
            return sync_log
            
        except Exception as e:
            self.logger.error(f"Error creating sync log: {str(e)}")
            raise
    
    async def _get_indicators_to_sync(self) -> List[Dict[str, Any]]:
        """Get list of indicators that need to be synced."""
        try:
            indicators = TrackedIndicator.objects.filter(
                is_active=True,
                sync_enabled=True
            ).values(
                'id', 'uid', 'name', 'dhis2_uid', 'sync_frequency',
                'last_sync_at', 'data_type'
            )
            
            return list(indicators)
            
        except Exception as e:
            self.logger.error(f"Error getting indicators to sync: {str(e)}")
            raise
    
    async def _perform_sync(self, indicators: List[Dict[str, Any]], 
                          org_unit_ids: List[str], periods: List[str], 
                          sync_log: DataSyncLog) -> Dict[str, Any]:
        """
        Perform the actual data synchronization.
        
        Args:
            indicators: List of indicators to sync
            org_unit_ids: List of organization unit IDs
            periods: List of periods
            sync_log: Sync log entry
            
        Returns:
            Sync results
        """
        try:
            total_indicators = len(indicators)
            total_org_units = len(org_unit_ids)
            total_periods = len(periods)
            
            self.logger.info(f"Starting sync for {total_indicators} indicators, {total_org_units} org units, {total_periods} periods")
            
            # Initialize counters
            sync_results = {
                'total_indicators': total_indicators,
                'total_org_units': total_org_units,
                'total_periods': total_periods,
                'successful_syncs': 0,
                'failed_syncs': 0,
                'skipped_syncs': 0,
                'errors': [],
                'started_at': timezone.now(),
                'completed_at': None
            }
            
            # Process in batches
            for i in range(0, total_indicators, self.sync_batch_size):
                batch = indicators[i:i + self.sync_batch_size]
                
                # Update progress
                progress = (i / total_indicators) * 100
                await self._update_sync_progress(sync_log, progress)
                
                # Sync batch
                batch_results = await self._sync_indicator_batch(
                    batch, org_unit_ids, periods
                )
                
                # Update counters
                sync_results['successful_syncs'] += batch_results['successful']
                sync_results['failed_syncs'] += batch_results['failed']
                sync_results['skipped_syncs'] += batch_results['skipped']
                sync_results['errors'].extend(batch_results['errors'])
                
                # Check for timeout
                if (timezone.now() - sync_results['started_at']).seconds > self.sync_timeout:
                    self.logger.warning("Sync timeout reached")
                    break
            
            sync_results['completed_at'] = timezone.now()
            sync_results['duration'] = (sync_results['completed_at'] - sync_results['started_at']).total_seconds()
            
            self.logger.info(f"Sync completed: {sync_results['successful_syncs']} successful, {sync_results['failed_syncs']} failed")
            
            return sync_results
            
        except Exception as e:
            self.logger.error(f"Error performing sync: {str(e)}")
            raise
    
    async def _sync_indicator_batch(self, indicators: List[Dict[str, Any]], 
                                  org_unit_ids: List[str], periods: List[str]) -> Dict[str, Any]:
        """
        Sync a batch of indicators.
        
        Args:
            indicators: List of indicators in the batch
            org_unit_ids: List of organization unit IDs
            periods: List of periods
            
        Returns:
            Batch sync results
        """
        try:
            batch_results = {
                'successful': 0,
                'failed': 0,
                'skipped': 0,
                'errors': []
            }
            
            for indicator in indicators:
                try:
                    # Check if sync is needed
                    if not self._should_sync_indicator(indicator):
                        batch_results['skipped'] += 1
                        continue
                    
                    # Sync indicator
                    success = await self._sync_single_indicator(
                        indicator, org_unit_ids, periods
                    )
                    
                    if success:
                        batch_results['successful'] += 1
                        # Update last sync timestamp
                        await self._update_indicator_sync_timestamp(indicator['id'])
                    else:
                        batch_results['failed'] += 1
                        
                except Exception as e:
                    batch_results['failed'] += 1
                    error_msg = f"Error syncing indicator {indicator.get('name', 'Unknown')}: {str(e)}"
                    batch_results['errors'].append(error_msg)
                    self.logger.error(error_msg)
            
            return batch_results
            
        except Exception as e:
            self.logger.error(f"Error syncing indicator batch: {str(e)}")
            raise
    
    def _should_sync_indicator(self, indicator: Dict[str, Any]) -> bool:
        """
        Check if an indicator should be synced based on its sync frequency.
        
        Args:
            indicator: Indicator data
            
        Returns:
            True if indicator should be synced
        """
        try:
            last_sync = indicator.get('last_sync_at')
            sync_frequency = indicator.get('sync_frequency', 'DAILY')
            
            if not last_sync:
                return True
            
            current_time = timezone.now()
            time_since_last_sync = current_time - last_sync
            
            # Check frequency requirements
            if sync_frequency == 'HOURLY':
                return time_since_last_sync.total_seconds() >= 3600
            elif sync_frequency == 'DAILY':
                return time_since_last_sync.days >= 1
            elif sync_frequency == 'WEEKLY':
                return time_since_last_sync.days >= 7
            elif sync_frequency == 'MONTHLY':
                return time_since_last_sync.days >= 30
            else:
                return True
                
        except Exception as e:
            self.logger.error(f"Error checking sync requirement: {str(e)}")
            return True
    
    async def _sync_single_indicator(self, indicator: Dict[str, Any], 
                                   org_unit_ids: List[str], periods: List[str]) -> bool:
        """
        Sync a single indicator for all org units and periods.
        
        Args:
            indicator: Indicator data
            org_unit_ids: List of organization unit IDs
            periods: List of periods
            
        Returns:
            True if sync was successful
        """
        try:
            indicator_id = indicator['id']
            dhis2_uid = indicator.get('dhis2_uid')
            
            if not dhis2_uid:
                self.logger.warning(f"Indicator {indicator['name']} has no DHIS2 UID, skipping")
                return False
            
            # Fetch data from DHIS2
            dhis2_data = await self._fetch_dhis2_data(dhis2_uid, org_unit_ids, periods)
            
            if not dhis2_data:
                self.logger.warning(f"No DHIS2 data found for indicator {indicator['name']}")
                return False
            
            # Process and store data
            success = await self._store_indicator_data(indicator_id, dhis2_data)
            
            return success
            
        except Exception as e:
            self.logger.error(f"Error syncing single indicator: {str(e)}")
            return False
    
    async def _fetch_dhis2_data(self, dhis2_uid: str, org_unit_ids: List[str], 
                              periods: List[str]) -> Optional[Dict[str, Any]]:
        """
        Fetch data from DHIS2 for an indicator.
        
        Args:
            dhis2_uid: DHIS2 indicator UID
            org_unit_ids: List of organization unit IDs
            periods: List of periods
            
        Returns:
            DHIS2 data or None
        """
        try:
            # This would integrate with your DHIS2 client
            # For now, return a placeholder structure
            return {
                'indicator_uid': dhis2_uid,
                'data_points': []
            }
            
        except Exception as e:
            self.logger.error(f"Error fetching DHIS2 data: {str(e)}")
            return None
    
    async def _store_indicator_data(self, indicator_id: int, dhis2_data: Dict[str, Any]) -> bool:
        """
        Store indicator data in the database.
        
        Args:
            indicator_id: Indicator ID
            dhis2_data: DHIS2 data
            
        Returns:
            True if storage was successful
        """
        try:
            # This would store the data in your database
            # For now, just log the action
            self.logger.info(f"Storing data for indicator {indicator_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error storing indicator data: {str(e)}")
            return False
    
    async def _update_indicator_sync_timestamp(self, indicator_id: int) -> None:
        """Update the last sync timestamp for an indicator."""
        try:
            await TrackedIndicator.objects.filter(id=indicator_id).aupdate(
                last_sync_at=timezone.now()
            )
            
        except Exception as e:
            self.logger.error(f"Error updating indicator sync timestamp: {str(e)}")
    
    async def _update_sync_progress(self, sync_log: DataSyncLog, progress: float) -> None:
        """Update sync progress in the log."""
        try:
            sync_log.progress = progress
            await sync_log.asave(update_fields=['progress'])
            
        except Exception as e:
            self.logger.error(f"Error updating sync progress: {str(e)}")
    
    async def _update_sync_log(self, sync_log: DataSyncLog, results: Dict[str, Any]) -> None:
        """Update sync log with final results."""
        try:
            sync_log.status = 'COMPLETED' if results['failed_syncs'] == 0 else 'PARTIAL'
            sync_log.completed_at = timezone.now()
            sync_log.results = results
            sync_log.progress = 100.0
            
            await sync_log.asave()
            
        except Exception as e:
            self.logger.error(f"Error updating sync log: {str(e)}")
    
    async def get_sync_status(self, sync_log_id: int) -> Optional[Dict[str, Any]]:
        """
        Get the status of a sync operation.
        
        Args:
            sync_log_id: Sync log ID
            
        Returns:
            Sync status information
        """
        try:
            sync_log = await DataSyncLog.objects.filter(id=sync_log_id).afirst()
            
            if not sync_log:
                return None
            
            return {
                'id': sync_log.id,
                'status': sync_log.status,
                'progress': sync_log.progress,
                'started_at': sync_log.started_at,
                'completed_at': sync_log.completed_at,
                'results': sync_log.results,
                'org_units': sync_log.org_units,
                'periods': sync_log.periods
            }
            
        except Exception as e:
            self.logger.error(f"Error getting sync status: {str(e)}")
            return None
    
    async def get_recent_syncs(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get recent sync operations.
        
        Args:
            limit: Maximum number of syncs to return
            
        Returns:
            List of recent sync operations
        """
        try:
            sync_logs = await DataSyncLog.objects.order_by('-started_at')[:limit].values(
                'id', 'status', 'progress', 'started_at', 'completed_at',
                'org_units', 'periods'
            )
            
            return list(sync_logs)
            
        except Exception as e:
            self.logger.error(f"Error getting recent syncs: {str(e)}")
            return []
    
    async def cleanup_old_sync_logs(self, days: int = 30) -> int:
        """
        Clean up old sync log entries.
        
        Args:
            days: Number of days to keep logs
            
        Returns:
            Number of logs deleted
        """
        try:
            cutoff_date = timezone.now() - timedelta(days=days)
            
            deleted_count = await DataSyncLog.objects.filter(
                started_at__lt=cutoff_date
            ).adelete()
            
            self.logger.info(f"Deleted {deleted_count[0]} old sync logs")
            return deleted_count[0]
            
        except Exception as e:
            self.logger.error(f"Error cleaning up old sync logs: {str(e)}")
            return 0
    
    async def resolve_sync_conflicts(self, indicator_id: int, 
                                   org_unit_id: str, period: str) -> bool:
        """
        Resolve conflicts in synced data.
        
        Args:
            indicator_id: Indicator ID
            org_unit_id: Organization unit ID
            period: Period
            
        Returns:
            True if conflicts were resolved
        """
        try:
            # This would implement conflict resolution logic
            # For now, just log the action
            self.logger.info(f"Resolving conflicts for indicator {indicator_id}, org unit {org_unit_id}, period {period}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error resolving sync conflicts: {str(e)}")
            return False
    
    async def validate_sync_data(self, indicator_id: int, 
                               org_unit_id: str, period: str) -> Dict[str, Any]:
        """
        Validate synced data for consistency.
        
        Args:
            indicator_id: Indicator ID
            org_unit_id: Organization unit ID
            period: Period
            
        Returns:
            Validation results
        """
        try:
            # This would implement data validation logic
            validation_results = {
                'is_valid': True,
                'errors': [],
                'warnings': []
            }
            
            # Add validation logic here
            
            return validation_results
            
        except Exception as e:
            self.logger.error(f"Error validating sync data: {str(e)}")
            return {
                'is_valid': False,
                'errors': [str(e)],
                'warnings': []
            }
