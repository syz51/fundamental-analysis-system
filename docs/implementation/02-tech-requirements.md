# Technical Requirements

## Overview

This document specifies the complete technical stack, infrastructure requirements, and memory-specific capabilities needed to implement the memory-enhanced multi-agent fundamental analysis system.

The system requires sophisticated infrastructure to support parallel agent execution, real-time memory synchronization, pattern learning, and human collaboration at scale.

---

## Infrastructure Requirements

### Compute Resources

#### Production Environment

- **Kubernetes cluster** with auto-scaling
  - 10-50 nodes depending on load
  - CPU-optimized nodes for agents
  - GPU nodes for pattern mining and ML workloads
  - Memory-optimized nodes for graph processing
- **Horizontal scaling**: Support for 1000+ concurrent analyses
- **Vertical scaling**: Individual agents scale based on workload
- **Resource quotas**: Per-agent limits to prevent resource exhaustion

#### Development Environment

- Docker Compose for local development
- Minikube for Kubernetes testing
- Staging environment mirror of production

#### Macro Analyst Compute (Phase 2+)

**Monthly Report Generation**:
- Frequency: Monthly (1st week of month)
- Duration: 2-4 hours (automated batch)
- Process: Fetch indicators → analyze regime → score sectors → generate charts → render PDF

**Daily Monitoring**:
- Frequency: Daily at 5am ET
- Duration: 5-10 minutes
- Process: Regime detection, indicator fetch, threshold checks

**Weekly Sector Scoring**:
- Frequency: Weekly (Sunday night)
- Duration: 15-20 minutes
- Process: Calculate favorability for 11 sectors, update valuations

### Storage Requirements

#### Minimum: 50TB Total Storage

- **Raw data**: 10TB (SEC filings, transcripts, market data)
- **Processed data**: 5TB (statements, ratios, peer comparisons)
- **Models**: 5TB (DCF models, valuations, scenarios)
- **Memory storage**: 20TB (knowledge graph, patterns, outcomes)
- **Outputs**: 5TB (reports, watchlists, logs)
- **Backups**: 5TB (versioned backups, disaster recovery)

#### Macro Data Storage (Phase 2+)

**Macro Indicators** (~3GB/year):
- Time series data (23-28 indicators × daily/monthly × 10 years)
- Format: JSON/CSV, compressed
- Retention: 10 years historical + ongoing

**Macro Reports** (~500MB/year):
- Monthly PDFs (8-12 pages × 12 months × ~2MB each)
- Dashboard data (JSON, charts)
- Retention: Permanent (audit trail)

**Peer Groups** (Future Phase 3+):
- Industry universe mappings
- Comp table data

#### Storage Types

- **SSD**: Hot data, memory caches (10TB)
- **NVMe**: Ultra-low latency for L1/L2 memory (2TB)
- **HDD**: Cold storage, archives (38TB)

### Database Infrastructure

#### PostgreSQL (Structured Data)

- **Version**: 15+
- **Purpose**: Financial statements, ratios, market data, metadata
- **Size**: 5-10TB
- **Configuration**:
  - High-performance SSD storage
  - Connection pooling (PgBouncer)
  - Read replicas for query load
  - Partitioning by date/ticker
  - Automated backups (daily)
- **Schemas**:
  - `financial_data`: Statements, ratios, metrics
  - `market_data`: Prices, volumes, events
  - `metadata`: Companies, sectors, peers
  - `workflow`: Pause/resume state, checkpoints, batch operations (DD-011, DD-012)
  - `access_tracking`: File access logs, weekly aggregations, tier metadata (DD-019)

#### MongoDB (Document Storage)

- **Version**: 6+
- **Purpose**: SEC filings, transcripts, unstructured text, news articles
- **Size**: 10-15TB
- **Configuration**:
  - Sharded cluster (3+ shards)
  - Replica sets for HA
  - Text search indexes
  - GridFS for large documents
  - Automated backups (daily)
- **Collections**:
  - `sec_filings`: 10-K, 10-Q, 8-K, proxies
  - `transcripts`: Earnings calls, presentations
  - `news`: Articles, press releases
  - `reports`: Generated investment memos

#### Neo4j (Knowledge Graph) - NEW

- **Version**: 5+
- **Purpose**: Central knowledge graph, relationships, patterns
- **Size**: 15-20TB
- **Configuration**:
  - Enterprise edition for scale
  - Causal clustering (3+ core servers)
  - Read replicas for query load
  - Full-text search plugin
  - Graph algorithms library (GDS)
  - Automated backups (hourly incremental, daily full)
  - PITR recovery capability (<1hr RTO/RPO)
  - Cross-region backup replication (AWS us-west-2)
  - Secondary backup provider (GCP Cloud Storage)
- **Schemas**:
  - Nodes: Company, Analysis, Pattern, Decision, Agent, Outcome
  - Relationships: HAS_ANALYSIS, IDENTIFIED_PATTERN, LED_TO, PERFORMED, MADE, SIMILAR_TO, PEER_OF
- **Indexes**:
  - Composite indexes on frequently queried properties
  - Full-text indexes on text content
  - Graph algorithm projections
- **High Availability Architecture** (Phase 4):
  - See [DD-021: Neo4j High Availability](../design-decisions/DD-021_NEO4J_HA.md) for complete design
  - Resolves [Flaw #21: Scalability Architecture](../design-flaws/resolved/21-scalability.md)

#### In-Memory Cache & Storage - NEW

**Purpose**: L1/L2 agent working memory, session cache, optional message queue

**Requirements**:

- **Performance**:
  - Sub-millisecond read latency (p95)
  - High throughput (100k+ ops/sec)
  - 500GB-1TB capacity
- **Persistence**:
  - Snapshot-based backup (RDB equivalent)
  - Append-only log (AOF equivalent)
  - Survive restarts without data loss
- **Eviction**:
  - LRU policy for cache data
  - TTL support for temporary data
- **Data Structures**:
  - Key-value storage
  - Hash maps for nested data
  - Lists/sets for collections
- **Namespacing**:
  - `L1:{agent_id}:working`: Agent working memory
  - `L2:{agent_id}:specialized`: Agent domain cache
  - `sessions:{session_id}`: Debate/collaboration sessions
  - Optional: `queue:{topic}` if used for message queue

**Technology Options**: [Redis, Memcached + persistence layer, Dragonfly]
**Decision**: TBD - Phase 2 implementation

**Note**: Role decision (cache-only vs dual cache+queue) deferred to Phase 2. If separate message queue chosen, remove `queue:{topic}` namespace.

#### Vector Database (Semantic Search)

- **Options**: Pinecone, Weaviate, or Qdrant
- **Purpose**: Semantic similarity search for patterns, precedents
- **Size**: 2-5TB
- **Configuration**:
  - Embedding dimension: 1536 (OpenAI ada-002)
  - Distance metric: Cosine similarity
  - Sharding for scale
  - Metadata filtering support

### Message Queue

**Purpose**: Inter-agent communication, memory sync events, learning updates

**Requirements**:

- **Reliability**:
  - At-least-once delivery semantics
  - Persistent storage (survive restarts)
  - Dead letter queue for failed deliveries
  - High availability (no single point of failure)
- **Performance**:
  - Latency: <100ms (p95)
  - Throughput: Support 5-10 concurrent agents
  - Queue depth: 1000 messages per topic
- **Ordering**:
  - Per-sender ordering guarantee
  - Priority levels: 4 tiers (critical, high, normal, low)
- **Retention**:
  - Standard messages: 7 days
  - Memory events: Permanent (or until processed)
  - Configurable per topic
- **Topology**:
  - Topic-based routing with partitioning
  - Broadcast capability (system announcements)
  - Unicast (direct agent-to-agent)
- **Retry Policy**:
  - Max retries: 3 attempts
  - Exponential backoff: 1s, 2s, 4s
  - Dead letter after max retries

**Topic Categories** (implementation-agnostic):

- **Agent Communication**:
  - `agent.findings`: Analysis findings between agents
  - `agent.challenges`: Debate challenges
- **Memory & Learning**:
  - `memory.sync`: Memory synchronization events
  - `memory.updates`: Learning updates, pattern discoveries
- **Human Integration**:
  - `human.gates`: Human decision requests
- **Outcome Tracking**:
  - `outcomes.tracking`: Prediction tracking events

**Technology Options**: [Apache Kafka, RabbitMQ, Redis Streams]
**Decision**: TBD - Phase 2 implementation
**Selection Criteria**: Reliability, operational complexity, existing infrastructure, throughput needs

---

## Database Schema Specification (DD-011, DD-012)

### Workflow Schema (PostgreSQL)

The `workflow` schema contains tables for agent checkpoints and workflow pause/resume state.

#### Table 1: `agent_checkpoints` (DD-011)

**Purpose**: Track agent execution state at subtask boundaries for failure recovery

```sql
CREATE TABLE agent_checkpoints (
    id SERIAL PRIMARY KEY,
    stock_ticker VARCHAR(10) NOT NULL,
    agent_type VARCHAR(50) NOT NULL,
    analysis_id UUID NOT NULL,
    checkpoint_time TIMESTAMP NOT NULL,

    -- Execution state
    progress_pct DECIMAL(5,2),
    current_subtask VARCHAR(100),
    completed_subtasks TEXT[],
    pending_subtasks TEXT[],

    -- Context snapshot
    working_memory JSONB,        -- L1 cache dump
    interim_results JSONB,        -- Partial findings not yet in Neo4j
    agent_config JSONB,           -- Agent configuration

    -- Error details (if checkpoint due to failure)
    failure_reason TEXT,
    error_details JSONB,
    retry_count INT DEFAULT 0,

    -- Metadata
    agent_version VARCHAR(20),    -- For backwards compatibility
    created_at TIMESTAMP DEFAULT NOW(),

    INDEX idx_stock_agent (stock_ticker, agent_type),
    INDEX idx_analysis (analysis_id),
    UNIQUE (analysis_id, agent_type, checkpoint_time)
);
```

**Retention Policy**:

- Success: Delete immediately after analysis completes
- Failure: Retain for 30 days
- Manual override: Flag to preserve for debugging

#### Table 2: `paused_analyses` (DD-012)

**Purpose**: Track pause state for individual stock analyses

```sql
CREATE TABLE paused_analyses (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    stock_id VARCHAR(10) NOT NULL,
    pause_reason TEXT NOT NULL,
    pause_trigger VARCHAR(20) NOT NULL
        CHECK (pause_trigger IN ('AUTO_TIER2', 'MANUAL', 'GATE_TIMEOUT', 'GATE_REJECTION')),
    pause_timestamp TIMESTAMP NOT NULL DEFAULT NOW(),
    resume_timestamp TIMESTAMP,
    checkpoint_id UUID NOT NULL,  -- FK to agent_checkpoints.id
    failed_agent VARCHAR(50),
    resume_dependencies JSONB,  -- {restart: [], skip: [], wait: []}
    status VARCHAR(20) NOT NULL
        CHECK (status IN ('PAUSING', 'PAUSED', 'RESUMING', 'RESUMED', 'STALE', 'EXPIRED')),
    created_by VARCHAR(100) NOT NULL,  -- Username or 'SYSTEM'
    batch_id UUID,  -- FK to batch_pause_operations.id (nullable)
    alert_day3_sent BOOLEAN DEFAULT FALSE,
    alert_day7_sent BOOLEAN DEFAULT FALSE,
    extended_until TIMESTAMP,  -- Grace period extension
    extension_reason TEXT,

    FOREIGN KEY (checkpoint_id) REFERENCES agent_checkpoints(id),
    FOREIGN KEY (batch_id) REFERENCES batch_pause_operations(id)
);

CREATE INDEX idx_paused_stock_status ON paused_analyses(stock_id, status);
CREATE INDEX idx_paused_timestamp ON paused_analyses(pause_timestamp);
CREATE INDEX idx_paused_batch ON paused_analyses(batch_id) WHERE batch_id IS NOT NULL;
CREATE INDEX idx_stale_candidates ON paused_analyses(pause_timestamp) WHERE status = 'PAUSED';
CREATE INDEX idx_alert_day3 ON paused_analyses(pause_timestamp, alert_day3_sent)
    WHERE status = 'PAUSED' AND alert_day3_sent = FALSE;
CREATE INDEX idx_alert_day7 ON paused_analyses(pause_timestamp, alert_day7_sent)
    WHERE status = 'PAUSED' AND alert_day7_sent = FALSE;
```

**Key Fields**:

- `pause_trigger`: Distinguishes auto-pause (Tier 2 failure) vs manual vs gate timeout
- `resume_dependencies`: JSONB storing `{restart: [...], skip: [...], wait: [...]}`
- `alert_day3_sent`, `alert_day7_sent`: Prevent duplicate reminder alerts
- `extended_until`: Grace period for human-requested pause extensions
- `batch_id`: Links to batch operation (if part of batch pause)

**Retention Policy**:

- PAUSED/RESUMING: Until resume or expiration
- RESUMED: Archive after 30 days to `paused_analyses_history`
- STALE: Purge after 30 days from stale date (keep audit log)

#### Table 3: `batch_pause_operations` (DD-012)

**Purpose**: Track batch pause/resume operations for multiple stocks

```sql
CREATE TABLE batch_pause_operations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    batch_name VARCHAR(100) NOT NULL,
    pause_reason TEXT NOT NULL,
    stock_ids TEXT[] NOT NULL,
    total_count INTEGER NOT NULL,
    paused_count INTEGER DEFAULT 0,
    resumed_count INTEGER DEFAULT 0,
    failed_count INTEGER DEFAULT 0,
    status VARCHAR(20) NOT NULL
        CHECK (status IN ('IN_PROGRESS', 'COMPLETED', 'PARTIALLY_FAILED', 'FAILED')),
    concurrency_limit INTEGER DEFAULT 5,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMP,

    CHECK (total_count = array_length(stock_ids, 1))
);

CREATE INDEX idx_batch_name ON batch_pause_operations(batch_name);
CREATE INDEX idx_batch_status ON batch_pause_operations(status);
CREATE INDEX idx_batch_created ON batch_pause_operations(created_at);
```

**Key Fields**:

- `stock_ids`: Array of tickers included in batch (denormalized for quick access)
- `paused_count`, `resumed_count`, `failed_count`: Progress tracking
- `concurrency_limit`: Max parallel operations for this batch

**Retention Policy**: Archive after 90 days to cold storage

#### Table 4: `resume_plans` (DD-012)

**Purpose**: Store dependency-resolved resume execution plans

```sql
CREATE TABLE resume_plans (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    paused_analysis_id UUID NOT NULL,  -- FK to paused_analyses.id
    restart_agents TEXT[] NOT NULL,  -- Agents to restart from checkpoint
    skip_agents TEXT[] NOT NULL,  -- Completed agents to skip
    wait_agents TEXT[] NOT NULL,  -- In-progress agents to check
    plan_created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    executed_at TIMESTAMP,
    execution_status VARCHAR(20) NOT NULL DEFAULT 'PENDING'
        CHECK (execution_status IN ('PENDING', 'IN_PROGRESS', 'COMPLETED', 'FAILED')),

    FOREIGN KEY (paused_analysis_id) REFERENCES paused_analyses(id) ON DELETE CASCADE
);

CREATE INDEX idx_resume_paused_analysis ON resume_plans(paused_analysis_id);
CREATE INDEX idx_resume_execution_status ON resume_plans(execution_status);
```

**Key Fields**:

- `restart_agents`: Agents to re-execute (failed agent + dependents)
- `skip_agents`: Completed agents (from checkpoint)
- `wait_agents`: In-progress agents (check completion before deciding)

**Retention Policy**:

- COMPLETED: Purge after 30 days
- FAILED: Keep for 90 days (debugging)

#### Table 5: `failure_correlations` (DD-017)

**Purpose**: Track correlated failures across stocks for automatic batch operation triggering

```sql
CREATE TABLE failure_correlations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Correlation metadata
    error_signature VARCHAR(16) NOT NULL,  -- Generated signature hash
    detected_at TIMESTAMP NOT NULL DEFAULT NOW(),
    correlation_window_min INTEGER DEFAULT 5,

    -- Correlated failures
    failure_ids UUID[] NOT NULL,  -- FK to agent_failures.id
    stock_tickers TEXT[] NOT NULL,
    failure_count INTEGER NOT NULL,

    -- Root cause inference
    root_cause TEXT,
    inference_confidence DECIMAL(3,2),  -- 0.00-1.00
    data_sources TEXT[],  -- Unique data sources involved
    agent_types TEXT[],  -- Unique agent types involved
    error_types TEXT[],  -- Unique error types involved

    -- Batch operation linkage
    batch_id UUID,  -- FK to batch_pause_operations.id (DD-012)
    batch_triggered_at TIMESTAMP,

    -- Resolution tracking
    resolved_at TIMESTAMP,
    resolution_action VARCHAR(50),  -- 'batch_resumed', 'manually_resolved', 'expired'

    FOREIGN KEY (batch_id) REFERENCES batch_pause_operations(id)
);

CREATE INDEX idx_signature ON failure_correlations(error_signature);
CREATE INDEX idx_detected_at ON failure_correlations(detected_at);
CREATE INDEX idx_unresolved ON failure_correlations(resolved_at) WHERE resolved_at IS NULL;
CREATE INDEX idx_batch ON failure_correlations(batch_id) WHERE batch_id IS NOT NULL;
```

**Key Fields**:

- `error_signature`: 16-char hash of normalized error (agent_type, error_type, data_source, pattern)
- `failure_ids`: Array of individual agent failure IDs that matched signature
- `root_cause`: Human-readable inference (e.g., "Koyfin API quota exceeded")
- `inference_confidence`: Confidence score 0.00-1.00 based on inference rule match quality
- `batch_id`: Links to batch operation (if auto-triggered batch pause)

**Retention Policy**:

- Unresolved: 14 days (active)
- Resolved: Archive after 90 days to cold storage
- Archived: Purge after 1 year (keep audit log)

#### Table 6: `file_access_log` (DD-019)

**Purpose**: Track file access patterns for tier re-promotion decisions

```sql
-- Raw access log (append-only, partitioned by week)
CREATE TABLE file_access_log (
    id BIGSERIAL PRIMARY KEY,
    file_id VARCHAR(255) NOT NULL,
    access_timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    access_type VARCHAR(50),  -- 'read', 'pattern_validation', 'post_mortem'
    agent_id VARCHAR(100),
    tier_at_access VARCHAR(10)  -- 'hot', 'warm', 'cold'
) PARTITION BY RANGE (access_timestamp);

-- Weekly aggregation (materialized view, refreshed daily)
CREATE MATERIALIZED VIEW file_access_weekly AS
SELECT
    file_id,
    COUNT(*) as access_count_7d,
    MAX(access_timestamp) as last_access,
    current_tier,
    promotion_candidate
FROM file_access_log
WHERE access_timestamp > NOW() - INTERVAL '7 days'
GROUP BY file_id, current_tier;

-- Indexes for performance
CREATE INDEX idx_file_access_timestamp ON file_access_log(access_timestamp);
CREATE INDEX idx_file_id_timestamp ON file_access_log(file_id, access_timestamp DESC);
CREATE INDEX idx_weekly_promotion ON file_access_weekly(promotion_candidate) WHERE promotion_candidate = true;
```

**Key Fields**:

- `access_type`: Categorizes access reason (read, pattern_validation, post_mortem)
- `tier_at_access`: Tier where file was stored when accessed (performance tracking)
- `access_count_7d`: Aggregated 7-day access frequency for promotion thresholds

**Re-Promotion Thresholds**:

- Warm → Hot: 10+ accesses per 7-day window
- Cold → Warm: 3+ accesses per 7-day window

**Retention Policy**:

- Raw logs: 30-day rolling window (partition-based cleanup)
- Materialized view: Refreshed daily at 02:00 UTC
- Historical aggregations: Archive after 90 days

### Archival Process

**Monthly job** (runs on day 1 of each month):

```sql
-- Archive completed pauses
INSERT INTO paused_analyses_history
SELECT * FROM paused_analyses
WHERE status = 'RESUMED' AND resume_timestamp < NOW() - INTERVAL '30 days';

DELETE FROM paused_analyses
WHERE status = 'RESUMED' AND resume_timestamp < NOW() - INTERVAL '30 days';

-- Purge stale/expired
DELETE FROM paused_analyses
WHERE status IN ('STALE', 'EXPIRED')
  AND pause_timestamp < NOW() - INTERVAL '30 days';

-- Archive old batch operations
INSERT INTO batch_operations_archive
SELECT * FROM batch_pause_operations
WHERE completed_at < NOW() - INTERVAL '90 days';

DELETE FROM batch_pause_operations
WHERE completed_at < NOW() - INTERVAL '90 days';

-- Archive resolved failure correlations
INSERT INTO failure_correlations_archive
SELECT * FROM failure_correlations
WHERE resolved_at < NOW() - INTERVAL '90 days';

DELETE FROM failure_correlations
WHERE resolved_at < NOW() - INTERVAL '90 days';

-- Clean up old file access logs (DD-019)
-- Partition-based cleanup: Drop partitions older than 30 days
DO $$
DECLARE
    partition_name TEXT;
BEGIN
    FOR partition_name IN
        SELECT tablename
        FROM pg_tables
        WHERE schemaname = 'workflow'
          AND tablename LIKE 'file_access_log_%'
          AND tablename < 'file_access_log_' || to_char(NOW() - INTERVAL '30 days', 'YYYY_MM_DD')
    LOOP
        EXECUTE 'DROP TABLE IF EXISTS workflow.' || partition_name;
    END LOOP;
END $$;
```

---

### API Integrations

#### External APIs

- **SEC EDGAR**: Free, rate-limited to 10 requests/second
- **Financial data providers**:
  - Koyfin (preferred for coverage)
  - Alpha Vantage (backup)
  - Yahoo Finance (free tier)
- **News feeds**:
  - NewsAPI.org
  - Reuters API (if budget allows)
  - RSS aggregation
- **Alternative data** (future):
  - Web traffic (SimilarWeb API)
  - Social sentiment (Twitter API)

#### Macro Data APIs (Phase 2+)

**Required (Free)**:
- **FRED API**: Federal Reserve Economic Data
  - Endpoint: https://api.stlouisfed.org/fred/
  - Authentication: API key (free, register at fred.stlouisfed.org)
  - Rate limit: 120 requests/minute
  - Indicators: GDP, CPI, unemployment, Fed Funds, 10Y Treasury

- **IMF WEO API**: International Monetary Fund World Economic Outlook
  - Endpoint: https://www.imf.org/external/datamapper/api/v1/
  - Authentication: None (open API)
  - Rate limit: Not specified
  - Indicators: Global GDP forecasts, inflation, government debt

- **OECD Stats API**: OECD Statistics
  - Endpoint: https://stats.oecd.org/restsdmx/sdmx.ashx/
  - Authentication: None (open API)
  - Rate limit: Not specified
  - Indicators: 700 indicators, 27 EU countries

- **CBOE VIX**: Chicago Board Options Exchange Volatility Index
  - Options: API (if available) or web scraping
  - Update frequency: Real-time during market hours
  - Indicators: VIX, put/call ratios

**Optional (Paid, Phase 3+)**:
- Bloomberg Terminal: $32K/yr
- FactSet: $12K-$50K/yr

#### Internal APIs

- **Agent Service API**: RESTful API for agent communication
- **Memory Service API**: GraphQL API for knowledge graph queries
- **Dashboard API**: WebSocket + REST for real-time updates
- **Data Collector API**: Batch processing endpoints

---

## Technology Stack

### Backend Requirements

#### Languages

- **Python 3.11+** (primary language for agents)
  - Type hints required
  - Async/await for I/O operations
  - Dataclasses for structured data
- **SQL** (PostgreSQL queries)
- **Cypher** (Neo4j graph queries)
- **TypeScript** (dashboard backend)

#### Agent Framework

- **LangChain** with memory support
  - Agent executor framework
  - Memory integrations (Redis, Neo4j)
  - LLM abstraction layer
  - Tool/function calling
  - Streaming responses
- **Celery** for task orchestration
  - Distributed task queue
  - Periodic tasks (screening, monitoring)
  - Result backends
  - Task routing by agent

#### Async & Concurrency

- **asyncio** for I/O-bound operations
- **uvloop** for performance
- **aiohttp** for async HTTP
- **asyncpg** for async PostgreSQL
- **motor** for async MongoDB

#### Web Framework

- **FastAPI** for agent services
  - OpenAPI documentation
  - Pydantic validation
  - WebSocket support
  - Dependency injection
  - Authentication (OAuth2)

### Frontend Requirements

#### Framework

- **React 18+** with TypeScript
  - Functional components with hooks
  - Context API for state management
  - React Query for server state
  - Suspense for data fetching

#### Visualization

- **D3.js** for custom visualizations
  - Knowledge graph visualization
  - Pattern relationship networks
  - Time series charts
- **Recharts** for standard charts
  - Financial statement charts
  - Performance dashboards
- **Cytoscape.js** for graph visualization
  - Interactive knowledge graph
  - Agent relationship networks

#### UI Components

- **Material-UI** or **Ant Design**
- **TailwindCSS** for custom styling
- **React Table** for data grids

### Orchestration

#### Workflow Engine

- **Apache Airflow** for analysis pipeline orchestration
  - DAG-based workflow definition
  - Task dependencies
  - Retry logic
  - Monitoring and alerting
- **Temporal** (alternative) for more complex workflows
  - Durable execution
  - Long-running workflows
  - Versioning support

#### Task Queue

- **Celery** with Redis/Kafka backend
  - Task routing by agent type
  - Priority queues
  - Rate limiting
  - Result caching

### Analysis Tools

#### Data Processing

- **pandas** for tabular data
  - Financial statement processing
  - Ratio calculations
  - Time series analysis
- **NumPy** for numerical computation
- **Dask** for parallel/distributed processing

#### Statistical Analysis

- **statsmodels** for econometric analysis
  - Regression models
  - Time series decomposition
  - Statistical tests
- **scikit-learn** for machine learning
  - Pattern clustering
  - Anomaly detection
  - Feature importance

#### Time Series Forecasting

- **Prophet** for business metric forecasting
  - Revenue projections
  - Seasonality detection
- **ARIMA/SARIMAX** via statsmodels
- **LSTM** via PyTorch (if needed)

#### Network Analysis

- **NetworkX** for graph algorithms
  - Pattern relationship analysis
  - Agent collaboration networks
  - Company peer networks

### AI & LLM Integration

#### Language Models

- **OpenAI GPT-4** for primary NLP tasks
  - Document analysis
  - Report generation
  - Debate facilitation
- **Anthropic Claude** (alternative/backup)
- **Local models** (future cost optimization)

#### Embeddings

- **OpenAI text-embedding-ada-002**
  - Semantic similarity search
  - Pattern matching
  - Document clustering

#### ML Frameworks

- **scikit-learn** for traditional ML
  - Pattern classification
  - Regression for predictions
  - Clustering for pattern discovery
- **AutoML** (H2O.ai or auto-sklearn)
  - Automated pattern mining
  - Feature engineering
  - Model selection
- **PyTorch** (if deep learning needed)
  - Custom neural networks
  - Fine-tuning embeddings

---

## Memory-Specific Requirements

### Knowledge Graph Infrastructure

#### Neo4j Configuration

- **Memory**: 64GB+ RAM for graph operations
- **CPU**: 16+ cores for parallel queries
- **Storage**: SSD for graph database files
- **Plugins**:
  - Graph Data Science (GDS) library
  - APOC procedures
  - Full-text search
- **Clustering**: 3+ core servers for HA

**Backup & Recovery** ([DD-019](../design-decisions/DD-019_DATA_TIER_OPERATIONS.md)):

- **Backup Strategy**:
  - Hourly incremental backups
  - Daily full backups at 02:00 UTC
  - 30-day retention period
  - Primary: Cross-region replication (AWS us-west-2)
  - Secondary: Separate provider (GCP Cloud Storage)
- **Recovery SLAs**:
  - RTO (Recovery Time Objective): <1 hour
  - RPO (Recovery Point Objective): <1 hour (hourly backup granularity)
  - Minor corruption: <15min (automated repair)
  - Catastrophic failure: <1hr (PITR restore from primary)
  - Provider outage: <4hr (restore from secondary GCP)

**Integrity Monitoring**:

- **Real-Time** (Prometheus):
  - Transaction failure rate monitoring (<1% threshold)
  - Constraint violation alerts
  - Replication lag monitoring (<30s threshold)
- **Hourly Checks** (every :05):
  - Relationship count anomaly detection (±20% from baseline)
  - Index consistency verification
  - Recent write failure detection
- **Daily Comprehensive** (02:00 UTC):
  - Orphaned relationship scan
  - Missing required properties check
  - Pattern evidence link validation
  - Agent credibility score range validation
  - Duplicate node detection
  - Circular reference detection
- **Automated Repair**:
  - Orphaned relationship cleanup
  - Missing property restoration (default values)
  - Failed index rebuilding
  - Duplicate node merging

#### Graph Processing

- **NetworkX** for algorithm prototyping
- **Neo4j GDS** for production algorithms
  - PageRank for pattern importance
  - Community detection for pattern clusters
  - Shortest path for precedent search
  - Similarity algorithms

### Cache Layer Infrastructure

#### Redis Configuration

- **L1 Cache** (working memory):
  - Namespace per agent
  - TTL: 24 hours
  - Size: 100MB per agent
  - Eviction: LRU
- **L2 Cache** (specialized memory):
  - Namespace per agent domain
  - TTL: 30 days
  - Size: 1GB per agent
  - Persistence: RDB snapshots
- **Replication**: Master-replica for read scaling

#### Cache Warming

- Pre-load frequently accessed patterns
- Pre-compute common graph queries
- Background refresh of expiring data

### Vector Database Requirements

#### Embedding Pipeline

- Batch embedding generation (1000s/minute)
- Incremental index updates
- Multi-tenancy support (by agent)
- Metadata filtering (sector, date, pattern type)

#### Search Performance

- Sub-100ms query latency
- Top-K retrieval (K=10-100)
- Hybrid search (vector + metadata filters)
- Result re-ranking by relevance

### Memory Synchronization Infrastructure

#### Event-Driven Sync Protocols

**Three-Tier Priority System**:

- **Critical sync** (<2s): Debates, challenges, human gates

  - Immediate bidirectional sync (L1/L2 ↔ L3)
  - Blocks until complete
  - Creates memory snapshots for consistency

- **High-priority sync** (<10s): Important findings, alerts

  - Fast push: L2 → L3 for discoveries (importance > 0.7)
  - Fast pull: L3 → L2 for relevant updates
  - Async with priority queuing

- **Normal sync** (5min): Routine updates, batch operations
  - Scheduled push: L2 → L3 for background updates
  - Periodic pull: L3 → L2 for cross-domain insights
  - Standard async queuing

**Message-Triggered Sync**:

System automatically triggers appropriate sync level based on message type:

- Challenge/Alert → Critical
- Finding with precedent → High
- Request/Confirmation → High
- Routine communication → Normal

#### Conflict Resolution

- Timestamp-based ordering with priority override
- Importance-weighted merging
- Locked snapshots during critical operations
- Human arbitration for unresolvable conflicts

---

## Development Tools

### Version Control

- **Git** with GitHub/GitLab
- **Git LFS** for large files
- Branch protection rules
- Code review required

### CI/CD

- **GitHub Actions** or **GitLab CI**
- Automated testing on PR
- Docker image building
- Staging deployment automation
- Production deployment with approval

### Testing

- **pytest** for Python unit/integration tests
- **Jest** for React testing
- **Cypress** for E2E testing
- **Locust** for load testing
- **Great Expectations** for data quality

### Monitoring & Observability

#### Application Monitoring

- **Prometheus** for metrics
- **Grafana** for dashboards
- **ELK Stack** for logs (Elasticsearch, Logstash, Kibana)
- **Jaeger** for distributed tracing

#### Memory Monitoring

- Graph database query performance
- Cache hit rates
- Memory utilization by agent
- Pattern accuracy tracking
- Learning rate monitoring

**Graph Integrity Monitoring** ([DD-019](../design-decisions/DD-019_DATA_TIER_OPERATIONS.md)):

- **Prometheus Metrics**:
  - `neo4j_transaction_failures_total`: Transaction failure count
  - `neo4j_constraint_violations_total`: Constraint violation count
  - `neo4j_replication_lag_seconds`: Replication lag monitoring
  - `neo4j_relationship_count_by_type`: Relationship counts for anomaly detection
  - `neo4j_integrity_check_pass_rate`: Hourly/daily check success rate
  - `neo4j_backup_success_total`: Backup completion status
- **Grafana Dashboards**:
  - Graph Health Overview (transaction throughput, failure rate, memory usage)
  - Integrity Check Status (hourly/daily check results, repair actions)
  - Backup & Recovery (backup status, retention compliance, RTO/RPO metrics)
  - Relationship Trends (count by type, anomaly detection visualization)
- **Alert Thresholds**:
  - Transaction failure rate >1% (5min window) → Page on-call
  - Integrity check failure → Slack ops channel + ticket
  - Backup failure → Email data team + Slack alert
  - Replication lag >30s → Warning alert

#### Alerting

- **PagerDuty** or **Opsgenie** for on-call
- Slack/email notifications
- Alert thresholds for:
  - Memory corruption
  - Pattern accuracy degradation
  - Agent performance issues
  - Human gate timeouts

---

## Security Requirements

### Authentication & Authorization

- OAuth2 for user authentication
- JWT tokens for API access
- Role-based access control (RBAC)
- API key management for external services

### Data Protection

- Encryption at rest (AES-256)
- Encryption in transit (TLS 1.3)
- Secrets management (Vault or AWS Secrets Manager)
- PII detection and masking

### Network Security

- VPC isolation
- Security groups/firewall rules
- DDoS protection
- Rate limiting on APIs

### Compliance

- Audit logging for all decisions
- Data retention policies
- GDPR/CCPA compliance for user data
- SEC compliance for investment recommendations

---

## Scalability Considerations

### Horizontal Scaling

- Stateless agent services (scale to 100s of instances)
- Database read replicas
- Message queue partitioning
- Load balancing (NGINX or ALB)

### Vertical Scaling

- Database server sizing
- Memory-optimized instances for graph DB
- GPU instances for pattern mining

### Cost Optimization

- Spot instances for batch workloads
- Auto-scaling policies
- Data lifecycle management (hot → warm → cold)
- Reserved instances for baseline load

---

## Performance Targets

### Response Times

- **L1 memory access**: <10ms (in-memory cache)
- **L2 memory access**: <50ms (local agent cache)
- **L3 memory access**: <500ms uncached, <200ms cached (p95) - see scalability requirements below
- **API endpoints**: <200ms (p95)
- **Dashboard load**: <2s initial, <500ms interactions

### Throughput

- **Screening**: 1000+ companies/day
- **Analysis**: 50+ companies/day (full analysis), target 200+ at scale
- **Memory queries**: 1000+ queries/second with <5% timeout rate
- **Message processing**: 10,000+ messages/second
- **Cache hit rate**: >80% for memory queries (Phase 3-4)

### Availability

- **System uptime**: 99.5%
- **Database availability**: 99.9%
- **Memory system availability**: 99.9%
- **RTO (Recovery Time Objective)**: <1 hour
- **RPO (Recovery Point Objective)**: <5 minutes

### Scalability Optimization Requirements (DD-005)

To support 1000+ stocks and <24hr analysis turnaround, the system implements comprehensive memory optimization. Requirements are tech-agnostic pending production research.

**Caching Infrastructure**:

- System-wide L1 cache (hot layer):
  - Sub-10ms access time
  - Recent/frequent queries
  - 1hr TTL, ~500MB capacity
  - Tech options: Redis, Memcached, or equivalent
- Query result caching with 80%+ hit rate target
- Cache warming capabilities (predictive preload before analysis)
- Separate cache instances for different priority tiers

**Query Optimization**:

- Pre-computed similarity indexes (offline batch processing):
  - Nightly/weekly rebuild pipeline
  - Top-K storage (e.g., top 10 similar analyses per company)
  - Incremental index updates during day
- Materialized views for common queries:
  - Top patterns by sector
  - Agent credibility scores
  - Peer comparison matrices
- Query budget enforcement (500ms hard timeout):
  - Fallback to approximate results when timeout exceeded
  - Monitoring: alert if >5% queries timeout

**Monitoring Metrics**:

- Memory query latency (p50, p95, p99) by query type
- Cache hit rate tracking and alerting (target >80%)
- Timeout frequency by query type (target <5%)
- Graph query performance at scale (track degradation)
- Query success rate (target >95% within budget or fallback)
- Index rebuild time and staleness metrics
- Agent credibility calculation time (target <10ms incremental)

**Memory Pruning**:

- Archive strategy for >2yr old memories
- Pruning criteria (age, access frequency, relevance, superseded)
- Summarization before archival (preserve key findings)
- Cold storage for archived detail (S3, data warehouse, or equivalent)
- Active graph size limit: <50K nodes

**Benchmarking Requirements**:

- Phase 1-2 (MVP): Baseline at 100 analyses, 100 patterns
- Phase 3 (Beta): Validate at 150-500 analyses, 500-1K patterns
- Phase 4 (Production): Stress test at 600-2K analyses, 1K-3K patterns
- Phase 5 (Scale): Confirm targets at 3K-15K analyses, 3K-5K patterns
- Track: graph query latency, pattern matching time, credibility calc time, cache hit rate, end-to-end memory overhead

---

## Related Documentation

- **Implementation Roadmap**: See `01-roadmap.md` for phased deployment plan
- **System Architecture**: See main design doc Section 2 for high-level architecture
- **Memory Architecture**: See `../architecture/02-memory-system.md` for memory system details with scalability optimizations
- **Risk Assessment**: See `03-risks-compliance.md` for technical risks and mitigation
- **Agent Specifications**: See main design doc Section 4 for agent requirements
- **DD-005: Memory Scalability Optimization**: See `../design-decisions/DD-005_MEMORY_SCALABILITY_OPTIMIZATION.md` for performance optimization design

---

_Document Version: 2.1 | Last Updated: 2025-11-17_
