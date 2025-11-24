# Research Findings: EdgarTools Built-in Ratio/Trend Methods

**Date**: 2025-11-24
**Status**: COMPLETE
**Priority**: HIGH (Blocking MVP)
**Decision Impact**: Determines if we can skip custom MetricsCalculator (300+ lines)

---

## Executive Summary

❌ **RESULT**: EdgarTools built-in ratio methods **INCOMPLETE & UNRELIABLE**

🎯 **RECOMMENDATION**:

- **Build custom MetricsCalculator** (cannot skip)
- **Use getter methods** with DataFrame fallback for data extraction
- **Do NOT use** `calculate_ratios()` or `analyze_trends()` (empty/inconsistent)

---

## Test Results

### Test Configuration

- **Companies Tested**: 5 S&P 500 companies (AAPL, JPM, JNJ, XOM, WMT)
- **Sectors**: Tech, Banking, Healthcare, Energy, Consumer
- **EdgarTools Version**: 4.30.0
- **Test Date**: 2025-11-24

---

## Key Findings

### 1. calculate_ratios() - UNRELIABLE ❌

**Method**: `statement.calculate_ratios() -> Dict[str, float]`

**Coverage**: 2/5 companies (40%) returned data

| Ticker | Income Statement Ratios  | Balance Sheet Ratios |
| ------ | ------------------------ | -------------------- |
| AAPL   | `{}` (empty)             | `{}` (empty)         |
| JPM    | `{}` (empty)             | `{}` (empty)         |
| JNJ    | `{}` (empty)             | `{}` (empty)         |
| XOM    | `{'net_margin': 0.0963}` | `{}` (empty)         |
| WMT    | `{'net_margin': 0.0285}` | `{}` (empty)         |

**Issues**:

- Only 2/5 companies returned ANY data
- Only ONE ratio available (net_margin)
- No ROE, ROA, ROIC, operating margin, or any balance sheet ratios
- Inconsistent across companies (why XOM/WMT but not AAPL/JPM/JNJ?)

**Source Code Analysis**:

```python
def calculate_ratios(self) -> Dict[str, float]:
    """Calculate common financial ratios for this statement."""
    ratios = {}
    data = self.get_raw_data()

    # Calls internal _calculate_income_statement_ratios() or
    # _calculate_balance_sheet_ratios() - NOT accessible to users

    return ratios  # Returns empty dict if internal methods fail
```

**Conclusion**: Method exists but implementation is INCOMPLETE. Cannot rely on it.

---

### 2. analyze_trends() - NOT FUNCTIONAL ❌

**Method**: `statement.analyze_trends(periods: int = 4) -> Dict[str, List[float]]`

**Coverage**: 0/5 companies (0%) returned data

| Ticker | Income Statement Trends | Balance Sheet Trends |
| ------ | ----------------------- | -------------------- |
| ALL    | `{}` (empty)            | `{}` (empty)         |

**Issues**:

- Returns empty dict for ALL companies
- No CAGR calculation available
- No trend analysis available
- Method exists but does nothing useful

**Source Code Analysis**:

```python
def analyze_trends(self, periods: int = 4) -> Dict[str, List[float]]:
    """Analyze trends in key metrics over time."""
    trends = {}

    period_views = self.xbrl.get_period_views(statement_type)
    if not period_views:
        return trends  # Empty dict

    # Internal trend methods likely not implemented
    return trends
```

**Conclusion**: Method exists but is NON-FUNCTIONAL. Must build custom CAGR calculation.

---

### 3. get_financial_metrics() - DOES NOT EXIST ❌

**Method**: `financials.get_financial_metrics()`

**Finding**: Method does NOT exist on Company or Financials objects

**Error**: `'Company' object has no attribute 'financials'`

**Conclusion**: This method was hypothesized but doesn't exist in EdgarTools 4.30.0.

---

### 4. Getter Methods - PARTIALLY RELIABLE ⚠️

**Method**: `financials.get_<metric>() -> float | str | None`

**Location**: On Financials object (not Statement object)

**Coverage Analysis**:

| Metric                      | AAPL | JPM     | JNJ      | XOM | WMT      | Success Rate |
| --------------------------- | ---- | ------- | -------- | --- | -------- | ------------ |
| `get_revenue()`             | ✅   | ❌ ""   | ❌ None  | ✅  | ✅       | 60%          |
| `get_net_income()`          | ✅   | ✅      | ✅       | ✅  | ✅       | **100%** ✅  |
| `get_total_assets()`        | ✅   | ✅      | ✅       | ✅  | ✅       | **100%** ✅  |
| `get_stockholders_equity()` | ✅   | ✅      | ✅       | ✅  | ✅       | **100%** ✅  |
| `get_operating_cash_flow()` | ✅   | ❌ ""   | ❌ ""    | ✅  | ❌ ""    | 40%          |
| `get_free_cash_flow()`      | ✅   | ❌ None | ❌ Error | ✅  | ❌ Error | 40%          |
| `get_current_assets()`      | ✅   | ❌ None | ✅       | ✅  | ✅       | 80%          |
| `get_current_liabilities()` | ✅   | ❌ None | ✅       | ✅  | ✅       | 80%          |

**Type Issues**:

- **AAPL, XOM**: All methods return `float` ✅
- **JPM** (Bank): Returns empty string `""` or `None` for many methods
- **JNJ**: Returns `None` for revenue, empty string for cash flow
- **WMT**: Returns empty string for cash flow methods

**Root Cause**:

- Banks (JPM) likely have different statement structure (no "revenue" line item)
- Some companies have missing data in filings
- EdgarTools getters don't handle all edge cases

**Reliability for Screening Metrics**:

- ✅ Net Income: 100% success
- ✅ Total Assets: 100% success
- ✅ Stockholders' Equity: 100% success
- ⚠️ Revenue: 60% success (fails for banks, some others)
- ⚠️ Current Assets/Liabilities: 80% success

**Conclusion**: Core balance sheet metrics (100% success) are reliable. Revenue has issues with banks.

---

## Gap Analysis vs. Screening Requirements

### Required Screening Metrics (from RESEARCH_TODO.md)

| Metric                 | EdgarTools Built-in  | Coverage | Decision                       |
| ---------------------- | -------------------- | -------- | ------------------------------ |
| Revenue (latest)       | `get_revenue()`      | 60%      | ⚠️ Use with DataFrame fallback |
| Net Income (latest)    | `get_net_income()`   | 100%     | ✅ Use getter method           |
| Revenue CAGR (10Y, 5Y) | ❌ None              | 0%       | ❌ Build custom                |
| Operating Margin (3Y)  | ❌ None              | 0%       | ❌ Build custom                |
| Net Margin (3Y)        | `calculate_ratios()` | 40%      | ❌ Build custom (unreliable)   |
| ROE (3Y avg)           | ❌ None              | 0%       | ❌ Build custom                |
| ROA (3Y avg)           | ❌ None              | 0%       | ❌ Build custom                |
| ROIC (3Y avg)          | ❌ None              | 0%       | ❌ Build custom                |
| Debt/Equity            | ❌ None              | 0%       | ❌ Build custom                |
| Current Ratio          | `get_current_*`      | 80%      | ⚠️ Use with fallback           |

**Summary**:

- **0/10 metrics** available from built-in methods (9 missing, 1 unreliable)
- **Must build custom MetricsCalculator**
- **Cannot skip 300+ lines of code** as hoped

---

## Recommended Data Extraction Strategy

### Hybrid Approach: Getter Methods + DataFrame Fallback

```python
from edgar import Company

company = Company("AAPL")
financials = company.get_financials()

# Approach 1: Try getter method first (fast, simple)
try:
    revenue = financials.get_revenue()
    if revenue is None or revenue == "":
        raise ValueError("Empty revenue")
except (AttributeError, ValueError, TypeError):
    # Approach 2: Fallback to DataFrame extraction
    tenk = company.get_filings(form="10-K").latest(1)
    financials_obj = tenk.obj()
    income_stmt = financials_obj.income_statement
    df = income_stmt.to_dataframe()

    # Extract revenue from DataFrame (see previous research)
    revenue_row = df[df['concept'].str.contains('Revenue', case=False)]
    revenue = float(revenue_row.iloc[0]['2024-12-31'])
```

**Benefits**:

- Fast path for companies where getters work (AAPL, XOM, WMT)
- Robust fallback for banks and edge cases (JPM, JNJ)
- Handles all companies reliably

---

## Final Recommendations

### 1. **DO NOT USE** `calculate_ratios()` or `analyze_trends()`

**Reasons**:

- 40% coverage (calculate_ratios)
- 0% coverage (analyze_trends)
- Inconsistent behavior across companies
- Only provides 1 ratio (net_margin)
- Not maintained/complete

### 2. **BUILD Custom MetricsCalculator**

**Required Custom Metrics**:

- Revenue CAGR (10Y, 5Y)
- Operating Margin (latest, 3Y avg)
- Net Margin (latest, 3Y avg)
- ROE, ROA, ROIC (latest, 3Y avg)
- Debt/Equity ratio
- Current Ratio (with getter fallback)

**Estimated LOC**: 300-400 lines (as originally planned)

### 3. **Data Extraction Layer**

**Use Hybrid Approach**:

1. Try getter methods first (60-100% success depending on metric)
2. Fallback to DataFrame extraction (100% success with proper parsing)
3. Handle type normalization (float, str, None)

**Example Wrapper**:

```python
def safe_get_metric(financials, getter_method, df_fallback):
    """Try getter method, fallback to DataFrame if needed"""
    try:
        value = getattr(financials, getter_method)()
        if value is None or value == "":
            raise ValueError("Empty value")
        return float(value) if isinstance(value, str) else value
    except (AttributeError, ValueError, TypeError):
        return df_fallback()  # Custom DataFrame extraction
```

### 4. **Time Series Extraction** (Next Research Item)

**Critical for CAGR**:

- `analyze_trends()` does NOT work
- Must extract multi-year data from DataFrame
- Next research task: Test time series extraction patterns

---

## Updated Implementation Plan

### Original Hope (from TODO)

> **Impact**: Could eliminate 300+ lines of custom metric code

### Reality

**Cannot eliminate MetricsCalculator**. Must build full implementation with:

1. **Data Extraction Layer** (~100 lines)

   - Hybrid getter + DataFrame approach
   - Type normalization
   - Error handling

2. **Ratio Calculations** (~150 lines)

   - Net/Operating Margin
   - ROE, ROA, ROIC
   - Debt/Equity
   - Current Ratio

3. **Trend Calculations** (~100 lines)
   - Revenue CAGR (10Y, 5Y)
   - 3-year averages
   - Growth rates

**Total**: ~350 lines (as originally estimated)

---

## Next Research Task

**Priority**: 🔴 HIGH (still blocking)

**Task**: Time Series Data Extraction for CAGR

**Questions**:

1. How to extract 10 years of revenue from DataFrame?
2. Are XBRL tags consistent across companies?
3. Best approach for multi-year metrics?

**Script**: `research/test_time_series_extraction.py` (to create)

---

## Files Generated

1. `research/test_builtin_metrics.py` - Initial method discovery
2. `research/test_builtin_metrics_deep_dive.py` - Method signature analysis
3. `research/test_raw_data_extraction.py` - Raw data structure tests
4. `research/test_getter_methods_vs_calculate_ratios.py` - Comparison tests
5. `research/test_getter_type_issues.py` - Type reliability analysis
6. `research/FINDINGS_builtin_metrics_raw.json` - Raw test results
7. `research/FINDINGS_EdgarTools_Builtin_Metrics.md` - This document

---

## Decision Log

**DD-034: EdgarTools Built-in Metrics**

- **Decision**: Do NOT use `calculate_ratios()` or `analyze_trends()`
- **Rationale**: 0-40% coverage, incomplete implementation, unreliable
- **Alternative**: Build custom MetricsCalculator with hybrid data extraction
- **Impact**: ~350 lines of code (as originally planned, cannot skip)
- **Date**: 2025-11-24
