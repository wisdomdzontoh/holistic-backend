from django.core.management.base import BaseCommand
from django.utils import timezone
from indicators.models import TrackedIndicator
from assessments.models import IndicatorScore, ScoringContext
from assessments.services.scoring_service import HolisticScoringService
from configurations.models import AssessmentPeriod, Objective
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Test the Holistic Assessment scoring system'

    def add_arguments(self, parser):
        parser.add_argument(
            '--indicator-id',
            type=int,
            help='Test scoring for a specific indicator ID'
        )
        parser.add_argument(
            '--create-test-data',
            action='store_true',
            help='Create test indicator scores for testing'
        )
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Enable verbose output'
        )

    def handle(self, *args, **options):
        self.stdout.write("Testing Holistic Assessment scoring system...")
        
        if options['verbose']:
            logging.getLogger().setLevel(logging.DEBUG)
        
        # Initialize scoring service
        scoring_service = HolisticScoringService()
        
        if options['create_test_data']:
            self.create_test_data()
        
        if options['indicator_id']:
            self.test_specific_indicator(options['indicator_id'], scoring_service)
        else:
            self.test_all_indicators(scoring_service)
    
    def create_test_data(self):
        """Create test indicator scores for testing"""
        self.stdout.write("Creating test data...")
        
        # Get or create test assessment period
        period, created = AssessmentPeriod.objects.get_or_create(
            name='Test Period 2024',
            defaults={
                'period_type': 'yearly',
                'start_date': '2024-01-01',
                'end_date': '2024-12-31',
                'is_active': True,
                'is_current': True
            }
        )
        
        # Get or create test objective
        objective, created = Objective.objects.get_or_create(
            name='Test Objective',
            defaults={
                'code': 'TEST_OBJ',
                'order': 1,
                'is_active': True
            }
        )
        
        # Get first few indicators
        indicators = TrackedIndicator.objects.filter(is_active=True)[:5]
        
        for i, indicator in enumerate(indicators):
            # Create test indicator score
            score, created = IndicatorScore.objects.get_or_create(
                indicator=indicator,
                objective=objective,
                org_unit_id='TEST_ORG_UNIT',
                org_unit_name='Test Organization Unit',
                assessment_period=period,
                defaults={
                    'current_value': 75.0 + (i * 5),  # Varying current values
                    'previous_value': 70.0 + (i * 3),  # Varying previous values
                    'target_value': 80.0,  # Fixed target
                    'score': 0,
                    'weight': 1.0
                }
            )
            
            if created:
                self.stdout.write(f"Created test score for {indicator.name}")
        
        self.stdout.write(self.style.SUCCESS("Test data created successfully"))
    
    def test_specific_indicator(self, indicator_id, scoring_service):
        """Test scoring for a specific indicator"""
        try:
            indicator = TrackedIndicator.objects.get(id=indicator_id)
            self.stdout.write(f"Testing indicator: {indicator.name}")
            
            # Get indicator score
            score = IndicatorScore.objects.filter(indicator=indicator).first()
            if not score:
                self.stdout.write(self.style.ERROR(f"No score found for indicator {indicator_id}"))
                return
            
            # Test scoring
            result = scoring_service.calculate_indicator_score(
                indicator=indicator,
                current_value=float(score.current_value) if score.current_value else None,
                previous_value=float(score.previous_value) if score.previous_value else None,
                data_provided=score.current_value is not None
            )
            
            self.display_scoring_result(result, indicator)
            
        except TrackedIndicator.DoesNotExist:
            self.stdout.write(self.style.ERROR(f"Indicator {indicator_id} not found"))
    
    def test_all_indicators(self, scoring_service):
        """Test scoring for all indicators with scores"""
        self.stdout.write("Testing all indicators with scores...")
        
        scores = IndicatorScore.objects.select_related('indicator').all()[:10]  # Limit to first 10
        
        for score in scores:
            self.stdout.write(f"\nTesting: {score.indicator.name}")
            
            result = scoring_service.calculate_indicator_score(
                indicator=score.indicator,
                current_value=float(score.current_value) if score.current_value else None,
                previous_value=float(score.previous_value) if score.previous_value else None,
                data_provided=score.current_value is not None
            )
            
            self.display_scoring_result(result, score.indicator)
    
    def display_scoring_result(self, result, indicator):
        """Display scoring result in a formatted way"""
        self.stdout.write(f"  Target: {indicator.target_value} {indicator.target_operator}")
        self.stdout.write(f"  Current meets target: {result['current_meets_target']}")
        self.stdout.write(f"  Previous meets target: {result['previous_meets_target']}")
        self.stdout.write(f"  Change category: {result['change_category']}")
        self.stdout.write(f"  Gap category: {result['gap_category']}")
        self.stdout.write(f"  Percent change: {result['percent_change']}%")
        self.stdout.write(f"  Target gap: {result['target_gap']}%")
        self.stdout.write(f"  Final score: {result['score']}")
        
        # Color code the score
        if result['score'] >= 1:
            self.stdout.write(self.style.SUCCESS(f"  Score: {result['score']} (Good)"))
        elif result['score'] == 0:
            self.stdout.write(self.style.WARNING(f"  Score: {result['score']} (Satisfactory)"))
        else:
            self.stdout.write(self.style.ERROR(f"  Score: {result['score']} (Needs Improvement)"))
