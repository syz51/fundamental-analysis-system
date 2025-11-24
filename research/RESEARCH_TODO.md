# Research TODO: EdgarTools Screening Implementation

**Last Updated**: 2025-11-24
**Status**: In Progress

---

## Completed Research ✅

### 1. EdgarTools Field Normalization (HIGH PRIORITY)

**Status**: ✅ COMPLETE (2025-11-24)

**Findings**:

- Field mapper NOT needed - EdgarTools provides getter methods
- 100% success rate across 10 companies
- Saves 200+ lines of code

**Details**: See `research/FINDINGS_EdgarTools_Field_Normalization.md`

---

### 2. EdgarTools Built-in Ratio/Trend Methods (HIGH PRIORITY)

**Status**: ✅ COMPLETE (2025-11-24)

**Findings**:

- Built-in methods (calculate_ratios, analyze_trends) UNRELIABLE (0-40% coverage)
- Must build custom MetricsCalculator (~350 lines)
- Use hybrid: getter methods + DataFrame fallback

**Details**: See `research/FINDINGS_EdgarTools_Builtin_Metrics.md`

---

### 3. Time Series Data Extraction for CAGR

**Status**: ✅ COMPLETE (2025-11-24)

**Findings**:

- 100% success rate using Statement.to_dataframe()
- Only 3 years in single 10-K (not 10 years!)
- Revenue detection: fuzzy match + filter NaN headers
- Use 3Y CAGR for screening, 10Y for deep analysis

**Details**: See `research/FINDINGS_EdgarTools_Time_Series.md`

---

## Medium Priority Research (Nice to Have)

### 4. EdgarTools IFRS/20-F Support

**Priority**: 🟡 MEDIUM
**Impact**: ~10% of S&P 500 (foreign filers)
**Blocking**: No (document as MVP limitation)

**Test Companies** (foreign filers):

- ARM (UK, IFRS)
- SAP (Germany, IFRS)
- LIN (Ireland, IFRS)
- NVS (Switzerland, IFRS)
- SHOP (Canada, IFRS)

**Questions**:

1. Does EdgarTools handle 20-F filings?
2. Are IFRS tags mapped to US-GAAP equivalents?
3. Do getter methods work on foreign filers?
4. Success rate vs. US companies?

**Deliverables**:

- Success rate report (% working)
- Failure analysis (why failed?)
- Fallback strategy if unsupported

---

### 5. Special Company Types (REITs, Banks)

**Priority**: 🟡 MEDIUM
**Impact**: ~10% of S&P 500 (incorrect metrics)
**Blocking**: No (document as MVP limitation)

**Test Companies**:

- **REITs**: AMT, PLD, EQIX, DLR, PSA
- **Banks**: JPM, BAC, WFC, C, GS
- **SPACs**: (find 2-3 if any in S&P 500)

**Questions**:

**REIT-Specific**:

1. Does EdgarTools provide FFO (Funds From Operations)?
2. Do getter methods work? (`get_net_income()` on REITs)
3. Which metrics are valid for REITs?
4. How to detect REITs programmatically?

**Bank-Specific**:

1. Does balance sheet structure differ significantly?
2. Do standard ratios work? (Current Ratio, Quick Ratio)
3. What bank-specific metrics are available?
4. How to detect banks programmatically?

**Deliverables**:

1. **Detection Strategy**:

   - Industry/SIC code approach
   - Balance sheet structure analysis
   - Filing type analysis
   - Recommended method

2. **Fallback Strategies**:

   - REITs: FFO-based metrics or skip?
   - Banks: Bank-specific ratios or skip?
   - SPACs: Auto-skip (zero revenue)

3. **Decision**:
   - MVP: Document limitation
   - Production: Implement special handlers

---

## Low Priority Research (Future Optimization)

### 6. ROIC Calculation Accuracy

**Priority**: 🟢 LOW
**Impact**: <5% of companies (missing interest expense)
**Blocking**: No (assume 0, add warning)

**Question**: When `interest_expense` missing, should we:

- A: Assume 0 (may understate ROIC)
- B: Estimate from industry avg
- C: Skip ROIC calculation (return None)

**Test Plan**:

1. Query 100 companies
2. Measure `interest_expense` availability
3. Compare approaches (A vs C)
4. Validate assumptions vs industry benchmarks

**Recommendation**: Start with Option A, revisit if needed

---

### 7. S&P 500 Composition Changes

**Priority**: 🟢 LOW
**Impact**: <1% per quarter
**Blocking**: No (weekly refresh sufficient)

**Questions**:

1. Refresh frequency? (daily/weekly/monthly)
2. Ticker change handling? (FB → META)
3. Addition/removal tracking?

**Recommendation**:

- Weekly refresh from SPY holdings API
- Cache to static CSV file
- Track changes in `metadata.sp500_universe` table

---

## Research Execution Plan

### Week 1 (Current)

1. ✅ EdgarTools field normalization (COMPLETE)
2. ✅ Test built-in ratio/trend methods (COMPLETE)
3. ✅ Test time series extraction (COMPLETE)

### Week 2 (If time permits)

1. 🟡 Test IFRS/20-F support
2. 🟡 Test special company types

### Future (Post-MVP)

1. 🟢 ROIC calculation accuracy
2. 🟢 S&P 500 composition changes

---

## Suggested Next Steps

**Immediate (before implementation)**:

1. Test `get_financial_metrics()`, `calculate_ratios()`, `analyze_trends()`

   - Create: `research/test_builtin_metrics.py`
   - Run on 5 companies
   - Document all available metrics
   - **Decision**: Can we skip custom MetricsCalculator?

2. Test time series extraction for CAGR
   - Create: `research/test_time_series_extraction.py`
   - Run on 10 companies (diverse sectors + recent IPO)
   - Document XBRL tag consistency
   - **Decision**: Best approach for multi-year metrics?

**Deferred (document as limitations)**:

- Foreign filers (IFRS/20-F)
- Special company types (REITs, banks)
- Missing data edge cases

**Post-MVP (optimization)**:

- ROIC calculation refinement
- S&P 500 composition tracking
- Performance optimization
- Advanced error handling

---

## Success Criteria

**MVP Launch Ready**:

- ✅ Basic getter methods work (COMPLETE)
- ✅ Multi-year metrics (CAGR) working (COMPLETE - 3Y from single filing)
- ✅ Ratio calculations available (COMPLETE - building custom)
- ✅ 80%+ success rate on standard US companies (COMPLETE - 100%)
- 🔲 Documented limitations (foreign filers, REITs, banks)

**Production Ready** (Future):

- All research questions resolved
- 95%+ success rate on all S&P 500
- Special handling for REITs/banks
- Foreign filer support
- Comprehensive error handling

---

## Notes

- All research scripts in `research/` directory
- Findings documented in `research/FINDINGS_*.md`
- Update implementation plan as research completes
- Tag commits with research decisions (e.g., `DD-034: Time Series Extraction`)
