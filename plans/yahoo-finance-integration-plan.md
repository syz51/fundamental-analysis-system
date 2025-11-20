# Yahoo Finance Integration Plan

**Status**: Ready to implement
**Phase**: Phase 1 - Foundation (Screening Data)
**Estimated Timeline**: 2-3 days
**Dependencies**: PostgreSQL operational
**Related Decisions**: DD-032 (Hybrid Data Sourcing Strategy)

---

## 1. Overview

Integrate Yahoo Finance API as primary data source for **screening stage only** (Days 1-2 of analysis pipeline). Deep analysis stage (Days 3-7) continues to use SEC EDGAR parsing per DD-031.

**Purpose**: Enable immediate screening of S&P 500 companies without 4.2hr SEC filing backfill wait.

**Scope**:
- Fetch 10Y historical financials for S&P 500 (revenue, EPS, margins, debt ratios)
- Calculate screening metrics (10Y/5Y revenue CAGR, ROE/ROA/ROIC)
- Store in PostgreSQL with `data_source='yahoo_finance'`
- Generate quantitative summaries for Human Gate 1

**Out of Scope** (Deep Analysis - uses SEC EDGAR):
- Qualitative data (MD&A, risk factors, business descriptions)
- Amendment tracking
- Context disambiguation
- 98.55% data quality validation

---

## 2. Library Selection

### Option A: yfinance (RECOMMENDED)

**Description**: Unofficial Yahoo Finance API wrapper, most popular Python library

**Pros**:
- ✅ Free, open source
- ✅ 11K+ GitHub stars, actively maintained
- ✅ Simple API: `yf.Ticker('AAPL').financials`
- ✅ 10Y+ historical data available
- ✅ Annual + quarterly granularity
- ✅ Covers: income statement, balance sheet, cash flow

**Cons**:
- ⚠️ Unofficial (Yahoo can break API anytime)
- ⚠️ Rate limiting unclear (community reports 2K req/hour safe)
- ⚠️ Data quality ~95% (good enough for screening per DD-032)

**Installation**: `pip install yfinance` (add to pyproject.toml)

**Example**:
```python
import yfinance as yf

aapl = yf.Ticker('AAPL')
financials = aapl.financials  # Annual income statement (last 4 years)
quarterly = aapl.quarterly_financials  # Quarterly (last 4 quarters)
balance = aapl.balance_sheet
cashflow = aapl.cashflow
```

---

### Option B: Alpha Vantage

**Description**: Official financial data API with free + premium tiers

**Pros**:
- ✅ Official API (stable, documented)
- ✅ Free tier: 5 req/min, 500 req/day
- ✅ Premium tier: $50/month for unlimited
- ✅ 10Y+ historical data

**Cons**:
- ❌ Rate limit: 5 req/min (S&P 500 = 100 min = 1.7 hours for full fetch)
- ❌ Premium cost: $50/month (vs yfinance free)
- ❌ More complex API (requires API key, parsing JSON responses)

**Installation**: `pip install alpha-vantage`

**Example**:
```python
from alpha_vantage.fundamentaldata import FundamentalData

fd = FundamentalData(key='YOUR_API_KEY')
income_statement, _ = fd.get_income_statement_annual('AAPL')
```

---

### Recommendation: Start with yfinance

**Rationale**:
- Free, simple, covers all screening needs
- If rate limits hit, can throttle requests or upgrade to Alpha Vantage
- Fallback: SEC EDGAR parsing (already designed per DD-031)

**Fallback Path**:
1. Try yfinance
2. If rate limited: Throttle to 2 req/sec (S&P 500 = 4.2 min)
3. If Yahoo breaks API: Switch to Alpha Vantage or SEC parsing

---

## 3. Implementation Phases

### Phase A: Yahoo Finance Client (1 day)

**A1. Client Wrapper** (`src/data_collector/yahoo_finance_client.py`)

```python
"""Yahoo Finance API client for bulk financial data fetching"""
import yfinance as yf
from typing import Dict, List, Optional
import asyncio
import logging

logger = logging.getLogger(__name__)

class YahooFinanceClient:
    """Fetch historical financial data from Yahoo Finance"""

    def __init__(self, rate_limit_delay: float = 0.5):
        """
        Args:
            rate_limit_delay: Delay between requests in seconds (default 0.5s = 2 req/sec)
        """
        self.rate_limit_delay = rate_limit_delay

    async def get_financials(self, ticker: str) -> Dict:
        """
        Fetch 10Y financial data for a single company

        Returns:
            {
                'ticker': 'AAPL',
                'annual_income': DataFrame,  # Last 4 years
                'quarterly_income': DataFrame,  # Last 4 quarters
                'balance_sheet': DataFrame,
                'cash_flow': DataFrame,
                'info': {  # Company metadata
                    'sector': 'Technology',
                    'industry': 'Consumer Electronics',
                    'market_cap': 3000000000000
                }
            }
        """
        try:
            await asyncio.sleep(self.rate_limit_delay)  # Rate limiting

            stock = yf.Ticker(ticker)

            return {
                'ticker': ticker,
                'annual_income': stock.financials,  # Annual income statement
                'quarterly_income': stock.quarterly_financials,
                'balance_sheet': stock.balance_sheet,
                'cash_flow': stock.cashflow,
                'info': stock.info  # Company metadata (sector, industry, etc.)
            }

        except Exception as e:
            logger.error(f"Failed to fetch {ticker}: {e}")
            return None

    async def get_bulk_financials(self, tickers: List[str]) -> Dict[str, Dict]:
        """
        Fetch financials for multiple companies (batched with rate limiting)

        Args:
            tickers: List of ticker symbols (e.g., ['AAPL', 'MSFT', 'GOOGL'])

        Returns:
            {'AAPL': {...}, 'MSFT': {...}, ...}
        """
        results = {}

        for ticker in tickers:
            data = await self.get_financials(ticker)
            if data:
                results[ticker] = data

        logger.info(f"Fetched {len(results)}/{len(tickers)} companies successfully")
        return results

    async def get_sp500_financials(self) -> Dict[str, Dict]:
        """Fetch financials for all S&P 500 companies"""
        sp500_tickers = self._get_sp500_tickers()
        return await self.get_bulk_financials(sp500_tickers)

    def _get_sp500_tickers(self) -> List[str]:
        """Get list of S&P 500 ticker symbols"""
        # Option 1: Hardcode list (most reliable)
        # Option 2: Fetch from Wikipedia (dynamic but fragile)
        import pandas as pd

        url = 'https://en.wikipedia.org/wiki/List_of_S%26P_500_companies'
        tables = pd.read_html(url)
        sp500 = tables[0]
        return sp500['Symbol'].tolist()
```

**Testing**:
- Unit test: Fetch AAPL, verify DataFrames not empty
- Integration test: Fetch 10 companies, measure latency
- Rate limit test: Fetch 100 companies, verify no 429 errors
- Fallback test: Mock Yahoo API failure, verify error handling

---

### Phase B: Data Transformation (0.5 days)

**B1. Metrics Calculator** (`src/data_collector/yahoo_metrics.py`)

```python
"""Calculate screening metrics from Yahoo Finance data"""
import pandas as pd
import numpy as np
from typing import Dict, Optional

def calculate_cagr(values: pd.Series, years: int) -> Optional[float]:
    """
    Calculate Compound Annual Growth Rate

    Args:
        values: Time series of financial metric (most recent first)
        years: Number of years for CAGR (e.g., 10)

    Returns:
        CAGR as decimal (e.g., 0.15 for 15%)
    """
    if len(values) < years + 1:
        return None  # Insufficient data

    try:
        values = values.sort_index()  # Oldest to newest
        start_value = values.iloc[0]
        end_value = values.iloc[-1]

        if start_value <= 0:
            return None  # Can't calculate CAGR with zero/negative start

        cagr = (end_value / start_value) ** (1 / years) - 1
        return float(cagr)

    except Exception:
        return None

def calculate_screening_metrics(yahoo_data: Dict) -> Dict:
    """
    Calculate all screening metrics from Yahoo Finance data

    Args:
        yahoo_data: Output from YahooFinanceClient.get_financials()

    Returns:
        {
            'ticker': 'AAPL',
            'revenue_cagr_10y': 0.15,  # 15%
            'revenue_cagr_5y': 0.12,
            'operating_margin_avg': 0.25,
            'net_margin_avg': 0.20,
            'roe_avg': 0.35,
            'roa_avg': 0.15,
            'roic_avg': 0.25,
            'debt_to_equity_latest': 1.5,
            'current_ratio_latest': 1.2
        }
    """
    try:
        income = yahoo_data['annual_income']
        balance = yahoo_data['balance_sheet']

        # Revenue CAGR
        revenue = income.loc['Total Revenue'] if 'Total Revenue' in income.index else None
        revenue_cagr_10y = calculate_cagr(revenue, 10) if revenue is not None else None
        revenue_cagr_5y = calculate_cagr(revenue, 5) if revenue is not None else None

        # Margins (average last 3 years)
        operating_income = income.loc['Operating Income'] if 'Operating Income' in income.index else None
        net_income = income.loc['Net Income'] if 'Net Income' in income.index else None

        operating_margin_avg = (operating_income / revenue).tail(3).mean() if operating_income is not None else None
        net_margin_avg = (net_income / revenue).tail(3).mean() if net_income is not None else None

        # ROE, ROA (average last 3 years)
        total_assets = balance.loc['Total Assets'] if 'Total Assets' in balance.index else None
        total_equity = balance.loc['Total Stockholder Equity'] if 'Total Stockholder Equity' in balance.index else None

        roe_avg = (net_income / total_equity).tail(3).mean() if total_equity is not None else None
        roa_avg = (net_income / total_assets).tail(3).mean() if total_assets is not None else None

        # ROIC = NOPAT / Invested Capital (simplified)
        # NOPAT ≈ Operating Income * (1 - tax rate)
        # Invested Capital ≈ Total Equity + Total Debt
        tax_rate = 0.21  # Assume 21% corporate tax
        nopat = operating_income * (1 - tax_rate) if operating_income is not None else None
        total_debt = balance.loc['Total Debt'] if 'Total Debt' in balance.index else None
        invested_capital = (total_equity + total_debt) if total_debt is not None else total_equity
        roic_avg = (nopat / invested_capital).tail(3).mean() if nopat is not None else None

        # Debt ratios (latest)
        debt_to_equity_latest = (total_debt / total_equity).iloc[0] if total_debt is not None else None

        # Current ratio (latest)
        current_assets = balance.loc['Current Assets'] if 'Current Assets' in balance.index else None
        current_liabilities = balance.loc['Current Liabilities'] if 'Current Liabilities' in balance.index else None
        current_ratio_latest = (current_assets / current_liabilities).iloc[0] if current_assets is not None else None

        return {
            'ticker': yahoo_data['ticker'],
            'revenue_cagr_10y': revenue_cagr_10y,
            'revenue_cagr_5y': revenue_cagr_5y,
            'operating_margin_avg': operating_margin_avg,
            'net_margin_avg': net_margin_avg,
            'roe_avg': roe_avg,
            'roa_avg': roa_avg,
            'roic_avg': roic_avg,
            'debt_to_equity_latest': debt_to_equity_latest,
            'current_ratio_latest': current_ratio_latest
        }

    except Exception as e:
        logger.error(f"Failed to calculate metrics for {yahoo_data['ticker']}: {e}")
        return {'ticker': yahoo_data['ticker'], 'error': str(e)}
```

**Testing**:
- Unit test: Calculate CAGR for known values (verify math)
- Integration test: Calculate metrics for AAPL, compare to known values
- Edge cases: Zero revenue, negative values, missing data

---

### Phase C: PostgreSQL Integration (0.5 days)

**C1. Schema Update**

Add `data_source` column to track Yahoo vs SEC data:

```sql
-- Migration: Add data_source column
ALTER TABLE financial_data.income_statements
ADD COLUMN data_source VARCHAR(20) DEFAULT 'sec_edgar';

ALTER TABLE financial_data.balance_sheets
ADD COLUMN data_source VARCHAR(20) DEFAULT 'sec_edgar';

ALTER TABLE financial_data.cash_flows
ADD COLUMN data_source VARCHAR(20) DEFAULT 'sec_edgar';

-- Index for filtering by source
CREATE INDEX idx_income_statements_source ON financial_data.income_statements(data_source);
CREATE INDEX idx_balance_sheets_source ON financial_data.balance_sheets(data_source);
CREATE INDEX idx_cash_flows_source ON financial_data.cash_flows(data_source);
```

**C2. PostgreSQL Client Update** (`src/storage/postgres_client.py`)

```python
async def insert_yahoo_screening_metrics(
    self,
    ticker: str,
    metrics: Dict,
    data_source: str = 'yahoo_finance'
):
    """
    Insert screening metrics from Yahoo Finance

    Args:
        ticker: Company ticker symbol
        metrics: Output from calculate_screening_metrics()
        data_source: 'yahoo_finance' (vs 'sec_edgar')
    """
    # Store in screening_metrics table (or repurpose financial_data with source flag)
    # Simplified: Store as JSON metadata for now, can normalize later
    pass
```

**Testing**:
- Migration test: Run Alembic migration, verify column added
- Insert test: Insert Yahoo data, verify `data_source='yahoo_finance'`
- Query test: Filter by `data_source`, verify only Yahoo data returned

---

## 4. Screening Integration

**Workflow**:

```
1. YahooFinanceClient.get_sp500_financials()
   ↓ Fetch 500 companies (4.2 min @ 2 req/sec)

2. For each company: calculate_screening_metrics()
   ↓ CAGR, margins, ROE/ROA/ROIC

3. PostgresClient.insert_yahoo_screening_metrics()
   ↓ Store with data_source='yahoo_finance'

4. Screening Agent queries PostgreSQL
   ↓ Filter: revenue_cagr_10y ≥ 0.15, operating_margin ≥ 0.08, etc.

5. Generate summaries
   ↓ "AAPL: 18% 10Y CAGR, 25% operating margin, ROE 35%"

6. Human Gate 1
   ↓ Select ~10-20 candidates

7. Data Collector: Fetch SEC filings for approved companies
   ↓ Deep analysis (per DD-031)
```

**CLI Command** (`src/agents/data_collector/cli.py`):

```bash
# Fetch Yahoo Finance screening data for all S&P 500
python -m src.data_collector yahoo-backfill

# Fetch Yahoo data for specific companies
python -m src.data_collector yahoo-fetch --tickers AAPL,MSFT,GOOGL
```

---

## 5. Fallback Strategy

**Trigger Conditions**:
1. Yahoo API returns 429 (rate limit exceeded)
2. Yahoo API returns 503 (service unavailable)
3. Yahoo data missing for >10% of companies
4. Yahoo data quality check fails (e.g., balance sheet doesn't balance)

**Fallback Actions**:

**Tier 1: Retry with Backoff**
```python
for attempt in range(3):
    try:
        data = await yahoo_client.get_financials(ticker)
        break
    except RateLimitError:
        await asyncio.sleep(2 ** attempt)  # 1s, 2s, 4s
```

**Tier 2: Switch to SEC Parsing**
```python
if yahoo_fetch_failures > 50:  # >10% of S&P 500
    logger.warning("Yahoo Finance degraded, falling back to SEC parsing")
    await sec_edgar_client.fetch_for_screening(tickers)
```

**Tier 3: Use Cached Data**
```python
# If Yahoo unavailable and SEC parsing slow, use last successful fetch
cached_data = await postgres.get_latest_yahoo_data(max_age_days=7)
if cached_data:
    logger.warning("Using cached Yahoo data (up to 7 days old)")
    return cached_data
```

**Monitoring**:
- Alert if Yahoo fetch failures >10%
- Alert if fallback to SEC parsing triggered
- Dashboard: Show data source distribution (Yahoo vs SEC vs cached)

---

## 6. Testing Strategy

### Unit Tests

**test_yahoo_finance_client.py**:
- Fetch single ticker (AAPL)
- Fetch batch (10 tickers)
- Rate limiting (verify delay between requests)
- Error handling (invalid ticker, API failure)

**test_yahoo_metrics.py**:
- CAGR calculation (known values)
- Margin calculation
- ROE/ROA/ROIC calculation
- Edge cases (zero revenue, negative values, missing data)

### Integration Tests

**test_yahoo_screening_pipeline.py**:
- Fetch Yahoo data for 10 companies
- Calculate metrics
- Store in PostgreSQL
- Query by screening filters
- Verify data_source='yahoo_finance'

### Performance Tests

**test_yahoo_bulk_fetch.py**:
- Fetch 100 companies (measure latency)
- Verify rate limiting (no 429 errors)
- Memory usage (should be <200MB)

### Validation Tests

**test_yahoo_vs_sec.py**:
- Fetch same company from Yahoo + SEC
- Compare revenue, net income, total assets
- Flag discrepancies >10%
- Log patterns for QC Agent review

---

## 7. Data Quality Validation

**Validation Rules** (before storing Yahoo data):

1. **Completeness Check**:
   - Require minimum 5/8 screening metrics
   - Flag companies with <5Y data (insufficient for 10Y CAGR)

2. **Range Checks**:
   - Revenue ≥ $0 (never negative)
   - Margins between -100% and +100%
   - ROE/ROA/ROIC between -200% and +200%

3. **Balance Sheet Equation**:
   - Assets ≈ Liabilities + Equity (10% tolerance for Yahoo data)
   - Flag if equation doesn't balance

4. **CAGR Sanity Check**:
   - Flag if CAGR >100% or < -50% (likely data error)

**Logging**:
```python
validation_results = {
    'total_companies': 500,
    'successful': 475,
    'incomplete_data': 20,  # <5/8 metrics
    'range_violations': 3,
    'balance_sheet_errors': 2
}
logger.info(f"Yahoo Finance validation: {validation_results}")
```

---

## 8. Timeline & Milestones

### Day 1: Client & Metrics

**Morning (4 hours)**:
- Implement `YahooFinanceClient` (Phase A)
- Add `yfinance` to pyproject.toml, test installation
- Unit tests: Fetch AAPL, verify DataFrames

**Afternoon (4 hours)**:
- Implement `calculate_screening_metrics()` (Phase B)
- Unit tests: CAGR, margins, ratios
- Integration test: AAPL end-to-end (fetch + calculate)

---

### Day 2: Storage & Integration

**Morning (4 hours)**:
- PostgreSQL schema migration (add `data_source` column)
- Update `PostgresClient.insert_yahoo_screening_metrics()`
- Integration test: Store Yahoo data, query by source

**Afternoon (4 hours)**:
- Implement screening pipeline (fetch S&P 500 → calculate → store)
- CLI command: `python -m src.data_collector yahoo-backfill`
- Run backfill for 10 test companies

---

### Day 3: Validation & Testing

**Morning (4 hours)**:
- Implement data quality validation
- Implement fallback strategy (retry, SEC fallback, cached data)
- Unit tests: Validation rules, fallback triggers

**Afternoon (4 hours)**:
- Run full S&P 500 backfill (500 companies, ~4.2 min)
- Validation report: Success rate, data quality, errors
- Documentation: Update data-collector-implementation.md

---

## 9. Success Criteria

**Functional Requirements**:
- ✅ Fetch 10Y financial data for S&P 500 companies
- ✅ Calculate screening metrics (CAGR, margins, ROE/ROA/ROIC)
- ✅ Store in PostgreSQL with `data_source='yahoo_finance'`
- ✅ Screening Agent can query Yahoo data for filtering
- ✅ Fallback to SEC parsing if Yahoo unavailable

**Performance Requirements**:
- ✅ S&P 500 backfill: <10 min (500 companies @ 2 req/sec)
- ✅ Success rate: >90% (acceptable to miss 10% and fall back to SEC)
- ✅ Data quality: >95% (per DD-032 screening acceptable threshold)

**Quality Requirements**:
- ✅ Test coverage: >80%
- ✅ Validation: Balance sheet checks, range checks, completeness
- ✅ Logging: Structured logs with success/failure metrics
- ✅ Fallback: Automatic retry + SEC fallback implemented

---

## 10. Unresolved Questions

1. **S&P 500 ticker list source**: Hardcode or fetch from Wikipedia? (Wikipedia fragile but dynamic)
2. **Quarterly vs annual data**: Screening uses annual (10Y CAGR), but deep analysis needs quarterly. Store both from Yahoo?
3. **Data refresh frequency**: How often re-fetch Yahoo data? (Daily, weekly, monthly?)
4. **yfinance rate limits**: Community reports 2K req/hour safe. What's actual limit?

**Blocking**: None - can proceed with assumptions, adjust later

---

## 11. Related Documents

- **DD-032**: Hybrid Data Sourcing Strategy (Yahoo + SEC decision rationale)
- **DD-031**: SEC Filing Parser Tool Selection (deep analysis parser)
- **data-collector-implementation.md**: Phase C updated to use Yahoo for screening
- **docs/architecture/03-agents-specialist.md**: Screening Agent requirements

---

## 12. Next Steps After Completion

**Immediate**:
1. Update Screening Agent to query Yahoo data (vs waiting for SEC backfill)
2. Implement Human Gate 1 dashboard (display Yahoo metrics)
3. Test screening filters on real Yahoo data

**Phase 2** (after Human Gate 1):
1. Trigger SEC parsing for approved companies (10-20 companies)
2. Compare Yahoo screening data vs SEC deep analysis data (QC validation)
3. Build QC Agent logic to flag Yahoo vs SEC discrepancies

**Estimated Phase 2 Start**: Week 2 (after Yahoo screening validated)
