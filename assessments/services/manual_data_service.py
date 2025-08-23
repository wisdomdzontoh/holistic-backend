#!/usr/bin/env python
"""
Manual Data Entry Service

This service handles manual data entry for indicators and score overrides.
It works with existing IndicatorData and IndicatorScore models.
"""

import logging
from typing import Dict, List, Optional, Any
from decimal import Decimal
from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.db import transaction
from django.db.models import Count

from ..models import TrackedIndicator, IndicatorData, IndicatorScore, SavedAssessment
from .validation_service import ValidationService
from .cache_service import CacheService
from .data_processing_service import DataProcessingService

logger = logging.getLogger(__name__)


class ManualDataEntryService:
    """
    Service for handling manual data entry for indicators.
    
    This service manages manual data entry, validation, and integration
    with assessment calculations using existing IndicatorData and IndicatorScore models.
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.validation_service = ValidationService()
        self.cache_service = CacheService()
        self.data_processor = DataProcessingService()
    
    def update_manual_indicator_data(self, request, indicator_id: int, org_unit_id: str, 
                                   assessment_period_id: int, data_updates: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update manual indicator data and recalculate scores.
        
        Args:
            request: HTTP request object
            indicator_id: Indicator ID
            org_unit_id: Organization unit ID
            assessment_period_id: Assessment period ID
            data_updates: Dictionary containing data updates
            
        Returns:
            Updated data result
        """
        try:
            with transaction.atomic():
                # Validate inputs
                self.validation_service.validate_indicator_id(indicator_id)
                self.validation_service.validate_org_unit_id(org_unit_id)
                
                # Get indicator
                indicator = TrackedIndicator.objects.get(id=indicator_id)
                
                # Get or create indicator data entry
                indicator_data, created = IndicatorData.objects.get_or_create(
                    indicator=indicator,
                    org_unit_id=org_unit_id,
                    period=f"manual_{assessment_period_id}",
                    defaults={
                        'org_unit_name': org_unit_id,  # Will be updated if available
                        'value': None,
                        'numerator': None,
                        'denominator': None,
                        'sync_log': None,  # Manual entries don't have sync logs
                        'dhis2_response': {'manual_entry': True}
                    }
                )
                
                # Update data values
                if 'value' in data_updates:
                    indicator_data.value = Decimal(str(data_updates['value']))
                if 'numerator' in data_updates:
                    indicator_data.numerator = Decimal(str(data_updates['numerator']))
                if 'denominator' in data_updates:
                    indicator_data.denominator = Decimal(str(data_updates['denominator']))
                
                indicator_data.save()
                
                # Update indicator scores if score override is provided
                if 'score' in data_updates:
                    self._update_indicator_score(
                        indicator, org_unit_id, assessment_period_id, 
                        data_updates['score'], request
                    )
                
                # Clear related caches
                self._clear_related_caches(indicator_id, org_unit_id, assessment_period_id)
                
                return {
                    'success': True,
                    'message': 'Manual data updated successfully',
                    'indicator_data': {
                        'id': indicator_data.id,
                        'value': float(indicator_data.value) if indicator_data.value else None,
                        'numerator': float(indicator_data.numerator) if indicator_data.numerator else None,
                        'denominator': float(indicator_data.denominator) if indicator_data.denominator else None,
                        'updated_at': indicator_data.updated_at.isoformat()
                    }
                }
                
        except Exception as e:
            self.logger.error(f"Error updating manual indicator data: {str(e)}")
            raise
    
    def bulk_update_manual_data(self, request, updates: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Bulk update multiple indicator data entries.
        
        Args:
            request: HTTP request object
            updates: List of update dictionaries
            
        Returns:
            List of update results
        """
        results = []
        
        for update in updates:
            try:
                result = self.update_manual_indicator_data(
                    request=request,
                    indicator_id=update['indicator_id'],
                    org_unit_id=update['org_unit_id'],
                    assessment_period_id=update['assessment_period_id'],
                    data_updates=update.get('data_updates', {})
                )
                results.append({
                    'indicator_id': update['indicator_id'],
                    'success': True,
                    'result': result
                })
            except Exception as e:
                results.append({
                    'indicator_id': update['indicator_id'],
                    'success': False,
                    'error': str(e)
                })
        
        return results
    
    def _update_indicator_score(self, indicator: TrackedIndicator, org_unit_id: str, 
                              assessment_period_id: int, score: float, request) -> None:
        """
        Update indicator score with manual override.
        
        Args:
            indicator: TrackedIndicator instance
            org_unit_id: Organization unit ID
            assessment_period_id: Assessment period ID
            score: Manual score value
            request: HTTP request object
        """
        try:
            # Get the indicator score
            indicator_score = IndicatorScore.objects.get(
                indicator=indicator,
                org_unit_id=org_unit_id,
                assessment_period_id=assessment_period_id
            )
            
            # Apply manual override
            indicator_score.apply_manual_override(
                new_score=score,
                user=request.user,
                reason="Manual data entry override"
            )
            
        except IndicatorScore.DoesNotExist:
            self.logger.warning(f"No indicator score found for manual override: {indicator.id}")
        except Exception as e:
            self.logger.error(f"Error updating indicator score: {str(e)}")
            raise
    
    def _clear_related_caches(self, indicator_id: int, org_unit_id: str, assessment_period_id: int) -> None:
        """
        Clear caches related to the updated data.
        
        Args:
            indicator_id: Indicator ID
            org_unit_id: Organization unit ID
            assessment_period_id: Assessment period ID
        """
        try:
            # Clear indicator-specific caches
            cache_keys = [
                f"indicator_data_{indicator_id}_{org_unit_id}",
                f"indicator_score_{indicator_id}_{org_unit_id}_{assessment_period_id}",
                f"assessment_data_{org_unit_id}_{assessment_period_id}"
            ]
            
            for cache_key in cache_keys:
                self.cache_service.clear_cache(cache_key)
                
        except Exception as e:
            self.logger.error(f"Error clearing caches: {str(e)}")
    
    def get_manual_entries(self, indicator_id: Optional[int] = None, 
                          org_unit_id: Optional[str] = None,
                          period: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get manual data entries.
        
        Args:
            indicator_id: Optional indicator ID filter
            org_unit_id: Optional org unit ID filter
            period: Optional period filter
            
        Returns:
            List of manual data entries
        """
        try:
            queryset = IndicatorData.objects.filter(
                dhis2_response__manual_entry=True
            ).select_related('indicator')
            
            if indicator_id:
                queryset = queryset.filter(indicator_id=indicator_id)
            if org_unit_id:
                queryset = queryset.filter(org_unit_id=org_unit_id)
            if period:
                queryset = queryset.filter(period=period)
            
            entries = []
            for entry in queryset:
                entries.append({
                    'id': entry.id,
                    'indicator_id': entry.indicator.id,
                    'indicator_name': entry.indicator.name,
                    'org_unit_id': entry.org_unit_id,
                    'org_unit_name': entry.org_unit_name,
                    'period': entry.period,
                    'value': float(entry.value) if entry.value else None,
                    'numerator': float(entry.numerator) if entry.numerator else None,
                    'denominator': float(entry.denominator) if entry.denominator else None,
                    'created_at': entry.created_at.isoformat(),
                    'updated_at': entry.updated_at.isoformat()
                })
            
            return entries
            
        except Exception as e:
            self.logger.error(f"Error getting manual entries: {str(e)}")
            raise
    
    def delete_manual_entry(self, entry_id: int) -> Dict[str, Any]:
        """
        Delete a manual data entry.
        
        Args:
            entry_id: Entry ID to delete
            
        Returns:
            Deletion result
        """
        try:
            entry = IndicatorData.objects.get(
                id=entry_id,
                dhis2_response__manual_entry=True
            )
            
            entry.delete()
            
            # Clear related caches
            self._clear_related_caches(
                entry.indicator.id, 
                entry.org_unit_id, 
                entry.period.replace('manual_', '')
            )
            
            return {
                'success': True,
                'message': 'Manual entry deleted successfully'
            }
            
        except IndicatorData.DoesNotExist:
            raise ValidationError("Manual entry not found")
        except Exception as e:
            self.logger.error(f"Error deleting manual entry: {str(e)}")
            raise
    
    def get_manual_entry_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about manual data entries.
        
        Returns:
            Statistics dictionary
        """
        try:
            total_entries = IndicatorData.objects.filter(
                dhis2_response__manual_entry=True
            ).count()
            
            entries_by_indicator = IndicatorData.objects.filter(
                dhis2_response__manual_entry=True
            ).values('indicator__name').annotate(
                count=Count('id')
            ).order_by('-count')
            
            recent_entries = IndicatorData.objects.filter(
                dhis2_response__manual_entry=True
            ).order_by('-updated_at')[:10]
            
            return {
                'total_entries': total_entries,
                'entries_by_indicator': list(entries_by_indicator),
                'recent_entries': [
                    {
                        'id': entry.id,
                        'indicator_name': entry.indicator.name,
                        'org_unit_id': entry.org_unit_id,
                        'updated_at': entry.updated_at.isoformat()
                    }
                    for entry in recent_entries
                ]
            }
            
        except Exception as e:
            self.logger.error(f"Error getting manual entry statistics: {str(e)}")
            raise
