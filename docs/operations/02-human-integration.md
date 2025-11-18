# Human Integration - Decision Gates and Interfaces

## Overview

This document describes how human expertise integrates with the AI-powered analysis system. The system supports three operational modes and implements six strategic decision gates where human judgment enhances and validates AI recommendations.

Human integration serves dual purposes:

1. **Oversight**: Ensuring AI recommendations align with broader investment strategy and risk tolerance
2. **Learning**: Capturing valuable human expertise and intuition to improve future analyses

---

## Human-in-the-Loop Integration

### Engagement Modes

The system supports three operational modes balancing automation with human oversight:

#### 1. Full Autopilot Mode

- **Usage**: Low-risk screening, watchlist monitoring
- **Human Touch**: Weekly summary reviews
- **Decisions**: Auto-proceed with conservative defaults
- **Best For**: Large-scale screening, position monitoring

#### 2. Collaborative Mode (Recommended)

- **Usage**: New position analysis, major decisions
- **Human Touch**: Input at key gates
- **Decisions**: Human guided with AI support
- **Best For**: High-conviction investments

#### 3. Training Mode

- **Usage**: System improvement, complex situations
- **Human Touch**: Active guidance throughout
- **Decisions**: Human-led with AI learning
- **Best For**: Edge cases, new sectors

---

## Enhanced Human Gates with Memory Context

### Gate 1: Screening Validation with History

**Input Required**: Approve/modify candidate list
**Interface**: Ranked table with key metrics
**Time Limit**: 24 hours
**Default Action**: Proceed with top 10 candidates

```yaml
Display:
  - Candidate list with scores
  - Previous analysis dates and outcomes (if any)
  - Similar companies analyzed (with results)
  - Pattern matches: 'Similar to XYZ which we bought at...'

Human Actions:
  - Approve/modify list
  - Request historical deep-dive
  - Add context about past experiences
  - Override based on qualitative memory
```

**Memory Enhancements**:

The system presents each candidate with historical context:

- Companies previously analyzed with their outcomes
- Similar business models and their performance
- Pattern matches from successful/failed past investments
- Sector-specific screening success rates

This enables humans to leverage institutional memory for better candidate selection while adding their own experiential knowledge.

### Gate 2: Research Direction with Precedents

**Input Required**: Identify focus areas and concerns
**Interface**: SWOT summary with investigation prompts
**Time Limit**: 12 hours
**Default Action**: Standard checklist investigation

```yaml
Display:
  - SWOT with historical validation
  - "Last time we saw this pattern..." notifications
  - Agent disagreements with track records
  - Lessons from similar analyses

Human Actions:
  - Focus investigation areas
  - Share institutional knowledge
  - Correct historical misconceptions
  - Add qualitative patterns
```

**Purpose**:

After initial parallel analysis, humans guide the depth and direction of research by:

- Identifying areas requiring deeper investigation
- Surfacing concerns not visible in quantitative screens
- Sharing industry knowledge that may not be documented
- Correcting any misinterpretations by agents

The system shows where similar companies had unexpected issues, prompting proactive investigation.

### Gate 3: Assumption Validation with Calibration

**Input Required**: Validate/adjust model parameters
**Interface**: Interactive model dashboard
**Time Limit**: 24 hours
**Default Action**: Conservative estimates

```yaml
Display:
  - Model assumptions with historical accuracy
  - 'Our models tend to overestimate X by Y%'
  - Sector-specific calibration factors
  - Confidence intervals based on track record

Human Actions:
  - Adjust with experience-based intuition
  - Override systematic biases
  - Add scenario probabilities
  - Input macro views
```

**Critical Validation Areas**:

- Revenue growth assumptions
- Margin expansion/contraction
- Discount rates and terminal values
- Scenario probabilities
- Key value drivers

The system shows historical accuracy of similar assumptions, enabling humans to adjust for systematic biases while applying their macro and sector-specific insights.

### Gate 4: Debate Arbitration with Historical Context

**Input Required**: Resolve significant disagreements
**Interface**: Side-by-side comparison view
**Time Limit**: 6 hours (with automatic fallback)
**Default Action**: Apply conservative default (provisional resolution)

```yaml
Display:
  - Conflicting agent positions with credibility scores
    - Phase 2 (Months 3-4): Simple credibility (overall accuracy + temporal decay + confidence intervals)
    - Phase 4 (Months 7-8): Comprehensive credibility (adds regime, trend, override, context)
  - Historical precedents for similar debates
  - Pattern success rates supporting each position
  - Agent track records in this context
  - Priority classification (critical-path, valuation, supporting)
  - Queue status: "Debate 2/3" (current load indicator)
  - Timeout countdown: "4h 23m remaining"
  - Facilitator's recommended resolution (if credibility gap exists)

Human Actions:
  - Arbitrate between positions (binding resolution)
  - Request additional evidence (extends timeout +2hr, max once)
  - Identify missing considerations
  - Set uncertainty level for final decision
  - Accept facilitator's recommendation (if auto-resolution attempted)
  - Defer to next gate (low-priority only)
```

**Timeout Enforcement**:

If human doesn't respond within 6 hours:

1. **Automatic Fallback Triggered** (Level 4 escalation)

   - System applies conservative default logic
   - Most cautious position selected automatically
   - Resolution marked as "provisional - awaiting review"
   - Pipeline continues (non-blocking)

2. **Override Window Opens**

   - Provisional decision reviewable at next gate
   - Appears in gate queue as "X provisional decisions require review"
   - Human can confirm, override, or request re-debate

3. **Notification Sent**
   - Alert: "Debate auto-resolved using conservative default"
   - Summary of provisional resolution
   - Reminder to review at next gate

**Queue Management (Single Expert)**:

The system enforces workload limits to prevent expert overload:

- **Max concurrent debates**: 3
- **Current load displayed**: "2/3 debates" indicator
- **Queue position shown**: "Your debate is #1 in queue"

**Overflow Handling**:

When expert queue reaches capacity (3/3) and new debate arrives:

1. **High-Priority Debates** (critical-path blocking):

   - If credibility differential >threshold (dynamic: max(0.25, CI_A + CI_B)): Auto-resolve via facilitator (Level 2)
   - If credibility differential <threshold: Apply conservative default (Level 4)
   - Never queue high-priority debates beyond 3

2. **Medium-Priority Debates** (valuation impact):

   - If credibility auto-resolution possible: Apply automatically
   - Else: Defer to next gate or apply conservative default

3. **Low-Priority Debates** (supporting analysis):
   - Automatically defer to next gate
   - No provisional resolution needed (not blocking pipeline)

**Priority Classification**:

Debates are automatically classified and routed:

| Priority          | Definition                         | Queue Behavior                    | Timeout Action                   |
| ----------------- | ---------------------------------- | --------------------------------- | -------------------------------- |
| **Critical-Path** | Blocks immediate pipeline progress | Force resolution (never queue >3) | Conservative default immediately |
| **Valuation**     | Affects DCF, price targets         | Queue if <3, else auto-resolve    | Conservative default after 6hr   |
| **Supporting**    | Background research                | Queue if <3, else defer           | Defer to next gate               |

**Conflict Resolution**:

When agents disagree significantly, humans see:

- Each position with supporting evidence
- Historical accuracy of each agent in similar contexts
- Past debates on similar topics and their resolutions
- Pattern success rates supporting each argument
- **Facilitator's analysis**: Credibility scores and recommended resolution
- **Conservative default preview**: Which position would be applied if timeout
- **Downstream impact**: What analyses depend on this resolution

This enables informed arbitration based on both current evidence and historical performance.

**Provisional Decision Review at Subsequent Gates**:

At each gate following a provisional resolution, human sees:

```yaml
Provisional Decisions Requiring Review: [2]

1. Debate: Management Capital Allocation Effectiveness
   - Conservative Position Applied: Strategy Analyst (skeptical view)
   - Alternative Position: Financial Analyst (optimistic view)
   - Rationale: Selected lower ROIC projection (8% vs 12%)
   - Impact: Reduced DCF valuation by 15%
   - Credibility Scores: Strategy 0.73, Financial 0.68
   - Your Actions:
     * Confirm conservative default (becomes final)
     * Override to Financial Analyst position (check downstream impact)
     * Request re-debate with additional context

2. Debate: [similar format]

If Override Selected:
  Downstream Impact Analysis:
    - Valuation model: Re-run required (5min)
    - Target price: Will increase ~$12-15
    - Risk assessment: Confidence score will adjust
    - Recommendation: May shift from Hold to Buy

  Note: See full algorithm specification in
  [Downstream Impact Calculation](../architecture/07-collaboration-protocols.md#downstream-impact-calculation-algorithm)

  Confirm Override? [Yes] [No]
```

This ensures no provisional decision becomes final without explicit human review.

### Gate 5: Final Decision with Full Context

**Input Required**: Investment decision and sizing
**Interface**: Executive summary with scoring
**Time Limit**: None (blocking)
**Default Action**: N/A - requires explicit approval

```yaml
Display:
  - Complete analysis synthesis
  - Memory-adjusted confidence scores
  - Historical similar decisions and outcomes
  - Risk factors from pattern matching
  - Agent consensus with credibility weighting

Human Actions:
  - Approve/reject investment
  - Set position size
  - Define entry/exit criteria
  - Add qualitative override rationale
  - Specify monitoring requirements
```

**Final Decision Components**:

The executive summary includes:

- Investment thesis (bull/base/bear cases)
- Valuation analysis with target ranges
- Risk assessment and mitigation
- Agent consensus with confidence scores
- Historical precedents and outcomes
- Recommended position sizing
- Entry/exit criteria
- Monitoring plan

Humans make the final go/no-go decision with full transparency into AI reasoning and historical context.

### Gate 6: Learning Validation (NEW)

**Purpose**: Prevent confirmation bias and false pattern propagation by requiring human validation of system learnings

**Input Required**: Review and validate learning updates
**Trigger**: (50 outcomes OR 30 days) AND 7-day cooldown since last validation
**Time Limit**: 48 hours
**Default Action**: Quarantine unvalidated patterns (don't use in decisions)

**Trigger Logic** (DD-004):

- Validation fires when either threshold met: 50 outcomes accumulated OR 30 days elapsed
- Minimum 7-day cooldown prevents validation spam (no trigger within 7 days of last)
- Urgency escalates if 75+ outcomes or 45+ days (prompts faster review)
- Whichever threshold reached first (after cooldown) triggers validation

**Pattern Validation Architecture** ([DD-007](../design-decisions/DD-007_PATTERN_VALIDATION_ARCHITECTURE.md)):

All patterns presented at Gate 6 have already passed 3-tier statistical validation:

1. **Hold-out validation**: Performance within 20% of training accuracy on unseen data
2. **Blind testing**: Pattern helps >1.5x more than hurts (6-month shadow analysis, agents unaware)
3. **Statistical significance**: p < 0.05 improvement vs control group (domain-specific thresholds)

Only patterns with status='statistically_validated' reach Gate 6. Human review focuses on causal mechanisms and domain expertise validation.

```yaml
Display:
  New Patterns Discovered:
    - pattern_name: 'Tech margin compression in rising rate environment'
      status: statistically_validated  # Passed all 3 validation tiers
      occurrences: 5
      correlation: 0.73
      training_accuracy: 0.73
      validation_accuracy: 0.68
      test_accuracy: 0.66
      blind_test_score: 2.3  # Helped 2.3x more than hurt
      control_p_value: 0.04  # Statistically significant improvement
      affected_sectors: [Technology, Software]
      proposed_action: 'Reduce margin estimates by 2%'
      confidence: MEDIUM
      validation_summary:
        - hold_out: PASSED (test accuracy 0.66, degradation 10% < 20% threshold)
        - blind_test: PASSED (improvement_ratio 2.3 > 1.5 threshold)
        - statistical: PASSED (p=0.04 < 0.05 threshold)

  Agent Credibility Changes:
    - agent: Financial Analyst
      domain: Retail margins
      old_score: 0.82
      new_score: 0.79
      reason: 'Overestimated margins in 3 of 4 recent analyses'
      proposed_action: 'Apply -1.5% bias correction'
      sample_size: 12 decisions
      time_weighted_score: 0.77

  Lessons Learned:
    - lesson: 'Supply chain improvements overestimated in retail'
      evidence: [DECISION-001, DECISION-034, DECISION-089]
      proposed_change: 'Cap inventory benefit at 1% max'
      success_rate_before: 0.62
      projected_success_after: 0.71

**Auto-Approval Rules** (DD-004 - Production Phase):

Items that bypass human review (accuracy target >95%):

- **Credibility Changes**: Auto-approve if delta <0.05 AND sample_size ≥20
- **Lessons Learned**: Auto-approve if confirmations ≥5 AND confidence ≥0.9
- **Patterns**: NEVER auto-approved (too high-risk for false propagation)
- **Valuation Domain**: NEVER auto-approved (high stakes)

Phase-based auto-approval: MVP 0% → Beta 20-30% → Production 40-50% → Scale 50-60%

**Auto-Approval Validation Requirements** (DD-014):

Before enabling auto-approval in production, must complete validation:

- **Shadow Mode**: 90 days AND ≥100 decisions (compute auto-decision, compare with human)
- **Accuracy Target**: >95% agreement with statistical significance (p < 0.05)
- **Error Rates**: ≤1% false positive (auto-approve when shouldn't), ≤5% false negative
- **Timeline**: Shadow mode runs Phase 4 (months 7-9), enabled Phase 5 if validated

Post-deployment continuous monitoring with automatic rollback:

- **Accuracy Tracking**: 14-day rolling window, weekly spot-check audits (10% sample)
- **Rollback Trigger**: 94% accuracy → investigation (48hrs), 92% → auto-disable
- **Monitoring**: Track FP/FN rates, audit sample for errors, dashboard alerts

Conservative thresholds prioritize safety (1% FP vs 2-5% industry standard). Shadow mode prevents deploying untested auto-approval. See [DD-014](../design-decisions/DD-014_VALIDATION_GAPS_RESOLUTION.md) for complete validation specifications.

Human Actions:
  Pattern Validation:
    - Approve pattern (use in future decisions)
    - Reject pattern (spurious correlation)
    - Request more evidence (triggers adaptive probation - see below)
    - Modify pattern (adjust correlation threshold or conditions)
    - Add validity conditions (market regime, sector, timeframe)

  Credibility Management:
    - Approve credibility change
    - Override credibility (human judgment)
    - Request detailed error analysis
    - Reset due to regime change

  Lesson Application:
    - Approve lesson learned
    - Add context/caveats to lesson
    - Reject lesson (incorrect attribution)
    - Request A/B test before applying
```

**Validation Criteria for Patterns**:

Approve if:

- Logical causation mechanism exists (not just correlation)
- Passes hold-out validation (performance within 20% on unseen data)
- Sufficient sample size (typically 5+ occurrences)
- Statistically significant per domain thresholds (see below)
- Aligns with domain expertise
- No obvious confounding variables

Reject if:

- Spurious correlation (no causal mechanism)
- Fails hold-out validation (overfitting)
- Too few data points
- Specific to unique historical event
- Contradicts fundamental principles
- Human expert has counter-evidence

**Domain-Specific Statistical Thresholds** (DD-004):

Universal minimum: p < 0.10 (absolute floor)

| Domain              | p < 0.01 | p < 0.05             | p < 0.10             |
| ------------------- | -------- | -------------------- | -------------------- |
| Valuation Models    | APPROVE  | PROBATION            | REJECT               |
| Market Timing       | APPROVE  | PROBATION            | REJECT               |
| Financial Metrics   | APPROVE  | APPROVE              | PROBATION            |
| Business Model      | APPROVE  | APPROVE              | APPROVE_WITH_CAVEATS |
| Strategy/Management | APPROVE  | APPROVE_WITH_CAVEATS | PROBATION (if r>0.8) |
| Operational Metrics | APPROVE  | APPROVE              | PROBATION            |

Rationale: High-stakes domains (valuation, timing) require stricter thresholds. Strategy/management domains accommodate smaller samples with large effect sizes.

**Adaptive Probation Policy** (DD-004):

When "Request more evidence" selected:

- **Duration**: 90 days (monthly patterns), 180 days (quarterly), 365 days (annual)
- **Required occurrences**: 2-5 more (based on initial correlation strength)
- **Extensions**: Max 2 extensions (90 days each) if 50%+ progress toward target
- **Deadline evaluation**: Auto-approve if correlation holds, reject if degrades or insufficient evidence
- **Total maximum**: Original duration + 180 days (prevents indefinite probation)

**Anti-Confirmation Bias Mechanisms** ([DD-007](../design-decisions/DD-007_PATTERN_VALIDATION_ARCHITECTURE.md)):

All patterns undergo 3-tier validation before Gate 6 review:

1. **Hold-Out Validation**: Patterns tested on data not used for discovery (train/val/test split 70%/15%/15%)
2. **Blind Testing**: Track pattern performance without agent awareness (6-month shadow analysis)
3. **Control Groups**: A/B test pattern-using vs. baseline analyses (statistical significance testing)
4. **Statistical Rigor**: Domain-specific p-value thresholds (p < 0.01 to p < 0.10 depending on domain)
5. **Human Expert Review**: Domain experts validate causal mechanisms at Gate 6

This prevents confirmation bias loops and self-fulfilling prophecies (see [Flaw #3](../../docs/design-flaws/resolved/03-pattern-validation.md)).

---

## Human Interface Design

### Dashboard Components

```text
┌──────────────────────────────────────┐
│         Pipeline Overview            │
├──────────────────────────────────────┤
│ ▶ Screening    [12 new] [3 pending] │
│ ▶ Analysis     [8 active] [2 done]  │
│ ▶ Decisions    [4 awaiting]         │
└──────────────────────────────────────┘

┌──────────────────────────────────────┐
│        Pending Decisions             │
├──────────────────────────────────────┤
│ 🔴 AAPL valuation assumptions       │
│ 🟡 MSFT peer group validation       │
│ 🟢 GOOGL screening approval         │
└──────────────────────────────────────┘
```

### Request Prioritization

| Priority | Description                    | Response Time | Auto-Action (After Timeout)          | Applies To                                  |
| -------- | ------------------------------ | ------------- | ------------------------------------ | ------------------------------------------- |
| CRITICAL | Blocks all analysis            | 2 hours       | Halt pipeline                        | System errors, data corruption              |
| HIGH     | Critical-path blocking debates | 6 hours       | Conservative default (provisional)   | Debates blocking immediate progress         |
| MEDIUM   | Valuation/model decisions      | 24 hours      | Conservative estimates (provisional) | Gate 3 assumptions, medium-priority debates |
| LOW      | Nice-to-have                   | 48 hours      | Skip or defer to next gate           | Supporting analysis debates                 |

**Debate-Specific Priority Routing**:

- **Critical-Path Debates** → HIGH priority (6hr timeout → conservative default)
- **Valuation Debates** → MEDIUM priority (24hr timeout → conservative estimates)
- **Supporting Debates** → LOW priority (48hr timeout → defer to next gate)

All provisional resolutions remain reviewable until next gate, enabling human override without blocking pipeline progress.

### Notification System

**Channels**:

- Email for non-urgent gate notifications
- SMS/push for critical decisions
- Dashboard alerts for real-time monitoring
- Weekly summary reports

**Notification Types**:

- Gate ready for review
- Analysis complete
- Material event detected
- System learning update
- Performance summary

---

## Expertise Routing

```yaml
Technical Analyst:
  - Entry/exit timing
  - Chart patterns
  - Technical indicators

Industry Specialist:
  - Business model assessment
  - Competitive dynamics
  - Industry trends

Financial Expert:
  - Accounting review
  - Model validation
  - Ratio analysis

Risk Manager:
  - Position sizing
  - Portfolio impact
  - Risk assessment
```

**Multi-Expert Workflows**:

Complex analyses may require multiple human experts:

1. Industry specialist validates business model (Gate 2)
2. Financial expert validates model assumptions (Gate 3)
3. Risk manager determines position sizing (Gate 5)

The system routes to appropriate experts based on their specialization and the analysis phase.

---

## Human Memory Contributions

The system captures and leverages human expertise through structured interfaces.

**Capture Mechanisms**:

- Explicit insight entry during gate reviews
- Override rationale documentation
- Pattern validation feedback
- Ad-hoc notes and observations
- Post-mortem analysis contributions

**Human Insight Types**:

- **Experiential**: "I've seen this pattern fail when X happens"
- **Relationship-based**: "Management team has reputation for Y"
- **Industry-specific**: "This sector has unwritten rule about Z"
- **Qualitative**: "Company culture seems strong/weak"
- **Political/regulatory**: "Upcoming regulation may impact..."

**Memory Storage**:

Human insights are stored with high priority in the knowledge base:

- Tagged as high-value human experiential knowledge
- Surfaced prominently in future similar analyses
- Shared with relevant agents immediately
- Used to validate or challenge pattern discoveries
- Incorporated into debating and decision-making

**Requesting Human Memory**:

The system can explicitly request human recall:

```text
Analyzing: Tesla's manufacturing scale-up strategy

Do you recall similar situations from your experience?
Particularly interested in:
- Outcomes that surprised the models
- Qualitative factors we might miss
- Industry-specific knowledge
- Relationship/political dynamics
```

This active solicitation ensures valuable human knowledge is captured before it's forgotten.

---

## Success Metrics

### Gate Performance

- **Response time**: Average time to human input at each gate
- **Override rate**: Frequency of human overrides to AI recommendations
- **Decision quality**: Accuracy of human-guided vs. auto-approved decisions
- **Throughput impact**: Effect of human delays on pipeline velocity

### Learning Contribution

- **Insight capture rate**: Human insights stored per analysis
- **Insight utilization**: Frequency of human insights applied in future analyses
- **Pattern validation quality**: Accuracy of human-validated vs. auto-validated patterns
- **Override value**: Correlation between human overrides and improved outcomes

### User Experience

- **Interface usability**: Time to complete gate reviews
- **Notification effectiveness**: Response rates by channel and priority
- **Cognitive load**: Complexity of decision packages
- **Satisfaction**: Human analyst satisfaction scores

---

## Related Documentation

### Core Documentation

- [System Design v2.0](../../multi_agent_fundamental_analysis_v2.0.md) - Complete system specification
- [Memory Architecture](../architecture/memory.md) - Memory system design
- [Learning Systems](./learning-systems.md) - Continuous improvement mechanisms

### Operations Documentation

- [Analysis Pipeline](./01-analysis-pipeline.md) - Core 12-day analysis workflow
- [Data Management](./03-data-management.md) - Data sources and storage
- [Monitoring & Alerts](../implementation/monitoring.md) - System observability

### User Guides

- [Dashboard User Guide](../guides/dashboard-guide.md) - Interface navigation
- [Gate Review Best Practices](../guides/gate-review-guide.md) - Effective gate participation
- [Insight Capture Guide](../guides/insight-capture-guide.md) - Recording valuable knowledge
