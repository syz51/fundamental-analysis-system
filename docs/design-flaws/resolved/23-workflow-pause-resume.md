---
flaw_id: 23
title: Workflow Pause/Resume Infrastructure Undefined
status: resolved
priority: high
phase: 2
effort_weeks: 4
impact: Cannot safely stop analysis mid-pipeline when failures occur
blocks: ['Partial failure recovery', 'Agent failure handling']
depends_on: ['Flaw #22 (agent checkpoints)']
domain: ['architecture', 'operations']
sub_issues:
  - id: B1
    severity: high
    title: No per-stock pipeline pause capability
  - id: B2
    severity: high
    title: Dependency-aware resumption logic missing
  - id: B3
    severity: medium
    title: Parallel resume for batch failures undefined
discovered: 2025-11-18
resolved: 2025-11-18
---

# Flaw #23: Workflow Pause/Resume Infrastructure Undefined

---
**RESOLVED**

**Resolution Date**: 2025-11-18
**Resolved By**: DD-012 (Workflow Pause/Resume Infrastructure)
**Implementation Status**: Design Complete - Pending Phase 2 Implementation (4 weeks)
**Design Decision**: See [DD-012](../design-decisions/DD-012_WORKFLOW_PAUSE_RESUME.md) for comprehensive architecture, API specs, state machine, database schema

**Summary**: Design completed with 3-component architecture (PauseManager, DependencyResolver, BatchManager), 3-tier failure classification, 14-day timeout policy, tech-agnostic orchestrator integration. All sub-issues (B1, B2, B3) addressed.

---

[Original flaw content below]

---

**Status**: 🔴 ACTIVE
**Priority**: High
**Impact**: Cannot safely stop analysis mid-pipeline when failures occur
**Phase**: Phase 2 (Months 3-4)

---

## Problem Description

No mechanism to pause/resume analyses mid-pipeline when agent failures occur:

1. **B1**: No per-stock pipeline pause capability (all-or-nothing execution)
2. **B2**: Dependency-aware resumption logic missing (which agents can resume? which wait?)
3. **B3**: Parallel resume for batch failures undefined (sequential vs. concurrent)

### Sub-Issue B1: No Per-Stock Pipeline Pause Capability

**Current State**: Pipeline runs to completion or fails entirely

**Problem**: When agent fails for one stock (e.g., AAPL), cannot pause just that analysis:

- Either entire system halts (blocks other stocks)
- Or analysis silently continues incomplete (data integrity issue)
- No "pause AAPL, continue MSFT/GOOGL" capability

**Example Scenario**:

```text
Day 5 - Phase 2 Parallel Analysis:
  AAPL: ❌ Strategy Analyst FAILED (Koyfin rate limit)
  MSFT: ✅ All agents running normally
  GOOGL: ✅ All agents running normally
  AMZN: ✅ All agents running normally

Current Behavior: No pause mechanism
  → Either halt all 4 analyses (inefficient)
  → Or continue AAPL incomplete (data integrity risk)

Desired Behavior: Pause AAPL only
  → MSFT/GOOGL/AMZN continue unaffected
  → AAPL waits for human intervention
  → Resume AAPL after Koyfin quota restored
```

**Missing Components**:

- Pipeline pause API (stop analysis for specific stock)
- Pause state persistence (remember "AAPL paused at Phase 2 Day 5")
- Other stocks isolation (MSFT analysis unaffected by AAPL pause)
- Pause reason tracking (why paused? which agent failed?)

---

### Sub-Issue B2: Dependency-Aware Resumption Logic Missing

**Problem**: When resuming paused analysis, which agents should restart? Which should wait?

**Example Resume Scenario**:

```text
AAPL paused at Phase 2 Day 5:
  ✅ Business Research: COMPLETED (findings in Neo4j)
  ✅ Financial Analyst: COMPLETED (findings in Neo4j)
  ❌ Strategy Analyst: FAILED (checkpoint at 60%)
  ⏸️ Valuation: WAITING (depends on Strategy findings)
  ✅ News Monitor: COMPLETED (findings in Neo4j)

Human resolves Koyfin quota at 3:15 PM.

Resume Questions:
  1. Should Business/Financial/News restart or stay "done"?
     → Stay done (findings already in Neo4j)

  2. Should Strategy restart from beginning or checkpoint?
     → Resume from checkpoint (60% - M&A review)

  3. Should Valuation start immediately or wait?
     → Wait for Strategy to complete (dependency)

  4. After Strategy completes, should Valuation auto-start?
     → Yes (dependency satisfied)

  5. What if Strategy fails again?
     → Pause again, alert human
```

**Missing Dependency Logic**:

```python
# Need to track agent dependencies for resume
AGENT_DEPENDENCIES = {
    'business_research': [],  # No dependencies
    'financial_analyst': [],  # No dependencies
    'strategy_analyst': [],   # No dependencies
    'valuation': ['business_research', 'financial_analyst', 'strategy_analyst'],
    'news_monitor': []        # No dependencies
}

# On resume:
# 1. Check which dependencies completed before pause
# 2. Resume failed agent from checkpoint
# 3. Auto-start waiting agents when dependencies satisfied
```

**Current Gap**: Lead Coordinator has DAG for task scheduling, but no pause/resume logic.

---

### Sub-Issue B3: Parallel Resume for Batch Failures Undefined

**Problem**: If multiple stocks paused due to shared failure (e.g., Koyfin quota affects 5 stocks), how to resume?

**User Requirement** (from discussion): Allow parallel resume (no forced sequential)

**Batch Resume Scenario**:

```text
5 stocks paused due to Koyfin rate limit:
  AAPL - Strategy Analyst at 60%
  MSFT - Strategy Analyst at 45%
  GOOGL - Strategy Analyst at 70%
  AMZN - Strategy Analyst at 30%
  META - Strategy Analyst at 55%

Human upgrades Koyfin to paid tier at 3:15 PM.
Clicks "Resume All" button.

Current Behavior: Undefined
  → Sequential resume? (one at a time, 5x slower)
  → Parallel resume? (all 5 simultaneously)
  → Priority-based? (resume highest progress first?)

Desired Behavior: Parallel resume
  → All 5 Strategy Agents restart from checkpoints simultaneously
  → Respects agent concurrency limits (max 3 concurrent Strategy Analysts)
  → Queue remaining: AAPL/MSFT/GOOGL start, AMZN/META queued
  → As slots free, queued agents start
```

**Missing Specification**:

- Batch resume API (resume multiple stocks at once)
- Concurrency limit enforcement (respect max 3 Strategy Analysts)
- Queue management (which stocks start first if >concurrency limit?)
- Progress tracking (show "2/5 stocks resumed, 3 queued")

---

## Recommended Solution

### Pause API (Lead Coordinator Extension)

```python
class LeadCoordinator:
    """Extended with pause/resume capabilities"""

    def pause_analysis(self, stock_ticker, reason, failed_agent=None):
        """Pause pipeline for specific stock"""

        # Get current pipeline state
        pipeline_state = self.get_pipeline_state(stock_ticker)

        # Save pause metadata
        pause_record = {
            'stock_ticker': stock_ticker,
            'paused_at': datetime.utcnow(),
            'phase': pipeline_state.current_phase,
            'day': pipeline_state.current_day,
            'reason': reason,
            'failed_agent': failed_agent,
            'completed_agents': pipeline_state.completed_agents,
            'in_progress_agents': pipeline_state.in_progress_agents,
            'pending_agents': pipeline_state.pending_agents,
            'analysis_id': pipeline_state.analysis_id
        }

        # Persist to PostgreSQL
        db.insert('paused_analyses', pause_record)

        # Update Airflow DAG state
        airflow_dag = self.get_dag(stock_ticker)
        airflow_dag.pause(reason=reason)

        # Publish pause event
        self.publish_event({
            'event_type': 'analysis_paused',
            'stock_ticker': stock_ticker,
            'reason': reason,
            'failed_agent': failed_agent
        })

        logger.info(f"Analysis paused: {stock_ticker} - {reason}")

        return pause_record

    def resume_analysis(self, stock_ticker):
        """Resume paused analysis from checkpoint"""

        # Load pause record
        pause_record = db.query(
            "SELECT * FROM paused_analyses "
            "WHERE stock_ticker = %s AND resumed_at IS NULL "
            "ORDER BY paused_at DESC LIMIT 1",
            (stock_ticker,)
        ).one()

        if not pause_record:
            raise ValueError(f"No paused analysis found for {stock_ticker}")

        # Determine which agents need to resume
        resume_plan = self.create_resume_plan(pause_record)

        # Execute resume plan
        for agent_task in resume_plan.tasks:
            if agent_task.status == 'completed':
                # Skip - already done
                continue
            elif agent_task.status == 'failed':
                # Resume from checkpoint
                agent = self.restore_agent_from_checkpoint(
                    pause_record['analysis_id'],
                    agent_task.agent_type
                )
                self.start_agent(agent, resume=True)
            elif agent_task.status == 'waiting':
                # Schedule to start when dependencies satisfied
                self.schedule_when_ready(agent_task)

        # Update pause record
        db.execute(
            "UPDATE paused_analyses SET resumed_at = NOW() "
            "WHERE stock_ticker = %s AND resumed_at IS NULL",
            (stock_ticker,)
        )

        # Resume Airflow DAG
        airflow_dag = self.get_dag(stock_ticker)
        airflow_dag.unpause()

        # Publish resume event
        self.publish_event({
            'event_type': 'analysis_resumed',
            'stock_ticker': stock_ticker,
            'resume_plan': resume_plan.summary()
        })

        logger.info(f"Analysis resumed: {stock_ticker}")

        return resume_plan

    def create_resume_plan(self, pause_record):
        """Determine which agents to resume/skip/wait"""

        plan = ResumePlan(stock_ticker=pause_record['stock_ticker'])

        for agent_type in ALL_AGENT_TYPES:
            if agent_type in pause_record['completed_agents']:
                # Agent finished before pause - skip
                plan.add_task(agent_type, action='skip', reason='already_completed')

            elif agent_type == pause_record['failed_agent']:
                # Failed agent - resume from checkpoint
                plan.add_task(agent_type, action='resume_from_checkpoint', reason='failed')

            elif agent_type in pause_record['in_progress_agents']:
                # Was in progress - check if has checkpoint
                checkpoint = self.get_latest_checkpoint(
                    pause_record['analysis_id'],
                    agent_type
                )
                if checkpoint:
                    plan.add_task(agent_type, action='resume_from_checkpoint', reason='interrupted')
                else:
                    plan.add_task(agent_type, action='restart', reason='no_checkpoint')

            elif agent_type in pause_record['pending_agents']:
                # Never started - check dependencies
                dependencies = AGENT_DEPENDENCIES[agent_type]
                dependencies_met = all(
                    dep in pause_record['completed_agents'] or
                    dep in plan.resuming_agents
                    for dep in dependencies
                )

                if dependencies_met:
                    plan.add_task(agent_type, action='start_when_ready', reason='dependencies_met')
                else:
                    plan.add_task(agent_type, action='wait_for_dependencies', reason='blocked')

        return plan
```

### Dependency-Aware Resumption

```python
# Define agent dependencies (parallel analysis phase)
AGENT_DEPENDENCIES = {
    'screening': [],
    'business_research': ['screening'],
    'financial_analyst': ['screening'],
    'strategy_analyst': ['screening'],
    'news_monitor': ['screening'],
    'valuation': ['business_research', 'financial_analyst', 'strategy_analyst'],
    'debate_facilitator': ['valuation', 'news_monitor'],
    'qc_agent': ['debate_facilitator'],
    'report_writer': ['qc_agent']
}

class DependencyResolver:
    """Resolve agent dependencies for resumption"""

    def get_ready_agents(self, completed_agents, resuming_agents):
        """Return agents whose dependencies are satisfied"""

        ready = []

        for agent_type, dependencies in AGENT_DEPENDENCIES.items():
            if agent_type in completed_agents or agent_type in resuming_agents:
                continue  # Already done or resuming

            dependencies_met = all(
                dep in completed_agents or dep in resuming_agents
                for dep in dependencies
            )

            if dependencies_met:
                ready.append(agent_type)

        return ready

    def auto_start_on_completion(self, completed_agent, pause_record):
        """Auto-start waiting agents when dependency completes"""

        # Find agents waiting for this completion
        waiting_for_this = [
            agent_type
            for agent_type, deps in AGENT_DEPENDENCIES.items()
            if completed_agent in deps and
               agent_type in pause_record['pending_agents']
        ]

        for agent_type in waiting_for_this:
            # Check if all dependencies now satisfied
            all_deps_met = all(
                dep in pause_record['completed_agents']
                for dep in AGENT_DEPENDENCIES[agent_type]
            )

            if all_deps_met:
                logger.info(f"Auto-starting {agent_type} (dependencies satisfied)")
                self.start_agent(agent_type, pause_record['stock_ticker'])
```

### Batch Resume (Parallel)

```python
class BatchResumeManager:
    """Handle resuming multiple paused analyses"""

    def resume_batch(self, stock_tickers):
        """Resume multiple stocks in parallel (respecting concurrency limits)"""

        # Get all pause records
        pause_records = [
            self.get_pause_record(ticker)
            for ticker in stock_tickers
        ]

        # Create resume plans
        resume_plans = [
            self.create_resume_plan(record)
            for record in pause_records
        ]

        # Group by agent type for concurrency management
        agent_tasks = defaultdict(list)
        for plan in resume_plans:
            for task in plan.tasks:
                if task.action == 'resume_from_checkpoint':
                    agent_tasks[task.agent_type].append({
                        'stock': plan.stock_ticker,
                        'task': task
                    })

        # Submit tasks respecting concurrency limits
        for agent_type, tasks in agent_tasks.items():
            concurrency_limit = AGENT_CONCURRENCY[agent_type]

            # Start first N tasks (up to limit)
            immediate = tasks[:concurrency_limit]
            queued = tasks[concurrency_limit:]

            for task_info in immediate:
                self.start_agent_resume(
                    task_info['stock'],
                    agent_type,
                    priority='immediate'
                )

            for task_info in queued:
                self.queue_agent_resume(
                    task_info['stock'],
                    agent_type,
                    priority='normal'
                )

        # Return batch resume status
        return BatchResumeStatus(
            total=len(stock_tickers),
            immediate=sum(len(t[:AGENT_CONCURRENCY[a]]) for a, t in agent_tasks.items()),
            queued=sum(len(t[AGENT_CONCURRENCY[a]:]) for a, t in agent_tasks.items())
        )


# Agent concurrency limits (from docs/architecture/03-agents-specialist.md)
AGENT_CONCURRENCY = {
    'screening': 5,
    'business_research': 3,
    'financial_analyst': 2,
    'strategy_analyst': 3,
    'valuation': 1,
    'news_monitor': 10,
    # ... others
}
```

### Pause State Schema (PostgreSQL)

```sql
CREATE TABLE paused_analyses (
    id SERIAL PRIMARY KEY,
    stock_ticker VARCHAR(10) NOT NULL,
    analysis_id UUID NOT NULL,

    -- Pause details
    paused_at TIMESTAMP NOT NULL,
    resumed_at TIMESTAMP,
    phase VARCHAR(50),
    day INT,
    reason TEXT,
    failed_agent VARCHAR(50),

    -- Pipeline state snapshot
    completed_agents TEXT[],
    in_progress_agents TEXT[],
    pending_agents TEXT[],

    -- Resume tracking
    resume_plan JSONB,
    resume_outcome TEXT,

    INDEX idx_ticker (stock_ticker),
    INDEX idx_active_pauses (stock_ticker, resumed_at) WHERE resumed_at IS NULL
);
```

---

## Implementation Plan

**Week 1**: Pause API, pause state schema, Airflow DAG integration
**Week 2**: Dependency resolution, resume plan creation
**Week 3**: Batch resume, concurrency management
**Week 4**: Auto-start on dependency satisfaction, testing

---

## Success Criteria

- ✅ Pause single stock without affecting others (100% isolation)
- ✅ Resume from checkpoint with correct dependencies (no premature starts)
- ✅ Batch resume respects concurrency limits (no overload)
- ✅ Auto-start waiting agents when dependencies satisfied (<30s latency)
- ✅ Parallel resume for 5 stocks completes in <10min (vs. 50min sequential)

---

## Dependencies

- **Blocks**: Flaw #24 (agent failure alerts - needs pause mechanism)
- **Depends On**: Flaw #22 (agent checkpoints - must exist to resume)
- **Related**: Flaw #19 (partial failures - pause is response to failures)

---

## Files Affected

**New Files**:

- `src/coordination/pause_manager.py` - Pause/resume logic
- `src/coordination/dependency_resolver.py` - Dependency tracking
- `migrations/xxx_paused_analyses.sql` - PostgreSQL schema

**Modified Files**:

- `src/coordination/lead_coordinator.py` - Add pause/resume API
- `src/workflows/airflow_dags.py` - DAG pause/unpause support
- `docs/operations/01-analysis-pipeline.md` - Document pause/resume workflow
- `docs/architecture/05-agents-coordination.md` - Add pause/resume protocol
