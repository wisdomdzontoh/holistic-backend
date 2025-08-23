"""
Period Service

This service handles period conversion and processing for DHIS2.
It provides utilities for converting between different period formats and generating period lists.
"""

import logging
import re
from typing import List, Optional, Any
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class PeriodService:
    """
    Service for handling period operations and conversions.
    """
    
    def process_periods(self, periods_raw: List[Any]) -> List[str]:
        """
        Process periods from various formats to standardized list.
        
        Args:
            periods_raw: Raw periods list (can contain strings or objects)
            
        Returns:
            List of standardized period strings
        """
        periods = []
        
        for period in periods_raw:
            if isinstance(period, dict) and 'code' in period:
                periods.append(period['code'])
            elif isinstance(period, str):
                periods.append(period)
            else:
                # Fallback: try to extract code from period object
                period_code = getattr(period, 'code', str(period))
                periods.append(period_code)
        
        # Sort periods chronologically to ensure correct change calculation
        periods.sort()
        
        return periods
    
    def convert_to_dhis2_period(self, period: Any) -> Optional[str]:
        """
        Convert period to DHIS2 format.
        
        Supported formats:
        - Yearly: 2024 -> 2024
        - Six-monthly: 2024S1, 2024S2
        - Quarterly: 2024Q1, 2024Q2, 2024Q3, 2024Q4
        - Monthly: 202401, 202402, etc.
        - Weekly: 2024W1, 2024W2, etc.
        - Date strings: 2024-01-01 -> 202401
        
        Args:
            period: Period to convert
            
        Returns:
            DHIS2 formatted period string or None
        """
        try:
            if not period or not isinstance(period, (str, dict)):
                logger.warning(f"Invalid period format: {period}")
                return None

            # Handle period dict format
            if isinstance(period, dict):
                if 'code' in period:
                    period = period['code']
                else:
                    logger.warning(f"Invalid period dict format: {period}")
                    return None

            # Handle relative periods
            relative_periods = {
                'THIS_YEAR': lambda: datetime.now().strftime('%Y'),
                'LAST_YEAR': lambda: str(int(datetime.now().strftime('%Y')) - 1),
                'THIS_QUARTER': lambda: self._get_current_quarter(),
                'LAST_QUARTER': lambda: self._get_last_quarter(),
                'THIS_MONTH': lambda: datetime.now().strftime('%Y%m'),
                'LAST_MONTH': lambda: (datetime.now().replace(day=1) - timedelta(days=1)).strftime('%Y%m'),
            }

            if period in relative_periods:
                return relative_periods[period]()

            # Handle date string format (YYYY-MM-DD)
            if re.match(r'^\d{4}-\d{2}-\d{2}$', period):
                try:
                    date_obj = datetime.strptime(period, '%Y-%m-%d')
                    # For date strings, determine the appropriate period format based on the date
                    # For now, convert to quarterly format since that's commonly used
                    year = date_obj.year
                    month = date_obj.month
                    quarter = ((month - 1) // 3) + 1
                    dhis2_period = f"{year}Q{quarter}"
                    logger.info(f"Converted date {period} to quarterly period {dhis2_period}")
                    return dhis2_period
                except ValueError:
                    logger.warning(f"Invalid date string format: {period}")
                    return None

            # Handle fixed period formats
            if re.match(r'^\d{4}$', period):  # Yearly: 2024
                return period
            elif re.match(r'^\d{4}S[1-2]$', period):  # Six-monthly: 2024S1
                return period
            elif re.match(r'^\d{4}\s+S[1-2]$', period):  # Six-monthly: 2024 S1
                return period.replace(' ', '')  # Remove space
            elif re.match(r'^\d{4}Q[1-4]$', period):  # Quarterly: 2024Q1
                return period
            elif re.match(r'^\d{4}\s+Q[1-4]$', period):  # Quarterly: 2024 Q1
                return period.replace(' ', '')  # Remove space
            elif re.match(r'^\d{6}$', period):  # Monthly: 202401
                return period
            elif re.match(r'^\d{4}W[1-53]$', period):  # Weekly: 2024W1
                return period
            elif re.match(r'^\d{4}\s+W[1-53]$', period):  # Weekly: 2024 W1
                return period.replace(' ', '')  # Remove space
            else:
                # Try to parse as date if it contains dashes
                if '-' in period:
                    try:
                        date_obj = datetime.strptime(period.split('T')[0], '%Y-%m-%d')
                        return date_obj.strftime('%Y%m')  # Convert to YYYYMM format
                    except ValueError:
                        pass
                logger.warning(f"Unrecognized period format: {period}")
                return None

        except Exception as e:
            logger.error(f"Error converting period {period}: {str(e)}")
            return None
    
    def get_alternative_periods(self, period: str) -> List[str]:
        """
        Get alternative period formats for a given period.
        
        Args:
            period: Period string
            
        Returns:
            List of alternative period formats
        """
        alternative_periods = []
        
        try:
            # Extract year and period type
            year = period[:4]
            period_type = None
            
            if '-' in period:  # Handle date format like 2022-10-01
                try:
                    date_obj = datetime.strptime(period, '%Y-%m-%d')
                    year = date_obj.strftime('%Y')
                    month = date_obj.strftime('%m')
                    period_type = 'monthly'
                    period = f"{year}{month}"  # Convert to YYYYMM format
                except ValueError:
                    logger.warning(f"Invalid date format: {period}")
                    return []
            elif 'Q' in period:
                period_type = 'quarterly'
            elif 'S' in period:
                period_type = 'sixmonthly'
            
            if period_type == 'monthly':
                # Try quarterly period for the corresponding month
                quarter = ((int(period[4:6]) - 1) // 3) + 1
                alternative_periods.append(f"{year}Q{quarter}")
                
                # Try six-monthly period
                semester = 1 if int(period[4:6]) <= 6 else 2
                alternative_periods.append(f"{year}S{semester}")
                
            elif period_type == 'quarterly':
                # Try monthly periods for the quarter
                quarter = int(period[5])
                start_month = (quarter - 1) * 3 + 1
                for month in range(start_month, start_month + 3):
                    alternative_periods.append(f"{year}{month:02d}")
                    
            elif period_type == 'sixmonthly':
                # Try quarterly periods for the semester
                semester = int(period[5])
                start_quarter = (semester - 1) * 2 + 1
                for quarter in range(start_quarter, start_quarter + 2):
                    alternative_periods.append(f"{year}Q{quarter}")
            
            # Always try yearly as fallback
            alternative_periods.append(year)
            
        except Exception as e:
            logger.error(f"Error generating alternative periods for {period}: {str(e)}")
        
        return alternative_periods
    
    def generate_alternative_periods(self, period: str) -> List[str]:
        """
        Generate alternative period formats for DHIS2 data fetching.
        
        Args:
            period: Period string
            
        Returns:
            List of alternative period formats
        """
        try:
            # Generate alternative period formats based on the input period
            alternative_periods = []
            year = period[:4]
            
            if 'Q' in period:  # Quarterly period
                quarter = int(period[5])
                # Try monthly periods for the quarter
                months = [(quarter - 1) * 3 + i + 1 for i in range(3)]
                for month in months:
                    alternative_periods.append(f"{year}{month:02d}")
                # Try six-monthly period
                semester = 1 if quarter <= 2 else 2
                alternative_periods.append(f"{year}S{semester}")
                # Try yearly period
                alternative_periods.append(year)
                
            elif 'S' in period:  # Six-monthly period
                semester = int(period[5])
                # Try quarterly periods
                quarters = [2*semester - 1, 2*semester]
                for quarter in quarters:
                    alternative_periods.append(f"{year}Q{quarter}")
                # Try monthly periods
                start_month = (semester - 1) * 6 + 1
                for month in range(start_month, start_month + 6):
                    alternative_periods.append(f"{year}{month:02d}")
                # Try yearly period
                alternative_periods.append(year)
                
            elif len(period) == 6:  # Monthly period
                month = int(period[4:6])
                # Try quarterly period
                quarter = (month - 1) // 3 + 1
                alternative_periods.append(f"{year}Q{quarter}")
                # Try six-monthly period
                semester = 1 if month <= 6 else 2
                alternative_periods.append(f"{year}S{semester}")
                # Try yearly period
                alternative_periods.append(year)
                # Try bi-monthly period
                bimonth = (month - 1) // 2 + 1
                alternative_periods.append(f"{year}B{bimonth}")
                
            elif len(period) == 4:  # Yearly period
                # Try all quarters
                for quarter in range(1, 5):
                    alternative_periods.append(f"{year}Q{quarter}")
                # Try all six-monthly periods
                for semester in range(1, 3):
                    alternative_periods.append(f"{year}S{semester}")
                # Try all months
                for month in range(1, 13):
                    alternative_periods.append(f"{year}{month:02d}")
            
            # Add relative periods for recent data
            alternative_periods.extend([
                "THIS_QUARTER",
                "LAST_QUARTER",
                "THIS_YEAR",
                "LAST_YEAR",
                "THIS_SIX_MONTH",
                "LAST_SIX_MONTH"
            ])
            
            return alternative_periods
            
        except Exception as e:
            logger.error(f"Error generating alternative periods: {str(e)}")
            return []
    
    def generate_periods_from_dates(self, start_date: str, end_date: str) -> List[str]:
        """
        Generate period list from date range.
        
        Args:
            start_date: Start date string
            end_date: End date string
            
        Returns:
            List of periods
        """
        periods = []
        
        try:
            # Convert start_date to datetime
            if isinstance(start_date, str):
                if 'Q' in start_date:  # Handle quarterly period format
                    year = int(start_date[:4])
                    quarter = int(start_date[5])
                    month = (quarter - 1) * 3 + 1
                    start = datetime(year, month, 1)
                else:
                    start = datetime.strptime(start_date, '%Y-%m-%d')
            else:
                start = start_date
            
            # Convert end_date to datetime
            if isinstance(end_date, str):
                if 'Q' in end_date:  # Handle quarterly period format
                    year = int(end_date[:4])
                    quarter = int(end_date[5])
                    month = quarter * 3  # Last month of the quarter
                    end = datetime(year, month, 1)
                else:
                    end = datetime.strptime(end_date, '%Y-%m-%d')
            else:
                end = end_date
            
            # Generate periods based on the actual date range
            start_year = start.year
            end_year = end.year
            
            # Check if periods are quarterly (based on input format)
            is_quarterly = isinstance(start_date, str) and 'Q' in start_date
            
            if is_quarterly:
                # Generate quarterly periods
                current = start
                while current <= end:
                    quarter = ((current.month - 1) // 3) + 1
                    period = f"{current.year}Q{quarter}"
                    periods.append(period)
                    
                    # Move to next quarter
                    if quarter == 4:
                        current = current.replace(year=current.year + 1, month=1)
                    else:
                        current = current.replace(month=min(12, (quarter * 3) + 1))
            else:
                # Default to yearly periods for multi-year ranges
                if end_year - start_year > 0:
                    for year in range(start_year, end_year + 1):
                        periods.append(str(year))
                else:
                    # Generate monthly periods for single year
                    current = start
                    while current <= end:
                        period = current.strftime('%Y%m')
                        periods.append(period)
                        
                        # Move to next month
                        if current.month == 12:
                            current = current.replace(year=current.year + 1, month=1)
                        else:
                            current = current.replace(month=current.month + 1)
            
            logger.info(f"Generated periods from {start_date} to {end_date}: {periods}")
            return periods
            
        except Exception as e:
            logger.error(f"Error generating periods from dates: {str(e)}")
            return []
    
    def get_current_quarter(self) -> str:
        """
        Get current quarter in DHIS2 format.
        
        Returns:
            Current quarter string (e.g., "2024Q1")
        """
        now = datetime.now()
        year = now.strftime('%Y')
        quarter = ((now.month - 1) // 3) + 1
        return f"{year}Q{quarter}"
    
    def get_last_quarter(self) -> str:
        """
        Get last quarter in DHIS2 format.
        
        Returns:
            Last quarter string (e.g., "2024Q4")
        """
        now = datetime.now()
        year = now.strftime('%Y')
        quarter = ((now.month - 1) // 3)
        
        if quarter == 0:
            year = str(int(year) - 1)
            quarter = 4
        
        return f"{year}Q{quarter}"
    
    def get_current_year(self) -> str:
        """
        Get current year.
        
        Returns:
            Current year string
        """
        return datetime.now().strftime('%Y')
    
    def get_last_year(self) -> str:
        """
        Get last year.
        
        Returns:
            Last year string
        """
        return str(int(datetime.now().strftime('%Y')) - 1)
    
    def get_current_month(self) -> str:
        """
        Get current month in DHIS2 format.
        
        Returns:
            Current month string (e.g., "202401")
        """
        return datetime.now().strftime('%Y%m')
    
    def get_last_month(self) -> str:
        """
        Get last month in DHIS2 format.
        
        Returns:
            Last month string (e.g., "202312")
        """
        last_month = datetime.now().replace(day=1) - timedelta(days=1)
        return last_month.strftime('%Y%m')
    
    def validate_period_format(self, period: str) -> bool:
        """
        Validate if a period string is in a valid format.
        
        Args:
            period: Period string to validate
            
        Returns:
            True if valid, False otherwise
        """
        if not isinstance(period, str):
            return False
        
        # Check for valid period formats
        patterns = [
            r'^\d{4}$',  # Yearly: 2024
            r'^\d{4}S[1-2]$',  # Six-monthly: 2024S1
            r'^\d{4}\s+S[1-2]$',  # Six-monthly with space: 2024 S1
            r'^\d{4}Q[1-4]$',  # Quarterly: 2024Q1
            r'^\d{4}\s+Q[1-4]$',  # Quarterly with space: 2024 Q1
            r'^\d{6}$',  # Monthly: 202401
            r'^\d{4}W[1-53]$',  # Weekly: 2024W1
            r'^\d{4}\s+W[1-53]$',  # Weekly with space: 2024 W1
            r'^\d{4}-\d{2}-\d{2}$',  # Date: 2024-01-01
        ]
        
        for pattern in patterns:
            if re.match(pattern, period):
                return True
        
        # Check for relative periods
        relative_periods = {
            'THIS_YEAR', 'LAST_YEAR', 'THIS_QUARTER', 'LAST_QUARTER',
            'THIS_MONTH', 'LAST_MONTH', 'THIS_SIX_MONTH', 'LAST_SIX_MONTH'
        }
        
        if period in relative_periods:
            return True
        
        # Handle human-readable period formats like "January 2023"
        month_names = [
            'January', 'February', 'March', 'April', 'May', 'June',
            'July', 'August', 'September', 'October', 'November', 'December'
        ]
        
        # Pattern for "Month Year" format
        month_year_pattern = r'^(' + '|'.join(month_names) + r')\s+\d{4}$'
        if re.match(month_year_pattern, period, re.IGNORECASE):
            return True
        
        # Pattern for "Month Year" with comma
        month_year_comma_pattern = r'^(' + '|'.join(month_names) + r'),\s*\d{4}$'
        if re.match(month_year_comma_pattern, period, re.IGNORECASE):
            return True
        
        return False
    
    def get_period_type(self, period: str) -> Optional[str]:
        """
        Get the type of a period.
        
        Args:
            period: Period string
            
        Returns:
            Period type or None if unknown
        """
        if not self.validate_period_format(period):
            return None
        
        if re.match(r'^\d{4}$', period):
            return 'yearly'
        elif re.match(r'^\d{4}S[1-2]$', period):
            return 'sixmonthly'
        elif re.match(r'^\d{4}Q[1-4]$', period):
            return 'quarterly'
        elif re.match(r'^\d{6}$', period):
            return 'monthly'
        elif re.match(r'^\d{4}W[1-53]$', period):
            return 'weekly'
        elif re.match(r'^\d{4}-\d{2}-\d{2}$', period):
            return 'date'
        else:
            return 'relative'
    
    def get_period_year(self, period: str) -> Optional[int]:
        """
        Extract year from a period string.
        
        Args:
            period: Period string
            
        Returns:
            Year as integer or None
        """
        try:
            if re.match(r'^\d{4}', period):
                return int(period[:4])
            return None
        except (ValueError, TypeError):
            return None
    
    def get_period_month(self, period: str) -> Optional[int]:
        """
        Extract month from a period string.
        
        Args:
            period: Period string
            
        Returns:
            Month as integer or None
        """
        try:
            if re.match(r'^\d{6}$', period):  # Monthly format
                return int(period[4:6])
            elif re.match(r'^\d{4}Q[1-4]$', period):  # Quarterly format
                quarter = int(period[5])
                return (quarter - 1) * 3 + 1  # First month of quarter
            return None
        except (ValueError, TypeError):
            return None
    
    def get_period_quarter(self, period: str) -> Optional[int]:
        """
        Extract quarter from a period string.
        
        Args:
            period: Period string
            
        Returns:
            Quarter as integer or None
        """
        try:
            if re.match(r'^\d{4}Q[1-4]$', period):
                return int(period[5])
            elif re.match(r'^\d{6}$', period):  # Monthly format
                month = int(period[4:6])
                return ((month - 1) // 3) + 1
            return None
        except (ValueError, TypeError):
            return None
    
    def get_period_semester(self, period: str) -> Optional[int]:
        """
        Extract semester from a period string.
        
        Args:
            period: Period string
            
        Returns:
            Semester as integer or None
        """
        try:
            if re.match(r'^\d{4}S[1-2]$', period):
                return int(period[5])
            elif re.match(r'^\d{6}$', period):  # Monthly format
                month = int(period[4:6])
                return 1 if month <= 6 else 2
            elif re.match(r'^\d{4}Q[1-4]$', period):  # Quarterly format
                quarter = int(period[5])
                return 1 if quarter <= 2 else 2
            return None
        except (ValueError, TypeError):
            return None
    
    def _get_current_quarter(self) -> str:
        """
        Get current quarter in DHIS2 format.
        
        Returns:
            Current quarter string
        """
        now = datetime.now()
        year = now.strftime('%Y')
        quarter = ((now.month - 1) // 3) + 1
        return f"{year}Q{quarter}"
    
    def _get_last_quarter(self) -> str:
        """
        Get last quarter in DHIS2 format.
        
        Returns:
            Last quarter string
        """
        now = datetime.now()
        year = now.strftime('%Y')
        quarter = ((now.month - 1) // 3)
        
        if quarter == 0:
            year = str(int(year) - 1)
            quarter = 4
        
        return f"{year}Q{quarter}"
