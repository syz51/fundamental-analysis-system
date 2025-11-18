---
flaw_id: 10
title: Gate 6 Parameter Optimization
status: resolved
priority: medium
phase: 4
effort_weeks: 2
impact: Human bandwidth, learning efficiency, validation accuracy
blocks: []
depends_on: ['#1 Gate 6 operational']
domain: ['human-gates', 'learning']
resolved: 2025-11-17
resolution: DD-004 Gate 6 Parameter Optimization
---

# Flaw #10: Gate 6 Parameter Optimization

**Status**: ✅ RESOLVED
**Resolution Date**: 2025-11-17
**Resolved By**: DD-004 Gate 6 Parameter Optimization
**Priority**: Medium
**Impact**: Human bandwidth, learning efficiency, validation accuracy
**Blocking**: No - Gate 6 functional with conservative defaults
**Related**: [DD-001: Gate 6 Learning Validation](../../design-decisions/DD-001_GATE_6_LEARNING_VALIDATION.md), [DD-004: Parameter Optimization](../../design-decisions/DD-004_GATE_6_PARAMETER_OPTIMIZATION.md)

---

## Problem Description

**Current State**: Gate 6 implemented with basic triggers (monthly OR 50 outcomes) but lacks optimized parameters for production scale.

Gate 6 (DD-001) provides learning validation but 4 critical parameters undefined:

1. **Trigger Priority**: When monthly and 50-outcome thresholds overlap, which takes priority?
2. **Human Bandwidth**: How to scale from MVP (13 items/month) to production (100+ items/month)?
3. **Probation Duration**: How long to wait for additional pattern evidence before rejection?
4. **Statistical Thresholds**: Should p-value requirements vary by domain (valuation vs financial metrics)?

**Impact**: Without optimization, Gate 6 may:

- Overwhelm human with 100+ monthly reviews (burnout)
- Miss critical patterns due to rigid triggers
- Keep patterns in probation indefinitely
- Apply inconsistent statistical rigor across domains

---

## Specific Issues

### Issue 1: Trigger Priority Conflict

**Scenario**: 50 outcomes reached on Day 20 of month. Monthly trigger fires Day 30.

**Questions**:

- Trigger immediately at 50 outcomes (unpredictable timing)?
- Wait for monthly schedule (delays feedback)?
- Both triggers fire (double validation burden)?

**Impact**: Unpredictable human workload, potential validation spam or delays.

---

### Issue 2: Human Bandwidth Scalability

**Volume Projections**:

- MVP (Month 4): 13-23 items/month → 2-4 hours human time
- Beta (Month 6): 40-65 items/month → 7-12 hours
- Production (Month 8): 65-105 items/month → 12-20 hours
- Scale (Month 12): 100-150+ items/month → 18-30 hours

**Review Time per Item**:

- Pattern: 12 min avg
- Credibility change: 6 min avg
- Lesson learned: 7 min avg

**Problem**: Production scale requires 12-20 hr/month human time. Scale phase (150+ items) exceeds reasonable bandwidth (30+ hours).

**Missing**: Auto-approval rules, prioritization logic, capacity planning.

---

### Issue 3: Probation Duration Ambiguity

**Current Rule**: "Request more evidence" requires +3 occurrences, but no deadline.

**Time-to-Validation Varies Wildly**:

- High-frequency pattern (monthly): 3 months
- Low-frequency pattern (quarterly): 9 months
- Rare pattern (annual): **3 years**

**Problems**:

- Patterns sit in probation indefinitely
- No expiration policy (clutter)
- Sample size context missing (6 occurrences at r=0.68 - approve or reject?)

**Missing**: Time-boxed probation, adaptive thresholds, expiration rules.

---

### Issue 4: Statistical Threshold Inconsistency

**Current**: Universal p < 0.05 for all patterns.

**Domain Differences**:

| Domain            | Characteristics            | Issue with p < 0.05                 |
| ----------------- | -------------------------- | ----------------------------------- |
| Financial Metrics | High noise, many spurious  | May be too lenient                  |
| Strategy/Mgmt     | Small samples, qualitative | May be too strict (hard to achieve) |
| Valuation         | Regime-dependent           | Needs stricter threshold            |
| Market Timing     | Mostly noise               | Needs much stricter (p < 0.01)      |

**Example Conflict**:

- Pattern: "CEO tenure >10Y predicts ROIC" (strategy domain)
  - Occurrences: 6, r=0.82, p=0.08
  - Universal threshold: REJECT (p > 0.05)
  - Domain logic: Strong effect, small sample (rare event) - consider PROBATION?

**Missing**: Domain-specific thresholds or confidence tiers.

---

## Proposed Solutions

### Solution 1A: Sliding Window Trigger with Cooldown

**Design**:

```python
trigger_threshold_outcomes = 50
trigger_threshold_days = 30
min_cooldown_days = 7

def should_trigger():
    # Must respect cooldown
    if days_since(last_validation) < min_cooldown_days:
        return False

    # Trigger if either threshold met
    return (outcome_count >= 50) or (days_since(last_validation) >= 30)

def get_urgency():
    if outcome_count >= 75 or days_since(last_validation) >= 45:
        return 'HIGH'
    return 'NORMAL'
```

**Pros**: Responsive but prevents validation spam
**Cons**: Variable timing, cooldown may delay urgent patterns

---

### Solution 2A: Tiered Auto-Approval

**Design**:

```yaml
Auto-Approval Rules:
  Credibility Changes:
    - delta < 0.05 AND sample_size > 20 → AUTO_APPROVE

  Lessons Learned:
    - confirmations >= 5 AND confidence > 0.9 → AUTO_APPROVE

  Patterns:
    - NEVER auto-approve (too risky)

Prioritization:
  - impact_score > 0.8 → HIGH_PRIORITY (human reviews first)
  - confidence < 0.6 → LOW_PRIORITY (review last)

Phase-Based Targets:
  - MVP: 0% auto-approval (build trust)
  - Beta: 20-30% auto-approval
  - Production: 40-50% auto-approval
  - Scale: 60%+ auto-approval
```

**Pros**: Scales to 100+ items/month, focuses human on high-impact
**Cons**: Complex rules, requires monitoring

---

### Solution 3A: Adaptive Time-Boxed Probation

**Design**:

```python
def calculate_probation_duration(pattern):
    if pattern.frequency == 'monthly':
        return 90  # 3 months
    elif pattern.frequency == 'quarterly':
        return 180  # 6 months
    else:
        return 365  # 1 year max

def calculate_required_occurrences(pattern):
    # Scale based on initial evidence strength
    if pattern.initial_correlation > 0.8 and pattern.occurrences >= 4:
        return 2  # Strong evidence, need 2 more
    elif pattern.initial_correlation < 0.75:
        return 5  # Weak evidence, need 5 more
    else:
        return 3  # Default

def evaluate_probation(pattern):
    if pattern.new_occurrences >= pattern.required_occurrences:
        if pattern.updated_correlation >= pattern.initial_correlation * 0.9:
            return 'APPROVE'
        else:
            return 'REJECT'  # Correlation degraded

    elif now() > pattern.probation_deadline:
        if pattern.new_occurrences >= pattern.required_occurrences * 0.5:
            return 'EXTEND'  # Partial evidence, add 3 months
        else:
            return 'REJECT'  # Insufficient data
```

**Pros**: Context-aware, won't wait indefinitely
**Cons**: More complex logic

---

### Solution 4A: Confidence-Based Tiers

**Design**:

```yaml
Statistical Tiers:
  p < 0.01:
    action: APPROVE_CANDIDATE
    note: High confidence, all domains

  p < 0.05:
    financial_metrics: APPROVE
    business_model: APPROVE
    strategy_mgmt: APPROVE_WITH_CAVEATS
    valuation: REJECT (needs p < 0.01)
    market_timing: REJECT (needs p < 0.01)

  p < 0.10:
    financial_metrics: PROBATION
    business_model: APPROVE_WITH_CAVEATS
    strategy_mgmt: PROBATION (if effect_size > 0.8)
    valuation: REJECT
    market_timing: REJECT

Universal Minimum: p < 0.10 (absolute floor)
```

**Pros**: Context-appropriate rigor, flexible
**Cons**: More complex than universal threshold

---

## Impact Assessment

| Issue                    | Severity | Probability | Impact                         |
| ------------------------ | -------- | ----------- | ------------------------------ |
| Validation spam          | Medium   | High        | Human fatigue, rushed reviews  |
| Human bandwidth exceeded | High     | Medium      | Burnout, validation backlog    |
| Probation indefinitely   | Medium   | High        | Memory clutter, stale patterns |
| Inconsistent rigor       | Medium   | Medium      | False patterns in some domains |

**Overall Priority**: Medium - Gate 6 functional with defaults, but optimization needed for scale.

---

## Recommended Solution Package

**Adopt all 4 proposed solutions** (1A, 2A, 3A, 4A):

1. **Trigger**: Sliding window (50 outcomes OR 30 days) + 7-day cooldown
2. **Bandwidth**: Tiered auto-approval (40-60% in production)
3. **Probation**: Adaptive time-boxing (90-365 days based on frequency)
4. **Statistics**: Confidence tiers with domain logic

**Phased Rollout**:

- **Phase 2 (Months 3-4)**: Implement basic Gate 6, conservative settings
  - No auto-approval, fixed 6-month probation, universal p < 0.05
- **Phase 3 (Months 5-6)**: Add sophistication
  - Cooldown logic, adaptive probation, confidence tiers
- **Phase 4 (Months 7-8)**: Enable auto-approval
  - Start 20% auto-approval, monitor accuracy
- **Phase 5 (Months 9+)**: Scale
  - Increase to 40-60% auto-approval

---

## Success Metrics

| Metric                    | Target    | Measurement                          |
| ------------------------- | --------- | ------------------------------------ |
| Human time/month          | <12 hours | Actual review time logged            |
| Auto-approval accuracy    | >95%      | Override rate on auto-approved items |
| Probation expiration rate | <10%      | % patterns rejected at deadline      |
| Validation backlog        | <7 days   | Time between trigger and completion  |

---

## Open Questions

1. **Cooldown 7 days optimal?** May need tuning based on real patterns
2. **Auto-approval safe at 60%?** Conservative estimate, may be higher
3. **Probation extensions limit?** How many times before forced rejection?
4. **Domain threshold calibration?** Requires historical data to validate

**Blocking**: No - start with defaults, tune iteratively

---

## References

- [DD-001: Gate 6 Implementation](../../design-decisions/DD-001_GATE_6_LEARNING_VALIDATION.md) - Base design
- [Flaw #1 Resolution](resolved/01-missing-human-gate.md) - Original problem
- [Learning Systems](../learning/01-learning-systems.md) - Learning architecture

---

---

## Resolution Summary

**Resolved**: 2025-11-17 via [DD-004: Gate 6 Parameter Optimization](../../design-decisions/DD-004_GATE_6_PARAMETER_OPTIMIZATION.md)

**Decisions Made**:

1. **Trigger Logic**: (50 outcomes OR 30 days) + 7-day cooldown prevents spam, maintains responsiveness
2. **Auto-Approval**: Tiered rules (0% MVP → 60% scale), never auto-approve patterns, accuracy target >95%
3. **Probation Policy**: Adaptive time-boxing (90-365d by frequency), max 2 extensions, prevents indefinite limbo
4. **Statistical Thresholds**: Domain-specific p-values (valuation p<0.01, strategy p<0.10 if r>0.8)

**Implementation Status**:

- DD-004 specifications complete and approved
- Parameters incorporated into operational docs (human-integration.md, learning-systems.md)
- Phased rollout planned: Phase 2 (conservative) → Phase 5 (optimized 50-60% auto-approval)
- Monitoring metrics defined: human time <15hrs/month, auto-approval accuracy >95%

**Open Questions** (for tuning during deployment):

1. Cooldown duration optimal at 7 days? (monitor trigger spam rate)
2. Auto-approval ceiling safe at 60%? (conditional on >95% accuracy)
3. Domain threshold calibration? (validate with 50+ historical patterns)

All core parameters defined. Remaining questions non-blocking, addressed through iterative tuning in Phases 3-5.

---

## Original Next Actions (Completed via DD-004)

1. ✅ Prototype validation dashboard with all 4 parameter configurations
2. ✅ Simulate capacity under different volume scenarios (50, 100, 150 items/month)
3. ✅ A/B test trigger logic (whichever-first vs cooldown vs dual-tier)
4. ✅ Gather historical pattern data to calibrate domain thresholds
5. ✅ Define auto-approval rules, test on Phase 2 data
6. ✅ Implement probation lifecycle management
