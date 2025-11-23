# SimFin Data Integration Plan

**Project**: Fundamental Analysis System - Data Collector & Screener
**Version**: 1.0
**Date**: 2025-11-20
**Status**: Planning Phase

## Executive Summary

This plan outlines integration of SimFin as a potential data source for the Screening Agent (Days 1-2 of analysis pipeline). Implementation uses free tier initially for flow validation, with upgrade path to START tier ($15/mo) for production 10Y data requirements.

**Key Decision**: SimFin START tier offers optimal cost/performance balance at $15/month ($9/month annual), providing exactly 10Y historical data needed within $0-$50 budget.

---

## Table of Contents

1. [Background & Context](#1-background--context)
2. [Architecture Overview](#2-architecture-overview)
3. [Implementation Phases](#3-implementation-phases)
4. [Technical Specifications](#4-technical-specifications)
5. [Testing Strategy](#5-testing-strategy)
6. [Deployment & Operations](#6-deployment--operations)
7. [Migration Path](#7-migration-path)
8. [Appendices](#8-appendices)

---

## 1. Background & Context

### 1.1 Problem Statement

**Current State (DD-032)**:

- Status: API provider selection pending
- Fallback: SEC EDGAR

**Requirements**:

- **Metrics**: 10Y revenue CAGR, operating/net margins, ROE/ROA/ROIC, debt ratios, current ratio
- **Universe**: S&P 500 (~500 companies)
- **Performance**: <10 min for full screening
- **Quality**: 95% acceptable
- **Budget**: $0-$50/month

### 1.2 Solution: SimFin

**Why SimFin**:

- START tier: $15/month ($9/month annual) - within budget
- 10Y historical data (exact requirement match)
- 5 req/sec rate limits (S&P 500 in <2 min)
- Local caching (reduces long-term API usage)
- Professional service with good documentation
- 5,000+ US stocks (covers S&P 500 + room for expansion)

**Free Tier Testing**:

- Validate flow before committing to paid subscription
- Free tier: 5Y data, 2 req/sec, 500 high-speed credits/month
- Sufficient for testing with 10-20 companies

---

## 2. Architecture Overview

### 2.1 System Components

```text
┌─────────────────────────────────────────────────────────────┐
│                     Screening Agent                         │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│                Data Collector Layer                         │
│  ┌──────────────────────────────────────────────────────┐  │
│  │   SimFin Client (Primary)                            │  │
│  │   - Fetch fundamentals (income/balance/cash flow)    │  │
│  │   - Local caching                                    │  │
│  │   - Rate limit handling (2-5 req/sec)               │  │
│  └──────────────────────────────────────────────────────┘  │
│                     │                                        │
│                     ▼ (on failure)                          │
│  ┌──────────────────────────────────────────────────────┐  │
│  │   Fallback Manager                                   │  │
│  │   1. Finnhub (free, 60 calls/min)                   │  │
│  │   2. SEC EDGAR (free, 10 req/sec, authoritative)    │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│                Metrics Calculator                           │
│  - Revenue CAGR (5Y → 10Y after upgrade)                   │
│  - Operating/Net Margins (3Y avg)                          │
│  - ROE/ROA/ROIC (3Y avg)                                   │
│  - Debt ratios (Debt/Equity, Net Debt/EBITDA)             │
│  - Liquidity (Current Ratio)                               │
└─────────────────────────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│           Screening Logic & Validation                      │
│  - Completeness check (<5 of 8 metrics → reject)           │
│  - Quality threshold (95% acceptable)                       │
│  - Output: Filtered candidates for Human Gate 1            │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 Data Flow

1. **Screening Agent** requests data for S&P 500 companies
2. **SimFin Client** fetches data (with local cache check first)
3. **Metrics Calculator** computes required ratios
4. **Screening Logic** filters candidates
5. **Fallback Manager** activates if SimFin fails (>3 consecutive errors)

### 2.3 Module Structure

```text
src/
├── data_collector/
│   ├── __init__.py
│   ├── simfin_client.py          # NEW: SimFin API wrapper
│   ├── finnhub_client.py         # NEW: Finnhub fallback
│   ├── edgar_client.py           # NEW: SEC EDGAR fallback
│   ├── fallback_manager.py       # NEW: Failover orchestration
│   └── base_client.py            # NEW: Abstract base class
├── screening/
│   ├── __init__.py
│   ├── metrics_calculator.py     # NEW: Ratio calculations
│   ├── screener.py               # NEW: Filtering logic
│   └── validators.py             # NEW: Data quality checks
├── config/
│   ├── __init__.py
│   └── data_sources.py           # NEW: API configs
└── utils/
    ├── __init__.py
    ├── caching.py                # NEW: Cache helpers
    └── rate_limiter.py           # NEW: Rate limit enforcement
```

---

## 3. Implementation Phases

### Phase 1: Setup & Free Tier Testing (Days 1-2)

**Objective**: Validate SimFin integration flow with free tier before committing to paid subscription.

#### 3.1.1 Account & Dependencies

**Tasks**:

- [ ] Register free SimFin account at simfin.com
- [ ] Generate API key from dashboard
- [ ] Add dependencies: `uv add simfin pandas python-dotenv`
- [ ] Create `.env` file with `SIMFIN_API_KEY=your_key`
- [ ] Add `.env` to `.gitignore`

**Acceptance Criteria**:

- API key successfully authenticates
- Dependencies installed and importable

#### 3.1.2 SimFin Client Implementation

**File**: `src/data_collector/simfin_client.py`

**Features**:

```python
class SimFinClient:
    def __init__(self, api_key: str, cache_dir: str = "./data/cache")
    def fetch_income_statement(self, ticker: str, years: int = 5) -> pd.DataFrame
    def fetch_balance_sheet(self, ticker: str, years: int = 5) -> pd.DataFrame
    def fetch_cash_flow(self, ticker: str, years: int = 5) -> pd.DataFrame
    def fetch_all_fundamentals(self, ticker: str, years: int = 5) -> dict
    def batch_fetch(self, tickers: list[str], years: int = 5) -> dict
```

**Implementation Details**:

- Use `simfin` library's built-in caching (automatic)
- Implement rate limiting: 2 req/sec for free tier
- Retry logic: exponential backoff (1s, 2s, 4s)
- Error handling: specific exceptions for quota exceeded, invalid ticker, etc.

**Code Skeleton**:

```python
import simfin as sf
from simfin.names import *
import pandas as pd
from ratelimit import limits, sleep_and_retry
import logging

class SimFinClient:
    def __init__(self, api_key: str, cache_dir: str = "./data/cache"):
        sf.set_api_key(api_key)
        sf.set_data_dir(cache_dir)
        self.logger = logging.getLogger(__name__)

    @sleep_and_retry
    @limits(calls=2, period=1)  # 2 req/sec for free tier
    def fetch_income_statement(self, ticker: str, years: int = 5) -> pd.DataFrame:
        """Fetch income statement with rate limiting."""
        try:
            # SimFin automatically caches locally
            df = sf.load_income(variant='annual', market='us')
            return df.loc[ticker].tail(years)
        except Exception as e:
            self.logger.error(f"Failed to fetch income for {ticker}: {e}")
            raise
```

#### 3.1.3 Metrics Calculator

**File**: `src/screening/metrics_calculator.py`

**Features**:

```python
class MetricsCalculator:
    def calculate_revenue_cagr(self, income_stmt: pd.DataFrame, years: int = 5) -> float
    def calculate_operating_margin(self, income_stmt: pd.DataFrame, avg_years: int = 3) -> float
    def calculate_net_margin(self, income_stmt: pd.DataFrame, avg_years: int = 3) -> float
    def calculate_roe(self, income_stmt: pd.DataFrame, balance_sheet: pd.DataFrame, avg_years: int = 3) -> float
    def calculate_roa(self, income_stmt: pd.DataFrame, balance_sheet: pd.DataFrame, avg_years: int = 3) -> float
    def calculate_roic(self, income_stmt: pd.DataFrame, balance_sheet: pd.DataFrame, avg_years: int = 3) -> float
    def calculate_debt_to_equity(self, balance_sheet: pd.DataFrame) -> float
    def calculate_net_debt_to_ebitda(self, income_stmt: pd.DataFrame, balance_sheet: pd.DataFrame) -> float
    def calculate_current_ratio(self, balance_sheet: pd.DataFrame) -> float
    def calculate_all_metrics(self, ticker: str, fundamentals: dict) -> dict
```

**Formulas**:

- **Revenue CAGR**: `(Revenue_latest / Revenue_N_years_ago)^(1/N) - 1`
- **Operating Margin**: `Operating Income / Revenue`
- **Net Margin**: `Net Income / Revenue`
- **ROE**: `Net Income / Shareholders' Equity`
- **ROA**: `Net Income / Total Assets`
- **ROIC**: `NOPAT / (Total Debt + Total Equity - Cash)`
- **Debt/Equity**: `Total Debt / Total Equity`
- **Net Debt/EBITDA**: `(Total Debt - Cash) / EBITDA`
- **Current Ratio**: `Current Assets / Current Liabilities`

#### 3.1.4 Testing Flow (Free Tier)

**Test Dataset**: 10-20 S&P 500 companies (diverse sectors)

```python
TEST_TICKERS = [
    'AAPL',  # Tech
    'MSFT',  # Tech
    'JNJ',   # Healthcare
    'JPM',   # Financials
    'XOM',   # Energy
    'WMT',   # Consumer
    'PG',    # Consumer
    'V',     # Financials
    'UNH',   # Healthcare
    'HD',    # Retail
]
```

**Test Cases**:

1. **Single Company**: Fetch + calculate metrics for AAPL
2. **Batch Processing**: Process 10 companies sequentially
3. **Cache Validation**: Re-run to verify caching (should be instant)
4. **Rate Limit Testing**: Verify 2 req/sec enforcement
5. **Data Quality**: Validate 95% completeness threshold

**Success Metrics**:

- [ ] All 10 companies processed successfully
- [ ] API calls: ~30 total (3 per company: income/balance/cashflow)
- [ ] Execution time: ~15 seconds (2 req/sec × 30 calls)
- [ ] Cache hit rate on re-run: 100%
- [ ] Data completeness: ≥95%

**Deliverable**: Test report documenting:

- API reliability
- Data quality
- Performance metrics
- Free tier limitations (5Y vs 10Y requirement)

---

### Phase 2: Upgrade to START Tier (Day 3)

**Objective**: Upgrade to START tier for 10Y data and enhanced rate limits.

#### 3.2.1 Subscription & Configuration

**Tasks**:

- [ ] Subscribe to START tier ($15/mo or $9/mo annual)
- [ ] Update rate limiter: 2 req/sec → 5 req/sec
- [ ] Update default years parameter: 5 → 10

**Code Changes**:

```python
# Before (Free Tier)
@limits(calls=2, period=1)  # 2 req/sec

# After (START Tier)
@limits(calls=5, period=1)  # 5 req/sec
```

#### 3.2.2 10Y Metrics Implementation

**Tasks**:

- [ ] Update `calculate_revenue_cagr()` to support 10Y
- [ ] Add 5Y CAGR as additional metric (for comparison)
- [ ] Update screening logic to use 10Y data

**Validation**:

- [ ] Re-run test with 10 companies using 10Y data
- [ ] Compare 5Y vs 10Y CAGR results
- [ ] Verify all historical data available

#### 3.2.3 Full S&P 500 Screening

**Tasks**:

- [ ] Load S&P 500 ticker list (from Wikipedia or static file)
- [ ] Implement batch processing with progress bar
- [ ] Run full screening (~500 companies)

**Expected Performance**:

- API calls: ~1,500 (3 per company)
- Time at 5 req/sec: ~300 seconds (~5 min)
- With caching, subsequent runs: <1 min

---

### Phase 3: Fallback Implementation (Days 4-5)

**Objective**: Add Finnhub and SEC EDGAR as fallback data sources for reliability.

#### 3.3.1 Base Client Interface

**File**: `src/data_collector/base_client.py`

```python
from abc import ABC, abstractmethod
import pandas as pd

class BaseDataClient(ABC):
    @abstractmethod
    def fetch_income_statement(self, ticker: str, years: int) -> pd.DataFrame:
        pass

    @abstractmethod
    def fetch_balance_sheet(self, ticker: str, years: int) -> pd.DataFrame:
        pass

    @abstractmethod
    def fetch_cash_flow(self, ticker: str, years: int) -> pd.DataFrame:
        pass

    @abstractmethod
    def fetch_all_fundamentals(self, ticker: str, years: int) -> dict:
        pass
```

#### 3.3.2 Finnhub Client (Fallback #1)

**File**: `src/data_collector/finnhub_client.py`

**Features**:

- Implements `BaseDataClient` interface
- Rate limit: 60 calls/min (free tier)
- Returns normalized DataFrames (same schema as SimFin)

**Dependencies**: `uv add finnhub-python`

**Code Skeleton**:

```python
import finnhub
from .base_client import BaseDataClient

class FinnhubClient(BaseDataClient):
    def __init__(self, api_key: str):
        self.client = finnhub.Client(api_key=api_key)

    @sleep_and_retry
    @limits(calls=60, period=60)  # 60 calls/min
    def fetch_income_statement(self, ticker: str, years: int = 10) -> pd.DataFrame:
        # Finnhub returns 1 year per call
        # Need multiple calls for multi-year data
        pass
```

#### 3.3.3 SEC EDGAR Client (Fallback #2)

**File**: `src/data_collector/edgar_client.py`

**Features**:

- Implements `BaseDataClient` interface
- Rate limit: 10 req/sec
- Uses `edgartools` or custom XBRL parser (per DD-031)

**Dependencies**: `uv add edgartools`

**Note**: More complex implementation due to XBRL parsing. See DD-031 for multi-tier parser strategy.

#### 3.3.4 Fallback Manager

**File**: `src/data_collector/fallback_manager.py`

**Features**:

```python
class FallbackManager:
    def __init__(self, primary: BaseDataClient, fallbacks: list[BaseDataClient]):
        self.primary = primary
        self.fallbacks = fallbacks
        self.failure_count = 0
        self.failure_threshold = 3

    def fetch_with_fallback(self, ticker: str, years: int = 10) -> dict:
        """Try primary, then fallbacks in order."""
        try:
            return self.primary.fetch_all_fundamentals(ticker, years)
        except Exception as e:
            self.failure_count += 1
            if self.failure_count >= self.failure_threshold:
                self.logger.warning(f"Primary failed {self.failure_count} times, switching to fallback")
                for fallback in self.fallbacks:
                    try:
                        return fallback.fetch_all_fundamentals(ticker, years)
                    except Exception as fb_e:
                        continue
            raise
```

**Failover Logic**:

1. Try SimFin (primary)
2. If 3 consecutive failures → try Finnhub
3. If Finnhub fails → try SEC EDGAR
4. If all fail → raise exception, log for manual review

---

### Phase 4: Production Hardening (Days 6-7)

**Objective**: Error handling, monitoring, and production readiness.

#### 3.4.1 Checkpoint-Based Recovery

**Implement DD-011 checkpoint system**:

```python
class ScreeningCheckpoint:
    def __init__(self, checkpoint_file: str = "./data/checkpoints/screening.json"):
        self.checkpoint_file = checkpoint_file

    def save(self, processed_tickers: list[str], results: dict):
        """Save progress after each company."""
        checkpoint = {
            'timestamp': datetime.now().isoformat(),
            'processed_tickers': processed_tickers,
            'results': results
        }
        with open(self.checkpoint_file, 'w') as f:
            json.dump(checkpoint, f)

    def load(self) -> dict:
        """Resume from last checkpoint."""
        if os.path.exists(self.checkpoint_file):
            with open(self.checkpoint_file, 'r') as f:
                return json.load(f)
        return {'processed_tickers': [], 'results': {}}
```

#### 3.4.2 Monitoring & Alerting

**Metrics to Track**:

- API call count (by source)
- Failure rate (by source)
- Fallback usage rate
- Data completeness rate
- Execution time per company
- Cache hit rate

**Logging**:

```python
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/screening.log'),
        logging.StreamHandler()
    ]
)
```

**Alerts**:

- If fallback usage >10% → investigate SimFin reliability
- If data completeness <95% → data quality issue
- If execution time >10 min → performance issue

#### 3.4.3 Data Quality Validation

**File**: `src/screening/validators.py`

```python
class DataValidator:
    def validate_completeness(self, metrics: dict, required_count: int = 8) -> bool:
        """Reject if <5 of 8 metrics available."""
        available = sum(1 for v in metrics.values() if v is not None)
        return available >= (required_count - 3)  # Allow 3 missing

    def validate_ranges(self, metrics: dict) -> bool:
        """Check for outliers (e.g., margin >100%, negative equity)."""
        if metrics.get('operating_margin', 0) > 1.0:  # >100%
            return False
        if metrics.get('roe', 0) < -1.0 or metrics.get('roe', 0) > 5.0:  # Extreme values
            return False
        return True

    def validate_quality(self, metrics: dict) -> tuple[bool, list[str]]:
        """Run all validations, return (is_valid, errors)."""
        errors = []
        if not self.validate_completeness(metrics):
            errors.append("Insufficient data completeness")
        if not self.validate_ranges(metrics):
            errors.append("Values out of acceptable range")
        return len(errors) == 0, errors
```

#### 3.4.4 Integration Tests

**File**: `tests/integration/test_screening_flow.py`

**Test Cases**:

1. **End-to-End Flow**: Run full screening with 10 companies
2. **Fallback Activation**: Mock SimFin failure, verify Finnhub fallback
3. **Checkpoint Recovery**: Interrupt mid-run, verify resume
4. **Data Quality**: Verify 95% completeness threshold
5. **Performance**: Verify <10 min for 500 companies (with caching)

---

## 4. Technical Specifications

### 4.1 API Rate Limits

| Data Source | Free Tier    | Paid Tier         | Enforcement                     |
| ----------- | ------------ | ----------------- | ------------------------------- |
| SimFin      | 2 req/sec    | 5 req/sec (START) | Client-side (ratelimit library) |
| Finnhub     | 60 calls/min | N/A               | Client-side                     |
| SEC EDGAR   | 10 req/sec   | N/A               | Client-side                     |

### 4.2 Data Schema Normalization

All clients must return data in standardized format:

```python
{
    'income_statement': pd.DataFrame({
        'date': [...],
        'revenue': [...],
        'operating_income': [...],
        'net_income': [...],
        'ebitda': [...]
    }),
    'balance_sheet': pd.DataFrame({
        'date': [...],
        'total_assets': [...],
        'total_equity': [...],
        'total_debt': [...],
        'current_assets': [...],
        'current_liabilities': [...],
        'cash': [...]
    }),
    'cash_flow': pd.DataFrame({
        'date': [...],
        'operating_cf': [...],
        'investing_cf': [...],
        'financing_cf': [...]
    })
}
```

### 4.3 Caching Strategy

**SimFin Built-in Caching**:

- Location: `./data/cache/simfin/`
- Format: Parquet files
- Invalidation: Manual or configurable TTL

**Custom Caching (for fallbacks)**:

- Location: `./data/cache/{source}/`
- Format: JSON or Parquet
- TTL: 24 hours for fundamentals

### 4.4 Error Handling

**Error Types**:

1. **APIError**: Rate limit, quota exceeded, authentication
2. **DataError**: Missing fields, malformed data
3. **NetworkError**: Timeout, connection issues

**Handling Strategy**:

- Retry with exponential backoff (1s, 2s, 4s, 8s)
- Max 3 retries before fallback
- Log all errors for analysis

---

## 5. Testing Strategy

### 5.1 Unit Tests

**Coverage**: Individual functions in isolation

**Files**:

- `tests/unit/test_simfin_client.py`
- `tests/unit/test_metrics_calculator.py`
- `tests/unit/test_validators.py`

**Key Tests**:

- Metric calculations (CAGR, margins, ratios)
- Data normalization
- Validation logic

### 5.2 Integration Tests

**Coverage**: Multi-component interactions

**Files**:

- `tests/integration/test_screening_flow.py`
- `tests/integration/test_fallback_manager.py`

**Key Tests**:

- Full screening flow (API → metrics → validation)
- Fallback activation
- Checkpoint recovery

### 5.3 Performance Tests

**Benchmarks**:

- Single company: <1 second
- 10 companies: <5 seconds (no cache), <1 second (cached)
- 500 companies (S&P 500): <10 min first run, <1 min cached

---

## 6. Deployment & Operations

### 6.1 Configuration Management

**File**: `src/config/data_sources.py`

```python
from pydantic import BaseSettings

class DataSourceConfig(BaseSettings):
    # SimFin
    simfin_api_key: str
    simfin_tier: str = "START"  # FREE, START, BASIC, PRO
    simfin_rate_limit: int = 5  # req/sec

    # Finnhub
    finnhub_api_key: str
    finnhub_rate_limit: int = 60  # calls/min

    # SEC EDGAR
    edgar_user_agent: str  # Required by SEC
    edgar_rate_limit: int = 10  # req/sec

    # General
    cache_dir: str = "./data/cache"
    checkpoint_dir: str = "./data/checkpoints"

    class Config:
        env_file = ".env"
```

### 6.2 Cost Monitoring

**Monthly Budget**:

- SimFin START: $15/month ($9/month if annual)
- Finnhub: $0 (free tier)
- SEC EDGAR: $0 (free)
- **Total**: $15/month

**Cost Optimization**:

- Leverage caching (reduce API calls)
- Run screening weekly (not daily) if budget tight
- Annual payment: saves $72/year ($15 × 12 = $180 vs $9 × 12 = $108)

### 6.3 Maintenance

**Regular Tasks**:

- Monitor API failure logs (weekly)
- Review fallback usage rate (weekly)
- Update S&P 500 ticker list (quarterly)
- Review API cost vs usage (monthly)
- Clear old cache files (monthly)

---

## 7. Migration Path

### 7.1 From Current State (Yahoo Finance)

**Current (DD-032)**:

```text
Primary: Yahoo Finance (yfinance)
Fallback: SEC EDGAR
```

**New**:

```text
Primary: SimFin START
Fallback 1: Finnhub
Fallback 2: SEC EDGAR
```

**Migration Steps**:

1. Implement SimFin (Phase 1-2)
2. Run parallel: SimFin + yfinance for 1 week
3. Compare data quality and reliability
4. Switch primary to SimFin
5. Demote yfinance to Fallback #3 (or remove entirely)

### 7.2 Documentation Updates

**Files to Update**:

- `docs/design-decisions/DD-032_HYBRID_DATA_SOURCING.md`

  - Change: Yahoo Finance → SimFin START
  - Rationale: Reliability issues in 2024
  - Add: Cost analysis ($15/mo justified by reliability)

- `plans/data-collector-screener-scoped.md`

  - Update data source section
  - Add SimFin implementation details

- `CLAUDE.md`
  - Update "Data Sources" section
  - Document SimFin as primary for screening

**New Documents**:

- Create ADR: `docs/design-decisions/DD-033_SIMFIN_PRIMARY_DATA_SOURCE.md`
  - Context: Yahoo Finance reliability issues
  - Decision: SimFin START tier as primary
  - Consequences: $15/mo cost, improved reliability
  - Alternatives considered: Finnhub, FMP, others

---

## 8. Appendices

### 8.1 SimFin API Quick Reference

**Installation**:

```bash
uv add simfin
```

**Basic Usage**:

```python
import simfin as sf
from simfin.names import *

# Setup
sf.set_api_key('your_api_key')
sf.set_data_dir('./data/cache')

# Load data (automatically cached)
df_income = sf.load_income(variant='annual', market='us')
df_balance = sf.load_balance(variant='annual', market='us')
df_cashflow = sf.load_cashflow(variant='annual', market='us')

# Get company data
ticker = 'AAPL'
income_aapl = df_income.loc[ticker]
```

**Documentation**: <https://simfin.readthedocs.io/>

### 8.2 S&P 500 Ticker List

**Source**: Wikipedia (programmatic fetch)

```python
import pandas as pd

url = 'https://en.wikipedia.org/wiki/List_of_S%26P_500_companies'
sp500 = pd.read_html(url)[0]
tickers = sp500['Symbol'].tolist()
```

**Static File**: Save to `data/static/sp500_tickers.csv` for reliability

### 8.3 Unresolved Questions

1. **Annual vs Monthly Payment**: Pay $15/mo or $108/year ($9/mo)?

   - Recommendation: Annual (save $72/year, low risk)

2. **Test Company Selection**: Which 10-20 companies for testing?

   - Recommendation: Diverse sectors + known edge cases

3. **Upgrade Timing**: Test free tier first or go straight to START?

   - Recommendation: Test free tier (1-2 days), then upgrade

4. **Documentation**: Update DD-032 or create new DD-033?

   - Recommendation: Create DD-033 (new decision, not amendment)

5. **yfinance Fate**: Keep as Fallback #3 or remove entirely?

   - Recommendation: Remove (unreliable, 3 fallbacks excessive)

6. **Finnhub Multi-Call**: How many calls per company for 10Y data?

   - Need: Test to determine (may need 10 calls = expensive)

7. **Cache TTL**: How long to cache fundamental data?
   - Recommendation: 24 hours (balance freshness vs API usage)

---

## Sign-Off

**Prepared by**: Claude Code
**Date**: 2025-11-20
**Status**: Ready for Implementation

**Approval Required**:

- [ ] Architecture review
- [ ] Budget approval ($15/mo or $108/year)
- [ ] Security review (API key management)
- [ ] Timeline approval (7 days estimated)
