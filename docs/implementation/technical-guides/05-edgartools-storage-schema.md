# EdgarTools 9-Filing Storage Schema Implementation

**Status**: Ready for Implementation
**Priority**: P0 (Blocking Data Collector)
**Dependencies**: PostgreSQL schema migration `774d9680756d`
**Related**: `research/FINDINGS_EdgarTools_Time_Series.md`, `plans/edgartools-screening-implementation.md`

---

## Executive Summary

Current PostgreSQL schema supports basic financial statement storage but lacks critical fields for:

- EdgarTools XBRL metadata tracking (concept/label extraction)
- Multi-tier parser diagnostics (which tier succeeded, confidence scores)
- Pre-calculated screening metrics (10Y CAGR, margins, ROE/ROA/ROIC)
- Data quality tracking (source credibility, accounting standards)

**Scope**: Extend schema to support 9-filing approach (4,500 filings for 500 companies) with full EdgarTools extraction capabilities.

---

## Table of Contents

1. [Current Schema Status](#current-schema-status)
2. [Gap Analysis](#gap-analysis)
3. [Required Schema Changes](#required-schema-changes)
4. [Migration Strategy](#migration-strategy)
5. [Storage Capacity Analysis](#storage-capacity-analysis)
6. [Implementation Priorities](#implementation-priorities)
7. [Testing Strategy](#testing-strategy)
8. [PostgresClient Updates](#postgresclient-updates)

---

## Current Schema Status

### ✅ Implemented (Migration `774d9680756d`)

**1. metadata.companies**

- ticker (PK), cik, company_name, sector, industry, exchange, country
- Status: ✅ Adequate for company metadata

**2. document_registry.filings** (partitioned by fiscal_year)

- filing_id (UUID), ticker, cik, company_name, form_type
- filing_date, period_end_date, fiscal_year, fiscal_quarter
- accession_number (unique), s3_path, parse_status
- version, is_latest, superseded_by (amendment tracking)
- Partitions: 2019-2030 (11 years)
- Status: ✅ Core structure good, missing metadata fields

**3. financial_data.income_statements** (partitioned by fiscal_year)

- id (UUID), ticker, filing_id, period_end_date, fiscal_year, fiscal_quarter
- revenue, cost_of_revenue, gross_profit, operating_income, net_income
- eps_basic, eps_diluted, shares_outstanding
- version, is_latest
- Status: ⚠️ Core metrics covered, missing EBITDA/tax/interest fields

**4. financial_data.balance_sheets** (partitioned by fiscal_year)

- total_assets, current_assets, cash, accounts_receivable, inventory
- total_liabilities, current_liabilities, total_debt, accounts_payable
- total_equity, retained_earnings
- Status: ⚠️ Core covered, missing long-term debt breakdown, PP&E, goodwill

**5. financial_data.cash_flows** (partitioned by fiscal_year)

- operating_cf, investing_cf, financing_cf, capex
- free_cash_flow, dividends_paid
- Status: ✅ Adequate for screening needs

### 📊 Current Coverage

| Data Category     | Current Fields | Needed for 9-Filing | Status  |
| ----------------- | -------------- | ------------------- | ------- |
| Filing Metadata   | 12             | 17                  | 🟡 71%  |
| Income Statement  | 8              | 16                  | 🟡 50%  |
| Balance Sheet     | 11             | 18                  | 🟡 61%  |
| Cash Flow         | 6              | 6                   | ✅ 100% |
| Screening Metrics | 0              | 12                  | 🔴 0%   |
| XBRL Metadata     | 0              | 6                   | 🔴 0%   |
| **Overall**       | **37**         | **75**              | 🟡 49%  |

---

## Gap Analysis

### 🔴 Critical Gaps (P0 - Blocking)

#### 1. Missing XBRL Metadata Tracking

**Problem**: EdgarTools extracts from XBRL tags like `us-gaap:Revenues`, `ifrs-full:Revenue`, etc. Need to track which tag was used for:

- Debugging parse failures (why did EdgarTools fail?)
- Understanding tag variability across companies (AAPL uses "Contract Revenue", GOOGL uses "Total Cost of Revenue")
- QC Agent validation (verify correct tag selected)

**Current State**: No tracking of XBRL concepts/labels used
**Impact**: Cannot debug why 5% of filings fail Tier 0 parsing

#### 2. Missing Parser Tier Diagnostics

**Problem**: Multi-tier parser (Tier 0→1.5→2→2.5→3→4) needs tracking of:

- Which tier succeeded (tier0=EdgarTools, tier2=LLM, etc.)
- Confidence scores from LLM parsing (Tier 2)
- Accounting standard detected (US-GAAP vs IFRS)

**Current State**: Only tracks `parse_status` (success/failed)
**Impact**: Cannot measure parser effectiveness or optimize tier thresholds

#### 3. Missing Screening Metrics Table

**Problem**: Need pre-calculated metrics for fast screening queries:

- 10Y/5Y/3Y revenue CAGR
- 3Y average margins (operating, net, gross)
- 3Y average returns (ROE, ROA, ROIC)
- Latest debt ratios (debt/equity, current ratio)

**Current State**: Must calculate on-the-fly from raw financials (slow)
**Impact**: Screening 500 companies requires 500 × 9 filing queries + calculations = slow

#### 4. Missing Data Quality Fields

**Problem**: DD-010 requires source credibility tracking:

- Which data source provided this (edgartools tier0/tier1/tier2)
- Credibility score (degrades when contradictions found)
- Temporal decay (data freshness)

**Current State**: No credibility or freshness tracking
**Impact**: QC Agent cannot resolve contradictions or detect stale data

### 🟡 Important Gaps (P1 - Should Have)

#### 5. Missing Key Income Statement Fields

Current: 8 fields (revenue, gross_profit, operating_income, net_income, EPS, shares)

**Missing**:

- `interest_expense` (for interest coverage ratio)
- `tax_expense` (for effective tax rate)
- `ebit` / `ebitda` (common valuation multiples)
- `research_and_development` (critical for tech companies)
- `selling_general_admin` (SG&A)
- `depreciation_amortization` (non-cash expense)
- `other_income_expense` (non-operating items)

**Impact**: Cannot calculate key ratios without additional queries

#### 6. Missing Key Balance Sheet Fields

Current: 11 fields (assets, liabilities, equity breakdown)

**Missing**:

- `long_term_debt` (vs short_term_debt breakdown)
- `short_term_debt`
- `goodwill` (important for M&A-heavy companies)
- `intangible_assets`
- `property_plant_equipment` (PP&E)
- `deferred_tax_assets` / `deferred_tax_liabilities`
- `stockholders_equity` (vs total_equity - subtle GAAP difference)

**Impact**: Cannot analyze capital structure or asset quality thoroughly

### 🟢 Nice to Have (P2 - Future)

#### 7. Segment Data Table

For companies with geographic/business segment reporting (e.g., AAPL: Americas, Europe, Greater China)

**Impact**: Cannot analyze segment growth trends or diversification

#### 8. XBRL Raw Metadata Table

Store full DataFrame metadata for debugging:

- All available XBRL concepts found
- All labels extracted
- Date columns detected
- Parse warnings/errors

**Impact**: Harder to debug edge cases without raw metadata

---

## Required Schema Changes

### P0 Changes (3 migrations)

#### Migration 1: Extend `document_registry.filings`

**Add columns**:

```sql
ALTER TABLE document_registry.filings
ADD COLUMN parse_tier VARCHAR(10),              -- 'tier0', 'tier1', 'tier2', 'tier3', 'tier4'
ADD COLUMN parse_confidence NUMERIC,            -- 0.0 to 1.0 (from LLM if tier2)
ADD COLUMN accounting_standard VARCHAR(10),     -- 'US-GAAP', 'IFRS', 'OTHER'
ADD COLUMN is_restated BOOLEAN DEFAULT false,   -- Restatement flag
ADD COLUMN xbrl_context TEXT;                   -- Context info (consolidated vs parent-only)

-- Index for filtering by parse tier
CREATE INDEX idx_filings_parse_tier ON document_registry.filings(parse_tier, parse_status);
```

**Rationale**:

- `parse_tier`: Track which parser tier succeeded (measures tier effectiveness)
- `parse_confidence`: Validate LLM output quality (filter low confidence <0.80)
- `accounting_standard`: Critical for parser fallback logic (US-GAAP → IFRS)
- `is_restated`: Red flag indicator (frequent restatements = accounting issues)
- `xbrl_context`: Disambiguate consolidated vs parent-only statements

#### Migration 2: Extend Financial Data Tables

**Add to ALL financial tables** (income_statements, balance_sheets, cash_flows):

```sql
-- For financial_data.income_statements
ALTER TABLE financial_data.income_statements
ADD COLUMN xbrl_concept TEXT,           -- e.g., 'us-gaap:Revenues'
ADD COLUMN xbrl_label TEXT,             -- e.g., 'Contract Revenue'
ADD COLUMN source_credibility NUMERIC DEFAULT 1.0,  -- DD-010 tracking
ADD COLUMN data_freshness_score NUMERIC;            -- Temporal decay

-- Index for debugging which concepts are used
CREATE INDEX idx_income_xbrl_concept ON financial_data.income_statements(xbrl_concept);

-- Repeat for balance_sheets and cash_flows
ALTER TABLE financial_data.balance_sheets
ADD COLUMN xbrl_concept TEXT,
ADD COLUMN xbrl_label TEXT,
ADD COLUMN source_credibility NUMERIC DEFAULT 1.0,
ADD COLUMN data_freshness_score NUMERIC;

ALTER TABLE financial_data.cash_flows
ADD COLUMN xbrl_concept TEXT,
ADD COLUMN xbrl_label TEXT,
ADD COLUMN source_credibility NUMERIC DEFAULT 1.0,
ADD COLUMN data_freshness_score NUMERIC;
```

**Rationale**:

- `xbrl_concept`: Track which XBRL tag extracted (essential for debugging)
- `xbrl_label`: Human-readable label for QC validation
- `source_credibility`: DD-010 requirement for contradiction resolution
- `data_freshness_score`: Temporal decay for stale data detection

#### Migration 3: Create `screening_metrics` Table

**New table** (partitioned by fiscal_year):

```sql
CREATE TABLE financial_data.screening_metrics (
    id UUID DEFAULT gen_random_uuid(),
    ticker VARCHAR(10) NOT NULL,
    period_end_date DATE NOT NULL,
    fiscal_year INTEGER NOT NULL,

    -- Growth metrics (CAGR percentages stored as decimals, e.g., 0.15 = 15%)
    revenue_cagr_10y NUMERIC,
    revenue_cagr_5y NUMERIC,
    revenue_cagr_3y NUMERIC,
    net_income_cagr_10y NUMERIC,
    net_income_cagr_5y NUMERIC,

    -- Profitability metrics (3Y averages, stored as decimals)
    operating_margin_3y_avg NUMERIC,
    net_margin_3y_avg NUMERIC,
    gross_margin_3y_avg NUMERIC,

    -- Return metrics (3Y averages, stored as decimals)
    roe_3y_avg NUMERIC,      -- Return on Equity
    roa_3y_avg NUMERIC,      -- Return on Assets
    roic_3y_avg NUMERIC,     -- Return on Invested Capital

    -- Debt metrics (latest period)
    debt_to_equity NUMERIC,
    debt_to_ebitda NUMERIC,
    current_ratio NUMERIC,
    quick_ratio NUMERIC,
    interest_coverage NUMERIC,

    -- Calculation metadata
    calculated_at TIMESTAMP DEFAULT NOW(),
    calculation_method VARCHAR(50),  -- 'edgartools_9filing', 'manual'
    num_periods_used INTEGER,        -- How many periods for CAGR (9, 10, etc.)

    version INTEGER NOT NULL DEFAULT 1,
    is_latest BOOLEAN NOT NULL DEFAULT true,

    PRIMARY KEY (id, fiscal_year),
    FOREIGN KEY (ticker) REFERENCES metadata.companies(ticker) ON DELETE CASCADE,
    UNIQUE(ticker, period_end_date, version, fiscal_year)
) PARTITION BY RANGE (fiscal_year);

-- Create partitions 2019-2030
DO $$
BEGIN
    FOR year IN 2019..2030 LOOP
        EXECUTE format(
            'CREATE TABLE IF NOT EXISTS financial_data.screening_metrics_%s
             PARTITION OF financial_data.screening_metrics
             FOR VALUES FROM (%s) TO (%s)',
            year, year, year + 1
        );
    END LOOP;
END $$;

-- Indexes for fast screening queries
CREATE INDEX idx_screening_ticker ON financial_data.screening_metrics(ticker);
CREATE INDEX idx_screening_latest ON financial_data.screening_metrics(ticker, is_latest) WHERE is_latest = true;
CREATE INDEX idx_screening_cagr ON financial_data.screening_metrics(revenue_cagr_10y) WHERE is_latest = true;
CREATE INDEX idx_screening_roe ON financial_data.screening_metrics(roe_3y_avg) WHERE is_latest = true;

-- Trigger for auto-updating is_latest
CREATE OR REPLACE FUNCTION update_latest_screening()
RETURNS TRIGGER AS $$
BEGIN
    UPDATE financial_data.screening_metrics
    SET is_latest = false
    WHERE ticker = NEW.ticker
      AND period_end_date = NEW.period_end_date
      AND version < NEW.version;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_screening_latest
AFTER INSERT ON financial_data.screening_metrics
FOR EACH ROW
EXECUTE FUNCTION update_latest_screening();
```

**Rationale**:

- **Performance**: Pre-calculated metrics avoid expensive joins (500 companies × 9 filings = 4,500 rows to join)
- **Consistency**: Single source of truth for screening (same CAGR used by Screening Agent and reports)
- **Caching**: Calculated once, reused across screening + deep analysis stages
- **Versioning**: Track when metrics recalculated (e.g., after restatement)

**Query Performance**:

```sql
-- Without screening_metrics table (SLOW):
-- Must join 500 tickers × 9 filings × 3 statements = 13,500 rows + calculate CAGR
SELECT ticker,
       (revenue_latest / revenue_10y_ago) ^ (1/10.0) - 1 AS cagr_10y
FROM (complex_multi_table_join)
-- Execution time: ~5-10 seconds for 500 companies

-- With screening_metrics table (FAST):
SELECT ticker, revenue_cagr_10y
FROM financial_data.screening_metrics
WHERE is_latest = true
-- Execution time: ~50ms for 500 companies (100x speedup)
```

### P1 Changes (1 migration)

#### Migration 4: Extend Financial Statement Fields

**Add to `income_statements`**:

```sql
ALTER TABLE financial_data.income_statements
ADD COLUMN interest_expense BIGINT,
ADD COLUMN tax_expense BIGINT,
ADD COLUMN ebit BIGINT,
ADD COLUMN ebitda BIGINT,
ADD COLUMN research_and_development BIGINT,
ADD COLUMN selling_general_admin BIGINT,
ADD COLUMN depreciation_amortization BIGINT,
ADD COLUMN other_income_expense BIGINT;
```

**Add to `balance_sheets`**:

```sql
ALTER TABLE financial_data.balance_sheets
ADD COLUMN long_term_debt BIGINT,
ADD COLUMN short_term_debt BIGINT,
ADD COLUMN goodwill BIGINT,
ADD COLUMN intangible_assets BIGINT,
ADD COLUMN property_plant_equipment BIGINT,
ADD COLUMN deferred_tax_assets BIGINT,
ADD COLUMN deferred_tax_liabilities BIGINT;
```

**Rationale**:

- Enable calculation of additional ratios (interest coverage, effective tax rate, asset turnover)
- Support deeper financial analysis without re-querying raw filings

### P2 Changes (2 migrations)

#### Migration 5: Segment Data Table

```sql
CREATE TABLE financial_data.segments (
    id UUID DEFAULT gen_random_uuid(),
    ticker VARCHAR(10) NOT NULL,
    filing_id UUID NOT NULL,
    period_end_date DATE NOT NULL,
    fiscal_year INTEGER NOT NULL,
    fiscal_quarter INTEGER CHECK (fiscal_quarter BETWEEN 1 AND 4),

    segment_type VARCHAR(20),  -- 'geographic', 'business'
    segment_name VARCHAR(100),
    revenue BIGINT,
    operating_income BIGINT,
    total_assets BIGINT,

    version INTEGER NOT NULL DEFAULT 1,
    is_latest BOOLEAN NOT NULL DEFAULT true,

    PRIMARY KEY (id, fiscal_year),
    FOREIGN KEY (ticker) REFERENCES metadata.companies(ticker) ON DELETE CASCADE
) PARTITION BY RANGE (fiscal_year);

-- Create partitions
-- (same pattern as other tables)
```

#### Migration 6: XBRL Debug Metadata

```sql
CREATE TABLE document_registry.xbrl_metadata (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    filing_id UUID NOT NULL,

    -- EdgarTools DataFrame metadata
    available_concepts TEXT[],       -- All XBRL concepts in filing
    available_labels TEXT[],         -- All labels found
    date_columns TEXT[],             -- All period dates detected

    -- Parser diagnostics
    parse_warnings TEXT[],           -- Non-fatal warnings
    missing_concepts TEXT[],         -- Expected concepts not found
    ambiguous_concepts TEXT[],       -- Multiple matches found

    created_at TIMESTAMP DEFAULT NOW(),

    -- Foreign key with ON DELETE CASCADE (auto-cleanup when filing deleted)
    CONSTRAINT fk_xbrl_filing FOREIGN KEY (filing_id)
        REFERENCES document_registry.filings(filing_id)
        ON DELETE CASCADE
);

CREATE INDEX idx_xbrl_filing ON document_registry.xbrl_metadata(filing_id);
```

**Use Case**: When EdgarTools fails to parse AAPL 10-K, developer queries `xbrl_metadata` to see:

```sql
SELECT available_concepts, missing_concepts
FROM document_registry.xbrl_metadata
WHERE filing_id = 'abc123';

-- Output: available_concepts = ['us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax', ...]
--         missing_concepts = ['us-gaap:Revenues']
-- Insight: AAPL uses non-standard revenue tag, need Tier 1.5 fallback
```

---

## Migration Strategy

### Timeline

| Migration | Priority | Tables Modified | Estimated Time | Risk Level |
| --------- | -------- | --------------- | -------------- | ---------- |
| 1         | P0       | filings         | 1 hour         | Low        |
| 2         | P0       | 3 financial     | 2 hours        | Low        |
| 3         | P0       | screening (new) | 3 hours        | Medium     |
| 4         | P1       | 2 financial     | 1 hour         | Low        |
| 5         | P2       | segments (new)  | 2 hours        | Low        |
| 6         | P2       | xbrl_meta (new) | 1 hour         | Low        |

**Total P0 Migrations**: 6 hours (1 development day)

### Migration Order

**Phase 1: P0 Schema Extensions** (Day 1)

1. Migration 1 (filings table) - 1 hour
2. Migration 2 (financial tables) - 2 hours
3. Migration 3 (screening_metrics) - 3 hours
4. Test migrations on dev database
5. Apply to production with `alembic upgrade head`

**Phase 2: P1 Field Extensions** (Day 2) 6. Migration 4 (additional fields) - 1 hour 7. Backfill existing data (run EdgarTools re-extraction if needed)

**Phase 3: P2 Advanced Features** (Phase 2 of project) 8. Migrations 5-6 (segments, xbrl_metadata) - deferred to analyst agent phase

### Rollback Strategy

All migrations include `downgrade()` functions:

```python
def downgrade() -> None:
    """Rollback Migration 3: screening_metrics table"""
    op.execute("DROP TRIGGER IF EXISTS trigger_update_screening_latest ON financial_data.screening_metrics")
    op.execute("DROP FUNCTION IF EXISTS update_latest_screening()")
    op.execute("DROP TABLE IF EXISTS financial_data.screening_metrics CASCADE")
```

**Rollback command**:

```bash
alembic downgrade -1  # Rollback last migration
alembic downgrade 774d9680756d  # Rollback to specific version
```

### Data Migration for Existing Records

If database already contains filings (unlikely for new system):

```sql
-- Set default values for new columns
UPDATE document_registry.filings
SET parse_tier = 'tier0',  -- Assume EdgarTools succeeded
    accounting_standard = 'US-GAAP',  -- Default for US companies
    is_restated = false
WHERE parse_tier IS NULL;

-- Backfill screening metrics (run Python script)
-- python -m src.data_collector backfill-screening-metrics
```

---

## Storage Capacity Analysis

### Scenario: 500 Companies × 9 Filings = 4,500 Filings

#### Current Schema Storage (P0 Only)

**PostgreSQL Structured Data**:

| Table                     | Rows  | Bytes/Row | Total      | Notes                       |
| ------------------------- | ----- | --------- | ---------- | --------------------------- |
| metadata.companies        | 500   | 300       | 150 KB     | One-time load               |
| document_registry.filings | 4,500 | 600       | 2.7 MB     | +100 bytes for new columns  |
| income_statements         | 4,500 | 250       | 1.1 MB     | +50 bytes for xbrl tracking |
| balance_sheets            | 4,500 | 350       | 1.6 MB     | +50 bytes                   |
| cash_flows                | 4,500 | 200       | 900 KB     | +50 bytes                   |
| screening_metrics         | 500   | 400       | 200 KB     | 1 per company (latest only) |
| **Subtotal (Structured)** |       |           | **6.5 MB** | Negligible                  |

**PostgreSQL Indexes**:

- Estimate: 2-3x data size = ~20 MB
- **Total PostgreSQL**: ~27 MB for 500 companies ✅

**MinIO Raw Filings**:

- 5 MB/filing × 4,500 filings = **22.5 GB**
- Bucket: `raw/sec_filings/{ticker}/{year}/{accession}.html`

**Total Storage (P0)**:

- PostgreSQL: 27 MB (structured data + indexes)
- MinIO: 22.5 GB (raw HTML/XBRL filings)
- **Total**: 22.5 GB ✅ Well within 10-15TB MinIO capacity

#### With P1 Fields

**Additional columns**:

- Income statements: +8 fields × 8 bytes = +64 bytes/row → +288 KB
- Balance sheets: +7 fields × 8 bytes = +56 bytes/row → +252 KB
- **P1 Overhead**: +540 KB (0.5 MB) - negligible

#### With P2 Tables

**Segments table**:

- Assume 20% of companies report segments (100 companies)
- Avg 5 segments/company × 9 filings = 4,500 segment records
- 250 bytes/row × 4,500 = 1.1 MB

**XBRL metadata table**:

- 4,500 filings × 2 KB/filing = 9 MB (TEXT[] arrays are large)

**P2 Overhead**: 10 MB - still negligible

### Scaling to Full S&P 500 (10 Years)

If later expand to 10 years instead of 9 filings:

| Scenario         | Filings | PostgreSQL | MinIO   | Total   |
| ---------------- | ------- | ---------- | ------- | ------- |
| 9 filings (MVP)  | 4,500   | 27 MB      | 22.5 GB | 22.5 GB |
| 40 filings (10Y) | 20,000  | 120 MB     | 100 GB  | 100 GB  |

**Verdict**: Storage is NOT a bottleneck. 100 GB << 10 TB capacity ✅

---

## Implementation Priorities

### P0 (Must Have Before Data Collector Launch)

**Blocking Issues**:

1. Cannot track which XBRL tags extracted → Cannot debug parse failures
2. Cannot measure parser tier effectiveness → Cannot optimize parser
3. No pre-calculated screening metrics → Screening queries too slow (5-10 sec for 500 companies)

**Deliverables**:

- ✅ Migration 1: Extend `filings` table (parse_tier, accounting_standard, xbrl_context)
- ✅ Migration 2: Extend financial tables (xbrl_concept, xbrl_label, source_credibility)
- ✅ Migration 3: Create `screening_metrics` table

**Timeline**: 1 day (6 hours migrations + 2 hours testing)

**Acceptance Criteria**:

- [ ] All 3 migrations applied successfully
- [ ] PostgresClient dataclasses updated
- [ ] Test data inserted (1 company × 9 filings)
- [ ] Screening metrics calculated and stored
- [ ] Query performance: Latest screening metrics for 500 companies <100ms

### P1 (Should Have for Full Analysis)

**Benefits**:

- Enable calculation of advanced ratios (interest coverage, effective tax rate)
- Support Financial Analyst Agent deeper analysis
- Avoid re-querying raw filings for additional fields

**Deliverables**:

- ✅ Migration 4: Add income/balance sheet fields (EBITDA, PP&E, goodwill, etc.)

**Timeline**: 1 day (includes backfill testing)

**Acceptance Criteria**:

- [ ] Migration 4 applied
- [ ] EdgarTools parser updated to extract new fields
- [ ] 95%+ field coverage (some companies may not report all fields)

### P2 (Future Enhancement)

**Use Cases**:

- Segment analysis (geographic/business diversification)
- Parser debugging (XBRL metadata forensics)

**Deliverables**:

- ✅ Migration 5: Segments table
- ✅ Migration 6: XBRL metadata table

**Timeline**: Deferred to Phase 2 (analyst agents)

---

## Testing Strategy

### Unit Tests

**Test Migration Execution** (`tests/storage/test_migrations.py`):

```python
async def test_migration_1_filings_columns():
    """Verify new columns exist in filings table."""
    async with postgres_client.session() as session:
        result = await session.execute(text("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'filings'
              AND table_schema = 'document_registry'
        """))
        columns = {row.column_name for row in result}

        assert 'parse_tier' in columns
        assert 'parse_confidence' in columns
        assert 'accounting_standard' in columns
        assert 'is_restated' in columns
        assert 'xbrl_context' in columns

async def test_migration_3_screening_metrics_table():
    """Verify screening_metrics table and partitions created."""
    async with postgres_client.session() as session:
        # Check main table exists
        result = await session.execute(text("""
            SELECT EXISTS (
                SELECT 1 FROM information_schema.tables
                WHERE table_name = 'screening_metrics'
                  AND table_schema = 'financial_data'
            )
        """))
        assert result.scalar_one() is True

        # Check partitions exist
        for year in range(2019, 2031):
            result = await session.execute(text(f"""
                SELECT EXISTS (
                    SELECT 1 FROM pg_tables
                    WHERE tablename = 'screening_metrics_{year}'
                )
            """))
            assert result.scalar_one() is True
```

### Integration Tests

**Test Full Pipeline** (`tests/integration/test_edgartools_storage.py`):

```python
async def test_store_9_filings_with_xbrl_metadata():
    """Test storing 9 filings for AAPL with full XBRL tracking."""
    ticker = "AAPL"

    # Mock EdgarTools extraction (9 filings)
    for year in range(2016, 2025):
        filing_data = mock_edgartools_extraction(ticker, year)

        # Insert filing metadata with new fields
        filing_id = await postgres_client.insert_document_metadata(
            DocumentMetadata(
                ticker=ticker,
                cik="0000320193",
                company_name="Apple Inc.",
                form_type="10-K",
                filing_date=date(year, 10, 31),
                period_end_date=date(year, 9, 30),
                fiscal_year=year,
                fiscal_quarter=None,
                accession_number=f"0000320193-{year}-000077",
                s3_path=f"raw/sec_filings/{ticker}/{year}/mock.html",
                parse_status="success",
                parse_tier="tier0",  # New field
                parse_confidence=None,
                accounting_standard="US-GAAP",  # New field
                is_restated=False,
            )
        )

        # Insert income statement with XBRL tracking
        await postgres_client.insert_income_statement(
            IncomeStatementData(
                ticker=ticker,
                filing_id=filing_id,
                period_end_date=date(year, 9, 30),
                fiscal_year=year,
                fiscal_quarter=None,
                revenue=filing_data['revenue'],
                net_income=filing_data['net_income'],
                xbrl_concept="us-gaap:RevenueFromContractWithCustomer",  # New
                xbrl_label="Contract Revenue",  # New
                source_credibility=1.0,  # New
            )
        )

    # Verify 9 filings stored
    async with postgres_client.session() as session:
        result = await session.execute(text("""
            SELECT COUNT(*) FROM document_registry.filings
            WHERE ticker = :ticker
        """), {"ticker": ticker})
        assert result.scalar_one() == 9

async def test_calculate_screening_metrics():
    """Test calculating and storing screening metrics from 9 filings."""
    ticker = "AAPL"

    # Calculate CAGR from stored data (9 years = 10-year duration)
    screening_data = await calculate_screening_metrics(ticker)

    # Insert screening metrics
    await postgres_client.insert_screening_metrics(
        ScreeningMetricsData(
            ticker=ticker,
            period_end_date=date(2024, 9, 30),
            fiscal_year=2024,
            revenue_cagr_10y=screening_data['revenue_cagr_10y'],
            roe_3y_avg=screening_data['roe_3y_avg'],
            calculation_method='edgartools_9filing',
            num_periods_used=9,
        )
    )

    # Verify stored
    async with postgres_client.session() as session:
        result = await session.execute(text("""
            SELECT revenue_cagr_10y, roe_3y_avg
            FROM financial_data.screening_metrics
            WHERE ticker = :ticker AND is_latest = true
        """), {"ticker": ticker})
        row = result.fetchone()

        assert row.revenue_cagr_10y is not None
        assert row.roe_3y_avg is not None
```

### Performance Tests

**Test Query Speed** (`tests/performance/test_screening_queries.py`):

```python
async def test_screening_query_performance():
    """Verify screening metrics query <100ms for 500 companies."""
    import time

    # Insert 500 companies with screening metrics
    for i in range(500):
        ticker = f"TST{i:03d}"
        await postgres_client.insert_screening_metrics(
            mock_screening_data(ticker)
        )

    # Query all screening metrics
    start = time.time()
    async with postgres_client.session() as session:
        result = await session.execute(text("""
            SELECT ticker, revenue_cagr_10y, roe_3y_avg, debt_to_equity
            FROM financial_data.screening_metrics
            WHERE is_latest = true
            ORDER BY revenue_cagr_10y DESC
            LIMIT 50
        """))
        companies = result.fetchall()
    duration_ms = (time.time() - start) * 1000

    assert len(companies) == 50
    assert duration_ms < 100, f"Query took {duration_ms:.1f}ms (target: <100ms)"
```

### Manual Testing Checklist

**Before Production Deployment**:

- [ ] Run all migrations on dev database
- [ ] Insert 1 real company (AAPL) × 9 filings via EdgarTools
- [ ] Verify XBRL concepts tracked correctly
- [ ] Calculate screening metrics manually and compare with stored values
- [ ] Query latest screening metrics for 500 mock companies (<100ms)
- [ ] Rollback migration and verify database restored
- [ ] Re-apply migration and verify idempotency

---

## PostgresClient Updates

### New Dataclasses

**Extended `DocumentMetadata`**:

```python
@dataclass
class DocumentMetadata:
    """Filing metadata for document registry."""
    ticker: str
    cik: str
    company_name: str
    form_type: str
    filing_date: date
    period_end_date: date
    fiscal_year: int
    fiscal_quarter: int | None
    accession_number: str
    s3_path: str
    parse_status: str = "pending"
    version: int = 1

    # NEW FIELDS (Migration 1)
    parse_tier: str | None = None              # 'tier0', 'tier1', 'tier2', etc.
    parse_confidence: float | None = None      # 0.0 to 1.0
    accounting_standard: str | None = None     # 'US-GAAP', 'IFRS'
    is_restated: bool = False
    xbrl_context: str | None = None
```

**Extended `IncomeStatementData`** (similar for BalanceSheetData, CashFlowData):

```python
@dataclass
class IncomeStatementData:
    """Income statement financial data."""
    ticker: str
    filing_id: UUID
    period_end_date: date
    fiscal_year: int
    fiscal_quarter: int | None

    # Existing fields
    revenue: int | None = None
    cost_of_revenue: int | None = None
    gross_profit: int | None = None
    operating_income: int | None = None
    net_income: int | None = None
    eps_basic: int | None = None
    eps_diluted: int | None = None
    shares_outstanding: int | None = None
    version: int = 1

    # NEW FIELDS (Migration 2)
    xbrl_concept: str | None = None            # 'us-gaap:Revenues'
    xbrl_label: str | None = None              # 'Contract Revenue'
    source_credibility: float = 1.0
    data_freshness_score: float | None = None

    # P1 FIELDS (Migration 4)
    interest_expense: int | None = None
    tax_expense: int | None = None
    ebit: int | None = None
    ebitda: int | None = None
    research_and_development: int | None = None
    selling_general_admin: int | None = None
    depreciation_amortization: int | None = None
    other_income_expense: int | None = None
```

**New `ScreeningMetricsData`**:

```python
@dataclass
class ScreeningMetricsData:
    """Pre-calculated screening metrics for fast queries."""
    ticker: str
    period_end_date: date
    fiscal_year: int

    # Growth metrics (decimals, e.g., 0.15 = 15% CAGR)
    revenue_cagr_10y: float | None = None
    revenue_cagr_5y: float | None = None
    revenue_cagr_3y: float | None = None
    net_income_cagr_10y: float | None = None
    net_income_cagr_5y: float | None = None

    # Profitability metrics (3Y avg)
    operating_margin_3y_avg: float | None = None
    net_margin_3y_avg: float | None = None
    gross_margin_3y_avg: float | None = None

    # Return metrics (3Y avg)
    roe_3y_avg: float | None = None
    roa_3y_avg: float | None = None
    roic_3y_avg: float | None = None

    # Debt metrics (latest)
    debt_to_equity: float | None = None
    debt_to_ebitda: float | None = None
    current_ratio: float | None = None
    quick_ratio: float | None = None
    interest_coverage: float | None = None

    # Calculation metadata
    calculation_method: str = 'edgartools_9filing'
    num_periods_used: int = 9
    version: int = 1
```

### New Methods

**In `PostgresClient`**:

```python
async def insert_screening_metrics(self, data: ScreeningMetricsData) -> UUID:
    """Insert pre-calculated screening metrics."""
    async with self.session() as session:
        query = text("""
            INSERT INTO financial_data.screening_metrics (
                ticker, period_end_date, fiscal_year,
                revenue_cagr_10y, revenue_cagr_5y, revenue_cagr_3y,
                net_income_cagr_10y, net_income_cagr_5y,
                operating_margin_3y_avg, net_margin_3y_avg, gross_margin_3y_avg,
                roe_3y_avg, roa_3y_avg, roic_3y_avg,
                debt_to_equity, debt_to_ebitda, current_ratio, quick_ratio, interest_coverage,
                calculation_method, num_periods_used, version
            )
            VALUES (
                :ticker, :period_end_date, :fiscal_year,
                :revenue_cagr_10y, :revenue_cagr_5y, :revenue_cagr_3y,
                :net_income_cagr_10y, :net_income_cagr_5y,
                :operating_margin_3y_avg, :net_margin_3y_avg, :gross_margin_3y_avg,
                :roe_3y_avg, :roa_3y_avg, :roic_3y_avg,
                :debt_to_equity, :debt_to_ebitda, :current_ratio, :quick_ratio, :interest_coverage,
                :calculation_method, :num_periods_used, :version
            )
            RETURNING id
        """)
        result = await session.execute(query, asdict(data))
        return cast(UUID, result.scalar_one())

async def get_latest_screening_metrics(self, ticker: str) -> dict[str, Any] | None:
    """Fetch latest screening metrics for a company."""
    async with self.session() as session:
        query = text("""
            SELECT * FROM financial_data.screening_metrics
            WHERE ticker = :ticker AND is_latest = true
        """)
        result = await session.execute(query, {"ticker": ticker})
        row = result.fetchone()
        if row:
            return dict(row._mapping)
        return None

async def get_all_screening_metrics(self) -> list[dict[str, Any]]:
    """Fetch latest screening metrics for all companies (fast query)."""
    async with self.session() as session:
        query = text("""
            SELECT ticker, revenue_cagr_10y, roe_3y_avg, debt_to_equity,
                   operating_margin_3y_avg, current_ratio
            FROM financial_data.screening_metrics
            WHERE is_latest = true
            ORDER BY revenue_cagr_10y DESC NULLS LAST
        """)
        result = await session.execute(query)
        return [dict(row._mapping) for row in result]
```

---

## Next Steps

### Immediate (Before Data Collector Implementation)

1. **Create Migrations** (Day 1)

   - Write Migration 1: Extend filings table
   - Write Migration 2: Extend financial tables
   - Write Migration 3: Create screening_metrics table
   - Test migrations on dev database

2. **Update PostgresClient** (Day 1)

   - Update dataclasses with new fields
   - Add insert_screening_metrics() method
   - Add get_latest_screening_metrics() method
   - Add get_all_screening_metrics() method

3. **Integration Testing** (Day 1)
   - Test storing 1 company × 9 filings with new fields
   - Verify XBRL metadata tracked correctly
   - Test screening metrics calculation and storage
   - Verify query performance (<100ms for 500 companies)

### Follow-Up (Phase 1 Continuation)

4. **Create Migration 4** (Day 2 - P1)

   - Add income/balance sheet fields (EBITDA, PP&E, etc.)
   - Update EdgarTools parser to extract new fields
   - Test field coverage (95%+ target)

5. **Defer to Phase 2** (P2)
   - Migrations 5-6 (segments, xbrl_metadata)
   - Implement when analyst agents need segment analysis

---

## Summary

**Current Schema**: 49% complete for EdgarTools 9-filing approach

**Critical Gaps Fixed by P0 Migrations**:

- ✅ XBRL metadata tracking (debug parse failures)
- ✅ Parser tier diagnostics (measure effectiveness)
- ✅ Pre-calculated screening metrics (100x query speedup)
- ✅ Data quality tracking (source credibility, freshness)

**Storage Impact**: Negligible (~27 MB PostgreSQL for 500 companies)

**Timeline**: 1 day for P0 migrations (blocking Data Collector launch)

**Success Metrics**:

- All migrations applied without errors
- 1 company × 9 filings stored successfully
- Screening query <100ms for 500 companies
- 95%+ XBRL concept tracking coverage
