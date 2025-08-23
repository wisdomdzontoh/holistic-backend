"""
Holistic Scoring Service

This service implements the Holistic Assessment scoring algorithm based on Excel formulas.
It provides scoring functionality for indicators, objectives, and sector levels.
"""

import logging
from decimal import Decimal
from typing import Dict, Any, Optional, List
from django.utils import timezone

from indicators.models import TrackedIndicator
from configurations.models import ScoringRule
from ..models import IndicatorScore, ScoringContext

logger = logging.getLogger(__name__)


class HolisticScoringService:
    """
    Simplified Holistic Assessment scoring algorithm based on Excel formulas.
    Matches the exact logic shown in the performance analysis table.
    """
    
    def calculate_indicator_score(
        self,
        indicator: TrackedIndicator,
        current_value: Optional[float],
        previous_value: Optional[float],
        data_provided: bool = True
    ) -> Dict[str, Any]:
        """
        Calculate score using simplified Holistic Assessment algorithm.
        
        Based on Excel formulas from the performance analysis table:
        - Data Provided: =IF($G4<>"","Yes","No")
        - First Year: =IF(OR($F4<>"",$E4<>"",$D4<>"",$C4<>""),"No","Yes")
        - Target Achieved: =IF($G4<=J4,"Yes","No")
        - Performance Change: =IF($H4<=-10%,"<=-10%",IF($H4<=-5%,"-10%<C<=-5%",IF($H4<=5%,"5%<=C>-5%",IF($H4>5%,">5%",""))))
        - Gap to Target: =IF($I4<=10%,"<=10%",IF(AND($I4>10%,$I4<=40%),"10%<PT<=40%",IF($I4>40%,">40%","")))
        
        Args:
            indicator: Indicator instance
            current_value: Current period value
            previous_value: Previous period value
            data_provided: Whether data is provided
            
        Returns:
            Dictionary containing scoring results
        """
        
        # Step 1: Data Provided (Column G) - =IF($G4<>"","Yes","No")
        data_provided_flag = "Yes" if data_provided and current_value is not None else "No"
        
        # Step 2: First Year of Reporting - =IF(OR($F4<>"",$E4<>"",$D4<>"",$C4<>""),"No","Yes")
        has_previous_data = previous_value is not None
        is_first_year = "Yes" if not has_previous_data else "No"
        
        # Step 3: Was Target Achieved - =IF($G4<=J4,"Yes","No")
        target_achieved = self._check_target_achievement(current_value, indicator)
        
        # Step 4: Performance Change (Column H)
        percent_change = self._calculate_percent_change(current_value, previous_value, indicator)
        change_category = self._classify_change_category(percent_change, indicator.target_type)
        
        # Step 5: Gap to Target (Column I)
        target_gap = self._calculate_target_gap(current_value, indicator)
        gap_category = self._classify_gap_category(target_gap)
        
        # Step 6: Calculate final score based on the flowchart logic
        score = self._calculate_final_score(
            data_provided_flag, is_first_year, target_achieved, 
            change_category, gap_category, indicator
        )
        
        # Debug logging
        logger.debug(f"Scoring Debug for Indicator {indicator.id} ({indicator.name}):")
        logger.debug(f"  target_type: {indicator.target_type}")
        logger.debug(f"  target_operator: {indicator.target_operator}")
        logger.debug(f"  target_value: {indicator.target_value}")
        logger.debug(f"  current_value: {current_value}")
        logger.debug(f"  previous_value: {previous_value}")
        logger.debug(f"  percent_change: {percent_change}")
        logger.debug(f"  target_achieved: {target_achieved}")
        logger.debug(f"  change_category: {change_category}")
        logger.debug(f"  gap_category: {gap_category}")
        logger.debug(f"  final_score: {score}")
        
        return {
            'score': score,
            'data_provided': data_provided_flag,
            'is_first_year': is_first_year,
            'target_achieved': target_achieved,
            'change_category': change_category,
            'gap_category': gap_category,
            'percent_change': percent_change,
            'target_gap': target_gap,
            'current_value': current_value,
            'previous_value': previous_value,
            'target_value': float(indicator.target_value) if indicator.target_value else None
        }
    
    def _check_target_achievement(self, current_value: Optional[float], indicator: TrackedIndicator) -> str:
        """
        Check if target was achieved.
        
        Args:
            current_value: Current value
            indicator: Indicator instance
            
        Returns:
            "Yes" or "No"
        """
        if current_value is None:
            return "No"
        
        try:
            current_val = float(current_value)
            
            # Handle different target formats
            if hasattr(indicator, 'target_format') and indicator.target_format == 'RANGE':
                # Range target: check if current value is within the range
                if indicator.target_lower_limit is not None and indicator.target_upper_limit is not None:
                    lower_limit = float(indicator.target_lower_limit)
                    upper_limit = float(indicator.target_upper_limit)
                    return "Yes" if lower_limit <= current_val <= upper_limit else "No"
                else:
                    # Fallback to single target value
                    if indicator.target_value is not None:
                        target_float = float(indicator.target_value)
                        if indicator.target_type == 'decrease':
                            return "Yes" if current_val <= target_float else "No"
                        else:
                            return "Yes" if current_val >= target_float else "No"
            elif hasattr(indicator, 'target_format') and indicator.target_format == 'MINIMUM':
                # Minimum target: current value should be >= target_value
                if indicator.target_value is not None:
                    target_float = float(indicator.target_value)
                    return "Yes" if current_val >= target_float else "No"
            elif hasattr(indicator, 'target_format') and indicator.target_format == 'MAXIMUM':
                # Maximum target: current value should be <= target_value
                if indicator.target_value is not None:
                    target_float = float(indicator.target_value)
                    return "Yes" if current_val <= target_float else "No"
            else:
                # Single value target: use the target_operator
                if indicator.target_value is not None:
                    target_float = float(indicator.target_value)
                    
                    # Use the target_operator to determine achievement
                    if indicator.target_operator == '>=':
                        return "Yes" if current_val >= target_float else "No"
                    elif indicator.target_operator == '>':
                        return "Yes" if current_val > target_float else "No"
                    elif indicator.target_operator == '<=':
                        return "Yes" if current_val <= target_float else "No"
                    elif indicator.target_operator == '<':
                        return "Yes" if current_val < target_float else "No"
                    elif indicator.target_operator == '=':
                        return "Yes" if current_val == target_float else "No"
                    else:
                        # Default to >= for backward compatibility
                        return "Yes" if current_val >= target_float else "No"
            
            return "No"
            
        except Exception:
            return "No"
    
    def _calculate_percent_change(
        self, 
        current_value: Optional[float], 
        previous_value: Optional[float], 
        indicator: TrackedIndicator
    ) -> Optional[float]:
        """
        Calculate percentage change between current and previous values.
        
        Args:
            current_value: Current period value
            previous_value: Previous period value
            indicator: Indicator instance
            
        Returns:
            Percentage change or None
        """
        if current_value is None or previous_value is None:
            return None
        
        try:
            target_format = getattr(indicator, 'target_format', 'SINGLE')
            
            if target_format == 'RANGE':
                # For range indicators, always use standard formula regardless of target_type
                if previous_value != 0:
                    return round(((current_value - previous_value) / abs(previous_value)) * 100, 2)
            else:
                # For non-range indicators, use target_type specific formula
                if indicator.target_type == 'decrease':
                    # For decrease indicators: (previous_value - current_value) / abs(current_value) * 100
                    if current_value != 0:
                        return round(((previous_value - current_value) / abs(current_value)) * 100, 2)
                    else:
                        # Special case: current value is 0 for decrease indicator
                        return None
                else:
                    # For increase indicators: (current_value - previous_value) / abs(previous_value) * 100
                    if previous_value != 0:
                        return round(((current_value - previous_value) / abs(previous_value)) * 100, 2)
            
            return None
            
        except Exception:
            return None
    
    def _calculate_target_gap(self, current_value: Optional[float], indicator: TrackedIndicator) -> Optional[float]:
        """
        Calculate gap to target.
        
        Args:
            current_value: Current value
            indicator: Indicator instance
            
        Returns:
            Target gap percentage or None
        """
        if current_value is None:
            return None
        
        try:
            # Handle different target formats for gap calculation
            if hasattr(indicator, 'target_format') and indicator.target_format == 'RANGE':
                # Range target: calculate gap to the upper limit
                if indicator.target_lower_limit is not None and indicator.target_upper_limit is not None:
                    upper_limit = float(indicator.target_upper_limit)
                    if upper_limit != 0:
                        return round((current_value - upper_limit) / upper_limit * 100, 2)
                else:
                    # Fallback to single target value
                    if indicator.target_value is not None:
                        target_float = float(indicator.target_value)
                        if target_float != 0:
                            if indicator.target_type == 'decrease':
                                if current_value != 0:
                                    return round((target_float - current_value) / current_value * 100, 2)
                                else:
                                    return None
                            else:
                                return round((current_value - target_float) / target_float * 100, 2)
            else:
                # Single value target
                if indicator.target_value is not None:
                    target_float = float(indicator.target_value)
                    if target_float != 0:
                        if indicator.target_type == 'decrease':
                            if current_value != 0:
                                return round((target_float - current_value) / current_value * 100, 2)
                            else:
                                return None
                        else:
                            return round((current_value - target_float) / target_float * 100, 2)
            
            return None
            
        except Exception:
            return None
    
    def _classify_change_category(self, percent_change: Optional[float], target_type: str = 'increase') -> Optional[str]:
        """
        Classify change into categories.
        
        Args:
            percent_change: Percentage change
            target_type: Target type
            
        Returns:
            Change category or None
        """
        if percent_change is None:
            return None
        
        # Use the correct formulas - percent_change is already the correct performance change
        performance_change = percent_change
        
        # Categorize based on performance change - EXACTLY matches flowchart
        if performance_change <= -10:
            return "<=-10%"
        elif performance_change <= -5:
            return "-10%<C<=-5%"
        elif performance_change <= 5:
            return "-5%<C<=5%"  # Stagnation category
        elif performance_change > 5:
            return ">5%"
        
        return None
    
    def _classify_gap_category(self, target_gap: Optional[float]) -> Optional[str]:
        """
        Classify gap into categories.
        
        Args:
            target_gap: Target gap percentage
            
        Returns:
            Gap category or None
        """
        if target_gap is None:
            return None
        
        # Categorize based on the signed target_gap, matching Excel's behavior
        if target_gap <= 10:
            return "<=10%"
        elif 10 < target_gap <= 40:
            return "10%<PT<=40%"
        elif target_gap > 40:
            return ">40%"
        
        return None
    
    def _calculate_final_score(
        self,
        data_provided: str,
        is_first_year: str,
        target_achieved: str,
        change_category: Optional[str],
        gap_category: Optional[str],
        indicator: TrackedIndicator
    ) -> int:
        """
        Calculate final score based on the flowchart logic.
        
        Args:
            data_provided: Whether data is provided
            is_first_year: Whether it's the first year
            target_achieved: Whether target was achieved
            change_category: Change category
            gap_category: Gap category
            indicator: Indicator instance
            
        Returns:
            Final score
        """
        
        logger.debug(f"_calculate_final_score inputs:")
        logger.debug(f"  data_provided: {data_provided}")
        logger.debug(f"  is_first_year: {is_first_year}")
        logger.debug(f"  target_achieved: {target_achieved}")
        logger.debug(f"  change_category: {change_category}")
        logger.debug(f"  gap_category: {gap_category}")
        
        # Special case: Decrease indicator with current value = 0 (excellent performance)
        if (indicator.target_type == 'decrease' and 
            hasattr(indicator, 'current_value') and indicator.current_value == 0):
            return 2
        
        # Decision 1: Was data provided?
        if data_provided == "No":
            return -2  # Red circle in flowchart
        
        # Decision 2: Is it the first year of reporting?
        if is_first_year == "Yes":
            # First year logic: check if target was achieved
            return 1 if target_achieved == "Yes" else 0
        
        # Not first year - proceed with complex logic
        # Decision 3: Was the target achieved?
        if target_achieved == "Yes":
            # Target WAS achieved - check performance change
            if change_category == ">5%":
                return 2  # Green circle - Increase
            elif change_category == "-5%<C<=5%":
                return 2  # Green circle - Stagnation
            elif change_category == "-10%<C<=-5%":
                return 1  # Green circle - Small decrease
            elif change_category == "<=-10%":
                return 0  # Yellow circle - Large decrease
            else:
                # Target achieved but no change category
                return 2  # Target achieved = good performance
        
        else:
            # Target NOT achieved - check performance change
            if change_category == ">5%":
                logger.debug("  Score calculation: change_category='>5%' -> score=1")
                return 1
            elif change_category == "-5%<C<=5%":
                # Stagnation - check how close to target
                if gap_category == "<=10%":
                    logger.debug("  Score calculation: change_category='-5%<C<=5%', gap_category='<=10%' -> score=1")
                    return 1
                elif gap_category == "10%<PT<=40%":
                    logger.debug("  Score calculation: change_category='-5%<C<=5%', gap_category='10%<PT<=40%' -> score=0")
                    return 0
                elif gap_category == ">40%":
                    logger.debug("  Score calculation: change_category='-5%<C<=5%', gap_category='>40%' -> score=-1")
                    return -1
                else:
                    logger.debug("  Score calculation: change_category='-5%<C<=5%', gap_category=None -> score=0")
                    return 0
            elif change_category == "-10%<C<=-5%":
                logger.debug("  Score calculation: change_category='-10%<C<=-5%' -> score=-1")
                return -1
            elif change_category == "<=-10%":
                logger.debug("  Score calculation: change_category='<=-10%' -> score=-1")
                return -1
            else:
                logger.debug("  Score calculation: change_category=None -> score=0")
                return 0
    
    def calculate_batch_scores(self, indicator_scores: List[IndicatorScore]) -> None:
        """
        Calculate scores for a batch of indicator scores.
        
        Args:
            indicator_scores: List of indicator scores to calculate
        """
        for indicator_score in indicator_scores:
            try:
                indicator_score.calculate_holistic_score()
            except Exception as e:
                logger.error(f"Error calculating score for {indicator_score}: {e}")
                continue
    
    def get_scoring_summary(self, indicator_score: IndicatorScore) -> Dict[str, Any]:
        """
        Get a summary of the scoring context for an indicator.
        
        Args:
            indicator_score: Indicator score instance
            
        Returns:
            Scoring summary dictionary
        """
        if not indicator_score.scoring_context:
            return {}
        
        context = indicator_score.scoring_context
        
        return {
            'data_provided': context.data_provided,
            'current_meets_target': context.current_meets_target,
            'previous_meets_target': context.previous_meets_target,
            'change_category': context.change_category,
            'gap_category': context.gap_category,
            'percent_change': float(context.percent_change) if context.percent_change else None,
            'target_gap': float(context.target_gap) if context.target_gap else None,
            'final_score': indicator_score.score,
            'score_color': indicator_score.score_color,
            'score_label': indicator_score.score_label
        }
