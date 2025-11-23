# DD-010: Data Contradiction Resolution with Timeout and Fallback

**Status**: Implemented
**Date**: 2025-11-18
**Decider(s)**: System Architect
**Related Docs**:

- [Data Management](../operations/03-data-management.md)
- [Human Integration](../operations/02-human-integration.md)
- [Collaboration Protocols](../architecture/07-collaboration-protocols.md)

**Related Decisions**:

- [DD-003: Debate Deadlock Resolution](DD-003_DEBATE_DEADLOCK_RESOLUTION.md) - Similar 4-level escalation pattern
- [DD-008: Agent Credibility System](DD-008_AGENT_CREDIBILITY_SYSTEM.md) - Credibility tracking framework

---

## Context

### The Problem

Data contradiction resolution had human arbitration but no timeout/fallback, creating pipeline deadlocks when humans unavailable.

**Current Implementation** (`docs/operations/03-data-management.md:337-342`):

```yaml
Contradiction resolution protocols:
  - Identify conflicting memories
  - Weight by recency and credibility
  - Escalate unresolvable conflicts to human # NO TIMEOUT SPECIFIED
  - Document resolution rationale
```

**Critical Gaps**:

1. No timeout for human arbitration (indefinite wait)
2. No fallback if human unavailable/overwhelmed
3. No source credibility calculation spec (only mentioned)
4. No queue management for concurrent contradictions
5. No blocking behavior spec for critical data

**Failure Scenarios**:

```text
Scenario 1: Critical data contradiction blocks analysis
  AAPL Revenue Q3 2024:
    - SEC 10-Q: $95.3B (authoritative)
    - Bloomberg: $94.8B (discrepancy $500M)

  Current: Escalate to human, wait indefinitely
  Impact: Analysis paused, no fallback, pipeline blocked

Scenario 2: Human unavailable (weekend/vacation)
  Multiple contradictions queue for review
  No prioritization (critical vs supporting data)
  No timeout → indefinite accumulation

Scenario 3: Source quality tracking missing
  Bloomberg had 30% error rate in contradictions
  System doesn't track source credibility
  Both sources weighted equally despite quality difference
```

**Why This Needs Resolution Now**: Same deadlock pattern as debate resolution (Flaw #8, resolved via DD-003). Data contradictions can block data collection/analysis pipeline when human unavailable, creating bottlenecks.

---

## Decision

**Implement 4-level tiered escalation with source credibility tracking, 6-hour timeout, and credibility-weighted fallback to guarantee zero pipeline deadlocks.**

System escalates contradictions through multiple resolution layers with timeouts at each level, ultimately falling back to credibility-weighted provisional resolution if human unavailable. Pipeline continues with provisional decisions reviewable at Gate 3.

Source credibility tracked via 3-component formula (base accuracy, source type hierarchy, temporal decay with 4-5 year half-life) to enable auto-resolution and informed fallbacks.

---

## Options Considered

### Option 1: Human-Only Resolution (Current - Rejected)

**Description**: All contradictions must be resolved by human before proceeding.

**Pros**:

- Highest data quality
- Direct human oversight
- Simple, clear accountability

**Cons**:

- Pipeline deadlocks when human unavailable
- No scalability (single expert bottleneck)
- Off-hours/weekend delays (24-72hrs)
- Can't handle concurrent contradictions
- No source quality differentiation

**Estimated Effort**: Low (current state)

**Rejection Rationale**: Same deadlock risk as debate resolution (DD-003). Friday evening contradiction blocks analysis until Monday. AAPL revenue contradiction ($500M discrepancy) can't proceed with incomplete data, blocking entire analysis.

---

### Option 2: Always Use Higher-Value Source (Naive - Rejected)

**Description**: Pre-define source hierarchy (SEC > Bloomberg > Reuters), always pick higher-ranked source.

**Pros**:

- Zero deadlocks (instant resolution)
- No human workload
- Simple logic (single hierarchy lookup)
- No credibility tracking needed

**Cons**:

- Ignores historical accuracy (Bloomberg may be more accurate than Reuters for specific data)
- No learning (can't detect when lower-tier source actually more accurate)
- Blind to source quality changes (Bloomberg data quality degrades, still preferred)
- Misses context (SEC filing typo exists, Bloomberg correct, but SEC always wins)
- No human review (systematic errors undetected)

**Estimated Effort**: Low (1-2 days)

**Rejection Rationale**: Too simplistic. Real scenario: SEC 10-Q has typo ($95.3B vs $9.53B), Bloomberg correct ($94.8B), naive hierarchy picks wrong source. No feedback loop to improve. Same issues as "agent-only auto-resolution" rejected in DD-003.

---

### Option 3: 4-Level Tiered Escalation with Source Credibility (Selected)

**Description**: Multi-level escalation with source credibility tracking: evidence quality → credibility auto-resolve → human arbitration → credibility-weighted fallback → Gate 3 review.

**Pros**:

- Zero deadlocks guaranteed (fallback always available)
- Source quality tracked (credibility based on historical outcomes)
- Workload management (3 concurrent max, priority routing)
- Provisional decisions reviewed at Gate 3
- Learning loop on source accuracy
- Context-aware (SEC typo scenario: human override teaches system)

**Cons**:

- More complex implementation (credibility tracking system)
- Requires source credibility database
- Provisional decisions may need override at Gate 3
- 3-component credibility formula (vs simple hierarchy)

**Estimated Effort**: Medium (2-3 weeks implementation)

---

## Rationale

Option 3 (4-level tiered escalation) chosen because:

**Zero deadlock guarantee**: Automatic fallbacks prevent pipeline blocking, same philosophy as DD-003 (debate resolution).

**Quality preservation**: 4 levels attempt higher-quality resolution before fallback:

1. Evidence quality (SEC filing vs blog post - clear winner)
2. Source credibility (Bloomberg 85% vs Reuters 70% - auto-resolve)
3. Human arbitration (expert judgment)
4. Credibility-weighted fallback (use higher credibility source provisionally)

**Safety net**: Provisional resolutions reviewed at Gate 3 before finalization (assumption validation gate).

**Learning capability**: Tracks source accuracy over time, detects quality changes (Bloomberg upgrades → credibility improves).

**Workload management**: Queue limits + priority routing prevent expert overload, same pattern as DD-003.

**Critical data protection**: CRITICAL contradictions (revenue, margins) **block analysis** if unresolved at Gate 3, ensuring incomplete/uncertain data doesn't drive investment decisions.

Rejected Option 1 (human-only) due to deadlock risk. Rejected Option 2 (naive hierarchy) due to no learning, blind to quality changes, misses context.

---

## Consequences

### Positive Impacts

**Pipeline reliability**: Guaranteed progress, no deadlocks from data contradictions.

**Source quality visibility**: Credibility tracking identifies unreliable sources (Bloomberg 70% vs Reuters 85% - action trigger).

**Expert workload**: Manageable (3 concurrent max, priority routing CRITICAL > HIGH > MEDIUM).

**Transparency**: All provisional resolutions flagged for Gate 3 review.

**Continuous improvement**: Source credibility updated based on contradiction outcomes, system learns over time.

**Critical data protection**: Revenue/margin contradictions block analysis if unresolved, preventing bad investment decisions.

### Negative Impacts / Tradeoffs

**Complexity**: Source credibility system (3 components: base accuracy, source type, temporal decay) more complex than simple hierarchy.

**Provisional risk**: Credibility-weighted fallback may be overridden at Gate 3 (requires data refetch if different source selected).

**Data requirements**: Source credibility requires 15+ historical contradiction outcomes per source for statistical reliability.

**Testing burden**: 6 scenarios required (unavailability, overload, timeouts, credibility auto-resolve, blocking behavior, Gate 3 override).

### Affected Components

**Data Collector Agent**: Source credibility lookup before storing data, contradiction detection triggers escalation flow.

**Lead Coordinator**: Queue management for concurrent contradictions, priority routing, workload tracking.

**Human Gates**: Gate 3 (provisional contradiction review UI).

**Memory System**: Source credibility storage (SourceCredibility node), contradiction outcome tracking.

---

## Implementation Notes

### Source Credibility Formula

3-component system (simplified from DD-008's 6-component agent credibility):

```python
class SourceCredibility:
    """Track data source credibility for contradiction resolution"""

    def calculate_credibility(self, source_id, current_date):
        """Calculate source credibility score (0.0 - 1.0)"""

        # Component 1: Base accuracy (historical contradiction outcomes)
        base_accuracy = self.get_historical_accuracy(source_id)
        # Example: Bloomberg correct in 70 of 100 contradictions = 0.70

        # Component 2: Source type weight (hierarchy)
        source_type_weight = self.get_source_type_weight(source_id)
        # SEC filings: 1.0 (authoritative)
        # Bloomberg/Refinitiv: 0.95 (professional data providers)
        # Reuters/news: 0.90 (reputable but less authoritative)
        # Alt data providers: 0.85
        # Blogs/unverified: 0.70

        # Component 3: Temporal decay (4-5 year half-life)
        temporal_weight = self.calculate_temporal_weight(source_id, current_date)
        # Exponential decay: weight = 0.5^(age_years / 4.5)
        # Longer half-life than agents (4.5yr vs 2yr) - sources more stable

        credibility = base_accuracy * source_type_weight * temporal_weight

        return credibility

    def get_historical_accuracy(self, source_id):
        """Calculate base accuracy from contradiction outcomes"""

        outcomes = self.get_contradiction_outcomes(source_id)

        if len(outcomes) < 15:
            # Insufficient data - use source type weight only
            return 1.0  # Neutral (type weight will dominate)

        # Time-weighted accuracy
        total_weight = 0
        correct_weight = 0

        for outcome in outcomes:
            age_years = (current_date - outcome.date).days / 365.0
            weight = 0.5 ** (age_years / 4.5)  # 4.5yr half-life

            total_weight += weight
            if outcome.source_was_correct:
                correct_weight += weight

        return correct_weight / total_weight if total_weight > 0 else 0.80  # Default

    def get_source_type_weight(self, source_id):
        """Get source type hierarchy weight"""

        source_type = self.get_source_type(source_id)

        weights = {
            'SEC_FILING': 1.00,     # 10-K, 10-Q, 8-K, proxies (authoritative)
            'BLOOMBERG': 0.95,      # Bloomberg Terminal
            'REFINITIV': 0.95,      # Refinitiv Eikon
            'FACTSET': 0.95,        # FactSet
            'REUTERS': 0.90,        # Reuters news/data
            'FINANCIAL_API': 0.85,  # Third-party financial data APIs
            'ALT_DATA': 0.85,       # Alternative data providers
            'NEWS': 0.80,           # General financial news
            'BLOG': 0.70,           # Unverified sources
        }

        return weights.get(source_type, 0.75)  # Default for unknown

    def calculate_temporal_weight(self, source_id, current_date):
        """Calculate temporal decay weight"""

        # Get most recent accuracy measurement date
        last_update = self.get_last_credibility_update(source_id)

        if not last_update:
            return 1.0  # No decay if no history

        age_years = (current_date - last_update).days / 365.0

        # 4.5-year half-life (sources more stable than agents)
        decay_halflife = 4.5
        weight = 0.5 ** (age_years / decay_halflife)

        return weight
```

### 4-Level Escalation System

Aligned with DD-003 debate resolution pattern:

```python
class ContradictionResolver:
    """Resolve data contradictions with tiered escalation"""

    RESOLUTION_TIMEOUT_HOURS = 6
    AUTO_RESOLVE_THRESHOLD = 0.25  # Credibility differential
    FALLBACK_THRESHOLD = 0.10      # Min differential for credibility-weighted fallback
    MAX_CONCURRENT_HUMAN_REVIEWS = 3

    def resolve_contradiction(self, contradiction):
        """4-level escalation matching debate protocol"""

        # Level 1: Evidence Quality Evaluation
        if evidence_clear := self.evaluate_evidence_quality(contradiction):
            return ResolutionResult(
                resolution='evidence_based',
                selected_source=evidence_clear.winner,
                confidence=evidence_clear.confidence,
                level=1,
                reason='Clear evidence quality difference'
            )

        # Level 2: Source Credibility Auto-Resolution
        cred_A = self.credibility_system.calculate_credibility(
            contradiction.source_A.id,
            contradiction.date
        )
        cred_B = self.credibility_system.calculate_credibility(
            contradiction.source_B.id,
            contradiction.date
        )

        cred_diff = abs(cred_A - cred_B)

        if cred_diff > self.AUTO_RESOLVE_THRESHOLD:
            higher_cred = (
                contradiction.source_A if cred_A > cred_B
                else contradiction.source_B
            )

            return ResolutionResult(
                resolution='credibility_auto_resolved',
                selected_source=higher_cred,
                confidence=max(cred_A, cred_B) * 0.90,  # 10% penalty for auto-resolution
                level=2,
                reason=f'Credibility differential {cred_diff:.2f} > {self.AUTO_RESOLVE_THRESHOLD}',
                requires_human_review=False
            )

        # Level 3: Human Arbitration (with queue management)
        if self.human_queue_available():
            try:
                human_resolution = self.escalate_to_human(
                    contradiction,
                    timeout_hours=self.RESOLUTION_TIMEOUT_HOURS,
                    priority=self.classify_priority(contradiction)
                )
                return human_resolution

            except TimeoutError:
                # Proceed to Level 4 fallback
                pass

        # Level 4: Credibility-Weighted Fallback
        if cred_diff > self.FALLBACK_THRESHOLD:
            # Use higher-credibility source provisionally
            higher_cred = (
                contradiction.source_A if cred_A > cred_B
                else contradiction.source_B
            )

            return ResolutionResult(
                resolution='provisional_credibility_weighted',
                selected_source=higher_cred,
                confidence=max(cred_A, cred_B) * 0.75,  # 25% penalty for timeout fallback
                level=4,
                reason='Human timeout, credibility-weighted fallback',
                requires_human_review=True,
                review_gate=3
            )
        else:
            # Credibility too close, mark both uncertain
            return ResolutionResult(
                resolution='provisional_uncertainty',
                action='mark_both_uncertain',
                confidence=0.50,
                level=4,
                reason='Human timeout, credibility differential too small',
                requires_human_review=True,
                review_gate=3,
                blocking_if_critical=True  # Block analysis if CRITICAL data
            )

    def evaluate_evidence_quality(self, contradiction):
        """Level 1: Clear evidence quality difference?"""

        # SEC filing vs non-SEC: SEC wins (authoritative source)
        if (contradiction.source_A.type == 'SEC_FILING' and
            contradiction.source_B.type != 'SEC_FILING'):
            return EvidenceResult(
                winner=contradiction.source_A,
                confidence=0.95,
                reason='SEC filing authoritative vs non-SEC'
            )

        if (contradiction.source_B.type == 'SEC_FILING' and
            contradiction.source_A.type != 'SEC_FILING'):
            return EvidenceResult(
                winner=contradiction.source_B,
                confidence=0.95,
                reason='SEC filing authoritative vs non-SEC'
            )

        # Primary source vs derived: Primary wins
        if (contradiction.source_A.is_primary and
            not contradiction.source_B.is_primary):
            return EvidenceResult(
                winner=contradiction.source_A,
                confidence=0.85,
                reason='Primary source vs derived'
            )

        # More recent data wins (if significant recency gap)
        recency_gap_days = abs(
            (contradiction.source_A.data_date - contradiction.source_B.data_date).days
        )
        if recency_gap_days > 90:  # >3 months gap
            more_recent = (
                contradiction.source_A if
                contradiction.source_A.data_date > contradiction.source_B.data_date
                else contradiction.source_B
            )
            return EvidenceResult(
                winner=more_recent,
                confidence=0.80,
                reason=f'Recency gap {recency_gap_days} days'
            )

        # No clear evidence winner
        return None

    def classify_priority(self, contradiction):
        """Priority routing (similar to debate priority)"""

        # CRITICAL: Core financial metrics
        critical_fields = [
            'revenue', 'net_income', 'operating_margin',
            'gross_margin', 'debt', 'cash_flow_from_operations',
            'free_cash_flow', 'shares_outstanding'
        ]

        # HIGH: Valuation-impacting metrics (>5% impact)
        high_impact_fields = [
            'capex', 'depreciation', 'tax_rate', 'working_capital',
            'ebitda', 'operating_income'
        ]

        if contradiction.field in critical_fields:
            return 'CRITICAL'  # Review within 6hr, blocks analysis if unresolved
        elif contradiction.field in high_impact_fields:
            return 'HIGH'  # Review within 12hr
        elif contradiction.valuation_impact_pct > 0.05:  # >5% valuation impact
            return 'HIGH'
        else:
            return 'MEDIUM'  # Review at Gate 3

    def human_queue_available(self):
        """Check if human queue has capacity"""
        current_queue_depth = self.get_queue_depth()
        return current_queue_depth < self.MAX_CONCURRENT_HUMAN_REVIEWS

    def should_block_analysis(self, resolution, contradiction):
        """Determine if unresolved contradiction should block analysis"""

        # CRITICAL contradictions must be resolved before proceeding
        if (contradiction.priority == 'CRITICAL' and
            resolution.resolution == 'provisional_uncertainty'):
            return True

        # HIGH/MEDIUM can proceed with provisional
        return False
```

### Gate 3 Integration

**Gate 3 UI Specification** (Provisional Contradiction Review):

```yaml
Gate 3: Assumption Validation

  Sections:
    - DCF Assumptions (existing)
    - Financial Statement Assumptions (existing)
    - Data Quality Review (existing)
    - Provisional Contradiction Review (NEW)

  Provisional Contradiction Review:
    Display:
      - Contradiction count: "2 provisional contradictions require review"
      - For each contradiction:
          * Data field: "AAPL Revenue Q3 2024"
          * Source A: "SEC 10-Q: $95.3B (credibility 0.88)"
          * Source B: "Bloomberg: $94.8B (credibility 0.82)"
          * Provisional resolution: "Using SEC 10-Q ($95.3B, confidence 0.75)"
          * Reason: "Human timeout, credibility-weighted fallback"
          * Valuation impact: "±$2.50/share if override to Bloomberg"

    Human Actions:
      - Confirm provisional (becomes final, confidence → 0.90)
      - Override to other source (triggers data refetch, downstream updates)
      - Mark uncertain (use conservative estimates, confidence → 0.50)
      - Request more investigation (pause analysis, escalate to data team)

    Blocking Behavior:
      - CRITICAL contradictions unresolved → "CANNOT PROCEED" button disabled
      - HIGH/MEDIUM contradictions → "PROCEED WITH PROVISIONAL" button enabled
      - Warning: "2 provisional resolutions will be used, reviewable at Gate 5"
```

### Queue Management

Same pattern as DD-003 debate resolution:

```python
class ContradictionQueue:
    """Manage concurrent contradiction reviews"""

    MAX_CONCURRENT = 3  # Per expert

    def add_to_queue(self, contradiction, priority):
        """Add contradiction to human review queue"""

        current_queue = self.get_current_queue()

        if len(current_queue) >= self.MAX_CONCURRENT:
            # Queue full - check priority
            if priority == 'CRITICAL':
                # Bump lowest priority item
                lowest_priority = min(current_queue, key=lambda x: x.priority_rank)
                if lowest_priority.priority_rank < self.priority_rank(priority):
                    # Remove lowest, add critical
                    self.defer_to_gate_3(lowest_priority)
                    current_queue.remove(lowest_priority)
                else:
                    # All items critical, defer this one
                    self.defer_to_gate_3(contradiction)
                    return None
            else:
                # HIGH/MEDIUM - defer to Gate 3
                self.defer_to_gate_3(contradiction)
                return None

        # Add to queue
        queue_item = QueueItem(
            contradiction=contradiction,
            priority=priority,
            added_at=datetime.now(),
            timeout_at=datetime.now() + timedelta(hours=6)
        )
        current_queue.append(queue_item)

        return queue_item

    def priority_rank(self, priority):
        """Priority ranking for queue management"""
        return {'CRITICAL': 3, 'HIGH': 2, 'MEDIUM': 1}[priority]
```

### Testing Requirements

**6 comprehensive scenarios**:

1. **Human unavailability** (off-hours, vacation)

   - Friday 6pm contradiction, human unavailable until Monday
   - Verify: 6hr timeout → credibility-weighted fallback → Gate 3 review

2. **Concurrent contradiction overload** (5+ simultaneous)

   - 5 contradictions, 3 queue slots
   - Verify: CRITICAL bumps MEDIUM, deferred to Gate 3

3. **Queue priority management**

   - CRITICAL + HIGH + MEDIUM in queue
   - New CRITICAL arrives
   - Verify: MEDIUM deferred, new CRITICAL added

4. **Credibility-based auto-resolution**

   - Bloomberg (0.85) vs Reuters (0.65)
   - Differential 0.20 > 0.25? No
   - Differential 0.30 > 0.25? Yes → auto-resolve to Bloomberg

5. **Critical data blocking**

   - Revenue contradiction unresolved at Gate 3
   - Verify: Analysis BLOCKED, "Cannot Proceed" button disabled

6. **Gate 3 provisional override**
   - Human overrides provisional (SEC → Bloomberg)
   - Verify: Data refetch, downstream recalculation, source credibility updated

### Critical Constraints

**Performance target**: <500ms contradiction resolution (Levels 1-2)

**Data requirements**:

- Source credibility: 15+ historical outcomes per source
- Graceful degradation: Use source type weight if <15 outcomes

**Backward compatibility**: Support new sources with <6 months operational history

- Use source type weight only (credibility = 1.0 \* type_weight)
- No temporal decay if insufficient history

### Rollback Strategy

**Phase 1: Parallel Calculation** (Week 1)

- Calculate both naive hierarchy and credibility-weighted resolution
- Use naive hierarchy for decisions (production)
- Log credibility-weighted (shadow mode)
- Compare accuracy, identify outliers

**Phase 2: A/B Testing** (Week 2)

- 50% contradictions use credibility-weighted
- 50% use naive hierarchy
- Measure resolution accuracy, human override rates

**Phase 3: Full Rollout** (Week 3)

- 100% use credibility-weighted
- Monitor for regressions
- Keep naive hierarchy for 30 days (rollback option)

**Rollback Trigger**: If credibility-weighted shows:

- Resolution accuracy <80% (vs >85% target)
- Human override rate >30% at Gate 3 (vs <20% target)
- Calculation latency >1000ms (vs <500ms target)

**Rollback Procedure**:

1. Switch to naive hierarchy (1-line config change)
2. Investigate root cause (evidence evaluation? credibility formula?)
3. Fix in shadow mode, re-validate
4. Re-attempt rollout

---

**Estimated Implementation Effort**: 2-3 weeks

**Breakdown**:

- Week 1: Source credibility system (3 components), database schema
- Week 2: Escalation logic (4 levels), queue management, Gate 3 UI
- Week 3: Testing (6 scenarios), documentation updates

**Dependencies**:

**Must Be Completed First**:

- Memory system operational (source credibility storage)
- Gate 3 UI functional (provisional review integration)

**External Systems/APIs Required**:

- None (uses existing data sources)

---

## Open Questions

**1. Source type hierarchy completeness?**

Current taxonomy: SEC, Bloomberg, Refinitiv, FactSet, Reuters, Financial APIs, Alt Data, News, Blog

**Missing source types**:

- Company IR websites (investor relations)
- Regulatory filings (non-SEC, e.g., international)
- Third-party research (Morningstar, S&P Capital IQ)

**Options**:

- A) Keep 9 types (sufficient for 90%+ of contradictions)
- B) Expand to 12-15 types (better coverage, more maintenance)

**Recommendation**: Start with 9 types (Option A), add specialized types if needed

**2. Temporal decay half-life validation?**

Current: 4.5-year half-life for sources (vs 2-year for agents)

**Too short** (2 years): Penalizes stable sources unnecessarily
**Too long** (7 years): Doesn't capture quality changes fast enough

**Options**:

- A) Fixed 4.5-year (simple, consistent)
- B) Source-type-specific (SEC=7yr, Bloomberg=4yr, News=2yr)
- C) A/B test on historical data (2yr, 4yr, 6yr), select best

**Recommendation**: Start with 4.5yr (Option A), tune if needed

**3. Contradiction outcome tracking mechanism?**

How to determine "source A was correct" in contradiction?

**Options**:

- A) Human labels at resolution (expert marks correct source)
- B) Subsequent filing confirmation (later 10-K confirms which was right)
- C) Consensus (if 3+ sources agree, outlier marked wrong)

**Recommendation**: Hybrid - human labels initially (Option A), validate with subsequent filings (Option B) when available

**Blocking**: No - reasonable defaults available (source type hierarchy if no credibility data)

---

## References

**Internal Documentation**:

- [Design Flaw #19, M6: Data Contradiction Resolution Timeout](../design-flaws/resolved/19-partial-failures.md) - Original problem specification
- [Data Management](../operations/03-data-management.md) - Contradiction resolution protocols
- [Human Integration](../operations/02-human-integration.md) - Gate 3 provisional review
- [DD-003: Debate Deadlock Resolution](DD-003_DEBATE_DEADLOCK_RESOLUTION.md) - 4-level escalation pattern
- [DD-008: Agent Credibility System](DD-008_AGENT_CREDIBILITY_SYSTEM.md) - Credibility tracking framework

**External Research**:

- **Temporal Weighting**: Exponential decay models (same as DD-008)
- **Confidence Intervals**: Wilson score interval for binomial proportions
- **Data Quality Assessment**: "Assessing Data Quality for Healthcare Systems" - source credibility metrics

**Similar Decisions in Other Systems**:

- **Wikipedia**: Source reliability ratings (reliable, generally reliable, unreliable)
- **Credit bureaus**: Data furnisher credibility scoring (TransUnion, Equifax, Experian)
- **News aggregators**: Publisher credibility (AP, Reuters > blogs)

---

## Status History

| Date       | Status      | Notes                                     |
| ---------- | ----------- | ----------------------------------------- |
| 2025-11-18 | Proposed    | Initial proposal from Flaw #19, M6        |
| 2025-11-18 | Approved    | Approved by system architect              |
| 2025-11-18 | Implemented | Design docs updated, code pending Phase 2 |

**Next Steps**:

1. Code implementation (Week 1-2): SourceCredibility class, escalation logic, queue management
2. Database schema updates (Week 2): SourceCredibility node, contradiction outcome tracking
3. Gate 3 UI integration (Week 2-3): Provisional contradiction review section
4. Testing & validation (Week 3): 6 scenarios, historical data validation

---

## Notes

**Design Philosophy**: This decision mirrors DD-003 (debate resolution) - same 4-level escalation, same timeout, same conservative fallback philosophy. Consistency across contradiction types (data vs agent debates) reduces cognitive load and implementation complexity.

**Why source credibility simpler than agent credibility**: Sources don't improve/degrade like agents (Bloomberg API doesn't "learn"), no market regime dependency (SEC filing quality constant across bull/bear markets), no human override patterns (humans override agents, not sources). 3 components (base accuracy, source type, temporal decay) vs 6 for agents (adds regime, trend, override).

**Critical data blocking rationale**: For fundamental investment analysis, incomplete/uncertain critical data (revenue, margins) can lead to incorrect decisions. Better to pause at Gate 3 and resolve than proceed with 50% confidence and make bad investment. HIGH/MEDIUM data can proceed provisionally because errors less impactful.

**Future Enhancements** (Post-Phase 4):

- Multi-source consensus (if 3+ sources agree, auto-resolve)
- Source-specific credibility (Bloomberg revenue credibility vs Bloomberg capex credibility)
- Contradiction pattern mining (certain fields chronically contradictory → upstream data quality issue)
- Automated source quality monitoring (trigger alerts when credibility drops <70%)
