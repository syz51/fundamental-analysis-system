# Screener Agent: Detailed Design

**Version**: 3.0
**Status**: Design Phase
**Last Updated**: 2025-11-20

## Table of Contents

1. [Overview & Purpose](#overview--purpose)
2. [Core Architecture](#core-architecture)
3. [Screening Logic & Criteria](#screening-logic--criteria)
4. [Memory & Learning](#memory--learning)
5. [Integration Points](#integration-points)
6. [Workflow & Timing](#workflow--timing)
7. [Performance & Scalability](#performance--scalability)
8. [Success Metrics & Monitoring](#success-metrics--monitoring)
9. [Evolution Across Phases](#evolution-across-phases)

---

## Overview & Purpose

### Primary Responsibility

The Screener Agent serves as the entry point to the 12-day analysis pipeline, performing **initial quantitative filtering** and **candidate prioritization** across the investment universe (S&P 500). It acts as the first line of defense, reducing ~500 companies to ~10-20 high-quality candidates for deep analysis.

**Core Function**: Identify companies meeting fundamental quality thresholds using historical financial data, pattern matching from prior analyses, and macro-economic context.

### Position in Analysis Pipeline

- **Timing**: Days 1-2 of 12-day cycle
- **Input**: S&P 500 universe (~500 companies) + macro sector scores (Phase 2+)
- **Output**: Ranked candidate list with one-page summaries → Human Gate 1
- **Next Stage**: Approved candidates proceed to parallel deep analysis (Days 3-7)

### Key Differentiators

1. **Memory-Informed**: Learns from past screening successes/failures, avoiding repeated mistakes
2. **Macro-Aware** (Phase 2+): Weights candidates by sector favorability, not just fundamentals
3. **Checkpoint-Based**: Resilient to failures via subtask checkpointing
4. **Pattern-Driven**: Adjusts thresholds based on sector/market regime patterns

---

## Core Architecture

### Component Structure

```text
┌─────────────────────────────────────────────────────────────────┐
│                       SCREENER AGENT                             │
├─────────────────────────────────────────────────────────────────┤
│  ┌────────────────┐  ┌──────────────────┐  ┌─────────────────┐ │
│  │ Data Fetch     │→ │ Quantitative     │→ │ Summary         │ │
│  │ Engine         │  │ Filter Engine    │  │ Generator       │ │
│  │ (Yahoo/EDGAR)  │  │ (Metrics/Ratios) │  │ (1-page briefs) │ │
│  └────────────────┘  └──────────────────┘  └─────────────────┘ │
│           ↓                   ↓                      ↓           │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │            Pattern Matcher & Ranking Engine                  ││
│  │  - Query historical outcomes from Neo4j                      ││
│  │  - Apply sector weights from Macro Analyst (Phase 2+)        ││
│  │  - Rank by composite score (fundamental × sector × pattern)  ││
│  └─────────────────────────────────────────────────────────────┘│
│           ↓                                                      │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │              Checkpoint Manager (DD-011)                     ││
│  │  - Save state after each subtask (PostgreSQL + Redis)        ││
│  │  - Enable <2s recovery on failure                            ││
│  └─────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────┘
         ↓                           ↑
    [Gate 1]                  [Knowledge Base]
    Human Review              Memory Queries
```

### Checkpoint-Based Execution (DD-011)

The Screener Agent divides work into 4 atomic subtasks, each with persistent checkpoints:

| Subtask               | Deliverable                                | Storage         | Duration | Recovery                 |
| --------------------- | ------------------------------------------ | --------------- | -------- | ------------------------ |
| `screener_data_fetch` | Raw financial metrics (500 companies)      | PostgreSQL      | 5 min    | Restore raw data         |
| `quantitative_filter` | Filtered candidate list (~30-50 companies) | PostgreSQL      | 3 min    | Restore filtered list    |
| `summary_generation`  | One-page summaries (~30-50 briefs)         | PostgreSQL      | 10 min   | Resume at failed summary |
| `priority_ranking`    | Ranked top 10-20 with historical context   | Neo4j + Message | 2 min    | Recompute rankings       |

**Total Screening Cycle**: ~20 minutes
**Failure Recovery Overhead**: <2s (vs 8 min full restart)

**Recovery Example**:

```text
Screening Cycle #47:
  ✅ screener_data_fetch (500 companies, 5 min)
  ✅ quantitative_filter (42 candidates, 3 min)
  ❌ summary_generation (failed at 60%, API timeout)

[Checkpoint restore triggered]
  ↳ Load state from Redis (checkpoint #2)
  ↳ Resume summary_generation for remaining 17 companies
  ↳ No re-fetch or re-filtering required
  ↳ Total overhead: 2s vs 8 min restart
```

### Memory System Integration

**3-Tier Memory Architecture** (see [Memory & Learning](#memory--learning)):

- **L1 (Working Memory)**: Current screening state, active filters, interim results (24hr retention)
- **L2 (Local Cache)**: Domain-specific screening patterns, sector success rates (30d retention, Redis)
- **L3 (Central Graph)**: Validated patterns, historical outcomes, cross-agent learnings (permanent, Neo4j)

**Memory Flow**:

1. Agent queries L2 cache for sector-specific patterns (<50ms)
2. Cache miss → query L3 Neo4j graph (<500ms)
3. Successful screenings promote patterns from L2 → L3 (validated at Gate 6)
4. Failed screenings update L2 false positive/negative tracking

### Data Sources (Unified SEC Approach)

**Screening Stage (Days 1-2)**: Self-made SEC layer with edgartools

- **Metrics**: 10Y revenue/EPS/margins, ROE/ROA/ROIC, debt ratios
- **Universe**: S&P 500 (~500 companies)
- **Quality**: 98.55% (same multi-tier parser as deep analysis)
- **Cost**: $0 (free SEC EDGAR API)
- **Performance**: ~30 min for 500 companies (latest 10-K only)

**Why SEC EDGAR for Screening?**

- Single authoritative source (no data consistency issues)
- Zero ongoing costs vs third-party APIs
- Same parser reused for deep analysis (no duplication)
- Sufficient performance (~30 min one-time backfill acceptable)

**Data Flow**:

```
SEC EDGAR API (500 companies, latest 10-K)
  ↓ Parse via edgartools multi-tier parser
  ↓ Extract revenue, margins, ROE, debt metrics
Screener Agent (quantitative filters)
  ↓ 10Y CAGR ≥ 15%, margins ≥ 8%, debt/EBITDA < 3.0
~30-50 candidates
  ↓ Pattern matching + sector weighting
Top 10-20 candidates
  ↓
Human Gate 1 (approve for deep analysis)
  ↓
SEC EDGAR (approved companies, full 10Y history, Days 3-7)
```

---

## Screening Logic & Criteria

### Quantitative Filters (Phase 1)

**Core Metrics** (adjustable thresholds):

| Metric           | Threshold | Rationale          | Sector Adjustments                   |
| ---------------- | --------- | ------------------ | ------------------------------------ |
| 10Y Revenue CAGR | ≥ 15%     | Sustained growth   | Tech: ≥20%, Utilities: ≥8%           |
| Operating Margin | ≥ 8%      | Profitability      | SaaS: ≥10%, Retail: ≥5%              |
| Net Debt/EBITDA  | < 3.0     | Leverage health    | REITs: <5.0, FinTech: <2.0           |
| ROE              | ≥ 15%     | Capital efficiency | Banks: ≥12%, Industrials: ≥18%       |
| ROIC             | ≥ 12%     | Value creation     | Asset-light: ≥20%, Asset-heavy: ≥10% |
| Current Ratio    | ≥ 1.2     | Liquidity          | Varies by working capital model      |

**Filter Cascade** (sequential elimination):

```
S&P 500 (500 companies)
  ↓ Revenue CAGR filter → ~150 companies
  ↓ Margin filter → ~80 companies
  ↓ Leverage filter → ~50 companies
  ↓ ROE/ROIC filter → ~30-40 companies
```

### Sector-Weighted Scoring (Phase 2+, DD-022)

**Composite Score Formula**:

```
final_score = fundamental_score × sector_weight × pattern_adjustment

Where:
  fundamental_score = weighted sum of metric percentiles (0-100)
  sector_weight = macro_analyst.sector_favorability[sector] / 100
  pattern_adjustment = historical_success_rate[sector, regime] (0.8-1.2)
```

**Pseudocode**:

```python
# Phase 2+: Query Macro Analyst for sector scores
sector_scores = macro_analyst.get_sector_favorability()  # 11 GICS sectors, 0-100 scale

for candidate in filtered_companies:
    # Calculate fundamental score (metrics-based)
    fundamental = calculate_fundamental_score(candidate)

    # Apply sector timing weight
    sector = candidate.gics_sector
    sector_weight = sector_scores[sector] / 100  # Normalize to 0-1

    # Apply pattern adjustment (learned from history)
    pattern = query_pattern_success_rate(sector, current_regime)

    # Composite score
    candidate.final_score = fundamental × sector_weight × pattern

# Rank by final_score, select top 10-20
ranked_candidates = sort_desc(candidates, key='final_score')[:20]
```

**Example Impact**:

- **Scenario**: Tech sector has 30/100 favorability (underweight in bear market)
- **Candidate A**: Tech stock, fundamental_score=85
  - Without sector weighting: score=85 (ranked #3)
  - With sector weighting: score=85 × 0.30 = 25.5 (ranked #47)
- **Candidate B**: Utilities, fundamental_score=72, favorability=90/100
  - Without sector weighting: score=72 (ranked #12)
  - With sector weighting: score=72 × 0.90 = 64.8 (ranked #4)

**Result**: Avoids screening in well-run companies at wrong sector timing.

### Pattern-Based Adjustments (Phase 4+)

**Learned Patterns** (stored in L2/L3 memory):

```yaml
screening_patterns:
  - pattern_id: 'value_trap_tech'
    description: 'Low P/E tech stocks often value traps'
    success_rate: 0.23 # 23% of screened candidates succeeded
    learned_from: ['INTC_2020', 'IBM_2019', 'CSCO_2018']
    sectors: ['Technology']
    regime: ['BEAR_HIGH_RATES']
    adjustment: -0.15 # Reduce score by 15%

  - pattern_id: 'defensive_quality_bear'
    description: 'High-margin consumer staples outperform in bear markets'
    success_rate: 0.78
    learned_from: ['PG_2020', 'KO_2022', 'CL_2020']
    sectors: ['Consumer Staples']
    regime: ['BEAR_HIGH_RATES', 'RECESSION']
    adjustment: +0.20 # Boost score by 20%
```

**Pattern Matching Algorithm** (pseudocode):

```python
def apply_pattern_adjustment(candidate, current_regime):
    matching_patterns = query_patterns(
        sector=candidate.sector,
        regime=current_regime,
        min_confidence=0.7
    )

    if not matching_patterns:
        return 1.0  # No adjustment

    # Weighted average of pattern adjustments
    total_weight = 0
    adjustment_sum = 0

    for pattern in matching_patterns:
        weight = pattern.confidence × pattern.sample_size / 10
        adjustment_sum += pattern.adjustment × weight
        total_weight += weight

    return 1.0 + (adjustment_sum / total_weight)  # Normalize to 0.8-1.2 range
```

### False Positive/Negative Classification

**Definitions** (resolves MINOR-ISSUE #98):

**False Positive**: Candidate screened in (passed filters) but rejected at Gate 5 (final decision)

- **Tracked Reason**: Pattern mismatch, sector timing, qualitative red flags, valuation
- **Learning**: Update pattern success rates, adjust sector thresholds

**False Negative**: Candidate screened out (failed filters) but would have passed Gate 5

- **Detection Method**: Quarterly post-hoc review of rejected companies that gained >30% (market-driven validation)
- **Learning**: Relax overly strict thresholds, identify blind spots (e.g., turnaround stories)

**Classification Logic**:

```python
# At Gate 5 (final decision)
if candidate.gate5_decision == 'REJECT':
    mark_as_false_positive(candidate, reason=gate5_rejection_reason)
    update_pattern_success_rate(candidate.matched_patterns, outcome='fail')

# Quarterly post-hoc review
for rejected in screening_history.last_quarter():
    if rejected.stock_return_3mo > 0.30:  # Gained >30%
        mark_as_false_negative(rejected)
        analyze_missed_criteria(rejected)
        suggest_threshold_relaxation(rejected.failed_filters)
```

---

## Memory & Learning

### 3-Tier Memory Architecture

**L1: Working Memory** (24hr active, 14d paused)

- Current screening state, active filters, interim candidate lists
- Redis storage for fast recovery
- Cleared after Gate 1 approval

**L2: Local Cache** (30d retention)

- Domain-specific screening patterns by sector
- False positive/negative tracking (rolling 90-day window)
- Sector-specific threshold adjustments
- Selective promotion to L3 after validation at Gate 6

**L3: Central Knowledge Graph** (permanent)

- Validated screening patterns with success rates
- Historical candidate outcomes (screened → Gate 5 decision)
- Cross-agent learnings (e.g., Business Agent identifies margin expectation flaws)
- Sector/regime pattern libraries

### Memory Query Patterns

**Pre-Screening Queries** (Days 1-2):

```python
# Query historical analysis of candidate
history = knowledge_base.query(
    company=candidate.ticker,
    fields=['analysis_date', 'gate5_decision', 'outcome', 'lessons']
)

# Query similar companies (sector + metric similarity)
similar = knowledge_base.find_similar(
    sector=candidate.sector,
    metrics={'revenue_cagr': candidate.cagr, 'margin': candidate.margin},
    similarity_threshold=0.85
)

# Query sector patterns for current regime
patterns = knowledge_base.query_patterns(
    sector=candidate.sector,
    regime=current_market_regime,
    min_success_rate=0.60
)
```

**Memory Display at Gate 1**:

```
Candidate: ACME Corp (Technology)
  Fundamental Score: 87/100
  Sector Weight: 0.65 (moderately favorable)
  Final Score: 56.6 (ranked #8)

Historical Context:
  ✓ Analyzed 2022-03-15: Rejected at Gate 3 (valuation too rich)
  ✓ Similar to XYZ Corp (2021): Approved, +42% return (successful pattern)
  ⚠ Pattern Match: 'high_growth_tech_bear' (success_rate: 0.34, caution advised)

Macro Context (Phase 2+):
  • Current Regime: BEAR_HIGH_RATES (confidence: 85%)
  • Sector Favorability: Technology 65/100 (neutral-bearish)
  • Key Risk: Rate sensitivity for unprofitable growth
```

### Learning Mechanisms

**1. Screening Pattern Evolution**

```python
# After Gate 5 decision (final investment decision)
def update_screening_pattern(candidate, gate5_decision):
    matched_patterns = candidate.matched_patterns

    for pattern in matched_patterns:
        # Update success rate (Bayesian update)
        if gate5_decision in ['APPROVE', 'BUY']:
            pattern.successes += 1
        else:
            pattern.failures += 1

        pattern.success_rate = pattern.successes / (pattern.successes + pattern.failures)
        pattern.last_updated = now()

        # Promote to L3 if confidence threshold met
        if (pattern.successes + pattern.failures) >= 10 and pattern.success_rate >= 0.60:
            promote_to_central_graph(pattern)
```

**2. Threshold Adaptation**

```python
# Quarterly review: Adjust sector-specific thresholds
def adapt_sector_thresholds(sector, review_period='Q1_2024'):
    false_positives = query_false_positives(sector, review_period)
    false_negatives = query_false_negatives(sector, review_period)

    # If FP rate > 30%, tighten thresholds
    if len(false_positives) / total_screened(sector) > 0.30:
        increase_threshold(sector, metric='revenue_cagr', delta=+2%)
        increase_threshold(sector, metric='margin', delta=+1%)

    # If FN rate > 15%, relax thresholds
    if len(false_negatives) / total_rejected(sector) > 0.15:
        decrease_threshold(sector, metric='revenue_cagr', delta=-2%)
```

**3. Cross-Agent Learning Propagation**

```python
# Business Research Agent discovers margin pressure trend
business_agent.finding = {
    'sector': 'Consumer Discretionary',
    'finding': 'E-commerce margin compression (shipping costs)',
    'impact': 'Historical 12% margins now 8-9%',
    'recommendation': 'Adjust screening margin threshold'
}

# Screener Agent updates local memory (L2)
screener_agent.update_sector_threshold(
    sector='Consumer Discretionary',
    metric='operating_margin',
    new_threshold=9%,  # Down from 12%
    reason='Business Agent: margin compression trend',
    effective_date='2024-Q2'
)
```

### Memory Sync Triggers

**Event-Driven Priority Sync** (DD-027):

- **Critical** (2s): Macro regime changes, sector favorability updates
- **High** (10s): New screening pattern validated at Gate 6
- **Normal** (5min): Routine threshold updates, false positive tracking

---

## Integration Points

### 1. Macro Analyst (Phase 2+, DD-022)

**Purpose**: Provide sector favorability scores to weight candidates by timing, not just fundamentals.

**Interface**:

```python
# Screener Agent queries Macro Analyst
sector_scores = macro_analyst.get_sector_favorability()
# Returns: {'Technology': 65, 'Financials': 82, 'Energy': 45, ...}  # 11 GICS sectors

# Screener applies weights
for candidate in filtered_companies:
    sector_weight = sector_scores[candidate.sector] / 100
    candidate.final_score = candidate.fundamental_score × sector_weight
```

**Data Flow**:

```
Macro Analyst (weekly batch, 20 min)
  ↓ Analyze market regime + sector positioning
  ↓ Generate 11 sector scores (0-100)
  ↓ Cache in Redis (7d TTL)
Screener Agent (daily screening)
  ↓ Query cached sector scores (<10ms)
  ↓ Apply weights to candidates
  ↓ Rank by composite score
```

**Example Integration**:

- **Without Macro**: 5 tech stocks (strong fundamentals) + 1 defensive stock → All tech selected
- **With Macro**: Bear market, tech=30/100, staples=90/100 → Defensive stock ranked higher despite lower fundamentals

### 2. Knowledge Base Agent

**Purpose**: Provide historical context for candidates and similar companies.

**Queries**:

```python
# Has this company been analyzed before?
history = knowledge_base.query_company_history(ticker='AAPL')
# Returns: [{'date': '2022-03-15', 'decision': 'REJECT', 'reason': 'Valuation', 'outcome': '+18% since'}]

# Find similar companies analyzed previously
similar = knowledge_base.find_similar_companies(
    sector='Technology',
    metrics={'revenue_cagr': 0.18, 'margin': 0.12},
    similarity_threshold=0.85
)
# Returns: [{'ticker': 'MSFT', 'decision': 'BUY', 'return': '+42%', 'lessons': 'Strong moat'}]

# Query sector patterns for current regime
patterns = knowledge_base.query_sector_patterns(
    sector='Technology',
    regime='BEAR_HIGH_RATES',
    min_success_rate=0.60
)
# Returns: [{'pattern': 'quality_defensive_tech', 'success_rate': 0.73, 'examples': ['MSFT', 'AAPL']}]
```

**Memory Presentation at Gate 1**:

- Previous analysis dates and outcomes
- Similar companies with results
- Pattern matches with success rates

### 3. Human Gate 1: Screening Validation

**Timing**: 24-hour review window (Days 2-3)

**Input Provided**:

```
Ranked Candidate Table (top 20):
┌──────┬──────────┬─────────┬────────────┬──────────────┬───────────────────┐
│ Rank │ Ticker   │ Sector  │ Fund Score │ Final Score  │ Key Context        │
├──────┼──────────┼─────────┼────────────┼──────────────┼───────────────────┤
│  1   │ MSFT     │ Tech    │    92      │    59.8      │ Analyzed 2022: +42%│
│  2   │ KO       │ Staples │    78      │    70.2      │ Similar to PG: +28%│
│  3   │ JPM      │ Finance │    85      │    69.7      │ New candidate      │
│ ...  │          │         │            │              │                    │
└──────┴──────────┴─────────┴────────────┴──────────────┴───────────────────┘

Macro Context (Phase 2+):
  • Current Regime: BEAR_HIGH_RATES (confidence: 85%)
  • Top Overweight Sectors: Financials (82), Staples (78), Healthcare (75)
  • Top Underweight Sectors: Tech (65), Consumer Disc (48), Energy (45)
  • Key Macro Risks: Rate shock, earnings recession, credit tightening
```

**Human Actions**:

- **Approve**: Proceed with top N candidates (default: 10)
- **Modify**: Override rankings, add/remove candidates
- **Historical Deep-Dive**: Request detailed history of specific company
- **Add Context**: Inject qualitative memory ("Avoid INTC, prior management issues")

**Default Behavior** (if no response in 24hr):

- Proceed with top 10 candidates
- Log timeout event for Gate 6 review

### 4. Cross-Agent Learning Loops

**Feedback Sources**:

| Source Agent      | Learning Type                                    | Screener Update                           |
| ----------------- | ------------------------------------------------ | ----------------------------------------- |
| Business Research | Margin trends by sector                          | Adjust margin thresholds                  |
| Financial Analyst | Red flags (e.g., related-party transactions)     | Add qualitative filters                   |
| Valuation Agent   | DCF sensitivity (e.g., high rate sensitivity)    | Boost defensive stocks in rate-up regimes |
| QC Agent          | Data quality issues (Yahoo vs SEC discrepancies) | Flag metrics for SEC validation           |

**Learning Propagation Flow**:

```
Business Agent finds: "SaaS margins compressing from 25% → 18%"
  ↓ Publish finding to message queue (priority: High)
  ↓ Knowledge Base stores in central graph (L3)
Screener Agent receives alert (10s sync)
  ↓ Update L2 local memory: SaaS margin threshold 25% → 18%
  ↓ Apply to next screening cycle
  ↓ Monitor false positive rate for validation
Gate 6 (Learning Validation)
  ↓ Human reviews: Is 18% threshold correct?
  ↓ Approve → Promote to L3 permanent pattern
```

---

## Workflow & Timing

### Screening Cycle (Days 1-2)

**Input**:

- S&P 500 universe (~500 companies)
- Current market regime (from Macro Analyst, Phase 2+)
- Sector favorability scores (from Macro Analyst, Phase 2+)
- Historical patterns (from Knowledge Base)

**Processing Steps**:

| Step | Duration | Activity                                                  | Output                      |
| ---- | -------- | --------------------------------------------------------- | --------------------------- |
| 0    | 1 min    | Query Macro Analyst for sector scores (Phase 2+)          | 11 sector weights (0-100)   |
| 1    | 5 min    | Fetch financial metrics from Yahoo Finance API            | Raw data (500 companies)    |
| 2    | 3 min    | Apply quantitative filters (CAGR, margin, debt, ROE)      | ~30-50 filtered candidates  |
| 3    | 10 min   | Generate one-page summaries for each candidate            | 30-50 company briefs        |
| 4    | 2 min    | Query historical context, apply pattern adjustments, rank | Top 10-20 ranked candidates |

**Total Cycle Time**: ~21 minutes (Phase 2+) or ~20 minutes (Phase 1)

**Output**:

```
Top 20 Candidates with Context:
  - Ranked table (ticker, sector, scores, historical context)
  - One-page summaries (key metrics, recent performance, red flags)
  - Macro context (regime, sector favorability, risks)
  - Pattern matches (similar companies, success rates)

Delivered to: Human Gate 1 dashboard
```

### Daily vs Weekly Screening

**Options**:

- **Daily Screening** (aggressive): Monitor for new opportunities daily

  - Cost: 30 screening cycles/month × $50/mo = $50/mo (Yahoo API)
  - Use case: Active monitoring, rapid opportunity capture

- **Weekly Screening** (balanced): Screen every Monday
  - Cost: 4 screening cycles/month × $50/mo = $50/mo (same, pay-per-use)
  - Use case: Reduces Gate 1 fatigue, batches candidates

**Recommendation**: Weekly screening (Mondays) for MVP, daily for production scale.

### Failure Recovery Scenarios

**Scenario 1: Yahoo Finance API Timeout**

```
Step 1: screener_data_fetch → TIMEOUT after 3 min
Recovery:
  ↳ Retry with exponential backoff (3s, 9s, 27s)
  ↳ If 3 retries fail → Fallback to SEC EDGAR bulk fetch (15 min)
  ↳ Resume from Step 2 (quantitative_filter) with SEC data
```

**Scenario 2: Summary Generation Failure (60% complete)**

```
Step 3: summary_generation → FAILURE at 18/30 companies
Recovery:
  ↳ Load checkpoint #2 from Redis (2s)
  ↳ Retrieve completed summaries (18 companies) from PostgreSQL
  ↳ Resume generation for remaining 12 companies (4 min)
  ↳ No re-work of Steps 1-2 or first 18 summaries
```

**Scenario 3: Macro Analyst Unavailable (Phase 2+)**

```
Step 0: Query Macro Analyst → SERVICE_UNAVAILABLE
Recovery:
  ↳ Check Redis cache for sector scores (7d TTL)
  ↳ If cached → Use cached scores with staleness warning
  ↳ If no cache → Default to equal sector weights (1.0 for all)
  ↳ Flag at Gate 1: "Sector scores unavailable, equal weighting applied"
```

---

## Performance & Scalability

### Throughput Targets

**Current Scale (MVP)**:

- **Universe**: S&P 500 (~500 companies)
- **Screening Time**: 20 minutes/cycle
- **Throughput**: 25 companies/minute (bulk fetch parallelization)
- **Gate 1 Candidates**: 10-20 companies/cycle

**Production Scale**:

- **Universe**: S&P 500 + Russell 2000 (~2,500 companies)
- **Screening Time**: Target <60 minutes/cycle
- **Throughput**: 42 companies/minute (requires parallel workers)
- **Gate 1 Candidates**: 20-30 companies/cycle

### Memory Performance

**Retrieval Latency**:

- **L2 Cache (Redis)**: <50ms for pattern queries (target: >80% hit rate)
- **L3 Graph (Neo4j)**: <500ms for complex pattern matching
- **Company History**: <200ms for ticker-based queries

**Cache Hit Rates** (targets):

- **Sector Patterns**: >85% (stable patterns, low churn)
- **Company History**: >60% (repeat analyses common for large caps)
- **Macro Scores**: >95% (weekly batch update, daily reuse)

### Scalability Bottlenecks

**1. Yahoo Finance API Rate Limits**

- Current: 2,000 requests/hour (sufficient for 500 companies)
- Bottleneck at: >1,000 companies (requires request batching)
- Mitigation: Bulk API endpoints, parallel workers with rate limiting

**2. Summary Generation (LLM Calls)**

- Current: 30-50 summaries × 30s/summary = 15-25 min (serial)
- Bottleneck: Serial LLM calls (latency-bound)
- Mitigation: Parallel LLM workers (10 concurrent → 3 min total)

**3. Neo4j Pattern Queries**

- Current: <500ms for complex pattern matching (acceptable)
- Bottleneck at: >10,000 patterns (index degradation)
- Mitigation: Cypher query optimization, pattern pre-computation

### Optimization Strategies

**Phase 1 (MVP)**:

- Single-threaded screening (simplicity over speed)
- No parallelization (acceptable for 20 min cycle)

**Phase 2-3 (Production)**:

- Parallel data fetching (10 workers → 2 min fetch time)
- Parallel summary generation (10 LLM workers → 3 min total)
- Pre-compute sector patterns weekly (cache in Redis)

**Phase 4+ (Scale)**:

- Distributed screening (Celery task queue)
- Incremental screening (only new/changed companies)
- Streaming results to Gate 1 (no wait for full batch)

---

## Success Metrics & Monitoring

### Primary KPIs

**1. Screening Efficiency Rate**

```
Efficiency = Candidates Approved at Gate 5 / Candidates Screened In
Target: >40% (4 of 10 screened candidates reach final approval)
```

**Tracking**:

- Monthly cohort analysis (screen date → Gate 5 decision)
- Breakdown by sector, market regime, pattern type

**2. False Positive Rate**

```
FP Rate = Candidates Rejected at Gate 5 / Total Screened In
Target: <60% (acceptable filtering stage, deep analysis refines)
```

**Classification**:

- **Early rejection** (Gates 2-3): Qualitative red flags (acceptable, screening can't catch all)
- **Late rejection** (Gates 4-5): Valuation/timing issues (suggests screening over-optimized for fundamentals)

**3. False Negative Rate**

```
FN Rate = Missed Opportunities / Total Screened Out
Target: <15% (minimize regret of rejected candidates)
```

**Detection**:

- Quarterly post-hoc review: Screened-out companies with >30% return
- Root cause analysis: Which filters caused rejection?

**4. Pattern Accuracy**

```
Pattern Accuracy = Successful Pattern Matches / Total Pattern Matches
Target: >65% (patterns should predict success more than random)
```

**Tracking**:

- Per-pattern success rates (updated at Gate 5)
- Breakdown by sector, regime, confidence level

### Secondary Metrics

**5. Time to Identify Opportunities**

```
Time = Screen Date → Gate 1 Approval
Target: <48 hours (Days 1-2 screening + 24hr Gate 1)
```

**6. Memory Retrieval Performance**

```
Cache Hit Rate (L2): >80%
Query Latency (L3): <500ms p95
```

**7. Data Quality**

```
Yahoo Finance Data Availability: >95%
SEC EDGAR Fallback Rate: <5%
```

### Monitoring Dashboard

**Real-Time Metrics** (updated per screening cycle):

```
┌─────────────────────────────────────────────────────────┐
│ SCREENER AGENT - CYCLE #47 (2024-11-18)                 │
├─────────────────────────────────────────────────────────┤
│ Status: ✅ COMPLETE (21 min)                             │
│                                                          │
│ Input: 500 companies (S&P 500)                           │
│ Filtered: 42 candidates (8.4% pass rate)                │
│ Top Ranked: 18 candidates (final score ≥50)             │
│                                                          │
│ Memory Performance:                                      │
│   L2 Cache Hit Rate: 87% (37/42 candidates)             │
│   L3 Query Latency: 423ms p95                            │
│   Pattern Matches: 28 patterns applied                   │
│                                                          │
│ Data Quality:                                            │
│   Yahoo Finance: 498/500 companies (99.6%)              │
│   SEC EDGAR Fallback: 2 companies (AAPL, GOOGL)         │
│                                                          │
│ Next Step: Human Gate 1 (24hr deadline: 2024-11-19 9am) │
└─────────────────────────────────────────────────────────┘
```

**Historical Trends** (monthly aggregation):

```
Oct 2024 Performance Summary:
  Screening Efficiency: 38% (15/40 approved at Gate 5) ⚠️ Below 40% target
  False Positive Rate: 62% (25/40 rejected at Gate 5)
  False Negative Rate: 12% (estimated via post-hoc review) ✅
  Pattern Accuracy: 68% (Tech: 72%, Staples: 81%, Energy: 45%) ⚠️ Energy patterns weak
  Avg Cycle Time: 22 min (target: <25 min) ✅

Recommendations:
  - Tighten Tech filters (high FP rate: 71%)
  - Rebuild Energy patterns (low accuracy: 45%)
  - Investigate Gate 5 rejections (primary reason: valuation 68%, timing 22%)
```

### Alerts & Anomalies

**Automated Alerts**:

```python
# Alert triggers
if screening_efficiency < 0.30:
    alert(severity='HIGH', message='Screening efficiency dropped to 28% (target: >40%)')

if false_negative_rate > 0.20:
    alert(severity='CRITICAL', message='Missing 22% of opportunities, review filters')

if cache_hit_rate < 0.70:
    alert(severity='MEDIUM', message='Cache hit rate 68% (target: >80%), check Redis')

if cycle_time > 30_minutes:
    alert(severity='MEDIUM', message='Screening took 32 min (target: <25 min), investigate bottleneck')
```

---

## Evolution Across Phases

### Phase 1: Foundation (MVP)

**Capabilities**:

- ✅ Basic quantitative screening (10Y CAGR, margins, debt, ROE/ROIC)
- ✅ Yahoo Finance API integration (S&P 500)
- ✅ Checkpoint-based execution (4 subtasks)
- ✅ One-page summary generation
- ✅ Human Gate 1 integration (ranked table)
- ❌ No memory system (stateless screening)
- ❌ No pattern learning
- ❌ No macro integration

**Screening Logic**:

```python
# Phase 1: Simple threshold-based filtering
for company in sp500:
    if (company.revenue_cagr_10y >= 0.15 and
        company.operating_margin >= 0.08 and
        company.net_debt_ebitda < 3.0 and
        company.roe >= 0.15):
        candidates.append(company)

# Rank by simple composite score (no sector weighting)
ranked = sort_desc(candidates, key=lambda c: c.revenue_cagr × c.margin × c.roe)
```

**Output**:

- Top 10-20 candidates with key metrics
- No historical context, no pattern matches

**Duration**: Phase 1 (Months 1-3)

### Phase 2: Macro Integration

**New Capabilities**:

- ✅ Macro Analyst integration (sector favorability scores)
- ✅ Sector-weighted composite scoring
- ✅ Basic memory system (L1 working memory only)
- ✅ Company history queries ("Have we analyzed this before?")
- ❌ No pattern learning yet
- ❌ No threshold adaptation

**Screening Logic**:

```python
# Phase 2: Add sector weighting from Macro Analyst
sector_scores = macro_analyst.get_sector_favorability()

for candidate in filtered_candidates:
    fundamental_score = calculate_fundamental_score(candidate)
    sector_weight = sector_scores[candidate.sector] / 100
    candidate.final_score = fundamental_score × sector_weight

ranked = sort_desc(candidates, key='final_score')
```

**Output**:

- Top 10-20 candidates with sector-weighted scores
- Company history (if previously analyzed)
- Macro context (regime, sector scores, risks)

**Duration**: Phase 2 (Months 4-6)

### Phase 3: Memory & Learning

**New Capabilities**:

- ✅ Full 3-tier memory system (L1/L2/L3)
- ✅ Pattern matching (similar companies, success rates)
- ✅ False positive/negative tracking
- ✅ Cross-agent learning (Business/Financial insights → Screener)
- ✅ Gate 6 learning validation
- ❌ No adaptive thresholds yet (manual adjustment only)

**Screening Logic**:

```python
# Phase 3: Add pattern-based adjustments
for candidate in filtered_candidates:
    fundamental_score = calculate_fundamental_score(candidate)
    sector_weight = sector_scores[candidate.sector] / 100

    # Query historical patterns
    patterns = knowledge_base.query_patterns(
        sector=candidate.sector,
        regime=current_regime,
        min_success_rate=0.60
    )

    # Apply pattern adjustment
    pattern_adjustment = calculate_pattern_adjustment(candidate, patterns)

    candidate.final_score = fundamental_score × sector_weight × pattern_adjustment

ranked = sort_desc(candidates, key='final_score')
```

**Output**:

- Top 10-20 candidates with full context
- Pattern matches: "Similar to MSFT (2021): +42% return"
- False positive/negative tracking dashboards

**Duration**: Phase 3 (Months 7-9)

### Phase 4: Advanced Learning & Optimization

**New Capabilities**:

- ✅ Adaptive threshold tuning (automated quarterly reviews)
- ✅ Regime-specific pattern libraries
- ✅ Cross-validation with Watchlist Manager (track long-term outcomes)
- ✅ Advanced pattern evolution (Bayesian updating, confidence intervals)
- ✅ Distributed screening (Celery workers for >1,000 companies)

**Screening Logic**:

```python
# Phase 4: Adaptive thresholds by sector and regime
def get_adaptive_threshold(sector, regime, metric):
    """Dynamically adjust thresholds based on recent FP/FN rates."""
    base_threshold = BASE_THRESHOLDS[metric]
    sector_adjustment = SECTOR_ADJUSTMENTS[sector][metric]
    regime_adjustment = REGIME_ADJUSTMENTS[regime][metric]

    # Apply learned adjustments from quarterly reviews
    learned_adjustment = query_learned_adjustment(sector, regime, metric)

    return base_threshold × (1 + sector_adjustment + regime_adjustment + learned_adjustment)

# Apply adaptive thresholds
for company in sp500:
    thresholds = {
        'cagr': get_adaptive_threshold(company.sector, current_regime, 'revenue_cagr'),
        'margin': get_adaptive_threshold(company.sector, current_regime, 'operating_margin'),
        # ...
    }

    if (company.revenue_cagr_10y >= thresholds['cagr'] and
        company.operating_margin >= thresholds['margin'] and ...):
        candidates.append(company)
```

**Output**:

- Top 10-20 candidates with confidence intervals
- Pattern success rates with Bayesian credibility intervals
- Long-term outcome tracking (1Y/3Y returns for validated patterns)

**Duration**: Phase 4 (Months 10-12)

### Long-Term Vision (Post-MVP)

**Future Enhancements**:

- **Expanded Universe**: S&P 500 → Russell 2000 → Global equities (ASX, LSE, etc.)
- **Alternative Data**: Web traffic, Glassdoor reviews, supply chain signals
- **Real-Time Screening**: Intraday monitoring for sudden metric changes (earnings surprises)
- **Probabilistic Scoring**: Replace point scores with probability distributions (Bayesian)
- **Explainability**: LLM-generated explanations for why each candidate was selected/rejected

---

## References

### Design Decisions

- **DD-011**: Checkpoint-based execution for failure recovery
- **DD-022**: Macro Analyst agent and sector favorability integration
- **DD-027**: Event-driven memory sync priorities
- **DD-032**: Hybrid data sourcing (Yahoo Finance vs SEC EDGAR)

### Related Documentation

- [System Overview](01-system-overview.md): 5-layer architecture, 14 agent types
- [Specialist Agents](03-agents-specialist.md): Overview of 6 specialist agents (including Screener)
- [Analysis Pipeline](../operations/01-analysis-pipeline.md): 12-day workflow, human gates
- [Human Integration](../operations/02-human-integration.md): Gate 1 specifications
- [Memory Architecture](04-memory-learning.md): 3-tier memory system (L1/L2/L3)
- [Feedback Loops](../learning/02-feedback-loops.md): Cross-agent learning propagation

### Implementation Roadmap

- [Roadmap](../implementation/01-roadmap.md): Phase 1-4 milestones, success criteria

---

**Document Status**: ✅ Complete
**Next Steps**: Review with team, validate Phase 1 scope, prioritize implementation tasks
