# Collaborative Intelligence Protocols

## Overview

This document defines the communication and collaboration protocols that enable agents to work together effectively, share knowledge, and collectively arrive at better decisions than any single agent could achieve alone.

---

## Basic Inter-Agent Messaging

### Message Structure

```json
{
  "from_agent": "financial_analyst",
  "to_agent": "valuation_agent",
  "message_type": "finding",
  "priority": "high",
  "content": {
    "finding": "Abnormal capex increase",
    "confidence": 0.85,
    "evidence": ["10-K page 45", "CFO commentary"],
    "impact": "Adjust FCF projections"
  },
  "timestamp": "2025-11-16T10:30:00Z",
  "requires_response": true
}
```

**Note**: Message structure is technology-agnostic. For message queue implementation details, reliability requirements, and technology selection, see [Tech Requirements](../implementation/02-tech-requirements.md).

### Message Types

**Finding**: Share analytical results

- Discovery from analysis
- Confidence level
- Supporting evidence
- Implications for other agents

**Request**: Ask for specific analysis

- Targeted query
- Scope and parameters
- Priority and deadline
- Context and rationale

**Challenge**: Dispute another agent's conclusion

- Disagreement with finding
- Basis for challenge
- Counter-evidence
- Request for clarification

**Confirmation**: Validate information

- Verify finding or data
- Cross-check assumption
- Seek agreement
- Build consensus

**Alert**: Urgent attention needed

- Material development
- Immediate action required
- Risk notification
- Deadline warning

---

## Data Handling Protocols

### Data Source Contradictions vs Agent Debates

This document focuses on **inter-agent collaboration protocols** (agent-to-agent communication and debates over analytical conclusions).

For **data source contradictions** (conflicting data from different providers like SEC vs Bloomberg), see:

- **[DD-010: Data Contradiction Resolution](../design-decisions/DD-010_DATA_CONTRADICTION_RESOLUTION.md)** - 4-level escalation system with source credibility
- **[Data Management](../operations/03-data-management.md)** - Operational procedures for contradiction resolution
- **[Memory System](./02-memory-system.md)** - SourceCredibility and DataContradiction nodes in knowledge graph

**Key Distinction**:

- **Agent debates** (this document): Disagreements over interpretation, methodology, or analytical conclusions between specialist agents
- **Data contradictions** (DD-010): Conflicting raw data from multiple external sources requiring source credibility evaluation

---

## Debate Protocol

### Challenge Format

```json
{
  "challenge_id": "CH-001",
  "challenger": "strategy_analyst",
  "challenged": "financial_analyst",
  "disputed_finding": "Management effectiveness",
  "challenge_basis": "ROI declining despite claims",
  "required_evidence": ["Historical ROI data", "Peer comparison"],
  "escalation_timer": 3600,
  "priority": "critical-path",
  "provisional_resolution": null
}
```

### 5-Level Tiered Escalation System

The debate protocol uses a tiered escalation approach with timeouts and fallback mechanisms to prevent pipeline deadlocks when humans are unavailable.

#### Level 1: Agent Direct Resolution (15min timeout)

**Process**:

1. Challenged agent acknowledges within 15 minutes
2. Agent provides evidence addressing challenge
3. Challenger evaluates response
4. If accepted → resolved, end debate
5. If rejected → escalate to Level 2

**Actions**:

- Confirm receipt of challenge
- Commit to response timeline
- Request clarification if needed
- Address challenge directly with evidence
- Acknowledge limitations
- Revise position if warranted

#### Level 2: Debate Facilitator Mediation (1hr timeout)

**Process**:

1. Debate Facilitator reviews both positions
2. Applies credibility scoring based on agent track records
3. If credibility differential >0.25 → auto-resolve to higher credibility position
4. If credibility differential <0.25 → escalate to Level 3
5. Documents reasoning and evidence considered

**Auto-Resolution Criteria**:

- Credibility gap threshold: 0.25 (or sum of confidence intervals, whichever is larger)
- Requires minimum 15 historical data points per agent for credibility calculation
- Credibility system evolves across implementation phases (see DD-008):

**Phase 2 (Months 3-4) - Simple Credibility**:

- **Base accuracy**: Overall domain-specific track record
- **Temporal weighting**: Exponential decay with 2-year half-life
- **Confidence intervals**: Wilson score intervals for statistical reliability
- Formula: `credibility = base_accuracy × temporal_weight`

**Phase 4 (Months 7-8) - Comprehensive Credibility** (adds):

- **Regime-specific accuracy** (30%): Performance in current market regime (bull/bear, rates, volatility)
- **Context matching** (30% weight if sufficient data): Multi-dimensional context (sector, metric, horizon, size, stage)
- **Performance trend**: Extrapolate improvement/degradation trajectory (if R² > 0.3)
- **Override penalty**: Credibility reduction if high human override rate (>20%)
- Requires minimum 50 data points for regime-specific scoring
- Formula: `credibility = base_accuracy × temporal_weight × regime_adjustment × trend_adjusted × override_penalty`

**Fallback**: If insufficient data or credibility differential below threshold → escalate to Level 3

#### Level 3: Human Arbitration - Gate 4 (6hr timeout)

**Process**:

1. Debate added to human queue with priority classification
2. Queue managed (max 3 concurrent per expert)
3. Human receives both positions with credibility scores and precedents
4. If human responds within 6 hours → binding resolution
5. If timeout → escalate to Level 4

**Priority Classification** (determines queue order):

- **Critical-path blocking**: Debates preventing immediate pipeline progress (highest)
- **Valuation impact**: Debates affecting DCF assumptions, price targets (medium)
- **Supporting analysis**: Background research disagreements (lowest)

**Queue Management**:

- Max concurrent debates per expert: 3
- Overflow handling: Auto-escalate to Level 4 or defer to next gate
- Load indicator displayed in dashboard

#### Level 4: Fallback Resolution (24hr timeout)

**Process**:

1. Conservative default logic applied automatically
2. Resolution marked as "provisional decision"
3. Pipeline continues (non-blocking)
4. Override window opens: Until next gate
5. Human can review and override at subsequent gates

**Conservative Default Logic**:

1. Identify most cautious position:
   - Lowest price target
   - Highest risk assessment
   - Most conservative assumptions
   - Most skeptical interpretation
2. Apply that position as provisional resolution
3. Document rationale in decision log
4. Flag for mandatory review at next gate

**Override Window**:

- Opens when fallback applied
- Closes at next human decision gate
- Human sees "X provisional decisions require review" at gate
- Actions: Confirm, Override (with rationale), Request re-debate

#### Level 5: Gate Review (at next decision point)

**Process**:

1. Next gate displays all provisional decisions requiring review
2. Human reviews fallback reasoning and agent positions
3. Options:
   - **Confirm**: Accept conservative default, becomes final
   - **Override**: Apply different resolution, check downstream impact
   - **Re-debate**: Trigger new debate with additional context
4. Final resolution propagated to all agents

**Downstream Impact Check**:

- If override changes key assumptions, flag dependent analyses
- Re-run affected calculations if needed
- Update confidence scores if cascading changes occur

### Downstream Impact Calculation Algorithm

When humans override provisional debate resolutions, the system must calculate downstream impact and re-run affected analyses. This algorithm specifies how to identify dependencies, estimate impact magnitude, and determine re-run requirements.

#### Algorithm Components

**1. Dependency Graph Construction**

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

**2. Impact Magnitude Calculation**

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

**3. Re-Run Strategy Determination**

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

#### Usage Example

```text
Debate: Financial Analyst vs Strategy Analyst on margin assumptions
  Financial: "25% operating margin" (conservative)
  Strategy: "30% operating margin" (optimistic)

Provisional Resolution: 25% (conservative default)
Pipeline continues with 25% → DCF model → Target price $85

Human Override: "Use 28% based on management guidance"

Downstream Impact Calculation:
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

### Escalation Timeouts Summary

| Level             | Timeout                     | Action if Exceeded                 |
| ----------------- | --------------------------- | ---------------------------------- |
| 1: Agent Direct   | 15min (ack), 1hr (evidence) | Escalate to Level 2                |
| 2: Facilitator    | 1hr                         | Escalate to Level 3                |
| 3: Human (Gate 4) | 6hr                         | Escalate to Level 4                |
| 4: Fallback       | 24hr (provisional)          | Continue with conservative default |
| 5: Gate Review    | Until next gate             | Override window closes             |

### Priority-Based Queue Management

**Queue Limits**:

- Single expert: Max 3 concurrent debates
- Overflow: Auto-resolve or defer based on priority

**Routing Logic**:

1. Critical-path debates → immediate attention (skip queue if <3)
2. Valuation debates → queue position based on arrival time
3. Supporting debates → defer to next gate if queue full

**Load Balancing** (future multi-expert):

- Round-robin assignment
- Expertise-based routing
- Workload-aware distribution

### Documentation Requirements

**For All Resolutions** (regardless of level):

- Final agreed/applied position
- Evidence considered
- Resolution level and method
- Confidence level
- Impact on analysis
- If provisional: Override window status

**Additional for Provisional Resolutions**:

- Conservative default rationale
- Alternative positions considered
- Review deadline (next gate)
- Downstream dependencies

---

## Memory-Enhanced Communication

### Enhanced Message Structure with Historical Context

```json
{
  "from_agent": "financial_analyst",
  "to_agent": "valuation_agent",
  "message_type": "finding_with_precedent",
  "priority": "high",
  "content": {
    "finding": "Abnormal capex increase",
    "confidence": 0.85,
    "evidence": ["10-K page 45", "CFO commentary"],
    "historical_context": {
      "similar_patterns": [
        {
          "company": "MSFT",
          "year": 2016,
          "outcome": "Cloud investment paid off"
        }
      ],
      "pattern_success_rate": 0.72,
      "my_accuracy_on_pattern": 0.81
    },
    "impact": "Adjust FCF projections with growth bias"
  },
  "timestamp": "2025-11-16T10:30:00Z",
  "requires_response": true
}
```

### Historical Context Fields

**Similar Patterns**:

- Past occurrences of same pattern
- Companies and timeframes
- Outcomes (positive/negative)
- Success rates

**Pattern Metadata**:

- Overall pattern success rate
- Agent's accuracy on this pattern
- Number of observations
- Confidence intervals

**Agent Credibility**:

- **Temporal decay**: Recent performance weighted heavily (exponential with 2-year half-life)
- **Market regime specificity**: Performance in current regime vs historical average
- **Context matching**: Accuracy in similar sector/metric/horizon/size/stage contexts
- **Performance trajectory**: Trend analysis showing improvement or degradation
- **Human override tracking**: Penalty applied if frequently overridden (>20% rate)
- **Confidence intervals**: Statistical significance based on sample size
- **Domain expertise weighting**: Relevance of agent specialization to current pattern

---

## Real-Time Collaborative Memory Building

**Note**: Code samples referenced here have been omitted from architecture docs. See `/examples/` directory for implementation examples.

### Collaborative Session Mechanics

**Shared Context Management**:

- Maintain common understanding across agents
- Track emerging insights in real-time
- Identify pattern candidates during analysis
- Alert agents to important cross-domain findings

**Cross-Validation**:

- Check findings against other agents' discoveries
- Strengthen patterns with multiple confirmations
- Identify contradictions early
- Build consensus incrementally

**Importance Filtering**:

- Broadcast high-importance findings (>0.8)
- Buffer medium-importance locally
- Discard low-value noise
- Adaptive thresholds based on context

**Synthesis Checkpoints**:

- Periodic consolidation of learnings
- Identify emerging patterns
- Surface contradictions for resolution
- Store intermediate insights

---

## Macro Analyst Broadcasts

### Purpose

Notify all agents of regime changes, major macro updates

### Trigger Events

1. **Regime Change** (confidence >80%):

   - Old regime → New regime transition detected
   - Example: BULL_LOW_RATES → BEAR_HIGH_RATES
   - **Priority: System-Critical** (Tier 0, bypasses queue)

2. **Major Fed Announcement**:

   - Rate change (25bps+)
   - Policy shift (QE/QT changes)
   - **Priority: System-Critical** (Tier 0, bypasses queue)

3. **Threshold Breach** (sustained >3 days):
   - Indicator moves to extreme percentile (>95th or <5th)
   - Example: VIX jumps to 40 (>95th percentile)
   - Priority: Normal (5min sync)

### Broadcast Message Format

```json
{
  "from_agent": "macro_analyst",
  "to_agent": "all",
  "message_type": "alert",
  "priority": "system_critical",
  "content": {
    "event_type": "regime_change",
    "old_regime": "BULL_LOW_RATES",
    "new_regime": "BEAR_HIGH_RATES",
    "confidence": 0.85,
    "implications": {
      "sector_favorability_changes": {
        "Technology": -15, // Score decreased 15pts
        "Healthcare": +10 // Score increased 10pts
      },
      "discount_rate_changes": {
        "Technology": 0.025, // +2.5% discount rate
        "Utilities": 0.015 // +1.5% discount rate
      }
    },
    "recommended_actions": [
      "Re-screen candidates with updated sector scores",
      "Recalculate DCF models with new discount rates",
      "Review in-progress analyses for regime sensitivity"
    ]
  },
  "requires_response": false,
  "timestamp": "2025-01-15T10:30:00Z"
}
```

### Agent Response Protocol

- **Screening Agent**: Re-weight candidates by new sector scores
- **Valuation Agent**: Update discount rates for in-progress DCF models
- **Financial/Business/Strategy Agents**: Note regime change in analysis context
- **Lead Coordinator**: Flag in-progress analyses for potential re-evaluation

### Human Notification

- Alert sent to Gates 1/2/5 dashboards
- Email notification (if configured)
- Updated macro report published within 2 hours

---

## Decision Meeting with Full Memory Context

### Decision Package Components

**Note**: Code samples referenced here have been omitted from architecture docs. See `/examples/` directory for implementation examples.

A complete decision package includes:

**Current Analysis**:

- All agent findings
- Confidence scores
- Supporting evidence
- Areas of uncertainty

**Historical Context**:

- Similar past decisions
- Success rates in this context
- Cautionary examples
- Lessons learned

**Agent Credibility**:

- **Comprehensive credibility scores**: Multi-factor calculation including recency, regime, context, trends, overrides
- **Track record summaries**: Overall and domain-specific accuracy with confidence intervals
- **Regime-specific performance**: Accuracy in current vs historical market regimes
- **Performance trends**: Improvement/degradation trajectories with statistical significance
- **Human override analysis**: Override rates and outcome validation
- **Context match quality**: Similarity of current analysis to agent's historical experience
- **Learning improvements**: Agent evolution and capability development over time

**Pattern Matches**:

- Relevant historical patterns
- Success/failure rates
- Applicability conditions
- Risk indicators

**Confidence Calibration**:

- Adjust scores for historical accuracy
- Apply learned bias corrections
- Quantify uncertainty
- Risk-adjusted recommendations

### Memory-Informed Recommendation

The system synthesizes:

- Credibility-weighted agent positions
- Historical precedent guidance
- Pattern match probabilities
- Risk factors from memory
- Confidence intervals with track record basis

---

## Debate Enhancement with Memory

### Pre-Debate Memory Synchronization

Before structured debates begin, the system ensures memory consistency using an **Atomic Sync-Lock Protocol**:

**Critical Sync Protocol**:

1. **Acquire Sync Lock**:

   - Pause write operations for all debate participants.
   - Prevents state drift between sync and snapshot.

2. **Force Sync All Participants** (<2 seconds):

   - Flush local working memory (L1) to central graph.
   - Ensures no stale local cache data.

3. **Create Memory Snapshot**:

   - Generate immutable snapshot ID (e.g., `snap_12345`).
   - All agents MUST reference this snapshot ID during debate.
   - **Lock Released** immediately after snapshot creation.

4. **Load Historical Context**:
   - Load context relative to the snapshot.
   - Relevant historical debates & precedents.

**Why Critical Sync Matters**: Without atomic locking, an agent could update its state (e.g., receive new price data) _after_ the sync but _before_ the debate logic runs, causing "hallucinated" disagreements where agents argue based on different versions of reality.

### Challenge with Historical Evidence

Challenges are strengthened by:

- Historical counter-examples
- Pattern accuracy rates
- Agent track records on topic
- Success rates of competing positions

### Resolution with Precedent

Conflict resolution considers:

- Similar historical conflicts
- Which position proved correct historically
- Agent credibility weighting
- Statistical likelihood based on patterns

### Post-Debate Synchronization

After debate resolution:

- Outcomes immediately synced to central knowledge graph
- All agents receive debate conclusions (high-priority sync)
- Updated credibility scores propagated
- Lessons learned added to institutional knowledge

---

## Related Documentation

- [System Overview](./01-system-overview.md) - Overall architecture
- [Memory System](./02-memory-system.md) - Knowledge graph supporting collaboration
- [Coordination Agents](./05-agents-coordination.md) - Debate facilitation
- [Specialist Agents](./03-agents-specialist.md) - Primary participants in collaboration
- [Technical Requirements](../implementation/02-tech-requirements.md#message-queue) - Message queue specifications for inter-agent communication
- [DD-002: Event-Driven Memory Sync](../design-decisions/DD-002_EVENT_DRIVEN_MEMORY_SYNC.md) - Priority-based messaging for debates
