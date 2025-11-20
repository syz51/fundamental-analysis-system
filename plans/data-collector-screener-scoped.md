# Data Collector Agent: Screener-Scoped Implementation Plan

**Status**: Ready to implement
**Scope**: Minimal viable Data Collector for Screener Agent only
**Phase**: Phase 1 - Foundation (Screening Stage)
**Estimated Timeline**: 7 days
**Dependencies**: PostgreSQL, Redis (operational)
**Deferred**: SEC EDGAR integration (for post-Gate 1 deep analysis)

---

## Implementation Status (as of 2025-11-20)

**Overall Progress**: 0% complete (not started)

**Infrastructure**:

- ✅ PostgreSQL 18.1 operational (port 5432)
- ✅ Redis operational (port 6379)
- ⚠️ **Schema Conflict**: Existing migration `774d9680756d` creates SEC EDGAR tables (`companies`, `filings`, raw financial statements), NOT screening tables
- ❌ Screening-specific tables (`screening_metrics`, `sp500_universe`, `data_sources`) NOT created

**Components Status**:

- ❌ Day 1 (0/3): Dependencies partially installed (Redis exists), migration needed, RedisClient missing
- ❌ Day 2 (0/2): SP500Manager missing, CLI commands missing
- ❌ Day 3 (0/1): YahooFinanceClient missing
- ❌ Day 4 (0/1): ScreeningCalculator missing
- ❌ Day 5 (0/1): StoragePipeline missing
- ❌ Day 6 (0/2): BulkOperations missing, bulk CLI commands missing
- ❌ Day 7 (0/1): DataCollectorAgent missing
- ❌ Testing (0/9): All unit and integration tests missing

**Total**: 0/29 components implemented

**Critical Decision Needed**: Schema coexistence strategy - existing SEC schema should remain for deep analysis (post-Gate 1), new screening schema needed for Days 1-2 pipeline per DD-032 hybrid data approach.

---

## Current Status & Next Steps

### What Exists in Codebase

**Infrastructure** (✅ Operational):

- PostgreSQL 18.1 running on port 5432
- Redis running on port 6379 (L1 cache)
- Docker Compose environment configured
- Database schemas created: `financial_data`, `metadata`, `document_registry`

**Existing Migrations**:

- `774d9680756d_data_collector_schemas.py` - Creates SEC EDGAR-focused tables:
  - `metadata.companies` (generic company registry, not S&P 500 specific)
  - `document_registry.filings` (SEC filings, partitioned by fiscal_year)
  - `financial_data.income_statements`, `balance_sheets`, `cash_flows` (raw statement data, not screening metrics)

**Dependencies** (Partial):

- ✅ `redis>=7.1.0` installed
- ❌ Missing: `yfinance`, `httpx`, `tenacity`, `beautifulsoup4`, `pandas`

### What's Missing (All Day 1-7 Components)

**Day 1 - Infrastructure**:

- ❌ New migration for screening tables (`screening_metrics`, `sp500_universe`, `data_sources`)
- ❌ `src/storage/redis_client.py` (RedisClient class with dedup, rate limiting, ticker changes)
- ❌ Dependencies: yfinance, httpx, tenacity, beautifulsoup4, pandas

**Day 2 - S&P 500 Management**:

- ❌ `src/data_collector/sp500_manager.py` (SP500Manager class)
- ❌ `src/data_collector/__main__.py` (CLI with sp500-refresh command)

**Day 3 - Yahoo Finance Client**:

- ❌ `src/data_collector/yahoo_finance_client.py` (YahooFinanceClient class)

**Day 4 - Metrics Calculator**:

- ❌ `src/data_collector/screening_calculator.py` (ScreeningCalculator, ScreeningMetrics dataclass)

**Day 5 - Storage Pipeline**:

- ❌ `src/data_collector/storage_pipeline.py` (StoragePipeline class)

**Day 6 - Bulk Operations**:

- ❌ `src/data_collector/bulk_operations.py` (BulkOperations class)
- ❌ CLI commands: yahoo-backfill, yahoo-refresh, yahoo-fetch

**Day 7 - Agent Interface**:

- ❌ `src/agents/data_collector/agent.py` (DataCollectorAgent class)

**Testing** (0/9 files):

- ❌ All unit tests (6 files)
- ❌ All integration tests (3 files)

### Immediate Next Steps

**Step 1: Resolve Schema Strategy** (Decision Required)

- **Option A**: Keep both schemas (SEC for deep analysis + screening for Days 1-2)
- **Option B**: Merge schemas (combine into single unified structure)
- **Recommendation**: Option A - Aligns with DD-032 hybrid data approach

**Step 2: Day 1 Implementation** (Start Here)

1. Add missing dependencies to `pyproject.toml`
2. Create new migration `XXXXXX_screening_metrics_schema.py` (separate from SEC schema)
3. Run `alembic upgrade head` to apply
4. Implement `src/storage/redis_client.py`
5. Write tests for RedisClient

**Step 3: Sequential Days 2-7**

- Follow plan sections exactly as written
- Each day builds on previous day's components
- Test each component before proceeding

**Step 4: Integration Testing**

- Backfill 50 tickers (verify >95% success)
- Performance test: 500 tickers <10 min
- Screener query integration

### Estimated Time to Completion

- Day 1: 8-10 hours (migration + RedisClient + tests)
- Days 2-7: 6-8 hours each (40-50 hours total)
- **Total**: 48-60 hours (6-7.5 full days)

---

## 1. Scope Definition

### What Screener Agent Needs (Days 1-2 of Analysis Pipeline)

**Data Requirements**:

- Yahoo Finance API data for S&P 500 (~500 companies)
- 10Y historical financial metrics for quantitative filtering
- Screening-specific calculated metrics (CAGR, averages, ratios)
- 95% data quality acceptable (screening tolerant to minor errors)

**Key Metrics** (from Screener Agent design):

- Revenue CAGR (10Y, 5Y)
- Operating margin (3Y average)
- Net margin (3Y average)
- ROE, ROA, ROIC (3Y averages)
- Debt/Equity ratio (latest)
- Net Debt/EBITDA (latest)
- Current ratio (latest)

**Performance Targets**:

- Fetch time: <10 min for 500 companies
- Storage: PostgreSQL only (no MinIO needed)
- Quality: >95% fetch success rate
- Completeness: Reject incomplete data (no partial metrics)

### What's Explicitly Deferred to Post-Gate 1

**NOT NEEDED for screening**:

- ❌ SEC EDGAR client (qualitative data for deep analysis)
- ❌ Multi-tier filing parser (XBRL parsing for 10-K/10-Q)
- ❌ MinIO/S3 storage (no raw documents to store)
- ❌ QC Agent integration (parse failure escalation)
- ❌ Task queue/priority system (simple sequential processing sufficient)
- ❌ Amendment tracking (screening uses latest data only)
- ❌ Monitoring dashboard (basic logging sufficient for MVP)

---

## 2. Architecture (Simplified)

```text
┌─────────────────────────────────────────────────────────────┐
│         DATA COLLECTOR (Screener-Only Scope)                │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────────────────────────────────────┐          │
│  │   S&P 500 Universe Manager                   │          │
│  │   - Load ticker list (Wikipedia/CSV/API)     │          │
│  │   - Track ticker changes (symbol updates)    │          │
│  │   - Store in metadata.sp500_universe         │          │
│  └────────────────────┬─────────────────────────┘          │
│                       ↓                                      │
│  ┌──────────────────────────────────────────────┐          │
│  │   Yahoo Finance Client                       │          │
│  │   - Bulk fetch S&P 500 (yfinance library)    │          │
│  │   - Rate limiting: 2 req/sec (Redis-backed)  │          │
│  │   - Retry logic: 3 attempts, exp backoff     │          │
│  │   - Fetch: annual + quarterly financials     │          │
│  └────────────────────┬─────────────────────────┘          │
│                       ↓                                      │
│  ┌──────────────────────────────────────────────┐          │
│  │   Screening Metrics Calculator               │          │
│  │   - 10Y/5Y CAGR from revenue series          │          │
│  │   - 3Y averages (margins, ROE/ROA/ROIC)      │          │
│  │   - Latest ratios (debt, liquidity)          │          │
│  │   - Completeness validation (reject partial) │          │
│  └────────────────────┬─────────────────────────┘          │
│                       ↓                                      │
│  ┌──────────────────────────────────────────────┐          │
│  │   Storage Pipeline                           │          │
│  │   1. Check Redis dedup (skip if <24h)        │          │
│  │   2. Fetch from Yahoo Finance                │          │
│  │   3. Calculate screening metrics             │          │
│  │   4. Validate completeness (5/8 minimum)     │          │
│  │   5. Insert → PostgreSQL                     │          │
│  │   6. Cache key → Redis (24hr TTL)            │          │
│  └────────────────────┬─────────────────────────┘          │
│                       ↓                                      │
│  ┌─────────────────────────────────────────────┐           │
│  │  PostgreSQL                   Redis L1       │           │
│  │  - screening_metrics         - Dedup cache  │           │
│  │  - data_sources              - Rate limits  │           │
│  │  - sp500_universe            - 24hr TTL     │           │
│  └─────────────────────────────────────────────┘           │
│                                                              │
└─────────────────────────────────────────────────────────────┘
         ↓
    [Screener Agent]
    Query screening_metrics table
```

---

## 3. PostgreSQL Schema (Screening-Specific)

### A. financial_data.screening_metrics (Core Table)

**Purpose**: Store calculated screening metrics for each company

```sql
CREATE TABLE financial_data.screening_metrics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    ticker VARCHAR(10) NOT NULL,
    data_source VARCHAR(20) DEFAULT 'yahoo_finance',
    period_type VARCHAR(10) NOT NULL,  -- 'annual' or 'quarterly'

    -- Growth metrics
    revenue_cagr_10y NUMERIC,  -- 10-year compound annual growth rate
    revenue_cagr_5y NUMERIC,   -- 5-year compound annual growth rate

    -- Profitability (3-year averages)
    operating_margin_3y_avg NUMERIC,  -- Operating income / revenue
    net_margin_3y_avg NUMERIC,        -- Net income / revenue

    -- Returns on capital (3-year averages)
    roe_3y_avg NUMERIC,   -- Return on equity
    roa_3y_avg NUMERIC,   -- Return on assets
    roic_3y_avg NUMERIC,  -- Return on invested capital

    -- Leverage & liquidity (latest values)
    debt_to_equity NUMERIC,      -- Total debt / total equity
    net_debt_to_ebitda NUMERIC,  -- (Total debt - cash) / EBITDA
    current_ratio NUMERIC,       -- Current assets / current liabilities

    -- Metadata
    as_of_date DATE NOT NULL,         -- Date metrics calculated
    fetched_at TIMESTAMP DEFAULT NOW(),

    -- Indexes for Screener Agent queries
    INDEX idx_screening_ticker (ticker),
    INDEX idx_screening_date (as_of_date),
    UNIQUE(ticker, as_of_date, data_source, period_type)
);
```

**Rationale**:

- Denormalized for fast Screener queries (no joins required)
- Stores both annual + quarterly for flexibility
- UNIQUE constraint prevents duplicate fetches

### B. document_registry.data_sources (Tracking Table)

**Purpose**: Track fetch success/failure for monitoring

```sql
CREATE TABLE document_registry.data_sources (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    ticker VARCHAR(10) NOT NULL,
    source_type VARCHAR(20) NOT NULL,  -- 'yahoo_finance'
    fetch_status VARCHAR(20) NOT NULL,  -- 'SUCCESS', 'FAILED', 'PARTIAL'
    error_message TEXT,                 -- Error details if failed
    records_inserted INT DEFAULT 0,     -- Number of metrics inserted
    fetched_at TIMESTAMP DEFAULT NOW(),

    INDEX idx_sources_ticker (ticker),
    INDEX idx_sources_status (fetch_status)
);
```

**Rationale**:

- Monitor Yahoo Finance API reliability
- Track which tickers failed for retry
- Debugging aid for data quality issues

### C. metadata.sp500_universe (Ticker List)

**Purpose**: Maintain S&P 500 ticker list with change tracking

```sql
CREATE TABLE metadata.sp500_universe (
    ticker VARCHAR(10) PRIMARY KEY,
    company_name VARCHAR(255) NOT NULL,
    gics_sector VARCHAR(50),              -- For Phase 2 sector weighting
    gics_sub_industry VARCHAR(100),
    added_to_index DATE,                  -- When added to S&P 500
    is_active BOOLEAN DEFAULT TRUE,       -- FALSE if removed from index
    previous_ticker VARCHAR(10),          -- For ticker changes (e.g., FB → META)
    ticker_changed_date DATE,             -- When ticker changed
    last_updated TIMESTAMP DEFAULT NOW(),

    INDEX idx_sp500_sector (gics_sector),
    INDEX idx_sp500_active (is_active)
);
```

**Rationale**:

- Track S&P 500 composition changes over time
- Handle ticker symbol changes (FB → META, GOOGL split)
- Support Phase 2 sector-weighted screening

### Redis Key Patterns

**1. Deduplication Cache** (24hr TTL)

```python
# Key: data:fetch:{ticker}:{date}
# Value: "fetched"
# TTL: 86400 seconds (24 hours)

# Example: data:fetch:AAPL:2025-11-20 → "fetched"
```

**2. Rate Limiting** (2 sec TTL)

```python
# Key: rate_limit:yahoo:{second}
# Value: request_count (integer)
# TTL: 2 seconds

# Example: rate_limit:yahoo:1732071234 → 2
```

**3. Ticker Change Cache** (7 day TTL)

```python
# Key: ticker:current:{old_ticker}
# Value: new_ticker
# TTL: 604800 seconds (7 days)

# Example: ticker:current:FB → META
```

---

## 4. Implementation Steps (7-Day Breakdown)

### Day 1: Infrastructure Setup ❌ NOT STARTED

**A. Dependencies** (`pyproject.toml`)

**Status**: Partially complete

- ✅ `redis>=7.1.0` (already installed)
- ✅ `asyncpg`, `sqlalchemy`, `alembic` (already installed)
- ❌ Need to add: `yfinance`, `httpx`, `tenacity`, `beautifulsoup4`, `pandas`

```toml
[project.dependencies]
# Already exists:
# asyncpg = ">=0.30.0"
# sqlalchemy = ">=2.0.44"
# alembic = ">=1.17.2"
# redis = ">=7.1.0"  # ✅ Already installed

# Add these:
yfinance = ">=0.2.0"        # Yahoo Finance API client
httpx = ">=0.25.0"          # Async HTTP for Wikipedia scraping
tenacity = ">=8.0.0"        # Retry logic decorator
beautifulsoup4 = ">=4.12.0" # HTML parsing for Wikipedia
pandas = ">=2.0.0"          # DataFrames for yfinance data
```

**B. Database Migrations** (`alembic revision`)

Create new migration: `src/storage/migrations/versions/XXXXXX_screening_metrics_schema.py`

```python
"""screening_metrics_schema

Revision ID: XXXXXX
Revises: 889bef0a0a43 (current latest)
Create Date: 2025-11-20
"""

def upgrade() -> None:
    # Create financial_data.screening_metrics table
    op.execute("""
    CREATE TABLE IF NOT EXISTS financial_data.screening_metrics (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        ticker VARCHAR(10) NOT NULL,
        data_source VARCHAR(20) DEFAULT 'yahoo_finance',
        period_type VARCHAR(10) NOT NULL,
        revenue_cagr_10y NUMERIC,
        revenue_cagr_5y NUMERIC,
        operating_margin_3y_avg NUMERIC,
        net_margin_3y_avg NUMERIC,
        roe_3y_avg NUMERIC,
        roa_3y_avg NUMERIC,
        roic_3y_avg NUMERIC,
        debt_to_equity NUMERIC,
        net_debt_to_ebitda NUMERIC,
        current_ratio NUMERIC,
        as_of_date DATE NOT NULL,
        fetched_at TIMESTAMP DEFAULT NOW(),
        UNIQUE(ticker, as_of_date, data_source, period_type)
    )
    """)

    op.execute("CREATE INDEX idx_screening_ticker ON financial_data.screening_metrics(ticker)")
    op.execute("CREATE INDEX idx_screening_date ON financial_data.screening_metrics(as_of_date)")

    # Create metadata.sp500_universe table
    op.execute("""
    CREATE TABLE IF NOT EXISTS metadata.sp500_universe (
        ticker VARCHAR(10) PRIMARY KEY,
        company_name VARCHAR(255) NOT NULL,
        gics_sector VARCHAR(50),
        gics_sub_industry VARCHAR(100),
        added_to_index DATE,
        is_active BOOLEAN DEFAULT TRUE,
        previous_ticker VARCHAR(10),
        ticker_changed_date DATE,
        last_updated TIMESTAMP DEFAULT NOW()
    )
    """)

    op.execute("CREATE INDEX idx_sp500_sector ON metadata.sp500_universe(gics_sector)")
    op.execute("CREATE INDEX idx_sp500_active ON metadata.sp500_universe(is_active)")

def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS financial_data.screening_metrics CASCADE")
    op.execute("DROP TABLE IF EXISTS metadata.sp500_universe CASCADE")
```

**C. Redis Client** (`src/storage/redis_client.py`)

```python
"""Redis L1 client for deduplication and rate limiting."""

import logging
from typing import Optional
import redis.asyncio as redis

logger = logging.getLogger(__name__)

class RedisClient:
    """Async Redis client for Data Collector caching."""

    def __init__(self, redis_url: str = "redis://localhost:6379/0"):
        """Initialize Redis connection pool.

        Args:
            redis_url: Redis connection URL
        """
        self.client = redis.from_url(
            redis_url,
            encoding="utf-8",
            decode_responses=True,
            max_connections=10
        )

    async def close(self) -> None:
        """Close Redis connection pool."""
        await self.client.close()

    # ========== Deduplication ==========

    async def check_fetch_cached(self, ticker: str, date: str) -> bool:
        """Check if ticker data already fetched today.

        Args:
            ticker: Stock ticker
            date: Date string (YYYY-MM-DD)

        Returns:
            True if cached, False otherwise
        """
        key = f"data:fetch:{ticker}:{date}"
        return await self.client.exists(key) > 0

    async def mark_fetch_cached(self, ticker: str, date: str, ttl: int = 86400) -> None:
        """Mark ticker as fetched (24hr default TTL).

        Args:
            ticker: Stock ticker
            date: Date string (YYYY-MM-DD)
            ttl: Time to live in seconds (default 24 hours)
        """
        key = f"data:fetch:{ticker}:{date}"
        await self.client.set(key, "fetched", ex=ttl)

    # ========== Rate Limiting ==========

    async def check_rate_limit(self, source: str, limit: int) -> bool:
        """Check if rate limit allows request.

        Args:
            source: Data source ('yahoo', 'sec')
            limit: Max requests per second

        Returns:
            True if request allowed, False if rate limited
        """
        import time
        current_second = int(time.time())
        key = f"rate_limit:{source}:{current_second}"

        count = await self.client.incr(key)
        if count == 1:
            await self.client.expire(key, 2)  # Expire after 2 seconds

        return count <= limit

    async def wait_for_rate_limit(self, source: str, limit: int) -> None:
        """Block until rate limit allows request.

        Args:
            source: Data source
            limit: Max requests per second
        """
        import asyncio
        while not await self.check_rate_limit(source, limit):
            await asyncio.sleep(0.1)  # Wait 100ms and retry

    # ========== Ticker Changes ==========

    async def get_current_ticker(self, old_ticker: str) -> Optional[str]:
        """Get current ticker if symbol changed.

        Args:
            old_ticker: Historical ticker symbol

        Returns:
            Current ticker or None if not changed
        """
        key = f"ticker:current:{old_ticker}"
        return await self.client.get(key)

    async def cache_ticker_change(
        self,
        old_ticker: str,
        new_ticker: str,
        ttl: int = 604800
    ) -> None:
        """Cache ticker symbol change (7 day default TTL).

        Args:
            old_ticker: Old ticker symbol
            new_ticker: New ticker symbol
            ttl: Time to live in seconds (default 7 days)
        """
        key = f"ticker:current:{old_ticker}"
        await self.client.set(key, new_ticker, ex=ttl)
```

**Testing**:

- `tests/storage/test_redis_client.py`:
  - Test dedup cache (set/get, TTL expiry)
  - Test rate limiting (verify blocks after limit)
  - Test ticker change cache
- Integration: Connect to real Redis, verify operations

**Deliverable**: ✅ Redis client operational, migrations applied, dependencies installed

---

### Day 2: S&P 500 Universe Management ❌ NOT STARTED

**A. S&P 500 Manager** (`src/data_collector/sp500_manager.py`)

```python
"""S&P 500 universe management with ticker change tracking."""

import logging
from datetime import date
from typing import Optional

import httpx
from bs4 import BeautifulSoup

from src.storage.postgres_client import PostgresClient
from src.storage.redis_client import RedisClient

logger = logging.getLogger(__name__)

class SP500Manager:
    """Manage S&P 500 ticker list and changes."""

    def __init__(self, postgres: PostgresClient, redis: RedisClient):
        """Initialize S&P 500 manager.

        Args:
            postgres: PostgreSQL client
            redis: Redis client
        """
        self.postgres = postgres
        self.redis = redis

    async def load_sp500_list(self, source: str = "wikipedia") -> list[dict]:
        """Load S&P 500 ticker list from source.

        Args:
            source: Data source ('wikipedia', 'csv_file', 'api')

        Returns:
            List of dicts with ticker, company_name, sector

        Raises:
            ValueError: If source not supported
        """
        if source == "wikipedia":
            return await self._load_from_wikipedia()
        elif source == "csv_file":
            return await self._load_from_csv()
        elif source == "api":
            return await self._load_from_api()
        else:
            raise ValueError(f"Unsupported source: {source}")

    async def _load_from_wikipedia(self) -> list[dict]:
        """Scrape S&P 500 list from Wikipedia.

        Returns:
            List of company dicts
        """
        url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"

        async with httpx.AsyncClient() as client:
            response = await client.get(url, timeout=30.0)
            response.raise_for_status()

        soup = BeautifulSoup(response.text, 'html.parser')
        table = soup.find('table', {'id': 'constituents'})

        if not table:
            raise RuntimeError("Wikipedia table structure changed")

        companies = []
        rows = table.find_all('tr')[1:]  # Skip header

        for row in rows:
            cols = row.find_all('td')
            if len(cols) >= 4:
                companies.append({
                    'ticker': cols[0].text.strip(),
                    'company_name': cols[1].text.strip(),
                    'gics_sector': cols[2].text.strip(),
                    'gics_sub_industry': cols[3].text.strip()
                })

        logger.info(f"Loaded {len(companies)} companies from Wikipedia")
        return companies

    async def _load_from_csv(self, file_path: str = "data/sp500.csv") -> list[dict]:
        """Load S&P 500 from CSV file.

        Args:
            file_path: Path to CSV file

        Returns:
            List of company dicts
        """
        import csv
        companies = []

        with open(file_path, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                companies.append({
                    'ticker': row['ticker'],
                    'company_name': row['company_name'],
                    'gics_sector': row.get('gics_sector', ''),
                    'gics_sub_industry': row.get('gics_sub_industry', '')
                })

        logger.info(f"Loaded {len(companies)} companies from CSV")
        return companies

    async def _load_from_api(self) -> list[dict]:
        """Load S&P 500 from external API.

        NOTE: Placeholder for future API integration (e.g., SlickCharts, DataHub)

        Returns:
            List of company dicts
        """
        raise NotImplementedError("API source not yet implemented")

    async def populate_universe(self, companies: list[dict]) -> None:
        """Populate metadata.sp500_universe table.

        Args:
            companies: List of company dicts from load_sp500_list()
        """
        async with self.postgres.session() as session:
            for company in companies:
                await session.execute(
                    """
                    INSERT INTO metadata.sp500_universe (
                        ticker, company_name, gics_sector, gics_sub_industry,
                        added_to_index, is_active, last_updated
                    )
                    VALUES (:ticker, :company_name, :gics_sector, :gics_sub_industry,
                            CURRENT_DATE, TRUE, NOW())
                    ON CONFLICT (ticker) DO UPDATE SET
                        company_name = EXCLUDED.company_name,
                        gics_sector = EXCLUDED.gics_sector,
                        gics_sub_industry = EXCLUDED.gics_sub_industry,
                        last_updated = NOW()
                    """,
                    {
                        'ticker': company['ticker'],
                        'company_name': company['company_name'],
                        'gics_sector': company.get('gics_sector', ''),
                        'gics_sub_industry': company.get('gics_sub_industry', '')
                    }
                )

        logger.info(f"Populated {len(companies)} companies in sp500_universe")

    async def handle_ticker_change(
        self,
        old_ticker: str,
        new_ticker: str,
        change_date: date
    ) -> None:
        """Handle ticker symbol change (e.g., FB → META).

        Args:
            old_ticker: Old ticker symbol
            new_ticker: New ticker symbol
            change_date: Date of change
        """
        # Update PostgreSQL
        async with self.postgres.session() as session:
            await session.execute(
                """
                INSERT INTO metadata.sp500_universe (
                    ticker, previous_ticker, ticker_changed_date, is_active, last_updated
                )
                VALUES (:new_ticker, :old_ticker, :change_date, TRUE, NOW())
                ON CONFLICT (ticker) DO UPDATE SET
                    previous_ticker = EXCLUDED.previous_ticker,
                    ticker_changed_date = EXCLUDED.ticker_changed_date,
                    last_updated = NOW()
                """,
                {
                    'new_ticker': new_ticker,
                    'old_ticker': old_ticker,
                    'change_date': change_date
                }
            )

            # Deactivate old ticker
            await session.execute(
                """
                UPDATE metadata.sp500_universe
                SET is_active = FALSE, last_updated = NOW()
                WHERE ticker = :old_ticker
                """,
                {'old_ticker': old_ticker}
            )

        # Cache in Redis
        await self.redis.cache_ticker_change(old_ticker, new_ticker)

        logger.info(f"Ticker change: {old_ticker} → {new_ticker}")

    async def get_active_tickers(self) -> list[str]:
        """Get list of active S&P 500 tickers.

        Returns:
            List of ticker symbols
        """
        async with self.postgres.session() as session:
            result = await session.execute(
                """
                SELECT ticker FROM metadata.sp500_universe
                WHERE is_active = TRUE
                ORDER BY ticker
                """
            )
            return [row[0] for row in result.fetchall()]

    async def resolve_ticker(self, ticker: str) -> Optional[str]:
        """Resolve ticker to current symbol if changed.

        Args:
            ticker: Ticker symbol (possibly old)

        Returns:
            Current ticker symbol or None if not found
        """
        # Check Redis cache first
        current = await self.redis.get_current_ticker(ticker)
        if current:
            return current

        # Check PostgreSQL
        async with self.postgres.session() as session:
            result = await session.execute(
                """
                SELECT ticker FROM metadata.sp500_universe
                WHERE previous_ticker = :old_ticker AND is_active = TRUE
                """,
                {'old_ticker': ticker}
            )
            row = result.fetchone()
            if row:
                new_ticker = row[0]
                await self.redis.cache_ticker_change(ticker, new_ticker)
                return new_ticker

        return None
```

**B. CLI Command** (`src/data_collector/__main__.py`)

```python
"""CLI commands for data collector agent."""

import asyncio
import click

from src.storage.postgres_client import PostgresClient
from src.storage.redis_client import RedisClient
from src.data_collector.sp500_manager import SP500Manager

@click.group()
def cli():
    """Data Collector Agent CLI."""
    pass

@cli.command()
@click.option('--source', default='wikipedia', help='Data source (wikipedia, csv_file, api)')
async def sp500_refresh(source: str):
    """Refresh S&P 500 ticker list."""
    postgres = PostgresClient()
    redis = RedisClient()
    manager = SP500Manager(postgres, redis)

    try:
        click.echo(f"Loading S&P 500 from {source}...")
        companies = await manager.load_sp500_list(source)

        click.echo(f"Populating {len(companies)} companies...")
        await manager.populate_universe(companies)

        click.echo("✅ S&P 500 universe updated")
    finally:
        await postgres.close()
        await redis.close()

if __name__ == '__main__':
    cli()
```

**Usage**:

```bash
python -m src.data_collector sp500-refresh --source wikipedia
```

**Testing**:

- Unit tests: Wikipedia scraping, CSV parsing
- Integration tests: Load + populate, verify 500 tickers in DB
- Ticker change tests: FB → META resolution

**Deliverable**: ✅ S&P 500 list loaded in PostgreSQL, ticker resolution working

---

### Day 3: Yahoo Finance Client ❌ NOT STARTED

**A. Yahoo Finance Client** (`src/data_collector/yahoo_finance_client.py`)

```python
"""Yahoo Finance API client with rate limiting."""

import logging
from typing import Any, Optional

import yfinance as yf
from tenacity import retry, stop_after_attempt, wait_exponential

from src.storage.redis_client import RedisClient

logger = logging.getLogger(__name__)

class YahooFinanceClient:
    """Async Yahoo Finance API client."""

    def __init__(self, redis: RedisClient, rate_limit: int = 2):
        """Initialize Yahoo Finance client.

        Args:
            redis: Redis client for rate limiting
            rate_limit: Max requests per second (default 2)
        """
        self.redis = redis
        self.rate_limit = rate_limit

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        reraise=True
    )
    async def get_financials(self, ticker: str) -> dict[str, Any]:
        """Fetch financial statements for ticker.

        Args:
            ticker: Stock ticker symbol

        Returns:
            Dict with keys: 'income_statement', 'balance_sheet', 'cash_flow', 'quarterly'

        Raises:
            ValueError: If ticker not found
            RuntimeError: If Yahoo Finance API fails
        """
        # Rate limiting
        await self.redis.wait_for_rate_limit('yahoo', self.rate_limit)

        try:
            stock = yf.Ticker(ticker)

            return {
                'income_statement': stock.financials,          # Annual (DataFrame)
                'balance_sheet': stock.balance_sheet,          # Annual
                'cash_flow': stock.cashflow,                   # Annual
                'quarterly_income': stock.quarterly_financials, # Quarterly
                'quarterly_balance': stock.quarterly_balance_sheet,
                'quarterly_cashflow': stock.quarterly_cashflow,
                'info': stock.info                              # Company metadata
            }
        except Exception as e:
            logger.error(f"Yahoo Finance fetch failed for {ticker}: {e}")
            raise RuntimeError(f"Yahoo Finance API error: {e}") from e

    async def get_sp500_financials(self, tickers: list[str]) -> dict[str, dict]:
        """Bulk fetch S&P 500 financial data.

        Args:
            tickers: List of ticker symbols

        Returns:
            Dict mapping ticker to financial data (or error)
        """
        results = {}

        for i, ticker in enumerate(tickers):
            try:
                logger.info(f"Fetching {ticker} ({i+1}/{len(tickers)})")
                results[ticker] = await self.get_financials(ticker)
            except Exception as e:
                logger.error(f"Failed to fetch {ticker}: {e}")
                results[ticker] = {'error': str(e)}

        success_count = sum(1 for v in results.values() if 'error' not in v)
        logger.info(f"Bulk fetch complete: {success_count}/{len(tickers)} successful")

        return results
```

**Testing**:

- Unit tests: Mock yfinance responses
- Integration tests: Fetch 5 real tickers (AAPL, MSFT, GOOGL, JPM, WMT)
- Rate limit tests: 10 requests, verify 2/sec limit
- Error tests: Invalid ticker, API timeout

**Deliverable**: ✅ Yahoo Finance client operational, rate limiting working

---

### Day 4: Screening Metrics Calculator ❌ NOT STARTED

**A. Metrics Calculator** (`src/data_collector/screening_calculator.py`)

```python
"""Calculate screening metrics from Yahoo Finance data."""

import logging
from dataclasses import dataclass
from datetime import date
from typing import Optional

import pandas as pd

logger = logging.getLogger(__name__)

@dataclass
class ScreeningMetrics:
    """Calculated screening metrics."""

    ticker: str
    period_type: str  # 'annual' or 'quarterly'
    as_of_date: date

    # Growth
    revenue_cagr_10y: Optional[float]
    revenue_cagr_5y: Optional[float]

    # Profitability
    operating_margin_3y_avg: Optional[float]
    net_margin_3y_avg: Optional[float]

    # Returns
    roe_3y_avg: Optional[float]
    roa_3y_avg: Optional[float]
    roic_3y_avg: Optional[float]

    # Leverage & liquidity
    debt_to_equity: Optional[float]
    net_debt_to_ebitda: Optional[float]
    current_ratio: Optional[float]

    def is_complete(self, min_metrics: int = 5) -> bool:
        """Check if metrics are complete enough for screening.

        Args:
            min_metrics: Minimum number of non-None metrics required

        Returns:
            True if at least min_metrics are present
        """
        metrics = [
            self.revenue_cagr_10y,
            self.operating_margin_3y_avg,
            self.net_margin_3y_avg,
            self.roe_3y_avg,
            self.roa_3y_avg,
            self.roic_3y_avg,
            self.debt_to_equity,
            self.current_ratio
        ]

        non_null_count = sum(1 for m in metrics if m is not None)
        return non_null_count >= min_metrics

class ScreeningCalculator:
    """Calculate screening metrics from Yahoo Finance data."""

    @staticmethod
    def calculate_cagr(start_value: float, end_value: float, years: int) -> Optional[float]:
        """Calculate compound annual growth rate.

        Args:
            start_value: Starting value
            end_value: Ending value
            years: Number of years

        Returns:
            CAGR as decimal (e.g., 0.15 for 15%) or None if invalid
        """
        if start_value <= 0 or end_value <= 0 or years <= 0:
            return None

        return (end_value / start_value) ** (1 / years) - 1

    @staticmethod
    def calculate_average(series: pd.Series, periods: int = 3) -> Optional[float]:
        """Calculate average of most recent periods.

        Args:
            series: Pandas Series with time-ordered data
            periods: Number of periods to average

        Returns:
            Average value or None if insufficient data
        """
        if len(series) < periods:
            return None

        return float(series.head(periods).mean())

    @staticmethod
    def calculate_metrics(
        financials: dict,
        ticker: str,
        as_of_date: date
    ) -> ScreeningMetrics:
        """Calculate screening metrics from Yahoo Finance data.

        Args:
            financials: Dict from YahooFinanceClient.get_financials()
            ticker: Stock ticker
            as_of_date: Date of calculation

        Returns:
            ScreeningMetrics object
        """
        income = financials['income_statement']
        balance = financials['balance_sheet']
        cashflow = financials['cash_flow']

        # Revenue CAGR
        revenue = income.loc['Total Revenue'] if 'Total Revenue' in income.index else None
        revenue_cagr_10y = None
        revenue_cagr_5y = None

        if revenue is not None and len(revenue) >= 5:
            revenue_latest = revenue.iloc[0]  # Most recent

            if len(revenue) >= 10:
                revenue_10y_ago = revenue.iloc[9]
                revenue_cagr_10y = ScreeningCalculator.calculate_cagr(
                    revenue_10y_ago, revenue_latest, 10
                )

            revenue_5y_ago = revenue.iloc[min(4, len(revenue)-1)]
            revenue_cagr_5y = ScreeningCalculator.calculate_cagr(
                revenue_5y_ago, revenue_latest, 5
            )

        # Operating margin (3Y avg)
        operating_income = income.loc['Operating Income'] if 'Operating Income' in income.index else None
        operating_margin_3y_avg = None

        if operating_income is not None and revenue is not None:
            margin_series = (operating_income / revenue)[:3]
            operating_margin_3y_avg = ScreeningCalculator.calculate_average(margin_series, 3)

        # Net margin (3Y avg)
        net_income = income.loc['Net Income'] if 'Net Income' in income.index else None
        net_margin_3y_avg = None

        if net_income is not None and revenue is not None:
            margin_series = (net_income / revenue)[:3]
            net_margin_3y_avg = ScreeningCalculator.calculate_average(margin_series, 3)

        # ROE (3Y avg)
        equity = balance.loc['Total Stockholder Equity'] if 'Total Stockholder Equity' in balance.index else None
        roe_3y_avg = None

        if net_income is not None and equity is not None:
            roe_series = (net_income / equity)[:3]
            roe_3y_avg = ScreeningCalculator.calculate_average(roe_series, 3)

        # ROA (3Y avg)
        assets = balance.loc['Total Assets'] if 'Total Assets' in balance.index else None
        roa_3y_avg = None

        if net_income is not None and assets is not None:
            roa_series = (net_income / assets)[:3]
            roa_3y_avg = ScreeningCalculator.calculate_average(roa_series, 3)

        # ROIC (3Y avg) - simplified as (Net Income - Dividends) / (Debt + Equity)
        total_debt = balance.loc['Total Debt'] if 'Total Debt' in balance.index else None
        roic_3y_avg = None

        if net_income is not None and equity is not None and total_debt is not None:
            invested_capital = equity + total_debt
            roic_series = (net_income / invested_capital)[:3]
            roic_3y_avg = ScreeningCalculator.calculate_average(roic_series, 3)

        # Debt/Equity (latest)
        debt_to_equity = None
        if total_debt is not None and equity is not None:
            debt_latest = total_debt.iloc[0]
            equity_latest = equity.iloc[0]
            if equity_latest != 0:
                debt_to_equity = float(debt_latest / equity_latest)

        # Net Debt/EBITDA (latest)
        cash = balance.loc['Cash'] if 'Cash' in balance.index else None
        ebitda = income.loc['EBITDA'] if 'EBITDA' in income.index else None
        net_debt_to_ebitda = None

        if total_debt is not None and cash is not None and ebitda is not None:
            net_debt = total_debt.iloc[0] - cash.iloc[0]
            ebitda_latest = ebitda.iloc[0]
            if ebitda_latest != 0:
                net_debt_to_ebitda = float(net_debt / ebitda_latest)

        # Current ratio (latest)
        current_assets = balance.loc['Current Assets'] if 'Current Assets' in balance.index else None
        current_liabilities = balance.loc['Current Liabilities'] if 'Current Liabilities' in balance.index else None
        current_ratio = None

        if current_assets is not None and current_liabilities is not None:
            ca_latest = current_assets.iloc[0]
            cl_latest = current_liabilities.iloc[0]
            if cl_latest != 0:
                current_ratio = float(ca_latest / cl_latest)

        return ScreeningMetrics(
            ticker=ticker,
            period_type='annual',
            as_of_date=as_of_date,
            revenue_cagr_10y=revenue_cagr_10y,
            revenue_cagr_5y=revenue_cagr_5y,
            operating_margin_3y_avg=operating_margin_3y_avg,
            net_margin_3y_avg=net_margin_3y_avg,
            roe_3y_avg=roe_3y_avg,
            roa_3y_avg=roa_3y_avg,
            roic_3y_avg=roic_3y_avg,
            debt_to_equity=debt_to_equity,
            net_debt_to_ebitda=net_debt_to_ebitda,
            current_ratio=current_ratio
        )
```

**Testing**:

- Unit tests: CAGR calculation, average calculation
- Integration tests: Calculate metrics for AAPL, verify against manual calculations
- Edge cases: Missing data, zero values, negative equity

**Deliverable**: ✅ Metrics calculator operational, completeness validation working

---

### Day 5: Storage Pipeline ❌ NOT STARTED

**A. Storage Pipeline** (`src/data_collector/storage_pipeline.py`)

```python
"""Storage pipeline for screening data."""

import logging
from datetime import date

from src.data_collector.yahoo_finance_client import YahooFinanceClient
from src.data_collector.screening_calculator import ScreeningCalculator, ScreeningMetrics
from src.storage.postgres_client import PostgresClient
from src.storage.redis_client import RedisClient

logger = logging.getLogger(__name__)

class StoragePipeline:
    """Orchestrate fetch → calculate → validate → store."""

    def __init__(
        self,
        yahoo_client: YahooFinanceClient,
        postgres: PostgresClient,
        redis: RedisClient
    ):
        """Initialize storage pipeline.

        Args:
            yahoo_client: Yahoo Finance API client
            postgres: PostgreSQL client
            redis: Redis client
        """
        self.yahoo = yahoo_client
        self.postgres = postgres
        self.redis = redis
        self.calculator = ScreeningCalculator()

    async def process_ticker(self, ticker: str, today: date) -> dict:
        """Process single ticker through pipeline.

        Args:
            ticker: Stock ticker symbol
            today: Date for as_of_date and cache key

        Returns:
            Dict with status: 'success', 'failed', or 'skipped'
        """
        # Step 1: Check Redis deduplication
        if await self.redis.check_fetch_cached(ticker, str(today)):
            logger.info(f"{ticker}: Skipped (cached < 24hr)")
            return {'status': 'skipped', 'reason': 'cached'}

        try:
            # Step 2: Fetch from Yahoo Finance
            logger.info(f"{ticker}: Fetching from Yahoo Finance")
            financials = await self.yahoo.get_financials(ticker)

            if 'error' in financials:
                await self._log_failure(ticker, 'yahoo_finance', financials['error'])
                return {'status': 'failed', 'reason': financials['error']}

            # Step 3: Calculate screening metrics
            logger.info(f"{ticker}: Calculating metrics")
            metrics = self.calculator.calculate_metrics(financials, ticker, today)

            # Step 4: Validate completeness
            if not metrics.is_complete(min_metrics=5):
                logger.warning(f"{ticker}: Incomplete data, rejecting")
                await self._log_failure(ticker, 'yahoo_finance', 'Incomplete data (<5 metrics)')
                return {'status': 'failed', 'reason': 'incomplete_data'}

            # Step 5: Insert to PostgreSQL
            logger.info(f"{ticker}: Inserting to PostgreSQL")
            await self._insert_metrics(metrics)

            # Step 6: Cache in Redis
            await self.redis.mark_fetch_cached(ticker, str(today))

            # Log success
            await self._log_success(ticker, 'yahoo_finance')

            logger.info(f"{ticker}: ✅ Success")
            return {'status': 'success', 'metrics': metrics}

        except Exception as e:
            logger.error(f"{ticker}: Error - {e}")
            await self._log_failure(ticker, 'yahoo_finance', str(e))
            return {'status': 'failed', 'reason': str(e)}

    async def process_batch(self, tickers: list[str], today: date) -> dict:
        """Process batch of tickers.

        Args:
            tickers: List of ticker symbols
            today: Date for processing

        Returns:
            Dict with summary statistics
        """
        results = {
            'success': 0,
            'failed': 0,
            'skipped': 0,
            'failed_tickers': []
        }

        for ticker in tickers:
            result = await self.process_ticker(ticker, today)

            if result['status'] == 'success':
                results['success'] += 1
            elif result['status'] == 'failed':
                results['failed'] += 1
                results['failed_tickers'].append(ticker)
            elif result['status'] == 'skipped':
                results['skipped'] += 1

        return results

    async def _insert_metrics(self, metrics: ScreeningMetrics) -> None:
        """Insert screening metrics to PostgreSQL.

        Args:
            metrics: Calculated screening metrics
        """
        async with self.postgres.session() as session:
            await session.execute(
                """
                INSERT INTO financial_data.screening_metrics (
                    ticker, data_source, period_type, revenue_cagr_10y, revenue_cagr_5y,
                    operating_margin_3y_avg, net_margin_3y_avg, roe_3y_avg, roa_3y_avg,
                    roic_3y_avg, debt_to_equity, net_debt_to_ebitda, current_ratio,
                    as_of_date, fetched_at
                )
                VALUES (
                    :ticker, 'yahoo_finance', :period_type, :revenue_cagr_10y, :revenue_cagr_5y,
                    :operating_margin_3y_avg, :net_margin_3y_avg, :roe_3y_avg, :roa_3y_avg,
                    :roic_3y_avg, :debt_to_equity, :net_debt_to_ebitda, :current_ratio,
                    :as_of_date, NOW()
                )
                ON CONFLICT (ticker, as_of_date, data_source, period_type) DO UPDATE SET
                    revenue_cagr_10y = EXCLUDED.revenue_cagr_10y,
                    revenue_cagr_5y = EXCLUDED.revenue_cagr_5y,
                    operating_margin_3y_avg = EXCLUDED.operating_margin_3y_avg,
                    net_margin_3y_avg = EXCLUDED.net_margin_3y_avg,
                    roe_3y_avg = EXCLUDED.roe_3y_avg,
                    roa_3y_avg = EXCLUDED.roa_3y_avg,
                    roic_3y_avg = EXCLUDED.roic_3y_avg,
                    debt_to_equity = EXCLUDED.debt_to_equity,
                    net_debt_to_ebitda = EXCLUDED.net_debt_to_ebitda,
                    current_ratio = EXCLUDED.current_ratio,
                    fetched_at = NOW()
                """,
                {
                    'ticker': metrics.ticker,
                    'period_type': metrics.period_type,
                    'revenue_cagr_10y': metrics.revenue_cagr_10y,
                    'revenue_cagr_5y': metrics.revenue_cagr_5y,
                    'operating_margin_3y_avg': metrics.operating_margin_3y_avg,
                    'net_margin_3y_avg': metrics.net_margin_3y_avg,
                    'roe_3y_avg': metrics.roe_3y_avg,
                    'roa_3y_avg': metrics.roa_3y_avg,
                    'roic_3y_avg': metrics.roic_3y_avg,
                    'debt_to_equity': metrics.debt_to_equity,
                    'net_debt_to_ebitda': metrics.net_debt_to_ebitda,
                    'current_ratio': metrics.current_ratio,
                    'as_of_date': metrics.as_of_date
                }
            )

    async def _log_success(self, ticker: str, source: str) -> None:
        """Log successful fetch to data_sources table.

        Args:
            ticker: Stock ticker
            source: Data source
        """
        async with self.postgres.session() as session:
            await session.execute(
                """
                INSERT INTO document_registry.data_sources (
                    ticker, source_type, fetch_status, records_inserted, fetched_at
                )
                VALUES (:ticker, :source, 'SUCCESS', 1, NOW())
                """,
                {'ticker': ticker, 'source': source}
            )

    async def _log_failure(self, ticker: str, source: str, error: str) -> None:
        """Log failed fetch to data_sources table.

        Args:
            ticker: Stock ticker
            source: Data source
            error: Error message
        """
        async with self.postgres.session() as session:
            await session.execute(
                """
                INSERT INTO document_registry.data_sources (
                    ticker, source_type, fetch_status, error_message, fetched_at
                )
                VALUES (:ticker, :source, 'FAILED', :error, NOW())
                """,
                {'ticker': ticker, 'source': source, 'error': error}
            )
```

**Testing**:

- Unit tests: Each pipeline step isolated (mock dependencies)
- Integration tests: Process 10 tickers end-to-end
- Error tests: Yahoo timeout, incomplete data, PostgreSQL failure
- Dedup tests: Process same ticker twice, verify second skipped

**Deliverable**: ✅ Storage pipeline operational, data in PostgreSQL

---

### Day 6: Bulk Fetch & Daily Refresh ❌ NOT STARTED

**A. Bulk Operations** (`src/data_collector/bulk_operations.py`)

```python
"""Bulk fetch operations for S&P 500."""

import logging
from datetime import date

from src.data_collector.storage_pipeline import StoragePipeline
from src.data_collector.sp500_manager import SP500Manager

logger = logging.getLogger(__name__)

class BulkOperations:
    """Bulk data collection operations."""

    def __init__(self, pipeline: StoragePipeline, sp500_manager: SP500Manager):
        """Initialize bulk operations.

        Args:
            pipeline: Storage pipeline
            sp500_manager: S&P 500 universe manager
        """
        self.pipeline = pipeline
        self.sp500_manager = sp500_manager

    async def backfill_sp500(self, today: date) -> dict:
        """Backfill all S&P 500 companies with screening data.

        Args:
            today: Date for as_of_date

        Returns:
            Dict with summary statistics
        """
        logger.info("Starting S&P 500 backfill")

        # Get active tickers
        tickers = await self.sp500_manager.get_active_tickers()
        logger.info(f"Found {len(tickers)} active S&P 500 companies")

        # Process batch
        import time
        start_time = time.time()

        results = await self.pipeline.process_batch(tickers, today)

        duration = time.time() - start_time
        results['duration_seconds'] = int(duration)
        results['duration_minutes'] = round(duration / 60, 1)

        logger.info(
            f"Backfill complete: {results['success']} success, "
            f"{results['failed']} failed, {results['skipped']} skipped "
            f"({results['duration_minutes']} min)"
        )

        return results

    async def daily_refresh(self, today: date) -> dict:
        """Daily refresh of S&P 500 screening data.

        Only fetches tickers not already fetched today (Redis cache check).

        Args:
            today: Date for processing

        Returns:
            Dict with summary statistics
        """
        logger.info("Starting daily refresh")

        tickers = await self.sp500_manager.get_active_tickers()
        results = await self.pipeline.process_batch(tickers, today)

        logger.info(
            f"Daily refresh complete: {results['success']} fetched, "
            f"{results['skipped']} cached"
        )

        return results
```

**B. CLI Commands** (`src/data_collector/__main__.py` - expand)

```python
@cli.command()
async def yahoo_backfill():
    """Initial backfill of S&P 500 screening data."""
    from datetime import date
    from src.data_collector.yahoo_finance_client import YahooFinanceClient
    from src.data_collector.storage_pipeline import StoragePipeline
    from src.data_collector.bulk_operations import BulkOperations

    postgres = PostgresClient()
    redis = RedisClient()
    yahoo = YahooFinanceClient(redis)
    sp500_manager = SP500Manager(postgres, redis)
    pipeline = StoragePipeline(yahoo, postgres, redis)
    bulk_ops = BulkOperations(pipeline, sp500_manager)

    try:
        today = date.today()
        click.echo(f"Starting S&P 500 backfill for {today}...")

        results = await bulk_ops.backfill_sp500(today)

        click.echo(f"✅ Backfill complete:")
        click.echo(f"  Success: {results['success']}")
        click.echo(f"  Failed: {results['failed']}")
        click.echo(f"  Skipped: {results['skipped']}")
        click.echo(f"  Duration: {results['duration_minutes']} min")

        if results['failed_tickers']:
            click.echo(f"  Failed tickers: {', '.join(results['failed_tickers'][:10])}")
    finally:
        await postgres.close()
        await redis.close()

@cli.command()
async def yahoo_refresh():
    """Daily refresh of S&P 500 screening data."""
    from datetime import date
    from src.data_collector.yahoo_finance_client import YahooFinanceClient
    from src.data_collector.storage_pipeline import StoragePipeline
    from src.data_collector.bulk_operations import BulkOperations

    postgres = PostgresClient()
    redis = RedisClient()
    yahoo = YahooFinanceClient(redis)
    sp500_manager = SP500Manager(postgres, redis)
    pipeline = StoragePipeline(yahoo, postgres, redis)
    bulk_ops = BulkOperations(pipeline, sp500_manager)

    try:
        today = date.today()
        click.echo(f"Starting daily refresh for {today}...")

        results = await bulk_ops.daily_refresh(today)

        click.echo(f"✅ Daily refresh complete:")
        click.echo(f"  Fetched: {results['success']}")
        click.echo(f"  Cached (skipped): {results['skipped']}")
    finally:
        await postgres.close()
        await redis.close()

@cli.command()
@click.option('--tickers', required=True, help='Comma-separated ticker list')
async def yahoo_fetch(tickers: str):
    """Fetch specific tickers on-demand."""
    from datetime import date
    from src.data_collector.yahoo_finance_client import YahooFinanceClient
    from src.data_collector.storage_pipeline import StoragePipeline

    postgres = PostgresClient()
    redis = RedisClient()
    yahoo = YahooFinanceClient(redis)
    pipeline = StoragePipeline(yahoo, postgres, redis)

    try:
        ticker_list = [t.strip().upper() for t in tickers.split(',')]
        today = date.today()

        click.echo(f"Fetching {len(ticker_list)} tickers...")
        results = await pipeline.process_batch(ticker_list, today)

        click.echo(f"✅ Fetch complete:")
        click.echo(f"  Success: {results['success']}")
        click.echo(f"  Failed: {results['failed']}")
    finally:
        await postgres.close()
        await redis.close()
```

**Usage**:

```bash
# Initial backfill (run once)
python -m src.data_collector yahoo-backfill

# Daily refresh (scheduled)
python -m src.data_collector yahoo-refresh

# Ad-hoc fetch
python -m src.data_collector yahoo-fetch --tickers AAPL,MSFT,GOOGL
```

**Testing**:

- Integration tests: Backfill 50 tickers, verify success rate >95%
- Performance tests: Measure backfill time for 500 tickers (target <10 min)
- Daily refresh tests: Verify cached tickers skipped

**Deliverable**: ✅ Bulk fetch operational, S&P 500 data in PostgreSQL

---

### Day 7: Agent API & Integration ❌ NOT STARTED

**A. Agent Interface** (`src/agents/data_collector/agent.py`)

```python
"""Data Collector Agent (Screener-scoped)."""

import logging
from datetime import date
from typing import Optional

from src.data_collector.yahoo_finance_client import YahooFinanceClient
from src.data_collector.sp500_manager import SP500Manager
from src.data_collector.storage_pipeline import StoragePipeline
from src.data_collector.bulk_operations import BulkOperations
from src.storage.postgres_client import PostgresClient
from src.storage.redis_client import RedisClient

logger = logging.getLogger(__name__)

class DataCollectorAgent:
    """Data Collector Agent - Screener-scoped implementation."""

    def __init__(self, database_url: str, redis_url: str):
        """Initialize Data Collector Agent.

        Args:
            database_url: PostgreSQL connection URL
            redis_url: Redis connection URL
        """
        self.postgres = PostgresClient(database_url)
        self.redis = RedisClient(redis_url)
        self.yahoo_client = YahooFinanceClient(self.redis)
        self.sp500_manager = SP500Manager(self.postgres, self.redis)
        self.pipeline = StoragePipeline(self.yahoo_client, self.postgres, self.redis)
        self.bulk_ops = BulkOperations(self.pipeline, self.sp500_manager)

    async def close(self) -> None:
        """Cleanup connections."""
        await self.postgres.close()
        await self.redis.close()

    # ========== Yahoo Finance Methods (Screening) ==========

    async def yahoo_backfill_sp500(self, as_of_date: Optional[date] = None) -> dict:
        """Fetch Yahoo Finance data for all S&P 500 companies.

        Args:
            as_of_date: Date for metrics (default: today)

        Returns:
            Dict with statistics: success/failed/skipped counts, duration
        """
        today = as_of_date or date.today()
        return await self.bulk_ops.backfill_sp500(today)

    async def yahoo_refresh(self, as_of_date: Optional[date] = None) -> dict:
        """Daily refresh of S&P 500 screening data (cached entries skipped).

        Args:
            as_of_date: Date for metrics (default: today)

        Returns:
            Dict with statistics
        """
        today = as_of_date or date.today()
        return await self.bulk_ops.daily_refresh(today)

    async def yahoo_fetch(self, tickers: list[str], as_of_date: Optional[date] = None) -> dict:
        """Fetch Yahoo Finance data for specific tickers.

        Args:
            tickers: List of stock ticker symbols
            as_of_date: Date for metrics (default: today)

        Returns:
            Dict with statistics
        """
        today = as_of_date or date.today()
        return await self.pipeline.process_batch(tickers, today)

    async def get_screening_data(self, ticker: str) -> Optional[dict]:
        """Query stored screening metrics for a ticker.

        Args:
            ticker: Stock ticker symbol

        Returns:
            Dict with screening metrics or None if not found
        """
        async with self.postgres.session() as session:
            result = await session.execute(
                """
                SELECT * FROM financial_data.screening_metrics
                WHERE ticker = :ticker
                ORDER BY as_of_date DESC
                LIMIT 1
                """,
                {'ticker': ticker}
            )
            row = result.fetchone()

            if row:
                return {
                    'ticker': row.ticker,
                    'data_source': row.data_source,
                    'revenue_cagr_10y': row.revenue_cagr_10y,
                    'revenue_cagr_5y': row.revenue_cagr_5y,
                    'operating_margin_3y_avg': row.operating_margin_3y_avg,
                    'net_margin_3y_avg': row.net_margin_3y_avg,
                    'roe_3y_avg': row.roe_3y_avg,
                    'roa_3y_avg': row.roa_3y_avg,
                    'roic_3y_avg': row.roic_3y_avg,
                    'debt_to_equity': row.debt_to_equity,
                    'net_debt_to_ebitda': row.net_debt_to_ebitda,
                    'current_ratio': row.current_ratio,
                    'as_of_date': row.as_of_date,
                    'fetched_at': row.fetched_at
                }
            return None

    async def get_status(self) -> dict:
        """Get agent status and statistics.

        Returns:
            Dict with operational statistics
        """
        async with self.postgres.session() as session:
            # Count screening metrics
            result = await session.execute(
                "SELECT COUNT(*) FROM financial_data.screening_metrics"
            )
            total_metrics = result.scalar_one()

            # Count successful fetches today
            result = await session.execute(
                """
                SELECT COUNT(*) FROM document_registry.data_sources
                WHERE fetch_status = 'SUCCESS'
                  AND fetched_at >= CURRENT_DATE
                """
            )
            fetched_today = result.scalar_one()

            # Count failures today
            result = await session.execute(
                """
                SELECT COUNT(*) FROM document_registry.data_sources
                WHERE fetch_status = 'FAILED'
                  AND fetched_at >= CURRENT_DATE
                """
            )
            failed_today = result.scalar_one()

            return {
                'total_metrics_stored': total_metrics,
                'fetched_today': fetched_today,
                'failed_today': failed_today,
                'data_sources': ['yahoo_finance'],
                'status': 'operational'
            }
```

**B. Screener Integration Example** (`tests/integration/test_screener_integration.py`)

```python
"""Test Screener Agent integration with Data Collector."""

import pytest
from datetime import date

from src.agents.data_collector.agent import DataCollectorAgent

@pytest.mark.integration
async def test_screener_can_query_data():
    """Verify Screener Agent can query screening metrics."""

    # Initialize Data Collector
    agent = DataCollectorAgent(
        database_url="postgresql+asyncpg://postgres:postgres@localhost/fundamental_analysis",
        redis_url="redis://localhost:6379/0"
    )

    try:
        # Fetch data for test tickers
        test_tickers = ['AAPL', 'MSFT', 'GOOGL']
        results = await agent.yahoo_fetch(test_tickers, date.today())

        assert results['success'] == 3

        # Verify Screener can query
        for ticker in test_tickers:
            metrics = await agent.get_screening_data(ticker)

            assert metrics is not None
            assert metrics['ticker'] == ticker
            assert metrics['revenue_cagr_10y'] is not None
            assert metrics['roe_3y_avg'] is not None

            # Screener applies filters
            passes_growth_filter = metrics['revenue_cagr_10y'] >= 0.15  # 15% CAGR
            passes_roe_filter = metrics['roe_3y_avg'] >= 0.15  # 15% ROE

            print(f"{ticker}: Growth={passes_growth_filter}, ROE={passes_roe_filter}")

    finally:
        await agent.close()
```

**Testing**:

- Unit tests: Agent method isolation
- Integration tests: End-to-end with Screener queries
- Status tests: Verify statistics accurate

**Deliverable**: ✅ Agent API operational, Screener can query data

---

## 5. Testing Strategy

### Unit Tests (pytest)

**Coverage Target**: >80%

**Test Files**:

- `tests/storage/test_redis_client.py` - Redis operations
- `tests/data_collector/test_sp500_manager.py` - Universe management
- `tests/data_collector/test_yahoo_client.py` - Yahoo Finance API
- `tests/data_collector/test_screening_calculator.py` - Metrics calculation
- `tests/data_collector/test_storage_pipeline.py` - Pipeline orchestration
- `tests/agents/test_data_collector_agent.py` - Agent interface

**Mock Strategy**:

- Mock yfinance responses (sample AAPL data)
- Mock Redis (fakeredis library)
- Mock PostgreSQL for isolated tests

### Integration Tests (testcontainers)

**Test Files**:

- `tests/integration/test_end_to_end.py` - Full pipeline (5 tickers)
- `tests/integration/test_bulk_operations.py` - S&P 500 batch (50 tickers)
- `tests/integration/test_screener_integration.py` - Screener queries

**Infrastructure** (testcontainers):

- PostgreSQL container (session-scoped, shared)
- Redis container (session-scoped, shared)

**Success Criteria**:

>

- > 95% fetch success rate
- <10 min for 500 companies
- Completeness validation rejects <5 metrics
- Redis dedup prevents refetch <24hr

### Performance Tests

```python
@pytest.mark.slow
async def test_sp500_backfill_performance():
    """Verify S&P 500 backfill completes in <10 min."""
    import time

    agent = DataCollectorAgent(...)

    start = time.time()
    results = await agent.yahoo_backfill_sp500()
    duration = time.time() - start

    assert duration < 600  # 10 minutes
    assert results['success'] >= 475  # >95% success
    assert results['failed'] < 25
```

---

## 6. Configuration & Environment

### Environment Variables

```bash
# .env file

# PostgreSQL
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/fundamental_analysis

# Redis
REDIS_URL=redis://localhost:6379/0

# Yahoo Finance
YAHOO_RATE_LIMIT=2  # requests/second
YAHOO_RETRY_ATTEMPTS=3

# S&P 500 Source
SP500_SOURCE=wikipedia  # or 'csv_file', 'api'

# Screening
SCREENING_MIN_METRICS=5  # Minimum metrics for completeness

# Logging
LOG_LEVEL=INFO
```

### Deployment Checklist

**Prerequisites**:

- ✅ PostgreSQL 18.1 operational (port 5432)
- ✅ Redis operational (port 6379)
- ✅ Alembic migrations applied
- ✅ Dependencies installed (yfinance, httpx, tenacity)

**Initial Setup**:

```bash
# 1. Refresh S&P 500 list
python -m src.data_collector sp500-refresh

# 2. Run initial backfill
python -m src.data_collector yahoo-backfill

# 3. Verify data
python -m src.data_collector status
```

**Daily Operations**:

```bash
# Scheduled daily refresh (cron: 0 7 * * *)
python -m src.data_collector yahoo-refresh
```

---

## 7. Success Criteria

### Functional Requirements

- ✅ Fetch Yahoo Finance data for S&P 500 (500 companies)
- ✅ Calculate screening metrics (CAGR, margins, ROE/ROA/ROIC, ratios)
- ✅ Store in PostgreSQL `screening_metrics` table
- ✅ Deduplication via Redis (skip <24hr cached)
- ✅ Rate limiting (2 req/sec Yahoo Finance)
- ✅ Reject incomplete data (<5 metrics)
- ✅ Handle ticker changes (FB → META)

### Performance Requirements

- ✅ Backfill time: <10 min for 500 companies
- ✅ Success rate: >95% (Yahoo API reliability)
- ✅ Daily refresh: <5 min (cached entries skipped)
- ✅ Memory usage: <500MB agent process

### Quality Requirements

- ✅ Test coverage: >80%
- ✅ No security vulnerabilities
- ✅ Structured logging (JSON format)
- ✅ Configuration externalized (environment variables)
- ✅ Documentation: Usage guide + API reference

---

## 8. What's Deferred to Post-Gate 1

### SEC EDGAR Integration (Days 3-7, Post-Human Gate 1)

**NOT NEEDED for screening**, required only after Gate 1 approves companies for deep analysis.

**When to Implement**:

- After Screener Agent operational
- After Human Gate 1 approves ~10-20 candidates
- Before Business Research Agent needs qualitative data

**Components to Build** (5-7 days):

- SEC EDGAR client (rate limiting 10 req/sec)
- Multi-tier filing parser (EdgarTools + LLM)
- MinIO storage for raw documents
- Amendment tracking
- QC Agent integration for parse failures
- Task queue with priority levels (CRITICAL for Gate 1 approved)

**Implementation Guide**: See `plans/data-collector-implementation.md` Phase B & C

---

## 9. Unresolved Questions

1. **Schema coexistence strategy**: Keep SEC schema (`774d9680756d`) + add screening schema, or merge into unified structure? (Recommend: Keep both per DD-032)
2. **Migration naming**: Create new `XXXXXX_screening_metrics_schema.py` or modify existing `774d9680756d`? (Recommend: New migration to preserve SEC schema)
3. **S&P 500 list source**: Wikipedia scraping reliable? CSV file source? Paid API? (Recommend: Start with Wikipedia, fallback to CSV)
4. **Ticker change tracking**: How far back to track historical symbols? (Currently 7d cache)
5. **Quarterly data**: Store quarterly metrics in addition to annual? (Currently annual only)
6. **Partial failure**: If 50/500 companies fail, continue or abort? (Currently continue)
7. **Daily refresh timing**: Pre-market (7am) or post-market (5pm)? (Currently configurable)

---

## 10. Related Documentation

### Design Decisions

- **DD-032**: Hybrid Data Sourcing Strategy (Yahoo for screening, SEC for deep analysis)
- **DD-031**: SEC Filing Parser Tool Selection (deferred to post-Gate 1)
- **DD-028**: Redis persistence strategy (L1 cache with 24hr TTL)

### Related Plans

- **data-collector-implementation.md**: Full Data Collector plan (includes SEC EDGAR)
- **yahoo-finance-integration-plan.md**: Detailed Yahoo Finance design
- **data-collector-backfill-strategy.md**: Backfill approach rationale

### Architecture Docs

- **docs/architecture/07-data-collector-agent.md**: Full design (including SEC)
- **docs/architecture/08-screener-agent.md**: Screener requirements

---

**Document Status**: ✅ Complete
**Next Steps**: Begin Day 1 implementation (dependencies, migrations, Redis client)
