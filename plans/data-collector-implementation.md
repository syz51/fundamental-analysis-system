# Data Collector Implementation Plan

**Status**: Ready to implement
**Phase**: Phase 1 - Foundation
**Estimated Timeline**: 8-11 days
**Dependencies**: PostgreSQL, MinIO, Redis L1 (all operational)

---

## 1. Infrastructure Status Verification

### Current Completion: 60%

#### ✅ Operational Components

**PostgreSQL (Structured Data)**

- Docker service: `postgres:18.1` on port 5432
- Schema: 8 schemas, 15+ tables fully migrated via Alembic
- Key schemas for data collector:
  - `document_registry`: Track all fetched documents
  - `financial_data`: Store structured financial statements
  - `metadata`: Company and filing metadata
- Dependencies: `asyncpg>=0.30.0`, `sqlalchemy>=2.0.44`, `alembic>=1.17.2`
- Migration: `a125ac7b2db7_initial_schema.py` deployed
- **Gap**: No Python client code yet

**MinIO/S3 (Object Storage)**

- Docker service: `minio/minio:latest` on ports 9000/9001
- Buckets created via `scripts/setup_minio.sh`:
  - `raw` (versioning enabled): For SEC filings
  - `processed`: For parsed financial statements
  - `outputs`: For generated reports
- Storage capacity: 10-15TB planned
- **Gap**: No Python client (boto3/minio SDK not in dependencies)

**Redis L1 (Working Memory)**

- Docker service: `redis:latest` on port 6379
- Persistence: AOF + RDB hybrid (DD-028)
- Use cases for data collector:
  - Deduplication cache (check if filing already fetched)
  - Active task tracking (in-progress fetches)
  - 24h TTL for working memory
- Dependencies: `redis>=5.0.0`
- **Gap**: No Python client wrapper

**Elasticsearch (Document Search)**

- Docker service: `elasticsearch:8.14.0` on port 9200
- Indices: `sec_filings`, `transcripts`, `news` (created but empty)
- Client exists: `src/storage/search_tool.py`
- **Deferred**: Document indexing to Phase 2 (analyst agents need search, not collector)

#### ❌ Not Needed for Data Collector

**Neo4j (L3 Knowledge Graph)**

- Status: Not implemented
- Why deferred: Data collector fetches/stores raw data only
- Graph relationships created by analyst agents (Business Research, Financial Analyst) during analysis
- Phase 2 dependency for analyst agents, NOT data collector

**Redis L2 (Agent Cache)**

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

**Document Formats**:

- **HTML filings**: Pre-2009 filings, text extraction via BeautifulSoup
- **XBRL filings**: 2009+ filings, structured XML with financial data tags
- **Inline XBRL (iXBRL)**: 2019+ filings, HTML with embedded XBRL tags

```python
# Interface design
class FilingParser:
    def extract_metadata(filing_content: bytes) -> dict
    def parse_xbrl_financials(filing_content: bytes) -> dict
    def extract_text(filing_content: bytes) -> str
    def validate_filing(filing_content: bytes) -> bool
```

**Metadata Extraction**:

- Ticker, CIK, company name
- Filing date, period end date, fiscal year/quarter
- Form type (10-K, 10-Q, 8-K)
- Accession number (unique identifier)

**XBRL Financial Parsing** (Priority):

- Income statement: Revenue, operating income, net income, EPS
- Balance sheet: Assets, liabilities, equity, cash, debt
- Cash flow: Operating CF, investing CF, financing CF
- Key tags: `us-gaap:Revenues`, `us-gaap:NetIncomeLoss`, `us-gaap:Assets`

**Text Extraction** (Phase 2):

- Item 1: Business description
- Item 7: MD&A (Management Discussion & Analysis)
- Item 8: Financial statements
- Risk factors, legal proceedings

**Data Validation**:

- Schema compliance (required fields present)
- Data type checks (dates valid, numbers numeric)
- Consistency: Assets = Liabilities + Equity
- Outlier detection: Revenue >$0, debt ratios reasonable

**Dependencies**:

```toml
beautifulsoup4 = "^4.12.0"
lxml = "^5.0.0"
python-edgar = "^4.0.0"  # XBRL parsing library
```

**Testing**:

- Unit tests: Parse sample 10-K XBRL (AAPL Q4 2023)
- Validation tests: Reject malformed filings
- Edge cases: Missing tags, non-GAAP adjustments

**B3. Storage Pipeline** (`src/agents/data_collector/storage_pipeline.py`)

**Workflow**:

```
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

**C1. Agent Implementation** (`src/agents/data_collector/agent.py`)

**Agent Responsibilities**:

- Receive fetch requests (ticker, form_types, date_range)
- Orchestrate storage pipeline for multiple filings
- Manage task queue (prioritize recent filings)
- Report progress to human dashboard
- Handle errors gracefully (don't crash on single filing failure)

```python
# Interface design
class DataCollectorAgent:
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

**D1. End-to-End Test**

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

**D2. Documentation**

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

````

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
````

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

### Week 2: SEC EDGAR Integration (Days 4-7)

- **Day 4**: EDGAR client (rate limiting, filing search, CIK lookup)
- **Day 5**: Filing parser (XBRL parsing, metadata extraction)
- **Day 6**: Storage pipeline (orchestration, error handling, transactions)
- **Day 7**: Integration testing (end-to-end with real SEC data)

### Week 2-3: Agent + Validation (Days 8-11)

- **Day 8**: Agent implementation (task queue, concurrency, state management)
- **Day 9**: Configuration + testing (unit tests, mock tests)
- **Day 10**: Load testing (1000 filings, performance validation)
- **Day 11**: End-to-end validation (10 companies) + documentation

**Total**: 11 days (can compress to 8 days with parallel work on storage clients)

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

## 7. Unresolved Questions

1. **SEC EDGAR downtime** - How handle 503 errors during market hours (high traffic)?
2. **XBRL parsing edge cases** - Non-GAAP adjustments, restated financials, foreign filers?
3. **Storage limits** - MinIO 10-15TB sufficient for 5 years of data?
4. **Backfill strategy** - Fetch all historical filings or only recent 1 year?
5. **Data retention** - How long keep raw filings vs just parsed financials?
6. **Filing amendments** - How handle 10-K/A amended filings (overwrite or version)?
7. **Concurrency scaling** - Can increase workers beyond 10 without hitting SEC limits?
8. **Parse failure threshold** - When alert human vs auto-skip filing?

---

## 8. Related Design Decisions

- **DD-027**: Elasticsearch Unified Hybrid Search (deferred indexing to Phase 2)
- **DD-028**: Redis 3-tier persistence strategy (using L1 only for now)
- **DD-029**: Elasticsearch index mapping (indices created, awaiting documents)
- **DD-009**: S3 tiered storage (raw bucket with versioning)
- **DD-019**: PostgreSQL partitioning (financial_data partitioned by year)

---

## 9. Next Steps After Completion

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

```

```
