# Gate 6: Parameter Optimization for Scale

**Status**: Approved
**Date**: 2025-11-17
**Decider(s)**: System Architect
**Related Docs**: [DD-001](DD-001_GATE_6_LEARNING_VALIDATION.md), [Human Integration](../operations/02-human-integration.md), [Learning Systems](../learning/01-learning-systems.md)
**Related Decisions**: DD-001 (Gate 6 Learning Validation)
**Resolves**: [Flaw #10: Gate 6 Parameter Optimization](../design-flaws/resolved/10-gate-6-parameters.md)

---

## Context

DD-001 implemented Gate 6 learning validation with basic triggers (monthly OR 50 outcomes) but deferred parameter optimization. Without tuning, Gate 6 faces scalability issues:

- **Trigger conflicts**: 50 outcomes + monthly = potential validation spam or delays
- **Human bandwidth**: Production scale (100-150 items/month, 18-30 hrs) exceeds reasonable capacity
- **Probation ambiguity**: No time limits = patterns in limbo indefinitely (potentially 3+ years)
- **Statistical inconsistency**: Universal p < 0.05 too strict for strategy (small samples), too lenient for valuation (high noise)

Flaw #10 analyzed 4 optimization dimensions with proposed solutions. This DD formalizes parameter selections for production deployment.

---

## Decision

**Adopt comprehensive 4-parameter optimization package with phased rollout**:

1. **Trigger Logic**: Sliding window with cooldown
2. **Auto-Approval**: Tiered rules (0% → 60% across phases)
3. **Probation Policy**: Adaptive time-boxing with extensions
4. **Statistical Thresholds**: Domain-specific confidence tiers

Parameters defined conservatively for MVP, tuned iteratively through production scale.

---

## Detailed Parameter Specifications

### 1. Trigger Logic: Sliding Window with Cooldown

**Rule**: Trigger when (50 outcomes OR 30 days elapsed) AND cooldown satisfied

```python
TRIGGER_THRESHOLD_OUTCOMES = 50
TRIGGER_THRESHOLD_DAYS = 30
MIN_COOLDOWN_DAYS = 7

def should_trigger_gate6():
    # Respect cooldown period
    if days_since(last_validation) < MIN_COOLDOWN_DAYS:
        return False

    # Trigger on whichever threshold met first
    return (outcome_count >= 50) or (days_since(last_validation) >= 30)

def get_validation_urgency():
    if outcome_count >= 75 or days_since(last_validation) >= 45:
        return 'HIGH'  # Accumulating backlog
    return 'NORMAL'
```

**Rationale**:

- Cooldown prevents validation spam when both thresholds overlap
- "Whichever first" after cooldown = responsive without overwhelming human
- Urgency indicator prompts faster review when backlog builds

**Edge Cases**:

- High volume (>75 outcomes): Escalate urgency but still respect 7-day cooldown
- Low activity (<50 outcomes/month): Monthly trigger ensures regular review
- Cooldown during critical pattern: Conservative - wait 7 days to batch with other items

---

### 2. Auto-Approval: Tiered Rules for Scalability

**Phase-Based Targets**:

| Phase      | Timeline    | Volume         | Auto-Approval % | Human Time/Month |
| ---------- | ----------- | -------------- | --------------- | ---------------- |
| MVP        | Months 3-4  | 13-23 items    | 0%              | 2-4 hrs          |
| Beta       | Months 5-6  | 40-65 items    | 20-30%          | 7-9 hrs          |
| Production | Months 7-8  | 65-105 items   | 40-50%          | 8-12 hrs         |
| Scale      | Months 9-12 | 100-150+ items | 50-60%          | 10-15 hrs        |

**Auto-Approval Rules** (Production Phase):

```yaml
Credibility Changes:
  auto_approve_if:
    - delta < 0.05 AND sample_size >= 20 AND time_weighted_score_stable
    - delta < 0.03 AND sample_size >= 10

  require_human_if:
    - delta >= 0.05 (significant change)
    - sample_size < 10 (insufficient data)
    - agent_track_record == 'probationary'
    - domain == 'valuation' (high stakes)

Lessons Learned:
  auto_approve_if:
    - confirmations >= 5 AND confidence >= 0.9 AND no_contradictions
    - confirmations >= 8 AND confidence >= 0.85

  require_human_if:
    - confidence < 0.85 (uncertain)
    - contradictory_evidence_exists
    - affects_valuation_methodology

Patterns:
  auto_approve_if: NEVER
  rationale: Too high-risk - false patterns propagate to all agents

  require_human_if: ALWAYS (all patterns reviewed by human)
```

**Prioritization** (within human-reviewed items):

```yaml
HIGH_PRIORITY (review first):
  - impact_score > 0.8 (material effect on decisions)
  - affects_valuation_models
  - domain == 'risk_assessment'
  - agent_disagreement_exists

LOW_PRIORITY (review last):
  - confidence < 0.6 (low conviction)
  - supporting_detail (non-critical)
  - sample_size < 5 (preliminary)
```

**Rationale**:

- Conservative ramp (0% → 60%) builds trust, allows monitoring
- Never auto-approve patterns = safeguard against false correlation propagation
- Small credibility changes + large samples = safe for automation
- High-confidence lessons (5+ confirmations, 90%+ confidence) = low-risk
- Prioritization focuses human attention on high-impact items

**Monitoring**:

- Track auto-approval accuracy (target >95%, measured by human override rate on spot-checks)
- If accuracy <90%, pause auto-approval increases
- Monthly review of auto-approved items (10% random sample)

---

### 3. Probation Policy: Adaptive Time-Boxing

**Time-Boxed Probation** (prevents indefinite limbo):

```python
def calculate_probation_duration(pattern):
    """Max time before forced review"""
    frequency = estimate_pattern_frequency(pattern)

    if frequency == 'monthly':
        return 90   # 3 months (3 cycles)
    elif frequency == 'quarterly':
        return 180  # 6 months (2 cycles)
    elif frequency == 'annual':
        return 365  # 1 year (1 cycle)
    else:
        return 180  # Default: 6 months

def calculate_required_occurrences(pattern):
    """Evidence needed to exit probation"""
    # Adaptive based on initial strength
    if pattern.initial_correlation >= 0.8 and pattern.occurrences >= 4:
        return 2  # Strong evidence, need 2 more confirmations
    elif pattern.initial_correlation < 0.75:
        return 5  # Weak evidence, need 5 more confirmations
    else:
        return 3  # Default: 3 more occurrences
```

**Probation Evaluation** (at deadline):

```python
def evaluate_probation_at_deadline(pattern):
    """Decide: approve, reject, or extend"""

    if pattern.new_occurrences >= pattern.required_occurrences:
        # Sufficient new data
        if pattern.updated_correlation >= pattern.initial_correlation * 0.9:
            return 'APPROVE'  # Evidence held up
        else:
            return 'REJECT'   # Correlation degraded

    elif pattern.new_occurrences >= pattern.required_occurrences * 0.5:
        # Partial evidence (50%+ of target)
        if pattern.extensions_count < 2:
            return 'EXTEND_90_DAYS'  # One more chance (max 2 extensions)
        else:
            return 'REJECT'  # Exceeded extension limit

    else:
        # Insufficient data after deadline
        return 'REJECT'  # Not enough evidence in reasonable timeframe
```

**Extension Limits**:

- Max 2 extensions per pattern (3 months each)
- Total probation cannot exceed: original_duration + 180 days
- Example: Quarterly pattern (180d initial) can extend max to 360d (1 year)

**Expiration Notification**:

- 30 days before deadline: "Pattern XYZ approaching probation deadline"
- 7 days before: "Pattern XYZ expires in 7 days - insufficient evidence"
- At deadline: Auto-evaluate and notify outcome

**Rationale**:

- Time-boxing prevents indefinite limbo, forces resolution
- Adaptive requirements account for pattern strength (strong patterns need less confirmation)
- Extension mechanism (50% progress) balances flexibility with decisiveness
- 2-extension limit prevents infinite deferral (max total: ~2 years for rare patterns)

**Edge Cases**:

- Rare pattern (1-2 occurrences/year): May legitimately need 2-year timeframe, but forced review at 1 year
- Degrading correlation: Reject even if sufficient occurrences (pattern weakening)
- High-frequency but no occurrences: Reject at 90 days (likely spurious)

---

### 4. Statistical Thresholds: Domain-Specific Confidence Tiers

**Universal Minimum**: p < 0.10 (absolute floor for any domain)

**Domain-Specific Thresholds**:

| Domain                  | p < 0.01 | p < 0.05             | p < 0.10             | Rationale                              |
| ----------------------- | -------- | -------------------- | -------------------- | -------------------------------------- |
| **Valuation Models**    | APPROVE  | PROBATION            | REJECT               | High stakes, need strong evidence      |
| **Market Timing**       | APPROVE  | PROBATION            | REJECT               | Mostly noise, strict threshold         |
| **Financial Metrics**   | APPROVE  | APPROVE              | PROBATION            | Moderate noise, standard threshold OK  |
| **Business Model**      | APPROVE  | APPROVE              | APPROVE_WITH_CAVEATS | Qualitative, less statistical rigor    |
| **Strategy/Mgmt**       | APPROVE  | APPROVE_WITH_CAVEATS | PROBATION (if r>0.8) | Small samples, qualitative, contextual |
| **Operational Metrics** | APPROVE  | APPROVE              | PROBATION            | Similar to financial metrics           |

**Confidence Tier Definitions**:

- **APPROVE**: Full validation, broadcast to all agents
- **APPROVE_WITH_CAVEATS**: Validate but add usage conditions (e.g., "Apply only in stable markets")
- **PROBATION**: Requires additional evidence (see probation policy above)
- **REJECT**: Insufficient statistical rigor

**Additional Considerations**:

```yaml
Strategy/Management Domain Special Rules:
  # Small samples acceptable if effect size large
  if domain == 'strategy_mgmt' and p < 0.10:
    if effect_size > 0.8 and occurrences >= 5: return 'PROBATION' # Strong effect, consider despite marginal p-value
    else: return 'REJECT'

Valuation Domain Special Rules:
  # Never accept marginal p-values for valuation
  if domain == 'valuation':
    if p >= 0.05: return 'REJECT' # Too much impact on pricing to risk false positive
```

**Rationale**:

- Domain-specific thresholds match risk profile (valuation = high stakes = strict)
- Strategy domain: Small samples expected (rare events), effect size matters more
- Financial metrics: Standard p < 0.05 appropriate (moderate noise, large samples)
- Market timing: Mostly noise, need very strong evidence (p < 0.01)

**Human Override**:

- Human can approve patterns below domain threshold if compelling causal logic
- Must document override rationale for audit trail
- Overrides tracked separately, reviewed quarterly for systematic biases

---

## Implementation Phases

**Phase 2 (Months 3-4): MVP - Conservative Defaults**

- No auto-approval (0%)
- Fixed 6-month probation for all patterns
- Universal p < 0.05 threshold
- Manual trigger monitoring
- **Goal**: Establish baseline, build trust

**Phase 3 (Months 5-6): Beta - Add Sophistication**

- Implement cooldown logic
- Deploy adaptive probation (90-365d by frequency)
- Introduce domain-specific confidence tiers
- Enable 20-30% auto-approval (small credibility changes only)
- **Goal**: Validate algorithms, begin scaling

**Phase 4 (Months 7-8): Production - Scale Enablement**

- Increase auto-approval to 40-50%
- Full probation lifecycle (extensions, expirations)
- Prioritization logic (high/low impact)
- Urgency indicators
- **Goal**: Support 100+ items/month

**Phase 5 (Months 9-12): Scale - Optimization**

- Tune auto-approval to 50-60% based on accuracy data
- Calibrate domain thresholds with historical patterns
- A/B test trigger parameters (cooldown duration)
- Continuous monitoring and adjustment
- **Goal**: Handle 150+ items/month efficiently

---

## Consequences

### Positive Impacts

- **Scalability**: Supports 150+ items/month without exceeding 15hrs human time
- **Responsiveness**: 7-day cooldown balances spam prevention with timely validation
- **Decisiveness**: Time-boxed probation prevents indefinite pattern limbo
- **Rigor**: Domain-specific thresholds apply appropriate statistical standards
- **Trust**: Conservative phased rollout (0% → 60% auto-approval) builds confidence
- **Focus**: Prioritization directs human attention to high-impact items

### Negative Impacts / Tradeoffs

- **Complexity**: 4 sophisticated subsystems vs simple rules (increased dev/test burden)
- **Tuning Required**: Parameters may need adjustment based on real data (ongoing maintenance)
- **Monitoring Overhead**: Auto-approval accuracy requires spot-checks (10% random sample monthly)
- **Edge Cases**: Rare patterns may still hit probation limits before sufficient evidence
- **Risk**: Auto-approval at 60% requires high confidence in algorithms (failure = false patterns)

### Affected Components

- **Learning Engine**: Trigger logic, probation lifecycle, auto-approval rules
- **Knowledge Base Agent**: Probation tracking, expiration management, domain tagging
- **Human Interface**: Dashboard showing priorities, urgencies, deadlines
- **All Specialist Agents**: Consume only validated patterns (unchanged from DD-001)
- **Monitoring System**: Track auto-approval accuracy, probation outcomes, human time spent

---

## Success Metrics

| Metric                           | Target   | Measurement                                         | Phase     |
| -------------------------------- | -------- | --------------------------------------------------- | --------- |
| Human time/month                 | <15 hrs  | Actual review time logged                           | Phase 4-5 |
| Auto-approval accuracy           | >95%     | Override rate on random sample (10% monthly)        | Phase 3-5 |
| Probation expiration rate        | <10%     | % patterns rejected at deadline (insufficient)      | Phase 3-5 |
| Validation backlog               | <7 days  | Time between trigger and completion                 | Phase 4-5 |
| Trigger spam (extra validations) | 0        | Validations triggered within cooldown (should be 0) | Phase 2-5 |
| Human satisfaction               | >4.0/5.0 | Monthly survey on workload, interface usability     | Phase 3-5 |

**Failure Criteria** (triggers parameter rollback):

- Auto-approval accuracy <90% for 2 consecutive months → reduce auto-approval %
- Human time >20 hrs/month for 2 months → increase auto-approval or reduce volume
- Probation expiration rate >20% → adjust required occurrences or duration
- Trigger spam >1/month → increase cooldown period

---

## Open Questions

### Tuning Parameters (resolve in Phase 3-4 with real data)

1. **Cooldown Duration**: 7 days optimal or adjust to 10/14 days?

   - _Answer_: Monitor trigger spam rate in Phase 2-3, adjust if >1 spam/month

2. **Auto-Approval Ceiling**: Safe to reach 60% or cap at 50%?

   - _Answer_: Conditional on accuracy >95% in Phase 4. If accuracy ≥97%, try 65%.

3. **Probation Extension Limit**: 2 extensions sufficient or allow 3?

   - _Answer_: Start with 2 (total ~2 years max), extend to 3 only for rare high-value patterns

4. **Domain Threshold Calibration**: p-values correct or need adjustment?
   - _Answer_: Gather 50+ historical patterns by domain, validate thresholds against outcomes

### Product Questions (ongoing)

5. **Human Override Tracking**: How often do humans override domain thresholds?

   - _Action_: Log all overrides with rationale, quarterly review for systematic patterns

6. **Pattern Frequency Estimation**: How accurate is algorithm at classifying monthly/quarterly/annual?
   - _Action_: Validate against actual occurrence intervals in Phase 3

**None blocking** - defaults allow system to function, tuning improves efficiency.

---

## Implementation Notes

### Core Classes

```python
class Gate6TriggerManager:
    """Manages validation triggers with cooldown"""
    def __init__(self):
        self.outcome_threshold = 50
        self.time_threshold_days = 30
        self.min_cooldown_days = 7
        self.last_validation_date = None

    def should_trigger(self):
        if self._in_cooldown():
            return False
        return self._outcome_threshold_met() or self._time_threshold_met()

    def get_urgency(self):
        if self.outcome_count >= 75 or self._days_since_validation() >= 45:
            return 'HIGH'
        return 'NORMAL'

class AutoApprovalEngine:
    """Tiered auto-approval rules"""
    def __init__(self, phase='mvp'):
        self.phase = phase
        self.approval_targets = {
            'mvp': 0.0,
            'beta': 0.25,
            'production': 0.45,
            'scale': 0.55
        }

    def evaluate_item(self, item):
        """Returns: 'AUTO_APPROVE', 'HUMAN_REVIEW_HIGH', 'HUMAN_REVIEW_LOW'"""
        if item.type == 'pattern':
            return 'HUMAN_REVIEW_HIGH'  # Never auto-approve patterns

        if self._meets_auto_approval_criteria(item):
            return 'AUTO_APPROVE'

        if self._is_high_priority(item):
            return 'HUMAN_REVIEW_HIGH'

        return 'HUMAN_REVIEW_LOW'

class ProbationManager:
    """Adaptive time-boxed probation"""
    def __init__(self):
        self.max_extensions = 2

    def calculate_deadline(self, pattern):
        frequency = self._estimate_frequency(pattern)
        durations = {'monthly': 90, 'quarterly': 180, 'annual': 365}
        return durations.get(frequency, 180)

    def evaluate_at_deadline(self, pattern):
        """Returns: 'APPROVE', 'REJECT', 'EXTEND_90_DAYS'"""
        # Implementation per specification above
        pass

class DomainStatisticalValidator:
    """Domain-specific p-value thresholds"""
    def __init__(self):
        self.thresholds = {
            'valuation': {'approve': 0.01, 'probation': 0.05},
            'market_timing': {'approve': 0.01, 'probation': 0.05},
            'financial_metrics': {'approve': 0.05, 'probation': 0.10},
            'strategy_mgmt': {'approve': 0.05, 'probation': 0.10},
            # ... other domains
        }

    def validate_pattern(self, pattern):
        """Returns: 'APPROVE', 'APPROVE_WITH_CAVEATS', 'PROBATION', 'REJECT'"""
        domain_rules = self.thresholds[pattern.domain]
        # Apply domain-specific logic per specification above
        pass
```

### Testing Requirements

**Trigger Logic**:

1. Cooldown enforcement (no trigger within 7 days)
2. Outcome threshold (triggers at 50 outcomes after cooldown)
3. Time threshold (triggers at 30 days after cooldown)
4. Urgency escalation (HIGH at 75 outcomes or 45 days)
5. Edge case: Both thresholds met simultaneously (should trigger once)

**Auto-Approval**:

1. Pattern never auto-approved (all require human)
2. Small credibility changes auto-approved (delta <0.05, n≥20)
3. High-confidence lessons auto-approved (5+ confirmations, 90%+ confidence)
4. Valuation domain never auto-approved (high stakes)
5. Accuracy monitoring (10% spot-check sample)

**Probation**:

1. Duration calculation (monthly=90d, quarterly=180d, annual=365d)
2. Deadline evaluation (approve/reject/extend logic)
3. Extension limit enforcement (max 2 extensions)
4. Expiration notifications (30d, 7d, deadline)
5. Degrading correlation rejection (even if sufficient occurrences)

**Statistical Validation**:

1. Domain routing (valuation → strict, strategy → flexible)
2. p-value tier logic (p<0.01 always approve, domain-specific otherwise)
3. Effect size consideration (strategy domain, r>0.8 allows p<0.10)
4. Human override tracking (documented rationale, quarterly review)

**Integration Tests**:

1. End-to-end validation flow (trigger → auto-approval → human review → pattern broadcast)
2. Phase transitions (MVP → Beta → Production settings changes)
3. Monitoring dashboards (metrics tracked correctly)

### Rollback Strategy

If auto-approval accuracy falls below 90% or human time exceeds 20 hrs/month:

1. **Immediate**: Reduce auto-approval % by 10-15 points (e.g., 50% → 35%)
2. **Phase 1 Rollback**: Return to 0% auto-approval, investigate failure modes
3. **Phase 2 Rollback**: Disable sophisticated features (adaptive probation → fixed 6mo, domain thresholds → universal p<0.05)
4. **Full Rollback**: Return to DD-001 conservative defaults

### Deployment Timeline

- **Phase 2 (Months 3-4)**: Basic Gate 6 with conservative defaults
- **Phase 3 (Months 5-6)**: Deploy cooldown, adaptive probation, domain thresholds, 20-30% auto-approval
- **Phase 4 (Months 7-8)**: Increase to 40-50% auto-approval, full prioritization
- **Phase 5 (Months 9-12)**: Tune to 50-60% auto-approval, continuous optimization

**Estimated Implementation Effort**:

- Phase 2 (Basic): 2 weeks (already completed per DD-001)
- Phase 3 (Sophistication): 4-5 weeks
- Phase 4-5 (Tuning): Ongoing optimization

**Dependencies**:

- DD-001 Gate 6 implementation (complete)
- Validation dashboard UI (Phase 2)
- Monitoring infrastructure (Phase 3)
- Historical pattern data for calibration (Phase 3-4)

---

## References

- [DD-001: Gate 6 Learning Validation](DD-001_GATE_6_LEARNING_VALIDATION.md) - Base implementation
- [Flaw #10: Gate 6 Parameter Optimization](../design-flaws/resolved/10-gate-6-parameters.md) - Problem analysis
- [Human Integration](../operations/02-human-integration.md) - Gate 6 in workflow
- [Learning Systems](../learning/01-learning-systems.md) - Learning architecture
- [Flaw #1 Resolution](../design-flaws/resolved/01-missing-human-gate.md) - Original problem

---

## Status History

| Date       | Status      | Notes                                     |
| ---------- | ----------- | ----------------------------------------- |
| 2025-11-17 | Proposed    | Resolving Flaw #10 parameter optimization |
| 2025-11-17 | Approved    | Approved by system architect              |
| 2025-11-17 | Implemented | Specifications added to design docs       |

---

## Notes

**Conservative Approach**: All 4 parameters start with safe defaults (no auto-approval, long probation, universal p<0.05, simple trigger). Sophistication added incrementally with monitoring at each phase. Reduces risk of premature optimization.

**Auto-Approval Safety**: Never auto-approve patterns (highest risk). Only small credibility changes and high-confidence lessons. 10% spot-check sampling ensures quality control. Accuracy target >95% with rollback trigger at <90%.

**Probation Philosophy**: Time-boxing forces resolution but allows reasonable timeframes (up to 2 years for rare patterns with extensions). Prevents indefinite limbo while accommodating low-frequency legitimate patterns.

**Domain Thresholds**: Reflect risk profile - valuation affects pricing (strict), strategy has small samples (flexible). Human can override with documented rationale, creating feedback loop for threshold calibration.

**Phased Rollout Critical**: Jumping directly to 60% auto-approval risky. 0% → 25% → 45% → 55% allows monitoring, builds trust, enables rollback if issues detected.
