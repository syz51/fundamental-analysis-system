# Analysis Pipeline - Memory-Enhanced Workflow

## Overview

This document describes the core 12-day analysis cycle that powers the fundamental analysis system. The pipeline leverages institutional memory at every stage, enabling each analysis to build upon past learnings and continuously improve accuracy.

The workflow is organized into 5 major phases, each incorporating historical context and pattern recognition to enhance decision quality. Human oversight gates are strategically positioned to guide the system while capturing valuable expertise for future analyses.

---

## Memory-Enhanced Workflow

### Phase 1: Memory-Informed Discovery (Days 1-2)

```mermaid
graph LR
    A[Market Scan] --> B[Check Knowledge Base]
    B --> C[Known Company?]
    C -->|Yes| D[Load Historical Context]
    C -->|No| E[Standard Screening]
    D --> F[Screening Agent with Context]
    E --> F
    F --> G[Human Review with History]
    G --> H[Candidate Pipeline]
```

**Memory Activities**:

1. Query: "Have we analyzed this company before?"
2. Load: Previous recommendations, outcomes, lessons
3. Pattern match: "Similar companies that succeeded/failed"
4. Present: Historical context to human reviewer

**Core Activities**:

1. Run quantitative screens
2. Generate candidate list
3. Create initial summaries
4. Human validation of candidates

### Phase 2: Parallel Analysis with Historical Context (Days 3-7)

```mermaid
graph TB
    A[Candidate Stock] --> B[Business Research]
    A --> C[Financial Analysis]
    A --> D[Strategy Review]
    A --> E[News Monitoring]
    B --> F[Integration Point]
    C --> F
    D --> F
    E --> F
```

**Parallel Workstreams**:

- Business model deep dive
- Financial statement analysis
- Management evaluation
- Current events tracking

**Memory Integration**:

Each specialist agent begins by loading relevant memories. The system retrieves:

- **Company history**: Previous analyses, recommendations, and outcomes
- **Sector patterns**: Industry-specific trends and success rates
- **Peer outcomes**: Performance of comparable companies
- **Macro context**: Market regime patterns and their impact
- **Agent expertise**: Historical accuracy of specific agents in similar contexts

This contextual loading ensures analysts don't start from scratch but build upon institutional knowledge accumulated over time.

### Phase 3: Memory-Powered Debate & Synthesis (Days 8-9)

```mermaid
graph TB
    A[Agent Findings] --> B[Load Debate History]
    B --> C[Similar Past Debates]
    C --> D[Structured Challenge with Precedents]
    D --> E[Evidence + Historical Support]
    E --> F[Facilitator Weighs by Track Record]
    F --> G{Credibility Gap >Threshold?}
    G -->|Yes| H[Auto-Resolve to Higher Credibility]
    G -->|No| I[Human Arbitration with Context]
    I --> J{Human Response?}
    J -->|Within 6hr| K[Binding Resolution]
    J -->|Timeout| L[Conservative Default - Provisional]
    H --> M[Consensus with Confidence Score]
    K --> M
    L --> N[Pipeline Continues - Non-Blocking]
    N --> O[Review at Next Gate]
```

**Debate Protocol (Non-Blocking with Fallbacks)**:

1. Each agent presents findings
2. Structured challenges issued (15min ack, 1hr evidence)
3. **Facilitator applies credibility-weighted auto-resolution if gap >threshold** (dynamic: max(0.25, CI_A + CI_B))
4. If unresolved, escalate to human (6hr timeout)
5. **If human unavailable, apply conservative default (provisional)**
6. **Pipeline continues with provisional resolution**
7. **Human reviews provisional decisions at next gate**

**Async Resolution Pathway**:

The system ensures debates never block pipeline progress:

**_Path A: Direct Resolution (No Human Needed)_**

- Agent consensus reached → Continue immediately
- Credibility gap >threshold (dynamic: max(0.25, CI_A + CI_B)) → Facilitator auto-resolves → Continue immediately

**_Path B: Human Resolution (Standard)_**

- Human arbitrates within 6 hours → Binding resolution → Continue

**_Path C: Provisional Resolution (Fallback)_**

- Human timeout after 6 hours → Conservative default applied → **Pipeline continues**
- Resolution marked "provisional - awaiting review"
- Override window opens until next gate
- Downstream analyses proceed with conservative assumption

**Provisional Resolution Handling**:

When conservative default is applied:

1. **Most Cautious Position Selected**:

   - Compare agent positions on risk spectrum
   - Select lowest price target, highest risk assessment, most conservative assumptions

2. **Downstream Continuation**:

   - Valuation agent receives provisional assumption
   - Proceeds with DCF modeling using conservative inputs
   - Final recommendation reflects conservative stance

3. **Gate Review Integration**:

   - At Gate 3 (Valuation) or Gate 5 (Final Decision):
     - Display: "2 provisional decisions require review"
     - Show conservative position applied vs alternative positions
     - Enable override with downstream impact analysis
   - If overridden:
     - Re-run affected valuations (typically 5-10min)
     - Update target prices and recommendations
     - Propagate changes through dependency chain

4. **Learning Capture**:
   - Track fallback accuracy (human override rate)
   - Learn which types of debates benefit from conservative defaults
   - Improve credibility scoring over time

**Memory Enhancement**:

The debate facilitator enhances discussions by:

- Pre-loading relevant precedents for all participants
- Retrieving historical debate outcomes on similar topics
- Weighting agent positions by historical accuracy
- Finding counter-examples from past analyses
- Checking pattern success rates to validate claims
- Resolving conflicts using historical outcomes
- **Tracking fallback resolution accuracy for calibration**
- **Learning conservative default effectiveness by debate type**

When agents disagree, the system can surface which position proved correct in similar past situations, enabling data-driven conflict resolution while still allowing human judgment to override when context differs. **If human unavailable, conservative defaults ensure pipeline progress while maintaining safety through provisional status and mandatory review.**

### Phase 4: Calibrated Valuation (Days 10-11)

```mermaid
graph LR
    A[Consensus Data] --> B[Valuation Models]
    B --> C[Sensitivity Analysis]
    C --> D[Human Gate 3: Assumptions]
    D --> E[Price Targets]
```

**Valuation Process**:

1. Build financial models
2. Run multiple scenarios
3. Human validates assumptions
4. Generate target ranges

**Memory Calibration**:

Valuation models are calibrated using historical performance:

- **Model accuracy tracking**: Sector-specific historical errors
- **Assumption adjustment**: Calibrate inputs based on past prediction errors
- **Scenario weighting**: Apply historical probabilities to bull/base/bear cases
- **Confidence scoring**: Calculate based on track record in similar situations

For example, if the valuation agent has historically overestimated tech company growth by 8%, the system automatically adjusts current projections downward and widens confidence intervals appropriately.

### Phase 5: Documentation & Watchlist (Day 12)

```mermaid
graph LR
    A[Complete Analysis] --> B[Report Generation]
    B --> C[Human Gate 4: Review]
    C --> D[Final Report]
    D --> E[Watchlist Entry]
```

**Documentation Activities**:

1. Synthesize all findings
2. Generate investment memo
3. Human reviews final report
4. Add to watchlist with alerts
5. Store analysis in knowledge base

**Memory Storage**:

All analysis outputs are stored in the knowledge base for future reference:

- Investment memos with full reasoning chains
- Agent consensus and dissent
- Human overrides and rationale
- Price targets and assumptions
- Risk factors identified
- Patterns matched during analysis

This creates a complete audit trail while building the institutional memory that future analyses will leverage.

---

## Pipeline Integration Points

### Data Collection Integration

Throughout all phases, the Data Collector Agent continuously:

- Monitors for new filings and disclosures
- Updates market data and price information
- Tracks news and material events
- Validates data quality and freshness

### News Monitor Integration

The News Monitor Agent runs in parallel across all phases:

- Alerts to material events requiring immediate attention
- Provides context for price movements
- Tracks competitor announcements
- Identifies regulatory developments
- Triggers re-analysis when thesis-changing events occur

### Quality Control Integration

The QC Agent validates work at each phase:

- Cross-verifies findings across agents
- Identifies contradictions requiring resolution
- Ensures checklist completion
- Validates data sources and calculations
- Flags inconsistencies for human review

---

## Failure Recovery & Pause/Resume

The pipeline supports graceful failure recovery and workflow pause/resume using checkpoint-based state persistence ([DD-011](../design-decisions/DD-011_AGENT_CHECKPOINT_SYSTEM.md), [DD-012](../design-decisions/DD-012_WORKFLOW_PAUSE_RESUME.md)).

### Checkpoint-Based Recovery

**How It Works**:

Each specialist agent saves execution state after completing each subtask:

- Subtask progress (completed/pending)
- Working memory snapshot (L1 cache dump)
- Intermediate results (partial findings)
- Execution context (config, retry count)

**Storage**: Dual-tier for reliability and speed

- PostgreSQL (durable, permanent record)
- Redis (fast recovery, 7-day TTL)

### Failure Classification (3-Tier System)

The system classifies failures into 3 tiers with different handling strategies:

| Tier | Failure Type | Examples | Action | Rationale |
|------|-------------|----------|--------|-----------|
| 1 | Transient | Network timeout (<3x), rate limits (429), 5xx | Auto-retry | Self-resolving |
| 2 | Recoverable | Agent crash, data quality, persistent API failure | Auto-pause | Needs investigation |
| 3 | Irrecoverable | Data integrity violation, security breach, delisted ticker | Auto-fail | Not fixable |

**Tier 1 (Auto-Retry)**:
- Network timeouts (< 3 consecutive failures)
- Rate limit errors (HTTP 429) with exponential backoff
- Transient API unavailability (5xx with retry-after header)
- **Handling**: Retry with exponential backoff, max 3 attempts
- **Rationale**: High probability of self-resolution, low cost to retry

**Tier 2 (Auto-Pause)**:
- Agent crashes/unhandled exceptions
- Data quality failures (missing required SEC filings, corrupt data)
- Dependency failures (upstream agent failed, cannot proceed)
- Resource exhaustion (OOM, disk full)
- Persistent API failures (3+ consecutive timeouts on same endpoint)
- **Handling**: Auto-pause with alert, save checkpoint, await resolution
- **Rationale**: Requires investigation or external fix, resumable after resolution

**Tier 3 (Auto-Fail)**:
- Data integrity violations (contradictory checkpoint data)
- Security violations (unauthorized access attempts)
- Configuration errors blocking entire pipeline
- Irrecoverable validation failures (ticker delisted, fundamentally flawed)
- **Handling**: Mark failed, notify human, remove from pipeline
- **Rationale**: Not fixable by pause/resume, requires redesign or stock removal

### Failure Recovery Workflow

```mermaid
graph TB
    A[Agent Failure Detected] --> B{Checkpoint Exists?}
    B -->|Yes| C[Restore from Checkpoint]
    B -->|No| D[Restart from Beginning]
    C --> E[Resume from Next Subtask]
    E --> F[Continue Pipeline]
    D --> F
```

**Recovery Process**:

1. **Failure Detection**: Lead Coordinator detects agent failure (API rate limit, network error, resource exhaustion)
2. **Checkpoint Lookup**: Query checkpoint storage for most recent state
3. **State Restoration**:
   - Fast path: Restore from Redis (<5s)
   - Fallback: Restore from PostgreSQL (<30s)
4. **Resume Execution**: Agent continues from next pending subtask
5. **Zero Duplicate Work**: Completed subtasks never re-executed

**Example Recovery**:

```text
Strategy Analyst - AAPL Analysis:
  ✅ historical_roi (completed - 10 min)
  ✅ ma_review (completed - 25 min)
  ❌ mgmt_compensation (failed at 45% - Koyfin rate limit)

[Recovery triggered]
  ↳ Checkpoint restored from Redis in 3s
  ↳ Resumed at mgmt_compensation subtask
  ↳ No re-work of historical_roi or ma_review
  ↳ Total recovery overhead: 3s vs 35 min restart
```

### Workflow Pause/Resume (DD-012)

The system supports per-stock pause/resume without affecting parallel analyses. When an analysis is paused, other stocks continue unaffected.

**Use Cases**:

- Tier 2 failures (auto-pause with alert)
- Human investigation needed (provisional decision review)
- Resource constraints (prioritize different analysis)
- External dependency (awaiting data provider response)
- Gate timeouts (24h human response limit exceeded)

**State Machine**:

```
                  Tier 2 Failure
    ┌─────────────────┐
    │                 │
    ▼                 │
RUNNING ──────► PAUSING ──────► PAUSED
                                  │
                                  │ Resume Triggered
                                  │
                                  ▼
                              RESUMING ──────► RUNNING
                                  │
                                  │ 14 days
                                  ▼
                               STALE ──────► EXPIRED (30d)
```

**States**:
- **RUNNING**: Normal analysis execution
- **PAUSING**: Saving checkpoint, coordinating agent shutdown
- **PAUSED**: Idle, awaiting manual/auto resume
- **RESUMING**: Loading checkpoint, restarting agents per plan
- **STALE**: Paused >14 days, marked for expiration
- **EXPIRED**: Purged from active tables (audit log only)

**Pause Workflow**:

1. Tier 2 failure detected (or manual trigger)
2. PauseManager saves checkpoint via DD-011
3. Analysis marked "PAUSED" with reason and timestamp
4. Alert sent to human (priority based on trigger)
5. Resources released (agents can work on other stocks)
6. L1 memory TTL extended from 24h → 14d

**Resume Workflow**:

1. Resume triggered (manual or auto when blocker resolved)
2. DependencyResolver creates resume plan:
   - **Skip**: Agents completed before pause (findings in Neo4j)
   - **Restart**: Failed agent + downstream dependents
   - **Continue**: Independent parallel agents (if checkpoint exists)
3. Checkpoint loaded via DD-011
4. **L1 working memory restored via DD-016**:
   - DualRecoveryStrategy attempts 3-tier fallback (L1 existing → Redis secondary → PostgreSQL)
   - Type preservation ensures all Redis types (string, list, hash, set, zset) restored correctly
   - ConsistencyVerifier runs SHA256 hash validation (fail-fast on mismatch)
   - TTL restored to 24h for active analysis
   - Zero duplicate work: agents continue from exact memory state
5. Agents resume per plan
6. Pipeline continues from pause point

**Dependency Resolution Example**:

```
Scenario: Financial Analyst fails on Day 4 of 12-day pipeline

State at Pause:
- Screening Agent: COMPLETED (Day 1-2)
- Business Research Agent: COMPLETED (Day 3-4)
- Financial Analyst: FAILED (Day 4)
- Strategy Analyst: IN_PROGRESS (Day 4, parallel)
- News Monitor: IN_PROGRESS (Day 1-12, independent)

Resume Plan Generated:
- Skip: Screening, Business Research (already completed)
- Restart: Financial Analyst (failed), Strategy Analyst (dependent), Valuation Agent (dependent)
- Continue: News Monitor (independent, no dependency on failed agent)

Result: Resume saves 2 days by skipping completed work, restarts 3 agents
```

**Batch Pause Scenario**:

```
Scenario: Koyfin API quota exhausted (10,000 requests/day)

Day 0, 2pm: Quota reached after 8 stock analyses
- 10 remaining stocks in batch encounter quota errors
- Batch pause triggered: pause_batch(stock_ids=[...], reason="Koyfin quota exceeded")
- All 10 stocks status: PAUSED
- Alert sent: "10 stocks paused - Koyfin quota exhausted, resumes at midnight"

Day 1, 12:01am: Quota reset detected
- Auto-resume triggered: resume_batch(stock_ids=[...], concurrency_limit=5)
- First 5 stocks resume concurrently
- After completion, next 5 stocks resume
- Alert sent: "Batch 'koyfin_quota_batch' resumed: 10/10 successful"

Efficiency: Single batch operation vs 10 individual pause/resume cycles
```

**Timeout Escalation Timeline**:

```
Pause Timeout Lifecycle:

Day 0:  Pause occurs → Alert: "Stock AAPL paused - Financial Analyst failed: data quality issue"
Day 3:  Reminder → Alert: "3 stocks paused for 3+ days, review needed"
Day 7:  Warning → Alert: "Approaching expiration: 2 stocks paused 7+ days"
Day 14: Expiration → Status: STALE, moved to archive queue
Day 30: Purge → Deleted from active tables (audit log retained)

Grace Period: Human can extend to 30 days max with justification
```

**Integration with Human Gates**:

Pause/resume particularly useful for:

- **Gate 3** (Assumption Validation): Auto-pause on 24h timeout
- **Gate 4** (Debate Arbitration): Pause if human needs expert consultation
- **Gate 5** (Final Decision): Pause for investment committee scheduling

**Gate Timeout Example**:

```
Scenario: Gate 3 (Assumption Validation) times out after 24h

Timeline:
- Day 7, 9am: Valuation Agent reaches Gate 3, awaits human approval
- Day 7, 9am-Day 8, 7am: Gate in WAITING_FOR_HUMAN state (22h elapsed)
- Day 8, 7am-9am: Warning alerts sent, human not responsive (24h elapsed)
- Day 8, 9am: Gate times out
  - Action: Auto-pause analysis with reason "Gate 3 timeout, needs review"
  - Checkpoint saved at Gate 3 entry
  - Alert: "Gate 3 timeout for AAPL, analysis paused"

Human Review:
- Portfolio manager reviews pause queue
- Sees "Gate 3 timeout" reason, reviews valuation assumptions
- Validates assumptions manually, approves gate
- Triggers resume: resume_analysis('AAPL', resume_plan, notify=True)

Resume:
- Checkpoint loaded at Gate 3 entry
- Gate bypassed (already validated by human)
- Valuation Agent continues to next step
- Alert: "AAPL resumed - Gate 3 validated, analysis continuing"
```

**Checkpoint Integration (DD-011)**:

- Pause triggers checkpoint save before state transition
- Checkpoint includes: agent states, intermediate results, memory snapshots
- Resume loads checkpoint and rehydrates agent state
- If checkpoint corrupted → Tier 3 failure (auto-fail, no resume)

**Orchestrator Integration (Tech-Agnostic)**:

```python
# Pause flow
def handle_tier2_failure(stock_id, agent, reason):
    checkpoint_id = checkpoint_system.save(stock_id)  # DD-011
    pause_manager.pause_analysis(stock_id, reason, checkpoint_id)
    orchestrator.pause_workflow(f"stock_{stock_id}")  # Generic API

# Resume flow
def handle_resume(stock_id):
    resume_plan = dependency_resolver.create_resume_plan(stock_id)
    checkpoint_system.load(stock_id, resume_plan.checkpoint_id)
    orchestrator.resume_workflow(f"stock_{stock_id}")
    pause_manager.resume_analysis(stock_id, resume_plan, notify=True)
```

Supports: Airflow (DAG pause), Prefect (flow pause), Temporal (signal), Custom

### Checkpoint Retention

**Cleanup Policy**:

- **Success**: Delete checkpoints immediately after analysis completes
- **Failure**: Retain for 30 days (audit trail, debugging)
- **Manual Override**: Flag to preserve for investigation

**Storage Impact**: ~5 KB per checkpoint × 5 checkpoints/agent × 5 agents = ~125 KB per stock

---

## Timeline Management

### Standard 12-Day Cycle

| Phase | Days  | Activities                      | Gates          | Fallback Handling                                   |
| ----- | ----- | ------------------------------- | -------------- | --------------------------------------------------- |
| 1     | 1-2   | Screening & validation          | Gate 1         | Auto-proceed with top 10 (24hr)                     |
| 2     | 3-7   | Parallel specialist analysis    | Gate 2 (Day 3) | Standard checklist (12hr)                           |
| 3     | 8-9   | Debate & synthesis              | Gate 4         | **Conservative default (6hr), review at next gate** |
| 4     | 10-11 | Valuation modeling              | Gate 3         | Conservative estimates (24hr)                       |
| 5     | 12    | Documentation & watchlist setup | Gate 5         | Blocking (no auto-action)                           |

**Key Change**: Phase 3 debates are now **non-blocking**. If human unavailable, conservative defaults applied provisionally and pipeline continues. Provisional decisions reviewed at Gates 3 or 5.

### Accelerated Cycle (6 Days)

For time-sensitive opportunities:

- Days 1-2: Screening & validation
- Days 3-4: Parallel analysis (compressed)
- Day 5: Debate & valuation (combined)
- Day 6: Documentation

Requires:

- Higher human engagement
- More aggressive parallelization
- Reduced validation cycles

### Continuous Monitoring

For existing watchlist positions:

- Weekly: Price and news monitoring
- Monthly: Thesis validation check
- Quarterly: Full re-analysis
- Event-driven: Immediate review on material events

---

## Success Metrics

### Pipeline Performance

- **Throughput**: Number of stocks analyzed per month
- **Cycle time**: Days from screening to final decision
- **Accuracy**: Percentage of recommendations achieving targets
- **Efficiency**: Agent utilization and parallel processing effectiveness

### Memory Utilization

- **Context retrieval**: Percentage of analyses using historical data
- **Pattern application**: Frequency of pattern matching in decisions
- **Calibration impact**: Improvement from historical error correction
- **Learning rate**: Accuracy improvement over time

### Human Engagement

- **Gate response time**: Average time to human decision at gates
- **Override rate**: Frequency of human overrides to AI recommendations
- **Feedback quality**: Value of human insights captured
- **Time savings**: Hours saved through automation

---

## Related Documentation

### Core Documentation

- [System Design v2.0](../../multi_agent_fundamental_analysis_v2.0.md) - Complete system specification
- [Agent Architecture](../architecture/agents.md) - Detailed agent specifications
- [Memory Architecture](../architecture/memory.md) - Memory system design

### Operations Documentation

- [Human Integration](./02-human-integration.md) - Human decision gates and interfaces
- [Data Management](./03-data-management.md) - Data sources and storage
- [Learning Systems](./learning-systems.md) - Continuous improvement mechanisms

### Implementation Guides

- [Pipeline Deployment](../implementation/pipeline-deployment.md) - Setup and configuration
- [Monitoring & Alerts](../implementation/monitoring.md) - Observability setup
- [Performance Tuning](../implementation/performance-tuning.md) - Optimization guides
