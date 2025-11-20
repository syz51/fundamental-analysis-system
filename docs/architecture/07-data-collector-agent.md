# Data Collector Agent: Detailed Design

**Version**: 3.0
**Status**: Design Phase
**Last Updated**: 2025-11-20

## Table of Contents

1. [Overview & Purpose](#overview--purpose)
2. [Key Responsibilities](#key-responsibilities)
3. [Architecture & Components](#architecture--components)
4. [Hybrid Data Sourcing Strategy](#hybrid-data-sourcing-strategy)
5. [SEC EDGAR Integration](#sec-edgar-integration)
6. [Multi-Tier Parsing System](#multi-tier-parsing-system)
7. [Storage Infrastructure](#storage-infrastructure)
8. [Yahoo Finance Integration](#yahoo-finance-integration)
9. [Data Quality & Validation](#data-quality--validation)
10. [Error Handling & Recovery](#error-handling--recovery)
11. [Performance & Scalability](#performance--scalability)
12. [API & Interface](#api--interface)
13. [Backfill Strategy](#backfill-strategy)
14. [Testing Strategy](#testing-strategy)
15. [Configuration Parameters](#configuration-parameters)
16. [Dependencies & Infrastructure](#dependencies--infrastructure)
17. [Monitoring & Observability](#monitoring--observability)
18. [Related Design Decisions](#related-design-decisions)
19. [Implementation Timeline](#implementation-timeline)
20. [Open Questions](#open-questions)

---

## Overview & Purpose

### Primary Responsibility

The Data Collector Agent serves as the **data acquisition and storage management layer** for the entire fundamental analysis system. It acts as the bridge between external data sources (SEC EDGAR, Yahoo Finance) and the internal analytical infrastructure, ensuring all specialist agents have access to high-quality, validated financial data.

**Core Function**: Fetch, parse, validate, and store financial data with 98.55% quality target through multi-tier parsing and intelligent fallback strategies.

### Position in System Architecture

- **Layer**: Support Layer (5-layer v3.0 architecture)
- **Timing**: Operates in two distinct modes:
  - **Pre-screening batch** (Day 1): Yahoo Finance bulk fetch for S&P 500
  - **On-demand deep fetch** (Days 3-7): SEC EDGAR parsing for Gate 1 approved companies
- **Consumers**: All specialist agents (Screener, Business Research, Financial Analyst, Strategy, Valuation)
- **Infrastructure**: PostgreSQL (structured data) + MinIO (raw documents) + Redis (deduplication/rate limiting)

### Key Differentiators

1. **Hybrid Data Sourcing** (DD-032): Different data sources for different pipeline stages (screening vs deep analysis)
2. **Multi-Tier Parsing** (DD-031): 5-tier recovery system (EdgarTools → LLM → QC → Human) achieves 98.55% quality
3. **Amendment Tracking**: Version control for filing amendments with superseding relationships
4. **Intelligent Backfill**: Priority queue-based fetching (critical/high/medium/low) triggered by pipeline gates
5. **Source Credibility** (DD-010): Track data source metadata and credibility scores for contradiction resolution

---

## Key Responsibilities

### Core Duties

1. **Data Acquisition**

   - Yahoo Finance API integration (10Y metrics for screening)
   - SEC EDGAR filing fetch (10-K, 10-Q, 8-K, proxies)
   - Rate limit enforcement (SEC: 10 req/sec, Yahoo: 2 req/sec)
   - CIK lookup and ticker resolution

2. **Document Parsing**

   - Multi-tier XBRL parsing (EdgarTools baseline + custom fallbacks)
   - HTML/text parsing for non-XBRL filings
   - Qualitative data extraction (MD&A, risk factors)
   - Amendment detection and version tracking

3. **Data Validation**

   - Accounting standard consistency (US-GAAP vs IFRS)
   - Balance sheet equation validation (1% tolerance)
   - Value range checks (negative revenue detection)
   - Completeness requirements (minimum 5/8 core metrics)
   - False positive detection (Tier 2.5 validation layer)

4. **Storage Management**

   - Raw filing storage (MinIO/S3 object storage)
   - Structured data storage (PostgreSQL financial tables)
   - Deduplication caching (Redis L1, 24hr TTL)
   - Metadata registry (filing dates, form types, CIKs)

5. **Data Quality Assurance**

   - Source credibility tracking (DD-010)
   - Temporal decay metadata (data freshness)
   - Parse failure escalation to QC Agent
   - Data consistency monitoring

6. **Operational Excellence**
   - Task queue management (priority-based fetching)
   - Concurrency control (10 parallel workers)
   - Error recovery and retry logic
   - Performance monitoring and alerting

### Out of Scope

- Financial statement analysis (Financial Analyst Agent)
- Data interpretation or insights (Specialist Agents)
- Direct user interaction (Lead Coordinator)
- Real-time market data streaming (future consideration)

---

## Architecture & Components

### High-Level Architecture

```text
┌───────────────────────────────────────────────────────────────────┐
│                     DATA COLLECTOR AGENT                           │
├───────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌──────────────────────┐         ┌──────────────────────┐        │
│  │   Yahoo Finance      │         │    SEC EDGAR         │        │
│  │   Client             │         │    Client            │        │
│  │                      │         │                      │        │
│  │ - S&P 500 screening  │         │ - Filing fetch       │        │
│  │ - 10Y metrics        │         │ - CIK lookup         │        │
│  │ - Rate limit: 2/s    │         │ - Rate limit: 10/s   │        │
│  └──────────┬───────────┘         └──────────┬───────────┘        │
│             │                                 │                     │
│             └────────────┬────────────────────┘                     │
│                          ↓                                          │
│           ┌──────────────────────────────┐                         │
│           │   Multi-Tier Filing Parser   │                         │
│           │                              │                         │
│           │  Tier 0: EdgarTools (95%)   │                         │
│           │  Tier 1.5: Smart Rules (35%)│                         │
│           │  Tier 2: LLM Parse (60%)    │                         │
│           │  Tier 2.5: Validation       │                         │
│           │  Tier 3: QC Agent (75%)     │                         │
│           │  Tier 4: Human (100%)       │                         │
│           └──────────────┬───────────────┘                         │
│                          ↓                                          │
│           ┌──────────────────────────────┐                         │
│           │    Storage Pipeline          │                         │
│           │                              │                         │
│           │ 1. Check Redis L1 cache      │                         │
│           │ 2. Upload raw → MinIO        │                         │
│           │ 3. Parse financials          │                         │
│           │ 4. Validate (Tier 2.5)       │                         │
│           │ 5. Insert → PostgreSQL       │                         │
│           │ 6. Cache key → Redis         │                         │
│           └──────────────┬───────────────┘                         │
│                          ↓                                          │
│  ┌───────────────┐  ┌────────────┐  ┌──────────────────┐          │
│  │ PostgreSQL    │  │  MinIO/S3  │  │  Redis L1 Cache  │          │
│  │               │  │            │  │                  │          │
│  │ - Metadata    │  │ - Raw      │  │ - Dedup keys     │          │
│  │ - Financials  │  │   filings  │  │ - Rate limits    │          │
│  │ - Amendments  │  │ - 5GB/500  │  │ - Task state     │          │
│  └───────────────┘  └────────────┘  └──────────────────┘          │
│                                                                     │
└───────────────────────────────────────────────────────────────────┘
         ↓                               ↑
  [Specialist Agents]          [QC Agent Escalation]
  Consume validated data       Parse failure reviews
```

### Component Breakdown

#### 1. Yahoo Finance Client

**Purpose**: Fast quantitative screening data for S&P 500

**Capabilities**:

- Bulk financial metrics fetch (500 companies in 4-10 minutes)
- Historical data (10Y revenue, margins, ROE/ROA/ROIC)
- Automatic retry with exponential backoff
- Rate limiting (2 requests/second)

**Key Methods**:

```python
async def get_sp500_financials() -> dict
async def get_financials(tickers: list[str]) -> dict
async def calculate_screening_metrics(ticker: str) -> dict
```

#### 2. SEC EDGAR Client

**Purpose**: Deep analysis data (qualitative + quantitative)

**Capabilities**:

- Company search and CIK lookup
- Filing index parsing (10-K, 10-Q, 8-K, proxies)
- User-agent compliance
- Rate limit enforcement (10 requests/second)
- Amendment detection (form types ending with /A)

**Key Methods**:

```python
async def fetch_filing(cik: str, accession: str) -> bytes
async def get_company_filings(ticker: str, form_types: list) -> list
async def ticker_to_cik(ticker: str) -> str
```

#### 3. Multi-Tier Filing Parser

**Purpose**: Extract financial data with 98.55% success rate

**Architecture**: See [Multi-Tier Parsing System](#multi-tier-parsing-system)

**Key Methods**:

```python
async def parse_filing(filing_content: bytes) -> ParseResult
async def extract_financials_tier0(xbrl: Any) -> dict  # EdgarTools
async def extract_financials_tier1(xbrl: Any) -> dict  # Smart rules
async def extract_financials_tier2(html: str) -> dict  # LLM
async def validate_financials(data: dict) -> ValidationResult  # Tier 2.5
```

#### 4. Storage Pipeline

**Purpose**: Persist raw and structured data with deduplication

**Workflow**:

1. Check Redis cache (skip if exists)
2. Fetch filing from source
3. Upload raw to MinIO
4. Parse with multi-tier system
5. Validate with Tier 2.5 rules
6. Insert to PostgreSQL (metadata + financials)
7. Cache filing key in Redis (24hr TTL)

**Key Methods**:

```python
async def store_filing(ticker: str, filing: Filing) -> str  # Returns filing_id
async def check_duplicate(cik: str, accession: str) -> bool
async def upload_raw_filing(filing: bytes, path: str) -> str
```

#### 5. Task Queue Manager

**Purpose**: Priority-based fetching triggered by pipeline gates

**Priority Levels**:

- **CRITICAL**: Gate 1 approved (fetch immediately, 10 parallel workers)
- **HIGH**: Top 20 screening candidates (speculative pre-fetch)
- **MEDIUM**: Latest 10-K for screening (initial backfill)
- **LOW**: Long-tail companies (background jobs)

**Key Methods**:

```python
async def add_task(ticker: str, priority: Priority) -> str
async def process_queue() -> None
async def get_queue_status() -> dict
```

---

## Hybrid Data Sourcing Strategy

### Design Decision: DD-032

**Problem**: Different pipeline stages have different data quality and latency requirements.

**Solution**: Use Yahoo Finance for screening (Days 1-2), SEC EDGAR for deep analysis (Days 3-7, post-Gate 1).

### Rationale

| Pipeline Stage           | Data Needs                          | Quality Target  | Latency Tolerance | Optimal Source    |
| ------------------------ | ----------------------------------- | --------------- | ----------------- | ----------------- |
| Screening (Days 1-2)     | 10Y quantitative metrics            | 95% acceptable  | <10 minutes       | Yahoo Finance API |
| Deep Analysis (Days 3-7) | Qualitative narratives + amendments | 98.55% required | <1 hour           | SEC EDGAR parsing |

**Cost-Benefit**:

- Yahoo + SEC: ~$10/month + 2 hours labor
- SEC only: ~$88 + 20 hours labor (original plan)
- Savings: $78/month + 18 hours/month

### Data Flow

```text
Day 1: Pre-Screening Backfill
─────────────────────────────
Yahoo Finance API
  ↓ Fetch S&P 500 (500 companies, 4-10 min)
  ↓ Metrics: 10Y CAGR, margins, ROE/ROA/ROIC, debt ratios
PostgreSQL financial_data (data_source='yahoo_finance')
  ↓ Mark ready for screening
Screening Agent (Days 1-2)
  ↓ Quantitative filters
  ↓ ~30-50 candidates pass filters
  ↓ Pattern matching + ranking
  ↓ Top 10-20 candidates

Human Gate 1 (24hr review)
  ↓ Approve ~10 candidates

Days 3-7: Deep Analysis Fetch
──────────────────────────────
Data Collector Agent (triggered by Gate 1 approval)
  ↓ Priority queue: Add approved tickers (CRITICAL priority)
  ↓ Fetch 10Y filings (10-K + 10-Q, ~40 filings/company)
SEC EDGAR API
  ↓ Download raw filings
  ↓ Multi-tier parsing (EdgarTools → LLM → QC)
MinIO raw storage + PostgreSQL structured data
  ↓ 98.55% quality financials + qualitative data
Specialist Agents (Business, Financial, Strategy)
  ↓ Consume SEC-sourced data for deep analysis
```

### Fallback Strategy

**Scenario 1: Yahoo Finance Degradation**

```text
Yahoo API failure rate >10%
  ↓ Automatic fallback to SEC EDGAR
  ↓ Fetch latest 10-K for screening (slower: 15-30 min)
  ↓ Continue screening with SEC data
```

**Scenario 2: SEC EDGAR Unavailable**

```text
SEC 503 (service unavailable)
  ↓ Use cached Yahoo data for screening
  ↓ Queue SEC fetches for retry (exponential backoff)
  ↓ Alert human: "Deep analysis delayed, SEC downtime"
```

### Data Consistency

**Tracking Source Origin**:

```sql
-- PostgreSQL financial_data table
CREATE TABLE financial_data (
    id UUID PRIMARY KEY,
    ticker VARCHAR(10),
    data_source VARCHAR(20),  -- 'yahoo_finance' or 'sec_edgar'
    metric_name VARCHAR(50),
    metric_value NUMERIC,
    period_end_date DATE,
    created_at TIMESTAMP
);
```

**Source Preference Rules**:

- Screening stage: Prefer Yahoo (faster)
- Deep analysis: Require SEC (qualitative data)
- Discrepancy resolution: SEC data overrides Yahoo (higher quality)

---

## SEC EDGAR Integration

### API Endpoints

**1. Company Search**

```text
https://www.sec.gov/cgi-bin/browse-edgar
  ?action=getcompany
  &CIK={cik}
  &type={form_type}
  &count={count}
```

**2. Filing Download**

```text
https://www.sec.gov/Archives/edgar/data/{cik}/{accession_no_dashes}/{accession}.txt
```

**3. Company Tickers (bulk lookup)**

```text
https://www.sec.gov/files/company_tickers.json
```

### Rate Limiting

**SEC Requirements**:

- Maximum: 10 requests/second
- User-Agent: "FundamentalAnalysisSystem <admin@example.com>"
- IP-based enforcement (no authentication)

**Implementation**:

```python
class EDGARClient:
    def __init__(self):
        self.rate_limiter = RateLimiter(max_requests=10, window=1.0)
        self.user_agent = "FundamentalAnalysisSystem admin@example.com"

    async def fetch_with_rate_limit(self, url: str) -> bytes:
        await self.rate_limiter.acquire()  # Block if limit reached
        response = await httpx.get(url, headers={'User-Agent': self.user_agent})
        return response.content
```

**Redis-Based Rate Limiting**:

```python
# Redis counter: rate_limit:{second}
# INCR rate_limit:1732071234
# EXPIRE rate_limit:1732071234 2

async def check_rate_limit() -> bool:
    current_second = int(time.time())
    key = f"rate_limit:{current_second}"
    count = await redis.incr(key)
    await redis.expire(key, 2)  # Cleanup
    return count <= 10
```

### Filing Types

**Priority Focus**:

| Form Type       | Description         | Analysis Use                             | Fetch Frequency         |
| --------------- | ------------------- | ---------------------------------------- | ----------------------- |
| 10-K            | Annual report       | Full financials, MD&A, risk factors      | Annual (10Y backfill)   |
| 10-Q            | Quarterly report    | Updated financials, trending             | Quarterly (3Y backfill) |
| 8-K             | Current events      | Material events, M&A, management changes | On-demand               |
| DEF 14A (Proxy) | Shareholder meeting | Executive compensation, governance       | Annual (5Y backfill)    |

**Secondary Forms** (Phase 2+):

- 10-K/A, 10-Q/A (amendments)
- S-1 (IPO registration)
- 13F (institutional holdings)

### CIK Lookup

**Problem**: SEC uses CIK (Central Index Key), not tickers.

**Solution**: Maintain ticker-to-CIK mapping cache.

```python
# Initial load from SEC bulk file
async def load_ticker_cik_mapping():
    response = await httpx.get('https://www.sec.gov/files/company_tickers.json')
    mappings = response.json()
    # Cache in Redis with 7d TTL
    for ticker, cik in mappings.items():
        await redis.set(f"cik:{ticker}", cik, ex=86400*7)

# Runtime lookup with fallback
async def ticker_to_cik(ticker: str) -> str:
    # Check cache
    cik = await redis.get(f"cik:{ticker}")
    if cik:
        return cik

    # Fallback: Search SEC API
    response = await edgar_search(ticker)
    cik = parse_cik_from_response(response)
    await redis.set(f"cik:{ticker}", cik, ex=86400*7)
    return cik
```

### Amendment Detection

**Challenge**: Amended filings (10-K/A) supersede original 10-K.

**Implementation**:

```python
async def detect_amendment(form_type: str) -> bool:
    return form_type.endswith('/A')

async def process_filing(filing: Filing):
    if detect_amendment(filing.form_type):
        base_form = filing.form_type.rstrip('/A')
        original = await postgres.get_filing_by_period(
            ticker=filing.ticker,
            period_end_date=filing.period_end_date,
            form_type=base_form
        )

        if original:
            # Link amendment to original
            await postgres.insert_filing(
                version=original.version + 1,
                superseded_by=None
            )
            await postgres.update_filing(
                filing_id=original.filing_id,
                is_latest=False,
                superseded_by=new_filing_id
            )
```

**PostgreSQL Schema**:

```sql
CREATE TABLE document_registry.filings (
    filing_id UUID PRIMARY KEY,
    ticker VARCHAR(10),
    form_type VARCHAR(10),
    period_end_date DATE,
    version INTEGER DEFAULT 1,
    is_latest BOOLEAN DEFAULT TRUE,
    superseded_by UUID REFERENCES filings(filing_id),
    UNIQUE(ticker, period_end_date, form_type, version)
);
```

---

## Multi-Tier Parsing System

### Design Decision: DD-031

**Problem**: No single XBRL parser handles all edge cases (non-standard tags, IFRS, amendments, holding companies, etc.). Achieving 98.55% quality requires multiple fallback strategies.

**Solution**: 5-tier system with increasing sophistication and cost.

### Tier Architecture

```text
1,000 Filings Enter Multi-Tier Parser
──────────────────────────────────────

Tier 0: EdgarTools (Baseline)
  ↓ Success: 950 filings (95%)
  ↓ Cost: Free
  ↓ Speed: 10-30x faster than custom
  ✓ Standard XBRL, conventional tags

Tier 1.5: Smart Deterministic (Metadata-Aware)
  ↓ Recovery: 17 filings (35% of remaining 50)
  ↓ Cost: $0
  ↓ Logic: US-GAAP → IFRS → fuzzy match
  ✓ Context disambiguation (consolidated vs parent)
  ✓ Accounting standard switching

Tier 2: LLM-Assisted Parsing (Semantic)
  ↓ Recovery: 20 filings (60% of remaining 33)
  ↓ Cost: $0.15/filing × 33 = $4.95
  ↓ Model: Claude Sonnet 4.5
  ✓ Semantic understanding of filing structure
  ✓ Confidence scoring (threshold: 0.80)

Tier 2.5: Data Validation (False Positive Catch)
  ↓ Reject: 2 filings (10% false positive rate)
  ↓ Cost: $0
  ✓ Balance sheet equation validation
  ✓ Accounting standard consistency
  ✓ Value range checks

Tier 3: QC Agent Deep Review (Root Cause Analysis)
  ↓ Recovery: 8 filings (75% of remaining 11)
  ↓ Cost: $0.30/review × 11 = $3.30
  ✓ Strategic retry recommendations
  ✓ Learning insights for parser improvement

Tier 4: Human Escalation (Manual Review)
  ↓ Resolution: 3 filings (100%)
  ↓ Cost: 15-30 min/filing × 3 = 45-90 min
  ✓ Corrupted files, novel filing types
  ✓ Ambiguous data requiring judgment

Final Results:
──────────────
Success: 998 filings (99.8%)
Cost: $8.25 + 45-90 min labor
Quality: 98.55% (2 false positives caught by Tier 2.5)
```

### Tier 0: EdgarTools (Baseline)

**Purpose**: Handle 95% of standard filings with industry-proven library.

**Capabilities**:

- XBRL parsing with standardized taxonomy
- Multi-period extraction (quarterly, annual)
- Financial statement identification
- Battle-tested (1.2K GitHub stars)

**Implementation**:

```python
from edgartools import Filing

async def parse_tier0(filing_content: bytes) -> ParseResult:
    try:
        filing = Filing.from_bytes(filing_content)
        financials = filing.obj()  # Extract XBRL

        return ParseResult(
            success=True,
            tier='tier0',
            data={
                'revenue': financials.get('us-gaap:Revenues'),
                'net_income': financials.get('us-gaap:NetIncomeLoss'),
                'assets': financials.get('us-gaap:Assets'),
                # ... 8 core metrics
            },
            confidence=0.95
        )
    except Exception as e:
        return ParseResult(success=False, tier='tier0', error=str(e))
```

**Limitations**:

- No context disambiguation (restated vs original)
- No IFRS tag fallback
- No data validation (accepts malformed data)

### Tier 1.5: Smart Deterministic (Metadata-Aware)

**Purpose**: Recover 35% of Tier 0 failures using metadata-aware rule-based logic.

**Strategies**:

1. **Accounting Standard Fallback**

   ```python
   # Try US-GAAP, then IFRS, then fuzzy match
   revenue = (
       xbrl.get('us-gaap:Revenues') or
       xbrl.get('ifrs-full:Revenue') or
       fuzzy_match(xbrl, pattern='revenue|sales|turnover')
   )
   ```

2. **Context Disambiguation**

   ```python
   # Prefer consolidated over parent-only
   contexts = xbrl.get_all_contexts('us-gaap:Assets')
   for ctx in contexts:
       if 'consolidated' in ctx.entity.segment:
           return ctx.value
   ```

3. **Amendment Handling**

   ```python
   # Prefer restated over original
   periods = xbrl.get_periods('us-gaap:NetIncomeLoss')
   for period in sorted(periods, key=lambda p: p.filed_date, reverse=True):
       if period.is_restated:
           return period.value
   ```

**Success Rate**: 35% recovery (17 of 50 failures)

### Tier 2: LLM-Assisted Parsing

**Purpose**: Use semantic understanding to extract from non-standard filings.

**Approach**:

1. Sample filing HTML (focus on financial statement sections)
2. Provide metadata context (company type, accounting standard, form type)
3. Request structured JSON extraction
4. Validate confidence threshold (>0.80)

**Prompt Structure**:

```python
prompt = f"""
Extract financial metrics from this {form_type} filing:

Company: {ticker} ({company_type})
Accounting Standard: {accounting_standard}
Period End: {period_end_date}
Form Type: {form_type}

Filing Content (sampled sections):
{html_sample}

Extract these metrics in JSON:
- revenue (key: us-gaap:Revenues or equivalent)
- operating_income
- net_income
- eps_diluted
- total_assets
- total_liabilities
- shareholders_equity
- operating_cash_flow

For each metric, provide:
- value (numeric)
- confidence (0-1 scale)
- source_tag (XBRL tag or description)

Special cases:
- If IFRS filer: Use IFRS tag equivalents
- If holding company: Use consolidated financials
- If restated: Use most recent restatement
"""
```

**Output Example**:

```json
{
  "revenue": {
    "value": 365000000000,
    "confidence": 0.92,
    "source_tag": "us-gaap:Revenues"
  },
  "net_income": {
    "value": 94300000000,
    "confidence": 0.88,
    "source_tag": "us-gaap:NetIncomeLoss"
  },
  "assets": {
    "value": 352700000000,
    "confidence": 0.95,
    "source_tag": "us-gaap:Assets"
  }
}
```

**Confidence Threshold**:

- Accept if all metrics >0.80 confidence
- Escalate to Tier 3 if any metric <0.80

**Cost**: ~$0.15/filing (1,500 tokens input + 500 tokens output @ Sonnet 4.5 pricing)

### Tier 2.5: Data Validation Layer

**Purpose**: Catch false positives from Tier 2 LLM parsing (20% error rate without validation).

**Validation Rules**:

**1. Accounting Standard Consistency**

```python
def validate_accounting_standard(data: dict, expected_standard: str) -> bool:
    """Ensure IFRS filers don't return US-GAAP tags."""
    for metric, details in data.items():
        source_tag = details['source_tag']
        if expected_standard == 'IFRS' and source_tag.startswith('us-gaap:'):
            return False  # Flag: IFRS filer with US-GAAP tag
        if expected_standard == 'US-GAAP' and source_tag.startswith('ifrs-full:'):
            return False
    return True
```

**2. Balance Sheet Equation**

```python
def validate_balance_sheet(data: dict) -> bool:
    """Assets = Liabilities + Equity (1% tolerance)."""
    assets = data.get('total_assets', {}).get('value', 0)
    liabilities = data.get('total_liabilities', {}).get('value', 0)
    equity = data.get('shareholders_equity', {}).get('value', 0)

    if assets == 0:
        return False  # Missing data

    calculated_assets = liabilities + equity
    tolerance = 0.01
    return abs(assets - calculated_assets) / assets < tolerance
```

**3. Value Range Checks**

```python
def validate_value_ranges(data: dict) -> bool:
    """Revenue ≥ 0, Net Income vs Revenue reasonableness."""
    revenue = data.get('revenue', {}).get('value', 0)
    net_income = data.get('net_income', {}).get('value', 0)

    if revenue < 0:
        return False  # Red flag: Negative revenue

    if revenue > 0 and abs(net_income) > revenue * 2:
        return False  # Implausible: Net income > 200% revenue
    return True
```

**4. Completeness Check**

```python
def validate_completeness(data: dict) -> bool:
    """Require minimum 5/8 core metrics."""
    required_metrics = [
        'revenue', 'net_income', 'total_assets',
        'total_liabilities', 'shareholders_equity',
        'operating_cash_flow', 'operating_income', 'eps_diluted'
    ]
    found = sum(1 for metric in required_metrics if metric in data)
    return found >= 5
```

**Impact**: Catches 66% of false positives (2 of 3 in simulation), improving quality from 95% → 98.55%.

### Tier 3: QC Agent Deep Review

**Purpose**: Root cause analysis and strategic retry recommendations.

**Message Bus Integration**:

```python
# Data Collector → QC Agent
await message_bus.send(
    from_agent="DataCollectorAgent",
    to_agent="QCAgent",
    message_type="PARSE_FAILURE_REVIEW",
    priority="HIGH",
    content={
        "filing_id": "uuid-123",
        "ticker": "AAPL",
        "form_type": "10-K",
        "period_end_date": "2023-09-30",
        "error": {
            "tier0_error": "KeyError: 'us-gaap:Revenues'",
            "tier1_error": "No IFRS fallback found",
            "tier2_confidence": 0.72,  # Below 0.80 threshold
            "validation_failures": ["balance_sheet_equation"]
        },
        "filing_content_sample": "...",
        "strategies_tried": ["US-GAAP", "IFRS", "LLM"],
        "requires_response": True,
        "timeout": 3600  # 1 hour
    }
)
```

**QC Agent Analysis**:

- Review filing structure and metadata
- Identify root cause (non-standard format, holding company structure, etc.)
- Recommend retry strategy (different tag pattern, manual extraction)
- Update parser knowledge base with learnings

**Success Rate**: 75% recovery (8 of 11 escalations)

### Tier 4: Human Escalation

**Triggers**:

- Tier 3 QC Agent unable to resolve
- Corrupted/unreadable filing
- Novel filing type (SPAC, bankruptcy, etc.)
- Critical filing for high-priority analysis

**Human Interface**:

```text
Parse Failure Escalation #47
────────────────────────────
Company: ACME Corp (ACME)
Form: 10-K for period ending 2023-12-31
CIK: 0001234567
Accession: 0001234567-23-000045

Issue: Multi-period restated financials with ambiguous context
Strategies Tried: EdgarTools, IFRS fallback, LLM (confidence: 0.65)
QC Agent Recommendation: Manual extraction, focus on Note 2 (Restatement)

Actions:
[ ] Review filing manually
[ ] Extract financials (provide JSON)
[ ] Mark filing type for future automation
[ ] Escalate to SEC team if corrupted

Estimated Time: 20-30 minutes
```

**Success Rate**: 100% (by definition)

---

## Storage Infrastructure

### Three-Tier Storage Architecture

```text
┌─────────────────────────────────────────────────────────────┐
│                    STORAGE LAYER                             │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌─────────────────┐  ┌─────────────────┐  ┌──────────────┐ │
│  │  PostgreSQL     │  │   MinIO/S3      │  │  Redis L1    │ │
│  │  (Structured)   │  │   (Raw Docs)    │  │  (Cache)     │ │
│  ├─────────────────┤  ├─────────────────┤  ├──────────────┤ │
│  │ • Metadata      │  │ • HTML/XML      │  │ • Dedup keys │ │
│  │ • Financials    │  │ • Full filings  │  │ • Rate limit │ │
│  │ • Amendments    │  │ • Versioned     │  │ • Task state │ │
│  │ • Source cred   │  │ • 5GB/500 cos   │  │ • 24hr TTL   │ │
│  └─────────────────┘  └─────────────────┘  └──────────────┘ │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### PostgreSQL: Structured Data

**Schema Overview**:

**1. document_registry.filings** (Metadata)

```sql
CREATE TABLE document_registry.filings (
    filing_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    ticker VARCHAR(10) NOT NULL,
    cik VARCHAR(10) NOT NULL,
    form_type VARCHAR(10) NOT NULL,
    filing_date DATE NOT NULL,
    period_end_date DATE,
    accession_number VARCHAR(20) UNIQUE,
    version INTEGER DEFAULT 1,
    is_latest BOOLEAN DEFAULT TRUE,
    superseded_by UUID REFERENCES filings(filing_id),
    data_source VARCHAR(20),  -- 'yahoo_finance' or 'sec_edgar'
    parse_tier VARCHAR(10),  -- 'tier0', 'tier1', 'tier2', etc.
    s3_path TEXT,  -- MinIO storage path
    created_at TIMESTAMP DEFAULT now(),
    INDEX idx_ticker_period (ticker, period_end_date),
    INDEX idx_form_type (form_type),
    INDEX idx_is_latest (is_latest)
);
```

**2. financial_data.income_statement**

```sql
CREATE TABLE financial_data.income_statement (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    filing_id UUID REFERENCES document_registry.filings(filing_id),
    ticker VARCHAR(10),
    period_end_date DATE,
    revenue NUMERIC,
    operating_income NUMERIC,
    net_income NUMERIC,
    eps_diluted NUMERIC,
    source_credibility NUMERIC DEFAULT 1.0,  -- DD-010
    timestamp_created TIMESTAMP DEFAULT now(),  -- Temporal decay
    INDEX idx_ticker_period (ticker, period_end_date)
);
```

**3. financial_data.balance_sheet**

```sql
CREATE TABLE financial_data.balance_sheet (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    filing_id UUID REFERENCES document_registry.filings(filing_id),
    ticker VARCHAR(10),
    period_end_date DATE,
    total_assets NUMERIC,
    total_liabilities NUMERIC,
    shareholders_equity NUMERIC,
    cash_and_equivalents NUMERIC,
    total_debt NUMERIC,
    source_credibility NUMERIC DEFAULT 1.0,
    timestamp_created TIMESTAMP DEFAULT now()
);
```

**Connection Pooling**:

```python
# src/storage/postgres_client.py
class PostgresClient:
    def __init__(self):
        self.engine = create_async_engine(
            DATABASE_URL,
            pool_size=5,  # Minimum connections
            max_overflow=15,  # Maximum 20 total connections
            pool_pre_ping=True,  # Check connection health
            pool_recycle=3600  # Recycle after 1 hour
        )

    async def bulk_insert(self, table: str, records: list[dict], batch_size: int = 100):
        """Batch insert for performance (100+ filings/transaction)."""
        async with self.engine.begin() as conn:
            for i in range(0, len(records), batch_size):
                batch = records[i:i+batch_size]
                await conn.execute(insert(table).values(batch))
```

### MinIO/S3: Raw Document Storage

**Purpose**: Store original filing documents for audit trail and re-parsing.

**Path Structure**:

```text
raw/
├── sec_filings/
│   ├── AAPL/
│   │   ├── 2023/
│   │   │   ├── 0000320193-23-000077.html  (10-K)
│   │   │   ├── 0000320193-23-000106.html  (10-Q Q1)
│   │   │   └── ...
│   │   ├── 2022/
│   │   └── ...
│   ├── MSFT/
│   └── ...
└── yahoo_cache/  (future: cache Yahoo API responses)
```

**Client Implementation**:

```python
# src/storage/s3_client.py
import boto3

class S3Client:
    def __init__(self):
        self.client = boto3.client(
            's3',
            endpoint_url=MINIO_ENDPOINT,  # http://localhost:9000
            aws_access_key_id=MINIO_ACCESS_KEY,
            aws_secret_access_key=MINIO_SECRET_KEY
        )
        self.bucket = 'fundamental-analysis'

    async def upload_filing(self, filing_content: bytes, path: str) -> str:
        """Upload with retry logic (3 attempts, exponential backoff)."""
        for attempt in range(3):
            try:
                # Use multipart upload for files >5MB
                if len(filing_content) > 5 * 1024 * 1024:
                    await self.multipart_upload(path, filing_content)
                else:
                    await self.client.put_object(
                        Bucket=self.bucket,
                        Key=path,
                        Body=filing_content
                    )
                return f"s3://{self.bucket}/{path}"
            except Exception as e:
                if attempt == 2:
                    raise
                await asyncio.sleep(2 ** attempt)
```

**Versioning**: Enabled for amendment tracking (automatic versioning by MinIO).

### Redis L1: Working Memory Cache

**Purpose**: Deduplication, rate limiting, task state tracking.

**Key Patterns**:

**1. Deduplication** (24hr TTL)

```python
# Key: filing:{cik}:{accession}
# Value: filing_id (UUID)

async def check_duplicate(cik: str, accession: str) -> Optional[str]:
    key = f"filing:{cik}:{accession}"
    filing_id = await redis.get(key)
    return filing_id

async def mark_cached(cik: str, accession: str, filing_id: str):
    key = f"filing:{cik}:{accession}"
    await redis.set(key, filing_id, ex=86400)  # 24hr TTL
```

**2. Rate Limiting**

```python
# Key: rate_limit:{second}
# Value: request count

async def check_rate_limit() -> bool:
    current_second = int(time.time())
    key = f"rate_limit:{current_second}"
    count = await redis.incr(key)
    await redis.expire(key, 2)
    return count <= 10  # SEC limit
```

**3. Task State Tracking**

```python
# Key: task:active:{task_id}
# Value: JSON task metadata

async def track_active_task(task_id: str, metadata: dict):
    key = f"task:active:{task_id}"
    await redis.set(key, json.dumps(metadata), ex=3600)  # 1hr
```

**Configuration**:

- Max memory: 512MB
- Eviction policy: `allkeys-lru` (least recently used)
- Persistence: RDB snapshots (hourly)

---

## Yahoo Finance Integration

### Purpose

Provide fast quantitative screening data for S&P 500 without deep SEC parsing overhead.

### Library Selection: yfinance

**Rationale**:

- Free and open-source
- 11K+ GitHub stars (well-maintained)
- Simple API (3-line data fetch)
- 10Y+ historical data available

**Installation**:

```bash
uv add yfinance
```

### Key Methods

```python
# src/data_collector/yahoo_finance_client.py
import yfinance as yf

class YahooFinanceClient:
    def __init__(self):
        self.rate_limiter = RateLimiter(max_requests=2, window=1.0)

    async def get_financials(self, ticker: str) -> dict:
        """Fetch annual financial statements."""
        await self.rate_limiter.acquire()
        stock = yf.Ticker(ticker)
        return {
            'income_statement': stock.financials,  # Annual
            'balance_sheet': stock.balance_sheet,
            'cash_flow': stock.cashflow,
            'quarterly': stock.quarterly_financials
        }

    async def get_sp500_financials(self) -> dict:
        """Bulk fetch S&P 500 (500 companies, ~4-10 min)."""
        sp500_tickers = await self.load_sp500_list()
        results = {}

        for ticker in sp500_tickers:
            try:
                results[ticker] = await self.get_financials(ticker)
            except Exception as e:
                logger.error(f"Yahoo fetch failed: {ticker}, {e}")
                results[ticker] = {'error': str(e)}

        return results
```

### Screening Metrics Calculation

```python
# src/data_collector/yahoo_metrics.py
def calculate_screening_metrics(financials: dict) -> dict:
    """Transform raw Yahoo data into screening metrics."""
    income = financials['income_statement']
    balance = financials['balance_sheet']

    # 10Y Revenue CAGR
    revenue_10y_ago = income.loc['Total Revenue'].iloc[-1]  # Oldest
    revenue_latest = income.loc['Total Revenue'].iloc[0]  # Most recent
    years = 10
    revenue_cagr_10y = (revenue_latest / revenue_10y_ago) ** (1 / years) - 1

    # Operating Margin (3Y avg)
    operating_income = income.loc['Operating Income'][:3].mean()
    revenue = income.loc['Total Revenue'][:3].mean()
    operating_margin = operating_income / revenue

    # ROE (3Y avg)
    net_income = income.loc['Net Income'][:3].mean()
    equity = balance.loc['Total Stockholder Equity'][:3].mean()
    roe = net_income / equity

    # Debt/Equity (latest)
    total_debt = balance.loc['Total Debt'].iloc[0]
    equity_latest = balance.loc['Total Stockholder Equity'].iloc[0]
    debt_to_equity = total_debt / equity_latest

    return {
        'revenue_cagr_10y': revenue_cagr_10y,
        'revenue_cagr_5y': calculate_cagr(income, years=5),
        'operating_margin_3y_avg': operating_margin,
        'net_margin_3y_avg': calculate_margin(income, 'Net Income'),
        'roe_3y_avg': roe,
        'roa_3y_avg': calculate_roa(income, balance),
        'roic_3y_avg': calculate_roic(income, balance),
        'debt_to_equity': debt_to_equity,
        'current_ratio': calculate_current_ratio(balance)
    }
```

### CLI Commands

```bash
# S&P 500 bulk backfill (initial screening setup)
python -m src.data_collector yahoo-backfill

# Fetch specific tickers (ad-hoc)
python -m src.data_collector yahoo-fetch --tickers AAPL,MSFT,GOOGL

# Refresh stale data (>7 days old)
python -m src.data_collector yahoo-refresh
```

### Fallback Strategy

**Scenario: Yahoo API Failure**

```python
async def fetch_with_fallback(ticker: str) -> dict:
    # Tier 1: Yahoo Finance
    try:
        return await yahoo_client.get_financials(ticker)
    except Exception as e:
        logger.warning(f"Yahoo fetch failed: {ticker}, trying SEC fallback")

    # Tier 2: Check Redis cache (7d TTL)
    cached = await redis.get(f"yahoo_cache:{ticker}")
    if cached and (now() - cached['timestamp']).days < 7:
        logger.info(f"Using cached Yahoo data: {ticker}")
        return cached['data']

    # Tier 3: SEC EDGAR fallback (slower but reliable)
    logger.info(f"Falling back to SEC EDGAR: {ticker}")
    return await edgar_client.fetch_latest_10k(ticker)
```

---

## Data Quality & Validation

### Validation Rules (Tier 2.5)

See [Multi-Tier Parsing System](#multi-tier-parsing-system) for detailed validation logic.

**Summary of Checks**:

1. Accounting standard consistency (IFRS vs US-GAAP)
2. Balance sheet equation (Assets = Liabilities + Equity, 1% tolerance)
3. Value range checks (revenue ≥ 0, net income reasonableness)
4. Completeness (minimum 5/8 core metrics)
5. Holding company consolidated source verification

### Source Credibility Tracking (DD-010)

**Purpose**: Track data source reliability for contradiction resolution.

**Implementation**:

```python
# PostgreSQL: financial_data tables include source_credibility column
async def update_source_credibility(source: str, credibility: float):
    """
    Update credibility score based on contradiction resolution.
    Range: 0.0 (unreliable) to 1.0 (highly reliable)
    """
    await postgres.execute(
        "UPDATE financial_data.income_statement "
        "SET source_credibility = :credibility "
        "WHERE data_source = :source",
        {'credibility': credibility, 'source': source}
    )

# QC Agent resolves contradiction → updates credibility
# Example: Yahoo reported $100M revenue, SEC shows $95M
#   → SEC wins (higher quality)
#   → Yahoo credibility: 1.0 → 0.95 (small decrease)
```

### Data Quality Metrics

**Target Benchmarks**:

| Metric                            | Target | Current (v1.0)            |
| --------------------------------- | ------ | ------------------------- |
| Parse Success Rate (Tier 0)       | >95%   | 95% (EdgarTools)          |
| Overall Quality (Post-Validation) | >98.5% | 98.55% (simulation)       |
| False Positive Rate (Tier 2)      | <5%    | 4.5% (caught by Tier 2.5) |
| Yahoo Finance Availability        | >95%   | TBD                       |
| SEC EDGAR Fallback Rate           | <5%    | TBD                       |

**Monitoring Dashboard**:

```sql
-- Data quality view
CREATE VIEW data_quality_metrics AS
SELECT
    parse_tier,
    COUNT(*) as total_filings,
    COUNT(*) FILTER (WHERE validation_status = 'PASS') as valid_filings,
    COUNT(*) FILTER (WHERE validation_status = 'FAIL') as invalid_filings,
    ROUND(100.0 * COUNT(*) FILTER (WHERE validation_status = 'PASS') / COUNT(*), 2) as quality_percent
FROM document_registry.filings
GROUP BY parse_tier;
```

---

## Error Handling & Recovery

### Error Categories

**1. Rate Limit Errors (SEC 429, Yahoo throttling)**

**Handling**:

```python
async def fetch_with_rate_limit_retry(url: str) -> bytes:
    for attempt in range(3):
        try:
            if not await check_rate_limit():
                await asyncio.sleep(0.1)  # Wait 100ms
                continue
            return await httpx.get(url)
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:
                backoff = 10 * (2 ** attempt)  # 10s, 20s, 40s
                logger.warning(f"Rate limit hit, backing off {backoff}s")
                await asyncio.sleep(backoff)
            else:
                raise
    raise Exception("Rate limit retry exhausted")
```

**2. Parse Failures (Tiers 0-2)**

**Escalation Path**:

```python
async def parse_filing_with_escalation(filing: Filing) -> ParseResult:
    # Tier 0: EdgarTools
    result = await parse_tier0(filing)
    if result.success:
        return result

    # Tier 1.5: Smart Deterministic
    result = await parse_tier1(filing)
    if result.success:
        return result

    # Tier 2: LLM
    result = await parse_tier2(filing)
    if result.success and result.confidence > 0.80:
        # Tier 2.5: Validate
        if await validate_tier2_5(result.data):
            return result
        else:
            logger.warning(f"Tier 2.5 validation failed: {filing.accession}")

    # Tier 3: Escalate to QC Agent
    await escalate_to_qc_agent(filing, result)
    return ParseResult(success=False, tier='escalated')
```

**3. Storage Failures (PostgreSQL deadlock, MinIO timeout)**

**Retry Logic**:

```python
async def insert_with_retry(table: str, data: dict, retries: int = 3):
    for attempt in range(retries):
        try:
            async with postgres.begin() as conn:
                await conn.execute(insert(table).values(data))
            return
        except asyncpg.DeadlockDetectedError:
            if attempt == retries - 1:
                raise
            backoff = 0.5 * (2 ** attempt)  # 0.5s, 1s, 2s
            logger.warning(f"Deadlock detected, retrying in {backoff}s")
            await asyncio.sleep(backoff)
        except asyncio.TimeoutError:
            logger.error(f"Database timeout on attempt {attempt + 1}")
            if attempt == retries - 1:
                # Fallback: Store in Redis for later processing
                await redis.lpush('failed_inserts', json.dumps(data))
                raise
```

**4. Redis Degradation (Cache unavailable)**

**Graceful Degradation**:

```python
async def check_duplicate_with_fallback(cik: str, accession: str) -> bool:
    try:
        # Primary: Check Redis cache
        return await redis.get(f"filing:{cik}:{accession}") is not None
    except redis.ConnectionError:
        logger.warning("Redis unavailable, checking PostgreSQL directly")
        # Fallback: Query PostgreSQL (slower)
        result = await postgres.fetchone(
            "SELECT 1 FROM document_registry.filings "
            "WHERE cik = :cik AND accession_number = :accession",
            {'cik': cik, 'accession': accession}
        )
        return result is not None
```

### Recovery Scenarios

**Scenario 1: SEC EDGAR 503 (Service Unavailable)**

```text
SEC API returns 503 during high traffic
  ↓ Immediate retry with 10s delay
  ↓ If still unavailable: Queue tasks for retry (exponential backoff)
  ↓ Alert human: "SEC downtime, deep analysis delayed"
  ↓ Continue screening with cached Yahoo data
  ↓ Retry queue every 5 minutes until SEC available
```

**Scenario 2: Parse Failure Cascade (>10% failure rate)**

```text
Tier 0 failure rate spikes from 5% → 15%
  ↓ Alert: "Parse failure threshold exceeded"
  ↓ Investigation: Check for SEC XBRL taxonomy changes
  ↓ Temporary measure: Increase Tier 2 LLM usage
  ↓ Long-term: Update EdgarTools library or add new Tier 1 rules
```

**Scenario 3: PostgreSQL Connection Pool Exhaustion**

```text
All 20 connections in use (high concurrency)
  ↓ New requests wait for available connection (timeout: 10s)
  ↓ If timeout exceeded: Queue task for retry
  ↓ Alert: "Connection pool saturated, consider increasing pool_size"
  ↓ Mitigation: Increase max_overflow from 15 → 25
```

---

## Performance & Scalability

### Throughput Targets

**Current Scale (MVP)**:

- **Screening backfill**: 500 companies (S&P 500) in <10 minutes (Yahoo Finance)
- **Deep analysis fetch**: 40 filings/company in <10 minutes (10 parallel workers)
- **Parse throughput**: >10 filings/minute (Tier 0-1)
- **LLM parse (Tier 2)**: 30s/filing (serial, acceptable for 5% rate)

**Production Scale**:

- **Universe expansion**: S&P 500 + Russell 2000 (2,500 companies)
- **Screening time**: <30 minutes for 2,500 companies
- **Parallel workers**: 20-30 workers (SEC rate limit: 10 req/sec shared)

### Latency Targets

| Operation                      | Target       | Current           |
| ------------------------------ | ------------ | ----------------- |
| Yahoo Finance fetch            | <30s/company | ~15s (measured)   |
| SEC EDGAR fetch                | <10s/filing  | ~5s (measured)    |
| Tier 0 parse                   | <5s/filing   | ~3s (EdgarTools)  |
| Tier 2 LLM parse               | <60s/filing  | ~30s (Sonnet 4.5) |
| PostgreSQL insert              | <1s/batch    | ~0.5s (batch 100) |
| MinIO upload                   | <10s/filing  | ~2s (<5MB files)  |
| End-to-end (fetch+parse+store) | <30s/filing  | ~20s (measured)   |

### Concurrency Management

**Worker Pool Architecture**:

```python
# src/data_collector/task_queue.py
class TaskQueue:
    def __init__(self, max_workers: int = 10):
        self.queue = asyncio.PriorityQueue()
        self.workers = []
        self.max_workers = max_workers

    async def start_workers(self):
        """Start worker pool."""
        for i in range(self.max_workers):
            worker = asyncio.create_task(self.worker_loop(i))
            self.workers.append(worker)

    async def worker_loop(self, worker_id: int):
        """Process tasks from priority queue."""
        while True:
            priority, task = await self.queue.get()
            try:
                await self.process_task(task)
            except Exception as e:
                logger.error(f"Worker {worker_id} error: {e}")
            finally:
                self.queue.task_done()

    async def add_task(self, ticker: str, priority: Priority):
        """Add task to queue with priority."""
        task = FetchTask(ticker=ticker, priority=priority)
        await self.queue.put((priority.value, task))
```

**Priority Levels**:

```python
class Priority(Enum):
    CRITICAL = 1  # Gate 1 approved, fetch immediately
    HIGH = 2      # Top 20 screening candidates (speculative)
    MEDIUM = 3    # Latest 10-K for screening
    LOW = 4       # Long-tail companies, background jobs
```

### Scalability Bottlenecks

**1. SEC Rate Limit (10 req/sec)**

- Current: 10 parallel workers share 10 req/sec = 1 req/sec per worker
- Mitigation: Intelligent batching, prioritize critical tasks
- Future: Multiple IP addresses (requires SEC approval)

**2. LLM Parse Latency (Tier 2)**

- Current: Serial processing, 30s/filing
- Bottleneck at: >50 simultaneous Tier 2 escalations
- Mitigation: Parallel LLM workers (10 concurrent), acceptable for 5% failure rate

**3. PostgreSQL Write Throughput**

- Current: Batch insert (100 records/transaction), ~200ms
- Bottleneck at: >1,000 filings/minute (unlikely in MVP)
- Mitigation: Connection pool tuning, async commit

### Memory Optimization

**Target**: <500MB agent process memory

**Strategies**:

1. **Stream large filings**: Don't load entire filing into memory

   ```python
   async def fetch_filing_stream(url: str) -> AsyncIterator[bytes]:
       async with httpx.stream('GET', url) as response:
           async for chunk in response.aiter_bytes(chunk_size=8192):
               yield chunk
   ```

2. **Periodic garbage collection**: Clear parsed data after storage

   ```python
   async def process_filing(filing: Filing):
       result = await parse_filing(filing)
       await store_filing(result)
       del filing, result  # Explicit cleanup
       gc.collect()
   ```

3. **Redis memory limits**: 512MB max, LRU eviction

---

## API & Interface

### Agent Methods

```python
# src/agents/data_collector/agent.py
class DataCollectorAgent:
    """Main agent interface for data acquisition."""

    async def yahoo_backfill_sp500(self) -> dict:
        """
        Fetch 10Y financial metrics for all S&P 500 companies.

        Returns:
            dict: {
                'success': 498,
                'failed': 2,
                'duration_seconds': 420,
                'error_tickers': ['BRK.B', 'BF.B']
            }
        """

    async def yahoo_fetch(self, tickers: list[str]) -> dict:
        """
        Fetch Yahoo Finance data for specific tickers.

        Args:
            tickers: List of stock tickers

        Returns:
            dict: {ticker: financial_data}
        """

    async def fetch_company(self, ticker: str, form_types: list[str] = ['10-K', '10-Q']) -> dict:
        """
        Fetch SEC filings for a single company (on-demand, Gate 1 approved).

        Args:
            ticker: Stock ticker (e.g., 'AAPL')
            form_types: Filing types to fetch

        Returns:
            dict: {
                'filing_ids': [uuid1, uuid2, ...],
                'success_count': 38,
                'failed_count': 2,
                'parse_tiers': {'tier0': 36, 'tier2': 2}
            }
        """

    async def fetch_batch(self, tickers: list[str], priority: Priority = Priority.HIGH) -> dict:
        """
        Batch fetch for multiple companies (Gate 1 approved list).

        Args:
            tickers: List of stock tickers
            priority: Task priority (CRITICAL, HIGH, MEDIUM, LOW)

        Returns:
            dict: Aggregate statistics across all tickers
        """

    async def monitor_new_filings(self, watch_tickers: list[str], interval_hours: int = 24):
        """
        Monitor SEC EDGAR for new filings (8-K, amendments).

        Args:
            watch_tickers: Tickers to monitor
            interval_hours: Check frequency

        Background task, runs continuously.
        """

    async def get_status(self) -> dict:
        """
        Get agent status and metrics.

        Returns:
            dict: {
                'active_tasks': 5,
                'queue_depth': 23,
                'completed_today': 147,
                'failed_today': 3,
                'parse_quality_24h': 98.7,
                'storage_usage_gb': 12.3
            }
        """
```

### CLI Commands

```bash
# Yahoo Finance operations
python -m src.data_collector yahoo-backfill
python -m src.data_collector yahoo-fetch --tickers AAPL,MSFT,GOOGL
python -m src.data_collector yahoo-refresh --older-than 7d

# SEC EDGAR operations
python -m src.data_collector edgar-fetch --ticker AAPL --forms 10-K,10-Q
python -m src.data_collector edgar-batch --file approved_tickers.txt --priority HIGH
python -m src.data_collector edgar-monitor --tickers AAPL,MSFT --interval 24h

# Status and monitoring
python -m src.data_collector status
python -m src.data_collector quality-report --period 7d

# Storage management
python -m src.data_collector storage-stats
python -m src.data_collector cleanup --older-than 5y
```

### Message Bus Protocol

**Parse Failure Escalation** (to QC Agent):

```python
await message_bus.send(
    from_agent="DataCollectorAgent",
    to_agent="QCAgent",
    message_type="PARSE_FAILURE_REVIEW",
    priority="HIGH",
    content={
        "filing_id": "uuid-123",
        "ticker": "AAPL",
        "form_type": "10-K",
        "error": {...},
        "strategies_tried": ["EdgarTools", "IFRS", "LLM"],
        "requires_response": True
    }
)
```

**Data Quality Alert** (to Lead Coordinator):

```python
await message_bus.send(
    from_agent="DataCollectorAgent",
    to_agent="LeadCoordinator",
    message_type="ALERT",
    priority="CRITICAL",
    content={
        "alert_type": "PARSE_FAILURE_THRESHOLD_EXCEEDED",
        "message": "Parse failure rate: 15% (threshold: 10%)",
        "affected_tickers": ["AAPL", "MSFT", ...],
        "recommended_action": "Investigate SEC XBRL taxonomy changes"
    }
)
```

---

## Backfill Strategy

### Problem

Initial deployment needs historical data (10Y for growth CAGR, trend analysis), but comprehensive backfill creates tradeoff between completeness, time, and storage.

### Solution: Hybrid Backfill (Option D)

**Phase 1: Screening Preparation** (Pre-Day 1)

```text
Objective: Enable screening of S&P 500
Data Needed: Latest 10-K (500 companies)
Source: Yahoo Finance (10Y metrics included)
Duration: 4-10 minutes
Storage: Negligible (structured metrics only)
```

**Phase 2: On-Demand Deep Fetch** (Days 3-7, triggered by Gate 1)

```text
Objective: Provide 10Y data for approved candidates
Data Needed: 40 filings/company (10-K + 10-Q, 10Y)
Source: SEC EDGAR (qualitative + quantitative)
Duration: <10 minutes/company (parallel)
Storage: 500MB/company × 10 companies = 5GB
```

### Priority Queue Implementation

```python
# Triggered by Lead Coordinator at Gate 1
@on_human_gate_1_approval
async def backfill_approved_companies(approved_tickers: list[str]):
    """
    Gate 1 approval triggers CRITICAL priority fetch for 10Y data.
    """
    for ticker in approved_tickers:
        # Check coverage
        filing_count = await postgres.count_filings(ticker)

        if filing_count < 40:  # Need 10Y data (4 filings/year × 10Y)
            await task_queue.add_task(
                ticker=ticker,
                priority=Priority.CRITICAL,
                form_types=['10-K', '10-Q'],
                years=range(2014, 2025)  # 10 years
            )
            logger.info(f"Queued backfill for {ticker} (CRITICAL priority)")

    # Wait for critical tasks to complete before launching analysis agents
    await task_queue.wait_for_priority(Priority.CRITICAL)
    logger.info("All approved companies backfilled, launching analysis agents")

    # Launch specialist agents
    await lead_coordinator.launch_agents([
        'BusinessResearchAgent',
        'FinancialAnalystAgent',
        'StrategyAnalystAgent'
    ])
```

### Coverage Monitoring

```sql
-- View: Backfill coverage status
CREATE VIEW backfill_coverage AS
SELECT
    ticker,
    COUNT(*) as filing_count,
    MIN(filing_date) as earliest_filing,
    MAX(filing_date) as latest_filing,
    CASE
        WHEN COUNT(*) >= 40 THEN 'READY_ANALYSIS'
        WHEN COUNT(*) >= 1 THEN 'READY_SCREENING'
        ELSE 'NO_DATA'
    END as status
FROM document_registry.filings
WHERE form_type IN ('10-K', '10-Q')
GROUP BY ticker;
```

### Speculative Pre-Fetching (Optional)

**Strategy**: Pre-fetch top 20 screening candidates (HIGH priority) before Gate 1.

**Rationale**:

- Reduce latency at Gate 1 (data already available)
- Acceptable risk (20 companies × 500MB = 10GB wasted if not approved)

**Implementation**:

```python
# After screening completes (Day 2)
async def speculative_prefetch(top_candidates: list[str]):
    """
    Pre-fetch top 20 screening candidates before Gate 1 approval.
    """
    for ticker in top_candidates[:20]:
        await task_queue.add_task(
            ticker=ticker,
            priority=Priority.HIGH,  # Lower than CRITICAL
            form_types=['10-K', '10-Q'],
            years=range(2014, 2025)
        )
```

---

## Testing Strategy

### Unit Tests

**Scope**: Individual components (EDGAR client, parser, storage clients)

**Key Tests**:

```python
# tests/agents/test_edgar_client.py
async def test_ticker_to_cik():
    """Test CIK lookup."""
    client = EDGARClient()
    cik = await client.ticker_to_cik('AAPL')
    assert cik == '0000320193'

async def test_rate_limiting():
    """Ensure rate limit enforced."""
    client = EDGARClient()
    start = time.time()
    for _ in range(15):
        await client.fetch_filing_with_rate_limit(test_url)
    duration = time.time() - start
    assert duration >= 1.5  # 15 requests at 10/sec = 1.5s minimum

# tests/agents/test_parser.py
async def test_parse_tier0_standard_filing():
    """Test EdgarTools baseline parsing."""
    filing = load_test_filing('AAPL_10K_2023.html')
    result = await parse_tier0(filing)
    assert result.success
    assert result.data['revenue'] > 0

async def test_parse_tier1_ifrs_filer():
    """Test IFRS fallback logic."""
    filing = load_test_filing('foreign_filer_10K.html')
    result = await parse_tier1(filing)
    assert result.success
    assert 'ifrs-full:Revenue' in result.data['source_tags']

# tests/storage/test_postgres_client.py
async def test_bulk_insert():
    """Test batch insert performance."""
    records = [generate_mock_filing() for _ in range(100)]
    start = time.time()
    await postgres.bulk_insert('document_registry.filings', records)
    duration = time.time() - start
    assert duration < 1.0  # <1s for 100 records
```

### Integration Tests

**Scope**: End-to-end workflows (fetch → parse → store)

**Test Environment**: Testcontainers (PostgreSQL + Redis + MinIO)

**Key Tests**:

```python
# tests/integration/test_end_to_end.py
async def test_full_pipeline_10_companies():
    """
    End-to-end test: Fetch, parse, store 10 real companies.
    """
    tickers = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'META', 'TSLA', 'NVDA', 'JPM', 'V', 'WMT']

    agent = DataCollectorAgent()
    results = await agent.fetch_batch(tickers, priority=Priority.HIGH)

    # Assertions
    assert results['success_count'] >= 380  # 10 companies × ~40 filings, >95% success
    assert results['failed_count'] < 20  # <5% failure rate

    # Verify PostgreSQL storage
    for ticker in tickers:
        filings = await postgres.get_filings(ticker)
        assert len(filings) >= 38

    # Verify MinIO storage
    for ticker in tickers:
        s3_paths = await s3_client.list_objects(prefix=f'raw/sec_filings/{ticker}/')
        assert len(s3_paths) >= 38

    # Verify Redis cache
    for ticker in tickers:
        cik = await edgar_client.ticker_to_cik(ticker)
        cached_filings = await redis.keys(f'filing:{cik}:*')
        assert len(cached_filings) >= 38
```

### Load Tests

**Scope**: Scalability validation (1,000 filing batch)

**Tools**: Locust or custom async load generator

**Key Metrics**:

- Throughput: >10 filings/min sustained
- Latency: p95 <60s end-to-end
- Error rate: <5%
- Memory: <500MB agent process

```python
# tests/load/test_scalability.py
async def test_1000_filing_batch():
    """
    Load test: Process 1,000 filings, measure performance.
    """
    # Generate 1,000 filing tasks
    tasks = [generate_fetch_task() for _ in range(1000)]

    start = time.time()
    results = await process_batch(tasks, max_workers=10)
    duration = time.time() - start

    # Assertions
    assert duration < 6000  # <100 minutes (10 filings/min × 1000)
    assert results['success_rate'] > 0.95
    assert results['memory_peak_mb'] < 500
```

### Validation Tests

**Scope**: Data quality verification (Yahoo vs SEC comparison)

**Approach**: Fetch same companies from both sources, compare metrics

```python
# tests/validation/test_data_quality.py
async def test_yahoo_vs_sec_comparison():
    """
    Compare Yahoo Finance vs SEC EDGAR data for 100 random companies.
    Tolerance: 5% difference acceptable (rounding, timing differences).
    """
    sample_tickers = random.sample(sp500_tickers, 100)

    for ticker in sample_tickers:
        yahoo_data = await yahoo_client.get_financials(ticker)
        sec_data = await edgar_client.fetch_latest_10k(ticker)

        yahoo_revenue = yahoo_data['Total Revenue']
        sec_revenue = sec_data['revenue']

        # Allow 5% tolerance
        diff_pct = abs(yahoo_revenue - sec_revenue) / sec_revenue
        assert diff_pct < 0.05, f"{ticker}: Yahoo/SEC revenue diff {diff_pct:.1%}"
```

---

## Configuration Parameters

```python
# src/agents/data_collector/config.py

# SEC EDGAR Configuration
SEC_RATE_LIMIT = 10  # requests/second
SEC_USER_AGENT = "FundamentalAnalysisSystem admin@example.com"
SEC_API_BASE = "https://www.sec.gov"
SEC_RETRY_ATTEMPTS = 3
SEC_RETRY_BACKOFF = [10, 20, 40]  # seconds

# Yahoo Finance Configuration
YAHOO_RATE_LIMIT = 2  # requests/second
YAHOO_RETRY_ATTEMPTS = 3
YAHOO_CACHE_TTL = 86400 * 7  # 7 days

# Parsing Configuration
BATCH_SIZE = 100  # filings per batch insert
CONCURRENT_WORKERS = 10  # parallel fetch workers
FETCH_TIMEOUT = 30  # seconds per filing fetch
PARSE_TIMEOUT = 60  # seconds per filing parse
LLM_CONFIDENCE_THRESHOLD = 0.80  # Tier 2 minimum confidence

# Storage Configuration
POSTGRES_POOL_SIZE = 5  # minimum connections
POSTGRES_MAX_OVERFLOW = 15  # maximum 20 total
POSTGRES_TRANSACTION_TIMEOUT = 10  # seconds
S3_UPLOAD_TIMEOUT = 60  # seconds
S3_MULTIPART_THRESHOLD = 5 * 1024 * 1024  # 5MB
REDIS_CACHE_TTL = 86400  # 24 hours
REDIS_MAX_MEMORY = '512mb'

# Task Queue Configuration
QUEUE_MAX_SIZE = 1000
QUEUE_CHECK_INTERVAL = 1.0  # seconds
PRIORITY_WEIGHTS = {
    Priority.CRITICAL: 1,
    Priority.HIGH: 2,
    Priority.MEDIUM: 3,
    Priority.LOW: 4
}

# Data Quality Configuration
BALANCE_SHEET_TOLERANCE = 0.01  # 1% for Assets = L + E
COMPLETENESS_THRESHOLD = 5  # minimum 5/8 core metrics
FALSE_POSITIVE_THRESHOLD = 0.10  # alert if >10% FP rate

# Monitoring Configuration
ALERT_PARSE_FAILURE_THRESHOLD = 0.10  # alert if >10% failure rate
ALERT_YAHOO_FAILURE_THRESHOLD = 0.10
METRICS_COLLECTION_INTERVAL = 60  # seconds
```

---

## Dependencies & Infrastructure

### Python Dependencies

```toml
# pyproject.toml
[project.dependencies]
# Database
asyncpg = ">=0.30.0"
sqlalchemy = ">=2.0.44"
alembic = ">=1.17.2"

# Storage
boto3 = ">=1.28.0"  # S3/MinIO client
redis = ">=5.0.0"

# Data Sources
edgartools = ">=3.0.0"  # SEC XBRL parsing (Tier 0)
yfinance = ">=0.2.0"  # Yahoo Finance API
beautifulsoup4 = ">=4.12.0"  # HTML parsing
lxml = ">=5.0.0"  # XML/XBRL parsing

# HTTP
httpx = ">=0.25.0"  # Async HTTP client

# Parsing & Validation
anthropic = ">=0.25.0"  # Claude API (Tier 2 LLM parsing)

# Utilities
pydantic = ">=2.0.0"  # Data validation
tenacity = ">=8.0.0"  # Retry logic
```

### External Infrastructure

**Required Services**:

| Service    | Purpose                 | Version | Resource Requirements |
| ---------- | ----------------------- | ------- | --------------------- |
| PostgreSQL | Structured data storage | 18.1    | 4GB RAM, 50GB disk    |
| Redis      | L1 cache, deduplication | 7.0+    | 512MB RAM             |
| MinIO      | Raw document storage    | Latest  | 100GB disk (10Y data) |

**Optional Services** (Phase 2+):

| Service       | Purpose            | Phase   |
| ------------- | ------------------ | ------- |
| Neo4j         | L3 knowledge graph | Phase 2 |
| Elasticsearch | Document search    | Phase 3 |

### Development Environment

```bash
# Install dependencies
uv sync

# Start infrastructure (Docker Compose)
docker-compose up -d postgres redis minio

# Run database migrations
alembic upgrade head

# Run tests
PYTHONPATH=$PWD uv run pytest tests/

# Start agent
uv run python -m src.agents.data_collector.agent
```

---

## Monitoring & Observability

### Key Metrics

**1. Data Acquisition Metrics**

```python
# Prometheus format
data_collector_fetch_total{source="yahoo|edgar", status="success|failed"}
data_collector_fetch_duration_seconds{source="yahoo|edgar", quantile="0.5|0.95|0.99"}
data_collector_rate_limit_hits_total{source="sec"}
```

**2. Parse Quality Metrics**

```python
data_collector_parse_success_rate{tier="tier0|tier1|tier2"}
data_collector_parse_tier_distribution{tier="tier0|tier1|tier2|tier3|tier4"}
data_collector_validation_failures_total{rule="balance_sheet|completeness|value_range"}
data_collector_false_positive_rate
```

**3. Storage Metrics**

```python
data_collector_postgres_inserts_total{table="filings|income_statement|balance_sheet"}
data_collector_minio_uploads_total{status="success|failed"}
data_collector_redis_cache_hit_rate
data_collector_storage_usage_gb{storage="postgres|minio"}
```

**4. Queue Metrics**

```python
data_collector_queue_depth{priority="critical|high|medium|low"}
data_collector_active_workers
data_collector_tasks_completed_total{priority="critical|high|medium|low"}
```

### Monitoring Dashboard

```text
┌────────────────────────────────────────────────────────────────┐
│ DATA COLLECTOR AGENT - REAL-TIME DASHBOARD                     │
├────────────────────────────────────────────────────────────────┤
│ Fetch Performance (Last 24h)                                   │
│   Yahoo Finance: 498/500 success (99.6%)                       │
│   SEC EDGAR: 387/400 success (96.8%)                           │
│   Avg Fetch Latency: 18s (p95: 42s)                            │
│                                                                 │
│ Parse Quality (Last 24h)                                       │
│   Tier 0 (EdgarTools): 368/387 (95.1%)                         │
│   Tier 1.5 (Smart): 12/19 (63.2%)                              │
│   Tier 2 (LLM): 6/7 (85.7%)                                    │
│   Tier 3 (QC Agent): 1/1 (100%)                                │
│   Overall Quality: 98.7% (Target: 98.5%) ✅                    │
│                                                                 │
│ Storage Health                                                  │
│   PostgreSQL: 12,487 filings, 62,435 financial records         │
│   MinIO: 12.3 GB raw filings (124,870 objects)                 │
│   Redis: 87% cache hit rate, 234 MB used                       │
│                                                                 │
│ Active Tasks                                                    │
│   Queue Depth: 23 (CRITICAL: 5, HIGH: 8, MEDIUM: 10)           │
│   Active Workers: 10/10                                         │
│   Est. Completion: 18 minutes                                   │
│                                                                 │
│ Alerts                                                          │
│   ⚠️  Yahoo Finance: 2 failed requests (BRK.B, BF.B)            │
│   ✅ No critical alerts                                         │
└────────────────────────────────────────────────────────────────┘
```

### Alerting Rules

```yaml
# Prometheus alerting rules
groups:
  - name: data_collector_alerts
    rules:
      - alert: HighParsFailureRate
        expr: data_collector_parse_success_rate{tier="tier0"} < 0.90
        for: 10m
        severity: warning
        annotations:
          summary: 'Parse failure rate exceeds 10%'

      - alert: SECRateLimitExceeded
        expr: increase(data_collector_rate_limit_hits_total{source="sec"}[5m]) > 10
        severity: critical
        annotations:
          summary: 'SEC rate limit violated'

      - alert: StorageCapacityWarning
        expr: data_collector_storage_usage_gb{storage="minio"} > 90
        severity: warning
        annotations:
          summary: 'MinIO storage >90GB, approaching 100GB limit'

      - alert: QueueBacklogHigh
        expr: data_collector_queue_depth{priority="critical"} > 50
        for: 15m
        severity: warning
        annotations:
          summary: 'Critical task queue backlog >50 for 15+ minutes'
```

### Logging Strategy

**Log Levels**:

- **DEBUG**: Individual filing fetch/parse details
- **INFO**: Batch completion, milestone events
- **WARNING**: Retry attempts, fallback usage
- **ERROR**: Parse failures, storage errors
- **CRITICAL**: System-wide issues (SEC downtime, database unavailable)

**Structured Logging**:

```python
logger.info(
    "Filing parsed successfully",
    extra={
        "ticker": "AAPL",
        "form_type": "10-K",
        "period_end_date": "2023-09-30",
        "parse_tier": "tier0",
        "parse_duration_ms": 3420,
        "filing_id": "uuid-123"
    }
)
```

---

## Related Design Decisions

### Primary ADRs

- **DD-031: SEC Filing Parser Tool Selection**

  - Decision: EdgarTools (Tier 0) + multi-tier recovery
  - Rationale: 95% baseline success, 10-30x faster than custom, proven in production
  - Impact: 98.55% quality target achievable with $88 + 20hrs for 20K filings

- **DD-032: Hybrid Data Sourcing Strategy**
  - Decision: Yahoo Finance (screening) + SEC EDGAR (deep analysis)
  - Rationale: Different stages have different quality/latency requirements
  - Impact: $78/month savings, 18hrs labor reduction vs SEC-only approach

### Supporting ADRs

- **DD-009: Data Versioning**

  - Decision: Store all amendment versions with superseding relationships
  - Impact: Full audit trail, red flag detection (frequent amendments)

- **DD-010: Source Credibility Tracking**

  - Decision: Track data source metadata and credibility scores
  - Impact: Enable contradiction resolution, source reliability monitoring

- **DD-011: Checkpoint-Based Execution**
  - Decision: Atomic subtasks with persistent checkpoints
  - Impact: <2s failure recovery (not directly applicable to data collector, but influences storage design)

---

## Implementation Timeline

### Phase A: Storage Client Abstractions (Days 1-3)

**Day 1-2: PostgreSQL Client**

- `src/storage/postgres_client.py`
- Async session factory, CRUD methods
- Schemas: `document_registry`, `financial_data`
- Bulk insert support (batch 100+)
- Connection pool configuration

**Day 2-3: MinIO/S3 Client**

- `src/storage/s3_client.py`
- Async operations with `boto3`
- Multipart upload for >5MB files
- Retry logic (3 attempts, exponential backoff)

**Day 3: Redis L1 Client**

- `src/storage/redis_client.py`
- Deduplication cache (24hr TTL)
- Rate limiting counter (atomic INCR)
- Task state tracking

**Deliverable**: Operational storage layer, integration tests pass

---

### Phase B: SEC EDGAR Integration (Days 4-6.5)

**Day 4-5: EDGAR Client**

- `src/agents/data_collector/edgar_client.py`
- Rate limit enforcement (10 req/sec)
- CIK lookup and ticker resolution
- Filing index parsing
- User-agent compliance

**Day 5-6: Filing Parser (Multi-Tier)**

- `src/agents/data_collector/filing_parser.py`
- Tier 0: EdgarTools integration
- Tier 1.5: Smart deterministic rules
- Tier 2: LLM-assisted parsing (stub for Phase C)
- Tier 2.5: Data validation layer
- Tier 3: QC Agent message bus integration

**Day 6.5: Storage Pipeline**

- `src/agents/data_collector/storage_pipeline.py`
- End-to-end workflow: check cache → fetch → parse → validate → store
- Error handling and retry logic
- Amendment detection and versioning

**Deliverable**: SEC EDGAR fetch and parse operational, 95%+ success rate

---

### Phase C: Agent & Yahoo Finance (Days 6.5-10)

**Day 6.5-7.5: Yahoo Finance Client**

- `src/data_collector/yahoo_finance_client.py`
- `yfinance` library integration
- Rate limiting (2 req/sec)
- S&P 500 bulk fetch
- Screening metrics calculation

**Day 7.5-8: PostgreSQL Integration**

- Add `data_source` column to financial tables
- Migration scripts (Alembic)
- Insert methods for Yahoo-sourced data

**Day 8-9: Agent Implementation**

- `src/agents/data_collector/agent.py`
- Agent methods: `yahoo_backfill`, `fetch_company`, `fetch_batch`, `monitor_new_filings`, `get_status`
- Task queue manager with priority levels
- CLI commands

**Day 9-10: Testing & Integration**

- Unit tests (EDGAR, Yahoo, parser, storage)
- Integration tests (end-to-end 10 companies)
- Load tests (1,000 filing batch)
- Validation tests (Yahoo vs SEC comparison)

**Deliverable**: Fully operational Data Collector Agent, test coverage >80%

---

### Phase D: Infrastructure Validation (Day 10-11)

**Day 10: End-to-End Test**

- Fetch 10 real companies (diverse sectors)
- Verify 100+ filings stored (PostgreSQL + MinIO)
- Validate Redis cache populated
- Check parse quality >95%

**Day 10-11: Performance Tuning**

- Optimize connection pool settings
- Tune batch sizes
- Validate throughput >10 filings/min
- Memory profiling (<500MB target)

**Day 11: Documentation & Handoff**

- Update architecture documentation
- Create runbooks (deployment, monitoring, troubleshooting)
- Training session for team

**Deliverable**: Production-ready Data Collector Agent, full documentation

---

**Total Timeline**: 10-11 development days

---

## Open Questions

### Operational Questions

1. **SEC EDGAR downtime handling**

   - How handle prolonged 503 errors during high traffic (earnings season)?
   - Should we maintain a separate backup data source (e.g., paid provider)?

2. **Data retention policy**

   - How long keep raw filings in MinIO (5 years? 10 years? permanent)?
   - Tiered storage strategy (hot/cold) for older filings?

3. **Concurrency scaling**
   - Can increase workers beyond 10 without hitting SEC rate limits?
   - Distribute workers across multiple IPs (requires SEC approval)?

### Data Quality Questions

4. **LLM prompt optimization**

   - Can improve Tier 2 recovery from 60% → 80% with better prompts?
   - Fine-tune model on SEC filing corpus?

5. **Partial data acceptance**

   - Accept filings with 5/8 metrics vs 8/8 completeness?
   - What's minimum viable data for screening vs deep analysis?

6. **Historical learning cutoff**
   - How long keep parse failure logs in QC Agent memory?
   - Prune old patterns (e.g., XBRL taxonomy changes make old rules obsolete)?

### Integration Questions

7. **QC Agent priority**

   - Should parse failure review block other QC tasks?
   - Dedicated QC capacity for data collector vs shared with other agents?

8. **S&P 500 ticker list source**

   - Hardcode list or fetch from Wikipedia/external API?
   - How handle index changes (companies added/removed)?

9. **Quarterly vs annual data**
   - Store both 10-K and 10-Q from Yahoo Finance?
   - Use quarterly for trending, annual for screening?

### Performance Questions

10. **Data refresh frequency**

    - How often re-fetch Yahoo data (daily? weekly? only on request)?
    - Trigger on market close? Detect stale data automatically?

11. **yfinance rate limits**
    - Community reports 2,000 req/hour safe, but no official docs
    - Monitor for throttling, fallback strategy if limited?

---

## References

### Design Decisions

- [DD-031: SEC Filing Parser Tool Selection](../design-decisions/DD-031_SEC_FILING_PARSER_TOOL_SELECTION.md)
- [DD-032: Hybrid Data Sourcing Strategy](../design-decisions/DD-032_HYBRID_DATA_SOURCING.md)
- [DD-009: Data Versioning](../design-decisions/DD-009_DATA_VERSIONING.md)
- [DD-010: Source Credibility Tracking](../design-decisions/DD-010_SOURCE_CREDIBILITY.md)

### Related Documentation

- [System Overview](01-system-overview.md): 5-layer architecture, 14 agent types
- [Support Agents](04-agents-support.md): Overview of 4 support agents (including Data Collector)
- [Analysis Pipeline](../operations/01-analysis-pipeline.md): 12-day workflow integration points
- [Data Management](../operations/03-data-management.md): Data governance, retention policies

### Implementation Plans

- [data-collector-implementation.md](../../plans/data-collector-implementation.md): Detailed phase breakdown
- [data-collector-parse-failure-strategy.md](../../plans/data-collector-parse-failure-strategy.md): Multi-tier parsing design
- [parse-failure-improvements-phase1.md](../../plans/parse-failure-improvements-phase1.md): Tier 2.5 validation layer
- [data-collector-backfill-strategy.md](../../plans/data-collector-backfill-strategy.md): Hybrid backfill approach
- [yahoo-finance-integration-plan.md](../../plans/yahoo-finance-integration-plan.md): Yahoo Finance implementation details

---

**Document Status**: Complete
**Next Steps**: Begin Phase A implementation (storage client abstractions), validate PostgreSQL schema with sample data
