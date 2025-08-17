# Formula Summary for Holistic Assessment

## **📊 Change Calculation Formulas**

### **1. Increase Indicators**
```
Change = ((Current Value - Previous Value) / |Previous Value|) × 100
```
**Example**: Current=98.89, Previous=97.83, Target=90%
- Change = ((98.89 - 97.83) / |97.83|) × 100 = (1.06 / 97.83) × 100 = +1.08%

### **2. Decrease Indicators**
```
Change = ((Previous Value - Current Value) / |Current Value|) × 100
```
**Example**: Current=35.5, Previous=40.0, Target=35.5%
- Change = ((40.0 - 35.5) / |35.5|) × 100 = (4.5 / 35.5) × 100 = +12.68%

### **3. Range Indicators**
```
Change = ((Current Value - Previous Value) / |Previous Value|) × 100
```
**Note**: Range indicators always use the standard formula regardless of target_type

---

## **🎯 P-T Gap Analysis Formulas**

### **1. Increase Indicators**
```
P-T Gap = ((Current Value - Target Value) / Target Value) × 100
```
**Example**: Current=98.89, Target=90%
- P-T Gap = ((98.89 - 90) / 90) × 100 = (8.89 / 90) × 100 = +9.88%

### **2. Decrease Indicators**
```
P-T Gap = ((Target Value - Current Value) / Current Value) × 100
```
**Example**: Current=35.5, Target=35.5%
- P-T Gap = ((35.5 - 35.5) / 35.5) × 100 = (0 / 35.5) × 100 = 0%

### **3. Range Indicators**
```
P-T Gap = ((Target Upper Limit - Current Value) / Current Value) × 100
```
**Example**: Current=85, Target Range=80-90%
- P-T Gap = ((90 - 85) / 85) × 100 = (5 / 85) × 100 = +5.88%

---

## **🏆 Scoring Logic (Based on Flowchart)**

### **Target Achieved = "Yes"**
- **Change > 5%**: Score = 2 (Green)
- **Change -5% to +5%**: Score = 2 (Green) - Stagnation
- **Change -10% to -5%**: Score = 1 (Light Green) - Small decrease
- **Change ≤ -10%**: Score = 0 (Yellow) - Large decrease

### **Target Achieved = "No"**
- **Change > 5%**: Score = 1 (Light Green)
- **Change -5% to +5%**: 
  - Gap ≤ 10%: Score = 1 (Light Green)
  - Gap 10-40%: Score = 0 (Yellow)
  - Gap > 40%: Score = -1 (Light Red)
- **Change -10% to -5%**: Score = -1 (Light Red)
- **Change ≤ -10%**: Score = -1 (Light Red)

---

## **🔍 Current Issues Identified**

### **Indicator 3.17: PMTCT testing coverage rate**
- **Expected P-T Gap**: ((98.87 - 86.79) / 86.79) × 100 = 13.92%
- **Displayed P-T Gap**: 16.3% ❌
- **Expected Score**: 2 (Target achieved + stagnation)
- **Displayed Score**: 1 ❌

### **Indicator 1.13: Proportion of newborns receiving PNC**
- **Expected Score**: 2 (Target achieved + positive change)
- **Displayed Score**: 1 ❌

### **Indicator 1.16: Percentage of babies breastfeeding**
- **Expected Change**: ((99.71 - 98.37) / 98.37) × 100 = 1.36%
- **Displayed Change**: 1.66% ❌
- **Expected P-T Gap**: ((99.71 - 100) / 100) × 100 = -0.29%
- **Displayed P-T Gap**: 5.3% ❌
- **Expected Score**: 2 (Target achieved + positive change)
- **Displayed Score**: 1 ❌

---

## **🚨 Root Cause Analysis**

The scoring inconsistencies suggest that:
1. **Frontend caching** may still be using old calculations
2. **Backend scoring logic** may have edge cases not handled properly
3. **Target achievement logic** may be incorrect for some indicators
4. **Change categorization** may not be working as expected

**Recommendation**: Clear all caches and verify the backend scoring logic is being used consistently.
