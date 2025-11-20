# Data Collector Implementation Plan

**Status**: Ready to implement
**Phase**: Phase 1 - Foundation
**Estimated Timeline**: 8-11 days
**Dependencies**: PostgreSQL, MinIO, Redis L1 (all operational)

---

## 1. Infrastructure Status Verification

### Current Completion: 60%

#### ✅ Operational Components

**_PostgreSQL (Structured Data)_**

- Docker service: `postgres:18.1` on port 5432
- Schema: 8 schemas, 15+ tables fully migrated via Alembic
- Key schemas for data collector:
  - `document_registry`: Track all fetched documents
  - `financial_data`: Store structured financial statements
  - `metadata`: Company and filing metadata
- Dependencies: `asyncpg>=0.30.0`, `sqlalchemy>=2.0.44`, `alembic>=1.17.2`
- Migration: `a125ac7b2db7_initial_schema.py` deployed
- **Gap**: No Python client code yet

**_MinIO/S3 (Object Storage)_**

- Docker service: `minio/minio:latest` on ports 9000/9001
- Buckets created via `scripts/setup_minio.sh`:
  - `raw` (versioning enabled): For SEC filings
  - `processed`: For parsed financial statements
  - `outputs`: For generated reports
- Storage capacity: 10-15TB planned
- **Gap**: No Python client (boto3/minio SDK not in dependencies)

**_Redis L1 (Working Memory)_**

- Docker service: `redis:latest` on port 6379
- Persistence: AOF + RDB hybrid (DD-028)
- Use cases for data collector:
  - Deduplication cache (check if filing already fetched)
  - Active task tracking (in-progress fetches)
  - 24h TTL for working memory
- Dependencies: `redis>=5.0.0`
- **Gap**: No Python client wrapper

**_Elasticsearch (Document Search)_**

- Docker service: `elasticsearch:8.14.0` on port 9200
- Indices: `sec_filings`, `transcripts`, `news` (created but empty)
- Client exists: `src/storage/search_tool.py`
- **Deferred**: Document indexing to Phase 2 (analyst agents need search, not collector)

#### ❌ Not Needed for Data Collector

**_Neo4j (L3 Knowledge Graph)_**

- Status: Not implemented
- Why deferred: Data collector fetches/stores raw data only
- Graph relationships created by analyst agents (Business Research, Financial Analyst) during analysis
- Phase 2 dependency for analyst agents, NOT data collector

**_Redis L2 (Agent Cache)_**

- Status: Operational (port 6380) but not needed yet
- Why deferred: Used by analyst agents for caching recent analysis context
- Data collector uses only L1 for deduplication

---

## 2. Memory Requirements Analysis

### Data Collector Memory Tier Usage

**L1 Working Memory (Redis, port 6379)** - ✅ REQUIRED

- **Deduplication**: Cache CIK+AccessionNumber to prevent refetching
- **Task state**: Track in-progress downloads (prevent duplicate concurrent fetches)
- **Rate limiting**: Track request timestamps for SEC 10 req/sec limit
- **TTL**: 24h (cleared after successful fetch)

**PostgreSQL** - ✅ REQUIRED

- **document_registry schema**: Record all fetched filings (ticker, filing_date, form_type, s3_path)
- **financial_data schema**: Store parsed financial statements (revenue, earnings, balance sheet)
- **metadata schema**: Company info (CIK, ticker, sector, industry)

**MinIO** - ✅ REQUIRED

- **raw/sec_filings/**: Upload complete filing documents (HTML, XBRL)
- **Path structure**: `raw/sec_filings/{ticker}/{year}/{accession_number}.html`
- **Versioning**: Enabled for audit trail

**L2 Agent Cache (Redis, port 6380)** - ❌ NOT NEEDED

- Used by analyst agents to cache recent analysis summaries
- Data collector doesn't analyze, just fetches

**L3 Knowledge Graph (Neo4j + Elasticsearch)** - ❌ NOT NEEDED

- Graph relationships (Company → Analysis → Pattern) created during analysis phase
- Analyst agents populate L3 when they run business/financial research
- Data collector is stateless fetcher, doesn't create relationships

### Conclusion

**Neo4j is NOT a blocker** for data collector implementation. Can proceed with PostgreSQL + MinIO + Redis L1 only.

---

## 3. Implementation Phases

### Phase A: Storage Client Abstractions (2-3 days)

**A1. PostgreSQL Client** (`src/storage/postgres_client.py`)

```python
# Interface design
class PostgresClient:
    async def insert_document_metadata(ticker, filing_date, form_type, s3_path)
    async def insert_financial_data(ticker, period, metrics_dict)
    async def bulk_insert_financials(records_list)
    async def check_filing_exists(cik, accession_number) -> bool
    async def get_company_metadata(ticker) -> dict
```

**Implementation**:

- Async session factory using existing Alembic schema
- CRUD methods for `document_registry`, `financial_data`, `metadata` schemas
- Bulk insert support (batch 100+ filings per transaction)
- Connection pool configuration (min 5, max 20 connections)
- Error handling: deadlock retry, connection timeout recovery
- Transaction management: rollback on failure

**Testing**:

- Unit tests: Insert/query operations
- Integration tests: Bulk insert 1000 records, verify integrity
- Error cases: Connection failure, constraint violations

**A2. MinIO/S3 Client** (`src/storage/s3_client.py`)

```python
# Interface design
class S3Client:
    async def upload_filing(ticker, year, accession_number, content) -> str
    async def download_filing(s3_path) -> bytes
    async def list_filings(ticker, year) -> list[str]
    async def filing_exists(s3_path) -> bool
```

**Implementation**:

- Add `boto3>=1.28.0` to pyproject.toml
- AWS S3 client configured for MinIO endpoint (<http://localhost:9000>)
- Multipart upload for files >5MB (SEC filings can be 10-50MB)
- Path structure: `raw/sec_filings/{ticker}/{year}/{accession_number}.html`
- Error handling: network timeouts, bucket not found, insufficient permissions
- Retry logic: 3 attempts with exponential backoff (1s, 2s, 4s)

**Configuration**:

```python
# Environment variables
MINIO_ENDPOINT = "localhost:9000"
MINIO_ACCESS_KEY = "minioadmin"
MINIO_SECRET_KEY = "minioadmin"
MINIO_BUCKET_RAW = "raw"
```

**Testing**:

- Unit tests: Upload/download round-trip
- Integration tests: Upload 100 files, verify all retrievable
- Error cases: Network failure, large file handling (>50MB)

**A3. Redis L1 Client** (`src/storage/redis_client.py`)

```python
# Interface design
class RedisL1Client:
    async def check_filing_cached(cik, accession_number) -> bool
    async def mark_filing_cached(cik, accession_number, ttl=86400)
    async def get_active_tasks() -> list[str]
    async def mark_task_active(task_id, ttl=3600)
    async def mark_task_complete(task_id)
    async def increment_rate_limit_counter() -> int
```

**Implementation**:

- Connect to redis_l1 (port 6379) with connection pool
- Key patterns:
  - `filing:{cik}:{accession}` → "1" (TTL 24h) for deduplication
  - `task:active:{task_id}` → JSON task state (TTL 1h)
  - `ratelimit:{current_second}` → counter (TTL 2s) for SEC 10 req/sec
- Atomic operations: INCR for rate limiting, SETNX for task locking
- Error handling: connection failures, Redis OOM

**Testing**:

- Unit tests: Cache hit/miss, TTL expiry
- Integration tests: Concurrent task locking (10 parallel workers)
- Rate limit tests: 100 req/sec burst, verify throttling to 10 req/sec

---

### Phase B: SEC EDGAR Integration (3-4 days)

**B1. EDGAR Client** (`src/agents/data_collector/edgar_client.py`)

**SEC EDGAR API Specifications**:

- Base URL: `https://www.sec.gov/cgi-bin/browse-edgar`
- Rate limit: **10 requests/second** (SEC requirement)
- User-Agent: Required format `"Company Name contact@email.com"`
- No API key required (public data)
- Filings available: 10-K, 10-Q, 8-K, DEF 14A (proxy statements)

```python
# Interface design
class EDGARClient:
    async def get_company_filings(cik: str, form_types: list[str], count: int = 100)
    async def download_filing(accession_number: str) -> bytes
    async def get_company_info(ticker: str) -> dict
    async def search_companies(query: str) -> list[dict]
```

**Implementation**:

- Rate limiting: Redis counter + asyncio.sleep() to enforce 10 req/sec
- CIK lookup: Map ticker → CIK via SEC company tickers JSON
- Filing index parsing: Extract accession numbers, filing dates, form types
- User-Agent compliance: `"FundamentalAnalysisSystem admin@example.com"`
- Error handling: 429 rate limit responses, 503 SEC downtime
- Retry logic: Exponential backoff for transient failures

**SEC API Endpoints**:

```python
COMPANY_SEARCH = "https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={cik}&type={form_type}&count={count}"
FILING_DOWNLOAD = "https://www.sec.gov/Archives/edgar/data/{cik}/{accession_no_dashes}/{accession}.txt"
COMPANY_TICKERS = "https://www.sec.gov/files/company_tickers.json"
```

**Testing**:

- Unit tests: CIK lookup, filing URL construction
- Integration tests: Fetch real AAPL 10-K (verify SEC connectivity)
- Rate limit tests: 100 concurrent requests, verify <10 req/sec actual
- Mock tests: SEC 429/503 error responses

**B2. Filing Parser** (`src/agents/data_collector/filing_parser.py`)

**Tool Selection Decision** (DD-027): Use **EdgarTools** as Tier 0 foundation + custom multi-tier recovery

**Research Finding**: Existing SEC filing parsers (EdgarTools, py-xbrl, Calcbench, sec-api.io) achieve 92-95% success rate but **none handle critical edge cases**:

- Context disambiguation (restated vs original, consolidated vs parent-only)
- Mixed GAAP/IFRS extraction
- Holding companies, SPACs, data validation
- Cost: Commercial tools $20K-$50K vs our $88 for 20K filings

**Multi-Tier Parsing Architecture**:

```python
# Interface design
class FilingParser:
    # Tier 0: EdgarTools (handles 95% of filings fast)
    async def parse_with_edgartools(accession_number: str) -> dict

    # Tier 1.5: Smart deterministic fallback (metadata-aware)
    async def parse_smart_deterministic(filing_content: bytes, metadata: dict) -> dict

    # Tier 2: LLM-assisted parsing (semantic understanding)
    async def parse_with_llm(filing_content: bytes, metadata: dict) -> dict

    # Tier 2.5: Data validation layer
    async def validate_financials(data: dict, metadata: dict) -> tuple[bool, list[str]]

    # Helper methods
    def extract_metadata(filing_content: bytes) -> dict
    def extract_text(filing_content: bytes) -> str
```

**Tier 0: EdgarTools Foundation**

- **What it handles**: 95% of standard filings (10-K, 10-Q, 8-K, 20-F)
- **Features**: Fast (10-30x speedup), XBRL standardization, multi-period analysis
- **Limitations**: No context disambiguation, no custom validation
- **Cost**: Free, open source

```python
from edgartools import Filing

filing = Filing(accession_number)
xbrl = filing.xbrl()
financials = xbrl.statements  # Income, balance sheet, cash flow
```

**Tier 1.5: Smart Deterministic Fallback**

- **When triggered**: EdgarTools fails or returns incomplete data
- **Features**: Metadata-aware tag selection (IFRS vs US-GAAP), context disambiguation, encoding fixes
- **Recovery rate**: 35% of Tier 0 failures
- **Implementation**: Custom lxml-based parser with business logic

**Metadata Extraction**:

- Ticker, CIK, company name
- Filing date, period end date, fiscal year/quarter
- Form type (10-K, 10-Q, 8-K, 20-F)
- Accounting standard (US-GAAP vs IFRS)
- Company type (operating, holding company, SPAC)
- Accession number (unique identifier)

**XBRL Financial Parsing** (Priority):

- Income statement: Revenue, operating income, net income, EPS
- Balance sheet: Assets, liabilities, equity, cash, debt
- Cash flow: Operating CF, investing CF, financing CF
- Tag support: `us-gaap:*`, `ifrs-full:*`, custom extensions

**Text Extraction** (Phase 2):

- Item 1: Business description
- Item 7: MD&A (Management Discussion & Analysis)
- Item 8: Financial statements
- Risk factors, legal proceedings

**Data Validation (Tier 2.5)**:

- Accounting standard consistency (IFRS filer shouldn't have US-GAAP primary tags)
- Balance sheet equation: Assets = Liabilities + Equity (1% tolerance)
- Holding company consolidated check
- Value ranges: Revenue ≥$0, net income vs revenue reasonableness
- Completeness: Minimum 5/8 core metrics

**Dependencies**:

```toml
edgartools = "^3.0.0"  # Tier 0 XBRL parser (10-30x faster)
beautifulsoup4 = "^4.12.0"  # HTML text extraction
lxml = "^5.0.0"  # Tier 1.5 custom XBRL parsing
```

**Testing**:

- Unit tests: Parse sample 10-K XBRL (AAPL Q4 2023)
- Tier 0 tests: EdgarTools integration, verify 95% baseline
- Tier 1.5 tests: Metadata-aware parsing, context disambiguation
- Validation tests: Reject false positives, balance sheet checks
- Edge cases: Missing tags, IFRS filers, holding companies, SPACs, amended filings

**B3. Storage Pipeline** (`src/agents/data_collector/storage_pipeline.py`)

**Workflow**:

```text
1. Check Redis L1 cache → if exists, skip
2. Fetch filing from SEC EDGAR
3. Upload raw filing to MinIO
4. Parse filing metadata + financials
5. Insert metadata to PostgreSQL document_registry
6. Insert financials to PostgreSQL financial_data
7. Mark filing cached in Redis L1 (24h TTL)
8. Log success
```

```python
# Interface design
class StoragePipeline:
    async def process_filing(cik: str, accession_number: str, form_type: str)
    async def process_batch(filings: list[dict])
    async def retry_failed(filing_id: str)
```

**Implementation**:

- Orchestrate EDGAR client + parser + storage clients
- Deduplication: Check Redis L1 before fetching (skip if cached)
- Atomic transactions: PostgreSQL insert + MinIO upload succeed/fail together
- Error handling: Partial failure recovery (retry individual filings)
- Progress tracking: Log each stage (fetch, parse, store)
- Batch processing: Process 100 filings in parallel (10 concurrent workers)

**Error Handling**:

- SEC rate limit (429): Sleep 10s, retry
- Parse failure: Log error, store raw filing only, mark for manual review
- Database deadlock: Retry transaction 3x
- MinIO upload failure: Retry 3x, fallback to local temp storage
- Redis failure: Continue without cache (performance degradation only)

**Monitoring**:

- Metrics: Filings fetched/min, parse success rate, storage latency
- Alerts: Parse failures >10%, storage errors, Redis unavailable
- Logging: Structured JSON logs with filing metadata

**Testing**:

- Unit tests: Each stage isolated (mock dependencies)
- Integration tests: End-to-end 10 filings (real SEC + local MinIO)
- Failure tests: Network timeout, parse error, database constraint violation
- Load tests: 1000 filings batch (validate performance)

---

### Phase C: Data Collector Agent (2-3 days)

**UPDATED**: Per DD-032 (Hybrid Data Sourcing Strategy), Phase C now uses **financial data API for screening** instead of SEC backfill. SEC parsing happens on-demand after Human Gate 1 approves companies for deep analysis. API provider selection is pending.

**C0. Financial API Screening Backfill** (NEW - Day 6.5)

**Purpose**: Fetch 10Y financial metrics for all S&P 500 companies to enable immediate screening (Days 1-2 of analysis pipeline) - API provider TBD

**Implementation**: Depends on API provider selection

**Quick Backfill**:

```bash
# Fetch financial data for all S&P 500 (timing varies by provider)
python -m src.data_collector api-backfill

# Result: 500 companies with screening metrics in PostgreSQL
# data_source='financial_api'
```

**What gets stored**:

- Revenue CAGR (10Y, 5Y)
- Operating margin, net margin (3Y avg)
- ROE, ROA, ROIC (3Y avg)
- Debt/equity, current ratio (latest)

**Screening flow**:

1. API backfill (timing varies) → PostgreSQL
2. Screening Agent queries API data (filter by CAGR, margins, ratios)
3. Generate summaries: "AAPL: 18% 10Y CAGR, 25% operating margin, ROE 35%"
4. Human Gate 1 selects ~10-20 candidates
5. **Trigger SEC parsing** for approved companies only (C1 below)

**C1. Agent Implementation** (`src/agents/data_collector/agent.py`)

**Agent Responsibilities**:

- **Screening stage**: Fetch financial API data for S&P 500 (bulk) - provider TBD
- **Deep analysis stage**: Receive fetch requests for approved companies (ticker, form_types, date_range)
- Orchestrate storage pipeline for SEC filings (post-Gate 1)
- Manage task queue (prioritize approved companies)
- Report progress to human dashboard
- Handle errors gracefully (don't crash on single filing failure)

```python
# Interface design
class DataCollectorAgent:
    # NEW: Yahoo Finance methods (screening)
    async def yahoo_backfill_sp500() -> dict  # Fetch all S&P 500 screening data
    async def yahoo_fetch(tickers: list[str]) -> dict  # Fetch specific companies

    # Existing: SEC EDGAR methods (deep analysis, post-Gate 1)
    async def fetch_company(ticker: str, form_types: list[str] = ["10-K", "10-Q"])
    async def fetch_batch(tickers: list[str])
    async def monitor_new_filings(watch_tickers: list[str])
    async def get_status() -> dict
```

**Task Queue**:

- Redis-based job queue (bull/rq equivalent)
- Priority levels: High (10-K annual), Medium (10-Q quarterly), Low (8-K events)
- Concurrency: 10 parallel workers (SEC rate limit / 10 workers = 1 req/sec/worker)
- Retry policy: 3 attempts, exponential backoff

**Agent State**:

- Active tasks (in-progress fetches)
- Completed tasks (success count)
- Failed tasks (error details)
- Last run timestamp
- Next scheduled run

**Integration with Coordination Layer** (Phase 2):

- Receive requests from Lead Coordinator
- Report completion to workflow orchestrator
- Trigger analyst agents when new filings available

**Testing**:

- Unit tests: Task queue operations
- Integration tests: Fetch 10 companies end-to-end
- Concurrency tests: 10 parallel workers, no race conditions
- Failure recovery: Kill agent mid-fetch, verify resume on restart

**C2. Configuration** (`src/agents/data_collector/config.py`)

```python
# SEC EDGAR settings
SEC_RATE_LIMIT = 10  # requests/second
SEC_USER_AGENT = "FundamentalAnalysisSystem admin@example.com"
SEC_MAX_RETRIES = 3
SEC_RETRY_BACKOFF = [1, 2, 4]  # seconds

# Batch processing
BATCH_SIZE = 100  # filings per batch
CONCURRENT_WORKERS = 10
FETCH_TIMEOUT = 30  # seconds per filing

# Storage settings
S3_UPLOAD_TIMEOUT = 60  # seconds
DB_TRANSACTION_TIMEOUT = 10  # seconds
REDIS_CACHE_TTL = 86400  # 24 hours

# Retry policy
MAX_PARSE_RETRIES = 1  # Don't retry parse failures (data issue)
MAX_STORAGE_RETRIES = 3  # Retry storage failures (transient)

# Monitoring
LOG_LEVEL = "INFO"
METRICS_INTERVAL = 60  # seconds
ALERT_THRESHOLD_ERRORS = 10  # per minute
```

**Environment Variables**:

```bash
# .env file
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=fundamental_analysis
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres

REDIS_L1_HOST=localhost
REDIS_L1_PORT=6379

MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
```

**C3. Testing** (`tests/agents/test_data_collector.py`)

**Test Coverage Goals**: >80%

**Unit Tests**:

- EDGAR client: CIK lookup, filing URL construction
- Parser: XBRL extraction, validation
- Storage clients: Insert operations
- Agent: Task queue management

**Integration Tests**:

- End-to-end: Fetch AAPL 10-K → verify in PostgreSQL + MinIO
- Batch processing: 10 companies, 100 filings total
- Deduplication: Fetch same filing twice, verify only one stored
- Rate limiting: 100 requests, verify <10 req/sec

**Mock Tests** (for CI/CD without SEC dependency):

- Mock SEC responses (sample 10-K HTML/XBRL)
- Mock PostgreSQL (in-memory SQLite)
- Mock MinIO (local filesystem)
- Mock Redis (fakeredis library)

**Load Tests**:

- 1000 filings batch (simulate initial backfill)
- Verify: No memory leaks, no deadlocks, <5% error rate
- Performance: >10 filings/min throughput

**Error Scenario Tests**:

- SEC rate limit (429): Verify backoff + retry
- Network timeout: Verify retry logic
- Parse failure: Verify raw filing still stored
- Database deadlock: Verify transaction retry
- Redis unavailable: Verify graceful degradation

**Dependencies**:

```toml
[tool.poetry.group.test.dependencies]
pytest = "^8.0.0"
pytest-asyncio = "^0.23.0"
pytest-mock = "^3.12.0"
fakeredis = "^2.21.0"
moto = "^5.0.0"  # Mock AWS S3
```

---

### Phase D: Infrastructure Validation (1 day)

**_D1. End-to-End Test_**

**Test Case**: Fetch 10 real companies, verify complete pipeline

**Companies** (diverse sectors):

1. AAPL (Technology)
2. MSFT (Technology)
3. GOOGL (Technology)
4. JPM (Financials)
5. JNJ (Healthcare)
6. XOM (Energy)
7. WMT (Consumer)
8. BA (Industrials)
9. DIS (Media)
10. TSLA (Automotive)

**Validation Checklist**:

- [ ] 100+ filings fetched (10-K + 10-Q for 5 years)
- [ ] PostgreSQL `document_registry`: 100+ records
- [ ] PostgreSQL `financial_data`: 500+ records (revenue, income, assets, etc.)
- [ ] MinIO `raw/sec_filings/`: 100+ files
- [ ] Redis L1 cache: 100+ deduplication keys
- [ ] No duplicate filings stored
- [ ] All filings parseable (success rate >95%)
- [ ] Storage consistency: Every PostgreSQL record has corresponding MinIO file
- [ ] Rate limiting working: SEC request rate <10 req/sec
- [ ] Error handling: Test 1 broken filing, verify pipeline continues

**Performance Metrics**:

- Throughput: >10 filings/min
- Latency: <30s per filing (fetch + parse + store)
- Memory usage: <500MB for agent process
- Error rate: <5%

**_D2. Documentation_**

**Update Roadmap** (`docs/implementation/01-roadmap.md`):

```markdown
### Phase 1: Foundation ✅

- [x] Set up data infrastructure
  - [x] PostgreSQL for structured data
  - [x] S3 (MinIO) for raw documents
  - [x] Redis L1 for working memory
  - [x] Elasticsearch (deferred indexing to Phase 2)
- [x] Implement data collector agent
  - [x] SEC EDGAR integration
  - [x] XBRL financial parsing
  - [x] Storage pipeline (PostgreSQL + MinIO + Redis)
  - [x] Deduplication + rate limiting
```

**Create Technical Guide** (`docs/implementation/technical-guides/04-data-collector.md`):

Contents:

- Architecture overview (EDGAR → Parser → Storage)
- SEC API usage (rate limits, user-agent, endpoints)
- Storage schema (PostgreSQL tables, MinIO paths, Redis keys)
- Configuration (environment variables, rate limits)
- Running the agent (CLI commands, batch processing)
- Monitoring (logs, metrics, alerts)
- Troubleshooting (common errors, debugging)
- Testing (unit/integration/load tests)

**Update CLAUDE.md**:

````markdown
## Data Collector Agent

**Status**: Operational (Phase 1)
**Location**: `src/agents/data_collector/`

**Capabilities**:

- Fetch SEC EDGAR filings (10-K, 10-Q, 8-K)
- Parse XBRL financial statements
- Store raw documents in MinIO
- Store structured data in PostgreSQL
- Deduplication via Redis L1

**Usage**:

```bash
# Fetch single company
python -m src.agents.data_collector fetch --ticker AAPL

# Fetch batch
python -m src.agents.data_collector fetch-batch --tickers AAPL,MSFT,GOOGL

# Monitor new filings
python -m src.agents.data_collector monitor --watch-list watchlist.txt
```
````

**Dependencies**: PostgreSQL, MinIO, Redis L1 (all must be running)

---

## 4. Deferred to Phase 2

### Elasticsearch Document Indexing

**Why deferred**: Analyst agents need search functionality, not data collector

**What's missing**:

- Document indexing pipeline (bulk upload to Elasticsearch)
- Embedding generation (currently mock vectors)
- Search API integration (keyword + semantic + hybrid)

**When needed**: Phase 2 when Business Research Agent needs to search filings

**Estimate**: 2-3 days

- Batch indexing (1000 docs/min throughput)
- Embedding model integration (OpenAI or local)
- Search relevance tuning (BM25 + vector weights)

### Neo4j L3 Knowledge Graph

**Why deferred**: Analyst agents create graph relationships, not data collector

**What's missing**:

- Neo4j Docker service
- Graph schema (Company, Analysis, Pattern nodes)
- Python neo4j-driver client

**When needed**: Phase 2 when analyst agents run and need to store:

- Company → Analysis relationships
- Pattern recognition (similar companies)
- Agent track record (which agents identified good insights)

**Estimate**: 5-7 days

- Neo4j setup + schema: 2 days
- Python client + query builders: 2 days
- Integration with analyst agents: 3 days

### Redis L2 Agent Cache

**Why deferred**: Analyst agents cache recent analysis, not data collector

**What's missing**:

- Redis L2 client wrapper (port 6380 already operational)
- Cache invalidation strategy
- TTL management (30 days)

**When needed**: Phase 2 when analyst agents need to cache:

- Recent financial analysis summaries
- Peer comparison results
- Industry context

**Estimate**: 1-2 days (L2 infrastructure exists, just need client code)

### Materialized Views for Latest Financials

**Why deferred**: Data collector writes only, Financial Analyst reads

**What's missing**:

- Pre-computed views for "latest financial statement per company"
- Refresh mechanisms (manual or automated after bulk inserts)
- Composite views joining income/balance/cash flow

**When needed**: Phase 2 when Financial Analyst queries latest earnings frequently

**Performance benefit**: 100x speedup for "show all companies' latest quarters" queries

**Implementation**:

```sql
-- Latest income statement per company
CREATE MATERIALIZED VIEW financial_data.latest_income_statements AS
SELECT DISTINCT ON (ticker) *
FROM financial_data.income_statements
WHERE is_latest = true
ORDER BY ticker, period_end_date DESC;

-- Latest balance sheet per company
CREATE MATERIALIZED VIEW financial_data.latest_balance_sheets AS
SELECT DISTINCT ON (ticker) *
FROM financial_data.balance_sheets
WHERE is_latest = true
ORDER BY ticker, period_end_date DESC;

-- Latest cash flow per company
CREATE MATERIALIZED VIEW financial_data.latest_cash_flows AS
SELECT DISTINCT ON (ticker) *
FROM financial_data.cash_flows
WHERE is_latest = true
ORDER BY ticker, period_end_date DESC;

-- Composite view with all three statements
CREATE MATERIALIZED VIEW financial_data.latest_complete_financials AS
SELECT
    i.ticker,
    i.period_end_date,
    i.fiscal_year,
    i.revenue,
    i.net_income,
    i.eps_diluted,
    b.total_assets,
    b.total_debt,
    b.total_equity,
    cf.operating_cf,
    cf.free_cash_flow
FROM financial_data.latest_income_statements i
LEFT JOIN financial_data.latest_balance_sheets b USING (ticker, period_end_date)
LEFT JOIN financial_data.latest_cash_flows cf USING (ticker, period_end_date);

-- Indexes for performance
CREATE INDEX idx_latest_income_ticker ON financial_data.latest_income_statements(ticker);
CREATE INDEX idx_latest_balance_ticker ON financial_data.latest_balance_sheets(ticker);
CREATE INDEX idx_latest_cashflow_ticker ON financial_data.latest_cash_flows(ticker);
```

**Refresh strategy**:

```python
# After bulk inserts in data collector
await session.execute("REFRESH MATERIALIZED VIEW CONCURRENTLY financial_data.latest_income_statements")
await session.execute("REFRESH MATERIALIZED VIEW CONCURRENTLY financial_data.latest_balance_sheets")
await session.execute("REFRESH MATERIALIZED VIEW CONCURRENTLY financial_data.latest_cash_flows")
await session.execute("REFRESH MATERIALIZED VIEW CONCURRENTLY financial_data.latest_complete_financials")
```

**Estimate**: 0.5 days

- Create views + indexes: 1-2 hours
- Add refresh calls to data collector: 1 hour
- Test query performance: 1 hour

### Real-Time Monitoring

**What's missing**:

- Prometheus exporters for data collector metrics
- Grafana dashboards (filings/min, parse success rate, storage latency)
- Alert rules (error rate >10%, SEC rate limit violations)

**When needed**: Phase 4 production deployment

**Estimate**: 2-3 days

---

## 5. Timeline Breakdown

### Week 1: Storage Clients (Days 1-3)

- **Day 1**: PostgreSQL client (async session, CRUD, bulk insert)
- **Day 2**: MinIO client (upload/download, multipart, retry)
- **Day 3**: Redis L1 client (deduplication, task tracking, rate limiting)

### Week 2: SEC EDGAR Integration (Days 4-6.5)

- **Day 4**: EDGAR client (rate limiting, filing search, CIK lookup)
- **Day 5**: Filing parser - **REVISED WITH EDGARTOOLS**
  - Morning: EdgarTools integration + Tier 0 wrapper (4 hours)
  - Afternoon: Tier 1.5 smart deterministic stub (4 hours)
  - **Time saved**: 0.5 days (EdgarTools handles 95% baseline vs building from scratch)
- **Day 6**: Storage pipeline (orchestration, error handling, multi-tier flow)
- **Day 6.5**: Integration testing (EdgarTools + Tier 1.5 end-to-end)

### Week 2-3: Yahoo Finance + Agent + Validation (Days 7-10)

- **Day 6.5**: Yahoo Finance integration (per `yahoo-finance-integration-plan.md`, 2-3 days compressed)
  - YahooFinanceClient implementation
  - Screening metrics calculator
  - PostgreSQL data_source column
  - S&P 500 backfill test
- **Day 7**: Agent implementation (task queue, concurrency, state management)
  - Add yahoo_backfill_sp500() and yahoo_fetch() methods
  - Update SEC fetch to trigger post-Gate 1
- **Day 8**: Configuration + testing (unit tests, mock tests)
- **Day 9**: Load testing (Yahoo: 500 companies, SEC: 100 filings for baseline validation)
- **Day 10**: End-to-end validation (Yahoo screening + SEC deep analysis for 10 companies) + documentation

**Total**: 10 days (unchanged, Yahoo integration fits in Day 6.5-7 alongside agent work)

**EdgarTools Impact**:

- **Time saved**: 0.5 days (Day 5 reduced from 1.0 → 0.5 days)
- **Complexity reduced**: No need to build basic XBRL parser from scratch
- **Quality improved**: Battle-tested parser handles 95% baseline vs 92-93% if custom-built

---

## 6. Success Criteria

### Functional Requirements

- ✅ Fetch SEC filings for any ticker (10-K, 10-Q, 8-K)
- ✅ Parse XBRL financial statements (income, balance sheet, cash flow)
- ✅ Store raw filings in MinIO
- ✅ Store structured data in PostgreSQL
- ✅ Deduplication prevents duplicate fetches
- ✅ Rate limiting complies with SEC 10 req/sec limit
- ✅ Error handling: Individual filing failures don't crash pipeline

### Performance Requirements

- ✅ Throughput: >10 filings/min
- ✅ Latency: <30s per filing (fetch + parse + store)
- ✅ Success rate: >95% (parse + store)
- ✅ Concurrent workers: 10 parallel fetches
- ✅ Memory usage: <500MB agent process

### Quality Requirements

- ✅ Test coverage: >80%
- ✅ No security vulnerabilities (SQL injection, path traversal)
- ✅ Logging: Structured JSON logs with filing metadata
- ✅ Configuration: Externalized via environment variables
- ✅ Documentation: Technical guide + API reference

---

## 7. Filing Amendments Strategy

### Decision: Keep Both Versions (Recommended)

**Problem**: Companies file amended reports (10-K/A, 10-Q/A) to correct errors in original filings. The system must decide whether to overwrite original filings or maintain version history.

**Chosen Approach**: Store both original and amended filings with full version tracking.

---

### Schema Support (Already Implemented)

The existing PostgreSQL schema (`774d9680756d_data_collector_schemas.py`) already supports versioning:

**Key columns in `document_registry.filings`**:

- `version` (INTEGER): Increments for each amendment (1, 2, 3, ...)
- `is_latest` (BOOLEAN): TRUE only for most recent version
- `superseded_by` (UUID): Points to the filing that supersedes this one

**Automated triggers** (lines 197-285 in migration):

- `update_latest_version()`: Automatically marks old versions as `is_latest=false` when amendment inserted
- Similar triggers for financial_data tables

---

### Implementation

**When Data Collector encounters 10-K/A amendment**:

```python
# In storage_pipeline.py
async def process_filing(self, cik: str, accession_number: str, form_type: str):
    """Process filing with amendment detection"""

    # Check if this is an amendment (form_type ends with /A)
    is_amendment = form_type.endswith("/A")  # e.g., "10-K/A", "10-Q/A"

    if is_amendment:
        # Find original filing for same period
        base_form = form_type.rstrip("/A")  # "10-K/A" → "10-K"
        original = await postgres.get_filing_by_period(
            ticker=ticker,
            period_end_date=period_end_date,
            form_type=base_form
        )

        if original:
            # Insert amendment as new version
            amendment_id = await postgres.insert_document_metadata(
                ticker=ticker,
                filing_date=filing_date,
                form_type=form_type,
                s3_path=s3_path,
                version=original.version + 1  # Increment version
            )

            # Link original to amendment
            await postgres.supersede_filing(
                old_filing_id=original.filing_id,
                new_filing_id=amendment_id
            )
            # Result: original.is_latest = false, original.superseded_by = amendment_id
            #         amendment.is_latest = true, amendment.version = original.version + 1

    else:
        # Regular filing, version = 1
        await postgres.insert_document_metadata(
            ticker=ticker,
            filing_date=filing_date,
            form_type=form_type,
            s3_path=s3_path,
            version=1
        )
```

**Both filings stored in MinIO**:

- Original: `raw/sec_filings/AAPL/2024/0000320193-24-000010.html`
- Amendment: `raw/sec_filings/AAPL/2024/0000320193-24-000123.html`

**Both financial statements in PostgreSQL**:

- Original: `version=1, is_latest=false`
- Amendment: `version=2, is_latest=true`

---

### Rationale for Keeping Both Versions

**1. Audit Trail for Analysts**

- Business Research Agent can see what data was originally filed vs corrected
- Shows what analysts/investors saw at the time of original filing
- Critical for understanding historical decision-making context

**2. Red Flag Detection**

- Pattern: Company frequently amends earnings → Red flag (accounting irregularities)
- Business Research Agent flags in SWOT analysis: "Company has filed 3 10-K/A amendments in last 2 years"
- Strategy Analyst evaluates management credibility (frequent errors indicate poor controls)

**3. QC Agent Analysis**

- QC Agent compares original vs amended financial data
- Detects what changed: Revenue adjustment? Debt reclassification? Related-party transaction disclosure?
- Example: "Amendment increased revenue by 5% - investigate aggressive revenue recognition"

**4. Regulatory Compliance**

- SEC investigations may require amendment history
- Audit trail demonstrates system tracked all versions
- Legal requirement for some investment advisors

**5. Learning Opportunities (L3 Knowledge Graph)**

- Pattern recognition: Which companies amend frequently?
- Correlation analysis: Do frequent amendments predict underperformance?
- Track record: Companies that amend → Historical performance

---

### Query Patterns (For Analyst Agents)

**Get latest financial data only** (most common):

```sql
SELECT * FROM financial_data.income_statements
WHERE ticker = 'AAPL'
  AND fiscal_year = 2024
  AND is_latest = true;  -- Only latest version
```

**Get version history** (for QC Agent):

```sql
SELECT version, revenue, net_income, is_latest, superseded_by
FROM financial_data.income_statements
WHERE ticker = 'AAPL'
  AND period_end_date = '2024-09-30'
ORDER BY version;
-- Result: Shows original vs amended values
```

**Detect frequent amendments** (for Business Research Agent):

```sql
SELECT ticker, COUNT(*) as amendment_count
FROM document_registry.filings
WHERE form_type LIKE '%/A'  -- All amendments
  AND filing_date > CURRENT_DATE - INTERVAL '2 years'
GROUP BY ticker
HAVING COUNT(*) >= 3
ORDER BY amendment_count DESC;
-- Result: Companies with 3+ amendments in 2 years (red flag)
```

---

### Storage Impact

**Frequency**: S&P 500 files ~25 amendments/year out of ~500 annual 10-Ks = **~5% amendment rate**

**Storage overhead**:

- 20,000 filings × 5% = 1,000 amendments
- 1,000 × 5MB/filing = **5GB additional MinIO storage**
- 1,000 × 10 financial metrics = **10,000 additional PostgreSQL rows**

**Verdict**: Negligible overhead (~5%) for significant analytical value

---

### Alternative Approaches (Not Chosen)

**Option B: Overwrite Original** (❌ NOT RECOMMENDED)

- Delete original filing from PostgreSQL + MinIO
- Insert amendment as if it's the original
- **Critical flaw**: Lose historical context, can't detect amendment patterns
- Only suitable for real-time data feeds where history doesn't matter

**Option C: Metadata Only** (⚠️ ACCEPTABLE IF STORAGE CONSTRAINED)

- Keep original metadata in PostgreSQL (for audit)
- Keep original raw filing in MinIO
- **Don't parse** original into financial_data (only parse amendment)
- **Trade-off**: Can see that amendment happened, but can't analyze what changed

---

### Integration with Analyst Agents (Phase 2)

**Business Research Agent**:

- Check amendment history during SWOT analysis
- Red flag: "Company filed 10-K/A on [date], amended revenue from $X to $Y (+5%)"
- Include in risk factors if frequent amendments detected

**QC Agent**:

- Compare original vs amended financial data
- Alert if material changes (revenue >5%, debt >10%, equity restatement)
- Track which companies amend frequently (feed to L3 knowledge graph)

**Financial Analyst Agent**:

- Always query `is_latest=true` for current analysis
- Can query version history if QC Agent flags discrepancy
- Calculate metrics using latest version only

---

### Success Metrics

**Implementation readiness**: ✅ Schema already supports versioning (migration `774d9680756d`)

**Testing checklist**:

- ✅ Test `supersede_filing()` method (existing in postgres_client.py:294-326)
- ✅ Verify triggers auto-update `is_latest` flag
- ✅ Test version increment logic
- ✅ Test query filtering `is_latest=true`

**Phase D validation**:

- Fetch a real amended filing (e.g., find recent 10-K/A in SEC EDGAR)
- Process both original + amendment
- Verify both stored, original marked `is_latest=false`
- Verify analyst queries only return latest version by default

---

## 8. Unresolved Questions

1. **SEC EDGAR downtime** - How handle 503 errors during market hours (high traffic)?
2. **XBRL parsing edge cases** - Non-GAAP adjustments, restated financials, foreign filers?
3. **Storage limits** - MinIO 10-15TB sufficient for 5 years of data?
4. **Backfill strategy** - ✅ **RESOLVED** - See DD-032 (Hybrid: Yahoo Finance for screening, SEC on-demand for deep analysis)
5. **Data retention** - How long keep raw filings vs just parsed financials?
6. **Filing amendments** - ✅ **RESOLVED** - See Section 7 (Keep both versions with versioning)
7. **Concurrency scaling** - Can increase workers beyond 10 without hitting SEC limits?
8. **Parse failure threshold** - ✅ **RESOLVED** - See `data-collector-parse-failure-strategy.md` (Multi-tier agent recovery)
9. **Yahoo Finance API selection** - ✅ **RESOLVED** - See DD-032 & `yahoo-finance-integration-plan.md` (Use yfinance library, fallback to Alpha Vantage or SEC)

**Note**: Questions 4, 6, 8, and 9 have been resolved and documented in separate strategy documents.

---

## 9. Related Design Decisions

- **DD-032**: Hybrid Data Sourcing Strategy (Yahoo Finance for screening, SEC EDGAR for deep analysis) - **NEW**
- **DD-031**: SEC Filing Parser Tool Selection (EdgarTools + multi-tier recovery for deep analysis)
- **DD-027**: Elasticsearch Unified Hybrid Search (deferred indexing to Phase 2)
- **DD-028**: Redis 3-tier persistence strategy (using L1 only for now)
- **DD-029**: Elasticsearch index mapping (indices created, awaiting documents)
- **DD-009**: S3 tiered storage (raw bucket with versioning)
- **DD-019**: PostgreSQL partitioning (financial_data partitioned by year)

### Related Strategy Documents

- **yahoo-finance-integration-plan.md**: Implementation plan for Yahoo Finance API client (screening data) - **NEW**
- **data-collector-backfill-strategy.md**: Comprehensive analysis of backfill options, recommended hybrid approach
- **data-collector-parse-failure-strategy.md**: Multi-tier agent recovery system for XBRL parsing failures

---

## 10. Next Steps After Completion

**Phase 2 Prerequisites**:

1. Data collector operational → Start Business Research Agent
2. PostgreSQL populated → Financial Analyst can query historical data
3. MinIO populated → Analyst agents can read raw filings

**Immediate Follow-On Tasks** (Phase 2):

1. Implement Business Research Agent (reads SEC filings from MinIO)
2. Implement Financial Analyst Agent (queries PostgreSQL financial_data)
3. Deploy Neo4j for L3 knowledge graph (analyst agents need this)
4. Implement Elasticsearch indexing (analyst agents need search)

**Estimated Phase 2 Start**: Week 3 (after data collector validation complete)
