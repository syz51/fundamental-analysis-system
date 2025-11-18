# Learning Systems

## Overview

The fundamental analysis system implements a comprehensive learning architecture that enables continuous improvement through systematic outcome tracking and pattern discovery. The system learns from every analysis, prediction, and decision, building institutional knowledge that enhances future accuracy.

This learning approach is designed to:

- Capture actual outcomes and compare them to predictions
- Identify recurring patterns that predict success or failure
- Improve agent accuracy over time through systematic error correction
- Build institutional memory that compounds value with each analysis
- Prevent false pattern propagation through statistical validation and human oversight

## Learning Validation Framework

**Critical Design Principle**: All learning updates (patterns, credibility scores, lessons) must pass human validation at Gate 6 before being applied to future decisions.

### Workflow

1. System identifies potential patterns/learnings
2. Patterns undergo statistical validation (hold-out, blind testing, control groups)
3. Validated patterns queued for human review at Gate 6
4. Human approves/rejects/modifies learnings
5. Only approved learnings applied to future analyses

### Pattern Status Lifecycle

Patterns move through distinct validation stages:

- **candidate**: Discovered but unvalidated
- **statistically_validated**: Passed hold-out/blind tests
- **human_approved**: Passed Gate 6 validation
- **active**: Currently used in decisions
- **probationary**: Needs more evidence (DD-004: 90-365 day time-box, max 2 extensions)
- **rejected**: Failed validation
- **deprecated**: Previously valid but no longer applicable

**Probation Details** (DD-004): Time-boxed by pattern frequency (monthly=90d, quarterly=180d, annual=365d). Requires 2-5 additional occurrences. Auto-evaluated at deadline: approve if correlation holds, reject if degrades. Max 2 extensions (90d each) if 50%+ progress.

## Outcome Tracking

The system continuously monitors actual outcomes against predictions to measure accuracy and identify systematic errors.

### Decision Tracking

Every investment decision is tracked through multiple checkpoints to measure prediction accuracy:

### Checkpoint Review Process

Regular reviews at 30, 90, 180, and 365 days track:

- Price performance vs. predictions
- Thesis accuracy (did events unfold as expected?)
- Surprise events not anticipated
- Model assumptions vs. actual results

### Accuracy Calculation

For each checkpoint, the system:

1. Retrieves actual performance metrics
2. Compares to original predictions
3. Calculates accuracy scores by domain
4. Updates agent track records
5. Extracts lessons learned
6. Stores outcomes in knowledge base

### Pattern Review Triggers

Significant deviations (>30% error) trigger pattern reviews to understand:

- Why predictions missed
- Whether underlying patterns have changed
- What corrections should be applied

### Post-Mortem Investigation (DD-006)

When checkpoint outcomes deviate >30% from predictions, mandatory post-mortem investigation triggered to conduct root cause analysis and extract negative lessons.

**Trigger Conditions**:

```text
abs(actual_outcome - predicted_outcome) / predicted_outcome > 0.30
```

Applies to both failures (negative outcomes) and missed opportunities (passed stocks that outperformed).

**Post-Mortem Workflow**:

1. **Queue Management**: Async investigation queue (max 5 concurrent), prioritized by deviation severity
2. **Root Cause Analysis**: AI-driven investigation categorizes failure using taxonomy:
   - Data quality issues (missing/incorrect data)
   - Model assumptions (DCF inputs, growth rates)
   - Missing factors (unconsidered variables)
   - Timing (thesis correct, too early/late)
   - Regime change (market conditions shifted)
   - Black swan (unforeseeable events)
3. **Human Review**: Structured questions completed within 48hrs:
   - Primary reason for unexpected outcome
   - Specific factors missed/underweighted
   - Warning signs should have caught
   - What to do differently in similar situations
   - Which patterns need revision
   - Foreseeability rating (1-5 scale)
4. **Success Validation**: For positive outcomes, validate that success was skill, not luck:
   - Thesis decomposition (did predicted drivers occur?)
   - Baseline comparison (performance vs market/sector)
   - Luck vs skill attribution (market/sector/stock-specific contributions)
   - Classification: Genuine Success (reinforce), Partial Success (partial credit), Lucky Success (don't reinforce)
5. **Lesson Broadcasting**: Actionable lessons extracted and applied:
   - Update affected agents (checklists, bias corrections)
   - Propose pattern revisions (for Gate 6 validation)
   - Add to screening filters (if relevant)
   - Store in searchable lesson library
   - Notify human of changes applied

**Failure Categorization Taxonomy**:

| Category          | Description                   | Example                                         |
| ----------------- | ----------------------------- | ----------------------------------------------- |
| Data Quality      | Missing or incorrect data     | Stale financials, unreported debt               |
| Model Assumptions | DCF parameters wrong          | Overstated growth, understated cost of capital  |
| Missing Factors   | Unconsidered variables        | Competitive threat, regulatory change           |
| Timing            | Thesis correct but early/late | Disruption predicted but adoption slower        |
| Regime Change     | Market conditions shifted     | Multiple compression, interest rate environment |
| Black Swan        | Unforeseeable events          | Pandemic, fraud, geopolitical shock             |

**Success Validation Logic**:

To prevent false positive learning (stock goes up for wrong reasons):

```yaml
Luck vs Skill Decomposition:
  market_contribution: Stock return attributable to market performance
  sector_contribution: Stock return attributable to sector performance
  stock_specific_contribution: Stock return unique to company

skill_ratio = stock_specific_contribution × thesis_validation_score

Classification:
  - skill_ratio > 0.6 AND thesis correct → Genuine Success (reinforce pattern)
  - 0.4 < skill_ratio ≤ 0.6 AND beat market → Partial Success (partial credit)
  - skill_ratio ≤ 0.4 → Lucky Success (do not reinforce, prevents false learning)
```

**Integration with Learning System**:

- Post-mortem lessons presented at Gate 6 for validation before pattern revisions applied
- Failure patterns stored in central knowledge graph for future reference
- Agents receive lesson updates to prevent recurrence
- Dashboard tracks "lessons learned from failures" by category

Complete specification: [DD-006: Negative Feedback System](../design-decisions/DD-006_NEGATIVE_FEEDBACK_SYSTEM.md)

### Post-Mortem Priority Algorithm (Queue Management)

When multiple post-mortems are triggered simultaneously, the system uses a weighted priority formula to determine investigation order. This ensures the most impactful failures are analyzed first while balancing percentage deviation, absolute financial loss, portfolio impact, and systemic risk factors.

#### Priority Calculation Formula

```python
class PostMortemPriority:
    """Calculate priority for post-mortem queue"""

    WEIGHTS = {
        'deviation_pct': 0.25,      # Prediction accuracy miss
        'absolute_loss': 0.35,      # Dollar impact (highest weight)
        'portfolio_impact': 0.30,   # % of total portfolio
        'systemic_risk': 0.10       # Sector/pattern failure indicator
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

    def _normalize_portfolio(self, portfolio_pct):
        """Linear normalization for portfolio impact"""
        # 1% → 0.20, 5% → 1.0 (capped)
        return min(portfolio_pct / 5.0, 1.0)

    def _assess_systemic(self, outcome):
        """Check if failure indicates systemic issue"""
        # High if multiple stocks in same sector failed
        sector_failures = self.count_sector_failures(
            outcome.sector,
            lookback_days=90
        )
        return min(sector_failures / 5, 1.0)  # Max at 5 failures
```

#### Priority Calculation Example

```text
Queue at Year-End Checkpoint:

Stock A (MSFT):
  Predicted: +20% return, Actual: -50%
  Deviation: |(-50 - 20)|/20 = 350%
  Investment: $100K position → Lost $50K
  Portfolio: 5% of total

  Factors:
    - deviation_pct: 0.95 (very high)
    - absolute_loss: 0.85 ($50K significant)
    - portfolio_impact: 1.0 (5% is high)
    - systemic_risk: 0.20 (tech sector has 1 other failure)

  Priority = 0.95*25 + 0.85*35 + 1.0*30 + 0.20*10
           = 23.75 + 29.75 + 30 + 2
           = 85.5 (HIGH PRIORITY)

Stock B (Small cap):
  Predicted: +5% return, Actual: -30%
  Deviation: |(-30 - 5)|/5 = 700%
  Investment: $10K position → Lost $3K
  Portfolio: 0.5% of total

  Factors:
    - deviation_pct: 0.98 (extremely high)
    - absolute_loss: 0.48 ($3K moderate)
    - portfolio_impact: 0.10 (0.5% is small)
    - systemic_risk: 0.0 (no other failures in sector)

  Priority = 0.98*25 + 0.48*35 + 0.10*30 + 0.0*10
           = 24.5 + 16.8 + 3 + 0
           = 44.3 (MEDIUM PRIORITY)

Result: Stock A investigated first despite lower % deviation
        (absolute loss and portfolio impact dominate)
```

#### Queue Management Rules

- **Max concurrent**: 5 post-mortems (per DD-006)
- **Overflow handling**: Queue additional by priority, process when slots free
- **Re-prioritization**: Daily recalculation as new failures added
- **Timeout**: 48 hours for human response (per DD-006)
- **Systemic escalation**: If systemic_risk factor >0.60, flag for immediate review

## Pattern Discovery and Validation

The system continuously mines historical data to identify recurring patterns while preventing confirmation bias through rigorous statistical validation.

### Pattern Evolution

Active patterns are continuously monitored for:

- **Performance degradation**: Pattern accuracy declining over time
- **Performance improvement**: Pattern becoming more reliable
- **Regime changes**: Market conditions affecting pattern validity

When patterns degrade significantly (>20% accuracy drop), they are:

1. Marked as deprecated
2. Investigated for root causes
3. Updated with validity conditions
4. Potentially retired or modified

### Statistical Validation Process

New pattern discovery follows a rigorous three-stage validation:

#### Data Splitting

- **Training set**: 70% (chronologically first, for pattern discovery)
- **Validation set**: 15% (middle period, for parameter tuning)
- **Test set**: 15% (most recent, for final validation)

Chronological splitting prevents data leakage and ensures patterns work on unseen future data.

#### Discovery on Training Data

Patterns are mined from training data only, requiring:

- Minimum 5 occurrences
- Minimum 0.7 correlation with outcomes
- Logical causal mechanism (not just correlation)

#### Hold-Out Validation

Candidate patterns tested on validation set:

- Must maintain >0.65 correlation
- Must have at least 3 confirming instances
- Performance must be within 20% of training accuracy

#### Final Testing

Patterns passing validation undergo final test on unseen data:

- Test on most recent 15% of data
- Must maintain >0.65 correlation
- Records training, validation, and test accuracy

### Pattern Failure Investigation

When patterns stop working, the system investigates:

#### Change Point Detection

Identify when pattern accuracy began declining using statistical methods.

#### Regime Change Analysis

Check if market regime shifts correlate with pattern failure:

- Interest rate environment changes
- Sector rotation patterns
- Regulatory environment shifts
- Technology disruption cycles

#### Structural Break Detection

Identify fundamental changes in the business environment:

- Industry consolidation
- New competitive dynamics
- Technological obsolescence
- Regulatory changes

#### Pattern Update

Based on investigation, patterns receive validity conditions:

- Time boundaries ("valid until date X")
- Regime dependencies ("only works in low rate environment")
- Structural factors ("requires fragmented competition")

### Implementation Requirements

Complete 3-tier validation architecture specified in [DD-007](../design-decisions/DD-007_PATTERN_VALIDATION_ARCHITECTURE.md). Implementation requires:

**Core Components**:

1. **PatternValidationPipeline** - Orchestrates all three validation tiers
2. **HoldOutValidator** - Chronological train/val/test split logic
3. **BlindTestingFramework** - Shadow analysis infrastructure (6-month evaluation)
4. **ControlGroupManager** - A/B testing with statistical significance tests
5. **PatternLifecycleManager** - Status transitions from candidate → active
6. **QuarantineEnforcer** - Prevents unvalidated patterns from reaching agents

**Success Criteria** (all must pass):

- Hold-out validation: >0.65 correlation on test set, <20% degradation from training
- Blind testing: Pattern helps >1.5x more than hurts (6-month evaluation, 10+ comparisons)
- Statistical significance: p < 0.05 improvement vs control group (domain-specific thresholds apply)

**Expected Pass Rates**:

- Hold-out: ~70% of candidates
- Blind testing: ~60% of hold-out survivors
- Control groups: ~70% of blind survivors
- **Overall**: ~30% of candidates become active patterns (aggressive filtering intentional)

**Integration Points**:

- Knowledge Base Agent: Pattern lifecycle management, quarantine storage
- Memory System: Validation metadata tracking (see [Memory System](../architecture/02-memory-system.md#pattern-validation-knowledge-graph-extensions))
- Gate 6: Human review of statistically validated patterns
- All Specialist Agents: Only consume active (validated + approved) patterns

**Implementation Phase**: Phase 3 (Months 5-6), estimated 6-8 weeks

### Auto-Approval Validation Framework

Gate 6 implements auto-approval for low-risk learnings (DD-004: credibility changes <0.05, high-confidence lessons) to manage human bandwidth at scale (target 50-60% auto-approval in production). However, auto-approval without validation creates critical risk: deploying untested auto-approval that propagates incorrect learnings system-wide.

**Validation Requirements** (DD-014): Auto-approval must pass two-stage validation before production deployment:

#### Shadow Mode Validation (Pre-Deployment)

Before enabling auto-approval, run 90-day shadow mode:

- **Duration**: 90 days AND ≥100 decisions (both required, no early exit)
- **Process**: Compute auto-approval decision but send all items to human anyway
- **Comparison**: Compare auto-approval recommendation vs human decision after review
- **Validation**: Achieve >95% agreement with statistical significance (p < 0.05)

**Conservative Error Rate Targets**:
- False positive rate ≤1% (auto-approve when shouldn't - most dangerous)
- False negative rate ≤5% (send to human when could auto-approve - inefficient but safe)
- Overall accuracy >95% required before enabling

**Rationale**: False positives propagate incorrect learnings to all agents, degrading decision quality. Conservative 1% FP threshold (vs 2-5% industry standard) prioritizes correctness. Shadow mode ensures auto-approval tested on real decisions before deployment.

#### Continuous Monitoring (Post-Deployment)

After enabling auto-approval, continuous monitoring with automatic rollback:

- **Accuracy tracking**: 14-day rolling window (conservative, smooths short-term volatility)
- **Rollback trigger**: 94% accuracy (1% buffer below 95% target, triggers investigation)
- **Auto-disable**: 92% accuracy (hard floor, immediate shutdown without human intervention)
- **Spot-check audits**: 10% random sample, weekly (catches errors monitoring might miss)

**Rollback Actions**:

| Accuracy (14d) | Action                     | Timeline  |
| -------------- | -------------------------- | --------- |
| ≥95%           | Continue normally          | N/A       |
| 94-95%         | Trigger investigation      | 48 hrs    |
| 92-94%         | Reduce auto-approval % 10-15pts | Immediate |
| <92%           | Auto-disable, full audit   | Immediate |

**Rationale**: 14-day window (vs 7-day) reduces false alarms from short-term fluctuations. 94% threshold provides early warning before disabling. 92% hard floor prevents runaway quality degradation. Weekly spot-checks verify automated monitoring accuracy.

#### Implementation

```python
class AutoApprovalValidator:
    """Shadow mode validation before enabling"""
    SHADOW_MODE_DURATION_DAYS = 90
    MIN_DECISIONS_FOR_VALIDATION = 100
    TARGET_ACCURACY = 0.95
    MAX_FALSE_POSITIVE_RATE = 0.01
    MAX_FALSE_NEGATIVE_RATE = 0.05

class AutoApprovalMonitor:
    """Post-deployment continuous monitoring"""
    ROLLBACK_THRESHOLD = 0.94
    HARD_FLOOR = 0.92
    ROLLING_WINDOW_DAYS = 14
    SPOT_CHECK_SAMPLE_RATE = 0.10
    AUDIT_FREQUENCY_DAYS = 7
```

**Timeline**: Shadow mode runs in Phase 4 (months 7-9), auto-approval enabled in Phase 5 if validated. Conservative parameters ensure safety over speed. See [DD-014](../design-decisions/DD-014_VALIDATION_GAPS_RESOLUTION.md) for complete specifications.

### Blind Testing Quarantine System

Pattern blind testing (DD-007) requires agents unaware of patterns during validation for statistical validity. However, shared infrastructure creates contamination risks: logs exposing pattern usage, L2 cache persistence, knowledge graph queries surfacing patterns, debugging output visibility.

**Contamination Impact**: Blind tests with contamination create circular validation (agents already aware of pattern), invalidating statistical rigor. Prevents detection of false patterns.

**Quarantine Requirements** (DD-014): Zero contamination tolerance during blind tests:

#### Pattern Isolation

When pattern enters blind testing:

1. **Quarantine marking**: Flag pattern as quarantined in knowledge base
2. **Cache flushing**: Remove pattern from all L2/L3 caches (verify zero residual)
3. **Log filtering**: Block pattern ID from logs during test period (scrub debugging output)
4. **Knowledge graph blocking**: Prevent pattern queries (zero accesses during test)
5. **Isolated agents**: Spawn clean agent instances with no pattern history

**Isolation Verification**:
- Automated checks after every blind test (all vectors verified)
- Manual audits weekly during first 6 months (catches subtle contamination)
- Zero tolerance: any contamination detected → invalidate test, restart

#### Contamination Detection

```python
class BlindTestingQuarantine:
    """Isolate patterns during blind testing"""
    CONTAMINATION_TOLERANCE = 0.0  # Zero tolerance

    def quarantine_pattern(self, pattern_id):
        """Mark pattern, prevent agent access, flush caches, filter logs"""
        pass

    def verify_isolation(self, pattern_id):
        """Confirm zero contamination (cache/logs/knowledge graph/agents)"""
        # All checks must pass (zero tolerance)
        return all([cache_clear, logs_filtered, kg_blocked, agents_isolated])

class ContaminationDetector:
    """Detect blind test contamination"""

    def detect_contamination(self, blind_test_results):
        """Scan logs, cache access, knowledge graph queries"""
        # Any contamination signal invalidates test
        return 'CONTAMINATED' if any(signals.values()) else 'CLEAN'
```

**Audit Protocol**:
- Automated checks: Every blind test (100% coverage)
- Manual audits: Weekly for 6 months, then monthly (verify automated checks working)
- Response: Contamination detected → invalidate test, fix vector, strengthen isolation

**Rationale**: Zero contamination (vs "minimal") ensures statistical validity. Defense in depth (cache + logs + knowledge graph + agents) provides redundancy. Automated checks scale, manual audits catch edge cases. See [DD-014](../design-decisions/DD-014_VALIDATION_GAPS_RESOLUTION.md) for complete quarantine specifications.

### Evidence Requirements for Pattern Validation

Pattern validation and re-validation require access to supporting evidence over time ([DD-009](../design-decisions/DD-009_DATA_RETENTION_PATTERN_EVIDENCE.md)). The system implements tiered storage and selective archiving to ensure evidence availability:

**Evidence Lifecycle**:

1. **Pattern Discovery** (Year 0):

   - Pattern identified from analysis of Company XYZ
   - Evidence: SEC filings, processed financial statements, agent analysis
   - Evidence stored in Hot tier (active analysis period)

2. **Pattern Validation** (Year 0-1):

   - Hold-out testing requires original evidence
   - Blind testing tracks performance over 6 months
   - **Tier 1 Archive Created**: Lightweight archive (1-5MB) captures:
     - Pattern metadata and validation results
     - Processed data summaries
     - Agent analysis snapshots
   - Purpose: Safety net if evidence ages out before investment decision

3. **Pattern Usage** (Year 1-5):

   - Pattern used in investment recommendations
   - Evidence migrates through storage tiers (Hot → Warm)
   - **Tier 2 Archive Created** (if critical): Full archive (50-200MB) captures:
     - Complete processed financial data
     - Full agent analysis and debate logs
     - Complete validation history
   - Trigger: Investment decision OR 2-of-4 criteria (confidence >0.7, impact >0.5, validations ≥3)

4. **Pattern Re-Validation** (Year 2-7):

   - Periodic re-validation requires evidence access
   - Evidence in Warm/Cold tier (slower but accessible)
   - Pattern archives ensure evidence available even if tiered storage expires
   - Re-validation prevents pattern drift and degradation

5. **Long-Term Retention** (Year 5-10):
   - Original evidence in Cold tier or expired
   - Pattern archives provide evidence for:
     - Deep post-mortem failure investigations
     - Regulatory compliance audits
     - Agent training on historical patterns
   - Critical patterns (Tier 2) retained 10 years
   - Standard patterns (Tier 1) retained 7 years

**Pattern-Aware Retention**:

Before deleting aging evidence from Cold tier, system checks:

- Does file support any active patterns? (query knowledge graph)
- Is file already archived in pattern archive? (check index)
- If yes: Retain in Cold OR safe to delete (if archived)

**Evidence Requirements by Validation Stage**:

| Stage              | Evidence Needed                    | Retention Strategy                      |
| ------------------ | ---------------------------------- | --------------------------------------- |
| **Discovery**      | Full raw + processed data          | Hot tier (0-2yr)                        |
| **Hold-Out**       | Training, validation, test sets    | Hot tier + Tier 1 archive at validation |
| **Blind Testing**  | 6-month performance tracking       | Warm tier (2-5yr)                       |
| **Control Groups** | A/B comparison data                | Warm tier                               |
| **Re-Validation**  | Historical evidence for re-testing | Cold tier (5-10yr) OR Tier 1/2 archive  |
| **Post-Mortem**    | Complete evidence trail            | Tier 2 archive (critical patterns only) |

**Archive Coverage**:

- **Tier 1 (Lightweight)**: 80% of validated patterns

  - Sufficient for most re-validation needs
  - 7-year retention
  - Cost: ~$0.02/mo for all archives

- **Tier 2 (Full)**: 10-20% of patterns (critical only)
  - Investment decisions, high-confidence, high-impact patterns
  - 10-year retention
  - Cost: ~$0.20/mo for all archives

**Integration with Validation Pipeline**:

```python
# When pattern passes validation, create Tier 1 archive
def on_pattern_validated(pattern):
    archive_manager.create_tier1_archive(
        pattern_id=pattern.id,
        evidence_refs=pattern.evidence_files,
        validation_results=pattern.validation_metadata
    )

    # Update pattern node in knowledge graph
    pattern.archive_tier = 1
    pattern.tier1_created_date = now()

# When pattern used in investment decision, create Tier 2 archive
def on_investment_decision(pattern, decision):
    if not pattern.archive_tier == 2:
        archive_manager.create_tier2_archive(
            pattern_id=pattern.id,
            evidence_refs=pattern.evidence_files,
            agent_analysis=decision.analysis_logs,
            validation_history=pattern.all_validations
        )

        # Mark as critical
        pattern.archive_tier = 2
        pattern.tier2_created_date = now()
        pattern.is_critical = True
        pattern.used_in_investment_decision = True
```

**Benefits**:

- **Continuous Re-Validation**: Evidence available for periodic pattern testing
- **Failure Investigation**: Post-mortems can review original evidence
- **Regulatory Compliance**: Investment decisions have complete audit trail
- **Agent Training**: New agents learn from historical pattern examples
- **Cost-Effective**: Selective archiving (10-20%) vs archiving all evidence (100%)

### Pattern Archive Lifecycle and Promotion

Deprecated patterns archived to cold storage can be promoted back to active status when they become relevant again ([DD-013](../design-decisions/DD-013_ARCHIVE_LIFECYCLE_MANAGEMENT.md)). This enables multi-year learning evolution and regime adaptation.

#### Deprecated Pattern Retention

When patterns are deprecated (performance degradation >20%), the system retains supporting evidence for 18 months to enable post-mortem investigations:

**Retention Logic**:

```yaml
Deprecated Pattern Evidence Retention:
  Early-stage deprecated (candidate/statistically_validated):
    - Retention: 18 months
    - Archive requirement: Tier 1 (lightweight) sufficient

  Late-stage deprecated (human_approved/active/probationary):
    - Retention: 18 months
    - Archive requirement: Tier 2 (full) required
    - Blocks deletion if Tier 2 missing

  Under Investigation:
    - Retention: Unlimited (until investigation completes)
    - Post-mortem lock prevents deletion regardless of age
```

**Example - Post-Mortem Protection**:

```text
2023: Pattern "SaaS margin expansion" validated and active
2024: Pattern performance degrades, moved to probationary
2025 Q1: Pattern deprecated after repeated failures
  - Deprecation date recorded
  - Evidence retained for 18 months (expires 2026 Q3)
  - Tier 2 archive verified (full evidence + agent analysis)

2025 Q3: Post-mortem investigation triggered
  - Pattern flagged: under_investigation = true
  - Retention lock applied (blocks expiration)
  - Root cause analysis accesses full evidence trail

2025 Q4: Post-mortem completes
  - Investigation flag cleared
  - Evidence retention resumes normal 18mo countdown
```

#### Archive Promotion System

Archived patterns can be automatically promoted back to active status when market conditions change, enabling the system to leverage historical knowledge:

**Promotion Triggers**:

1. **Regime Change Detection**: Market shifts make old patterns relevant
   - Interest rate changes >2% in 6 months
   - Inflation regime shifts >1% in quarter
   - Industry cycle transitions

2. **Access Frequency**: Pattern accessed 3+ times in 30 days
   - Multiple agents requesting same archived pattern
   - Signals current relevance

3. **Post-Mortem Request**: Human explicitly requests for investigation

4. **Re-Validation Request**: Pattern validation system needs historical comparison

**Example - Regime Change Promotion**:

```text
2020: Pattern "Bank profitability in high-rate environment"
  - Active during 2015-2020 (pre-pandemic)
  - Confidence: 0.82, Accuracy: 75%
  - Based on 12 financial institutions analysis

2021: Interest rates drop to near-zero, pattern deprecated
  - Archived to cold storage (S3)
  - Cached index entry created:
    - regime_tags: ["high_interest_rate", "financials"]
    - industry_tags: ["banking", "lending"]
    - confidence_score: 0.82
    - historical_accuracy: 0.75

2024: Interest rates spike to 5%+
  - Regime detector: Interest rate change = +4.5% in 8mo (exceeds 2% threshold)
  - Promotion engine queries index: search_by_regime(["high_interest_rate"])
  - Pattern matches: confidence 0.82 > 0.6 threshold
  - **Auto-promote immediately**:
    1. Retrieve full archive from S3 (~3s)
    2. Validate integrity
    3. Re-hydrate to L3 knowledge graph
    4. Status: "deprecated" → "active_from_archive"
    5. Add staleness metadata:
       - archived_at: 2021-03-15
       - promoted_at: 2024-11-18
       - promotion_trigger: "regime_change_interest_rate"
    6. Alert human for review (48hr window)
  - Pattern immediately available for agent use
  - Human notified for override review
```

#### Human Override Procedures

Auto-promoted patterns subject to human review within 48-hour window:

**Alert Format**:

```yaml
Pattern Promotion Alert:
  trigger: "Regime change: Interest rates increased 4.5% in 8mo"
  promoted_count: 5 patterns

  patterns:
    - pattern: "Bank profitability in high-rate environment"
      confidence: 0.82
      historical_accuracy: 75%
      last_used: "2020-03-15"
      evidence_age: 4.7 years

  action_required: "Review by 2024-11-20 14:30 UTC"
  default_action: "Promotion approved (no action = approval)"
  override_options:
    - Approve (no action needed)
    - Reject individual pattern
    - Reject entire trigger batch
    - Adjust trigger sensitivity
```

**Override Actions**:

1. **Approve Promotion** (Default):
   - No action required (promotion permanent after 48hr)
   - Pattern stays "active_from_archive"
   - Requires re-validation on new data before investment decisions

2. **Reject Promotion**:
   - Pattern demoted back to archive
   - Trigger cooldown: 6 months for this pattern+trigger combo
   - Rejection reason logged (false_regime_signal, pattern_obsolete, etc)
   - Pattern unavailable for agent use

3. **Adjust Trigger Sensitivity**:
   - Modify regime threshold (e.g., interest rate 2% → 3%)
   - Applies to future promotions
   - Reduces false positives

**Example - Override Workflow**:

```text
Day 0: Auto-promotion triggered (5 patterns promoted)
  - Human receives alert via dashboard + email
  - Patterns immediately active for agent queries

Day 1: Human reviews batch
  - Pattern A: "Bank profitability" → APPROVE (regime clearly changed)
  - Pattern B: "Lending margin expansion" → REJECT (market structure changed)
  - Pattern C-E: APPROVE (no action, default approval)

Day 1 (continued): System processes override
  - Pattern B demoted to archive
  - Pattern B + "regime_change_interest_rate" cooldown = 6 months
  - Override logged: reason = "Commercial lending dynamics fundamentally changed due to fintech competition"
  - Agents notified: Pattern B no longer available

Day 3 (48hr expires): Remaining patterns (A, C, D, E) promotions permanent
  - Status: "active_from_archive" maintained
  - Enter probationary period (3-6 months)
  - Require 2 successful validations before investment use
```

#### Re-Hydration and Probationary Status

Promoted patterns enter probationary status requiring validation before investment decisions:

**Re-Hydration Process**:

```python
# Pseudocode for archive promotion
def promote_pattern_from_archive(pattern_id, trigger_reason):
    # 1. Retrieve from S3
    archive = s3.get_object(f"archives/{pattern_id}/tier2/")

    # 2. Validate integrity
    if archive.version != current_version:
        warn_migration_needed(archive)

    # 3. Restore to knowledge graph
    pattern_node = knowledge_graph.create_pattern(
        pattern_data=archive.pattern_definition,
        validation_history=archive.validation_results,
        evidence_refs=archive.evidence_files  # May warn if evidence aged out
    )

    # 4. Add staleness metadata
    pattern_node.update({
        'status': 'active_from_archive',
        'archived_at': archive.archived_date,
        'promoted_at': now(),
        'promotion_trigger': trigger_reason,
        'staleness_warning': archive.evidence_age > 7  # Evidence >7yr old
    })

    # 5. Set probationary requirements
    pattern_node.set_probationary({
        'period': '6_months',
        'validations_required': 2,
        'validation_confidence_min': 0.65,
        'investment_use_blocked': True  # Until probation passes
    })

    return pattern_node
```

**Probationary Period**:

- **Duration**: 3-6 months or 2 successful validations (whichever first)
- **Investment Use**: Blocked until probation complete
- **Agent Use**: Available for analysis and hypothesis generation
- **Re-validation**: Pattern tested on recent data
- **Exit Criteria**:
  - 2+ successful validations (correlation >0.65)
  - No contradictory evidence
  - Human approval at next Gate 6
- **Failure**: If pattern fails re-validation, demoted back to archive

**Cooldown Logic**:

Prevents promotion/demotion thrashing:

- Promoted patterns observed minimum 6 months
- Cannot re-deprecate until 2+ validation failures
- Human-rejected promotions: 6-month trigger cooldown
- Prevents same pattern re-promoting within cooldown window

#### Cached Index for Fast Queries

Archive metadata stored in Redis/ElasticSearch for <100ms queries without S3 access:

**Index Schema**:

```yaml
Pattern Archive Index Entry:
  pattern_id: uuid-1234
  pattern_name: "Bank profitability in high-rate environment"
  status: "deprecated"
  deprecation_date: 2021-03-15
  archive_tier: 2

  # Searchable metadata
  regime_tags: ["high_interest_rate", "financials"]
  industry_tags: ["banking", "lending"]
  confidence_score: 0.82
  historical_accuracy: 0.75

  # Promotion tracking
  last_accessed: 2024-11-18
  access_count_30d: 3
  promotion_history:
    - promoted_at: 2024-11-18
      trigger: "regime_change_interest_rate"
      human_decision: "approved"
```

**Query Performance**:

- **Index queries**: <100ms (metadata only, no S3 access)
- **Full archive retrieval**: 3-5s (S3 GET when promoting)
- **Cost**: ~$0.01/mo for 10,000 patterns (negligible)

Complete specification: [DD-013: Archive Lifecycle Management](../design-decisions/DD-013_ARCHIVE_LIFECYCLE_MANAGEMENT.md)

### Anti-Confirmation Bias Mechanisms

Multiple safeguards prevent false pattern acceptance (see [DD-007](../design-decisions/DD-007_PATTERN_VALIDATION_ARCHITECTURE.md) for complete architecture):

#### 1. Hold-Out Validation

Patterns tested on data not used for discovery, ensuring they generalize beyond the training set.

#### 2. Blind Testing

Track pattern performance without agent awareness to prevent gaming or self-fulfilling prophecies.

#### 3. Control Groups

A/B test pattern-using analyses vs. baseline analyses to measure true incremental value.

#### 4. Statistical Rigor

Domain-specific p-value thresholds (DD-004) apply appropriate statistical standards:

- **Valuation/Market Timing**: p < 0.01 required (high stakes, strict threshold)
- **Financial/Operational Metrics**: p < 0.05 standard threshold
- **Business Model**: p < 0.10 acceptable (qualitative, less statistical)
- **Strategy/Management**: p < 0.10 if effect size r > 0.8 (small samples, large effects)

Universal minimum: p < 0.10 (absolute floor for all domains)

#### 5. Human Expert Review

Domain experts validate causal mechanisms at Gate 6, catching spurious correlations.

## How the System Learns

### Real-Time Pattern Mining

During each analysis cycle, the system:

1. Records all agent findings and reasoning
2. Tags findings with context (sector, market regime, company characteristics)
3. Links findings to eventual outcomes
4. Builds a growing database of situation-outcome pairs

### Continuous Pattern Refinement

On a rolling basis:

- Review active pattern performance
- Mine new pattern candidates
- Test candidates through validation pipeline
- Queue validated patterns for Gate 6 approval
- Apply approved patterns to agent decision-making

### Knowledge Propagation

When new patterns are validated and approved:

- Relevant agents receive pattern updates
- Agents incorporate patterns into decision logic
- Pattern usage tracked for effectiveness measurement
- Cross-domain patterns shared across specialist agents

### Learning Velocity

The system's learning accelerates over time as:

- More outcomes provide richer training data
- Pattern library grows and becomes more nuanced
- Agent track records enable better credibility weighting
- Human validation becomes more efficient with experience

## Debate Fallback Resolution Learning

The system learns from debate resolution outcomes to improve fallback accuracy and optimize the tiered escalation system.

### Fallback Accuracy Tracking

When debates are resolved using conservative defaults (Level 4) or credibility-weighted auto-resolution (Level 2), the system tracks whether the fallback resolution was correct:

**Tracking Mechanism**:

1. **Initial Fallback**: Conservative default or auto-resolution applied
2. **Human Review**: Human confirms, overrides, or validates at next gate
3. **Outcome Tracking**: When analysis outcome is known (6-12 months later), compare:
   - Fallback position outcome
   - Alternative position outcome (counterfactual)
   - Human override outcome (if applicable)

**Accuracy Metrics**:

```yaml
Fallback Resolution Metrics:

Conservative Default Accuracy:
  - Overall success rate: 0.87 (conservative default proved correct)
  - By debate type:
      margin_sustainability: 0.92 (15 cases)
      growth_assumptions: 0.83 (12 cases)
      management_quality: 0.79 (9 cases)
  - Human override rate: 0.15 (15% of cases overridden)
  - Override correctness: 0.67 (human overrides correct 67% of time)

Credibility-Weighted Auto-Resolution Accuracy:
  - Overall success rate: 0.84
  - By credibility differential:
      >0.40: 0.93 (high confidence)
      0.30-0.40: 0.86 (medium confidence)
      0.25-0.30: 0.76 (threshold cases)
  - False auto-resolution rate: 0.16 (should have escalated)
```

### Conservative Default Calibration

The system learns which types of debates benefit most from conservative defaults:

**Pattern Learning**:

- **High conservative accuracy** (>0.90): Margin compression debates, competitive threat assessments
- **Medium conservative accuracy** (0.75-0.90): Growth assumptions, capital allocation quality
- **Low conservative accuracy** (<0.75): Innovation potential, market timing calls

**Adaptive Logic**:

Based on historical accuracy, the system adjusts conservative default application:

```python
# Pseudocode for adaptive conservative default
if debate_type in high_conservative_accuracy_types:
    conservative_threshold = "lowest_estimate"  # Most cautious
elif debate_type in medium_conservative_accuracy_types:
    conservative_threshold = "middle_estimate"  # Moderate caution
else:
    conservative_threshold = "lower_quartile"  # Mild caution, escalate to human preferred
```

### Human Override Pattern Learning

The system tracks when humans override fallback resolutions and learns from these patterns:

**Override Analysis**:

1. **Override Frequency by Debate Type**:

   - Which debates are humans most likely to override?
   - Which fallbacks do humans consistently accept?

2. **Override Correctness**:

   - When human overrides, what's the outcome accuracy?
   - Are overrides improving decisions or introducing bias?

3. **Override Timing**:
   - How long after fallback does human review occur?
   - Does review delay correlate with override likelihood?

**Learning Applications**:

```yaml
Lessons from Override Patterns:

Pattern 1: "Margin debates in tech overridden 30% of time"
  - Conservative defaults too pessimistic for high-growth tech
  - Adjustment: Use "lower quartile" instead of "lowest estimate" for tech margins
  - Expected override reduction: 30% → 15%

Pattern 2: "Management quality debates rarely overridden (5%)"
  - Conservative defaults well-calibrated
  - Maintain current logic
  - High confidence in fallback accuracy

Pattern 3: "Overrides during Gate 5 more accurate than Gate 3"
  - More context available at final decision
  - Prioritize provisional review at Gate 5 when possible
  - Flag high-impact debates for Gate 5 review
```

### Credibility Threshold Optimization

The system learns the optimal credibility differential threshold for auto-resolution:

**Current Base Threshold**: 0.25 (actual threshold is dynamic: max(0.25, CI_A + CI_B) to account for statistical uncertainty)

**Note**: This analysis focuses on optimizing the base threshold value. The actual auto-resolution threshold adjusts upward based on confidence interval widths.

**Learning Objective**: Minimize (false_auto_resolutions + missed_auto_resolutions)

**Analysis**:

```yaml
Threshold Performance Analysis:

Threshold 0.20:
  - Auto-resolution rate: 45%
  - False auto-resolution rate: 22% (too high)
  - Verdict: Too aggressive

Threshold 0.25:
  - Auto-resolution rate: 32%
  - False auto-resolution rate: 16%
  - Verdict: Optimal balance

Threshold 0.30:
  - Auto-resolution rate: 21%
  - False auto-resolution rate: 11%
  - Verdict: Too conservative, missing opportunities

Recommendation: Maintain 0.25 threshold
  - Consider domain-specific thresholds (tech: 0.28, financials: 0.23)
```

**Domain-Specific Thresholds**:

As the system accumulates more data, it learns domain-specific thresholds:

- **High-uncertainty domains** (innovation, disruption): Higher threshold (0.30) - prefer human review
- **Stable domains** (margin analysis, cash flow): Standard threshold (0.25)
- **Well-understood domains** (accounting quality): Lower threshold (0.22) - safe to auto-resolve

### Debate Priority Learning

The system learns to classify debate priority more accurately:

**Initial Classification** (Rule-Based):

- Critical-path blocking: Keywords like "required for", "blocking", "dependency"
- Valuation impact: Keywords like "DCF", "target price", "valuation"
- Supporting: Everything else

**Learned Classification** (ML-Enhanced):

After tracking actual debate impact, the system learns:

```yaml
Learned Priority Indicators:

Critical-Path Signals:
  - Debate references "base case assumptions" (0.83 correlation with critical)
  - Multiple downstream analyses waiting (0.91 correlation)
  - Debate topic in ["revenue_growth", "margin_assumptions"] (0.76 correlation)

Valuation Impact Signals:
  - Debate affects WACC or terminal value (0.94 correlation with high impact)
  - Disagreement >20% on key driver (0.87 correlation)

Supporting Analysis Signals:
  - Debate on qualitative factors (0.72 correlation with low priority)
  - No numerical disagreement (0.81 correlation with supporting)
```

### Learning Integration with Gate 6

Debate fallback learnings presented at Gate 6 for validation (parameters per DD-004):

```yaml
Gate 6 Review - Debate Resolution Learnings:

New Pattern Discovered:
  - pattern: 'Conservative defaults in tech margin debates'
    current_accuracy: 0.78
    human_override_rate: 0.30
    proposed_change: 'Use lower quartile instead of minimum'
    expected_improvement: 'Accuracy 0.78 → 0.86, override 0.30 → 0.15'
    sample_size: 23 debates
    validation_required: YES

Credibility Score Updates:
  - Financial Analyst credibility in "tech_margins" domain: 0.82 → 0.79
    reason: 'Overestimated margin sustainability in 4 of 6 recent tech cases'
    proposed_bias_correction: '-2% to tech margin projections'

Human Actions:
  - Approve pattern change
  - Reject (maintain current conservative logic)
  - Request more evidence (need 5+ more cases)
  - Modify threshold (specify alternative)
```

### Success Metrics for Debate Learning

| Metric                     | Description                                      | Current | Target |
| -------------------------- | ------------------------------------------------ | ------- | ------ |
| Fallback Accuracy          | % of conservative defaults that proved correct   | 87%     | >85%   |
| Override Rate              | % of fallbacks overridden by human               | 15%     | <20%   |
| Override Correctness       | % of human overrides that improved outcome       | 67%     | >70%   |
| Auto-Resolution Accuracy   | % of credibility-weighted resolutions correct    | 84%     | >80%   |
| False Auto-Resolution Rate | % of auto-resolutions that should have escalated | 16%     | <20%   |
| Debate Priority Accuracy   | % of debates correctly prioritized               | 81%     | >85%   |

### Continuous Calibration

The debate fallback system recalibrates quarterly based on:

1. **Accuracy trends**: Are fallbacks maintaining >85% accuracy?
2. **Override patterns**: Are humans consistently overriding certain debate types?
3. **Threshold effectiveness**: Is 0.25 credibility threshold optimal?
4. **Priority classification**: Are debates routed correctly?

Recalibration results presented at Gate 6 for approval before application.

## Memory Integration

Learning is tightly integrated with the memory system:

### Pattern Storage

Validated patterns stored in central knowledge graph with:

- Discovery date and validation history
- Success rate over time
- Applicable contexts and validity conditions
- Related patterns and contradictions
- Agent usage and effectiveness

### Outcome Database

All predictions and actuals stored permanently:

- Original predictions with confidence scores
- Actual outcomes at each checkpoint
- Accuracy measurements
- Attribution to specific patterns and agents
- Lessons learned

### Agent Learning Records

Each agent maintains detailed learning history:

- Systematic errors and corrections applied
- Domain-specific accuracy trends
- Successful vs. unsuccessful patterns
- Calibration factors for predictions

## Continuous Improvement Cycle

The learning system operates on multiple timescales:

### Real-Time Learning (Minutes to Hours)

- Individual agent error detection
- Immediate pattern matching during analysis
- Dynamic confidence adjustment based on context

### Daily Learning

- Aggregate agent findings into patterns
- Check for contradictions requiring debate
- Update working memory with session learnings

### Weekly Learning

- Pattern performance review
- Cross-agent knowledge synchronization
- Emerging pattern candidate identification

### Monthly Learning (Gate 6)

**Trigger** (DD-004): (50 outcomes OR 30 days) AND 7-day cooldown

- Human validation of new patterns (never auto-approved)
- Agent credibility score updates (auto-approve if delta <0.05, n≥20)
- Lessons learned approval (auto-approve if 5+ confirmations, 90%+ confidence)
- Pattern library maintenance
- Auto-approval rate: MVP 0% → Production 40-50% → Scale 50-60%
- Adaptive probation: 90-365 days based on pattern frequency, max 2 extensions

### Quarterly Learning

- Strategic pattern effectiveness review
- Model recalibration across sectors
- Learning velocity measurement
- System capability benchmarking

## Key Performance Indicators

The learning system tracks:

| Metric               | Description                           | Target     |
| -------------------- | ------------------------------------- | ---------- |
| Pattern Accuracy     | % of patterns remaining valid         | >70%       |
| False Pattern Rate   | % of discovered patterns rejected     | <10%       |
| Agent Learning Rate  | Quarterly improvement in accuracy     | 5%/quarter |
| Prediction Error     | Average error on key metrics          | <15%       |
| Pattern Utilization  | % of decisions using pattern insights | >80%       |
| Validation Pass Rate | % of candidates passing Gate 6        | 30-50%     |

## Quality Safeguards

Multiple mechanisms ensure learning quality:

### Statistical Validation

- Chronological train/val/test splits
- Minimum sample size requirements
- Significance testing (p < 0.05)
- Performance degradation monitoring

### Human Oversight

- Gate 6 validation of all new learnings
- Expert review of causal mechanisms
- Approval authority over pattern activation
- Override capability for systematic biases

### Continuous Monitoring

- Pattern accuracy tracking over time
- Agent performance benchmarking
- Contradiction detection and resolution
- Memory quality audits

### Rollback Capability

- Version control for all patterns
- Ability to revert problematic updates
- Historical accuracy comparison
- Pattern deprecation when invalidated

## Success Criteria

Learning system effectiveness measured by:

1. **Accuracy Improvement**: Agent predictions becoming more accurate over time
2. **Pattern Validity**: High percentage of patterns remaining effective
3. **Low False Positives**: Minimal spurious patterns entering active use
4. **Human Efficiency**: Decreasing Gate 6 review time as system matures
5. **Knowledge Compound**: Each analysis building on institutional memory
6. **Adaptive Capability**: Quick response to regime changes and structural breaks

---

## Related Documentation

- [02-feedback-loops.md](./02-feedback-loops.md) - Agent improvement and track record systems
- [03-metrics.md](./03-metrics.md) - Memory system performance metrics
- [../memory/01-architecture.md](../memory/01-architecture.md) - Memory system architecture
- [../agents/09-knowledge-base-agent.md](../agents/09-knowledge-base-agent.md) - Knowledge Base Agent details
- [../workflow/05-documentation.md](../workflow/05-documentation.md) - Learning integration in workflow

---

**Navigation**: [← Memory](../memory/) | [Learning Home](./) | [Feedback Loops →](./02-feedback-loops.md)

**Note**: Code implementation examples for the learning systems can be found in `/examples/learning/`
