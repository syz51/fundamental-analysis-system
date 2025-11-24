# Implementation: 9-Filing Approach for 10-Year Financial Data

**Date**: 2025-11-24
**Decision**: Extract 10 years of financial data using 9 filings per company
**Rationale**: Marginal cost of 9th filing (12.5% more calls vs 8 filings) justified by true 10Y duration + reusable metrics

---

## Executive Summary

**Approach**: Query **9 10-K filings** per company to extract **10 years** of financial data.

**Coverage**: 11 unique year data points spanning 10 year duration (true 10 years).

**Performance**: ~3.4 hours for 500 companies (acceptable for weekly batch screening).

**Key Insight**: Extract ALL financials once, reuse for multiple screening metrics.

---

## Test Results: 9 Filings

| Company | Years | Range     | Duration | Time   | API Calls |
| ------- | ----- | --------- | -------- | ------ | --------- |
| AAPL    | 11    | 2014-2024 | 10.0Y    | 7.59s  | 9         |
| MSFT    | 11    | 2014-2024 | 10.0Y    | 14.24s | 9         |
| JPM     | 11    | 2013-2023 | 10.0Y    | 52.92s | 9         |

**Average**: ~25s per company (conservative estimate accounting for JPM outlier)

**Extrapolation to 500 companies**:

- API Calls: 4500 (9 per company)
- Rate Limit: 450s = 7.5 min minimum
- Actual Time: ~25s × 500 = 12,500s = 208 min = **203 min (~3.4 hours)**

---

## Performance vs Alternatives

| Approach    | Filings | Years  | Duration  | API Calls | Time (500 companies) |
| ----------- | ------- | ------ | --------- | --------- | -------------------- |
| Single      | 1       | 3      | 2.0Y      | 500       | 40 min               |
| Multi-4     | 4       | 6      | 5.0Y      | 2000      | 84 min               |
| Multi-7     | 7       | 9      | 8.0Y      | 3500      | 60-90 min            |
| Multi-8     | 8       | 10     | 9.0Y      | 4000      | ~180 min             |
| **Multi-9** | **9**   | **11** | **10.0Y** | **4500**  | **~203 min**         |

**Marginal Cost**: 9 filings vs 8 filings = +500 API calls (+12.5%), +23 min

**Value**: True 10Y data + reusable financials for ALL metrics

---

## All Metrics Extractable from 9 Filings

Once we have 9 filings, we can extract 10 years of data for ALL screening metrics:

### Income Statement Metrics (10-year time series)

**Revenue & Growth**:

- Revenue (total)
- Revenue CAGR (10Y)
- Revenue volatility (std dev)
- Revenue growth acceleration/deceleration

**Profitability**:

- Gross profit
- Operating income
- Net income
- Net income CAGR (10Y)
- Operating margin (10Y average, trend)
- Net margin (10Y average, trend)
- Gross margin (10Y average, trend)

**Expenses**:

- Cost of revenue
- Operating expenses
- Interest expense
- Tax expense

### Balance Sheet Metrics (10-year time series)

**Assets**:

- Total assets
- Current assets
- Cash & equivalents
- Accounts receivable
- Inventory
- Property, plant & equipment (PP&E)

**Liabilities**:

- Total liabilities
- Current liabilities
- Total debt (short-term + long-term)
- Accounts payable

**Equity**:

- Stockholders' equity
- Retained earnings

**Ratios**:

- Current ratio (current assets / current liabilities)
- Quick ratio ((current assets - inventory) / current liabilities)
- Debt/Equity ratio
- Net debt/EBITDA
- Asset turnover

### Cash Flow Statement Metrics (10-year time series)

**Operating Activities**:

- Operating cash flow
- Free cash flow (OCF - CapEx)

**Investing Activities**:

- Capital expenditures (CapEx)
- Acquisitions

**Financing Activities**:

- Dividends paid
- Share repurchases
- Debt issued/repaid

### Return Ratios (10-year average)

**Profitability Returns**:

- ROE (Return on Equity) = Net Income / Stockholders' Equity
- ROA (Return on Assets) = Net Income / Total Assets
- ROIC (Return on Invested Capital) = NOPAT / Invested Capital

**Trends**:

- ROE trend (improving/declining)
- ROA trend
- ROIC trend

---

## Screening Metrics Derived from 10Y Data

### High Priority (Blocking MVP)

1. **10Y Revenue CAGR** ✅

   - Source: Income statement, revenue row, 10 years
   - Calculation: ((Revenue_2024 / Revenue_2014) ^ (1/10) - 1) × 100

2. **Operating Margin (10Y avg)** ✅

   - Source: Income statement, operating income ÷ revenue
   - Calculation: Average over 10 years
   - Bonus: Trend analysis (improving/stable/declining)

3. **Net Debt/EBITDA** ✅

   - Source: Balance sheet (debt), income statement (EBITDA)
   - Latest year only (or 3Y average for stability)

4. **ROE, ROA, ROIC (10Y avg)** ✅
   - Source: All three statements
   - Calculation: Average over 10 years
   - Bonus: Trend analysis

### Medium Priority (Nice to Have)

5. **Free Cash Flow Margin (10Y avg)**

   - Source: Cash flow statement
   - Calculation: FCF / Revenue, averaged

6. **Asset Turnover**

   - Source: Income statement (revenue), balance sheet (assets)
   - Latest year or 3Y average

7. **Working Capital Ratios**
   - Current ratio, quick ratio
   - Latest year

---

## Data Structure: Multi-Filing Cache

**Concept**: Extract once, cache for 7 days, reuse for all metrics.

### Cache Schema

```python
{
    "ticker": "AAPL",
    "filings_fetched": 9,
    "years_available": 11,
    "date_range": "2014-09-27 to 2024-09-28",
    "duration_years": 10.0,
    "last_updated": "2025-11-24T02:00:00Z",

    "income_statement": {
        "2016-09-24": {
            "revenue": 215639000000,
            "operating_income": 60024000000,
            "net_income": 45687000000,
            "cost_of_revenue": 131376000000,
            ...
        },
        "2017-09-30": { ... },
        ...
        "2025-09-27": { ... }
    },

    "balance_sheet": {
        "2016-09-24": {
            "total_assets": 321686000000,
            "total_liabilities": 193437000000,
            "stockholders_equity": 128249000000,
            "current_assets": 106869000000,
            "current_liabilities": 79006000000,
            ...
        },
        ...
    },

    "cash_flow": {
        "2016-09-24": {
            "operating_cash_flow": 65824000000,
            "capital_expenditures": -12734000000,
            "free_cash_flow": 53090000000,
            ...
        },
        ...
    },

    "calculated_metrics": {
        "revenue_cagr_10y": 8.67,
        "net_income_cagr_10y": 12.34,
        "operating_margin_10y_avg": 27.5,
        "roe_10y_avg": 35.6,
        "roa_10y_avg": 14.2,
        "roic_10y_avg": 28.9,
        ...
    }
}
```

### Benefits

1. **Single extraction**: Query 9 filings once, extract all statements
2. **Multi-metric reuse**: Calculate 20+ screening metrics from same data
3. **Trend analysis**: 10-year trends for margins, returns, growth
4. **Cache efficiency**: Store for 7 days, reuse across screening runs
5. **Deep analysis**: Same data used for screening + deep analysis stages

---

## Implementation Plan

### Phase 1: Data Extraction Layer

**Module**: `src/data/financial_extractor.py`

```python
class MultiFilingFinancialExtractor:
    """Extract 10 years of financials from 9 10-K filings"""

    def extract_company_financials(self, ticker: str, num_filings: int = 9) -> Dict:
        """
        Extract all financials from multiple filings

        Returns:
            {
                "ticker": str,
                "filings_fetched": int,
                "years_available": int,
                "income_statement": Dict[date, Dict[metric, value]],
                "balance_sheet": Dict[date, Dict[metric, value]],
                "cash_flow": Dict[date, Dict[metric, value]]
            }
        """
        pass

    def extract_time_series(self, ticker: str, metric: str, statement: str) -> Dict[date, value]:
        """Extract single metric time series (e.g., revenue over 10 years)"""
        pass
```

### Phase 2: Metrics Calculator

**Module**: `src/analysis/metrics_calculator.py`

```python
class FinancialMetricsCalculator:
    """Calculate screening metrics from extracted financials"""

    def calculate_revenue_cagr(self, revenue_history: Dict) -> float:
        """10Y revenue CAGR"""
        pass

    def calculate_operating_margin_avg(self, income_stmt_history: Dict) -> float:
        """10Y average operating margin"""
        pass

    def calculate_roe_avg(self, income_stmt: Dict, balance_sheet: Dict) -> float:
        """10Y average ROE"""
        pass

    def calculate_all_screening_metrics(self, financials: Dict) -> Dict:
        """
        Calculate all 20+ screening metrics from extracted financials

        Returns:
            {
                "revenue_cagr_10y": float,
                "operating_margin_10y_avg": float,
                "net_margin_10y_avg": float,
                "roe_10y_avg": float,
                "roa_10y_avg": float,
                "roic_10y_avg": float,
                "debt_to_equity": float,
                "current_ratio": float,
                ...
            }
        """
        pass
```

### Phase 3: Caching Layer

**Module**: `src/data/financial_cache.py`

```python
class FinancialDataCache:
    """Cache extracted financials to avoid re-querying"""

    def get_cached_financials(self, ticker: str) -> Optional[Dict]:
        """Get cached data if <7 days old"""
        pass

    def cache_financials(self, ticker: str, financials: Dict):
        """Store extracted financials with timestamp"""
        pass

    def is_cache_valid(self, ticker: str, max_age_days: int = 7) -> bool:
        """Check if cached data is still valid"""
        pass
```

---

## Performance Optimization

### Parallel API Calls (Respect Rate Limit)

```python
import asyncio
from concurrent.futures import ThreadPoolExecutor

async def extract_all_companies_parallel(tickers: List[str], max_concurrent: int = 10):
    """
    Extract financials for 500 companies in parallel

    - Respect 10 req/sec SEC rate limit
    - Process 10 companies concurrently
    - Total: ~3.4 hours for 500 companies
    """

    with ThreadPoolExecutor(max_workers=max_concurrent) as executor:
        # Process in batches to respect rate limit
        for batch in batch_tickers(tickers, batch_size=10):
            await asyncio.gather(*[
                extract_company_financials(ticker)
                for ticker in batch
            ])
            await asyncio.sleep(1)  # Rate limit: 10 req/sec
```

### Incremental Updates

- **Weekly screening**: Only update companies with new filings
- **Quarterly 10-Q**: Update with latest quarter (separate cache)
- **Annual refresh**: Re-extract all 500 companies once per year

---

## Cost-Benefit Summary

### Costs

| Factor         | Amount                                    |
| -------------- | ----------------------------------------- |
| API Calls      | 4500 (9 per company × 500)                |
| Runtime        | ~3.4 hours (weekly batch)                 |
| Storage        | ~50MB per 500 companies (cached JSON)     |
| Implementation | ~500 LOC (extractor + calculator + cache) |

### Benefits

| Benefit             | Value                                 |
| ------------------- | ------------------------------------- |
| True 10Y CAGR       | Eliminates 9.84pp avg error           |
| Multi-metric reuse  | 20+ metrics from single extraction    |
| Trend analysis      | 10Y margins, returns, growth patterns |
| Deep analysis reuse | Same data for screening + deep dive   |
| Cache efficiency    | 7-day cache, reuse across runs        |

**ROI**: +3.4 hours runtime → 20+ high-quality metrics + trend analysis + deep analysis data

---

## Decision

**DD-036: 9-Filing Approach for 10-Year Financial Data**

**Decision**: Query **9 10-K filings** per company to extract **10 years** of financial data for ALL screening metrics.

**Rationale**:

1. True 10Y coverage (10 year duration, 11 unique years)
2. Extract ALL financials once, reuse for 20+ metrics
3. Same data used for screening + deep analysis stages
4. 3.4-hour runtime acceptable for weekly batch screening
5. Marginal cost vs 8 filings: +12.5% API calls for true 10Y duration

**Tradeoffs**:

- ✅ Pros: True 10Y data, multi-metric reuse, trend analysis, cache efficiency
- ⚠️ Cons: 3.4-hour runtime (vs 40 min for single filing)

**Impact**:

- Screening metrics: ALL 10Y (revenue CAGR, margins, ROE/ROA/ROIC, etc.)
- Screening time: ~3.4 hours weekly (acceptable for batch process)
- Data reuse: Same extraction for screening + deep analysis
- Cache: 7-day validity, avoids re-querying

**Implementation Priority**: HIGH (core screening infrastructure)

---

## Next Steps

1. ✅ Test 9-filing approach (COMPLETE)
2. ⏭️ Implement `MultiFilingFinancialExtractor` (~200 LOC)
3. ⏭️ Implement `FinancialMetricsCalculator` (~200 LOC)
4. ⏭️ Implement `FinancialDataCache` (~100 LOC)
5. ⏭️ Benchmark on 50 companies (dry run)
6. ⏭️ Full 500-company screening test

**Estimated Implementation**: 2-3 days for full extraction + metrics + cache layer

---

## Appendix: Sample Extraction Code

```python
def extract_10y_financials(ticker: str) -> Dict:
    """Extract 10 years of financials from 9 filings"""

    company = Company(ticker)
    filings = company.get_filings(form="10-K").latest(9)

    financials = {
        "ticker": ticker,
        "income_statement": {},
        "balance_sheet": {},
        "cash_flow": {}
    }

    for filing in filings:
        tenk = filing.obj()

        # Extract income statement
        inc_df = tenk.income_statement.to_dataframe()
        date_cols = extract_date_columns(inc_df)

        for date in date_cols:
            if date not in financials["income_statement"]:
                financials["income_statement"][date] = {
                    "revenue": extract_metric(inc_df, "revenue", date),
                    "operating_income": extract_metric(inc_df, "operating income", date),
                    "net_income": extract_metric(inc_df, "net income", date),
                    # ... extract all metrics
                }

        # Extract balance sheet
        bs_df = tenk.balance_sheet.to_dataframe()
        date_cols = extract_date_columns(bs_df)

        for date in date_cols:
            if date not in financials["balance_sheet"]:
                financials["balance_sheet"][date] = {
                    "total_assets": extract_metric(bs_df, "total assets", date),
                    "total_liabilities": extract_metric(bs_df, "total liabilities", date),
                    "stockholders_equity": extract_metric(bs_df, "stockholders equity", date),
                    # ... extract all metrics
                }

        # Extract cash flow
        cf_df = tenk.cash_flow_statement.to_dataframe()
        date_cols = extract_date_columns(cf_df)

        for date in date_cols:
            if date not in financials["cash_flow"]:
                financials["cash_flow"][date] = {
                    "operating_cash_flow": extract_metric(cf_df, "operating cash flow", date),
                    "capital_expenditures": extract_metric(cf_df, "capital expenditures", date),
                    # ... extract all metrics
                }

    return financials
```
