# Data Collector Agent MVP Design (Google ADK)

**Scope**: Define the MVP implementation of the Data Collector Agent using Google Agent Developer Kit (ADK) while leveraging the repository’s approved tooling (PostgreSQL, MinIO/S3, Redis L1, SEC EDGAR clients, Yahoo Finance integration, EdgarTools parser, Sonnet 4.5 LLM tier).  
**Sources**: `plans/data-collector-implementation.md`, `plans/data-collector-backfill-strategy.md`, `plans/data-collector-parse-failure-strategy.md`, DD-032, DD-031.

---

## 1. Objectives

- Provide the MVP blueprint for an autonomous Data Collector Agent that prepares screening data and deep-dive filings for the 12-day analysis pipeline.
- Anchor orchestration in Google ADK so the agent can register tools, manage memory, and comply with event-driven workflows.
- Ensure all storage, parsing, and validation paths use already-approved repository components.
- Document explicit hand-offs with Screening Agent, Lead Coordinator, QC Agent, and downstream analysts.

### Non-Goals

- Building analyst agents (Business Research, Financial Analyst, etc.).
- Implementing Elasticsearch indexing, Neo4j knowledge graph, or Redis L2 cache (Phase 2+).
- Production hardening of observability stack (Prometheus/Grafana deferred).

---

## 2. Toolchain & Dependencies

| Layer         | Tooling (must-use)                                                                                                               | Purpose                                                                                    |
| ------------- | -------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------ |
| Agent runtime | **Google ADK (Vertex AI Agent Developer Kit)**                                                                                   | Declarative agent graphs, tool adapters, secure secret handling, built-in monitoring hooks |
| External data | SEC EDGAR HTTP endpoints (free, 10 req/sec)                                                                                       | Filing acquisition + screening metrics via edgartools parser                               |
| Parsing       | `edgartools`, custom deterministic parser, Sonnet 4.5 (Tier 2), QC Agent (Tier 3)                                                | Multi-tier recovery per parse failure strategy                                             |
| Storage       | PostgreSQL schemas (`document_registry`, `financial_data`, `metadata`), MinIO buckets (`raw`, `processed`), Redis L1 (port 6379) | Durable storage + cache deduplication                                                      |
| Messaging     | ADK event bus → Lead Coordinator topics                                                                                          | Trigger fetches post Gate 1, publish readiness                                             |
| Observability | ADK run logs, structured JSON logging, future Prometheus exporters                                                               | Operational insight (Phase 4 enhancer)                                                     |

---

## 3. Google ADK Integration Plan

Google ADK provides composable primitives (Tasks, Tools, Connectors, Memory Stores) that align with the repository’s agent architecture.

1. **Project Skeleton**

   - `agents/data_collector/adk_project.yaml`: declares the agent, required tools, and policies.
   - Entry module `src/agents/data_collector/agent.py` instantiates the ADK runtime via `adk.Agent`.

2. **Tool Registration**

   - Register each repository "tool" as an ADK `ToolSpec`: `postgres_client`, `s3_client`, `redis_l1_client`, `edgar_client`, `filing_parser`, `storage_pipeline`, `screening_calculator`.
   - Each tool exposes async functions tagged with metadata (rate limits, idempotency) so ADK can schedule them.

3. **Task Graph**

   - **ScreeningPrepTask**: scheduled nightly via ADK cron trigger; invokes SEC screening backfill flow (`edgar_screening_backfill_sp500`).
   - **GateApprovalTask**: listens on `gate1.approved` topic; hydrates Deep Data pipeline for approved tickers.
   - **WatchlistTask**: optional ADK queue for user-provided ticker lists.
   - **ParseRecoveryTask**: ADK event triggered by QC Agent feedback to reprocess filings.

4. **State & Memory**

   - ADK short-term memory: maps to Redis L1 keys for deduplication and rate-limit counters.
   - ADK long-term memory: delegates to PostgreSQL coverage views (`backfill_coverage`) for readiness tracking.

5. **Security & Secrets**

   - Store SEC user-agent string, MinIO credentials, PostgreSQL DSN in ADK Secret Manager bindings; mount as env vars referenced by existing clients.

6. **Deployment Targets**
   - Local dev: run ADK agent via `adk run agents/data_collector`.
   - CI: use `adk test` to execute defined scenario suites before merging.
   - Production: ADK-managed service (GCP Cloud Run or Kubernetes) with horizontal scaling = 10 workers (aligns with rate limit math).

---

## 4. Architecture Overview

```text
          +-------------------+
          | Lead Coordinator  |
          +---------+---------+
                    |
        gate1.approved event
                    |
        +-----------v-----------+
        | Google ADK Data Agent |
        +-----------+-----------+
            |       |       |
            |       |       +---------------------------+
            |       |                                   |
   Screening flow   |                        Deep analysis flow
            |       |                                   |
            v       v                                   v
    SimFin Client  EDGAR Client  --> Storage Pipeline --> Redis/Postgres/MinIO
     (+ Finnhub     |
      fallback)     v
            |       Filing metadata + raw docs
            v       (stored + parsed)
        Screening
        metrics
```

**Screening Flow**: SEC EDGAR latest 10-K backfill populates PostgreSQL with screening metrics for all S&P 500 tickers (10 req/sec, ~30 min total); results drive Screening Agent filters.

**Deep Analysis Flow**: Upon Gate 1 approval, SEC filings (10-K/10-Q + amendments) are fetched, parsed via multi-tier stack, persisted, and surfaced to analyst agents.

---

## 5. Detailed Workflows

### 5.1 Screening Backfill (Phase 1)

1. ADK cron trigger (Sat 05:00 UTC) fires `ScreeningPrepTask`.
2. Task enumerates S&P 500 tickers (local static list or upstream service).
3. For each ticker:
   - Check Redis `screening:edgar:{ticker}`; skip if TTL valid (30d).
   - Invoke `edgar_client.get_latest_filing(ticker, '10-K')` to fetch most recent 10-K.
   - Parse filing via multi-tier parser (edgartools + custom tiers).
   - Calculate screening metrics (revenue CAGR, margins, ROE/ROA/ROIC, debt ratios) via `screening_calculator`.
   - Upsert into PostgreSQL `financial_data.screening_metrics` with `data_source='sec_edgar'`.
   - Update Redis cache with computed metrics (TTL 30d).
4. Performance: ~500 API calls (1 per company) at 10 req/sec = ~50 seconds + parsing time (~30 min total).
5. After loop, ADK publishes `screening.ready` event with coverage stats; Lead Coordinator uses this to start Screening Agent.

### 5.2 Deep Data Hydration (Phase 2 trigger, still MVP)

1. Lead Coordinator emits `gate1.approved` payload (tickers, priority, due date).
2. ADK `GateApprovalTask` ingests event, enqueues each ticker into priority queue:
   - `CRITICAL`: approved list
   - `MEDIUM`: top-20 speculative (configurable)
3. Workers (max 10) execute pipeline:
   1. Redis dedupe (`filing:{cik}:{accession}`) and task lock.
   2. `edgar_client.get_company_filings` (bounded count per plan).
   3. Upload raw filing to MinIO `raw/sec_filings/{ticker}/{year}/{accession}.html`.
   4. Parse via Filing Parser stack (EdgarTools → deterministic → LLM → QC).
   5. Insert metadata + structured data into PostgreSQL (atomic transaction).
   6. Update Redis caches + ADK memory for coverage dashboards.
4. Completion triggers `data.ready.{ticker}` events consumed by Business Research and Financial Analyst agents.

### 5.3 Parse Failure Escalation

1. If Tier 2 validation fails, ADK raises `parse.failure` event.
2. QC Agent (Phase 2) responds, posts `parse.recovery` with new data or instructions.
3. ADK `ParseRecoveryTask` replays the filing or finalizes as `SKIPPED/ESCALATED`.

---

## 6. Component Responsibilities

| Component                  | Responsibility                                | Implementation Notes                                                              |
| -------------------------- | --------------------------------------------- | --------------------------------------------------------------------------------- |
| `DataCollectorAgent` (ADK) | Owns task graph, rate limiting, and reporting | Single ADK project with tasks defined above                                       |
| `EDGARClient`              | SEC interface with 10 req/sec cap             | Async HTTP + Redis counters; handles 429/503                                      |
| `SimFinClient`             | Screening metrics fetcher (primary)           | 5 req/sec (START tier), bulk fundamentals download, built-in caching, 10Y data    |
| `FinnhubClient`            | Screening metrics fetcher (fallback)          | 60 calls/min (free tier), activated on SimFin failure (3+ errors)                 |
| `FallbackManager`          | Multi-source orchestration                    | Coordinates SimFin → Finnhub → SEC EDGAR failover sequence                        |
| `MetricsCalculator`        | Compute screening ratios from raw data        | CAGR, margins, ROE/ROA/ROIC, debt ratios from income/balance statements           |
| `StoragePipeline`          | Orchestrates fetch → parse → store            | Ensures atomic DB writes, S3 uploads, and Redis updates                           |
| `FilingParser`             | Multi-tier parsing with validation            | Tier 0 EdgarTools, Tier 1.5 deterministic, Tier 2 LLM, Tier 2.5 validation        |
| `PostgresClient`           | Inserts metadata + financials                 | Bulk insert, idempotent writes, versioning for amendments, `data_source` tracking |
| `S3Client (MinIO)`         | Raw filing persistence                        | Multipart uploads, versioning, path convention enforced                           |
| `RedisL1Client`            | Deduplication, task locks, rate counters      | TTL semantics (24h for screening cache, 1h for tasks, 2s for rate slots)          |
| `CoverageService`          | Reports readiness metrics                     | SQL views (`backfill_coverage`) accessible to ADK tasks                           |

---

## 7. Failure Handling & Resilience

1. **Rate Limits**:
   - SimFin: 5 req/sec (START tier), enforced client-side via `ratelimit` library
   - Finnhub: 60 calls/min, enforced client-side
   - SEC EDGAR: ADK scheduler enforces 1 req/sec per worker; Redis keys `ratelimit:{epoch_second}` guarantee global 10 req/sec
2. **Fallback Sequence**: SimFin (primary) → Finnhub (after 3 consecutive failures) → SEC EDGAR (last resort). `FallbackManager` tracks failure counts and switches sources automatically.
3. **Idempotency**: Postgres unique constraints on `(ticker, accession_number, version)` plus Redis dedupe ensures replays safe.
4. **Parsing Recovery**: Follow `data-collector-parse-failure-strategy.md`; ADK tasks escalate with structured payloads including root cause and context.
5. **Partial Success**: Raw filings always stored even if parsing fails; statuses `RAW_ONLY`, `LLM_PENDING`, `QC_PENDING` tracked.
6. **Amendments**: `document_registry.filings` triggers auto-manage `version` and `is_latest` fields—agent sets `form_type` accurately, parser ensures restated values prioritized.
7. **Google ADK Health Checks**: Use ADK built-in retries for transient tool failures; escalate to Lead Coordinator if task fails >3 times within SLA.

---

## 8. Observability & Reporting

- **Logging**: Structured JSON lines forwarded through ADK logging sink with key fields (`ticker`, `accession`, `stage`, `latency_ms`, `status`).
- **Metrics (MVP)**:
  - Filings/min, parse success rate, storage latency, Redis hit rate (emitted via ADK custom counters).
  - Coverage stats served via Postgres views and surfaced in ADK dashboards.
- **Alerts**:
  - ADK policy: failure rate >5% per 15 min window → notify ops channel.
  - SEC 429 streak >3 → throttle queue automatically, alert for manual review.
- **Future**: Prometheus exporters + Grafana boards once infrastructure matured (Phase 4).

---

## 9. Implementation Plan (10-Day MVP)

| Day | Focus                                           | Key Deliverables                                                                                       |
| --- | ----------------------------------------------- | ------------------------------------------------------------------------------------------------------ |
| 1   | ADK project bootstrap                           | `adk_project.yaml`, tool specs, secret bindings (SimFin, Finnhub keys)                                 |
| 2   | Postgres/MinIO/Redis clients wired as ADK tools | Connection pools, health checks                                                                        |
| 3   | SimFin screening workflow                       | SimFinClient, FinnhubClient, FallbackManager, MetricsCalculator per `plans/simfin-integration-plan.md` |
| 4   | EDGAR client + rate limiter                     | Compliance with SEC UA, 10 req/sec enforcement                                                         |
| 5   | Filing parser Tier 0 + Tier 1.5                 | EdgarTools integration, deterministic fallback                                                         |
| 6   | Storage pipeline + MinIO integration            | Atomic store, logging, Redis dedupe                                                                    |
| 7   | Tier 2 LLM + Tier 2.5 validation                | Sonnet prompt, validation hooks, parse_status updates                                                  |
| 8   | Gate approval workflow                          | Priority queue, ADK event wiring, status reporting                                                     |
| 9   | Testing + CI harness                            | Unit + integration tests, ADK scenario tests, fallback simulation                                      |
| 10  | Documentation + dry run                         | End-to-end rehearsal on 3 companies, finalize guide                                                    |

---

## 10. Testing Strategy

- **Unit**: Clients (Postgres, MinIO, Redis, EDGAR, SimFin, Finnhub), parser tiers, ADK task utilities, MetricsCalculator (use pytest + pytest-asyncio).
- **Integration**:
  - Screening flow: SimFin fetch → metrics calculation → Postgres upsert → coverage view assertion.
  - Fallback flow: Mock SimFin failures → verify Finnhub activation → verify SEC EDGAR last resort.
  - Deep flow: AAPL 10-K fetch → MinIO upload → parsed data persisted.
  - Rate limit: Simulate 100 concurrent requests, ensure SimFin <5 req/sec, SEC <10 req/sec.
- **ADK Scenario Tests**:
  - `scenario_screening_ready`: ensures cron task fills coverage gap using SimFin.
  - `scenario_gate1_batch`: feed Gate 1 event, assert all tickers processed, events emitted.
  - `scenario_parse_failure`: inject malformed XBRL to verify escalation path.
  - `scenario_simfin_fallback`: disable SimFin, verify Finnhub fallback within 3 failures.
- **Load**: 10 companies × 40 filings each (parallel) to validate throughput (>10 filings/min) and memory (<500MB).
- **CI Hooks**: `adk test` + `pytest tests/agents/test_data_collector.py`.

---

## 11. Security & Compliance Considerations

- Store all credentials in ADK Secret Manager; never commit to repo.
- SEC compliance: Unique User-Agent string and contact email per SEC policy.
- Data retention: follow DD-009 (raw filings versioned indefinitely, parsed data permanent).
- Auditing: Postgres triggers capture insert audit trails; ADK logs retained per policy.
- Network: Restrict outbound egress to SEC/Yahoo endpoints plus MinIO/Postgres/Redis internal hosts.

---

## 12. Deliverables Checklist

- `docs/implementation/technical-guides/04-data-collector-agent-mvp.md` (this file).
- ADK configuration + runtime code under `src/agents/data_collector/`.
- Updated plans referencing Google ADK usage (future PRs).
- Automated tests + CI scenarios.

---

## 13. Unresolved Questions

- Need dedicated GCP project for ADK deploy?
- SimFin START tier 5 req/sec sufficient for 500-ticker nightly run (~5 min acceptable)?
- Where store ADK task metrics until Prometheus online?
- Should speculative prefetch enable day one or wait for screening stats?
- SimFin annual payment ($108/year) vs monthly ($15/mo) - budget approval needed?
- Test free SimFin tier first (5Y data) or go straight to START tier (10Y data)?
