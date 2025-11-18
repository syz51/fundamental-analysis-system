# Workflow Pause/Resume Infrastructure

**Status**: Approved
**Date**: 2025-11-18
**Decider(s)**: System Architect
**Related Docs**: [Analysis Pipeline](../operations/01-analysis-pipeline.md), [Agents Coordination](../architecture/05-agents-coordination.md), [Memory System](../architecture/02-memory-system.md)
**Related Decisions**: [DD-011 Agent Checkpoint System](DD-011_AGENT_CHECKPOINT_SYSTEM.md), [DD-002 Event-Driven Memory Sync](DD-002_EVENT_DRIVEN_MEMORY_SYNC.md), [DD-015 Agent Failure Alert System](DD-015_AGENT_FAILURE_ALERT_SYSTEM.md)

---

## Context

Agent failures require graceful degradation without blocking parallel analyses. System currently lacks infrastructure to pause/resume stock analyses mid-pipeline when failures occur.

**Current State**:

- All-or-nothing execution (entire system halts or continues with corrupt data)
- No per-stock pause capability
- No dependency-aware resume logic
- Hard-stop policy (Flaw #19) cannot be implemented without pause/resume

**Why Address Now**:

- Blocks 4 dependent flaws:
  - #19: Partial failures handling
  - #24: Agent failure alerts
  - #25: Working memory durability during pause
  - #26: Multi-stock batch operations
- Phase 2 production readiness requires failure isolation
- Builds on DD-011 checkpoint system (prerequisite complete)

**Example Impact**: AAPL Strategy Analyst fails on Day 5 due to Koyfin quota. Current behavior: either halt all 4 concurrent analyses or continue AAPL incomplete (data integrity risk). Desired: pause AAPL only, continue MSFT/GOOGL/AMZN unaffected.

**Bidirectional Dependency with DD-015**: Pause/resume infrastructure requires alert system for human notification. PauseManager calls AlertManager on pause triggers. Alert system (DD-015) integrates with pause events (pause initiated, reminders Day 3/7, auto-resume notifications). Both systems implemented together in Phase 2.

---

## Decision

**Implement 3-component architecture for workflow pause/resume: PauseManager (state orchestration), DependencyResolver (resume planning), BatchManager (concurrent operations).**

System provides:

- Per-stock pause/resume without affecting parallel analyses
- 3-tier failure classification (retry/pause/fail)
- Dependency-aware resume plans (skip completed, restart failed+dependents)
- 14-day timeout with tiered escalation (3/7/14/30-day alerts)
- Tech-agnostic orchestrator integration
- Batch operations for shared failures (e.g., quota exhaustion affecting multiple stocks)

---

## Options Considered

### Option 1: 3-Component Architecture (CHOSEN)

**Description**: Separate concerns into PauseManager (orchestration), DependencyResolver (planning), BatchManager (concurrency).

**Pros**:

- Clear separation of concerns (orchestration vs planning vs batching)
- DependencyResolver reusable for both single and batch resumes
- PauseManager handles all state transitions and alerts
- Tech-agnostic design allows orchestrator flexibility
- Scales to batch operations naturally

**Cons**:

- 3 new components to implement and test
- More complex integration points
- Database overhead (3 new tables)

**Estimated Effort**: 4 weeks (Week 1: PauseManager+DB, Week 2: DependencyResolver, Week 3: BatchManager, Week 4: Testing)

---

### Option 2: Monolithic Pause Controller

**Description**: Single PauseController handles all pause/resume/batch operations.

**Pros**:

- Simpler to understand (one component)
- Fewer integration points
- Less inter-component coordination

**Cons**:

- God object anti-pattern (too many responsibilities)
- Harder to test (tightly coupled concerns)
- Difficult to extend for future use cases
- Dependency resolution logic buried in orchestration code

**Estimated Effort**: 3 weeks

---

### Option 3: Orchestrator-Native Pause/Resume

**Description**: Rely entirely on orchestrator's built-in pause/resume (e.g., Airflow DAG pause).

**Pros**:

- Minimal custom code
- Leverages existing orchestrator features
- Less maintenance burden

**Cons**:

- Locks into specific orchestrator (violates tech-agnostic principle)
- No dependency-aware resume logic (restart from beginning)
- No batch operations support
- No custom timeout policies
- Cannot extend L1 memory TTL during pause (Flaw #25)

**Estimated Effort**: 1 week

---

## Rationale

**Option 1 (3-component) chosen** because:

1. **Separation of concerns**: PauseManager orchestrates state, DependencyResolver plans execution, BatchManager coordinates concurrency. Each component testable independently.

2. **Tech-agnostic design**: Supports Airflow/Prefect/Temporal/custom orchestrators via adapter pattern. No vendor lock-in.

3. **Dependency-aware resume**: DependencyResolver analyzes agent DAG, generates executable plans (skip completed, restart failed+dependents). Prevents wasted re-execution.

4. **Batch efficiency**: BatchManager handles quota exhaustion scenarios (e.g., Koyfin rate limit affecting 10 stocks). Single operation resumes all vs. 10 sequential resumes.

5. **Extensibility**: Clean interfaces enable future enhancements (priority queues, resource-aware scheduling, auto-recovery when root cause resolved).

6. **Unblocks 4 flaws**: Architecture supports #19 (partial failures), #24 (alerts), #25 (memory durability), #26 (batching).

**Acceptable tradeoffs**:

- 3 components vs 1: complexity justified by extensibility and testability
- 4-week implementation: necessary for production-grade reliability
- Database overhead: 3 tables with retention policies prevent unbounded growth

---

## Consequences

### Positive Impacts

- ✅ **Per-stock failure isolation**: AAPL pause doesn't block MSFT/GOOGL
- ✅ **Unblocks 4 dependent flaws**: #19, #24, #25, #26 can proceed
- ✅ **Graceful degradation**: Production system continues despite failures
- ✅ **Resumable analyses**: No data loss, pick up where left off
- ✅ **Batch efficiency**: Parallel resume for quota/resource failures
- ✅ **Automated recovery**: Auto-resume when root cause resolved
- ✅ **Human oversight**: Escalation via alerts, manual override available

### Negative Impacts / Tradeoffs

- ❌ **Complexity**: 3 new components (PauseManager, DependencyResolver, BatchManager)
- ❌ **Database overhead**: 3 new tables, indexes, retention policies
- ❌ **Orchestrator dependency**: Must support pause/resume (limits choices)
- ❌ **Checkpoint dependency**: Requires DD-011 implementation first
- ❌ **Testing complexity**: State machine, concurrency, timeout edge cases
- ❌ **Memory overhead**: Extended L1 TTL during pauses (14d vs 24h)

**Mitigations**:

- Tech-agnostic design allows orchestrator flexibility
- Checkpoint system (DD-011) already approved and in progress
- Timeout policy prevents indefinite resource consumption
- Batch operations amortize overhead across multiple stocks

### Affected Components

**New Components**:

- `PauseManager` class (state orchestration, timeout escalation, alerts)
- `DependencyResolver` class (DAG analysis, resume plan generation)
- `BatchManager` class (concurrent pause/resume, resource checks)
- `paused_analyses` table (pause state tracking)
- `batch_pause_operations` table (batch coordination)
- `resume_plans` table (dependency-resolved execution plans)

**Modified Components**:

- `lead_coordinator.py`: Add pause/resume API integration
- `base_agent.py`: Trigger pause on Tier 2 failures
- `L1 cache`: Extend TTL from 24h → 14d during pause
- `AgentFailureAlertManager` (DD-015): Integrates with pause triggers, sends alerts on pause events

**Documentation Updates**:

- `01-analysis-pipeline.md`: Expand pause/resume workflow section
- `05-agents-coordination.md`: Add pause/resume components
- `02-tech-requirements.md`: Add database schema
- `01-roadmap.md`: Update Phase 2 implementation plan

---

## Implementation Notes

### Component 1: PauseManager

**Purpose**: Orchestrates pause/resume operations, manages state transitions

**API**:

```python
# Core operations
pause_analysis(
    stock_id: str,
    reason: str,
    checkpoint_id: UUID,
    trigger_source: Enum['AUTO_TIER2', 'MANUAL', 'GATE_TIMEOUT', 'GATE_REJECTION']
) -> PauseResult

resume_analysis(
    stock_id: str,
    resume_plan: ResumePlan,
    notify: bool = True
) -> ResumeResult

get_pause_state(stock_id: str) -> {
    status: Enum,
    reason: str,
    checkpoint_id: UUID,
    paused_at: Timestamp,
    resume_dependencies: Dict
}
```

**State Machine**:

```text
States:
  RUNNING     - Normal analysis execution
  PAUSING     - Saving checkpoint, coordinating agent shutdown
  PAUSED      - Idle, awaiting manual/auto resume
  RESUMING    - Loading checkpoint, restarting agents per plan
  STALE       - Paused >14 days, marked for expiration
  EXPIRED     - Purged from active tables (audit log only)

Transitions:
  RUNNING → PAUSING:      Tier 2 failure detected
  PAUSING → PAUSED:       Checkpoint saved, agents stopped
  PAUSED → RESUMING:      Resume triggered (manual or auto)
  RESUMING → RUNNING:     Checkpoint loaded, agents restarted
  PAUSED → STALE:         14 days elapsed without resume
  STALE → EXPIRED:        30 days elapsed, purged

Edge Cases:
  PAUSING → PAUSING:      Additional failures during pause (queue)
  RESUMING → PAUSING:     Failure during resume (re-pause)
  PAUSED → EXPIRED:       Manual expiration before 14 days
```

**Timeout Escalation**:

- **Day 0**: Pause occurs → Alert: "Stock {ticker} paused - {reason}"
- **Day 3**: Reminder → Alert: "{count} stocks paused for 3+ days, review needed"
- **Day 7**: Warning → Alert: "Approaching expiration: {count} stocks paused 7+ days"
- **Day 14**: Auto-expiration → Status: STALE, move to archive queue
- **Day 30**: Hard purge → Delete from active table (audit log retained)
- **Grace Period**: Human can extend up to 30 days total (max 1 extension)

### Component 2: DependencyResolver

**Purpose**: Analyzes agent dependency DAG, generates resume plans

**Algorithm**:

1. Load pipeline configuration, construct dependency DAG
2. Extract checkpoint state (completed agents)
3. Mark failed agent + downstream dependents for restart
4. Mark completed agents for skip
5. Mark parallel in-progress agents for wait/restart (check checkpoint)
6. Return `ResumePlan{restart: [], skip: [], wait: []}`

**Example**:

```text
Scenario: Financial Analyst fails on Day 4

State at pause:
  - Screening: COMPLETED
  - Business Research: COMPLETED
  - Financial Analyst: FAILED
  - Strategy Analyst: IN_PROGRESS (parallel with Financial)
  - News Monitor: IN_PROGRESS (parallel, independent)

Resume Plan:
  - Skip: [Screening, Business Research]
  - Restart: [Financial Analyst, Strategy Analyst, Valuation]
  - Continue: [News Monitor] (independent of failed agent)
```

### Component 3: BatchManager

**Purpose**: Coordinates concurrent pause/resume for multiple stocks

**Priority Queue**:

- Oldest pauses first (FIFO within priority)
- Gate-timeout pauses prioritized (higher urgency)
- Manual pauses lowest priority

**Concurrency Control**:

- Default: 5 parallel resumes (configurable)
- Resource checks before batch: API quota, compute capacity, DB connections

**Failure Isolation**:

- If >50% of batch fails on resume → pause entire batch
- If <50% fails → continue batch, re-pause failures

**API**:

```python
pause_batch(
    stock_ids: List[str],
    reason: str,
    max_concurrency: int = 5
) -> BatchPauseResult

resume_batch(
    stock_ids: List[str],
    concurrency_limit: int = 5
) -> BatchResumeResult

get_batch_status(batch_id: UUID) -> {
    total: int,
    paused: int,
    resumed: int,
    failed: int
}
```

### Failure Classification (3-Tier System)

**TIER 1: Auto-Retry (NO PAUSE)**

- Network timeouts (< 3 consecutive failures)
- Rate limit errors (HTTP 429) with exponential backoff
- Transient API unavailability (5xx with retry-after header)
- **Handling**: Retry with exponential backoff, max 3 attempts
- **Rationale**: High probability of self-resolution, low cost to retry

**TIER 2: Auto-Pause (IMMEDIATE PAUSE)**

- Agent crashes/unhandled exceptions
- Data quality failures (missing required SEC filings, corrupt data)
- Dependency failures (upstream agent failed, cannot proceed)
- Resource exhaustion (OOM, disk full)
- Persistent API failures (3+ consecutive timeouts on same endpoint)
- **Handling**: Auto-pause with alert, save checkpoint, await resolution
- **Rationale**: Requires investigation or external fix, resumable after resolution

**TIER 3: Auto-Fail (HARD STOP, NO PAUSE)**

- Data integrity violations (contradictory checkpoint data)
- Security violations (unauthorized access attempts)
- Configuration errors blocking entire pipeline
- Irrecoverable validation failures (ticker delisted, fundamentally flawed)
- **Handling**: Mark failed, notify human, remove from pipeline
- **Rationale**: Not fixable by pause/resume, requires redesign or stock removal

### Database Schema

#### Table 1: `paused_analyses`

```sql
CREATE TABLE paused_analyses (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    stock_id VARCHAR(10) NOT NULL,
    pause_reason TEXT NOT NULL,
    pause_trigger VARCHAR(20) NOT NULL
        CHECK (pause_trigger IN ('AUTO_TIER2', 'MANUAL', 'GATE_TIMEOUT', 'GATE_REJECTION')),
    pause_timestamp TIMESTAMP NOT NULL DEFAULT NOW(),
    resume_timestamp TIMESTAMP,
    checkpoint_id UUID NOT NULL,  -- FK to checkpoints.id (DD-011)
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

    FOREIGN KEY (checkpoint_id) REFERENCES checkpoints(id),
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

#### Table 2: `batch_pause_operations`

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

#### Table 3: `resume_plans`

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

### Retention Policies

| Table                    | Status           | Retention                  | Action                               |
| ------------------------ | ---------------- | -------------------------- | ------------------------------------ |
| `paused_analyses`        | PAUSED, RESUMING | Until resume or expiration | Active                               |
| `paused_analyses`        | RESUMED          | 30 days                    | Archive to `paused_analyses_history` |
| `paused_analyses`        | STALE            | 30 days from stale date    | Purge (keep audit log)               |
| `batch_pause_operations` | Any              | 90 days                    | Archive to cold storage              |
| `resume_plans`           | COMPLETED        | 30 days                    | Purge (linked paused_analyses kept)  |
| `resume_plans`           | FAILED           | 90 days                    | Keep for debugging                   |

### Human Gate Integration

**CANNOT Pause**:

- While gate is in `WAITING_FOR_HUMAN` state (already paused conceptually)
- During gate timeout countdown (human still has time)

**CAN Pause**:

- Before gate reached (agent execution phase)
- After gate completed (downstream agent execution)
- On gate timeout → auto-pause with reason "Gate {X} timeout"
- On gate rejection → conditional pause (soft rejection = pause, hard rejection = fail)

**Gate Timeout Example**:

```text
Gate 3 (Assumption Validation, 24h timeout)

Timeline:
  0-22h:  Normal gate wait, no pause allowed
  22-24h: Warning alerts, still no pause
  24h:    Timeout triggered
          → auto_pause(stock_id, reason="Gate 3 timeout, needs review")
          → Alert: "Gate 3 timeout for {ticker}, analysis paused"

Human action:
  - Reviews pause queue
  - Validates assumptions manually
  - Approves gate + triggers resume

Resume:
  - Loads checkpoint at Gate 3
  - Bypasses gate (already validated)
  - Continues to next agent
```

### Memory System Integration

**L1 Working Memory (24h → 14d during pause)**:

- Normal: Agent working memory TTL = 24h
- On pause: Extend L1 TTL to 14 days (matches pause timeout)
- On resume: Rehydrate L1 from checkpoint if expired
- On expire: L1 purged, resume from L2/L3 only

**L1 Persistence**: TTL extension (24h→14d) is part of broader L1 durability system including snapshot/restore and consistency verification. See [DD-016: L1 Memory Durability](DD-016_L1_MEMORY_DURABILITY.md) for complete L1 memory durability design.

**L2 Cache (30d, unaffected)**:

- Continues normal 30d retention during pause

**L3 Central Knowledge Graph (permanent, unaffected)**:

- Always available for resume

### Alert Integration

**Alert Types**:

1. **Pause Initiated**: Trigger: Tier 2 failure → auto-pause. Message: "Stock {ticker} paused - Agent {agent_name} failed: {reason}". Priority: HIGH

2. **Pause Reminder (Day 3)**: Message: "{count} stocks paused for 3+ days, review needed: {tickers}". Priority: MEDIUM

3. **Pause Warning (Day 7)**: Message: "Approaching expiration: {count} stocks paused 7+ days: {tickers}". Priority: HIGH

4. **Auto-Resume Success**: Message: "Stock {ticker} auto-resumed - {reason} resolved, analysis continuing". Priority: NORMAL

5. **Auto-Resume Failure**: Message: "Stock {ticker} auto-resume failed - {error}, re-paused for manual review". Priority: CRITICAL

6. **Batch Resume Complete**: Message: "Batch '{batch_name}' resumed: {success_count}/{total_count} successful". Priority: NORMAL

**Auto-Resume Policy**:

- **Enabled**: Yes, with alerts
- **Conditions**: Root cause resolved (e.g., API restored, quota reset)
- **Attempt Limit**: 3 auto-resume attempts, then manual intervention required
- **Notification**: Always alert on auto-resume (success or failure)

### Orchestrator Integration (Tech-Agnostic)

**Generic Orchestrator API**:

```python
class OrchestoratorAdapter:
    def pause_workflow(self, workflow_id: str) -> bool
    def resume_workflow(self, workflow_id: str) -> bool
    def get_workflow_state(self, workflow_id: str) -> WorkflowState
```

**Pause Sequence**:

1. Tier 2 failure detected by agent
2. PauseManager.pause_analysis() called
3. Checkpoint saved via DD-011 (blocks until complete)
4. OrchestoratorAdapter.pause_workflow() called
5. Orchestrator stops scheduling new tasks for workflow
6. Status: PAUSED, awaiting resume

**Resume Sequence**:

1. Resume triggered (manual or auto)
2. DependencyResolver.create_resume_plan() generates plan
3. Checkpoint loaded via DD-011
4. OrchestoratorAdapter.resume_workflow() called
5. Orchestrator schedules tasks per resume plan
6. Status: RESUMING → RUNNING

**Estimated Implementation Effort**: 4 weeks

- Week 1: PauseManager component, database tables, state machine
- Week 2: DependencyResolver component, resume plan generation
- Week 3: BatchManager component, orchestrator adapter
- Week 4: Integration (checkpoint, alerts, memory), testing

**Dependencies**:

- DD-011 checkpoint system (prerequisite - implemented)
- PostgreSQL infrastructure (exists)
- Redis infrastructure (exists)
- DD-015 alert system (approved - implements Flaw #24)
- Orchestrator selection (Airflow/Prefect/Temporal/custom)

### Testing Requirements

- **State machine transitions**: Verify all valid transitions, reject invalid
- **Dependency resolution**: Complex DAG scenarios, parallel agents, cascading failures
- **Batch concurrency**: Respect limits, queue management, failure isolation
- **Timeout escalation**: Alerts triggered at correct intervals, no duplicates
- **Auto-resume**: Root cause detection, retry limits, re-pause on failure
- **Edge cases**: Pause-during-pause, resume-during-pause, missing checkpoint, gate timeout

### Rollback Strategy

If pause/resume system has critical bugs:

1. Disable auto-pause (agents fail without pause, restart from beginning)
2. Fallback to current behavior (all-or-nothing execution)
3. Fix bug, re-enable pause/resume
4. No data loss: system degrades gracefully to pre-pause behavior

---

## Open Questions

**Resolved** (from design discussions):

1. ✅ Auto-pause triggers: 3-tier classification (retry/pause/fail)
2. ✅ Pause timeout: 14-day expiration with 3/7-day alerts
3. ✅ Human gate pause: No during active wait, yes on timeout/rejection
4. ✅ Batch concurrency: 5 parallel resumes (configurable)
5. ✅ Tech stack: Design tech-agnostic for orchestrator flexibility
6. ✅ Resume notifications: Auto-resume with alerts

**Pending**: None - design is complete, ready for implementation in Phase 2

**Blocking**: No

---

## References

- [Flaw #23: Workflow Pause/Resume Infrastructure](../design-flaws/resolved/23-workflow-pause-resume.md) - resolved by DD-012
- [Flaw #19: Partial Failures](../design-flaws/active/19-partial-failures.md) - enabled by pause/resume
- [DD-015: Agent Failure Alert System](DD-015_AGENT_FAILURE_ALERT_SYSTEM.md) - integrates with pause alerts, resolves Flaw #24
- [Flaw #25: Working Memory Durability](../design-flaws/resolved/25-working-memory-durability.md) - extends L1 TTL during pause
- [DD-016: L1 Memory Durability](DD-016_L1_MEMORY_DURABILITY.md) - implements L1 snapshot/restore on pause/resume
- [Flaw #26: Multi-Stock Batching](../design-flaws/resolved/26-multi-stock-batching.md) - uses BatchManager
- [DD-011: Agent Checkpoint System](DD-011_AGENT_CHECKPOINT_SYSTEM.md) - prerequisite for pause/resume

---

## Status History

| Date       | Status   | Notes                                          |
| ---------- | -------- | ---------------------------------------------- |
| 2025-11-18 | Approved | Design finalized, resolves Flaw #23 (B1/B2/B3) |

---

## Notes

Pause/resume infrastructure is critical for production-grade reliability. Without it, system cannot:

- Handle external API failures gracefully (Koyfin, SEC EDGAR quota limits)
- Isolate per-stock failures (AAPL failure blocks MSFT/GOOGL)
- Provide human oversight during complex failures
- Resume long-running analyses without data loss

Priority: High - blocks Phase 2 production readiness and 4 dependent flaws.
