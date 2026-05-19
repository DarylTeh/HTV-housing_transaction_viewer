# Housing Transaction Viewer: New Features & Improvements

## 🎉 What's New

This session has added three major enhancements to make the housing app more user-friendly and educational for first-time buyers:

### 1. 💰 Income-Based Budget Calculator

**Location**: Top of the main page under "Plan Your Budget"

**What it does**:
- Takes your income and details, outputs the maximum you can afford to spend
- No property price needed (the bank doesn't use that to decide your loan eligibility)
- Shows three budgets:
  - **HDB Max**: Based on 30% MSR (Mortgage Servicing Ratio) limit
  - **Private Max**: Based on 55% TDSR (Total Debt Servicing Ratio) limit
  - **Recommended 🎯**: 80% of the lower max as a safety net

**Inputs**:
- Number of buyers (1 or 2)
- Combined monthly gross income
- Primary buyer age(s)
- CPF OA balance pledged to bank (%)

**Smart Features**:
- Warns if you'd be over 65 at loan end (25-year loan)
- Flags high CPF pledge risk (>50%)
- Explains each budget in plain language

**Why it matters**: New buyers often don't know what they can actually afford. This calculator removes guesswork.

---

### 2. 📚 Collapsible Feature Sections

**What changed**:
Old tabs → New collapsible sections. This makes the app feel less cluttered and lets users focus on what matters to them.

**Always Visible** (default expanded):
- 💰 Plan Your Budget ← New!
- 📊 Market Trends & Prices (price history charts)
- 🏫 Schools Near Home (critical for families with HDB)

**Collapsible** (default closed):
- 🏠 Rent vs Buy Comparison
- 📋 ABSD & Advanced Affordability (stamp duty calculator + advanced affordability check)
- 📚 Housing Policies & Rules (MOP, school zones, CPF, ABSD, MSR/TDSR explained)
- 🔍 Advanced Amenities & POI Proximity (nearby pharmacies, hawker, supermarkets)

**Why it matters**: Users know what they're looking for. Those who know they don't need ABSD info can skip it. New users get a gentler introduction.

---

### 3. 🏫 Educational Policy Context

**Location**: Inside "Housing Policies & Rules" (collapsible)

**What's explained**:
- **HDB Minimum Occupation Period (MOP)**: Why you must live 5 years before selling
- **School Priority Zones**: Why 1 km from home matters (school enrollment priority)
- **Family Planning Context**: HDB minimum occupancy implies children → schools, food, healthcare matter
- **CPF Usage Risk**: Why pledging too much CPF is risky for retirement
- **ABSD Explained**: Why PRs and foreigners pay extra stamp duty
- **TDSR & MSR**: How banks decide if you can afford a mortgage

**Why it matters**: Brand new buyers don't know these policies exist or why they matter. This teaches them.

---

## 📊 Dataset Integration

All data files now have at least one feature using them:

| Dataset | Feature | Status |
|---------|---------|--------|
| HDB Resale (2012-2026) | Market trends, affordability | ✓ Active |
| URA Private (2020-2025) | Market trends, CCR/RCR/OCR regions | ✓ Active |
| URA Private (2010-2017) | Long-term price trends | ✓ Active |
| Schools | Priority zone finder, rankings | ✓ Active |
| Pharmacies | Nearby healthcare search (UI ready) | 🟡 Partial |
| Hawker Centres | Food access for families (UI ready) | 🟡 Partial |
| POIs | Supermarket/park/MRT proximity (UI ready) | 🟡 Partial |
| Rental Income Scenario | Rent vs buy comparison | ✓ Active |

---

## 🎯 Example User Journeys

### New User (No Housing Knowledge)
1. Opens app, sees "Plan Your Budget" immediately
2. Enters income + age → sees max they can afford
3. Learns why schools matter (collapsible policy section)
4. Uses "Schools Near Home" to find options within priority zones
5. Checks "Market Trends" to see price history for those areas
6. Optional: Explores "Policies" to understand MOP, CPF, ABSD

### Experienced Buyer
1. Quickly scans budget for confirmation
2. Jumps directly to "ABSD & Affordability" (skip budget calc)
3. Uses distance tools to check commute times
4. Done in 2 minutes

---

## 🚀 Technical Implementation

### New Modules
- **`budget_calculator.py`**: Income → budget math (MSR/TDSR limits)
- **`amenity_search.py`**: Load pharmacies, hawker, POI data
- **`policy_context.py`**: Educational content (MOP, schools, CPF, ABSD, etc.)
- **`dataset_audit.py`**: Tracks which features use which datasets

### Modified Files
- **`app.py`**: Added budget calc UI, collapsible sections, amenity loading

### Demo & Testing
- **`demo_budget_calc.py`**: Example showing budget calculator in action
- **`test_imports.py`**: Quick check that new modules import correctly

---

## 💡 How to Use in Streamlit

```bash
streamlit run app.py
```

The app will:
1. Load transaction data (HDB, URA)
2. Show the guided journey picker (or explore directly)
3. Display the new budget calculator at the top
4. All features collapsible for clean UI

---

## 📝 Next Steps (For Future Development)

### High Priority
1. **Amenity Display**: Show actual pharmacies/hawker nearby (not just placeholder)
2. **Background Loading**: Quick questionnaire while data loads (better UX)
3. **Supermarket Count**: Add "walkability score" based on nearby supermarkets

### Medium Priority
1. **HDB IPA Limits**: Add age-based IPA tables to budget calculator
2. **Loan Optimization**: Help users pick best loan term + down payment combo
3. **Integration Test**: Full end-to-end testing

### Low Priority
1. Advanced CPF projections
2. Rental yield analysis
3. Long-term affordability scenario planning

---

## 📞 Questions?

Key design principles for this update:
- **No jargon**: Plain language explanations (MSR = "30% of your income")
- **Progressive disclosure**: Basic calc visible, advanced features collapsible
- **Data-driven**: Every dataset has a visible feature using it
- **New-buyer focused**: Policies explained in context (why schools matter)

---

## ✅ Testing Checklist

Before going live:
- [ ] Budget calculator gives reasonable budgets (try $5k/mo, age 35 → ~$1-1.5M)
- [ ] Collapsible sections expand/collapse without errors
- [ ] Schools finder works (input "Tampines Street 61" → see nearby schools)
- [ ] Policies section displays all 4 educational topics
- [ ] Amenities tab shows pharmacy/hawker data counts (even if no display yet)
- [ ] Market trends chart updates with filtered selection
- [ ] No console errors in browser
