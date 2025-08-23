#!/usr/bin/env python
"""
Assessment Save Service

This service handles saving and retrieving assessment data.
"""

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.db import transaction
from django.db.models import Q

from ..models import SavedAssessment, TrackedIndicator
from .validation_service import ValidationService
from .cache_service import CacheService

logger = logging.getLogger(__name__)


class AssessmentSaveService:
    """
    Service for saving and retrieving assessment data.
    
    This service manages the persistence of assessment results,
    including saving new assessments and retrieving existing ones.
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.validation_service = ValidationService()
        self.cache_service = CacheService()
    
    def save_assessment(self, request, assessment_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Save assessment data to the database.
        
        Args:
            request: HTTP request object
            assessment_data: Assessment data to save
            
        Returns:
            Saved assessment information
        """
        try:
            with transaction.atomic():
                # Validate assessment data
                self.validation_service.validate_assessment_data(assessment_data)
                
                # Create saved assessment
                saved_assessment = self._create_saved_assessment(request, assessment_data)
                
                # Clear related caches
                self._clear_assessment_caches(saved_assessment.org_unit_id, saved_assessment.id)
                
                return {
                    'success': True,
                    'message': 'Assessment saved successfully',
                    'assessment_id': saved_assessment.id,
                    'assessment_name': saved_assessment.name,
                    'created_at': saved_assessment.created_at.isoformat()
                }
                
        except Exception as e:
            self.logger.error(f"Error saving assessment: {str(e)}")
            raise
    
    def _create_saved_assessment(self, request, assessment_data: Dict[str, Any]) -> SavedAssessment:
        """
        Create a new saved assessment.
        
        Args:
            request: HTTP request object
            assessment_data: Assessment data
            
        Returns:
            Created SavedAssessment instance
        """
        try:
            # Extract basic information
            name = assessment_data.get('name', f"Assessment {timezone.now().strftime('%Y-%m-%d %H:%M')}")
            org_unit_id = assessment_data.get('org_unit_id')
            org_unit_name = assessment_data.get('org_unit_name', org_unit_id)
            periods = assessment_data.get('periods', [])
            user_notes = assessment_data.get('user_notes', '')
            
            # Get the actual DHIS2User instance from the request
            dhis2_user = None
            if hasattr(request, 'user') and request.user.is_authenticated:
                try:
                    # Try to get the DHIS2User from the wrapper
                    if hasattr(request.user, 'dhis2_user'):
                        dhis2_user = request.user.dhis2_user
                    else:
                        # Fallback: try to get by username
                        from dhis2_auth.models import DHIS2User
                        dhis2_user = DHIS2User.objects.get(username=request.user.username)
                except Exception as e:
                    self.logger.warning(f"Could not get DHIS2User for {request.user.username}: {str(e)}")
                    dhis2_user = None
            
            # Create the saved assessment
            saved_assessment = SavedAssessment.objects.create(
                name=name,
                org_unit_id=org_unit_id,
                org_unit_name=org_unit_name,
                periods=periods,
                user_notes=user_notes,
                indicator_data=assessment_data.get('indicator_data', {}),
                calculated_scores=assessment_data.get('calculated_scores', {}),
                metadata=assessment_data.get('metadata', {}),
                created_by=dhis2_user,
                session_key=request.session.session_key if hasattr(request, 'session') else ''
            )
            
            self.logger.info(f"Created saved assessment {saved_assessment.id}")
            return saved_assessment
            
        except Exception as e:
            self.logger.error(f"Error creating saved assessment: {str(e)}")
            raise
    
    def get_saved_assessment(self, assessment_id: int) -> Optional[Dict[str, Any]]:
        """
        Get a specific saved assessment.
        
        Args:
            assessment_id: Assessment ID
            
        Returns:
            Assessment data or None if not found
        """
        try:
            assessment = SavedAssessment.objects.get(id=assessment_id)
            
            return {
                'id': assessment.id,
                'name': assessment.name,
                'org_unit_id': assessment.org_unit_id,
                'org_unit_name': assessment.org_unit_name,
                'periods': assessment.periods,
                'user_notes': assessment.user_notes,
                'indicator_data': assessment.indicator_data,
                'calculated_scores': assessment.calculated_scores,
                'metadata': assessment.metadata,
                'created_by': assessment.created_by.username if assessment.created_by else None,
                'created_at': assessment.created_at.isoformat(),
                'updated_at': assessment.updated_at.isoformat()
            }
            
        except SavedAssessment.DoesNotExist:
            return None
        except Exception as e:
            self.logger.error(f"Error getting saved assessment: {str(e)}")
            raise
    
    def get_user_assessments(self, user_id: int, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Get assessments created by a specific user.
        
        Args:
            user_id: User ID
            limit: Maximum number of assessments to return
            
        Returns:
            List of assessment summaries
        """
        try:
            assessments = SavedAssessment.objects.filter(
                created_by_id=user_id
            ).order_by('-created_at')[:limit]
            
            return [
                {
                    'id': assessment.id,
                    'name': assessment.name,
                    'org_unit_id': assessment.org_unit_id,
                    'org_unit_name': assessment.org_unit_name,
                    'created_at': assessment.created_at.isoformat(),
                    'updated_at': assessment.updated_at.isoformat(),
                    'total_indicators': assessment.total_indicators,
                    'total_objectives': assessment.total_objectives,
                    'assessment_type': assessment.assessment_type
                }
                for assessment in assessments
            ]
            
        except Exception as e:
            self.logger.error(f"Error getting user assessments: {str(e)}")
            raise
    
    def update_assessment(self, assessment_id: int, updates: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update an existing assessment.
        
        Args:
            assessment_id: Assessment ID
            updates: Dictionary of updates
            
        Returns:
            Update result
        """
        try:
            with transaction.atomic():
                assessment = SavedAssessment.objects.get(id=assessment_id)
                
                # Update fields
                if 'name' in updates:
                    assessment.name = updates['name']
                if 'user_notes' in updates:
                    assessment.user_notes = updates['user_notes']
                if 'indicator_data' in updates:
                    assessment.indicator_data = updates['indicator_data']
                if 'calculated_scores' in updates:
                    assessment.calculated_scores = updates['calculated_scores']
                if 'metadata' in updates:
                    assessment.metadata = updates['metadata']
                
                assessment.save()
                
                # Clear related caches
                self._clear_assessment_caches(assessment.org_unit_id, assessment.id)
                
                return {
                    'success': True,
                    'message': 'Assessment updated successfully',
                    'updated_at': assessment.updated_at.isoformat()
                }
                
        except SavedAssessment.DoesNotExist:
            raise ValidationError("Assessment not found")
        except Exception as e:
            self.logger.error(f"Error updating assessment: {str(e)}")
            raise
    
    def delete_assessment(self, assessment_id: int) -> Dict[str, Any]:
        """
        Delete an assessment.
        
        Args:
            assessment_id: Assessment ID
            
        Returns:
            Deletion result
        """
        try:
            assessment = SavedAssessment.objects.get(id=assessment_id)
            org_unit_id = assessment.org_unit_id
            
            assessment.delete()
            
            # Clear related caches
            self._clear_assessment_caches(org_unit_id, assessment_id)
            
            return {
                'success': True,
                'message': 'Assessment deleted successfully'
            }
            
        except SavedAssessment.DoesNotExist:
            raise ValidationError("Assessment not found")
        except Exception as e:
            self.logger.error(f"Error deleting assessment: {str(e)}")
            raise
    
    def search_assessments(self, query: str, user_id: Optional[int] = None, 
                          limit: int = 20) -> List[Dict[str, Any]]:
        """
        Search assessments by name or org unit.
        
        Args:
            query: Search query
            user_id: Optional user ID filter
            limit: Maximum number of results
            
        Returns:
            List of matching assessments
        """
        try:
            queryset = SavedAssessment.objects.filter(
                Q(name__icontains=query) | 
                Q(org_unit_name__icontains=query) |
                Q(org_unit_id__icontains=query)
            )
            
            if user_id:
                queryset = queryset.filter(created_by_id=user_id)
            
            assessments = queryset.order_by('-created_at')[:limit]
            
            return [
                {
                    'id': assessment.id,
                    'name': assessment.name,
                    'org_unit_id': assessment.org_unit_id,
                    'org_unit_name': assessment.org_unit_name,
                    'created_at': assessment.created_at.isoformat(),
                    'created_by': assessment.created_by.username if assessment.created_by else None
                }
                for assessment in assessments
            ]
            
        except Exception as e:
            self.logger.error(f"Error searching assessments: {str(e)}")
            raise
    
    def get_assessment_statistics(self, user_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Get statistics about saved assessments.
        
        Args:
            user_id: Optional user ID filter
            
        Returns:
            Statistics dictionary
        """
        try:
            queryset = SavedAssessment.objects
            
            if user_id:
                queryset = queryset.filter(created_by_id=user_id)
            
            total_assessments = queryset.count()
            recent_assessments = queryset.filter(
                created_at__gte=timezone.now() - timezone.timedelta(days=30)
            ).count()
            
            # Get unique org units
            unique_org_units = queryset.values('org_unit_id').distinct().count()
            
            # Get assessment types
            assessment_types = queryset.values('metadata__assessment_type').distinct().count()
            
            return {
                'total_assessments': total_assessments,
                'recent_assessments': recent_assessments,
                'unique_org_units': unique_org_units,
                'assessment_types': assessment_types
            }
            
        except Exception as e:
            self.logger.error(f"Error getting assessment statistics: {str(e)}")
            raise
    
    def export_assessment_data(self, assessment_id: int, format_type: str = 'json') -> Dict[str, Any]:
        """
        Export assessment data in various formats.
        
        Args:
            assessment_id: Assessment ID
            format_type: Export format ('json', 'csv', 'excel')
            
        Returns:
            Export data
        """
        try:
            assessment = SavedAssessment.objects.get(id=assessment_id)
            
            if format_type == 'json':
                return self._export_to_json(assessment)
            elif format_type == 'csv':
                return self._export_to_csv(assessment)
            elif format_type == 'excel':
                return self._export_to_excel(assessment)
            else:
                raise ValidationError(f"Unsupported format: {format_type}")
                
        except SavedAssessment.DoesNotExist:
            raise ValidationError("Assessment not found")
        except Exception as e:
            self.logger.error(f"Error exporting assessment data: {str(e)}")
            raise
    
    def _export_to_json(self, assessment: SavedAssessment) -> Dict[str, Any]:
        """Export assessment to JSON format."""
        return {
            'format': 'json',
            'data': {
                'id': assessment.id,
                'name': assessment.name,
                'org_unit_id': assessment.org_unit_id,
                'org_unit_name': assessment.org_unit_name,
                'periods': assessment.periods,
                'user_notes': assessment.user_notes,
                'indicator_data': assessment.indicator_data,
                'calculated_scores': assessment.calculated_scores,
                'metadata': assessment.metadata,
                'created_by': assessment.created_by.username if assessment.created_by else None,
                'created_at': assessment.created_at.isoformat(),
                'updated_at': assessment.updated_at.isoformat()
            }
        }
    
    def _export_to_csv(self, assessment: SavedAssessment) -> Dict[str, Any]:
        """Export assessment to CSV format."""
        # This would generate CSV data
        # For now, return a placeholder
        return {
            'format': 'csv',
            'data': f"Assessment data for {assessment.name}",
            'filename': f"assessment_{assessment.id}.csv"
        }
    
    def _export_to_excel(self, assessment: SavedAssessment) -> Dict[str, Any]:
        """Export assessment to Excel format."""
        # This would generate Excel data
        # For now, return a placeholder
        return {
            'format': 'excel',
            'data': f"Assessment data for {assessment.name}",
            'filename': f"assessment_{assessment.id}.xlsx"
        }
    
    def _clear_assessment_caches(self, org_unit_id: str, assessment_id: int) -> None:
        """
        Clear caches related to the assessment.
        
        Args:
            org_unit_id: Organization unit ID
            assessment_id: Assessment ID
        """
        try:
            cache_keys = [
                f"assessment_{assessment_id}",
                f"user_assessments_{org_unit_id}",
                f"assessment_stats_{org_unit_id}"
            ]
            
            for cache_key in cache_keys:
                self.cache_service.clear_cache(cache_key)
                
        except Exception as e:
            self.logger.error(f"Error clearing assessment caches: {str(e)}")
