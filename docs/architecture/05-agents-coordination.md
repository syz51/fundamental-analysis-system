# Coordination Agents

## Overview

Coordination agents orchestrate the overall workflow and manage collaborative processes. They ensure smooth execution across all agents, facilitate structured debates, and manage the human interface for critical decision gates.

The two coordination agents are:

1. Lead Analyst Coordinator - Overall workflow orchestration
2. Debate Facilitator Agent - Collaborative analysis and conflict resolution

---

## 1. Lead Analyst Coordinator

### Purpose

Orchestrate overall workflow

### Responsibilities

- Workflow orchestration across 13 agent types
- Agent lifecycle management (start, monitor, restart)
- Message routing via central queue
- **Pause/resume orchestration via PauseManager** (DD-012)
- **Failure classification (Tier 1/2/3 routing)** (DD-012)
- **Batch operation coordination via BatchManager** (DD-012)
- Conflict resolution escalation
- Human gate coordination
- Performance monitoring

### Coordination Functions

**Workflow Orchestration**:

- Schedule and sequence agent tasks
- Manage dependencies between analysis phases
- Track progress against timelines
- Optimize parallel execution

**Resource Allocation**:

- Distribute work across agents
- Balance load and priorities
- Allocate computational resources
- Manage queue and backlog

**Bottleneck Management**:

- Identify workflow slowdowns
- Resolve resource constraints
- Escalate blocking issues
- Rebalance workloads

**Communication Facilitation**:

- Route messages between agents
- Coordinate multi-agent tasks
- Manage information flow
- Ensure critical findings propagate

### Dependency Resolution and Parallel Scheduling

The Lead Coordinator uses a sophisticated dependency resolution algorithm to optimize parallel agent execution while respecting resource constraints and dependencies. This enables efficient processing of multiple stock analyses simultaneously without deadlocks or resource contention.

#### Algorithm Overview

The scheduler performs four key operations:

1. **Dependency graph construction** - Build DAG of analysis task dependencies
2. **Critical path calculation** - Identify longest execution path
3. **Topological sorting** - Determine valid execution order
4. **Capacity-aware scheduling** - Assign tasks to time slots respecting agent capacity limits

#### Implementation Specification

```python
class DependencyResolver:
    """Schedule parallel agent execution with dependencies"""

    def __init__(self):
        self.dependency_graph = nx.DiGraph()  # NetworkX directed graph
        self.agent_capacity = {
            'screening': 5,      # Can handle 5 concurrent stocks
            'business': 3,       # Can handle 3 concurrent analyses
            'financial': 2,      # Can handle 2 concurrent analyses
            'strategy': 3,       # Can handle 3 concurrent analyses
            'valuation': 1       # Bottleneck - 1 at a time
        }

    def build_schedule(self, analyses):
        """Create optimal execution schedule"""

        # Build dependency graph for all analyses
        for analysis in analyses:
            self._add_analysis_deps(analysis)

        # Find critical path (longest path in DAG)
        critical_path = self._find_critical_path()

        # Topological sort for execution order
        execution_order = list(nx.topological_sort(self.dependency_graph))

        # Schedule tasks respecting dependencies and capacity
        schedule = self._schedule_with_capacity(
            execution_order,
            critical_path
        )

        return ExecutionSchedule(
            tasks=schedule,
            critical_path=critical_path,
            estimated_completion=self._estimate_completion(schedule),
            parallelism_factor=self._calc_parallelism(schedule)
        )

    def _find_critical_path(self):
        """Find longest path (critical path) in DAG"""
        # Use dynamic programming to find critical path
        return nx.dag_longest_path(
            self.dependency_graph,
            weight='duration'
        )

    def _schedule_with_capacity(self, tasks, critical_path):
        """Assign tasks to time slots respecting capacity"""
        schedule = []
        time = 0
        active_tasks = defaultdict(int)  # {agent_type: count}

        while tasks:
            # Find tasks ready to execute (dependencies met)
            ready = [t for t in tasks if self._deps_met(t, schedule)]

            # Prioritize critical path tasks
            ready.sort(
                key=lambda t: t in critical_path,
                reverse=True
            )

            # Assign tasks up to capacity
            for task in ready:
                agent = task.agent_type
                if active_tasks[agent] < self.agent_capacity[agent]:
                    schedule.append(TaskExecution(
                        task=task,
                        start_time=time,
                        agent=agent
                    ))
                    active_tasks[agent] += 1
                    tasks.remove(task)

            # Advance time to next completion
            time = self._next_completion_time(schedule, time)
            active_tasks = self._update_active(schedule, time)

        return schedule

    def _deps_met(self, task, schedule):
        """Check if task dependencies are satisfied"""
        completed = {t.task.id for t in schedule if t.is_complete()}
        return all(dep in completed for dep in task.dependencies)
```

#### Scheduling Example

```text
Scenario: Two stocks (AAPL, MSFT) analyzed in parallel

Analysis Dependencies (per stock):
  Screening ──→ Business ──┐
           └──→ Financial ─┼──→ Valuation ──→ Report
                └──→ Strategy ┘

Agent Capacity Constraints:
  - Financial Analyst: 2 concurrent (can handle both stocks)
  - Valuation Agent: 1 concurrent (bottleneck - sequential only)

Optimal Schedule:

  T0-T2: AAPL Screening + MSFT Screening (parallel)
  T2-T4: AAPL Business + MSFT Business (parallel, no resource conflict)
  T4-T6: AAPL Financial + MSFT Financial (parallel, within capacity=2)
         AAPL Strategy + MSFT Strategy (parallel, within capacity=3)
  T6-T7: AAPL Valuation (sequential - MSFT must wait)
  T7-T8: MSFT Valuation (after AAPL completes)
  T8-T9: AAPL Report + MSFT Report (parallel)

Critical Path: Screening → Business → Financial → Valuation → Report
Total Time: 9 time units (vs 18 if purely sequential)
Parallelism Factor: 2.0x speedup

Bottleneck Analysis:
  - Valuation agent is bottleneck (capacity=1)
  - Other agents underutilized during valuation phase
  - Scaling valuation capacity to 2 would improve throughput
```

#### Deadlock Prevention

The algorithm prevents deadlocks through:

1. **DAG constraint** - Circular dependencies rejected during graph construction
2. **Topological ordering** - Ensures valid execution sequence exists
3. **Progress guarantee** - At least one task always schedulable if resources available
4. **Timeout detection** - Tasks exceeding expected duration flagged for intervention

#### Performance Optimization

**Critical Path Prioritization**: Tasks on critical path scheduled first when multiple ready

**Resource Balancing**: Agents with higher capacity allocated more work upfront

**Look-ahead Scheduling**: Consider next 3 time slots when assigning tasks to prevent local optima

**Dynamic Re-scheduling**: If agent becomes unavailable, re-run scheduler for remaining tasks

**Human Gate Preparation**:

- Package information for human review
- Prepare decision materials
- Send notifications and reminders
- Track human response times

---

### Pause/Resume Components (DD-012)

The Lead Coordinator integrates with three specialized components for workflow pause/resume operations:

#### PauseManager

**Purpose**: Orchestrates pause/resume operations, manages state transitions

**Responsibilities**:
- State machine management (RUNNING → PAUSING → PAUSED → RESUMING → RUNNING)
- Timeout escalation (day 3/7/14/30 alerts)
- Alert triggering (pause initiated, reminders, auto-resume)
- Checkpoint integration (save on pause, load on resume via DD-011)

**API**:
- `pause_analysis(stock_id, reason, checkpoint_id, trigger_source)`
- `resume_analysis(stock_id, resume_plan, notify)`
- `get_pause_state(stock_id)`

**Interactions**:
- Calls checkpoint system (DD-011) for state persistence
- Triggers alerts via alert system (Flaw #24)
- Extends L1 memory TTL via memory system (Flaw #25)

#### DependencyResolver

**Purpose**: Analyzes agent dependencies, generates resume plans

**Responsibilities**:
- Build agent dependency DAG from pipeline configuration
- Identify completed agents (skip on resume)
- Identify failed agent + dependents (restart on resume)
- Handle parallel in-progress agents (wait or restart)
- Generate executable resume plans

**Algorithm**:
1. Load pipeline config, construct DAG
2. Extract checkpoint state (completed agents)
3. Mark failed agent + downstream dependents for restart
4. Mark completed agents for skip
5. Return `ResumePlan{restart: [], skip: [], wait: []}`

**API**:
- `resolve_dependencies(failed_agent, checkpoint) -> ResumePlan`
- `create_resume_plan(stock_id) -> ResumePlan`

**Interactions**:
- Queries checkpoint system for agent completion status
- Provides resume plans to PauseManager and orchestrator

#### BatchManager

**Purpose**: Coordinates concurrent pause/resume for multiple stocks

**Responsibilities**:
- Batch pause operations (parallel coordination)
- Batch resume operations (priority queue, concurrency control)
- Resource-aware scheduling (quota/capacity checks)
- Failure isolation (batch pause if >50% fail)

**API**:
- `pause_batch(stock_ids, reason, max_concurrency=5)`
- `resume_batch(stock_ids, concurrency_limit=5)`
- `get_batch_status(batch_id) -> {total, paused, resumed, failed}`

**Strategy**:
- Priority queue: oldest pauses first, gate-timeouts prioritized
- Concurrency: 5 parallel resumes default (configurable)
- Resource checks: API quota, compute capacity, DB connections

**Interactions**:
- Calls PauseManager for individual stock operations
- Monitors orchestrator resource utilization
- Coordinates with alert system for batch notifications
- Accepts auto-trigger from FailureCorrelator (DD-017)

#### FailureCorrelator

**Purpose**: Automatically detect correlated failures, infer root causes, trigger batch operations

**Responsibilities**:
- Error signature generation (normalize vendor-specific errors)
- Temporal correlation detection (5min window clustering)
- Root cause inference (API quota vs network vs data patterns)
- Auto-batch trigger (3+ correlated failures → batch pause)

**Algorithm**:
1. On agent failure, generate error signature: `hash(agent_type, error_type, data_source, normalized_msg)`
2. Detect correlations: find failures with same signature within 5min window
3. Check batch threshold: if ≥3 correlated failures, trigger batch pause
4. Infer root cause: API quota (3+ stocks, same source) vs network (5+ stocks) vs data (404 patterns)
5. Auto-trigger BatchManager with root cause and correlation_id

**API**:
- `on_agent_failure(stock_ticker, agent_type, error_type, error_message, data_source) -> CorrelationResult`
- `generate_error_signature(agent_type, error_type, data_source, error_message) -> str`
- `detect_correlation(signature, timestamp, window_minutes=5) -> List[UUID]`
- `infer_root_cause(signature, correlated_failures) -> str`
- `trigger_batch_pause(stock_ids, root_cause, correlation_id) -> BatchPauseResult`

**Error Signature Normalization**:
- Remove timestamps, UUIDs, request IDs
- Normalize quota numbers: "1000/1000" → "LIMIT_EXCEEDED"
- Extract semantic patterns: "quota exceeded" → "api_quota_exceeded"
- Hash normalized signature for matching

**Root Cause Inference Rules**:
1. **API Quota**: 3+ stocks, same data source, quota error → "{source} API quota exceeded"
2. **Network Outage**: 5+ stocks, same source, timeout/connection → "{source} network connectivity"
3. **Data Unavailability**: 3+ stocks, 404/not found → "{source} data unavailable"
4. **Agent Bug**: 3+ stocks, same agent type, same error → "{agent} failure - {error}"
5. **Fallback**: Generic correlation → "Shared failure - {count} stocks"

**Example Correlations**:
- AAPL, MSFT, GOOGL, AMZN, TSLA all fail at 14:47 with Koyfin quota error
- FailureCorrelator detects within 30s: signature match, 5 failures within 5min window
- Infers: "Koyfin API quota exceeded"
- Auto-triggers: `BatchManager.pause_batch(["AAPL", "MSFT", ...], "Koyfin API quota exceeded")`
- AlertManager creates 5 separate cards (DD-015 requirement) with "Resume All" button

**Interactions**:
- Subscribes to agent failure events via Lead Coordinator
- Calls BatchManager for auto-batch pause trigger
- Stores correlation records in failure_correlations table
- Links correlations to batch operations via batch_id

#### Message Types (Extended)

**Existing Types**: Finding, Request, Challenge, Confirmation, Alert

**New Types (DD-012)**:
- **PAUSE_REQUEST**: `{stock_id, reason, checkpoint_id, trigger_source}`
  - Sent by: Lead Coordinator (on Tier 2 failure)
  - Recipient: PauseManager
- **PAUSE_COMPLETE**: `{stock_id, paused_at, resume_dependencies}`
  - Sent by: PauseManager
  - Recipient: Lead Coordinator, Alert System
- **RESUME_COMMAND**: `{stock_id, resume_plan, notify}`
  - Sent by: Lead Coordinator or Human
  - Recipient: PauseManager
- **BATCH_PAUSE_REQUEST**: `{stock_ids, reason, batch_id, max_concurrency}`
  - Sent by: Lead Coordinator
  - Recipient: BatchManager

**New Types (DD-017)**:
- **AGENT_FAILURE_EVENT**: `{stock_ticker, agent_type, error_type, error_message, data_source, timestamp}`
  - Sent by: Base Agent (on failure), Lead Coordinator
  - Recipient: FailureCorrelator
- **CORRELATION_DETECTED**: `{correlation_id, stock_tickers, root_cause, signature, batch_triggered}`
  - Sent by: FailureCorrelator
  - Recipient: Lead Coordinator, BatchManager
- **BATCH_TRIGGER**: `{stock_ids, root_cause, correlation_id}`
  - Sent by: FailureCorrelator (auto-trigger)
  - Recipient: BatchManager

---

## 2. Debate Facilitator Agent

### Purpose

Structure collaborative analysis, manage knowledge conflicts, and provide fallback resolution when human arbitration unavailable

### Responsibilities

- Organize discussion rounds
- Present opposing viewpoints
- Document consensus and dissent
- Force position defense with evidence
- Highlight uncertainties
- Ensure all perspectives considered
- **Apply credibility-weighted auto-resolution when appropriate**
- **Manage provisional resolutions and override tracking**
- **Route debates based on priority and expert workload**

### Debate Protocol

**Setup Phase**:

- Set debate topics and participants
- Establish evidence standards
- Load relevant historical context
- Set time limits and rules
- Assign priority classification (critical-path, valuation, supporting)
- Check expert queue status (max 3 concurrent per expert)

**Execution Phase**:

- Manage challenge-response cycles
- Track argument strength and credibility
- Enforce evidence requirements
- Maintain structured dialogue
- Apply tiered escalation (see Level 2 below)

**Resolution Phase**:

- Synthesize final positions
- Document areas of agreement/disagreement
- Escalate unresolved conflicts (with fallback mechanisms)
- Update knowledge base with outcomes
- Track provisional decisions for gate review

### Debate Mechanics

**Challenge Structure**:

- Challenger and challenged agents identified
- Disputed finding clearly stated
- Challenge basis with evidence
- Required response and evidence type
- Escalation timer (typically 1 hour)
- Priority classification

**Response Requirements**:

1. Acknowledge within 15 minutes
2. Provide evidence within 1 hour
3. Apply credibility-weighted auto-resolution if applicable (Level 2)
4. Escalate to human if unresolved (Level 3)
5. Apply fallback resolution if human unavailable (Level 4)
6. Document resolution

**Credibility Weighting**:

Sophisticated multi-factor credibility assessment incorporating:

- **Temporal decay**: Exponential weighting with configurable half-life (default 2 years)
- **Market regime specificity**: Regime-aware credibility (bull/bear, high/low rates, volatility)
- **Performance trends**: Linear regression on rolling accuracy, extrapolate 6 months forward
- **Human override tracking**: Penalty for high override rates (>20%)
- **Multi-dimensional context matching**: Sector, metric type, time horizon, company size, growth stage
- **Evidence quality**: Current debate evidence strength assessment
- **Credibility differential calculation**: Compare agents for auto-resolution threshold (>0.25)

### Fallback Resolution Authority (Level 2 & Level 4)

The Debate Facilitator has authority to resolve debates automatically when human arbitration is unavailable or when credibility gap is sufficient.

#### Level 2: Credibility-Weighted Auto-Resolution

**Trigger Conditions**:

- Agents fail to reach consensus after 1 hour
- Both agents have sufficient historical data (minimum 15 data points)
- Credibility differential >0.25 (dynamic threshold: `max(0.25, CI_A + CI_B)`)

**Process**:

1. Calculate comprehensive agent credibility scores in relevant context:

   ```python
   # Base accuracy with multi-dimensional context matching
   base_accuracy = (
       context_specific_accuracy * context_weight +
       overall_accuracy * (1 - context_weight)
   )

   # Temporal decay (exponential with agent-specific half-life)
   temporal_weight = 0.5^(age_years / decay_halflife_years)

   # Market regime adjustment (current regime vs historical regime)
   current_regime = detect_market_regime()  # BULL_LOW_RATES, BEAR_HIGH_RATES, etc.
   if regime_sample_size[current_regime] >= 50:
       regime_adjustment = regime_accuracy[current_regime] * 0.70 + overall_accuracy * 0.30
   else:
       regime_adjustment = regime_accuracy[current_regime] * 0.30 + overall_accuracy * 0.70

   # Performance trend extrapolation (if statistically significant)
   if trend_strength > 0.3:  # R² > 0.3
       extrapolated = current_accuracy + (trend_slope * 0.5_years)
       trend_adjusted = current_accuracy * 0.70 + extrapolated * 0.30
   else:
       trend_adjusted = current_accuracy

   # Human override penalty
   if override_rate > 0.40:
       override_penalty = 0.70
   elif override_rate > 0.20:
       override_penalty = 0.85
   else:
       override_penalty = 1.00

   # Confidence interval (Wilson score for statistical robustness)
   # See DD-008 for full implementation
   if sample_size == 0:
       confidence_interval = 0.5
   else:
       z = 1.96
       p = credibility
       n = sample_size
       denominator = 1 + z**2 / n
       center = (p + z**2 / (2 * n)) / denominator
       margin = z * sqrt((p * (1 - p) / n + z**2 / (4 * n**2))) / denominator
       lower = max(0.0, center - margin)
       upper = min(1.0, center + margin)
       confidence_interval = (upper - lower) / 2

   # Final credibility score
   credibility_score = (
       base_accuracy *
       temporal_weight *
       regime_adjustment *
       trend_adjusted *
       override_penalty
   )
   ```

2. Compute credibility differential with confidence intervals:

   ```python
   differential = abs(agent_A_credibility - agent_B_credibility)

   # Ensure differential exceeds confidence intervals (statistically significant)
   min_differential_required = max(
       0.25,
       agent_A_confidence_interval + agent_B_confidence_interval
   )
   ```

3. If differential > min_differential_required:

   - Auto-resolve to higher credibility agent's position
   - Mark as "facilitator-resolved" (binding, not provisional)
   - Document reasoning including:
     - Credibility scores (with confidence intervals)
     - Regime-specific performance
     - Performance trends
     - Override rates
     - Context match quality
   - Notify both agents of resolution
   - Track outcome for credibility system validation

4. If differential < min_differential_required:
   - Escalate to Level 3 (human arbitration)
   - Include comprehensive credibility analysis in escalation package
   - Provide regime-specific context and trend information

**Requirements for Auto-Resolution**:

- Minimum 15 historical data points per agent in similar context
- Clear credibility differential (>0.25, dynamic: max(0.25, CI_A + CI_B))
- No critical-path blocking status (those escalate to human)
- Both agents provided evidence in good faith

#### Level 4: Fallback Conservative Default

**Trigger Conditions**:

- Human arbitration (Level 3) timeout (6 hours)
- OR expert queue full (>3 concurrent debates)
- OR expert explicitly unavailable

**Process**:

1. **Identify Conservative Position**:

   - Compare positions on risk spectrum
   - Select most cautious interpretation:
     - Lowest price target
     - Highest risk assessment
     - Most conservative assumptions
     - Most skeptical view
   - Use decision tree if positions not directly comparable

2. **Apply Provisional Resolution**:

   - Mark debate as "provisional - conservative default"
   - Document rationale for conservative choice
   - Set override window: Until next gate
   - Add to gate review queue

3. **Enable Pipeline Continuation**:

   - Downstream agents receive provisional resolution
   - Analyses proceed with conservative assumption
   - Flag dependent calculations for potential revision

4. **Track for Review**:
   - Add to "provisional decisions" list
   - Display at next human gate with context
   - Enable override with downstream impact check
   - Learn from eventual human decision

### Workload-Aware Debate Routing

**Queue Management**:

- Monitor expert workload (current debates in progress)
- Enforce limits: Max 3 concurrent debates per expert
- Display load indicator in dashboard (e.g., "2/3 debates")

**Routing Logic by Priority**:

1. **Critical-Path Blocking** (highest priority):

   - If queue <3: Immediate routing to expert
   - If queue full (3/3): Force auto-resolution via credibility OR apply conservative default
   - Never defer critical-path debates

2. **Valuation Impact** (medium priority):

   - If queue <3: Add to queue in arrival order
   - If queue full: Apply credibility auto-resolution if possible, else defer to next gate

3. **Supporting Analysis** (lowest priority):
   - If queue <3: Add to queue
   - If queue full: Defer to next gate for review
   - OR auto-resolve via credibility if applicable

**Overflow Handling**:

- When expert queue full (3/3) and new debate arrives:
  1. Check if credibility-weighted auto-resolution applicable
  2. If yes, resolve automatically (doesn't enter queue)
  3. If no, check priority:
     - Critical-path: Apply conservative default (Level 4)
     - Valuation/Supporting: Defer to next gate

### Provisional Decision Tracking

**Tracking Mechanism**:

- Maintain list of all provisional resolutions
- For each provisional decision, track:
  - Debate ID and topic
  - Conservative position applied
  - Alternative positions considered
  - Rationale for conservative choice
  - Override window deadline (next gate)
  - Downstream dependencies

**Gate Review Integration**:

- At each subsequent gate, display:
  - Count: "X provisional decisions require review"
  - Summary of each provisional debate
  - Agent positions and credibility scores
  - Facilitator's conservative default rationale

**Human Actions at Review**:

1. **Confirm**: Accept conservative default → becomes final resolution
2. **Override**: Select different position → check downstream impact
3. **Request Re-debate**: Trigger new debate with additional context

**Override Impact Analysis**:

- If human overrides provisional decision:
  1. Identify analyses that used provisional assumption
  2. Flag for potential revision
  3. Re-run critical calculations if needed
  4. Update confidence scores
  5. Propagate changes through dependency chain

### Memory-Enhanced Facilitation

The Debate Facilitator leverages the memory system to:

- Pre-load relevant historical debates
- Surface precedents for similar disagreements
- Weight agent positions by track record
- Identify patterns in past resolutions
- Learn optimal debate structures
- **Retrieve credibility scores for auto-resolution**
- **Track fallback accuracy over time**
- **Learn which positions tend to be more accurate**

**Historical Context Integration**:

- Similar past debates and outcomes
- Pattern success rates supporting each position
- Agent credibility in specific contexts
- Cautionary examples from memory
- **Fallback resolution accuracy tracking**
- **Human override patterns for calibration**

---

## Related Documentation

- [System Overview](./01-system-overview.md) - Overall architecture
- [Memory System](./02-memory-system.md) - Historical context for coordination
- [Specialist Agents](./03-agents-specialist.md) - Agents being coordinated
- [Support Agents](./04-agents-support.md) - Infrastructure support
- [Collaboration Protocols](./07-collaboration-protocols.md) - Communication standards
