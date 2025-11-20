# Data Collector Backfill Strategy

**Status**: Design Decision
**Created**: 2025-11-20
**Related**: `data-collector-implementation.md`, Phase A-D
**Dependencies**: PostgreSQL, MinIO, SEC EDGAR API

---

## 1. Problem Statement

### The Challenge

When deploying the data collector agent for the first time, the system needs historical financial data to perform fundamental analysis. However, fetching 10 years of SEC filings for 500 companies presents a trade-off between:

1. **Completeness**: Need full historical data for accurate analysis
2. **Time**: Fetching 20,000+ filings takes 30+ hours at SEC rate limits
3. **Storage**: 100GB+ of raw filings and 200K+ database records
4. **Relevance**: May not analyze all 500 companies immediately

### Why Historical Data Matters

**Per CLAUDE.md system requirements**, fundamental analysis needs:

1. **10-Year Revenue CAGR** (key screening metric)

   - Filter: "Companies with 10Y revenue growth >15%"
   - Requires: 40+ quarterly filings (10-K + 10-Q from 2014-2024)

2. **Economic Cycle Analysis**

   - Evaluate performance across cycles (2008 recovery, COVID, inflation)
   - Requires: Full decade of data to see patterns

3. **Management Track Record**

   - Strategy Analyst evaluates historical capital allocation decisions
   - Requires: 5-10 years of M&A, capex, dividend history

4. **Pattern Recognition** (L3 Knowledge Graph)
   - Identify similar companies, successful strategies, red flags
   - Requires: Large dataset for meaningful patterns

**Conclusion**: Deep fundamental analysis requires 10Y data, not just recent quarters.

---

## 2. Analysis Requirements by Agent Type

### Screening Agent (Phase 1)

**Purpose**: Initial quantitative filtering of 500 companies to 50 candidates

**Data Needs**:

- Latest annual financials (most recent 10-K)
- Basic metrics: Revenue, net income, total debt, EBITDA, total assets
- Time horizon: Current year only

**Can operate with**: Latest 10-K for all companies (500 filings)

**Limitations without 10Y data**:

- Can't calculate true 10Y CAGR (use proxy: 3Y growth from latest 3 10-Ks if available)
- Can't evaluate cycle consistency
- Can't detect long-term trends

---

### Business Research Agent (Phase 2)

**Purpose**: Qualitative analysis of business model, competitive moats, SWOT

**Data Needs**:

- Recent 10-Ks (last 2-3 years) for business description, MD&A, risk factors
- Recent 10-Qs for quarterly updates
- Time horizon: 2-3 years

**Can operate with**: Last 8-12 filings (2-3 years)

**Limitations without 10Y data**:

- Can't analyze long-term strategic pivots
- May miss historical context (e.g., major restructuring 5 years ago)

---

### Financial Analyst Agent (Phase 2)

**Purpose**: Quantitative analysis of financial health, ratios, peer comparisons

**Data Needs**:

- Full 10Y financial statements (income, balance sheet, cash flow)
- Quarterly granularity for trend analysis
- Time horizon: 10 years

**Cannot operate without 10Y data**:

- 10Y revenue/earnings CAGR calculation
- ROE/ROIC trends across cycles
- Debt management during crises
- Working capital efficiency over time

**Critical dependency**: Needs 40+ filings per company

---

### Strategy Analyst Agent (Phase 2)

**Purpose**: Evaluate capital allocation, M&A track record, management decisions

**Data Needs**:

- Full 10Y cash flow statements (capex, M&A, dividends, buybacks)
- Proxy statements (executive compensation, board changes)
- Time horizon: 10 years (to calculate historical ROI on decisions)

**Cannot operate without 10Y data**:

- 5/10/15Y historical ROI calculation (key metric per CLAUDE.md)
- M&A success rate requires full history
- Capital allocation consistency across cycles

**Critical dependency**: Needs 40+ filings + proxies

---

### Valuation Agent (Phase 2)

**Purpose**: DCF modeling, scenario analysis, relative valuation

**Data Needs**:

- 10Y historical financials for DCF terminal value calculation
- 5Y average margins for normalization
- Peer 10Y data for relative multiples

**Can operate with partial data**:

- DCF possible with 3-5Y history (less accurate terminal value)
- Relative valuation needs only latest year if peers available

**Improved with 10Y data**: More accurate growth rate assumptions, better cycle-adjusted margins

---

## 3. Options Analysis

### Option A: Comprehensive Upfront Backfill

**Strategy**: Fetch all 10Y data for all S&P 500 companies before starting analysis

**Scope**:

- 500 companies × 40 filings (10 years × 4 quarters) = 20,000 filings
- Form types: 10-K (annual), 10-Q (quarterly)
- Time period: 2014-2024

**Timeline**:

- SEC rate limit: 10 requests/second
- Effective throughput: ~6 filings/minute (accounting for parsing, storage)
- Total time: 20,000 / 6 = **3,333 minutes = 55 hours = 2.3 days**
- Practical: Run over weekend (Saturday 8am → Monday 3pm)

**Storage**:

- MinIO: 20,000 filings × 5MB average = **100GB**
- PostgreSQL: 20,000 filings × 10 financial metrics = **200,000 rows**
- Redis L1: Deduplication cache (24h TTL, cleared after backfill)

**Pros**:

- ✅ **Zero latency**: Analysis starts immediately when user selects company
- ✅ **Full screening**: Can run "10Y CAGR >15%" filter on all 500 companies
- ✅ **Simple logic**: One-time setup, no dynamic fetching
- ✅ **Complete patterns**: L3 Knowledge Graph has full dataset from day 1

**Cons**:

- ❌ **Wasted effort**: If only 50 companies analyzed, fetched 450 unnecessarily (90% waste)
- ❌ **Upfront delay**: 2-3 day wait before system operational
- ❌ **SEC scrutiny**: Bulk fetching 20K filings in 55 hours may trigger rate limit warnings
- ❌ **Storage costs**: 100GB MinIO, 200K PostgreSQL rows for potentially unused data

**When to use**: Production system with commitment to analyze all S&P 500 companies

---

### Option B: Recent Data Only

**Strategy**: Fetch only last 2 years (8 quarters) for all companies

**Scope**:

- 500 companies × 8 filings = 4,000 filings
- Form types: 10-K (2 years), 10-Q (6 quarters)
- Time period: 2023-2024

**Timeline**:

- 4,000 filings / 6 per minute = **667 minutes = 11 hours**
- Practical: Run overnight (Saturday 8pm → Sunday 7am)

**Storage**:

- MinIO: 4,000 × 5MB = **20GB**
- PostgreSQL: 4,000 × 10 metrics = **40,000 rows**

**Pros**:

- ✅ **Fast deployment**: System operational in 11 hours
- ✅ **Lower storage**: 20% of comprehensive backfill
- ✅ **Data quality**: All iXBRL (2019+), easier parsing than old HTML filings
- ✅ **SEC-friendly**: Smaller request volume less likely to trigger scrutiny

**Cons**:

- ❌ **No 10Y CAGR**: Can't calculate key screening metric
- ❌ **No cycle analysis**: Miss COVID impact, 2015-2019 growth period
- ❌ **Incomplete patterns**: L3 graph lacks historical context
- ❌ **Screening bias**: Filters like "consistent 10Y margins >20%" impossible

**When to use**: MVP testing, proof-of-concept, short-term trading focus (not fundamental analysis)

---

### Option C: On-Demand Full Backfill

**Strategy**: Fetch 10Y data only when user selects company for analysis

**Workflow**:

```text
User: "Analyze NVDA"
  ↓
Lead Coordinator: Check PostgreSQL for NVDA 10Y data
  ↓
IF missing → Data Collector: Fetch 40 filings for NVDA (priority queue)
  ↓
Wait 5-10 minutes (40 filings × 15 seconds/filing)
  ↓
Launch Business Research + Financial Analyst agents
```

**Timeline per company**:

- 40 filings × 15 seconds = **600 seconds = 10 minutes**
- Parallel: Can fetch 10 companies simultaneously = 10 min for batch

**Storage** (after 50 companies analyzed):

- MinIO: 50 × 40 × 5MB = **10GB**
- PostgreSQL: 50 × 40 × 10 = **20,000 rows**

**Pros**:

- ✅ **Zero upfront cost**: No weekend backfill, system operational immediately
- ✅ **Efficient storage**: Only fetch data actually used (50 companies = 10GB vs 100GB)
- ✅ **Flexible**: User decides which companies matter
- ✅ **SEC-friendly**: Requests spread over weeks/months based on usage

**Cons**:

- ❌ **Analysis latency**: 10-minute wait before analysis starts
- ❌ **No bulk screening**: Can't run "10Y CAGR >15%" on all 500 until manually triggered
- ❌ **Poor UX**: User expects instant analysis, not "Please wait 10 min while I fetch data"
- ❌ **Pipeline mismatch**: 12-day analysis cycle assumes data ready (CLAUDE.md)

**When to use**: Ad-hoc analysis, unknown company universe (not S&P 500 focus)

---

### Option D: Hybrid - Screening Data + On-Demand Deep Data (RECOMMENDED ✅)

**Strategy**: Two-tier data model matching 12-day pipeline phases

**_Phase 1: Screening Data (Upfront)_**

- Fetch **latest 10-K only** for all S&P 500
- Scope: 500 filings
- Timeline: 500 / 6 per minute = **83 minutes = 1.4 hours**
- Storage: 500 × 5MB = **2.5GB MinIO**, 500 × 10 metrics = **5,000 PostgreSQL rows**

**_Phase 2: Deep Data (On-Demand, after Human Gate 1)_**

- When company approved for analysis → fetch full 10Y history
- Scope: 40 filings per company
- Timeline: 10 minutes per company, parallelizable (10 companies = 10 min total)
- Storage: 10 companies × 40 × 5MB = **2GB per batch**

**Complete Workflow**:

```text
Day 1: Screening Phase
├─ Data Collector: Fetch latest 10-K for S&P 500 (1.4 hours, run overnight)
├─ Screening Agent: Run quantitative filters on 500 companies
│   ├─ Latest revenue >$1B
│   ├─ Latest net margin >15%
│   ├─ Latest debt/EBITDA <3x
│   ├─ Proxy CAGR: (2024 revenue / 2020 revenue)^(1/4) - 1 >15% (if 2020 10-K available)
│   └─ Result: 50 candidates
└─ Human Gate 1: User approves 10 companies →
    └─ Data Collector: Fetch 10Y data for approved 10 (10 min parallel fetch)
        └─ Days 3-7: Business Research + Financial Analyst agents (full 10Y data available)
```

**Pros**:

- ✅ **Matches pipeline**: Screening (Days 1-2) uses lightweight data, analysis (Days 3-7) uses deep data
- ✅ **Fast deployment**: 1.4 hours to operational (vs 55 hours comprehensive)
- ✅ **Efficient storage**: 2.5GB upfront + 2GB per 10 companies (vs 100GB upfront)
- ✅ **Acceptable latency**: 10-min on-demand fetch happens overnight between Gate 1 and analysis start
- ✅ **SEC-friendly**: 500 filings in 1.4 hours, then gradual 40-filing batches over weeks
- ✅ **Flexible screening**: Can run basic filters immediately, expand as data fetched

**Cons**:

- ⚠️ **Screening limitations**: Can't calculate true 10Y CAGR in initial screen (use 4Y proxy)
- ⚠️ **Complex orchestration**: Two-phase fetching requires Lead Coordinator integration
- ⚠️ **Incomplete patterns**: L3 graph builds gradually as companies analyzed

**When to use**: Production fundamental analysis system (your use case)

---

## 4. Recommended Approach: Hybrid Implementation

### Phase 1: Lightweight Screening Backfill (Week 1)

**Objective**: Enable Screening Agent to filter 500 companies to 50 candidates

**Data to fetch**:

```python
# In data_collector_agent.py
async def initial_backfill():
    """Fetch latest 10-K for all S&P 500 companies"""
    sp500_tickers = await get_sp500_tickers()  # 500 tickers

    for ticker in sp500_tickers:
        # Fetch only most recent 10-K
        await edgar_client.get_company_filings(
            ticker=ticker,
            form_types=["10-K"],
            count=1  # Latest only
        )

    # Result: 500 filings, 1.4 hours, 2.5GB storage
```

**Screening metrics available**:

- Latest revenue, net income, EPS, total debt, EBITDA, total assets, equity
- Latest margins: Gross margin, operating margin, net margin
- Latest ratios: Debt/EBITDA, ROE, current ratio
- **Proxy CAGR**: If can fetch last 2-3 10-Ks (add optional fetch):

  ```python
  # Optionally fetch 3 latest 10-Ks for better proxy
  count=3  # Gets 2024, 2023, 2022
  # Calculate 2Y CAGR as proxy for 10Y
  ```

**Timeline**: Run Saturday morning, operational by afternoon

---

### Phase 2: Deep Analysis Backfill (On-Demand)

**Objective**: Fetch 10Y data for companies approved at Human Gate 1

**Trigger**: Lead Coordinator receives Human Gate 1 approval

**Implementation**:

```python
# In lead_coordinator.py
@on_human_gate_1_approval
async def prepare_deep_analysis(approved_tickers: list[str]):
    """
    Triggered after Screening Agent completes and human approves candidates

    Args:
        approved_tickers: List of 5-10 companies approved for deep analysis
    """
    # Fetch 10Y data in parallel
    tasks = []
    for ticker in approved_tickers:
        task = data_collector.fetch_historical_data(
            ticker=ticker,
            form_types=["10-K", "10-Q"],
            start_year=2014,
            end_year=2024
        )
        tasks.append(task)

    # Parallel execution: 10 companies × 10 min = 10 min total
    await asyncio.gather(*tasks)

    # Notify when ready
    await message_bus.send(
        to_agent="BusinessResearchAgent",
        message_type="DATA_READY",
        content={"tickers": approved_tickers}
    )
```

**Timeline**:

- Day 2 evening: Human Gate 1 approval
- Day 2 11pm - Day 3 12:10am: Data backfill (10 min)
- Day 3 morning: Analyst agents start with full 10Y data

---

### Phase 3: Incremental Expansion (Optional)

**Objective**: Pre-fetch deep data for high-probability candidates

**Strategy**: During Screening Agent execution, predict likely candidates and pre-fetch

**Implementation**:

```python
# In screening_agent.py
async def screen_companies(self):
    results = []

    for company in sp500_companies:
        score = await self.calculate_screen_score(company)
        results.append((company, score))

    # Sort by score
    results.sort(key=lambda x: x[1], reverse=True)

    # Top 20 are very likely to pass Human Gate 1
    top_20 = [ticker for ticker, score in results[:20]]

    # Speculatively pre-fetch deep data in background
    asyncio.create_task(
        data_collector.fetch_historical_batch(top_20)
    )

    # Continue with screening, data fetches in parallel
    return results[:50]  # Return top 50 to human
```

**Benefit**: If human approves top 10, data already fetched (0 latency)

**Risk**: If human picks different 10, wasted 20 × 40 × 5MB = 4GB storage

---

## 5. Trade-offs and Decision Factors

### Trade-off Matrix

| Factor                    | Comprehensive   | Recent Only | On-Demand         | Hybrid               |
| ------------------------- | --------------- | ----------- | ----------------- | -------------------- |
| **Upfront time**          | 55 hours ❌     | 11 hours ⚠️ | 0 hours ✅        | 1.4 hours ✅         |
| **Analysis latency**      | 0 min ✅        | 0 min ✅    | 10 min ❌         | 10 min ⚠️            |
| **Storage efficiency**    | 100GB ❌        | 20GB ⚠️     | 10GB ✅           | 2.5GB + 2GB/batch ✅ |
| **Screening capability**  | Full 10Y ✅     | 2Y only ❌  | None ❌           | Proxy (2-4Y) ⚠️      |
| **Analysis completeness** | Full 10Y ✅     | 2Y only ❌  | Full 10Y ✅       | Full 10Y ✅          |
| **SEC-friendly**          | Risky (bulk) ❌ | OK ⚠️       | Best (gradual) ✅ | Good ✅              |
| **Pattern learning**      | Immediate ✅    | Limited ⚠️  | Gradual ⚠️        | Gradual ⚠️           |

### Decision Factors

**Choose Comprehensive if**:

- Committed to analyzing all S&P 500 companies
- Can afford 55-hour deployment delay
- Storage costs not a concern (100GB acceptable)
- Want L3 Knowledge Graph fully populated from day 1

**Choose Recent Only if**:

- MVP/Beta testing only
- Short-term trading focus (not 10Y fundamental analysis)
- Need fast deployment (<12 hours)

**Choose On-Demand if**:

- Unknown company universe (not fixed S&P 500)
- Storage severely constrained
- Analysis is rare/ad-hoc (not regular workflow)

**Choose Hybrid if** (RECOMMENDED):

- Production fundamental analysis system
- 12-day pipeline with screening phase (Days 1-2)
- Balance between deployment speed and analysis completeness
- Efficient storage (only fetch what you analyze)

---

## 6. Implementation Details

### Hybrid Backfill Queue Design

**Priority Levels**:

```python
class FetchPriority(Enum):
    CRITICAL = 1   # Human Gate 1 approved (fetch immediately)
    HIGH = 2       # Top 20 screening candidates (speculative pre-fetch)
    MEDIUM = 3     # Latest 10-K for all S&P 500 (initial screening)
    LOW = 4        # Historical backfill for long-tail companies
```

**Queue Implementation**:

```python
# In data_collector_agent.py
class BackfillQueue:
    def __init__(self):
        self.queue = asyncio.PriorityQueue()

    async def add_task(self, ticker: str, priority: FetchPriority,
                       form_types: list[str], years: range):
        """Add backfill task to priority queue"""
        task = BackfillTask(
            ticker=ticker,
            priority=priority.value,
            form_types=form_types,
            years=years,
            created_at=datetime.now()
        )
        await self.queue.put((priority.value, task))

    async def process_queue(self, num_workers: int = 10):
        """Process queue with parallel workers"""
        workers = [
            asyncio.create_task(self._worker(worker_id))
            for worker_id in range(num_workers)
        ]
        await asyncio.gather(*workers)

    async def _worker(self, worker_id: int):
        """Worker processes tasks from queue"""
        while True:
            priority, task = await self.queue.get()

            # Rate limiting: 1 req/sec per worker (10 workers = 10 req/sec max)
            await rate_limiter.acquire()

            try:
                await self._fetch_and_store(task)
            except Exception as e:
                logger.error(f"Worker {worker_id} failed: {task.ticker} - {e}")
                # Re-queue with lower priority
                await self.queue.put((priority + 1, task))
            finally:
                self.queue.task_done()
```

### Lead Coordinator Integration

**Phase 1: Screening Preparation**:

```python
# In lead_coordinator.py
async def start_screening_phase(self):
    """Day 1: Prepare screening data"""
    # Check if screening data exists
    coverage = await postgres.get_coverage_stats()

    if coverage["sp500_latest_10k"] < 500:
        # Fetch missing latest 10-Ks
        missing = await postgres.get_missing_latest_10k()

        for ticker in missing:
            await backfill_queue.add_task(
                ticker=ticker,
                priority=FetchPriority.MEDIUM,
                form_types=["10-K"],
                years=range(2024, 2025)  # Latest only
            )

        # Wait for completion
        await backfill_queue.queue.join()

    # Launch Screening Agent
    await self.launch_agent("ScreeningAgent")
```

**Phase 2: Analysis Preparation**:

```python
# In lead_coordinator.py
async def start_analysis_phase(self, approved_tickers: list[str]):
    """Day 3: Prepare deep analysis data"""
    for ticker in approved_tickers:
        # Check if 10Y data exists
        coverage = await postgres.get_filing_coverage(ticker)

        if coverage["total_filings"] < 40:
            # Fetch full 10Y history
            await backfill_queue.add_task(
                ticker=ticker,
                priority=FetchPriority.CRITICAL,  # Blocking priority
                form_types=["10-K", "10-Q"],
                years=range(2014, 2025)
            )

    # Wait for CRITICAL tasks only (other priorities can continue in background)
    await backfill_queue.wait_for_critical()

    # Launch analyst agents
    await self.launch_agents([
        "BusinessResearchAgent",
        "FinancialAnalystAgent",
        "StrategyAnalystAgent"
    ])
```

---

## 7. Success Metrics

### Deployment Metrics

**Hybrid backfill should achieve**:

- ✅ Screening operational in <2 hours (vs 55 hours comprehensive)
- ✅ Analysis latency <15 min (10 min data fetch + 5 min buffer)
- ✅ Storage <5GB in Week 1 (vs 100GB comprehensive)
- ✅ SEC compliance: <10 req/sec sustained rate

### Coverage Metrics

**Track in PostgreSQL**:

```sql
-- Coverage dashboard view
CREATE VIEW backfill_coverage AS
SELECT
    COUNT(DISTINCT ticker) as total_companies,
    COUNT(DISTINCT CASE WHEN has_latest_10k THEN ticker END) as screening_ready,
    COUNT(DISTINCT CASE WHEN filing_count >= 40 THEN ticker END) as analysis_ready,
    AVG(filing_count) as avg_filings_per_company,
    SUM(CASE WHEN filing_count >= 40 THEN filing_count ELSE 0 END) as total_deep_filings
FROM (
    SELECT
        ticker,
        COUNT(*) as filing_count,
        MAX(CASE WHEN form_type = '10-K' AND fiscal_year = 2024 THEN 1 ELSE 0 END) as has_latest_10k
    FROM document_registry.filings
    GROUP BY ticker
) company_stats;
```

**Monitoring**:

- Screening ready: 500/500 (100%) after Phase 1
- Analysis ready: 0/500 initially, grows to 10/500 after first Gate 1, eventually 50+/500

---

## 8. Unresolved Questions

### 1. Screening Without Full 10Y Data

**Question**: How to run "10Y revenue CAGR >15%" screen with only latest 10-K?

**Options**:

- **A. Proxy CAGR**: Fetch last 3 10-Ks (2022, 2023, 2024), calculate 2Y CAGR, assume 10Y similar

  - Pros: Quick approximation
  - Cons: Misses companies with recent acceleration/deceleration

- **B. Alternative metrics**: Use metrics available in latest 10-K

  - Filter: "5Y revenue growth >X%" (disclosed in 10-K Item 6)
  - Filter: "Latest revenue >$1B AND latest margin >15%" (growth-agnostic)
  - Pros: No historical data needed
  - Cons: Different screening logic than 10Y CAGR

- **C. Pre-fetch 3 years**: Modify Phase 1 to fetch 3 latest 10-Ks instead of 1
  - Scope: 500 × 3 = 1,500 filings (vs 500)
  - Timeline: 1,500 / 6 = 250 min = 4.2 hours (vs 1.4 hours)
  - Enables: 2Y CAGR calculation as proxy

**Recommendation**: Option C (fetch 3 latest 10-Ks in Phase 1)

- Still fast (4 hours vs 1.4 hours, acceptable)
- Enables reasonable 2Y CAGR proxy
- Marginal storage increase (7.5GB vs 2.5GB)

### 2. Speculative Pre-Fetching Risk

**Question**: Should Screening Agent speculatively pre-fetch top 20 candidates?

**Risk**: Human picks different 10 → wasted 4GB storage

**Mitigation**:

- Monitor Human Gate 1 approval patterns over time
- If top 20 correlation >80%, enable speculative fetch
- If correlation <50%, disable (human preferences unpredictable)

**Decision**: Defer to Phase 2 (after 10+ screening cycles, analyze patterns)

### 3. Long-Tail Companies

**Question**: What if user wants to analyze non-S&P 500 company?

**Current plan**: On-demand fetch (10 min latency)

**Enhancement**: Watchlist pre-fetch

- User provides watchlist of 50 priority tickers (may include non-S&P 500)
- System pre-fetches 10Y data for watchlist in Phase 1
- Benefit: 0 latency for user's actual holdings/interests

**Decision**: Add watchlist feature in Phase C (Data Collector Agent CLI)

---

## 9. Related Design Decisions

- **DD-019**: Data Tier Operations (PostgreSQL partitioning supports large backfills)
- **DD-009**: Data Retention (versioning supports amendments during backfill)
- **data-collector-implementation.md**: Phase D validation uses 10-company backfill test

---

## 10. Next Steps

1. **Phase A**: Implement backfill queue with priority levels
2. **Phase B**: Add `fetch_latest_10k()` and `fetch_historical()` methods to EDGAR client
3. **Phase C**: Integrate backfill queue with Lead Coordinator (Phase 2 dependency)
4. **Phase D**: Test hybrid strategy with 10 real companies, measure latency and storage
5. **Refinement**: Tune Phase 1 to fetch 3 latest 10-Ks (vs 1) for better CAGR proxy

**Decision Date**: 2025-11-20
**Next Review**: After Phase D validation (compare actual vs estimated metrics)
