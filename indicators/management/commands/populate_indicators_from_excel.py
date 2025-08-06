from django.core.management.base import BaseCommand
from django.db import transaction
from indicators.models import TrackedIndicator
from configurations.models import Objective, IndicatorWeight, Milestone


class Command(BaseCommand):
    help = 'Populate indicators from Excel structure for holistic assessment'

    def handle(self, *args, **options):
        self.stdout.write('Starting to populate indicators from Excel structure...')
        
        with transaction.atomic():
            # First, create milestones
            milestones_data = [
                {
                    'name': 'MS 1.1',
                    'code': 'MS1.1',
                    'description': 'Milestone for Objective 1',
                    'order': 1,
                    'color': '#ffc107'
                },
                {
                    'name': 'MS 1.2',
                    'code': 'MS1.2',
                    'description': 'Milestone for Objective 2',
                    'order': 2,
                    'color': '#ffc107'
                },
                {
                    'name': 'MS 1.3',
                    'code': 'MS1.3',
                    'description': 'Milestone for Objective 3',
                    'order': 3,
                    'color': '#ffc107'
                },
                {
                    'name': 'MS 1.4',
                    'code': 'MS1.4',
                    'description': 'Milestone for Objective 4',
                    'order': 4,
                    'color': '#ffc107'
                },
                {
                    'name': 'MS 1.5',
                    'code': 'MS1.5',
                    'description': 'Milestone for Objective 5',
                    'order': 5,
                    'color': '#ffc107'
                }
            ]
            
            milestones = {}
            for ms_data in milestones_data:
                milestone, created = Milestone.objects.get_or_create(
                    code=ms_data['code'],
                    defaults={
                        'name': ms_data['name'],
                        'description': ms_data['description'],
                        'order': ms_data['order'],
                        'color': ms_data['color'],
                        'is_active': True
                    }
                )
                milestones[ms_data['code']] = milestone
                if created:
                    self.stdout.write(f'Created milestone: {milestone.name}')
                else:
                    self.stdout.write(f'Updated milestone: {milestone.name}')
            
            # Then, ensure objectives exist with milestones
            objectives_data = [
                {
                    'name': 'Objective 1: Universal access to better & efficiently managed quality healthcare services',
                    'code': 'OBJ1',
                    'description': 'Improve service delivery and patient care quality',
                    'color': '#fd7e14',
                    'order': 1,
                    'milestone_code': 'MS1.1',
                    'indicators': [
                        {
                            'name': 'Average revenue per OPD patient',
                            'dhis2_uid': 'INDICATOR_1_1',
                            'description': 'Average revenue generated per outpatient department patient',
                            'target_value': 15.0,
                            'target_type': 'decrease',
                            'weight': 1.0,
                            'indicator_number': '1.1',
                            'display_order': 1
                        },
                        {
                            'name': 'Family Planning Acceptor rate',
                            'dhis2_uid': 'INDICATOR_1_2',
                            'description': 'Rate of family planning acceptors',
                            'target_value': 25.0,
                            'target_type': 'increase',
                            'weight': 1.0,
                            'indicator_number': '1.2',
                            'display_order': 2
                        },
                        {
                            'name': 'Proportion of facility deaths that are medically certified',
                            'dhis2_uid': 'INDICATOR_1_3',
                            'description': 'Percentage of facility deaths with medical certification',
                            'target_value': 80.0,
                            'target_type': 'increase',
                            'weight': 1.0,
                            'indicator_number': '1.3',
                            'display_order': 3
                        },
                        {
                            'name': 'Proportion of deliveries attended by trained health workers',
                            'dhis2_uid': 'INDICATOR_1_4',
                            'description': 'Percentage of deliveries attended by skilled birth attendants',
                            'target_value': 90.0,
                            'target_type': 'increase',
                            'weight': 1.0,
                            'indicator_number': '1.4',
                            'display_order': 4
                        },
                        {
                            'name': 'Physician Assistant to population ratio',
                            'dhis2_uid': 'INDICATOR_1_5',
                            'description': 'Ratio of physician assistants to population',
                            'target_value': 1.0,
                            'target_type': 'increase',
                            'weight': 1.0,
                            'indicator_number': '1.5',
                            'display_order': 5
                        },
                        {
                            'name': 'Percentage of Children 6-59 months receiving Routine Vitamin A',
                            'dhis2_uid': 'INDICATOR_1_6',
                            'description': 'Coverage of vitamin A supplementation',
                            'target_value': 85.0,
                            'target_type': 'increase',
                            'weight': 1.0,
                            'indicator_number': '1.6',
                            'display_order': 6
                        },
                        {
                            'name': 'Penta 3 coverage',
                            'dhis2_uid': 'INDICATOR_1_7',
                            'description': 'Pentavalent vaccine third dose coverage',
                            'target_value': 90.0,
                            'target_type': 'increase',
                            'weight': 1.0,
                            'indicator_number': '1.7',
                            'display_order': 7
                        },
                        {
                            'name': 'Long Term couple year protection',
                            'dhis2_uid': 'INDICATOR_1_8',
                            'description': 'Long-term family planning method coverage',
                            'target_value': 30.0,
                            'target_type': 'increase',
                            'weight': 1.0,
                            'indicator_number': '1.8',
                            'display_order': 8
                        }
                    ]
                },
                {
                    'name': 'Objective 2: Reduce avoidable maternal, adolescent & child deaths and disabilities',
                    'code': 'OBJ2',
                    'description': 'Improve maternal and child health outcomes',
                    'color': '#dc3545',
                    'order': 2,
                    'milestone_code': 'MS1.2',
                    'indicators': [
                        {
                            'name': 'Proportion of facility deaths that are medically certified',
                            'dhis2_uid': 'INDICATOR_2_1',
                            'description': 'Percentage of facility deaths with medical certification',
                            'target_value': 80.0,
                            'target_type': 'increase',
                            'weight': 1.0,
                            'indicator_number': '2.1',
                            'display_order': 1
                        },
                        {
                            'name': 'Percentage of ANC Registrants within the First Trimester',
                            'dhis2_uid': 'INDICATOR_2_2',
                            'description': 'Early antenatal care registration rate',
                            'target_value': 70.0,
                            'target_type': 'increase',
                            'weight': 1.0,
                            'indicator_number': '2.2',
                            'display_order': 2
                        },
                        {
                            'name': 'Proportion of children U5 who were measured to assess stunting',
                            'dhis2_uid': 'INDICATOR_2_3',
                            'description': 'Coverage of child growth monitoring',
                            'target_value': 80.0,
                            'target_type': 'increase',
                            'weight': 1.0,
                            'indicator_number': '2.3',
                            'display_order': 3
                        },
                        {
                            'name': 'Proportion of children U5 who were measured to assess stunting',
                            'dhis2_uid': 'INDICATOR_2_4',
                            'description': 'Child stunting assessment coverage',
                            'target_value': 80.0,
                            'target_type': 'increase',
                            'weight': 1.0,
                            'indicator_number': '2.4',
                            'display_order': 4
                        },
                        {
                            'name': 'Prevalence of anaemia in pregnant women at 36 weeks of gestation',
                            'dhis2_uid': 'INDICATOR_2_5',
                            'description': 'Anaemia prevalence in pregnant women',
                            'target_value': 20.0,
                            'target_type': 'decrease',
                            'weight': 1.0,
                            'indicator_number': '2.5',
                            'display_order': 5
                        },
                        {
                            'name': 'Percentage of Children 6-59 months receiving Routine Vitamin A',
                            'dhis2_uid': 'INDICATOR_2_6',
                            'description': 'Vitamin A supplementation coverage',
                            'target_value': 85.0,
                            'target_type': 'increase',
                            'weight': 1.0,
                            'indicator_number': '2.6',
                            'display_order': 6
                        },
                        {
                            'name': 'Percentage of ANC Registrants within the First Trimester',
                            'dhis2_uid': 'INDICATOR_2_7',
                            'description': 'Early antenatal care registration',
                            'target_value': 70.0,
                            'target_type': 'increase',
                            'weight': 1.0,
                            'indicator_number': '2.7',
                            'display_order': 7
                        },
                        {
                            'name': 'Penta 3 coverage',
                            'dhis2_uid': 'INDICATOR_2_8',
                            'description': 'Pentavalent vaccine coverage',
                            'target_value': 90.0,
                            'target_type': 'increase',
                            'weight': 1.0,
                            'indicator_number': '2.8',
                            'display_order': 8
                        },
                        {
                            'name': 'Proportion of children under five years who are underweight',
                            'dhis2_uid': 'INDICATOR_2_9',
                            'description': 'Child underweight prevalence',
                            'target_value': 15.0,
                            'target_type': 'decrease',
                            'weight': 1.0,
                            'indicator_number': '2.9',
                            'display_order': 9
                        },
                        {
                            'name': 'Institutional all-cause mortality rate',
                            'dhis2_uid': 'INDICATOR_2_10',
                            'description': 'Overall institutional mortality rate',
                            'target_value': 5.0,
                            'target_type': 'decrease',
                            'weight': 1.0,
                            'indicator_number': '2.10',
                            'display_order': 10
                        },
                        {
                            'name': 'Institutional Maternal Mortality Ratio per 100,000',
                            'dhis2_uid': 'INDICATOR_2_11',
                            'description': 'Maternal mortality ratio in facilities',
                            'target_value': 100.0,
                            'target_type': 'decrease',
                            'weight': 1.0,
                            'indicator_number': '2.11',
                            'display_order': 11
                        },
                        {
                            'name': 'Institutional Neonatal Mortality Rate per 1000',
                            'dhis2_uid': 'INDICATOR_2_12',
                            'description': 'Neonatal mortality rate in facilities',
                            'target_value': 15.0,
                            'target_type': 'decrease',
                            'weight': 1.0,
                            'indicator_number': '2.12',
                            'display_order': 12
                        },
                        {
                            'name': 'Institutional Malaria Under 5 Case Fatality Rate',
                            'dhis2_uid': 'INDICATOR_2_13',
                            'description': 'Malaria case fatality rate in children under 5',
                            'target_value': 2.0,
                            'target_type': 'decrease',
                            'weight': 1.0,
                            'indicator_number': '2.13',
                            'display_order': 13
                        },
                        {
                            'name': 'Institutional Malaria Under 5 Case Fatality Rate',
                            'dhis2_uid': 'INDICATOR_2_14',
                            'description': 'Malaria case fatality rate in children under 5',
                            'target_value': 2.0,
                            'target_type': 'decrease',
                            'weight': 1.0,
                            'indicator_number': '2.14',
                            'display_order': 14
                        },
                        {
                            'name': 'Measles-Rubella 2 coverage',
                            'dhis2_uid': 'INDICATOR_2_15',
                            'description': 'Measles-Rubella second dose coverage',
                            'target_value': 85.0,
                            'target_type': 'increase',
                            'weight': 1.0,
                            'indicator_number': '2.15',
                            'display_order': 15
                        }
                    ]
                },
                {
                    'name': 'Objective 3: Increase access to responsive clinical and public health emergency services',
                    'code': 'OBJ3',
                    'description': 'Enhance emergency and clinical services',
                    'color': '#28a745',
                    'order': 3,
                    'milestone_code': 'MS1.3',
                    'indicators': [
                        {
                            'name': 'Emergency response time',
                            'dhis2_uid': 'INDICATOR_3_1',
                            'description': 'Average emergency response time',
                            'target_value': 15.0,
                            'target_type': 'decrease',
                            'weight': 1.0,
                            'indicator_number': '3.1',
                            'display_order': 1
                        },
                        {
                            'name': 'Clinical service availability',
                            'dhis2_uid': 'INDICATOR_3_2',
                            'description': 'Availability of clinical services',
                            'target_value': 95.0,
                            'target_type': 'increase',
                            'weight': 1.0,
                            'indicator_number': '3.2',
                            'display_order': 2
                        },
                        {
                            'name': 'Public health emergency preparedness',
                            'dhis2_uid': 'INDICATOR_3_3',
                            'description': 'Emergency preparedness score',
                            'target_value': 80.0,
                            'target_type': 'increase',
                            'weight': 1.0,
                            'indicator_number': '3.3',
                            'display_order': 3
                        },
                        {
                            'name': 'Proportion of suspected malaria cases that were tested for malaria before treatment',
                            'dhis2_uid': 'INDICATOR_3_4',
                            'description': 'Malaria testing before treatment rate',
                            'target_value': 90.0,
                            'target_type': 'increase',
                            'weight': 1.0,
                            'indicator_number': '3.4',
                            'display_order': 4
                        }
                    ]
                },
                {
                    'name': 'Objective 4: Governance and Leadership',
                    'code': 'OBJ4',
                    'description': 'Strengthen healthcare governance and leadership',
                    'color': '#6f42c1',
                    'order': 4,
                    'milestone_code': 'MS1.4',
                    'indicators': [
                        {
                            'name': 'Governance effectiveness score',
                            'dhis2_uid': 'INDICATOR_4_1',
                            'description': 'Overall governance effectiveness',
                            'target_value': 75.0,
                            'target_type': 'increase',
                            'weight': 1.0,
                            'indicator_number': '4.1',
                            'display_order': 1
                        },
                        {
                            'name': 'Completeness of reporting by health facilities',
                            'dhis2_uid': 'INDICATOR_4_2',
                            'description': 'Health facility reporting completeness',
                            'target_value': 95.0,
                            'target_type': 'increase',
                            'weight': 1.0,
                            'indicator_number': '4.2',
                            'display_order': 2
                        }
                    ]
                },
                {
                    'name': 'Objective 5: Innovation and Research',
                    'code': 'OBJ5',
                    'description': 'Promote healthcare innovation and research',
                    'color': '#17a2b8',
                    'order': 5,
                    'milestone_code': 'MS1.5',
                    'indicators': [
                        {
                            'name': 'Innovation adoption rate',
                            'dhis2_uid': 'INDICATOR_5_1',
                            'description': 'Rate of adoption of new healthcare innovations',
                            'target_value': 30.0,
                            'target_type': 'increase',
                            'weight': 1.0,
                            'indicator_number': '5.1',
                            'display_order': 1
                        },
                        {
                            'name': 'Research projects initiated',
                            'dhis2_uid': 'INDICATOR_5_2',
                            'description': 'Number of research projects initiated',
                            'target_value': 10.0,
                            'target_type': 'increase',
                            'weight': 1.0,
                            'indicator_number': '5.2',
                            'display_order': 2
                        },
                        {
                            'name': 'Digital Health Implementation Rate',
                            'dhis2_uid': 'INDICATOR_5_3',
                            'description': 'Rate of digital health solution implementation',
                            'target_value': 60.0,
                            'target_type': 'increase',
                            'weight': 1.0,
                            'indicator_number': '5.3',
                            'display_order': 3
                        }
                    ]
                }
            ]
            
            for obj_data in objectives_data:
                objective, created = Objective.objects.get_or_create(
                    code=obj_data['code'],
                    defaults={
                        'name': obj_data['name'],
                        'description': obj_data['description'],
                        'color': obj_data['color'],
                        'order': obj_data['order'],
                        'milestone': milestones.get(obj_data['milestone_code']),
                        'is_active': True
                    }
                )
                
                if created:
                    self.stdout.write(f'Created objective: {objective.name}')
                else:
                    # Update milestone if it changed
                    if objective.milestone != milestones.get(obj_data['milestone_code']):
                        objective.milestone = milestones.get(obj_data['milestone_code'])
                        objective.save()
                        self.stdout.write(f'Updated objective milestone: {objective.name}')
                
                # Create indicators for this objective
                for ind_data in obj_data['indicators']:
                    indicator, created = TrackedIndicator.objects.get_or_create(
                        dhis2_uid=ind_data['dhis2_uid'],
                        defaults={
                            'name': ind_data['name'],
                            'description': ind_data['description'],
                            'target_value': ind_data['target_value'],
                            'target_type': ind_data['target_type'],
                            'indicator_number': ind_data['indicator_number'],
                            'display_order': ind_data['display_order'],
                            'is_active': True
                        }
                    )
                    
                    if created:
                        self.stdout.write(f'  Created indicator: {indicator.indicator_number} - {indicator.name}')
                    else:
                        # Update indicator number and display order if they changed
                        if (indicator.indicator_number != ind_data['indicator_number'] or 
                            indicator.display_order != ind_data['display_order']):
                            indicator.indicator_number = ind_data['indicator_number']
                            indicator.display_order = ind_data['display_order']
                            indicator.save()
                            self.stdout.write(f'  Updated indicator: {indicator.indicator_number} - {indicator.name}')
                    
                    # Create indicator weight mapping
                    weight, created = IndicatorWeight.objects.get_or_create(
                        objective=objective,
                        indicator=indicator,
                        defaults={'weight': ind_data['weight']}
                    )
                    
                    if created:
                        self.stdout.write(f'    Created weight mapping: {weight.weight}')
                    else:
                        if weight.weight != ind_data['weight']:
                            weight.weight = ind_data['weight']
                            weight.save()
                            self.stdout.write(f'    Updated weight mapping: {weight.weight}')
            
            # Update all existing indicators with proper numbering based on their DHIS2 UIDs
            self.stdout.write('Updating existing indicators with proper numbering...')
            all_indicators = TrackedIndicator.objects.all()
            
            for indicator in all_indicators:
                # Extract objective and indicator number from DHIS2 UID
                if indicator.dhis2_uid and indicator.dhis2_uid.startswith('INDICATOR_'):
                    try:
                        # Parse UID like "INDICATOR_1_4" to get objective 1, indicator 4
                        parts = indicator.dhis2_uid.split('_')
                        if len(parts) >= 3:
                            objective_num = parts[1]
                            indicator_num = parts[2]
                            indicator_number = f"{objective_num}.{indicator_num}"
                            
                            if indicator.indicator_number != indicator_number:
                                indicator.indicator_number = indicator_number
                                indicator.display_order = int(indicator_num)
                                indicator.save()
                                self.stdout.write(f'  Updated existing indicator: {indicator_number} - {indicator.name}')
                    except (ValueError, IndexError):
                        # Skip if UID doesn't match expected format
                        continue
        
        self.stdout.write(self.style.SUCCESS('Successfully populated indicators from Excel structure!')) 