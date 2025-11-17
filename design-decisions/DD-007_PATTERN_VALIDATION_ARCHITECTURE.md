# Pattern Validation Architecture: 3-Tier Statistical Validation

**Status**: Implemented
**Date**: 2025-11-17
**Decider(s)**: System Architect
**Related Docs**: [Learning Systems](../docs/learning/01-learning-systems.md), [Memory System](../docs/architecture/02-memory-system.md), [Knowledge Base Agent](../docs/architecture/04-agents-support.md)
**Related Decisions**: DD-001 (Gate 6 Learning Validation)

---

## Context

v2.0 pattern detection used same dataset for discovery and validation → circular logic amplifying false patterns.

**Problem Flow**:
1. Pattern detected: "Tech CEO changes → underperformance" (3 occurrences, 0.7 correlation)
2. Pattern broadcast to all agents
3. Agents apply pattern → adjust estimates down
4. Lower conviction → smaller positions → worse relative outcomes
5. Outcome tracked as "pattern confirmed" → correlation increases to 0.85
6. **Self-fulfilling prophecy strengthens false pattern**

**Statistical Flaws**:
- No independent hold-out set (in-sample testing only)
- Data leakage (agents aware of pattern during analysis)
- No baseline comparison (no tracking what happens without pattern)
- Survivorship bias (rejected patterns disappear, false positive rate unknown)

Critical for MVP - prevents systematic bias amplification.

---

## Decision

**Implement 3-tier statistical validation requiring patterns pass ALL tests before agent use: (1) hold-out validation, (2) blind testing, (3) control group comparison.**

Patterns progress through lifecycle: candidate → statistically_validated → human_approved (Gate 6) → active. Unvalidated patterns quarantined, never broadcast to agents.

---

## Options Considered

### Option 1: Hold-Out Validation Only

**Description**: Chronological train/val/test split (70%/15%/15%), validate on unseen data

**Pros**:
- Standard ML best practice
- Prevents overfitting to training data
- Simple to implement
- Low computational cost

**Cons**:
- Doesn't prevent agent awareness contamination
- No measurement of actual decision impact
- Can't detect self-fulfilling prophecies
- Missing baseline comparison

**Estimated Effort**: Low (1-2 weeks)

---

### Option 2: Blind Testing Protocol

**Description**: Shadow tracking - calculate outcomes with/without pattern, agents unaware

**Pros**:
- Prevents agent behavior contamination
- Measures actual decision impact
- Detects self-fulfilling prophecies
- Real-world validation

**Cons**:
- Requires 6-month evaluation period
- Double computation (with/without pattern)
- Delayed pattern deployment
- Complex shadow analysis infrastructure

**Estimated Effort**: Medium (3-4 weeks)

---

### Option 3: 3-Tier Combined Validation (SELECTED)

**Description**: Require patterns pass (1) hold-out validation, (2) blind testing, (3) statistical significance vs control group

**Pros**:
- Comprehensive bias prevention (circular logic, self-fulfilling, spurious correlation)
- High confidence in validated patterns (multi-stage filtering)
- Audit trail for validation decisions
- Aligns with scientific rigor standards

**Cons**:
- Longest validation time (6+ months)
- Most complex implementation
- Highest computational cost
- Aggressive filtering (30-50% pass rate expected)

**Estimated Effort**: High (6-8 weeks, Phase 3)

---

## Rationale

Selected Option 3 because:

**Complementary Validation Methods**:
- Hold-out prevents overfitting (statistical validity)
- Blind testing prevents agent contamination (operational validity)
- Control groups measure actual improvement (decision validity)
- Each catches different failure modes

**Risk Mitigation**:
- False patterns cause systematic bias → compounds over time → high cost
- Conservative approach justified (better reject true pattern than accept false one)
- 30-50% pass rate acceptable (quality over quantity)

**System Principles**:
- "Rigorous validation over fast deployment" (principle #3)
- "Anti-confirmation bias by design" (principle #7)
- Aligns with Gate 6 human oversight philosophy

**Tradeoffs Acceptable**:
- 6-month delay tolerable (learning is long-term optimization)
- Computational cost small vs analyst salaries
- Complexity managed through modular implementation

---

## Consequences

### Positive Impacts

- **Bias elimination**: Circular validation loops prevented by design
- **Pattern quality**: Only statistically robust patterns reach agents
- **Trust**: Rigorous validation builds user confidence in system recommendations
- **Auditability**: Complete validation trail for regulatory compliance
- **Learning efficiency**: No wasted effort learning false patterns

### Negative Impacts / Tradeoffs

- **Learning delay**: 6+ months from discovery to deployment (vs immediate in v1.0)
- **Pattern scarcity**: 50-70% rejection rate → fewer patterns available
- **Computational cost**: 3x processing (training + validation + test sets)
- **Implementation complexity**: Shadow analysis infrastructure, A/B testing framework
- **Storage overhead**: Track validation metadata, shadow results, control group outcomes

### Affected Components

- **Learning Engine**: Validation pipeline, lifecycle management
- **Knowledge Base Agent**: Pattern status tracking (candidate/validated/approved/active), quarantine mechanism
- **All Specialist Agents**: Only consume validated+approved patterns
- **Memory System**: Store validation metadata (test dates, p-values, accuracy scores)
- **Human Interface**: Gate 6 validation dashboard shows test results
- **Report Writer**: Document pattern validation history in investment memos

---

## Implementation Notes

### Pattern Lifecycle

```text
Discovery → Candidate → Hold-Out Test → Blind Test → Control Test →
Statistically Validated → Gate 6 Review → Human Approved → Active
                ↓              ↓              ↓              ↓
           (rejected)     (rejected)     (rejected)     (rejected)
```

### Validation Thresholds

**Hold-Out Validation**:
- Min validation occurrences: 3
- Min validation correlation: 0.65
- Performance degradation: <20% vs training accuracy
- Pass criteria: ALL conditions met

**Blind Testing**:
- Evaluation period: 6 months
- Min comparisons: 10
- Improvement threshold: Pattern helps >1.5x more than hurts
- Pass criteria: pattern_helped > pattern_hurt * 1.5

**Control Group Testing**:
- Duration: 6 months concurrent with blind testing
- Statistical test: Two-sample t-test
- Significance level: p < 0.05
- Effect size: Treatment mean > Control mean
- Pass criteria: Statistically significant improvement

### Core Implementation

```python
class PatternValidationPipeline:
    def __init__(self):
        self.training_split = 0.7
        self.validation_split = 0.15
        self.test_split = 0.15

    def validate_pattern(self, candidate_pattern):
        """3-tier validation pipeline"""

        # Tier 1: Hold-out validation
        holdout_result = self.holdout_validation(candidate_pattern)
        if not holdout_result.passes:
            candidate_pattern.status = 'rejected_holdout'
            self.log_rejection(candidate_pattern, reason='no_generalization')
            return ValidationVerdict.REJECT

        # Tier 2: Blind testing (6 months)
        blind_result = self.blind_testing(candidate_pattern, months=6)
        if not blind_result.passes:
            candidate_pattern.status = 'rejected_blind'
            self.log_rejection(candidate_pattern, reason='contamination_detected')
            return ValidationVerdict.REJECT

        # Tier 3: Control group (concurrent with blind)
        control_result = self.control_group_test(candidate_pattern, months=6)
        if not control_result.passes:
            candidate_pattern.status = 'rejected_statistical'
            self.log_rejection(candidate_pattern, reason='no_significant_improvement')
            return ValidationVerdict.REJECT

        # All tests passed
        candidate_pattern.status = 'statistically_validated'
        candidate_pattern.validation_metadata = {
            'holdout_accuracy': holdout_result.correlation,
            'blind_test_score': blind_result.improvement_ratio,
            'statistical_significance': control_result.p_value,
            'validated_date': datetime.now()
        }

        # Queue for Gate 6 human review
        self.queue_for_gate6(candidate_pattern)
        return ValidationVerdict.APPROVE

    def holdout_validation(self, pattern):
        """Chronological train/val/test split"""
        all_data = self.kb.get_historical_data(pattern.timeframe)
        train, val, test = self.split_chronologically(all_data)

        # Pattern already trained, test on validation set
        val_correlation = pattern.test_on_data(val)
        test_correlation = pattern.test_on_data(test)

        passes = (
            val_correlation > 0.65 and
            test_correlation > 0.65 and
            test_correlation > pattern.training_correlation * 0.8  # <20% degradation
        )

        return ValidationResult(
            passes=passes,
            correlation=test_correlation,
            sample_size=len(test)
        )
```

### Integration with Gate 6

**Modified Gate 6 Input Package**:

```yaml
New Patterns Discovered:
  - pattern_name: string
    status: statistically_validated  # New requirement
    validation_results:
      holdout_accuracy: float
      blind_test_score: float
      p_value: float
      validation_sample_size: int
    occurrences: int
    correlation: float
    proposed_action: string
```

**Gate 6 Validation Criteria** (added to existing criteria):
- **Require statistical validation**: Patterns must have status='statistically_validated'
- **Review validation scores**: Human checks p-value, sample size, test results
- **Override option**: Human can reject statistically valid pattern if domain knowledge contradicts

### Testing Requirements

1. **Hold-out split correctness**: Chronological ordering preserved, no data leakage
2. **Blind testing isolation**: Agents unaware of pattern during shadow analysis
3. **Control group randomization**: Treatment/control assignment truly random
4. **Quarantine enforcement**: Unvalidated patterns never broadcast to agents
5. **Lifecycle transitions**: Pattern status updates correctly through pipeline
6. **Gate 6 integration**: Validation metadata displayed in approval UI

**Rollback Strategy**: Revert to Gate 6-only validation (DD-001), disable statistical validation pipeline.

**Estimated Implementation Effort**: 6-8 weeks (Phase 3)

**Dependencies**:
- Pattern detection system (Learning Engine) - Phase 2
- Gate 6 validation dashboard (Human Interface) - Phase 2
- Shadow analysis framework - Phase 3
- A/B testing infrastructure - Phase 3

---

## Open Questions

None - specification complete, ready for implementation.

**Blocking**: No

---

## References

- [Flaw #3: Pattern Validation Confirmation Bias Loop](../docs/design-flaws/resolved/03-pattern-validation.md) - Original problem analysis
- [DD-001: Gate 6 Learning Validation](DD-001_GATE_6_LEARNING_VALIDATION.md) - Human oversight layer
- [Learning Systems](../docs/learning/01-learning-systems.md) - Anti-confirmation bias mechanisms
- [Knowledge Base Agent](../docs/architecture/04-agents-support.md) - Pattern storage and lifecycle

---

## Status History

| Date       | Status      | Notes                                    |
| ---------- | ----------- | ---------------------------------------- |
| 2025-11-17 | Proposed    | Initial design from Flaw #3 analysis     |
| 2025-11-17 | Approved    | Approved by system architect             |
| 2025-11-17 | Implemented | Added to v2.0 design, resolves Flaw #3   |

---

## Notes

**Why 3 tiers vs just hold-out?** Each tier catches different failure mode:
- Hold-out: Overfitting to training data
- Blind: Agent behavior contamination, self-fulfilling prophecies
- Control: Actual decision improvement vs baseline

**Expected pass rates**:
- Hold-out: ~70% (standard ML)
- Blind testing: ~60% of hold-out survivors (catches contamination)
- Control groups: ~70% of blind survivors (statistical significance)
- **Overall**: ~30% of candidates become active patterns (aggressive filtering intentional)

**Validation time acceptable**: Learning is long-term optimization. 6-month delay justified by bias prevention. False pattern causes systematic error → compounds over years → far more costly than delayed deployment.

**Future optimization**: After production data available, could reduce validation period to 3 months if sufficient sample size achieved earlier. Conservative 6-month default for MVP.
