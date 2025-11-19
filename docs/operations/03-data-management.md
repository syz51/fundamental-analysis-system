# Data Management - Sources, Storage, and Governance

## Overview

This document describes the data architecture supporting the fundamental analysis system, including data sources, storage structures, quality assurance, and governance policies. The system manages traditional analysis data alongside memory-specific data that enables continuous learning.

---

## Data Management

### Data Sources

#### Primary Sources

- **SEC Filings**: 10-K, 10-Q, 8-K, proxy statements
- **Company Data**: Investor presentations, earnings calls
- **Market Data**: Price history, volume, volatility
- **Industry Data**: Sector reports, competitor analysis

**Acquisition Methods**:

- SEC EDGAR API for regulatory filings
- Company investor relations websites
- Market data providers (APIs)
- Industry research databases

**Update Frequency**:

- SEC filings: Real-time as filed
- Market data: Intraday updates
- Company presentations: Event-driven
- Industry reports: As published

#### Secondary Sources

- **News Feeds**: Reuters, Bloomberg, specialized publications
- **Alternative Data**: Web traffic, app downloads, satellite imagery
- **Expert Networks**: Industry consultants, former employees
- **Social Sentiment**: Twitter, Reddit, StockTwits

**Quality Considerations**:

- News: Verify through multiple sources
- Alternative data: Validate correlations before use
- Expert networks: Ensure compliance with regulations
- Social sentiment: Filter noise, identify material signals

**Integration Approach**:

Secondary sources supplement but don't replace primary analysis. They provide:

- Early warning signals
- Validation of trends
- Sentiment context
- Competitive intelligence

#### Macro & Economic Data Sources

**Free APIs (Phase 2)**:

1. **FRED (Federal Reserve Economic Data)**

   - Indicators: GDP, CPI, unemployment, Fed Funds Rate, 10Y Treasury, industrial production
   - Update frequency: Daily for market data, monthly for economic releases
   - API: <https://fred.stlouisfed.org/docs/api/> (free, register for key)
   - Rate limit: 120 requests/minute
   - Coverage: US economic data, 800,000+ time series

2. **IMF WEO Database**

   - Indicators: Global GDP forecasts, inflation, government debt, current account
   - Update frequency: Quarterly (Apr, Jul, Oct, Jan)
   - API: <https://www.imf.org/external/datamapper/api/help> (free, no key)
   - Coverage: 190 countries, global macro forecasts

3. **OECD Stats**

   - Indicators: 700 indicators for 27 EU countries + OECD members
   - Update frequency: Monthly/quarterly depending on indicator
   - API: <https://data.oecd.org/api/> (free, no key)
   - Coverage: OECD countries, harmonized indicators

4. **CBOE (Volatility Indices)**
   - Indicators: VIX (volatility index), put/call ratios
   - Update frequency: Real-time during market hours
   - API: Free via API or web scraping
   - Coverage: US market sentiment indicators

**Paid Options (Phase 3+, deferred)**:

- Bloomberg Terminal: $32K/yr (comprehensive, real-time)
- FactSet: $12K-$50K/yr (company data, screening, peer comps)
- IBISWorld: $15K-$25K/yr (industry reports, competitive landscape)

**Data Refresh Schedule**:

- Market data (S&P, VIX): Daily at 5am ET (post-market close)
- Economic indicators: Daily fetch, updates vary by release schedule
- Macro reports: Monthly (1st week of month)

---

## Enhanced Data Storage Architecture

```text
/data
├── /raw (Tiered: Hot → Warm → Cold → Delete)
│   ├── /sec_filings
│   ├── /transcripts
│   ├── /market_data
│   └── /news_articles
├── /processed (Tiered: Hot → Warm → Cold → Delete)
│   ├── /financial_statements
│   ├── /ratios
│   ├── /sentiment_scores
│   └── /peer_comparisons
├── /models
│   ├── /dcf_models
│   ├── /relative_valuations
│   └── /sensitivity_analyses
├── /memory                          # NEW
│   ├── /knowledge_graph
│   │   ├── /nodes
│   │   └── /relationships
│   ├── /agent_memories
│   │   ├── /financial_agent
│   │   ├── /strategy_agent
│   │   └── /valuation_agent
│   ├── /patterns
│   │   ├── /validated
│   │   └── /candidates
│   ├── /pattern_archives           # NEW (DD-009)
│   │   ├── /{pattern_id}/
│   │   │   ├── /tier1              # Lightweight (1-5MB, 7yr)
│   │   │   │   ├── metadata.json
│   │   │   │   ├── processed_summary.json
│   │   │   │   └── analysis_snapshot.json
│   │   │   ├── /tier2              # Full (50-200MB, 10yr, if critical)
│   │   │   │   ├── all_tier1_content/
│   │   │   │   ├── processed_data/
│   │   │   │   ├── agent_analysis/
│   │   │   │   └── validation_history/
│   │   │   └── archive_metadata.json
│   │   └── index.json              # pattern_id → archive_tier mapping
│   └── /outcomes
│       ├── /predictions
│       ├── /actuals
│       └── /lessons_learned
└── /outputs
    ├── /reports
    ├── /watchlists
    └── /decision_logs
```

### Directory Structure Details

#### /raw

Unprocessed source data in original format.

**Subdirectories**:

- **/sec_filings**: 10-K, 10-Q, 8-K, proxies (HTML/XML)
- **/transcripts**: Earnings call transcripts (TXT/PDF)
- **/market_data**: OHLCV data, corporate actions (CSV)
- **/news_articles**: News feeds and articles (JSON)

**Retention**: 7-10 years (tiered: Hot 0-2yr, Warm 2-5yr, Cold 5-10yr)

- Pattern-aware: Files supporting active patterns retained up to 10yr
- Non-pattern files: Eligible for deletion after 7yr
  **Size Estimate**: ~50GB/year new data
  **Storage Cost**: ~$5/mo for full 10yr retention (tiered)

#### /processed

Cleaned, normalized, and structured data ready for analysis.

**Subdirectories**:

- **/financial_statements**: Income statement, balance sheet, cash flow (parquet)
- **/ratios**: Calculated financial metrics (parquet)
- **/sentiment_scores**: NLP-derived sentiment (JSON)
- **/peer_comparisons**: Comparative metrics across peers (parquet)
- **/macro_indicators**: Economic time series (FRED, IMF, OECD) (JSON/CSV)
- **/industry_reports**: (Future Phase 3+)
- **/peer_groups**: (Future Phase 3+)

**Retention**: 7-10 years (tiered: Hot 0-2yr, Warm 2-5yr, Cold 5-7yr)

- Critical pattern evidence: Archived separately, retained 7-10yr
- Non-critical files: Eligible for deletion after 7yr
  **Size Estimate**: ~15GB/year new processed data
  **Storage Cost**: Included in tiered storage (~$5/mo total)

#### /search_indices

Unified hybrid search indices combining full-text (BM25) and semantic vector (kNN) search.

**Indices** (per [DD-029](../design-decisions/DD-029_ELASTICSEARCH_INDEX_MAPPING_STANDARD.md)):

- **sec_filings**: SEC filings (10-K/Q/8-K) with text + embeddings + filing metadata
- **transcripts**: Earnings calls with text + embeddings + speaker/segment metadata
- **news**: News articles with text + embeddings + event tracking metadata

**Technology**: Elasticsearch 8+ with unified hybrid search ([DD-027](../design-decisions/DD-027_UNIFIED_HYBRID_SEARCH_ARCHITECTURE.md))
**Schema**: Shared core schema (14 fields) + domain-specific extensions (DD-029)
**Retention**: Rebuildable from /raw (text) + embedding model (vectors)
**Size Estimate**: ~20-25% of raw text volume (includes dense_vector fields)

#### /models

Valuation models and scenario analyses.

**Subdirectories**:

- **/dcf_models**: Discounted cash flow models (Excel/JSON)
- **/relative_valuations**: Peer multiples analysis (parquet)
- **/sensitivity_analyses**: Scenario outputs (JSON)

**Retention**: Permanent (all versions)
**Size Estimate**: ~50GB per year

#### /memory (NEW)

Memory-specific data enabling institutional learning.

**Subdirectories**:

##### /knowledge_graph

Central graph database of all analyses and relationships.

- **/nodes**: Company, Analysis, Pattern, Decision, Agent entities
- **/relationships**: HAS_ANALYSIS, IDENTIFIED_PATTERN, LED_TO, SIMILAR_TO edges

**Technology**: Neo4j graph database
**Retention**: Permanent
**Size Estimate**: ~100GB per year

##### /agent_memories

Domain-specific caches for each specialist agent.

- **/financial_agent**: Ratio patterns, accounting red flags, peer comparisons
- **/strategy_agent**: Management patterns, capital allocation histories
- **/valuation_agent**: Model templates, multiple histories, sector norms
- **/macro_agent**: Regime patterns, forecast accuracy, sector rotation history

**Technology**: Redis (L2 Specialized Cache)
**Retention**: 30 days (with selective promotion to central graph)
**Size Estimate**: ~10GB per agent

##### /patterns

Discovered patterns and their validation status.

- **/validated**: Human-approved patterns used in decisions
- **/candidates**: Statistically validated but awaiting human approval

**Technology**: JSON with metadata
**Retention**: Permanent (with status tracking)
**Size Estimate**: ~5GB per year

##### /pattern_archives (NEW - DD-009)

Selective archiving of pattern evidence for re-validation and compliance.

- **/{pattern_id}/tier1/**: Lightweight archives (metadata + processed summaries)

  - Created: First validation pass
  - Contents: metadata.json, processed_summary.json, analysis_snapshot.json
  - Size: 1-5MB per pattern
  - Retention: 7 years
  - Coverage: 80% of validated patterns

- **/{pattern_id}/tier2/**: Full archives (complete processed data + agent analysis)
  - Created: Investment decision OR critical pattern (2-of-4 criteria)
  - Contents: All tier1 + full processed data + agent analysis + validation history
  - Size: 50-200MB per pattern
  - Retention: 10 years
  - Coverage: 10-20% of validated patterns (critical only)

**Technology**: File storage with index.json mapping
**Retention**: Tiered (7yr lightweight, 10yr full)
**Size Estimate**: ~17GB Tier 1 + ~200GB Tier 2 at scale
**Storage Cost**: ~$0.22/mo (Cold tier storage)

**Critical Pattern Criteria** (2-of-4 triggers Tier 2):

1. Used in investment decision
2. Confidence score >0.7
3. Impact score >0.5 (>$50K or >10% allocation)
4. Validation count ≥3

**Purpose**:

- Enable pattern re-validation when evidence ages out of tiered storage
- Regulatory compliance for investment decisions
- Deep post-mortem failure investigation
- Agent training on historical patterns

##### /outcomes

Tracking predictions vs. actual results.

- **/predictions**: Original forecasts and assumptions
- **/actuals**: Realized outcomes at checkpoints
- **/lessons_learned**: Extracted insights from prediction errors

**Technology**: PostgreSQL time-series tables
**Retention**: Permanent
**Size Estimate**: ~20GB per year

#### /outputs

Final analysis products.

**Subdirectories**:

- **/reports**: Investment memos, summaries (PDF/HTML)
- **/watchlists**: Position tracking configurations (JSON)
- **/decision_logs**: Complete decision audit trails (JSON)
- **/macro_reports**: Monthly PDFs, dashboards, forecast data
  - **/archive**: All report versions (permanent retention)

**Retention**: Permanent
**Size Estimate**: ~10GB per year

---

## Data Governance

### Quality Assurance

#### Standard Data Quality

**Validation Layers**:

1. **Source verification**

   - Validate data provider credentials
   - Cross-reference with multiple sources
   - Check digital signatures on filings

2. **Timestamp validation**

   - Ensure data freshness
   - Identify stale data
   - Track last update times

3. **Consistency checks**

   - Financial statement balancing
   - Ratio calculation verification
   - Peer group consistency

4. **Outlier detection**

   - Statistical anomaly identification
   - Flag extreme values for review
   - Compare to historical norms

5. **Version control**
   - Track data revisions
   - Maintain change history
   - Enable rollback to previous versions

**Automated Quality Checks**:

- Daily: Market data completeness
- Weekly: Filing availability for covered companies
- Monthly: Peer comparison data consistency
- Quarterly: Full data quality audit

#### Memory-Specific Quality

**Validation Requirements**:

1. **Pattern validation before storage**

   - Hold-out testing (70/15/15 train/val/test split)
   - Blind testing without agent awareness
   - Control group comparisons
   - Statistical significance (p < 0.05)
   - Causal mechanism validation

2. **Confidence scoring for all memories**

   - Prediction accuracy tracking
   - Pattern success rate monitoring
   - Agent credibility scoring
   - Time-weighted confidence decay

3. **Regular memory accuracy audits**

   - Monthly: Pattern performance review
   - Quarterly: Agent credibility recalibration
   - Annual: Full knowledge base audit
   - Continuous: Outcome tracking

4. **Contradiction resolution protocols** ([DD-010](../design-decisions/DD-010_DATA_CONTRADICTION_RESOLUTION.md))

   - Identify conflicting memories (data sources, agent findings)
   - 4-level tiered escalation with timeout/fallback:
     1. Evidence quality evaluation (SEC filing > Bloomberg > news)
     2. Source credibility auto-resolution (differential >0.25)
     3. Human arbitration (6hr timeout, max 3 concurrent, priority routing)
     4. Credibility-weighted fallback (provisional, reviewed at Gate 3)
   - Source credibility tracked via 3-component formula:
     - Base accuracy (historical contradiction outcomes)
     - Source type hierarchy (SEC=1.0, Bloomberg=0.95, Reuters=0.90, etc.)
     - Temporal decay (4.5-year half-life exponential weighting)
   - Critical data contradictions (revenue, margins) block analysis if unresolved at Gate 3
   - Document resolution rationale and update source credibility

5. **Memory versioning and rollback capability**
   - Version all pattern updates
   - Snapshot knowledge graph quarterly
   - Enable rollback to previous states
   - Track pattern lifecycle (candidate → validated → active → deprecated)

**Memory Quality Metrics**:

- Coverage: % of companies with historical context
- Recency: Average age of memory data
- Accuracy: Validated predictions / total predictions
- Pattern stability: Stable patterns / total patterns
- Contradiction rate: Contradictions / total memories
- Utilization: Accessed memories / total memories

### Retention Policy

#### Traditional Data with Tiered Storage

The system uses graduated storage tiers to balance cost with accessibility ([DD-009](../design-decisions/DD-009_DATA_RETENTION_PATTERN_EVIDENCE.md)):

**Storage Tiers**:

| Tier     | Age Range  | Cost/GB/mo | Access Time | Use Case                 |
| -------- | ---------- | ---------- | ----------- | ------------------------ |
| **Hot**  | 0-2 years  | $0.023     | <10ms       | Active analysis          |
| **Warm** | 2-5 years  | $0.010     | <100ms      | Recent history           |
| **Cold** | 5-10 years | $0.001     | <3s         | Historical investigation |

**Raw Data** (tiered retention):

- **0-2 years (Hot)**: Active analysis period

  - Full-speed access for ongoing research
  - Regulatory compliance window

- **2-5 years (Warm)**: Historical reference

  - Recent pattern validation
  - Backtest verification

- **5-10 years (Cold)**: Long-term archive
  - **Pattern-aware retention**: Files supporting active patterns retained
  - Files without pattern dependencies: Eligible for deletion
  - Total retention: 7-10 years based on pattern dependencies

**Processed Data** (tiered retention):

- **0-2 years (Hot)**: Primary analysis period

  - Normalized financial statements
  - Calculated ratios and metrics

- **2-5 years (Warm)**: Validation period

  - Pattern re-validation
  - Model backtesting

- **5-7 years (Cold)**: Extended retention
  - **Pattern-aware retention**: Critical pattern evidence retained 7-10 years
  - Non-pattern files: Eligible for deletion after 7 years
  - Regenerable from raw if needed (raw in Cold tier)

**Models**: All versions retained permanently

- Track modeling evolution
- Enable backtest validation
- Support error analysis

**Reports**: Permanent

- Investment decision documentation
- Compliance requirements
- Historical reference

**Decision logs**: Permanent

- Audit trail maintenance
- Learning from outcomes
- Regulatory compliance

**Pattern Archives** (NEW):

Two-tier selective archiving for critical pattern evidence:

- **Tier 1 (Lightweight)**: Created at first validation

  - Contents: Metadata, processed summaries (1-5MB)
  - Retention: 7 years
  - Triggers: Pattern passes validation (DD-007)
  - Storage: `/data/memory/pattern_archives/{pattern_id}/tier1/`

- **Tier 2 (Full)**: Created for critical patterns
  - Contents: Complete processed data, agent analysis (50-200MB)
  - Retention: 10 years
  - Triggers: Investment decision OR 2-of-4 criteria:
    1. Used in investment decision (auto-qualifies)
    2. Confidence score >0.7
    3. Impact score >0.5 (>$50K position or >10% allocation)
    4. Validation count ≥3
  - Storage: `/data/memory/pattern_archives/{pattern_id}/tier2/`

**Pattern-Aware Retention Logic** ([DD-013](../../design-decisions/DD-013_ARCHIVE_LIFECYCLE_MANAGEMENT.md) extends DD-009):

Before deleting files from Cold tier, system checks:

1. Does file support any active patterns? (query knowledge graph) → RETAIN
2. Does file support deprecated patterns? (check status + deprecation date)
   - If deprecated <18 months ago → RETAIN
   - If deprecated ≥18 months ago → Check archive sufficiency:
     - Late-stage deprecated (human_approved/active/probationary): Require Tier 2 archive
     - Early-stage deprecated (candidate/statistically_validated): Require Tier 1 archive
     - If required tier exists → Safe to delete
     - If required tier missing → RETAIN + ALERT
3. Is pattern under post-mortem investigation? → RETAIN (override time limits)
4. If all checks pass → Eligible for deletion

**Access-Based Tier Re-Promotion** ([DD-019](../../design-decisions/DD-019_DATA_TIER_OPERATIONS.md)):

While files auto-migrate Hot→Warm→Cold based on age, the system monitors access patterns and re-promotes frequently-accessed files to faster tiers:

**Re-Promotion Triggers**:

| From Tier | To Tier | Access Threshold | Recovery Time |
| --------- | ------- | ---------------- | ------------- |
| Warm      | Hot     | 10+ access/week  | <24hr         |
| Cold      | Warm    | 3+ access/week   | <24hr         |

**Access Tracking**:

- PostgreSQL table logs all file accesses (`file_access_log`)
- Weekly materialized view aggregates access counts per file
- Daily re-promotion job identifies candidates exceeding thresholds
- Manual tier override available via admin API (pin files to specific tier)

**Use Cases**:

- Pattern re-validation campaigns (DD-007) accessing historical data frequently
- Post-mortem investigations (DD-006) requiring fast access to archived evidence
- Seasonal analysis patterns (earnings seasons, industry cycles)

**Safety Mechanisms**:

- 7-day safety window: File kept in both tiers during migration
- Manual override priority: Admin-pinned tiers block automatic migrations
- Cost monitoring: Alerts if promotion costs exceed budget thresholds

**Performance Impact**:

- First few accesses: Slower tier latency (Warm: 100ms, Cold: 3s)
- After 24hr: Promoted to faster tier if threshold met
- Expected promotion rate: 10-15% of historical files

**Cost Estimate** (at scale, 1000 stocks/year):

```text
Tiered Storage:
  Hot (130GB):    $2.99/mo
  Warm (195GB):   $1.95/mo
  Cold (130GB):   $0.13/mo
  Subtotal:       $5.07/mo

Pattern Archives (DD-009):
  Tier 1 (17GB):  $0.02/mo
  Tier 2 (200GB): $0.20/mo
  Subtotal:       $0.22/mo

DD-013 Additions (Archive Lifecycle):
  Deprecated pattern retention (18mo, 40GB): $0.72/mo
  Late-stage Tier 2 archives (40 patterns):  $0.40/mo
  Cached index (in-memory, 50MB):            $0.01/mo
  Subtotal:                                  $1.13/mo

DD-019 Additions (Tier Re-Promotion):
  Access tracking (PostgreSQL, 500MB):       $0.01/mo
  Tier promotions (10% Cold→Warm, 5% Warm→Hot): $1.55/mo
  Integrity monitoring (backup storage):     $0.27/mo
  Subtotal:                                  $1.83/mo

Note: In-memory storage tech TBD (see tech-requirements.md)

Total:            $8.25/mo
vs. All Hot:      $23/mo (64% savings)
```

#### Memory Data

- **Working Memory**: 24 hours (active), 14 days (paused)

  - Agent L1 cache for active analysis
  - **Technology**: Redis (L1 Instance) with AOF+RDB hybrid persistence
  - Extended to 14d during pause ([DD-016](../../design-decisions/DD-016_L1_MEMORY_DURABILITY.md)), dual snapshot to Redis + PostgreSQL
  - Cleared after analysis completion
  - Critical items promoted to L2

- **Local Agent Cache**: 30 days (with selective promotion)

  - L2 cache for domain-specific patterns
  - **Technology**: Redis (L2 Instance) with RDB-only persistence
  - High-value items promoted to central graph
  - Auto-refresh from central as needed

- **Central Knowledge Graph**: Permanent

  - Institutional memory core
  - Enables long-term learning
  - Regular backups and versioning

- **Patterns**: Permanent with decay scoring

  - Active patterns tracked continuously
  - Deprecated patterns retained for analysis
  - Time-weighted relevance scoring

- **Outcomes**: Permanent

  - All predictions tracked indefinitely
  - Actual results recorded at checkpoints
  - Enables accuracy measurement over time

- **Human Insights**: Permanent with special protection
  - High-value experiential knowledge
  - Enhanced backup frequency
  - Priority in retrieval algorithms
  - Manual review before any deletion

---

## Data Security & Privacy

### Access Control

#### File Storage Access Control

**Role-Based Permissions** for data files (raw/processed data, models, outputs):

- **Analysts**: Read access to all data, write to outputs
- **Data Engineers**: Full access to raw/processed, read outputs
- **Admins**: Full system access
- **Auditors**: Read-only access to all data
- **External**: No direct access (API only)

#### Memory System Access Control

**Agent-Level Permissions** for memory tiers (L1/L2/L3, patterns, credibility):

The memory system (L1 working memory, L2 agent caches, L3 central knowledge graph) uses separate RBAC with 5 agent roles:

- **agent** (regular specialist agents): read_write_own (L1/L2), read_all (L3), propose patterns
- **knowledge_base_agent**: read_write_own (L1/L2), read_write (L3), validate patterns
- **debate_facilitator**: read_write_own (L1), read_all (L2/L3), access all credibility scores
- **learning_engine**: read_all (L2/L3), read_write_all (credibility scores)
- **human_admin**: full_control (all memory tiers, patterns, audit log)

**Key Differences from File Access**:

- **Agent Isolation**: Agents cannot read/write other agents' L1/L2 memory (prevents cache corruption)
- **L3 Write Restriction**: Only Knowledge Base Agent + Learning Engine can write to central graph
- **Pattern Governance**: Pattern lifecycle (PROPOSED → VALIDATED → APPROVED → ACTIVE) enforced
- **Credibility Protection**: Only Learning Engine can update agent credibility scores
- **Audit Trail**: All memory writes logged (actor, resource, action, old/new values) with 5-year retention

See [DD-020: Memory Access Control](../../design-decisions/DD-020_MEMORY_ACCESS_CONTROL.md) for complete RBAC design and [Memory System - Access Control](../../architecture/02-memory-system.md#access-control--security) for implementation details.

### Sensitive Data Handling

**Material Non-Public Information (MNPI)**:

- Strict prohibition on MNPI usage
- Automatic flagging of potential MNPI
- Compliance review before use
- Segregated storage with enhanced access controls

**Personal Information**:

- Minimal collection (executive names from public filings only)
- No consumer PII collected
- GDPR/CCPA compliance
- Right to deletion support

### Backup & Disaster Recovery

**Backup Strategy**:

- **Hourly**: Critical memory updates (incremental)
- **Daily**: Processed data and models (incremental)
- **Weekly**: Full system backup
- **Monthly**: Offsite archival backup

**Recovery Objectives**:

- RTO (Recovery Time Objective): 4 hours
- RPO (Recovery Point Objective): 1 hour
- Critical path: Knowledge graph and active analyses

---

## Data Pipeline Operations

### Ingestion Workflows

**SEC Filings Pipeline**:

1. Monitor SEC EDGAR RSS feeds
2. Download new filings for tracked companies
3. Extract text and financial tables
4. Parse XBRL for structured data
5. Store raw in /raw/sec_filings
6. Trigger processing pipeline

**Market Data Pipeline**:

1. Intraday API calls to data provider
2. Validate and normalize data
3. Store raw OHLCV data
4. Calculate derived metrics
5. Update time-series database
6. Notify monitoring agents

**News Pipeline**:

1. Consume news feed APIs
2. Filter for covered companies
3. NLP sentiment extraction
4. Identify material events
5. Alert News Monitor Agent
6. Store for future analysis

### Processing Workflows

**Financial Statement Processing**:

1. Extract tables from 10-K/10-Q
2. Standardize line items
3. Calculate growth rates
4. Generate common-size statements
5. Compute financial ratios
6. Store in /processed/financial_statements

**Memory Update Workflow**:

1. Agent discovers insight during analysis
2. Check importance threshold (0.7+)
3. Store in local L2 cache
4. Sync to central knowledge graph
5. Broadcast to relevant agents
6. Update pattern candidates if applicable

---

## Monitoring & Alerting

### Data Quality Monitoring

**Automated Checks**:

- Missing data detection
- Outlier flagging
- Staleness alerts
- Schema validation
- Consistency verification

**Alert Thresholds**:

- CRITICAL: Data completeness <90%
- HIGH: Outliers >3 standard deviations
- MEDIUM: Data age >7 days
- LOW: Minor inconsistencies

### Performance Monitoring

**Metrics Tracked**:

- Ingestion latency
- Processing throughput
- Storage utilization
- Query performance
- Memory sync latency

**Dashboards**:

- Real-time data pipeline status
- Storage capacity trends
- Query performance analytics
- Memory system health

---

## Related Documentation

### Core Documentation

- [System Design v2.0](../../multi_agent_fundamental_analysis_v2.0.md) - Complete system specification
- [Memory Architecture](../architecture/memory.md) - Memory system design details
- [Technical Requirements](../../multi_agent_fundamental_analysis_v2.0.md#appendix-a-technical-requirements) - Infrastructure specifications

### Operations Documentation

- [Analysis Pipeline](./01-analysis-pipeline.md) - Core 12-day analysis workflow
- [Human Integration](./02-human-integration.md) - Human decision gates and interfaces
- [Monitoring & Alerts](../implementation/monitoring.md) - System observability

### Implementation Guides

- [Data Infrastructure Setup](../implementation/data-infrastructure.md) - Database deployment
- [Pipeline Configuration](../implementation/pipeline-config.md) - ETL setup
- [Backup & Recovery](../implementation/backup-recovery.md) - DR procedures
