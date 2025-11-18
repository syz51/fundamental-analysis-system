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

**Retention**: 7-10 years (tiered: Hot 0-2yr, Warm 2-5yr, Cold 5-7yr)

- Critical pattern evidence: Archived separately, retained 7-10yr
- Non-critical files: Eligible for deletion after 7yr
  **Size Estimate**: ~15GB/year new processed data
  **Storage Cost**: Included in tiered storage (~$5/mo total)

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

**Technology**: Local PostgreSQL/SQLite per agent
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

Note: In-memory storage tech TBD (see tech-requirements.md)

Total:            $6.42/mo
vs. All Hot:      $23/mo (77% savings)
```

#### Memory Data

- **Working Memory**: 24 hours (active), 14 days (paused)

  - Agent L1 cache for active analysis
  - Extended to 14d during pause ([DD-016](../../design-decisions/DD-016_L1_MEMORY_DURABILITY.md)), dual snapshot to Redis + PostgreSQL
  - Cleared after analysis completion
  - Critical items promoted to L2

- **Local Agent Cache**: 30 days (with selective promotion)

  - L2 cache for domain-specific patterns
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

**Role-Based Permissions**:

- **Analysts**: Read access to all data, write to outputs
- **Data Engineers**: Full access to raw/processed, read outputs
- **Admins**: Full system access
- **Auditors**: Read-only access to all data
- **External**: No direct access (API only)

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
