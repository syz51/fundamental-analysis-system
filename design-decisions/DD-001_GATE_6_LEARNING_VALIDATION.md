# Gate 6: Learning Validation System

**Status**: Implemented
**Date**: 2025-11-17
**Decider(s)**: System Architect
**Related Docs**: [Human Integration](../docs/operations/02-human-integration.md), [Learning Systems](../docs/learning/01-learning-systems.md)
**Related Decisions**: DD-002 (Event-Driven Memory Sync), DD-003 (Debate Deadlock Resolution)

---

## Context

v2.0 initial design had agents learning autonomously from outcomes with no human validation mechanism. System could:

- Store patterns with `occurrence > 3` and `correlation > 0.7` automatically
- Update agent credibility scores without oversight
- Apply lessons learned with no human review
- Propagate spurious correlations to all agents

**Risk**: Confirmation bias loop - false patterns reinforced, systematic errors compound, overfitting to recent regimes.

Critical flaw requiring immediate resolution before MVP.

---

## Decision

**Implemented Gate 6: Learning Validation gate to provide human oversight on all learning updates (patterns, credibility changes, lessons learned).**

Gate triggered monthly or after 50 new outcomes tracked. Human reviews learning package within 48hrs, can approve/reject/request more evidence. Unvalidated patterns quarantined (not used in decisions).

---

## Consequences

### Positive Impacts

- **Bias prevention**: Human catches spurious correlations before reinforcement
- **Trust**: Oversight on all learning builds user confidence
- **Quality**: Patterns validated for causal logic, not just correlation
- **Audit trail**: All learning decisions documented

### Negative Impacts / Tradeoffs

- **Learning delay**: Up to 30 days between pattern discovery and application
- **Human burden**: 2-12 hours/month in production (manageable)
- **Complexity**: Quarantine mechanism, validation UI, package preparation

### Affected Components

- **Learning Engine**: Pattern validation status, quarantine logic
- **Knowledge Base Agent**: Stores validated vs unvalidated patterns separately
- **Human Interface**: Validation dashboard, approval workflows
- **All Specialist Agents**: Only consume validated patterns
- **Memory System**: Tracks validation metadata

---

## Implementation Notes

### Gate 6 Specification

**Trigger**:

- Monthly OR after 50 new outcomes tracked (whichever first)

**Input Package**:

```yaml
New Patterns Discovered:
  - pattern_name: string
    occurrences: int
    correlation: float
    affected_sectors: list
    proposed_action: string
    confidence: enum[LOW, MEDIUM, HIGH]

Agent Credibility Changes:
  - agent: string
    domain: string
    old_score: float
    new_score: float
    reason: string
    sample_size: int

Lessons Learned:
  - lesson: string
    evidence: list[decision_ids]
    proposed_change: string
    confidence: float
```

**Human Actions**:

- Approve pattern → status='validated', broadcast to agents
- Reject pattern → status='rejected', archive permanently
- Request more evidence → status='probationary', require +3 occurrences
- Modify pattern → adjust thresholds/conditions, mark validated
- Override credibility → human judgment supersedes automated score
- Add caveats to lessons → context-specific application notes

**Timeout**:

- 48 hours for response
- Default action: Quarantine all (don't apply until validated)

### Validation Criteria

**Approve patterns if**:

- Logical causation mechanism exists
- Sufficient sample size (5+ occurrences)
- Consistent across market conditions
- Aligns with domain expertise
- No obvious confounding variables

**Reject patterns if**:

- Spurious correlation
- Too few data points (<5)
- Specific to unique historical event
- Contradicts fundamental principles
- Human has counter-evidence

### Core Implementation

```python
class LearningValidationGate:
    def __init__(self):
        self.validation_threshold = 50  # outcomes
        self.validation_interval_days = 30
        self.timeout_hours = 48

    def trigger_validation_gate(self):
        package = self.prepare_validation_package()
        response = self.human_interface.request_learning_validation(
            package, timeout_hours=self.timeout_hours
        )
        self.process_validation_response(response)

    def prepare_validation_package(self):
        since = self.last_validation_date
        return ValidationPackage(
            patterns=self.kb.get_unvalidated_patterns(since=since),
            credibility_changes=self.kb.get_credibility_updates(since=since),
            lessons=self.kb.get_lessons_learned(since=since)
        )

    def process_validation_response(self, response):
        # Approve patterns
        for pattern in response.approved_patterns:
            pattern.status = 'validated'
            self.kb.promote_pattern(pattern)
            self.broadcast_to_agents(pattern)

        # Reject patterns
        for pattern in response.rejected_patterns:
            pattern.status = 'rejected'
            self.kb.archive_pattern(pattern)

        # Probationary patterns
        for pattern in response.needs_more_evidence:
            pattern.status = 'probationary'
            pattern.required_occurrences += 3
```

**Testing Requirements**:

1. Pattern quarantine (unvalidated patterns not used in decisions)
2. Monthly trigger (30 days since last validation)
3. Outcome threshold trigger (50 new outcomes)
4. Approval workflow (pattern promoted and broadcast)
5. Rejection workflow (pattern archived, never used)
6. Probation workflow (requires additional occurrences)

**Rollback Strategy**: Disable automatic pattern storage, revert to manual pattern entry only.

**Estimated Implementation Effort**: 3-4 weeks (Phase 2)

**Dependencies**:

- Pattern detection system (Learning Engine)
- Validation UI dashboard (Human Interface)
- Quarantine storage (Knowledge Base Agent)

---

## Open Questions

**4 design parameters require finalization** - see Flaw #10:

1. Trigger priority logic (monthly vs 50 outcomes - which takes precedence?)
2. Human bandwidth capacity planning (auto-approval thresholds)
3. Probation duration (how long to wait for additional evidence?)
4. Statistical significance thresholds (p-value requirements by domain)

**Blocking**: No - basic Gate 6 functional with conservative defaults, optimization can follow

---

## References

- [Flaw #1: Missing Human Gate](../docs/design-flaws/resolved/01-missing-human-gate.md) - Original problem analysis
- [Gate 6 Open Parameters](../docs/design-flaws/10-gate-6-parameters.md) - Flaw #10 for unresolved questions
- [Human Integration](../docs/operations/02-human-integration.md) - Gate 6 in pipeline
- [Learning Systems](../docs/learning/01-learning-systems.md) - Learning architecture

---

## Status History

| Date       | Status      | Notes                                |
| ---------- | ----------- | ------------------------------------ |
| 2025-11-17 | Proposed    | Initial design from Flaw #1 analysis |
| 2025-11-17 | Approved    | Approved by system architect         |
| 2025-11-17 | Implemented | Gate 6 added to v2.0 design          |

---

## Notes

**Why async vs blocking?** Blocking gate would delay learning by 30+ days after discovery. Async allows immediate discovery, quarantine until validation, then batch review monthly. More efficient for human, safer for system.

**Quarantine mechanism critical**: Unvalidated patterns stored separately, never broadcast to agents. Only validated patterns influence decisions. Prevents false pattern application while awaiting review.

**Future optimization** (Flaw #10): Auto-approval for low-risk items (small credibility changes, high-confidence lessons) could reduce human burden 40-60% in production. Requires parameter tuning.
