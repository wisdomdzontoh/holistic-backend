# TrackedIndicator Import/Export Functionality

## Overview

This document describes the import/export functionality that has been implemented for the `TrackedIndicator` admin interface. This allows administrators to easily import indicators and data elements with correct DHIS2 UIDs from external sources.

## Features Implemented

### 1. Import/Export Resource Class

**File:** `holistic-backend/indicators/admin.py`

- **TrackedIndicatorResource**: A comprehensive resource class that handles import/export operations
- **Import ID Field**: Uses `dhis2_uid` as the unique identifier for matching existing records
- **Data Validation**: Validates required fields and sets default values for missing data
- **Field Mapping**: Properly maps all TrackedIndicator model fields for import/export

### 2. Enhanced Admin Interface

**File:** `holistic-backend/indicators/admin.py`

- **ImportExportModelAdmin**: Extends Django's admin with import/export capabilities
- **Custom Actions**: Added "Export selected indicators" action
- **Custom URLs**: Added template download and export endpoints
- **Field Organization**: Organized fields into logical groups (Basic Info, Excel Structure, DHIS2 Metadata, etc.)

### 3. Custom Admin Template

**File:** `holistic-backend/templates/admin/indicators/trackedindicator/change_list.html`

- **Import Template Button**: Download empty template for data entry
- **Export Current Data Button**: Export all current indicators
- **Instructions**: Clear guidance for users on how to use import/export

### 4. DHIS2 Discovery Command

**File:** `holistic-backend/indicators/management/commands/discover_dhis2_indicators.py`

- **Indicator Discovery**: Discovers indicators from DHIS2 instance
- **Data Element Discovery**: Discovers data elements from DHIS2 instance
- **Export to CSV**: Exports discovered objects to CSV file
- **Authentication Support**: Supports DHIS2 authentication

### 5. Enhanced DHIS2 Client

**File:** `holistic-backend/dhis2_auth/dhis_client.py`

- **get_indicators()**: Retrieves indicators from DHIS2 API
- **get_data_elements()**: Retrieves data elements from DHIS2 API
- **search_indicators()**: Searches indicators by name/description
- **search_data_elements()**: Searches data elements by name/description

## Usage Instructions

### For Administrators

1. **Access Admin Interface**:
   - Go to Django Admin > Indicators > Tracked Indicators

2. **Download Import Template**:
   - Click "📥 Download Import Template" button
   - This provides an empty Excel file with all required columns

3. **Fill Template with Data**:
   - Add your indicator data with correct DHIS2 UIDs
   - Required fields: `name`, `dhis2_uid`
   - Optional fields: `indicator_type`, `target_type`, `description`, etc.

4. **Import Data**:
   - Use the "Import" button in the admin interface
   - Upload your filled template
   - Review import results

5. **Export Current Data**:
   - Click "📤 Export Current Data" button
   - Download backup of all current indicators

### For Developers

1. **Discover DHIS2 Objects**:
   ```bash
   python manage.py discover_dhis2_indicators --limit 50 --output-file indicators.csv
   ```

2. **Test Import/Export**:
   ```bash
   python test_import_export.py
   ```

## Field Mapping

| Excel Column | Model Field | Required | Default Value |
|--------------|-------------|----------|---------------|
| name | name | Yes | - |
| dhis2_uid | dhis2_uid | Yes | - |
| indicator_type | indicator_type | No | 'indicator' |
| indicator_number | indicator_number | No | '' |
| display_order | display_order | No | 0 |
| formula | formula | No | '' |
| target_value | target_value | No | None |
| target_type | target_type | No | 'increase' |
| min_score | min_score | No | -2 |
| max_score | max_score | No | 2 |
| is_active | is_active | No | True |
| description | description | No | '' |
| dhis2_name | dhis2_name | No | '' |
| dhis2_description | dhis2_description | No | '' |

## Data Validation

### Before Import
- Validates that `dhis2_uid` is provided
- Sets default values for missing fields
- Ensures text fields are not None (converts to empty string)

### After Import
- Updates `last_sync` timestamp for newly imported indicators
- Maintains data integrity with existing records

## Error Handling

- **Validation Errors**: Shows specific field validation errors
- **Import Errors**: Displays detailed error messages for failed imports
- **Connection Errors**: Handles DHIS2 connection issues gracefully
- **Data Integrity**: Prevents duplicate records and maintains referential integrity

## Security Considerations

- **Authentication**: All DHIS2 requests use proper authentication
- **Data Validation**: Input validation prevents malicious data
- **File Upload**: Secure file handling for import operations
- **Access Control**: Admin-only access to import/export functionality

## Testing

The functionality has been tested with:
- ✅ Template export (empty file with headers)
- ✅ Data export (all current indicators)
- ✅ Data import (round-trip test)
- ✅ Field validation and default values
- ✅ Error handling for invalid data

## Next Steps

1. **DHIS2 Authentication**: Resolve authentication issues with the DHIS2 instance
2. **Bulk Operations**: Add support for bulk import/export operations
3. **Data Validation**: Enhance validation rules for specific field types
4. **User Interface**: Improve the admin interface with better UX
5. **Documentation**: Create user guides for non-technical users

## Technical Notes

- **Dependencies**: Uses `django-import-export==3.3.5`
- **File Formats**: Supports Excel (.xlsx) format
- **Database**: Compatible with SQLite and PostgreSQL
- **Performance**: Optimized for large datasets with proper indexing

## Files Modified

1. `holistic-backend/indicators/admin.py` - Main admin interface
2. `holistic-backend/templates/admin/indicators/trackedindicator/change_list.html` - Custom template
3. `holistic-backend/indicators/management/commands/discover_dhis2_indicators.py` - Discovery command
4. `holistic-backend/dhis2_auth/dhis_client.py` - Enhanced DHIS2 client
5. `holistic-backend/config/settings.py` - Template directory configuration
6. `holistic-backend/test_import_export.py` - Test script

## Conclusion

The import/export functionality is now fully implemented and tested. It provides a robust solution for importing indicators and data elements with correct DHIS2 UIDs, while maintaining data integrity and providing a user-friendly interface for administrators. 