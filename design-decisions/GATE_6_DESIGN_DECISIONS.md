# Gate 6: Learning Validation - Open Design Decisions

**Date**: 2025-11-17
**Status**: Requires Resolution Before Implementation
**Related**: Design Flaw #1 Fix in v2.1

---

## Overview

Gate 6 (Learning Validation) addresses critical confirmation bias flaw. Following design decisions require resolution before implementation.

---

## 1. Trigger Priority: Monthly vs 50-Outcome Threshold

### Question

When both triggers occur simultaneously or overlap, which takes priority? What happens if 50 outcomes reached mid-month?

### Current Specification

```yaml
Trigger: Monthly or after 50 new outcomes tracked
```

### Options

#### Option A: Whichever Comes First

- Trigger immediately when either condition met
- Resets both counters after validation
- **Pros**: Faster feedback loop, prevents pattern backlog
- **Cons**: Unpredictable timing, potential human fatigue

#### Option B: Monthly Only, Queue Outcomes

- Fixed monthly schedule (e.g., 1st of month)
- Queue all outcomes since last validation
- **Pros**: Predictable, batches work efficiently
- **Cons**: May delay critical pattern validation up to 30 days

#### Option C: Dual-Tier System

- Monthly for routine validation
- Immediate trigger at 50 outcomes (emergency threshold)
- **Pros**: Balance predictability with responsiveness
- **Cons**: More complex logic, two validation modes

#### Option D: Sliding Window

- Trigger after 50 outcomes OR 30 days, whichever first
- Once triggered, minimum 7-day cooldown before next trigger
- **Pros**: Responsive but prevents validation spam
- **Cons**: Variable timing, cooldown may delay urgent patterns

### Recommendation

**Option D: Sliding Window with Cooldown**

```python
class ValidationTrigger:
    def __init__(self):
        self.outcome_threshold = 50
        self.time_threshold_days = 30
        self.min_cooldown_days = 7
        self.last_validation = None
        self.outcome_count = 0

    def should_trigger(self):
        # Must respect cooldown
        if self.last_validation and days_since(self.last_validation) < self.min_cooldown_days:
            return False

        # Trigger if either threshold met
        outcomes_trigger = self.outcome_count >= self.outcome_threshold
        time_trigger = days_since(self.last_validation) >= self.time_threshold_days

        return outcomes_trigger or time_trigger

    def get_urgency(self):
        if self.outcome_count >= self.outcome_threshold * 1.5:  # 75+ outcomes
            return 'HIGH'
        elif days_since(self.last_validation) >= self.time_threshold_days * 1.5:  # 45+ days
            return 'HIGH'
        else:
            return 'NORMAL'
```

**Rationale**: Balances responsiveness (catch issues fast) with human bandwidth (cooldown prevents fatigue). Urgency flag helps prioritize when backlog builds.

### Trade-offs

| Factor               | Impact               | Mitigation                            |
| -------------------- | -------------------- | ------------------------------------- |
| High-volume periods  | Many validations     | Cooldown prevents spam                |
| Low-activity periods | Stale patterns       | Time threshold ensures regular review |
| Human availability   | Unpredictable timing | Urgency levels help prioritize        |

---

## 2. Human Validation Bandwidth & Capacity Planning

### Question

Realistic human validation capacity per month? How many patterns/credibility changes/lessons can one person effectively review?

### Capacity Analysis

#### Time Estimates per Item Type

```yaml
Pattern Validation:
  Simple review: 5-10 min
  Complex review (request analysis): 15-30 min
  Average: 12 min

Credibility Change Review:
  Quick approval: 2-3 min
  Detailed error analysis: 10-15 min
  Average: 6 min

Lesson Learned Review:
  Simple lesson: 3-5 min
  Complex lesson (add caveats): 8-12 min
  Average: 7 min
```

#### Monthly Capacity Scenarios

**Conservative (2 hours/month dedicated)**:

- 10 patterns (120 min @ 12 min each)
- OR 20 credibility changes (120 min @ 6 min each)
- OR 17 lessons (120 min @ 7 min each)
- **Mixed**: ~5 patterns + 5 credibility + 5 lessons = ~125 min

**Moderate (5 hours/month dedicated)**:

- 25 patterns
- OR 50 credibility changes
- OR 42 lessons
- **Mixed**: ~12 patterns + 12 credibility + 12 lessons = ~300 min

**Aggressive (10 hours/month dedicated)**:

- 50 patterns
- OR 100 credibility changes
- OR 85 lessons
- **Mixed**: ~24 patterns + 24 credibility + 24 lessons = ~600 min

### Expected Volume Projections

```yaml
MVP Phase (Month 4):
  - 10 stocks analyzed
  - ~3-5 patterns discovered/month
  - ~5-8 credibility changes/month
  - ~5-10 lessons learned/month
  - Total items: 13-23/month
  - Time required: 2.5-4.5 hours/month

Beta Phase (Month 6):
  - 50 stocks analyzed
  - ~10-15 patterns/month
  - ~15-25 credibility changes/month
  - ~15-25 lessons/month
  - Total items: 40-65/month
  - Time required: 7-12 hours/month

Production (Month 8):
  - 200 stocks analyzed
  - ~15-25 patterns/month
  - ~25-40 credibility changes/month
  - ~25-40 lessons/month
  - Total items: 65-105/month
  - Time required: 12-20 hours/month
```

### Recommendation

**Tiered Validation Approach**

```python
class ValidationPrioritization:
    def prioritize_validation_queue(self, queue):
        """Prioritize items for human review"""

        # Auto-approve low-risk items
        auto_approved = []
        for item in queue:
            if self.can_auto_approve(item):
                auto_approved.append(item)
                queue.remove(item)

        # Prioritize remaining by impact
        prioritized = sorted(queue, key=lambda x: (
            x.impact_score * -1,  # Higher impact first
            x.confidence * -1,     # Higher confidence first
            x.num_agents_affected * -1  # More agents affected first
        ))

        return prioritized, auto_approved

    def can_auto_approve(self, item):
        """Auto-approve low-risk updates"""
        if isinstance(item, CredibilityChange):
            # Small changes with high sample size
            if abs(item.delta) < 0.05 and item.sample_size > 20:
                return True

        if isinstance(item, LessonLearned):
            # High-confidence lessons with multiple confirmations
            if item.confirmations >= 5 and item.confidence > 0.9:
                return True

        # Never auto-approve patterns - too risky
        return False
```

**Capacity Planning Guidelines**:

| Phase      | Expected Items/Month | Human Time Budget | Strategy                               |
| ---------- | -------------------- | ----------------- | -------------------------------------- |
| MVP        | 13-23                | 2-4 hours         | Human reviews all, builds intuition    |
| Beta       | 40-65                | 5-8 hours         | Auto-approve 20-30%, prioritize rest   |
| Production | 65-105               | 8-12 hours        | Auto-approve 40-50%, focus on patterns |
| Scale      | 100-150+             | 10-15 hours       | Auto-approve 60%+, sample validation   |

### Trade-offs

| Approach                  | Pros        | Cons                        | Risk        |
| ------------------------- | ----------- | --------------------------- | ----------- |
| Review everything         | Max safety  | Not scalable                | Burnout     |
| Auto-approve aggressively | Scales well | False patterns slip through | High        |
| Tiered prioritization     | Balanced    | Complex rules               | Medium      |
| Sampling validation       | Efficient   | May miss issues             | Medium-High |

**Mitigation**: Start conservative (review all), gradually increase auto-approval as trust builds. Monthly review auto-approval accuracy.

---

## 3. Pattern Probation Duration & Evidence Thresholds

### Question

When pattern marked "needs more evidence" (probationary), how long before re-evaluation? How many additional occurrences required?

### Current Specification

```yaml
Human Actions:
  - Request more evidence (need 3+ more occurrences)
```

### Issues with Fixed "3+ Occurrences"

1. **Time-to-validation varies wildly**:

   - High-frequency pattern (monthly): 3 months
   - Low-frequency pattern (quarterly): 9 months
   - Rare pattern (annual): 3 years (!!)

2. **Sample size context missing**:

   - Initial: 3 occurrences, correlation 0.75
   - After +3: 6 occurrences, correlation 0.68 (degrading)
   - Should we approve or reject?

3. **No expiration policy**:
   - Pattern sits in probation indefinitely
   - Clutters queue, wastes memory

### Recommendation

**Time-Boxed Probation with Adaptive Thresholds**

```python
class ProbationaryPattern:
    def __init__(self, pattern, human_feedback):
        self.pattern = pattern
        self.probation_start = now()
        self.probation_duration_days = self.calculate_duration(pattern)
        self.required_occurrences = self.calculate_required_occurrences(pattern)
        self.review_deadline = self.probation_start + days(self.probation_duration_days)

    def calculate_duration(self, pattern):
        """Adaptive duration based on pattern frequency"""
        if pattern.estimated_frequency == 'monthly':
            return 90  # 3 months
        elif pattern.estimated_frequency == 'quarterly':
            return 180  # 6 months
        elif pattern.estimated_frequency == 'annual':
            return 365  # 1 year
        else:
            return 180  # Default 6 months

    def calculate_required_occurrences(self, pattern):
        """Scale requirement based on initial evidence"""
        base_requirement = 3

        # Stronger initial evidence → fewer additional occurrences
        if pattern.initial_correlation > 0.8 and pattern.initial_occurrences >= 4:
            return 2  # Just need 2 more

        # Weaker initial evidence → more validation needed
        if pattern.initial_correlation < 0.75 or pattern.initial_occurrences == 3:
            return 5  # Need 5 more

        return base_requirement

    def should_re_evaluate(self):
        """Trigger re-evaluation"""
        # Met evidence threshold
        if self.pattern.new_occurrences >= self.required_occurrences:
            return True, 'evidence_threshold_met'

        # Deadline approaching (30 days out)
        if days_until(self.review_deadline) <= 30:
            return True, 'deadline_approaching'

        # Deadline passed
        if now() > self.review_deadline:
            return True, 'deadline_expired'

        return False, None

    def recommend_action(self):
        """Recommend action at re-evaluation"""
        reason = self.should_re_evaluate()[1]

        if reason == 'evidence_threshold_met':
            # Check if correlation held up
            if self.pattern.updated_correlation >= self.pattern.initial_correlation * 0.9:
                return 'APPROVE', 'Sufficient evidence, correlation stable'
            else:
                return 'REJECT', 'Correlation degraded with more data'

        elif reason == 'deadline_expired':
            # Not enough occurrences by deadline
            if self.pattern.new_occurrences >= self.required_occurrences * 0.5:
                return 'EXTEND', 'Partial evidence, extend probation'
            else:
                return 'REJECT', 'Insufficient occurrences within timeframe'

        else:  # deadline_approaching
            return 'REVIEW', 'Evaluate partial evidence'
```

**Policy Framework**:

| Initial Evidence      | Required Additional | Max Duration | Outcome                             |
| --------------------- | ------------------- | ------------ | ----------------------------------- |
| 3 occur, r=0.70       | 5 more              | 6 months     | Approve if r≥0.65                   |
| 4 occur, r=0.75       | 3 more              | 6 months     | Approve if r≥0.68                   |
| 5 occur, r=0.80       | 2 more              | 3 months     | Approve if r≥0.72                   |
| Any, deadline expired | N/A                 | N/A          | Reject if <50% required occurrences |

### Probation Lifecycle

```
Pattern enters probation
    ↓
Start clock (90-365 days based on frequency)
Set occurrence requirement (2-5 based on strength)
    ↓
[Monitor for new occurrences]
    ↓
Trigger re-evaluation if:
  - Required occurrences met → Approve/Reject based on correlation
  - 30 days from deadline → Early review with partial evidence
  - Deadline expired → Reject if insufficient, extend if partial
    ↓
Final decision:
  - APPROVE → Promote to active
  - REJECT → Archive permanently
  - EXTEND → Add 3 months, increase requirement by 2
```

### Trade-offs

| Approach               | Pros                | Cons                              |
| ---------------------- | ------------------- | --------------------------------- |
| Fixed 3 occurrences    | Simple, predictable | Ignores frequency, may wait years |
| Time-boxed only        | Won't wait forever  | May approve/reject prematurely    |
| Adaptive (recommended) | Context-aware, fair | More complex logic                |

---

## 4. Statistical Significance Threshold by Domain

### Question

Should p-value requirement (currently p < 0.05) vary by domain, or use universal threshold?

### Current Specification

```yaml
Statistical Rigor: Require p-value < 0.05 for significance
```

### Domain-Specific Considerations

#### Financial Metrics Domain

- **Characteristics**: High signal-to-noise, large sample sizes
- **Current threshold**: p < 0.05 (95% confidence)
- **Consideration**: Financial data often noisy, many spurious correlations

**Example**: Margin prediction patterns

```
Sample pattern: "Retailers compress margins in Q4"
- Occurrences: 12
- Correlation: 0.73
- p-value: 0.03
- Issue: Q4 seasonality well-known, pattern obvious, lenient threshold OK
```

#### Strategy/Management Domain

- **Characteristics**: Low sample sizes, qualitative factors
- **Current threshold**: p < 0.05
- **Consideration**: Fewer data points (CEO changes rare), harder to achieve significance

**Example**: Management effectiveness patterns

```
Sample pattern: "CEO with 10+ year tenure outperforms on capital allocation"
- Occurrences: 6
- Correlation: 0.82
- p-value: 0.08
- Issue: Strong correlation but small sample, strict threshold may reject valuable pattern
```

#### Valuation Domain

- **Characteristics**: Forward-looking, regime-dependent
- **Current threshold**: p < 0.05
- **Consideration**: Market regimes change, historical patterns may not hold

**Example**: Multiple expansion patterns

```
Sample pattern: "Tech stocks trade at 25x P/E in low-rate environment"
- Occurrences: 8
- Correlation: 0.85
- p-value: 0.02
- Issue: Regime-dependent, may not generalize, need stricter threshold?
```

### Options

#### Option A: Universal Threshold (Status Quo)

```python
SIGNIFICANCE_THRESHOLD = 0.05  # All domains
```

- **Pros**: Simple, consistent, scientifically standard
- **Cons**: Ignores domain characteristics, may be too strict/lenient

#### Option B: Domain-Specific Thresholds

```python
SIGNIFICANCE_THRESHOLDS = {
    'financial_metrics': 0.05,     # Standard
    'business_model': 0.10,         # More lenient (qualitative)
    'strategy_management': 0.10,    # More lenient (small sample)
    'valuation': 0.01,              # More strict (regime-dependent)
    'market_timing': 0.01,          # More strict (random walk)
}
```

- **Pros**: Context-appropriate rigor
- **Cons**: Complex, arbitrary thresholds, inconsistent

#### Option C: Confidence-Based Tiers

```python
class SignificanceEvaluation:
    def evaluate_pattern(self, pattern):
        p_value = pattern.p_value

        if p_value < 0.01:
            return 'HIGH_CONFIDENCE', 'Very strong evidence'
        elif p_value < 0.05:
            return 'MEDIUM_CONFIDENCE', 'Standard significance'
        elif p_value < 0.10:
            return 'LOW_CONFIDENCE', 'Suggestive but not definitive'
        else:
            return 'NOT_SIGNIFICANT', 'Insufficient evidence'

    def recommend_action(self, pattern, confidence_tier):
        if confidence_tier == 'HIGH_CONFIDENCE':
            return 'AUTO_APPROVE_CANDIDATE'  # Still needs human review

        elif confidence_tier == 'MEDIUM_CONFIDENCE':
            # Check domain context
            if pattern.domain in ['valuation', 'market_timing']:
                return 'REQUIRES_STRONG_JUSTIFICATION'
            else:
                return 'STANDARD_REVIEW'

        elif confidence_tier == 'LOW_CONFIDENCE':
            # Only accept with additional supporting evidence
            return 'REQUIRES_QUALITATIVE_SUPPORT'

        else:
            return 'REJECT'
```

- **Pros**: Flexible, transparent tiers, human makes final call
- **Cons**: Still requires human judgment

#### Option D: Bayesian Approach with Priors

```python
class BayesianPatternEvaluation:
    def __init__(self):
        # Prior beliefs about pattern validity by domain
        self.priors = {
            'financial_metrics': 0.3,      # 30% of discovered patterns real
            'business_model': 0.5,          # 50% real (more stable)
            'strategy_management': 0.4,     # 40% real
            'valuation': 0.2,               # 20% real (many spurious)
            'market_timing': 0.1,           # 10% real (mostly noise)
        }

    def calculate_posterior(self, pattern):
        """Update prior with observed evidence"""
        prior = self.priors[pattern.domain]
        likelihood = self.calculate_likelihood(pattern)

        # Bayes' theorem
        posterior = (likelihood * prior) / self.marginal_likelihood(pattern)

        return posterior

    def recommend_threshold(self, pattern):
        """Dynamic threshold based on posterior"""
        posterior = self.calculate_posterior(pattern)

        if posterior > 0.8:
            return 'p < 0.10'  # Lenient (strong prior + evidence)
        elif posterior > 0.6:
            return 'p < 0.05'  # Standard
        else:
            return 'p < 0.01'  # Strict (weak prior)
```

- **Pros**: Principled, combines prior knowledge with data
- **Cons**: Complex, requires prior calibration, harder to explain

### Recommendation

**Option C: Confidence-Based Tiers (Hybrid Approach)**

```python
class PatternSignificancePolicy:
    UNIVERSAL_MINIMUM = 0.10  # Absolute floor

    def evaluate(self, pattern):
        p_value = pattern.p_value
        domain = pattern.domain

        # Tier the confidence
        if p_value < 0.01:
            confidence = 'HIGH'
            recommendation = 'APPROVE_CANDIDATE'
        elif p_value < 0.05:
            confidence = 'MEDIUM'
            recommendation = self._medium_confidence_logic(pattern)
        elif p_value < 0.10:
            confidence = 'LOW'
            recommendation = self._low_confidence_logic(pattern)
        else:
            confidence = 'NONE'
            recommendation = 'REJECT'

        return {
            'confidence': confidence,
            'p_value': p_value,
            'recommendation': recommendation,
            'explanation': self._explain_decision(pattern, confidence)
        }

    def _medium_confidence_logic(self, pattern):
        """Context-specific handling of p < 0.05"""

        # Strict domains require higher standard
        if pattern.domain in ['valuation', 'market_timing']:
            return 'REJECT', 'Requires p < 0.01 for this domain'

        # Standard domains accept p < 0.05
        elif pattern.domain in ['financial_metrics', 'business_model']:
            return 'APPROVE_CANDIDATE', 'Meets standard threshold'

        # Qualitative domains with caveats
        else:
            return 'APPROVE_WITH_CAVEATS', 'Borderline significance, requires qualitative support'

    def _low_confidence_logic(self, pattern):
        """Handle suggestive but not definitive patterns"""

        # Never accept low confidence for market timing
        if pattern.domain == 'market_timing':
            return 'REJECT', 'Insufficient for market timing'

        # Accept for qualitative domains if strong effect size
        elif pattern.domain == 'strategy_management' and pattern.effect_size > 0.8:
            return 'PROBATIONARY', 'Weak statistical significance but strong effect, needs validation'

        else:
            return 'REJECT', 'Insufficient statistical evidence'
```

**Summary Table**:

| Domain            | p < 0.01 | p < 0.05           | p < 0.10                      | Notes                         |
| ----------------- | -------- | ------------------ | ----------------------------- | ----------------------------- |
| Financial Metrics | Approve  | Approve            | Probation                     | Standard rigor                |
| Business Model    | Approve  | Approve            | Approve w/ caveats            | More stable patterns          |
| Strategy/Mgmt     | Approve  | Approve w/ caveats | Probation if effect size >0.8 | Small samples                 |
| Valuation         | Approve  | Reject             | Reject                        | Regime-dependent, high rigor  |
| Market Timing     | Approve  | Reject             | Reject                        | Mostly noise, very high rigor |

**Rationale**:

- Maintains 0.05 as baseline but applies contextual logic
- Transparent tiers easier to explain than variable thresholds
- Human still makes final decision with full context
- Prevents both false positives (strict on timing) and false negatives (lenient on strategy)

### Trade-offs

| Approach         | Scientific Rigor | Flexibility | Complexity | Explainability |
| ---------------- | ---------------- | ----------- | ---------- | -------------- |
| Universal 0.05   | High             | Low         | Low        | High           |
| Domain-specific  | Medium           | High        | Medium     | Medium         |
| Confidence tiers | High             | High        | Medium     | High           |
| Bayesian         | Highest          | Highest     | High       | Low            |

---

## Summary & Recommendations

| Decision               | Recommendation                            | Rationale                                | Priority |
| ---------------------- | ----------------------------------------- | ---------------------------------------- | -------- |
| Trigger priority       | Sliding window w/ cooldown                | Balance responsiveness & human bandwidth | HIGH     |
| Human bandwidth        | Tiered validation (auto-approve 40-60%)   | Scale from MVP to production             | HIGH     |
| Probation duration     | Adaptive (90-365 days based on frequency) | Context-appropriate waiting periods      | MEDIUM   |
| Significance threshold | Confidence tiers with domain logic        | Flexible but principled                  | MEDIUM   |

## Implementation Order

1. **Phase 2 (Months 3-4)**: Implement basic Gate 6 with conservative settings

   - Trigger: 50 outcomes OR 30 days (no auto-approval)
   - Probation: Fixed 6 months, 3 additional occurrences
   - Significance: Universal p < 0.05
   - **Goal**: Establish baseline, gather data on validation volumes

2. **Phase 3 (Months 5-6)**: Add sophistication based on learnings

   - Trigger: Add 7-day cooldown, urgency levels
   - Probation: Implement adaptive durations
   - Significance: Add confidence tiers
   - **Goal**: Optimize for scale

3. **Phase 4 (Months 7-8)**: Enable auto-approval

   - Validation: Begin auto-approving low-risk items (20% of queue)
   - Monitor: Track auto-approval accuracy
   - **Goal**: Reduce human burden

4. **Phase 5 (Months 9+)**: Continuous refinement
   - Scale auto-approval to 40-60%
   - Implement Bayesian priors if needed
   - **Goal**: Achieve sustainable scale

---

**Next Actions**:

1. Review recommendations with stakeholders
2. Build prototype validation interface
3. Simulate capacity under different volume scenarios
4. Define auto-approval rules for Phase 4
