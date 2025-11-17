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
- **probationary**: Needs more evidence
- **rejected**: Failed validation
- **deprecated**: Previously valid but no longer applicable

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

### Anti-Confirmation Bias Mechanisms

Multiple safeguards prevent false pattern acceptance:

#### 1. Hold-Out Validation

Patterns tested on data not used for discovery, ensuring they generalize beyond the training set.

#### 2. Blind Testing

Track pattern performance without agent awareness to prevent gaming or self-fulfilling prophecies.

#### 3. Control Groups

A/B test pattern-using analyses vs. baseline analyses to measure true incremental value.

#### 4. Statistical Rigor

Require p-value < 0.05 for statistical significance, reducing false positive rate.

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

- Human validation of new patterns
- Agent credibility score updates
- Lessons learned approval
- Pattern library maintenance

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
