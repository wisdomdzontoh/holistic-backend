#!/usr/bin/env python
"""
Assessment services for DHIS2 integration and score calculation

This file maintains backward compatibility by importing and re-exporting
all services from the modular structure in the services/ directory.
"""

# Import all services from the modular structure
from .services import (
    # Core assessment services
    AssessmentService,
    RealTimeDHIS2Service,
    DataSyncService,
    HolisticScoringService,
    ManualDataEntryService,
    AssessmentSaveService,
    
    # Dashboard and analytics services
    DashboardService,
    AnalyticsService,
    
    # Excel and export services
    ExcelExportService,
    
    # Data processing services
    DataProcessingService,
    PeriodService,
    
    # Utility services
    ValidationService,
    CacheService,
)

# Re-export all services for backward compatibility
__all__ = [
    # Core services
    'AssessmentService',
    'RealTimeDHIS2Service',
    'DataSyncService',
    'HolisticScoringService',
    'ManualDataEntryService',
    'AssessmentSaveService',
    
    # Dashboard and analytics
    'DashboardService',
    'AnalyticsService',
    
    # Export services
    'ExcelExportService',
    
    # Data processing
    'DataProcessingService',
    'PeriodService',
    
    # Utilities
    'ValidationService',
    'CacheService',
]

# Legacy aliases for backward compatibility
# These maintain compatibility with any existing code that might use old class names
ScoreCalculationService = HolisticScoringService  # Legacy alias

# Note: All the original service classes have been moved to their respective modules
# in the services/ directory. This file now serves as a compatibility layer.
# 
# For new code, it's recommended to import directly from the specific service modules:
#   from .services.assessment_service import AssessmentService
#   from .services.scoring_service import HolisticScoringService
#   etc.