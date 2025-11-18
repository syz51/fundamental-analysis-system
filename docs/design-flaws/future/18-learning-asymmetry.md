---
flaw_id: 18
title: Learning Asymmetry - Human Expertise Not Tracked
status: future
priority: medium
phase: 5
effort_weeks: 3
impact: Suboptimal human-AI task division
blocks: []
depends_on: ['Human gates operational', '#6 implementation']
domain: ['learning', 'human-gates']
related_flaws: ['#6']
discovered: 2025-11-17
---

# Flaw #18: Learning Asymmetry - Human Expertise Not Tracked

**Status**: 🔮 FUTURE (Related to Flaw #6)
**Priority**: Medium
**Impact**: Suboptimal human-AI task division, agents penalized but humans not learned from
**Phase**: Phase 5 (Months 9-12)

---

## Problem Description

**Files**:

- `docs/learning/02-feedback-loops.md:199-243`
- `docs/operations/02-human-integration.md:170-189`

**Problem**: Override rate tracked and used to penalize agent credibility, but NOT used to build human expertise profiles or improve routing.

**Current State**:

```yaml
# feedback-loops.md L199-243
override_rate = human_overrides / total_recommendations

if override_rate > 0.40:
    credibility_multiplier = 0.70  # 30% penalty
elif override_rate > 0.20:
    credibility_multiplier = 0.85  # 15% penalty

# human-integration.md L170-189 - Override data COLLECTED:
- override_rate by context (sector/metric/regime)
- override_outcome_accuracy
- override_reasons categorized

# BUT Flaw #6 explicitly notes:
# "NOT used to build human expertise profiles or optimize routing"
```

**Logic Trap**:

- Agents tracked comprehensively (credibility, regime, context)
- Humans tracked minimally (override rate only)
- Asymmetric: Penalize agents without learning where humans add value

**Example Asymmetry**:

```text
Agent A: Financial Analyst
  - Overall credibility: 0.75
  - Override rate: 0.35 → 15% penalty applied
  - Context: Tech sector valuations

Human Expert: Sarah (Tech Specialist)
  - Overrides Agent A in 8/10 tech valuations
  - Override accuracy: 0.90 (9/10 correct)
  - Context: Tech sector only

CURRENT: Agent A penalized globally
OPTIMAL: Route tech valuations to Sarah first, use Agent A for other sectors

System penalizes agent but doesn't learn Sarah's tech expertise
```

---

## Relationship to Flaw #6

This issue is a **subset of Flaw #6 (Static Human Expertise Routing)**, which is deferred to Phase 5.

**Flaw #6 Scope**:

- Dynamic human expertise profiling
- Adaptive routing based on performance
- Human credibility tracking by domain

**Flaw #18 Focus**: Specifically on the asymmetry between agent penalties and lack of human learning

---

## Impact Assessment

| Aspect            | Impact                                                 |
| ----------------- | ------------------------------------------------------ |
| Agent Credibility | Overly penalized (global penalty for local gaps)       |
| Human Utilization | Suboptimal (experts not routed to strength areas)      |
| System Learning   | One-sided (learn agent weaknesses not human strengths) |

**Severity**: MEDIUM (deferred because incremental improvement, not blocking MVP)

---

## Recommended Solution (Deferred to Phase 5)

When Flaw #6 implemented, add:

```python
class HumanExpertiseTracking:
    """Track human performance to complement agent credibility"""

    def track_override_accuracy(self, human_id, override_decision, outcome):
        """Track human override outcomes"""

        self.record_override(
            human_id=human_id,
            decision=override_decision,
            outcome=outcome,
            context={
                'sector': outcome.sector,
                'metric': override_decision.metric,
                'regime': self.get_current_regime()
            }
        )

    def get_human_credibility(self, human_id, context):
        """Human credibility score (parallel to agent credibility)"""

        overrides = self.get_overrides_by_context(human_id, context)

        if len(overrides) < 5:
            return 0.50  # Insufficient data

        correct = sum(1 for o in overrides if o.outcome_correct)

        return HumanCredibility(
            overall=correct / len(overrides),
            context_specific=self._context_breakdown(overrides),
            sample_size=len(overrides)
        )

    def optimal_routing(self, task, available_experts):
        """Route to agent vs human based on comparative advantage"""

        agent_credibility = self.get_agent_credibility(task)
        human_credibilities = [
            self.get_human_credibility(h, task.context)
            for h in available_experts
        ]

        best_human = max(human_credibilities, key=lambda h: h.overall)

        if best_human.overall > agent_credibility.overall + 0.15:
            # Human has clear advantage
            return RoutingDecision(
                route_to='human',
                expert=best_human.human_id,
                reason='human_expertise_advantage'
            )

        return RoutingDecision(
            route_to='agent',
            reason='agent_sufficient'
        )
```

---

## Implementation Plan

**Phase 5 (Months 9-12)** - Deferred pending Flaw #6 implementation

---

## Success Criteria (When Implemented)

- ✅ Human credibility tracked by context (sector/metric/regime)
- ✅ Routing considers human vs agent comparative advantage
- ✅ Override rate decreases as routing improves
- ✅ Agents not globally penalized for context-specific gaps

---

## Dependencies

- **Blocked By**: Flaw #6 (Static Human Expertise Routing) - UNRESOLVED
- **Depends On**: Human gate usage data (6+ months)
- **Related**: DD-004 (Human Gates), Feedback loops
