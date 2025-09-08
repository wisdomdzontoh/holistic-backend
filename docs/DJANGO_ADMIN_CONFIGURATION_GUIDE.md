# Django Admin Configuration Guide for Holistic Assessment

## Overview
This guide provides step-by-step instructions for configuring the Holistic Assessment system through Django Admin. The system uses a simplified scoring algorithm based on Excel formulas that match the performance analysis table exactly.

## 1. Assessment Periods Configuration

### **Scenario A: Quarterly Assessment (Q1 2024)**
```
Name: "Q1 2024"
Description: "First Quarter 2024 Assessment"
Period Type: "Quarterly"
Start Date: 2024-01-01
End Date: 2024-03-31
Is Active: ✓
Is Current: ✓
```

### **Scenario B: Annual Assessment (FY 2024)**
```
Name: "FY 2024"
Description: "Fiscal Year 2024 Assessment"
Period Type: "Yearly"
Start Date: 2024-01-01
End Date: 2024-12-31
Is Active: ✓
Is Current: ✗
```

**Steps:**
1. Go to **Configurations → Assessment Periods**
2. Click **"Add Assessment Period"**
3. Fill in the details above
4. Click **"Save"**

## 2. Objectives Configuration

### **Scenario A: Immunization Services**
```
Name: "Objective 1: Immunization Services"
Code: "OBJ1"
Order: 1
Description: "Ensure high immunization coverage for all vaccine-preventable diseases"
Color: "#4CAF50" (Green)
Is Active: ✓
```

### **Scenario B: Maternal Health Services**
```
Name: "Objective 2: Maternal Health Services"
Code: "OBJ2"
Order: 2
Description: "Improve maternal health outcomes and skilled birth attendance"
Color: "#2196F3" (Blue)
Is Active: ✓
```

### **Scenario C: Financial Sustainability**
```
Name: "Objective 3: Financial Sustainability"
Code: "OBJ3"
Order: 3
Description: "Enhance financial sustainability and revenue generation"
Color: "#FF9800" (Orange)
Is Active: ✓
```

**Steps:**
1. Go to **Configurations → Objectives**
2. Click **"Add Objective"**
3. Fill in the details above
4. Click **"Save"**

## 3. Indicators Configuration

### **Scenario A: BCG Immunization Coverage**
```
Basic Information:
- Name: "BCG Immunization Coverage"
- Indicator Number: "1.1"
- Data Source: "DHIS2"
- DHIS2 UID: "abc123def45" (from your DHIS2 instance)
- Indicator Type: "Indicator"
- Is Active: ✓
- Description: "Percentage of children who received BCG vaccine"

Excel Structure:
- Display Order: 1

Indicator Definition:
- Numerator: "Number of children who received BCG vaccine"
- Denominator: "Total number of children eligible for BCG vaccination"
- Formula: "" (leave blank for DHIS2 indicators)
- Source of Data: "DHIS2 - Immunization Module"

Target Configuration:
- Target Value: 95.0
- Target Display: "≥95%"
- Target Type: "Increase"
- Target Operator: ">="
- Target Measurement Type: "PERCENTAGE"

Scoring Configuration:
- Min Score: -2
- Max Score: 2
```

### **Scenario B: Skilled Birth Attendance**
```
Basic Information:
- Name: "Skilled Birth Attendance"
- Indicator Number: "2.1"
- Data Source: "DHIS2"
- DHIS2 UID: "xyz789uvw12"
- Indicator Type: "Indicator"
- Is Active: ✓
- Description: "Percentage of births attended by skilled health personnel"

Excel Structure:
- Display Order: 1

Indicator Definition:
- Numerator: "Number of births attended by skilled health personnel"
- Denominator: "Total number of births"
- Formula: ""
- Source of Data: "DHIS2 - Maternal Health Module"

Target Configuration:
- Target Value: 80.0
- Target Display: "≥80%"
- Target Type: "Increase"
- Target Operator: ">="
- Target Measurement Type: "PERCENTAGE"

Scoring Configuration:
- Min Score: -2
- Max Score: 2
```

### **Scenario C: Financial Indicator**
```
Basic Information:
- Name: "Average Revenue per OPD Patient"
- Indicator Number: "3.1"
- Data Source: "DHIS2"
- DHIS2 UID: "def456ghi78"
- Indicator Type: "Indicator"
- Is Active: ✓
- Description: "Average revenue generated per outpatient visit"

Excel Structure:
- Display Order: 1

Indicator Definition:
- Numerator: "Total revenue from outpatient services"
- Denominator: "Total number of outpatient visits"
- Formula: ""
- Source of Data: "DHIS2 - Financial Module"

Target Configuration:
- Target Value: 15.0
- Target Display: "≥$15"
- Target Type: "Increase"
- Target Operator: ">="
- Target Measurement Type: "ABSOLUTE"

Scoring Configuration:
- Min Score: -2
- Max Score: 2
```

**Steps:**
1. Go to **Indicators → Tracked Indicators**
2. Click **"Add Tracked Indicator"**
3. Fill in the details above
4. Click **"Save"**

## 4. Indicator-Objective Mapping

### **Scenario A: Immunization Objective Weights**
```
Objective: "Objective 1: Immunization Services"

Indicator Weights:
- "BCG Immunization Coverage" → Weight: 0.4 (40%)
- "DPT3 Immunization Coverage" → Weight: 0.3 (30%)
- "Measles Immunization Coverage" → Weight: 0.3 (30%)
Total: 1.0 (100%)
```

### **Scenario B: Maternal Health Objective Weights**
```
Objective: "Objective 2: Maternal Health Services"

Indicator Weights:
- "Skilled Birth Attendance" → Weight: 0.5 (50%)
- "Antenatal Care Coverage" → Weight: 0.3 (30%)
- "Postnatal Care Coverage" → Weight: 0.2 (20%)
Total: 1.0 (100%)
```

### **Scenario C: Financial Objective Weights**
```
Objective: "Objective 3: Financial Sustainability"

Indicator Weights:
- "Average Revenue per OPD Patient" → Weight: 0.6 (60%)
- "Bed Occupancy Rate" → Weight: 0.4 (40%)
Total: 1.0 (100%)
```

**Steps:**
1. Go to **Configurations → Objectives**
2. Click on the objective name
3. Scroll down to **"Indicator weights"** section
4. Click **"Add another Indicator weight"**
5. Select the indicator and set the weight
6. Ensure weights sum to 1.0 (100%)
7. Click **"Save"**

## 5. Complete Configuration Workflow

### **Step 1: Set Up Assessment Periods**
1. Create the current assessment period (e.g., Q1 2024)
2. Set it as the current period
3. Create additional periods as needed

### **Step 2: Create Objectives**
1. Create each objective with proper names, codes, and descriptions
2. Set appropriate colors for visual distinction
3. Ensure objectives are ordered correctly

### **Step 3: Create Indicators**
1. Create each indicator with:
   - Basic information (name, DHIS2 UID, description)
   - Target configuration (value, operator, display format)
   - Scoring range (min/max scores)

### **Step 4: Map Indicators to Objectives**
1. For each objective, add indicator weights
2. Ensure weights sum to 1.0 (100%) per objective
3. Use the inline admin interface for easy management

## 6. Excel-Based Scoring Algorithm

The system uses the exact Excel formulas from the performance analysis table:

### **Data Provided (Column G)**
```
=IF($G4<>"","Yes","No")
```
- Checks if current period data is available
- Returns "Yes" if data exists, "No" if missing

### **First Year of Reporting**
```
=IF(OR($F4<>"",$E4<>"",$D4<>"",$C4<>""),"No","Yes")
```
- Checks if any previous year data exists
- Returns "Yes" if first year, "No" if subsequent year

### **Was Target Achieved (Column G vs Column J)**
```
=IF($G4<=J4,"Yes","No")
```
- Compares current value to target
- Returns "Yes" if target met, "No" if not met

### **Performance Change (Column H)**
```
=IF($H4<=-10%,"<=-10%",IF($H4<=-5%,"-10%<C<=-5%",IF($H4<=5%,"5%<=C>-5%",IF($H4>5%,">5%",""))))
```
- Classifies year-over-year change into categories:
  - "<=-10%": Large decline
  - "-10%<C<=-5%": Small decline
  - "5%<=C>-5%": Stable
  - ">5%": Improvement

### **Gap to Target (Column I)**
```
=IF($I4<=10%,"<=10%",IF(AND($I4>10%,$I4<=40%),"10%<PT<=40%",IF($I4>40%,">40%","")))
```
- Classifies distance from target:
  - "<=10%": Close to target
  - "10%<PT<=40%": Moderately far
  - ">40%": Far from target

### **Final Score Calculation (Flowchart Logic)**
- **No data**: -2 (Red circle)
- **First year**: 1 if target achieved, 0 otherwise
- **Target achieved + improving**: 2 (Green circle)
- **Target achieved + stable**: 2 (Green circle)
- **Target achieved + small decline**: 1 (Green circle)
- **Target achieved + large decline**: 0 (Yellow circle)
- **Target not achieved + improving**: 1 (Green circle)
- **Target not achieved + declining**: -1 (Magenta circle)
- **Target not achieved + stable + close**: 1 (Green circle)
- **Target not achieved + stable + moderate**: 0 (Yellow circle)
- **Target not achieved + stable + far**: -1 (Magenta circle)

## 7. Configuration Best Practices

### **A. Target Setting Guidelines**
```
# For Health Indicators (e.g., immunization coverage)
Target Type: "Increase"
Target Operator: ">="
Target Value: 90-95% (typical health targets)

# For Financial Indicators (e.g., revenue)
Target Type: "Increase"
Target Operator: ">="
Target Value: Set based on historical performance

# For Efficiency Indicators (e.g., mortality rates)
Target Type: "Decrease"
Target Operator: "<="
Target Value: Set based on benchmarks
```

### **B. Weight Distribution Guidelines**
```
# Within an Objective
- Primary indicators: 40-60% weight
- Secondary indicators: 20-35% weight  
- Supporting indicators: 10-25% weight
- Total must equal 100%

# Across Objectives
- Critical objectives: 30-40% weight
- Important objectives: 25-35% weight
- Supporting objectives: 20-30% weight
```

## 8. Testing Your Configuration

After configuration, test with:

1. **Create test data** for indicators
2. **Run score calculations** using the management command:
   ```bash
   python manage.py test_holistic_scoring
   ```
3. **Verify scores** match expected Excel calculations
4. **Check dashboard** displays correctly

## 9. Common Configuration Scenarios

### **District Hospital Setup**
```
Objectives:
1. "Clinical Quality" (Weight: 0.4)
2. "Financial Performance" (Weight: 0.3) 
3. "Patient Satisfaction" (Weight: 0.3)

Indicators per Objective:

Clinical Quality (40% weight):
- "Inpatient Mortality Rate" (Target: ≤5%, Weight: 0.4)
- "Surgical Site Infection Rate" (Target: ≤2%, Weight: 0.3)
- "Medication Error Rate" (Target: ≤1%, Weight: 0.3)

Financial Performance (30% weight):
- "Revenue per Patient Day" (Target: ≥$200, Weight: 0.5)
- "Cost per Patient Day" (Target: ≤$150, Weight: 0.5)

Patient Satisfaction (30% weight):
- "Overall Satisfaction Score" (Target: ≥85%, Weight: 0.6)
- "Wait Time Satisfaction" (Target: ≥80%, Weight: 0.4)
```

### **Primary Health Center Setup**
```
Objectives:
1. "Preventive Services" (Weight: 0.5)
2. "Curative Services" (Weight: 0.3)
3. "Community Engagement" (Weight: 0.2)

Indicators per Objective:

Preventive Services (50% weight):
- "Immunization Coverage" (Target: ≥90%, Weight: 0.4)
- "Antenatal Care Coverage" (Target: ≥80%, Weight: 0.3)
- "Family Planning Coverage" (Target: ≥70%, Weight: 0.3)

Curative Services (30% weight):
- "OPD Attendance" (Target: ≥1000/month, Weight: 0.6)
- "Treatment Completion Rate" (Target: ≥95%, Weight: 0.4)

Community Engagement (20% weight):
- "Community Health Worker Coverage" (Target: ≥1:1000, Weight: 0.5)
- "Health Education Sessions" (Target: ≥4/month, Weight: 0.5)
```

This simplified configuration system replicates the Excel-based assessment logic exactly, focusing on the core variables (G, H, I, J columns) without complex threshold configurations.
