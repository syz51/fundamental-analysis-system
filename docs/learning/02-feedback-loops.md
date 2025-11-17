# Feedback Loops

## Overview

The system implements sophisticated feedback loops that enable agents to improve their performance over time through systematic error analysis, credibility tracking, and human guidance integration. Each agent maintains a track record and continuously refines its decision-making based on outcomes.

This document covers:

- Agent self-improvement mechanisms
- Track record and credibility scoring systems
- Human feedback integration
- Learning propagation across agents
- Continuous calibration processes

## Agent Self-Improvement

Each agent actively learns from its mistakes and successes through systematic error analysis and correction.

### Error Pattern Identification

Agents analyze their historical errors to identify systematic biases:

#### Error Clustering

Errors grouped by:

- Type of mistake (overestimation, underestimation, missed signals)
- Context (sector, market regime, company characteristics)
- Frequency and magnitude
- Impact on final decisions

#### Systematic Bias Detection

When error patterns exceed 20% frequency, they're classified as systematic biases requiring correction.

### Correction Generation

For each identified bias, the system:

1. **Analyzes Root Cause**: Why did this error occur repeatedly?
2. **Generates Correction Factor**: Quantitative adjustment to prevent recurrence
3. **Tests on Historical Data**: Backtest correction on past analyses
4. **Validates Improvement**: Ensure correction improves accuracy >10%
5. **Commits or Rejects**: Apply if beneficial, discard if not

### Correction Application

Corrections integrated into agent decision logic:

- Adjust baseline assumptions
- Modify weighting of evidence
- Add checks for blind spots
- Update risk assessment factors

### Learning Sharing

Successful corrections shared with related agents:

- Financial Analyst learnings → Strategy Analyst
- Business Research learnings → Screening Agent
- Valuation learnings → Financial Analyst

Cross-pollination accelerates system-wide improvement.

## Track Record System

Comprehensive credibility tracking enables the system to weight agent opinions by historical accuracy.

### Accuracy Score Calculation

Each agent maintains accuracy scores across multiple dimensions:

#### Overall Accuracy

Percentage of predictions within acceptable error bounds:

- Financial projections: ±15% tolerance
- Strategic assessments: binary correct/incorrect
- Valuation targets: ±20% tolerance

#### Domain-Specific Accuracy

Separate scores for:

- Sector/industry (Technology, Retail, Healthcare, etc.)
- Metric type (Revenue, Margins, Cash Flow, etc.)
- Time horizon (Near-term, Medium-term, Long-term)
- Market regime (Bull, Bear, Neutral, Volatile)

#### Contextual Accuracy

Performance in specific contexts:

- Company size (Mega-cap, Large-cap, Mid-cap, Small-cap)
- Growth stage (Mature, Growth, Turnaround, Startup)
- Complexity (Simple, Moderate, Complex)

### Time-Weighted Scoring

Recent performance weighted more heavily than distant past:

- Last 3 months: 50% weight
- 3-12 months ago: 30% weight
- 1-2 years ago: 15% weight
- 2+ years ago: 5% weight

This enables agents to adapt to changing market dynamics while retaining institutional knowledge.

### Confidence Calibration

Agents learn to calibrate their confidence levels:

#### Over/Under Confidence Detection

- Track predictions by stated confidence level
- Measure actual accuracy at each confidence level
- Identify systematic over/under confidence patterns

#### Calibration Adjustment

If agent states 90% confidence but achieves only 70% accuracy:

- Apply calibration factor (multiply confidence by 0.78)
- Adjust until stated confidence matches realized accuracy
- Prevents overconfident predictions from dominating decisions

### Sample Size Tracking

Accuracy scores include sample size context:

- High confidence if 50+ decisions in category
- Medium confidence if 10-49 decisions
- Low confidence if <10 decisions

Prevents drawing strong conclusions from limited data.

## Credibility Weighting in Decisions

Agent track records directly influence decision-making power.

### Debate Weight Assignment

In collaborative debates, agent positions weighted by:

#### Track Record Component (60%)

Historical accuracy in similar contexts:

- Exact domain match (sector + metric): 100% weight
- Partial match (sector OR metric): 60% weight
- General accuracy: 30% weight

#### Recency Component (20%)

Performance in last 90 days receives premium:

- Trending up: +10% bonus
- Stable: baseline
- Trending down: -10% penalty

#### Confidence Component (20%)

Agent's stated confidence in current position:

- High confidence (>80%): full weight
- Medium confidence (50-80%): 0.7x weight
- Low confidence (<50%): 0.4x weight

### Consensus Calculation

Final system recommendation weighted by agent credibility:

```text
Weighted_Recommendation = Σ(Agent_Position × Credibility_Score) / Σ(Credibility_Score)
```

More accurate agents have greater influence on final decisions.

### Dynamic Reweighting

Credibility weights update continuously:

- After each outcome measurement
- Monthly comprehensive review
- Immediate adjustment for major errors
- Gradual adjustment for trend changes

## Human Feedback Integration

Human input serves as high-value training signal for system improvement.

### Feedback Types

#### Validation Feedback (Gate 6)

Human approval/rejection of:

- New patterns discovered
- Agent credibility changes
- Lessons learned
- Systematic corrections

This is the primary quality control mechanism.

#### Override Feedback (All Gates)

When humans override agent recommendations:

- Record human decision and rationale
- Tag with context and reasoning
- Use as high-value training example
- Identify blind spots in agent logic

#### Correction Feedback (Ad Hoc)

Humans can flag specific errors:

- Factual mistakes
- Logical flaws
- Missed considerations
- Inappropriate pattern applications

#### Guidance Feedback (Training Mode)

In training scenarios, humans provide:

- Domain expertise not in data
- Qualitative insights
- Industry-specific knowledge
- Relationship/political dynamics

### Feedback Processing

Human feedback receives special treatment:

#### High Priority Storage

- Stored in permanent knowledge base
- Tagged as "human_validated" or "human_corrected"
- Protected from automated cleanup
- Easily retrievable for similar situations

#### Immediate Propagation

- Shared with relevant agents within minutes
- Incorporated into active analyses
- Used to update pattern library
- Triggers review of related decisions

#### Learning Integration

- Used to validate or invalidate patterns
- Influences agent credibility scores
- Updates bias correction factors
- Guides future pattern mining

### Human-Agent Learning Dialogue

System can explicitly request human expertise:

#### Experience Queries

"Do you recall similar situations from your experience?"

Particularly valuable for:

- Outcomes that surprised the models
- Qualitative factors agents might miss
- Industry-specific knowledge
- Relationship/political dynamics

#### Validation Requests

"Does this pattern align with your domain expertise?"

Helps catch:

- Spurious correlations
- Data artifacts
- Missing context
- Causation vs. correlation errors

#### Blind Spot Identification

"What are we missing in this analysis?"

Reveals:

- Unconsidered factors
- Alternative interpretations
- Hidden risks
- Unique circumstances

## Learning Loop Examples

Real-world examples of feedback loops in action.

### Pattern Evolution Example

**Pattern**: "January Effect in Small Caps"

**Initial Discovery** (2020-01-15)

- Success Rate: 71%
- Applied to all small-cap stocks
- Strong statistical significance

**Evolution Timeline**:

**2020-2021**: 73% success (pattern strengthening)

- Confidence increased
- Broader application recommended

**2022**: 45% success (pattern weakening)

- Investigation triggered
- Pattern marked probationary

**2023**: 38% success (pattern breaking)

- Full investigation initiated
- Root cause analysis performed

**Investigation Result**:

- Retail trading apps democratized access
- Algorithmic trading arbitraged the opportunity
- Pattern now only works in micro-caps <$50M

**Updated Pattern**: "January Effect in Micro Caps Only"

- New Success Rate: 68%
- Validity Conditions:
  - Market cap < $50M
  - Low algorithmic trading volume
  - Illiquid securities preferred

**Outcome**: Pattern preserved with refined conditions rather than discarded.

### Agent Learning Example

**Agent**: Financial Analyst
**Domain**: Retail Sector Margins

**Initial Performance**:

- Margin predictions: 62% accuracy
- Systematic bias: Overestimating by avg 3.2%
- High confidence in predictions despite errors

**Error Analysis**:

Identified three systematic errors:

1. **E-commerce Competition Impact**: Underweighted in models

   - Traditional retailers losing margin to online competition
   - Effect stronger than historical data suggested

2. **Wage Inflation Effects**: Delayed recognition

   - Labor cost increases not immediately reflected in margins
   - 6-month lag not modeled

3. **Inventory Management**: Benefits overestimated
   - Expected efficiency gains from technology overstated
   - Industry-wide improvements limited to ~1% maximum

**Corrections Applied**:

1. **E-commerce Pressure Factor**: +1.5x weight

   - Now primary consideration in retail margin analysis
   - Sector-specific application (not applied to e-commerce natives)

2. **Wage Sensitivity**: 6-month lag added

   - Model now looks backward for labor cost signals
   - Adjusts margin projections with time delay

3. **Inventory Benefit Cap**: 1% max improvement
   - Realistic ceiling on efficiency gains
   - Prevents over-optimistic projections

**Post-Learning Performance**:

- Margin predictions: 79% accuracy (+17%)
- Bias reduced to 0.8% (-2.4%)
- Confidence calibration improved (stated confidence now matches realized accuracy)

**Knowledge Sharing**:
Lessons shared with:

- Consumer Goods Analyst (similar margin dynamics)
- Strategy Analyst (capital allocation for retail)
- Screening Agent (margin expectation filters)

**Outcome**: System-wide improvement in retail sector analysis accuracy.

### Human Override Learning Example

**Situation**: NVDA Valuation (2023)

**Agent Recommendation**: HOLD

- Valuation stretched (P/E 65)
- Historical pattern: "Tech premium compression" (73% accuracy)
- Consensus: Wait for pullback

**Human Override**: BUY

- Rationale: "AI revolution unique, historical patterns don't apply"
- Qualitative insight: Platform shift similar to mobile/cloud
- Domain expertise: Semiconductor cycles + software economics

**Outcome** (12 months):

- Stock up 239%
- Human decision vastly outperformed agent recommendation
- Pattern "Tech premium compression" failed in this context

**System Learning**:

1. **Pattern Update**:

   - Added validity condition: "Not applicable during platform shifts"
   - Requires structural assessment before application
   - Identified 3 historical exceptions (AAPL 2007, MSFT 2015, AMZN 2017)

2. **New Pattern Created**:

   - "Platform Transition Premium Sustainability"
   - Characteristics: Ecosystem lock-in, developer adoption, network effects
   - Success rate: 4 of 5 historical instances maintained premiums

3. **Agent Calibration**:

   - Valuation Agent learned to flag potential platform shifts
   - Strategy Agent elevated to higher weight for structural assessments
   - Human expertise explicitly requested for unusual market dynamics

4. **Meta-Learning**:
   - System now recognizes "regime change" scenarios
   - Automatically surfaces historical pattern failures
   - Requests human judgment when unprecedented situations detected

**Long-term Impact**: Improved handling of structural market changes and regime shifts.

## Feedback Loop Metrics

System tracks feedback loop effectiveness:

| Metric                    | Description                                 | Target     |
| ------------------------- | ------------------------------------------- | ---------- |
| Agent Learning Rate       | Quarterly accuracy improvement              | 5%/quarter |
| Correction Success        | % of corrections that improve accuracy      | >70%       |
| Human Override Rate       | % of agent recommendations overridden       | <20%       |
| Override Accuracy         | How often human overrides are correct       | >60%       |
| Feedback Integration Time | Hours from feedback to system update        | <24 hours  |
| Knowledge Sharing Rate    | % of learnings propagated to related agents | >80%       |

## Best Practices

Effective feedback loops require:

### For Agents

- Maintain detailed error logs
- Actively seek disconfirming evidence
- Update quickly based on outcomes
- Share learnings proactively
- Request human guidance when uncertain

### For Humans

- Provide rationale with overrides
- Validate patterns at Gate 6 thoughtfully
- Share qualitative insights liberally
- Correct errors promptly
- Engage with system requests for expertise

### For System

- Track all predictions and outcomes
- Calculate accuracy fairly (no gaming)
- Update credibility weights transparently
- Preserve human feedback permanently
- Balance automation with human judgment

## Continuous Improvement Cycle

Feedback loops operate continuously:

1. **Make Predictions**: Agents generate forecasts and recommendations
2. **Track Outcomes**: System monitors actual results
3. **Measure Accuracy**: Compare predictions to actuals
4. **Identify Errors**: Cluster mistakes and find patterns
5. **Generate Corrections**: Create fixes for systematic biases
6. **Test Corrections**: Validate on historical data
7. **Apply Learnings**: Update agent logic and credibility
8. **Share Knowledge**: Propagate learnings across agents
9. **Validate with Humans**: Get approval at Gate 6
10. **Monitor Impact**: Track effectiveness of improvements

This cycle repeats indefinitely, compounding improvements over time.

---

## Related Documentation

- [01-learning-systems.md](./01-learning-systems.md) - Overall learning architecture
- [03-metrics.md](./03-metrics.md) - Performance measurement systems
- [../agents/](../agents/) - Individual agent specifications
- [../collaboration/02-debate-protocol.md](../collaboration/02-debate-protocol.md) - Credibility-weighted debates
- [../human-gates/06-learning-validation.md](../human-gates/06-learning-validation.md) - Gate 6 details

---

**Navigation**: [← Learning Systems](./01-learning-systems.md) | [Learning Home](./) | [Metrics →](./03-metrics.md)

**Note**: Code examples for feedback loop implementation available in `/examples/learning/feedback_loops.py`
