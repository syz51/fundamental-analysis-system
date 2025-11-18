---
flaw_id: 22
title: Agent Checkpoint System Missing
status: resolved
priority: high
phase: 2
impact: Failed agents restart from scratch, wasting completed work
blocks: ['Agent resumption', 'Partial failure recovery']
depends_on: ['PostgreSQL/Redis infrastructure']
domain: ['agents', 'architecture']
sub_issues:
  - id: A1
    severity: high
    title: No agent execution state persistence
    status: resolved
  - id: A2
    severity: high
    title: Subtask progress tracking undefined
    status: resolved
  - id: A3
    severity: medium
    title: Checkpoint retention policy missing
    status: resolved
discovered: 2025-11-18
resolved: 2025-11-18
resolution: Design Decision DD-011 addresses all sub-issues
resolution_doc: docs/design-decisions/DD-011_AGENT_CHECKPOINT_SYSTEM.md
---

# Flaw #22: Agent Checkpoint System Missing

**Status**: ✅ RESOLVED
**Priority**: High
**Impact**: Failed agents restart from scratch, wasting completed work
**Phase**: Phase 2 (Months 3-4)

---

## Problem Description

No mechanism to save agent execution state during analysis, preventing resumption from checkpoint after failures:

1. **A1**: Agent execution state not persisted (progress, current subtask, interim results)
2. **A2**: Subtask progress tracking undefined (no granular checkpoints)
3. **A3**: Checkpoint retention policy missing (when to cleanup)

### Sub-Issue A1: No Agent Execution State Persistence

**Current State**: Task-level monitoring only (complete/failed/in-progress)

**Problem**: When agent fails, no record of:

- Which subtask was executing (e.g., "M&A review" step of capital allocation analysis)
- Progress percentage (e.g., 60% through 10-K parsing)
- Intermediate results (e.g., partial ROI calculations, half-completed SWOT)
- Working memory snapshot (L1 cache contents)

**Example Failure**:

```text
Strategy Analyst - AAPL Analysis:
  ✅ Historical ROI calculation (10Y data) - COMPLETED
  🔄 M&A track record review - IN PROGRESS (45% - reviewing acquisition #2 of 5)
  ⏸️ Management compensation analysis - PENDING
  ⏸️ Capital allocation scoring - PENDING

[Koyfin API rate limit exceeded at 2:47 PM]

Current Behavior: No checkpoint saved
  → Agent retry starts from beginning (wastes completed ROI work)
  → Re-fetches all data, re-parses filings
  → May hit rate limit again before reaching previous progress
```

**Missing Components**:

- Agent state schema (execution context, progress metrics)
- Storage mechanism (durable persistence layer)
- Save triggers (when to checkpoint)
- Restore procedure (how to resume from checkpoint)

---

### Sub-Issue A2: Subtask Progress Tracking Undefined

**Problem**: No specification for subtask granularity or checkpoint boundaries.

**Current Gaps**:

- What constitutes a "subtask" for checkpoint purposes?
- How granular should checkpoints be (every API call? Every finding? Every section?)
- Which subtasks have easily storable deliverables vs. transient state?
- How to handle nested subtasks (e.g., DCF model has 5 sub-steps)?

**Subtask Granularity Examples** (Need Specification):

**Financial Analyst**:

```python
# Proposed subtask breakdown
subtasks = [
    '10k_parsing',           # Deliverable: Parsed financial statements (JSON)
    'ratio_calculation',     # Deliverable: Ratio table (PostgreSQL)
    'peer_comparison',       # Deliverable: Comparison matrix (Redis L2)
    'red_flag_detection'     # Deliverable: Red flag findings (Neo4j)
]

# Checkpoint after each subtask completes
# If fails during 'peer_comparison', resume from there (ratios already saved)
```

**Strategy Analyst**:

```python
subtasks = [
    'historical_roi',        # Deliverable: 10Y ROI data (PostgreSQL)
    'ma_review',             # Deliverable: M&A track record (Neo4j findings)
    'mgmt_compensation',     # Deliverable: Compensation analysis (Neo4j)
    'capital_allocation_scoring'  # Deliverable: Final score (Neo4j + message)
]
```

**Valuation Agent** (Nested):

```python
subtasks = [
    'dcf_assumptions',       # Deliverable: Assumption table
    'cash_flow_projection',  # Deliverable: 10Y cash flow model
    'wacc_calculation',      # Deliverable: WACC inputs/result
    'terminal_value',        # Deliverable: Terminal value calc
    'sensitivity_analysis'   # Deliverable: Scenario table
]

# Each DCF step has sub-steps - checkpoint at what level?
```

**Undefined**:

- Should checkpoint after every subtask or only at major milestones?
- How to handle long-running subtasks (e.g., 10-K parsing takes 20 min)?
- Intermediate checkpoints within subtasks?

---

### Sub-Issue A3: Checkpoint Retention Policy Missing

**Problem**: No specification for when to cleanup checkpoints.

**Questions**:

1. Keep checkpoints after successful analysis completion?
2. Cleanup immediately or defer to memory system?
3. How long to retain failed analysis checkpoints?
4. What if human wants to review "why did agent restart 3 times"?

**User Decision** (from discussion):

- Cleanup after successful completion
- Defer retention decisions to memory system (let it manage lifecycle)
- As long as knowledge base keeps growing (findings always preserved in Neo4j)

**Missing Details**:

- Automatic cleanup trigger (on analysis success?)
- Manual override to preserve checkpoints for debugging
- Archival strategy for audit trail

---

## Recommended Solution

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
    agent_config JSONB,           -- Agent configuration at checkpoint time

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
# L1 working memory already in Redis - extend TTL on checkpoint
# Key: "checkpoint:{analysis_id}:{agent_type}"

checkpoint_data = {
    'l1_cache': redis.dump(f"L1:{agent_id}:working"),
    'checkpoint_time': datetime.utcnow().isoformat(),
    'expires_at': datetime.utcnow() + timedelta(days=7)
}

redis.setex(
    f"checkpoint:{analysis_id}:{agent_type}",
    7 * 24 * 3600,  # 7-day TTL for fast resume
    json.dumps(checkpoint_data)
)
```

### Subtask Granularity Specification

```python
class AgentCheckpointer:
    """Checkpoint agent state at subtask boundaries"""

    # Define checkpoint-worthy subtasks for each agent type
    SUBTASK_DEFINITIONS = {
        'financial_analyst': [
            {
                'name': '10k_parsing',
                'deliverable': 'financial_statements_json',
                'storage': 'PostgreSQL',
                'estimated_duration_min': 15
            },
            {
                'name': 'ratio_calculation',
                'deliverable': 'ratio_table',
                'storage': 'PostgreSQL',
                'estimated_duration_min': 5
            },
            {
                'name': 'peer_comparison',
                'deliverable': 'comparison_matrix',
                'storage': 'Redis L2',
                'estimated_duration_min': 10
            },
            {
                'name': 'red_flag_detection',
                'deliverable': 'findings',
                'storage': 'Neo4j',
                'estimated_duration_min': 20
            }
        ],
        'strategy_analyst': [
            {
                'name': 'historical_roi',
                'deliverable': 'roi_timeseries',
                'storage': 'PostgreSQL',
                'estimated_duration_min': 10
            },
            {
                'name': 'ma_review',
                'deliverable': 'ma_findings',
                'storage': 'Neo4j',
                'estimated_duration_min': 25
            },
            {
                'name': 'mgmt_compensation',
                'deliverable': 'compensation_analysis',
                'storage': 'Neo4j',
                'estimated_duration_min': 15
            },
            {
                'name': 'capital_allocation_scoring',
                'deliverable': 'final_score',
                'storage': 'Neo4j + message',
                'estimated_duration_min': 5
            }
        ],
        'valuation': [
            {
                'name': 'dcf_assumptions',
                'deliverable': 'assumption_table',
                'storage': 'PostgreSQL',
                'estimated_duration_min': 10
            },
            {
                'name': 'cash_flow_projection',
                'deliverable': 'fcf_model',
                'storage': 'PostgreSQL',
                'estimated_duration_min': 15
            },
            {
                'name': 'wacc_calculation',
                'deliverable': 'wacc_result',
                'storage': 'PostgreSQL',
                'estimated_duration_min': 5
            },
            {
                'name': 'terminal_value',
                'deliverable': 'terminal_value_calc',
                'storage': 'PostgreSQL',
                'estimated_duration_min': 5
            },
            {
                'name': 'sensitivity_analysis',
                'deliverable': 'scenario_table',
                'storage': 'Neo4j',
                'estimated_duration_min': 15
            }
        ]
        # ... other agents
    }

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

        # Save to Redis (fast recovery)
        redis.setex(
            f"checkpoint:{agent.analysis_id}:{agent.agent_type}",
            7 * 24 * 3600,
            json.dumps(checkpoint)
        )

        logger.info(f"Checkpoint saved: {agent.agent_type} - {subtask_completed}")

    def restore_checkpoint(self, analysis_id, agent_type):
        """Restore agent state from checkpoint"""

        # Try Redis first (fast)
        checkpoint_key = f"checkpoint:{analysis_id}:{agent_type}"
        checkpoint_json = redis.get(checkpoint_key)

        if checkpoint_json:
            checkpoint = json.loads(checkpoint_json)
        else:
            # Fallback to PostgreSQL
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

        # Restore L1 working memory
        agent.l1_cache.restore(checkpoint['working_memory'])

        # Restore interim results
        agent.set_interim_results(checkpoint['interim_results'])

        logger.info(f"Checkpoint restored: {agent_type} at {checkpoint['progress_pct']}%")

        return agent
```

### Agent Version Compatibility

```python
class AgentVersionManager:
    """Ensure new agent versions can read old checkpoints"""

    def migrate_checkpoint(self, checkpoint, from_version, to_version):
        """Migrate checkpoint data across agent versions"""

        migrations = self.get_migrations(from_version, to_version)

        for migration in migrations:
            checkpoint = migration.apply(checkpoint)

        return checkpoint

    # Example migration
    class AddSubtaskProgressMigration:
        """v1.0 → v1.1: Add subtask progress tracking"""

        def apply(self, checkpoint):
            if 'subtask_progress' not in checkpoint:
                # Infer from completed_subtasks
                checkpoint['subtask_progress'] = {
                    task: 1.0 for task in checkpoint['completed_subtasks']
                }
            return checkpoint
```

**Requirement**: All agent updates must include checkpoint migration logic.

### Checkpoint Retention Policy

```python
class CheckpointRetentionPolicy:
    """Manage checkpoint lifecycle"""

    def cleanup_on_success(self, analysis_id):
        """Delete checkpoints after successful analysis completion"""

        # Move to archive table (optional, for debugging)
        db.execute(
            "INSERT INTO agent_checkpoints_archive "
            "SELECT * FROM agent_checkpoints WHERE analysis_id = %s",
            (analysis_id,)
        )

        # Delete from active checkpoints
        db.execute(
            "DELETE FROM agent_checkpoints WHERE analysis_id = %s",
            (analysis_id,)
        )

        # Delete from Redis
        checkpoint_keys = redis.keys(f"checkpoint:{analysis_id}:*")
        if checkpoint_keys:
            redis.delete(*checkpoint_keys)

    def cleanup_expired_failures(self, days=30):
        """Delete old failed analysis checkpoints"""

        db.execute(
            "DELETE FROM agent_checkpoints "
            "WHERE failure_reason IS NOT NULL "
            "AND checkpoint_time < NOW() - INTERVAL '%s days'",
            (days,)
        )
```

---

## Implementation Plan

**Week 1**: PostgreSQL schema, Redis backup mechanism
**Week 2**: Subtask definitions for all 13 agents, save/restore API
**Week 3**: Agent version compatibility, retention policy, testing

---

## Success Criteria

- ✅ Checkpoint saved after every subtask completion (100% coverage for 13 agents)
- ✅ Restore from checkpoint completes <5s (Redis) or <30s (PostgreSQL)
- ✅ New agent versions read old checkpoints (backwards compatibility)
- ✅ Failed analysis resume from last checkpoint (no duplicate work)
- ✅ Checkpoint cleanup on success (no orphaned data)

---

## Dependencies

- **Blocks**: Flaw #23 (workflow pause/resume), Flaw #25 (working memory durability)
- **Depends On**: PostgreSQL/Redis infrastructure (exists)
- **Related**: Flaw #19 (partial failures - needs checkpoints for resumption)

---

## Files Affected

**New Files**:

- `src/agents/checkpoint.py` - Checkpointer class, save/restore logic
- `src/agents/subtasks.py` - Subtask definitions for each agent
- `migrations/xxx_agent_checkpoints.sql` - PostgreSQL schema

**Modified Files**:

- `src/agents/base_agent.py` - Add checkpoint hooks
- `src/agents/coordinator.py` - Restore from checkpoint on resume
- `docs/architecture/03-agents-specialist.md` - Document subtask structure
- `docs/architecture/02-memory-system.md` - Add checkpoint storage tier
