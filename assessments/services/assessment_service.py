"""
Main Assessment Service

This service orchestrates the assessment process by coordinating other services
and providing a unified interface for assessment operations.
"""

import logging
from typing import Dict, List, Optional, Any
from django.core.exceptions import ValidationError
from django.utils import timezone

from .real_time_service import RealTimeDHIS2Service
from .scoring_service import HolisticScoringService
from .validation_service import ValidationService
from .cache_service import CacheService
from .period_service import PeriodService
from ..models import SavedAssessment

logger = logging.getLogger(__name__)


class AssessmentService:
    """
    Main service for orchestrating assessment operations.
    
    This service coordinates between different specialized services to provide
    a unified interface for assessment functionality.
    """
    
    def __init__(self):
        self.real_time_service = RealTimeDHIS2Service()
        self.scoring_service = HolisticScoringService()
        self.validation_service = ValidationService()
        self.cache_service = CacheService()
        self.period_service = PeriodService()
    
    def generate_assessment(self, request, assessment_config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Generate a complete assessment with real-time data and scoring.
        
        Args:
            request: Django request object
            assessment_config: Configuration for the assessment
            
        Returns:
            List of assessment data for each org unit
        """
        try:
            # Validate assessment configuration
            self.validation_service.validate_assessment_config(assessment_config)
            
            # Generate assessment data using real-time service
            assessment_data = self.real_time_service.fetch_holistic_assessment_data(
                request, assessment_config
            )
            
            # Apply scoring to the assessment data
            self._apply_scoring_to_assessment(assessment_data)
            
            # Cache the assessment results
            cache_key = self._generate_cache_key(request, assessment_config)
            self.cache_service.set_assessment_cache(cache_key, assessment_data)
            
            return assessment_data
            
        except Exception as e:
            logger.error(f"Error generating assessment: {str(e)}")
            raise
    
    def get_cached_assessment(self, request, assessment_config: Dict[str, Any]) -> Optional[List[Dict[str, Any]]]:
        """
        Retrieve cached assessment data if available.
        
        Args:
            request: Django request object
            assessment_config: Configuration for the assessment
            
        Returns:
            Cached assessment data or None if not found
        """
        cache_key = self._generate_cache_key(request, assessment_config)
        return self.cache_service.get_assessment_cache(cache_key)
    
    def _get_dhis2_user(self, request):
        """
        Get the actual DHIS2User instance from the request.
        
        Args:
            request: Django request object
            
        Returns:
            DHIS2User instance or None
        """
        if hasattr(request, 'user') and request.user.is_authenticated:
            try:
                # Try to get the DHIS2User from the wrapper
                if hasattr(request.user, 'dhis2_user'):
                    return request.user.dhis2_user
                else:
                    # Fallback: try to get by username
                    from dhis2_auth.models import DHIS2User
                    return DHIS2User.objects.get(username=request.user.username)
            except Exception as e:
                logger.warning(f"Could not get DHIS2User for {request.user.username}: {str(e)}")
        return None
    
    def save_assessment(self, request, assessment_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Save an assessment to the database.
        
        Args:
            request: Django request object
            assessment_data: Assessment data to save
            
        Returns:
            Saved assessment information
        """
        try:
            # Get the actual DHIS2User instance from the request
            dhis2_user = self._get_dhis2_user(request)
            
            # Extract objectives from the assessment data if it's in the real-time format
            objectives = []
            if 'objectives' in assessment_data:
                objectives = assessment_data['objectives']
            elif 'indicator_data' in assessment_data and isinstance(assessment_data['indicator_data'], dict):
                # If indicator_data contains objectives, extract them
                if 'objectives' in assessment_data['indicator_data']:
                    objectives = assessment_data['indicator_data']['objectives']
            
            # Prepare the data to save
            # Save the complete structure including objectives
            indicator_data = assessment_data.get('indicator_data', {})
            if objectives:
                # If we have objectives, save them in the indicator_data
                indicator_data['objectives'] = objectives
            
            # Create saved assessment record
            saved_assessment = SavedAssessment.objects.create(
                name=assessment_data.get('name', 'Unnamed Assessment'),
                org_unit_id=assessment_data.get('org_unit_id'),
                org_unit_name=assessment_data.get('org_unit_name', ''),
                periods=assessment_data.get('periods', []),
                user_notes=assessment_data.get('user_notes', ''),
                indicator_data=indicator_data,
                calculated_scores=assessment_data.get('calculated_scores', {}),
                metadata=assessment_data.get('metadata', {}),
                created_by=dhis2_user,
                session_key=request.session.session_key if hasattr(request, 'session') else ''
            )
            
            logger.info(f"Assessment saved: {saved_assessment.name} (ID: {saved_assessment.id})")
            
            return {
                'id': saved_assessment.id,
                'name': saved_assessment.name,
                'org_unit_id': saved_assessment.org_unit_id,
                'org_unit_name': saved_assessment.org_unit_name,
                'created_at': saved_assessment.created_at.isoformat(),
                'total_indicators': saved_assessment.total_indicators,
                'total_objectives': saved_assessment.total_objectives
            }
            
        except Exception as e:
            logger.error(f"Error saving assessment: {str(e)}")
            raise
    
    def get_user_assessments(self, request, org_unit_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Retrieve saved assessments for the current user.
        
        Args:
            request: Django request object
            org_unit_id: Optional org unit filter
            
        Returns:
            Paginated list of user assessments
        """
        try:
            from django.db.models import Q
            
            # Get query parameters
            params = request.query_params
            page = int(params.get('page', 1)) if params.get('page') else 1
            size = int(params.get('size', 10)) if params.get('size') else 10
            search = params.get('search', '')
            ordering = params.get('ordering', '-created_at')
            owner = params.get('owner', 'mine')
            
            # Build queryset
            queryset = SavedAssessment.objects.all()
            
            # Apply filters
            if owner != 'all' and hasattr(request, 'user') and request.user.is_authenticated:
                dhis2_user = self._get_dhis2_user(request)
                if dhis2_user:
                    queryset = queryset.filter(created_by=dhis2_user)
            
            if org_unit_id:
                queryset = queryset.filter(org_unit_id=org_unit_id)
            
            if search:
                queryset = queryset.filter(
                    Q(name__icontains=search) | Q(org_unit_name__icontains=search)
                )
            
            # Apply ordering
            allowed_ordering = {'name', 'created_at', '-name', '-created_at'}
            if ordering not in allowed_ordering:
                ordering = '-created_at'
            queryset = queryset.order_by(ordering)
            
            # Pagination
            total = queryset.count()
            start = (page - 1) * size
            end = start + size
            page_qs = queryset[start:end]
            
            # Format results
            results = []
            for assessment in page_qs:
                results.append({
                    'id': assessment.id,
                    'name': assessment.name,
                    'org_unit_id': assessment.org_unit_id,
                    'org_unit_name': assessment.org_unit_name,
                    'created_at': assessment.created_at.isoformat(),
                    'updated_at': assessment.updated_at.isoformat(),
                    'last_opened': assessment.updated_at.isoformat(),
                    'total_indicators': assessment.total_indicators,
                    'total_objectives': assessment.total_objectives,
                    'assessment_type': assessment.assessment_type
                })
            
            return {
                'count': total,
                'page': page,
                'size': size,
                'ordering': ordering,
                'owner': owner if owner in ('mine', 'all') else 'mine',
                'results': results,
            }
            
        except Exception as e:
            logger.error(f"Error retrieving user assessments: {str(e)}")
            return {
                'count': 0,
                'page': 1,
                'size': 10,
                'ordering': '-created_at',
                'owner': 'mine',
                'results': [],
            }
    
    def get_assessment_by_id(self, request, assessment_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve a specific saved assessment.
        
        Args:
            request: Django request object
            assessment_id: ID of the assessment to retrieve
            
        Returns:
            Assessment data or None if not found
        """
        try:
            queryset = SavedAssessment.objects.filter(id=assessment_id)
            
            # Filter by user if available
            if hasattr(request, 'user') and request.user.is_authenticated:
                dhis2_user = self._get_dhis2_user(request)
                if dhis2_user:
                    queryset = queryset.filter(created_by=dhis2_user)
            
            assessment = queryset.first()
            
            if assessment:
                # Convert the indicator_data to match frontend expectations
                indicator_data = assessment.indicator_data or {}
                periods = assessment.periods or []
                
                # Create a mapping from DHIS2 period codes to period names
                # Based on the response data, periods are like ["2023 Q1", "2024 Q1", "2025 Q1"]
                # and data_values keys are like ["2023Q1", "2024Q1", "2025Q1"]
                period_mapping = {}
                for i, period_name in enumerate(periods):
                    # Convert period name to DHIS2 format (remove space)
                    dhis2_period = period_name.replace(' ', '')
                    period_mapping[dhis2_period] = period_name
                
                # Convert data_values keys to match period names
                converted_indicator_data = {}
                for indicator_id, indicator_info in indicator_data.items():
                    if isinstance(indicator_info, dict) and 'data_values' in indicator_info:
                        converted_data_values = {}
                        for dhis2_period, data_value in indicator_info['data_values'].items():
                            # Map DHIS2 period to human-readable period name
                            period_name = period_mapping.get(dhis2_period, dhis2_period)
                            converted_data_values[period_name] = data_value
                        
                        # Update the indicator with converted data_values
                        converted_indicator_data[indicator_id] = {
                            **indicator_info,
                            'data_values': converted_data_values
                        }
                    else:
                        converted_indicator_data[indicator_id] = indicator_info
                
                # Return the data with converted indicator_data
                return {
                    'id': assessment.id,
                    'name': assessment.name,
                    'org_unit_id': assessment.org_unit_id,
                    'org_unit_name': assessment.org_unit_name,
                    'periods': assessment.periods,
                    'user_notes': assessment.user_notes,
                    'indicator_data': converted_indicator_data,
                    'calculated_scores': assessment.calculated_scores,
                    'metadata': assessment.metadata,
                    'created_at': assessment.created_at.isoformat(),
                    'total_indicators': assessment.total_indicators,
                    'total_objectives': assessment.total_objectives,
                    'assessment_type': assessment.assessment_type
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Error retrieving assessment by ID: {str(e)}")
            return None
    
    def update_assessment(self, request, assessment_id: str, assessment_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Update an existing saved assessment.
        
        Args:
            request: Django request object
            assessment_id: ID of the assessment to update
            assessment_data: Updated assessment data
            
        Returns:
            Updated assessment data or None if not found/unauthorized
        """
        try:
            from django.db import transaction
            
            # Find the assessment and verify ownership
            queryset = SavedAssessment.objects.filter(id=assessment_id)
            if hasattr(request, 'user') and request.user.is_authenticated:
                dhis2_user = self._get_dhis2_user(request)
                if dhis2_user:
                    queryset = queryset.filter(created_by=dhis2_user)
            
            assessment = queryset.first()
            if not assessment:
                logger.warning(f"Assessment {assessment_id} not found or user not authorized")
                return None
            
            # Update the assessment
            with transaction.atomic():
                # Update basic fields
                if 'name' in assessment_data:
                    assessment.name = assessment_data['name']
                if 'org_unit_id' in assessment_data:
                    assessment.org_unit_id = assessment_data['org_unit_id']
                if 'org_unit_name' in assessment_data:
                    assessment.org_unit_name = assessment_data['org_unit_name']
                if 'periods' in assessment_data:
                    assessment.periods = assessment_data['periods']
                if 'user_notes' in assessment_data:
                    assessment.user_notes = assessment_data['user_notes']
                
                # Update data fields
                if 'indicator_data' in assessment_data:
                    assessment.indicator_data = assessment_data['indicator_data']
                if 'calculated_scores' in assessment_data:
                    assessment.calculated_scores = assessment_data['calculated_scores']
                if 'metadata' in assessment_data:
                    assessment.metadata = assessment_data['metadata']
                
                assessment.save()
            
            logger.info(f"Assessment updated: {assessment.name} (ID: {assessment.id})")
            
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
                'created_at': assessment.created_at.isoformat(),
                'updated_at': assessment.updated_at.isoformat(),
                'total_indicators': assessment.total_indicators,
                'total_objectives': assessment.total_objectives,
                'assessment_type': assessment.assessment_type
            }
            
        except Exception as e:
            logger.error(f"Error updating assessment {assessment_id}: {str(e)}")
            return None
    
    def delete_assessment(self, request, assessment_id: str) -> bool:
        """
        Delete a saved assessment.
        
        Args:
            request: Django request object
            assessment_id: ID of the assessment to delete
            
        Returns:
            True if deleted, False otherwise
        """
        try:
            queryset = SavedAssessment.objects.filter(id=assessment_id)
            
            if hasattr(request, 'user') and request.user.is_authenticated:
                dhis2_user = self._get_dhis2_user(request)
                if dhis2_user:
                    queryset = queryset.filter(created_by=dhis2_user)
            
            deleted_count, _ = queryset.delete()
            return deleted_count > 0
            
        except Exception as e:
            logger.error(f"Error deleting assessment {assessment_id}: {str(e)}")
            return False
    
    def _apply_scoring_to_assessment(self, assessment_data: List[Dict[str, Any]]) -> None:
        """
        Apply scoring to assessment data.
        
        Args:
            assessment_data: Assessment data to score
        """
        for assessment in assessment_data:
            for objective in assessment.get('objectives', []):
                for indicator in objective.get('indicators', []):
                    # Apply scoring if not already scored
                    if 'score' not in indicator or not indicator['score']:
                        score_data = self.scoring_service.calculate_indicator_score(
                            indicator=indicator,
                            current_value=indicator.get('current_value'),
                            previous_value=indicator.get('previous_value')
                        )
                        indicator['score'] = score_data
    
    def _generate_cache_key(self, request, assessment_config: Dict[str, Any]) -> str:
        """
        Generate a cache key for assessment data.
        
        Args:
            request: Django request object
            assessment_config: Assessment configuration
            
        Returns:
            Cache key string
        """
        import hashlib
        import json
        
        # Create a unique key based on user, org units, periods, and indicators
        key_data = {
            'user_id': getattr(request.user, 'id', None) if hasattr(request, 'user') else None,
            'org_unit_ids': assessment_config.get('org_unit_ids', []),
            'periods': assessment_config.get('periods', []),
            'indicator_uids': assessment_config.get('indicator_uids', []),
            'manual_entries': assessment_config.get('manual_entries', {}),
        }
        
        key_string = json.dumps(key_data, sort_keys=True)
        return f"assessment_{hashlib.md5(key_string.encode()).hexdigest()}"
