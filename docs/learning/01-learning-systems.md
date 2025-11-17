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

Complete 3-tier validation architecture specified in [DD-007](../../design-decisions/DD-007_PATTERN_VALIDATION_ARCHITECTURE.md). Implementation requires:

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

### Anti-Confirmation Bias Mechanisms

Multiple safeguards prevent false pattern acceptance (see [DD-007](../../design-decisions/DD-007_PATTERN_VALIDATION_ARCHITECTURE.md) for complete architecture):

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

**Current Threshold**: 0.25

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
