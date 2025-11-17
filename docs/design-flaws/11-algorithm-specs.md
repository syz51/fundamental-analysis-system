# Flaw #11: Missing Algorithm Specifications

**Status**: 🔴 ACTIVE
**Priority**: Critical
**Impact**: Blocks implementation of key automation features
**Phase**: Phase 2 (Months 3-4)

---

## Problem Description

Three critical algorithms described in design docs but lack complete specifications, preventing implementation:

1. **Downstream Impact Calculation** (debate overrides)
2. **Post-Mortem Priority Formula** (failure analysis queue)
3. **Agent Dependency Resolution** (parallel execution scheduling)

### Sub-Issue C1: Downstream Impact Calculation Missing

**Files**:
- `docs/operations/02-human-integration.md:266-269`
- `docs/operations/01-analysis-pipeline.md:147-150`

**Problem**: When humans override provisional debate resolutions, system should calculate "downstream impact" and re-run affected analyses. No algorithm specified.

**Current State**:
```yaml
# human-integration.md L266-269
If Override Selected:
  Downstream Impact Analysis:
    - Valuation model: Re-run required (5min)
    - Target price: Will increase ~$12-15  # HOW CALCULATED?
    - Risk assessment: Confidence score will adjust  # WHAT FORMULA?
```

**Missing Specifications**:
- Dependency graph construction algorithm
- Impact propagation calculation methodology
- Threshold for "required" vs "optional" re-run
- Time estimation methodology (why "5min"?)
- Price impact calculation formula

**Example Scenario**:
```text
Debate: Financial Analyst vs Strategy Analyst on margin assumptions
  Financial: "25% operating margin" (conservative)
  Strategy: "30% operating margin" (optimistic)

Provisional Resolution: 25% (conservative default)
Pipeline continues with 25% → DCF model → Target price $85

Human Override: "Use 28% based on management guidance"

Downstream Impact Calculation NEEDED:
  1. Identify dependencies: Which analyses used 25% assumption?
     - DCF valuation model
     - Sensitivity analysis
     - Risk assessment scoring
     - Peer comparison context

  2. Calculate impact magnitude:
     - DCF: +12% target price ($85 → $95)
     - Sensitivity: New base case scenario
     - Risk: Confidence score +0.05

  3. Determine re-run necessity:
     - Target price delta >10% → Re-run REQUIRED
     - Risk score delta <0.10 → Update only (no re-run)

  4. Estimate time to re-run:
     - DCF: 5 min (single model recalculation)
     - Sensitivity: 10 min (6 scenarios)
     - Total: 15 min
```

### Sub-Issue M3: Post-Mortem Priority Formula Undefined

**Files**:
- `docs/learning/01-learning-systems.md:87-115`
- `design-decisions/DD-006`

**Problem**: Post-mortems "prioritized by deviation severity" but no formula for calculating priority when multiple post-mortems queued.

**Current State**:
```yaml
# DD-006: "max 5 concurrent, prioritized by deviation severity"
# learning-systems.md L84-86
Trigger: abs(actual - predicted) / predicted > 0.30
```

**Missing Specification**: Priority calculation when multiple triggered

**Example Ambiguity**:
```text
Queue at Year-End Checkpoint:

Stock A (MSFT):
  Predicted: +20% return, Actual: -50%
  Deviation: |(-50 - 20)|/20 = 350%
  Investment: $100K position → Lost $50K

Stock B (Small cap):
  Predicted: +5% return, Actual: -30%
  Deviation: |(-30 - 5)|/5 = 700%  # LARGER PERCENTAGE
  Investment: $10K position → Lost $3K

Which has priority?
  - Stock B has larger % deviation (700% vs 350%)
  - Stock A has larger absolute loss ($50K vs $3K)
  - Stock A has larger portfolio impact (5% vs 0.3%)
```

**Needed**: Priority formula considering:
- Percentage deviation
- Absolute financial impact
- Portfolio weight
- Systemic vs idiosyncratic failure

### Sub-Issue G5: Dependency Resolution Algorithm Missing

**Files**: `docs/architecture/05-agents-coordination.md`

**Problem**: Analysis pipeline shows dependencies (Valuation needs Financial + Business + Strategy) but no algorithm for scheduling parallel execution.

**Current State**: Pipeline diagram shows dependencies but no scheduling logic

**Missing Specifications**:
- Dependency graph construction
- Critical path calculation
- Parallel execution optimizer
- Resource allocation across agents
- Deadlock detection

**Example Scenario**:
```text
Analysis A (AAPL):
  Screening ─→ Business ──┐
          └──→ Financial ─┼──→ Valuation ──→ Report
              └──→ Strategy ┘

Analysis B (MSFT) - parallel:
  Screening ─→ Business ──┐
          └──→ Financial ─┼──→ Valuation ──→ Report
              └──→ Strategy ┘

Shared Resources:
  - Financial Analyst (1 instance, can handle 2 concurrent)
  - Valuation Agent (1 instance, can handle 1 at a time)

Scheduling Questions:
  1. Start both screenings in parallel? YES
  2. Start both business research in parallel? YES (no shared resource)
  3. Start both financial analysis in parallel? YES (can handle 2)
  4. Start both valuations in parallel? NO (bottleneck - sequential)

Optimal Schedule:
  T0-T2: AAPL + MSFT Screening (parallel)
  T2-T4: AAPL + MSFT Business (parallel)
  T4-T6: AAPL + MSFT Financial (parallel, within capacity)
  T6-T7: AAPL Valuation (sequential - MSFT waits)
  T7-T8: MSFT Valuation (after AAPL completes)

Critical Path: Screening → Business → Financial → Valuation (longest path)

MISSING: Algorithm to compute this schedule automatically
```

---

## Impact Assessment

| Sub-Issue | Severity | Blocks                           | Workaround   |
| --------- | -------- | -------------------------------- | ------------ |
| C1        | CRITICAL | Debate override automation       | Manual calc  |
| M3        | MEDIUM   | Post-mortem queue optimization   | FIFO queue   |
| G5        | MEDIUM   | Parallel execution optimization  | Serial runs  |

**Aggregate Impact**:
- C1 blocks Phase 2 debate resolution Level 4-5 implementation
- Manual workarounds defeat automation purpose
- Suboptimal performance (serial vs parallel execution)

---

## Recommended Solution

### C1: Downstream Impact Calculation Algorithm

#### Step 1: Build Dependency Graph

```python
class DependencyGraph:
    """Track analysis dependencies for impact calculation"""

    def __init__(self):
        self.graph = {}  # {node_id: [dependent_node_ids]}
        self.assumptions = {}  # {node_id: {assumption_key: value}}

    def add_dependency(self, parent_id, child_id, assumption_used):
        """Record that child depends on parent's assumption"""
        if parent_id not in self.graph:
            self.graph[parent_id] = []
        self.graph[parent_id].append({
            'child': child_id,
            'assumption': assumption_used
        })

    def find_affected_nodes(self, changed_assumption):
        """Find all analyses using this assumption"""
        affected = []
        for node_id, deps in self.graph.items():
            for dep in deps:
                if dep['assumption'] == changed_assumption:
                    affected.append(dep['child'])
                    # Recursively find downstream
                    affected.extend(
                        self.find_affected_nodes(dep['child'])
                    )
        return list(set(affected))  # Deduplicate
```

#### Step 2: Calculate Impact Magnitude

```python
class ImpactCalculator:
    """Calculate downstream impact of assumption changes"""

    IMPACT_THRESHOLDS = {
        'target_price': 0.10,  # >10% change requires re-run
        'confidence_score': 0.15,  # >0.15 change requires re-run
        'rating': 1,  # Any rating change requires re-run
        'risk_score': 0.10,  # >0.10 change requires re-run
    }

    def calculate_impact(self,
                         old_assumption,
                         new_assumption,
                         affected_analyses):
        """Calculate impact of assumption change"""

        impacts = []
        for analysis_id in affected_analyses:
            # Get analysis type
            analysis = self.get_analysis(analysis_id)

            # Calculate impact based on type
            if analysis.type == 'valuation':
                impact = self._valuation_impact(
                    analysis, old_assumption, new_assumption
                )
            elif analysis.type == 'risk_assessment':
                impact = self._risk_impact(
                    analysis, old_assumption, new_assumption
                )

            impacts.append({
                'analysis_id': analysis_id,
                'type': analysis.type,
                'old_value': analysis.current_result,
                'estimated_new_value': impact.estimated_result,
                'delta': impact.delta,
                'requires_rerun': impact.delta > self.IMPACT_THRESHOLDS.get(
                    analysis.output_metric, 0.10
                )
            })

        return ImpactReport(
            changed_assumption=new_assumption,
            affected_count=len(impacts),
            impacts=impacts,
            total_rerun_time=self._estimate_rerun_time(impacts),
            high_impact_count=sum(1 for i in impacts if i['requires_rerun'])
        )

    def _valuation_impact(self, analysis, old_val, new_val):
        """Estimate valuation impact (linear approximation)"""
        # For margin changes, use DCF sensitivity
        if old_val.metric == 'operating_margin':
            # Typical sensitivity: 1% margin → 8-12% price change
            margin_delta = new_val.value - old_val.value
            price_delta_pct = margin_delta * 10  # 10x multiplier

            return ImpactEstimate(
                estimated_result=analysis.result * (1 + price_delta_pct/100),
                delta=abs(price_delta_pct/100),
                confidence=0.70  # Linear approximation has limitations
            )
```

#### Step 3: Determine Re-Run Strategy

```python
class RerunScheduler:
    """Decide what to re-run and when"""

    def plan_reruns(self, impact_report):
        """Create re-run plan based on impact"""

        # Separate required vs optional
        required = [i for i in impact_report.impacts if i['requires_rerun']]
        optional = [i for i in impact_report.impacts if not i['requires_rerun']]

        # Prioritize by impact magnitude
        required.sort(key=lambda x: x['delta'], reverse=True)

        # Build re-run plan
        plan = RerunPlan(
            required_reruns=required,
            optional_updates=optional,
            execution_strategy=self._determine_strategy(required),
            estimated_time=impact_report.total_rerun_time,
            blocking=len(required) > 0
        )

        return plan

    def _determine_strategy(self, required_reruns):
        """Choose serial vs parallel execution"""
        if len(required_reruns) <= 2:
            return 'serial'  # Fast enough sequentially
        elif self._can_parallelize(required_reruns):
            return 'parallel'  # Use multiple workers
        else:
            return 'serial'  # Dependencies prevent parallelization
```

### M3: Post-Mortem Priority Formula

```python
class PostMortemPriority:
    """Calculate priority for post-mortem queue"""

    WEIGHTS = {
        'deviation_pct': 0.25,
        'absolute_loss': 0.35,
        'portfolio_impact': 0.30,
        'systemic_risk': 0.10
    }

    def calculate_priority(self, outcome):
        """Compute priority score (0-100)"""

        # Normalize each factor to 0-100
        factors = {
            'deviation_pct': self._normalize_deviation(
                outcome.deviation_pct
            ),
            'absolute_loss': self._normalize_loss(
                outcome.absolute_loss
            ),
            'portfolio_impact': self._normalize_portfolio(
                outcome.portfolio_pct
            ),
            'systemic_risk': self._assess_systemic(
                outcome
            )
        }

        # Weighted sum
        priority = sum(
            factors[key] * self.WEIGHTS[key] * 100
            for key in factors
        )

        return PostMortemQueueEntry(
            stock_id=outcome.stock_id,
            priority=priority,
            factors=factors,
            queued_at=datetime.now()
        )

    def _normalize_deviation(self, deviation_pct):
        """Sigmoid normalization for deviation %"""
        # 50% deviation → 0.50, 100% → 0.75, 300% → 0.95
        return 1 / (1 + math.exp(-0.02 * (deviation_pct - 50)))

    def _normalize_loss(self, absolute_loss):
        """Log scale for absolute loss"""
        # $1K → 0.30, $10K → 0.60, $100K → 0.90
        if absolute_loss <= 0:
            return 0
        return min(math.log10(absolute_loss / 1000) / 3, 1.0)

    def _assess_systemic(self, outcome):
        """Check if failure indicates systemic issue"""
        # High if multiple stocks in same sector failed
        sector_failures = self.count_sector_failures(
            outcome.sector,
            lookback_days=90
        )
        return min(sector_failures / 5, 1.0)  # Max at 5 failures
```

### G5: Dependency Resolution Algorithm

```python
class DependencyResolver:
    """Schedule parallel agent execution with dependencies"""

    def __init__(self):
        self.dependency_graph = nx.DiGraph()
        self.agent_capacity = {
            'screening': 5,
            'business': 3,
            'financial': 2,
            'strategy': 3,
            'valuation': 1  # Bottleneck
        }

    def build_schedule(self, analyses):
        """Create optimal execution schedule"""

        # Build dependency graph for all analyses
        for analysis in analyses:
            self._add_analysis_deps(analysis)

        # Find critical path
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
```

---

## Implementation Plan

### Phase 1 (Week 1-2): C1 - Downstream Impact

- [ ] Implement `DependencyGraph` class
- [ ] Build `ImpactCalculator` with valuation/risk impact formulas
- [ ] Create `RerunScheduler` with strategy selection
- [ ] Add dependency tracking to debate resolution flow
- [ ] Update human-integration.md with algorithm specs

### Phase 2 (Week 3): M3 - Post-Mortem Priority

- [ ] Implement `PostMortemPriority` calculator
- [ ] Add normalization functions (deviation, loss, portfolio)
- [ ] Integrate with post-mortem queue system
- [ ] Update DD-006 with priority formula

### Phase 3 (Week 4): G5 - Dependency Resolution

- [ ] Implement `DependencyResolver` with NetworkX
- [ ] Add critical path calculation
- [ ] Create capacity-aware scheduler
- [ ] Benchmark parallel vs serial execution
- [ ] Update coordination-agents.md with algorithm

### Phase 4 (Week 5): Testing & Integration

- [ ] Test C1 with override scenarios
- [ ] Test M3 with multi-stock failure scenarios
- [ ] Test G5 with 5+ parallel analyses
- [ ] Integration testing across all three algorithms
- [ ] Performance benchmarking

---

## Success Criteria

### C1: Downstream Impact
- ✅ Correctly identifies all dependent analyses
- ✅ Impact estimation within 20% of actual (validated over 50 overrides)
- ✅ Re-run strategy completes within estimated time ±25%
- ✅ Zero missed dependencies (100% recall)

### M3: Post-Mortem Priority
- ✅ Highest absolute losses prioritized consistently
- ✅ Systemic failures identified (sector clustering detected)
- ✅ Queue processing order aligns with human judgment in >80% cases
- ✅ All post-mortems completed within SLA

### G5: Dependency Resolution
- ✅ Parallel execution achieves >2x speedup vs serial (5+ analyses)
- ✅ No deadlocks (100% successful completions)
- ✅ Critical path identified correctly (validated manually)
- ✅ Resource utilization >70% (agents not idle)

---

## Dependencies

- **Blocks**: Debate resolution Level 4-5 (C1), Post-mortem queue (M3), Parallel pipeline optimization (G5)
- **Depends On**: Debate protocol operational, Post-mortem system active, Agent coordination layer
- **Related Flaws**: #8 (Debate Deadlock), #9 (Negative Feedback)
- **Related DDs**: DD-003, DD-006

---

## Related Documentation

- [Human Integration](../../operations/02-human-integration.md)
- [Debate Protocols](../../architecture/07-collaboration-protocols.md)
- [Learning Systems](../../learning/01-learning-systems.md)
- [Agent Coordination](../../architecture/05-agents-coordination.md)
- [DD-006: Negative Feedback](../../../design-decisions/DD-006_NEGATIVE_FEEDBACK_SYSTEM.md)
