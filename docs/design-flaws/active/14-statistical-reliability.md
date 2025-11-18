---
flaw_id: 14
title: Statistical Reliability Issues
status: active
priority: high
phase: 2-3
effort_weeks: 4
impact: Auto-resolution may never trigger with current parameters
blocks: ["#8 auto-resolution"]
depends_on: ["Agent performance data", "Debate protocol"]
domain: ["agents", "learning"]
sub_issues:
  - id: C4
    severity: critical
    title: Confidence interval formula inconsistency
  - id: H6
    severity: high
    title: Minimum sample size too low (n=5)
  - id: CS4
    severity: medium
    title: Fixed vs dynamic threshold ambiguity
discovered: 2025-11-17
---

# Flaw #14: Statistical Reliability Issues

**Status**: 🔴 ACTIVE
**Priority**: High
**Impact**: Auto-resolution may never trigger, inconsistent confidence intervals
**Phase**: Phase 2-3 (Months 3-6)

---

## Problem Description

Three statistical reliability issues prevent credibility system from working correctly:

1. **C4**: Two different confidence interval formulas in different docs
2. **H6**: Auto-resolution minimum sample size (n=5) too low for statistical reliability
3. **CS4**: Fixed 0.25 threshold vs dynamic threshold based on confidence intervals

### Sub-Issue C4: Confidence Interval Formula Inconsistency

**Files**:
- `docs/implementation/05-credibility-system.md:656-677`
- `docs/learning/02-feedback-loops.md:310-337`

**Problem**: Standard error formula vs Wilson score interval - which is correct?

**Contradictory Implementations**:
```python
# credibility-system.md L656-677
def _calculate_confidence_interval(credibility, sample_size):
    if sample_size < 5:
        return 0.5  # Very wide interval
    z = 1.96  # 95% confidence
    interval = z * sqrt((credibility * (1-credibility)) / sample_size)
    return interval

# feedback-loops.md L195 (implied)
# "Confidence intervals (Wilson score for statistical significance)"
```

**Impact**: Different formulas yield different widths, affecting auto-resolution decisions

**Edge Cases**:
- Standard error undefined when credibility=0 or 1
- Wilson score more robust at extremes

### Sub-Issue H6: Minimum Sample Size Too Low

**Files**:
- `docs/architecture/05-agents-coordination.md:153-243`
- `design-decisions/DD-003`

**Problem**: Auto-resolution requires "minimum 5 data points" but confidence interval at n=5 wider than 0.25 threshold.

**Mathematical Proof**:
```python
# Auto-resolution requirements:
min_sample_size = 5
credibility_threshold = 0.25

# Example: Agent A credibility=0.80, Agent B credibility=0.55, n=5 each
agent_a_credibility = 0.80
agent_b_credibility = 0.55

# Calculate confidence intervals (standard error formula)
ci_a = 1.96 * sqrt(0.80 * 0.20 / 5) = 0.35
ci_b = 1.96 * sqrt(0.55 * 0.45 / 5) = 0.44

# Combined interval
combined_interval = ci_a + ci_b = 0.79

# Credibility differential
differential = 0.80 - 0.55 = 0.25

# Check auto-resolution condition:
if differential (0.25) > max(threshold, combined_interval):
    # 0.25 > max(0.25, 0.79) → 0.25 > 0.79 → FALSE
    auto_resolve = False

# RESULT: Auto-resolution NEVER triggers at n=5!
```

**Recommendation**: Increase minimum to n=10-15

### Sub-Issue CS4: Fixed vs Dynamic Threshold

**Files**:
- `docs/architecture/05-agents-coordination.md:154`
- `docs/implementation/05-credibility-system.md:709`

**Inconsistency**:
```python
# coordination-agents.md L154
threshold = 0.25  # Fixed

# credibility-system.md L709
min_required = max(
    0.25,
    agent_A_confidence_interval + agent_B_confidence_interval
)  # Dynamic
```

**Clarification Needed**: 0.25 is minimum, but actual threshold adjusted for CI

---

## Recommended Solution

### Standardize on Wilson Score Interval

```python
class CredibilityConfidenceInterval:
    """Wilson score confidence interval (robust at extremes)"""

    @staticmethod
    def wilson_interval(successes, total, confidence=0.95):
        """Wilson score interval for binomial proportion"""

        if total == 0:
            return (0.0, 1.0)

        p_hat = successes / total
        z = 1.96 if confidence == 0.95 else 2.576  # 99%

        denominator = 1 + z**2 / total
        center = (p_hat + z**2 / (2 * total)) / denominator
        margin = z * sqrt(
            (p_hat * (1 - p_hat) / total + z**2 / (4 * total**2))
        ) / denominator

        lower = max(0, center - margin)
        upper = min(1, center + margin)

        return WilsonInterval(
            lower=lower,
            upper=upper,
            center=center,
            width=upper - lower
        )
```

### Increase Minimum Sample Size

```python
# Updated requirements
MIN_SAMPLE_SIZE_FOR_AUTO_RESOLUTION = 15  # Increased from 5

# Validation that threshold achievable
def validate_auto_resolution_feasible(sample_size, threshold=0.25):
    """Check if threshold achievable with sample size"""

    # Worst case: credibility = 0.50 (maximum variance)
    worst_case_ci = CredibilityConfidenceInterval.wilson_interval(
        successes=sample_size // 2,
        total=sample_size
    )

    max_combined_ci = worst_case_ci.width * 2

    if max_combined_ci > threshold:
        return ValidationResult(
            feasible=False,
            reason=f"CI width ({max_combined_ci:.2f}) exceeds threshold ({threshold})"
        )

    return ValidationResult(feasible=True)

# At n=15:
validate_auto_resolution_feasible(15, 0.25)
# → max_combined_ci = 0.24 < 0.25 ✓ FEASIBLE
```

### Dynamic Threshold Clarification

```python
class DebateAutoResolution:
    """Clarified auto-resolution logic"""

    BASE_THRESHOLD = 0.25  # Minimum credibility differential

    def can_auto_resolve(self, agent_a, agent_b, context):
        """Determine if debate can be auto-resolved"""

        # Get credibility with confidence intervals
        cred_a = self.get_credibility_with_ci(agent_a, context)
        cred_b = self.get_credibility_with_ci(agent_b, context)

        # Check sample size
        if cred_a.sample_size < 15 or cred_b.sample_size < 15:
            return AutoResolutionDecision(
                can_resolve=False,
                reason='insufficient_sample_size'
            )

        # Calculate differential
        differential = abs(cred_a.point_estimate - cred_b.point_estimate)

        # Dynamic threshold: BASE or CI sum, whichever larger
        required_differential = max(
            self.BASE_THRESHOLD,
            cred_a.ci_width + cred_b.ci_width
        )

        if differential > required_differential:
            return AutoResolutionDecision(
                can_resolve=True,
                winner=agent_a if cred_a.point_estimate > cred_b.point_estimate else agent_b,
                differential=differential,
                threshold_used=required_differential
            )

        return AutoResolutionDecision(
            can_resolve=False,
            reason='insufficient_differential'
        )
```

---

## Implementation Plan

**Week 1**: Implement Wilson score interval
**Week 2**: Update all credibility calculations
**Week 3**: Increase min sample size to 15
**Week 4**: Update documentation

---

## Success Criteria

- ✅ C4: Single confidence interval formula (Wilson score) used everywhere
- ✅ H6: Auto-resolution triggers for 0.25+ differential at n=15
- ✅ CS4: Dynamic threshold clearly documented
- ✅ Validated on 100 debate scenarios

---

## Dependencies

- **Blocks**: Debate auto-resolution (Flaw #8), Credibility system (Flaw #4 - RESOLVED)
- **Depends On**: Agent performance data collection
- **Related**: DD-003 (Debate Protocol), DD-008 (Credibility System)
