# Agent Checkpoint System

**Status**: Approved
**Date**: 2025-11-18
**Decider(s)**: System Architect
**Related Docs**: [Memory System](../architecture/02-memory-system.md), [Specialist Agents](../architecture/03-agents-specialist.md), [Analysis Pipeline](../operations/01-analysis-pipeline.md)
**Related Decisions**: [DD-002 Event-Driven Memory Sync](DD-002_EVENT_DRIVEN_MEMORY_SYNC.md), [DD-005 Memory Scalability](DD-005_MEMORY_SCALABILITY_OPTIMIZATION.md)

---

## Context

System lacks mechanism to save agent execution state during analysis, preventing resumption after failures. When agents fail mid-task (API rate limits, network issues, resource constraints), they restart from scratch, wasting completed work and re-hitting external API limits.

**Current State**:

- Task-level monitoring only (complete/failed/in-progress)
- No record of subtask progress, intermediate results, or working memory state
- Failed agents always restart from beginning

**Why Address Now**:

- Blocks failure recovery (Flaw #19: hard stop policy requires checkpoint-based resumption)
- Blocks workflow pause/resume (Flaw #23)
- Blocks working memory durability for overnight pauses (Flaw #25)
- Phase 2 implementation requires reliable agent execution for production

**Example Impact**: Strategy Analyst analyzing AAPL completes 10Y ROI calculation (15 min), reaches 45% through M&A review when Koyfin API rate limit hit. Current behavior: restart wastes completed ROI work, may hit limit again before reaching prior progress.

---

## Decision

**Implement checkpoint system saving agent execution state at subtask boundaries, stored durably in PostgreSQL with Redis backup for fast recovery.**

System saves checkpoint after each subtask completes, recording:

- Progress tracking (current/completed/pending subtasks, percentage)
- Working memory snapshot (L1 cache dump)
- Intermediate results (partial findings not yet persisted to Neo4j)
- Execution context (config, retry count, agent version)
- Failure details (if checkpoint triggered by error)

On failure, Lead Coordinator restores agent from last checkpoint, resuming from next pending subtask without repeating completed work.

---

## Options Considered

### Option 1: Per-Subtask Checkpoints (CHOSEN)

**Description**: Save checkpoint after every subtask completion. Subtasks defined at natural work boundaries (e.g., "10-K parsing", "ratio calculation", "peer comparison").

**Pros**:

- Granular recovery (lose at most 1 subtask of work)
- Clear checkpoint boundaries (deliverable per subtask)
- Easy progress tracking (count completed subtasks)
- Aligns with atomic work units

**Cons**:

- More checkpoint writes (4-5 per agent vs 1-2 for milestones)
- Storage overhead (more checkpoint records)
- Requires subtask structure definition for all 13 agents

---

### Option 2: Milestone-Based Checkpoints

**Description**: Save checkpoints only at major milestones (e.g., after entire "financial statement analysis" phase, not individual subtasks).

**Pros**:

- Fewer checkpoint writes (1-2 per agent)
- Lower storage overhead
- Less subtask granularity needed

**Cons**:

- Coarse recovery (lose 30-60 min of work on failure)
- Doesn't prevent API rate limit re-hitting
- Poor progress visibility (binary "done/not done" per phase)
- Insufficient for user experience (long re-work delays)

---

### Option 3: Time-Based Checkpoints

**Description**: Save checkpoints at fixed intervals (e.g., every 5 minutes) regardless of subtask state.

**Pros**:

- Simple trigger logic
- Works for any agent without subtask structure

**Cons**:

- May checkpoint mid-subtask (incomplete deliverables, complex restore)
- Progress tracking unclear (percentage only, no semantic meaning)
- Doesn't align with natural work boundaries
- Hard to verify checkpoint validity

---

## Rationale

**Option 1 (per-subtask) chosen** because:

1. **Aligns with work units**: Agents already structured around deliverables (financial statements, ratios, findings). Subtask boundaries = completion of storable artifact.

2. **Minimal waste on failure**: Even 15-min subtask loss acceptable vs 30-60 min milestone loss. Critical for expensive API calls (Koyfin, Bloomberg charge per request).

3. **Progress visibility**: User sees "3 of 5 subtasks complete" vs opaque percentage. Supports human decision-making at gates.

4. **Validates deliverables**: Checkpoint only when subtask produces complete, storable output. Ensures restore always starts from valid state.

5. **Unblocks dependencies**: Flaw #19 (partial failures) explicitly requires subtask-level recovery. Flaw #23 (pause/resume) needs subtask granularity for workflow control.

**Acceptable tradeoffs**:

- 4-5 checkpoint writes per agent (vs 1-2 for milestones): negligible given PostgreSQL write performance
- Upfront effort defining subtasks for 13 agents: one-time cost, high long-term value

---

## Consequences

### Positive Impacts

- **Failure recovery**: Resume from checkpoint in <5s (Redis) or <30s (PostgreSQL)
- **Work preservation**: Zero duplicate work on retry (completed subtasks never re-executed)
- **API efficiency**: Never re-hit rate limits for completed subtasks
- **Progress visibility**: Users see granular progress at human gates
- **Unblocks features**: Enables Flaws #19 (partial failures), #23 (pause/resume), #25 (memory durability)
- **Audit trail**: Checkpoint history shows retry patterns, failure points for debugging

### Negative Impacts / Tradeoffs

- **Storage overhead**:

  - Estimate: 5 KB per checkpoint × 5 checkpoints/agent × 5 agents/stock × 200 stocks = 25 MB/batch
  - Mitigated by: auto-cleanup on success, 30-day retention for failures

- **Complexity**:

  - Save/restore logic in base agent class
  - Version compatibility system for schema changes
  - Mitigated by: clear abstraction (AgentCheckpointer class), comprehensive testing

- **Subtask definition effort**:
  - All 13 agents need structured subtask breakdown
  - Mitigated by: Flaw #22 already defines structure for 3 agents, extend pattern to remaining 10

### Affected Components

**New Components**:

- `agent_checkpoints` PostgreSQL table
- `checkpoint:{analysis_id}:{agent_type}` Redis keys
- `AgentCheckpointer` class (save/restore API)
- Subtask definitions for 13 agent types

**Modified Components**:

- `base_agent.py`: Add checkpoint hooks (call `save_checkpoint()` after subtask completion)
- `lead_coordinator.py`: Restore from checkpoint on analysis resume
- `L1 cache`: Extend `dump()` and `restore()` for working memory snapshot

**Documentation Updates**:

- `02-memory-system.md`: Add checkpoint storage tier
- `03-agents-specialist.md`: Add subtask structure for all agents
- `01-analysis-pipeline.md`: Add pause/resume workflow

---

## Implementation Notes

### Checkpoint Storage Schema (PostgreSQL)

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

### Redis Backup (Fast Recovery)

```python
# Dual storage: PostgreSQL (durable) + Redis (fast, 7-day TTL)
checkpoint_key = f"checkpoint:{analysis_id}:{agent_type}"
checkpoint_data = {
    'l1_cache': redis.dump(f"L1:{agent_id}:working"),
    'checkpoint_time': datetime.utcnow().isoformat(),
    'progress_pct': agent.calculate_progress(),
    'current_subtask': agent.next_subtask()
}

redis.setex(checkpoint_key, 7 * 24 * 3600, json.dumps(checkpoint_data))
```

### Subtask Granularity Specification

Define checkpoint-worthy subtasks for each agent type. Each subtask must produce storable deliverable:

**Financial Analyst** (4 subtasks):

1. `10k_parsing` → financial_statements_json (PostgreSQL)
2. `ratio_calculation` → ratio_table (PostgreSQL)
3. `peer_comparison` → comparison_matrix (Redis L2)
4. `red_flag_detection` → findings (Neo4j)

**Strategy Analyst** (4 subtasks):

1. `historical_roi` → roi_timeseries (PostgreSQL)
2. `ma_review` → ma_findings (Neo4j)
3. `mgmt_compensation` → compensation_analysis (Neo4j)
4. `capital_allocation_scoring` → final_score (Neo4j + message)

**Valuation Agent** (5 subtasks):

1. `dcf_assumptions` → assumption_table (PostgreSQL)
2. `cash_flow_projection` → fcf_model (PostgreSQL)
3. `wacc_calculation` → wacc_result (PostgreSQL)
4. `terminal_value` → terminal_value_calc (PostgreSQL)
5. `sensitivity_analysis` → scenario_table (Neo4j)

**Other 10 agents**: See updated `03-agents-specialist.md` for complete definitions.

### Save/Restore API

```python
class AgentCheckpointer:
    def save_checkpoint(self, agent, subtask_completed):
        """Save checkpoint after subtask completion"""
        checkpoint = {
            'stock_ticker': agent.stock_ticker,
            'agent_type': agent.agent_type,
            'analysis_id': agent.analysis_id,
            'checkpoint_time': datetime.utcnow(),
            'progress_pct': agent.calculate_progress(),
            'current_subtask': agent.next_subtask(),
            'completed_subtasks': agent.completed_subtasks,
            'pending_subtasks': agent.pending_subtasks,
            'working_memory': agent.l1_cache.dump(),
            'interim_results': agent.get_interim_results(),
            'agent_config': agent.config.to_dict(),
            'agent_version': agent.version,
            'retry_count': agent.retry_count
        }

        # Save to PostgreSQL (durable)
        db.insert('agent_checkpoints', checkpoint)

        # Save to Redis (fast recovery, 7-day TTL)
        redis.setex(
            f"checkpoint:{agent.analysis_id}:{agent.agent_type}",
            7 * 24 * 3600,
            json.dumps(checkpoint)
        )

    def restore_checkpoint(self, analysis_id, agent_type):
        """Restore agent state from checkpoint"""
        # Try Redis first (fast <5s)
        checkpoint_json = redis.get(f"checkpoint:{analysis_id}:{agent_type}")
        if checkpoint_json:
            checkpoint = json.loads(checkpoint_json)
        else:
            # Fallback to PostgreSQL (<30s)
            checkpoint = db.query(
                "SELECT * FROM agent_checkpoints "
                "WHERE analysis_id = %s AND agent_type = %s "
                "ORDER BY checkpoint_time DESC LIMIT 1",
                (analysis_id, agent_type)
            ).one()

        # Restore agent state
        agent = self.create_agent(agent_type, checkpoint['agent_config'])
        agent.analysis_id = analysis_id
        agent.stock_ticker = checkpoint['stock_ticker']
        agent.completed_subtasks = checkpoint['completed_subtasks']
        agent.pending_subtasks = checkpoint['pending_subtasks']
        agent.retry_count = checkpoint['retry_count']
        agent.l1_cache.restore(checkpoint['working_memory'])
        agent.set_interim_results(checkpoint['interim_results'])

        return agent
```

### Agent Version Compatibility

Include `agent_version` field in checkpoint schema. When agent code changes:

1. Increment agent version number
2. Provide migration function to transform old checkpoint format → new format
3. AgentCheckpointer checks version on restore, applies migrations if needed

Example:

```python
# v1.0 → v1.1: Add subtask_progress tracking
def migrate_v1_0_to_v1_1(checkpoint):
    if 'subtask_progress' not in checkpoint:
        checkpoint['subtask_progress'] = {
            task: 1.0 for task in checkpoint['completed_subtasks']
        }
    return checkpoint
```

### Checkpoint Retention Policy

**Cleanup on Success**:

- Delete checkpoints immediately after analysis completes successfully
- All findings already persisted to Neo4j, no need for checkpoint history
- Optional: move to `agent_checkpoints_archive` table for debugging

**Cleanup on Failure**:

- Retain for 30 days (allow human review of "why 3 retries?")
- Auto-delete after 30 days via scheduled cleanup job

**Manual Override**:

- Support flag to preserve checkpoints for debugging
- Use case: investigate agent performance issues, optimize subtask breakdown

### Integration Points

**Integration with L1 Memory**: When checkpoint is saved, L1 working memory is snapshotted to Redis secondary for crash recovery. See [DD-016: L1 Memory Durability](DD-016_L1_MEMORY_DURABILITY.md) for details.

1. **Base Agent Class**: Add checkpoint hook called after each subtask completes
2. **Lead Coordinator**: On analysis resume, check for checkpoint; restore if exists
3. **L1 Cache**: Implement `dump()` and `restore()` methods for working memory snapshot
4. **Failure Handler**: Trigger checkpoint save on error before agent shutdown

### Testing Requirements

- **Save/Restore Round-Trip**: Checkpoint → restore → verify identical state
- **Version Migration**: Old checkpoint → new agent version → successful restore
- **Fast Recovery**: Restore from Redis in <5s (performance test)
- **Fallback**: Redis miss → PostgreSQL fallback in <30s
- **Cleanup**: Verify checkpoints deleted on success, retained 30d on failure

### Rollback Strategy

If checkpoint system has critical bugs:

1. Disable checkpoint save (agents run without checkpoints)
2. Fallback to current behavior (restart from beginning on failure)
3. Fix bug, re-enable checkpoints
4. No data loss: system degrades gracefully to pre-checkpoint behavior

**Dependencies**:

- PostgreSQL infrastructure (exists)
- Redis infrastructure (exists)
- Subtask definitions for 13 agents (to be created)

---

## Open Questions

1. **Long-running subtasks**: For subtasks >20 min (e.g., 10-K parsing), add intermediate checkpoints within subtask?

   - **Answer**: Start with per-subtask only. Add intra-subtask checkpoints later if failure patterns show need.

2. **Nested subtasks**: Valuation DCF has 5 sub-steps. Checkpoint at what level?

   - **Answer**: Checkpoint at top-level subtask (e.g., "dcf_assumptions" completes when all sub-steps done). Sub-steps are implementation details, not checkpoint boundaries.

3. **Concurrent agent failures**: If 3 agents fail simultaneously, does checkpoint restore handle race conditions?
   - **Answer**: Each agent has independent checkpoint (unique by analysis_id + agent_type). No race conditions. Lead Coordinator restores sequentially or in parallel with separate checkpoint keys.

**Blocking**: No - answers resolved above.

---

## References

- [Flaw #22: Agent Checkpoint System Missing](../design-flaws/resolved/22-agent-checkpoints.md)
- [Flaw #19: Partial Failures](../design-flaws/active/19-partial-failures.md) - requires checkpoints for resumption
- [Flaw #23: Workflow Pause/Resume](../design-flaws/resolved/23-workflow-pause-resume.md) - depends on checkpoints
- [Flaw #25: Working Memory Durability](../design-flaws/resolved/25-working-memory-durability.md) - extends checkpoints for overnight pauses
- [DD-016: L1 Memory Durability](DD-016_L1_MEMORY_DURABILITY.md) - implements L1 snapshot/restore on checkpoint events
- PostgreSQL JSONB Documentation: <https://www.postgresql.org/docs/current/datatype-json.html>
- Redis TTL Documentation: <https://redis.io/commands/setex/>

---

## Status History

| Date       | Status   | Notes                                          |
| ---------- | -------- | ---------------------------------------------- |
| 2025-11-18 | Approved | Design finalized, resolves Flaw #22 (A1/A2/A3) |

---

## Notes

Checkpoint system is foundation for production-grade reliability. Without it, system cannot handle:

- External API failures gracefully
- Long-running analyses (overnight pauses lose L1 cache without checkpoints + Flaw #25 fix)
- User workflow control (pause/resume requires checkpoints)

Priority: High - blocks Phase 2 production readiness.
