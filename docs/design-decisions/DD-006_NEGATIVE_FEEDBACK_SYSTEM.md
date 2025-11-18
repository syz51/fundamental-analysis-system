# Negative Feedback System for Failure Investigation

**Status**: Approved
**Date**: 2025-11-17
**Decider(s)**: System Architect
**Related Docs**: [Learning Systems](../learning/01-learning-systems.md), [Memory Architecture](../architecture/04-memory-architecture.md), [Feedback Loops](../learning/02-feedback-loops.md)
**Related Decisions**: DD-001 (Gate 6 Learning Validation), DD-007 (Pattern Validation)

---

## Context

v2.0 learning system tracks outcomes and calculates accuracy scores but lacks structured negative feedback mechanisms:

- Checkpoint reviews (30/90/180/365 days) record success/failure
- Pattern degradation triggers (>20% drop) deprecate bad patterns
- Agent error patterns identified for self-improvement
- **Missing**: Deep failure investigation, root cause analysis, human expertise capture, success validation

**Problem**: System learns from outcomes but doesn't understand WHY failures occurred or distinguish "lucky success" from "genuine skill". Without root cause analysis:

- False patterns reinforced (stock up for wrong reasons)
- Failure lessons not systematically captured
- Missing factors not identified for future analyses
- Lucky successes strengthen bad reasoning

**Impact**: Superficial learning, repeated mistakes, confirmation bias loop.

---

## Decision

**Implemented async post-mortem system with mandatory investigation for significant deviations (>30%), human expertise capture, success validation, and systematic lesson broadcasting.**

Post-mortems triggered at checkpoints when outcomes deviate >30% from predictions. Async queue (max 5 concurrent) prioritized by deviation severity. Human completes structured review within 48hrs. Lessons extracted and broadcast to affected agents/patterns.

---

## Options Considered

### Option 1: No Structured Post-Mortems (Status Quo)

**Description**: Continue with basic outcome tracking and accuracy scoring only

**Pros**:

- Zero additional implementation effort
- No human time required
- Simple, automated learning

**Cons**:

- Can't learn from failures (only records failure happened)
- False patterns reinforced
- Repeated mistakes with no root cause understanding
- Lucky successes incorrectly strengthen bad reasoning

**Estimated Effort**: None

---

### Option 2: Synchronous Mandatory Post-Mortems

**Description**: Block pipeline until post-mortem completed for every significant failure

**Pros**:

- Immediate investigation while context fresh
- Guaranteed human review before continuing
- Forces attention to failures

**Cons**:

- Blocks pipeline (post-mortems happen 30-365 days after decision)
- High human burden (must respond immediately to old failures)
- Defeats purpose (post-mortems retrospective, not blocking)
- Poor user experience

**Estimated Effort**: 3-4 weeks

---

### Option 3: Async Post-Mortem System (CHOSEN)

**Description**: Async investigation queue triggered at checkpoints, human reviews on schedule, lessons applied retroactively

**Pros**:

- Non-blocking (doesn't delay pipeline)
- Batch reviews efficient for human
- Systematic root cause analysis
- Success validation prevents false positive learning
- Lesson broadcasting shares insights across system
- Queue management prevents overload

**Cons**:

- Lessons applied after pattern may have been used (mitigated by Gate 6 quarantine)
- Requires async queue infrastructure
- 48hr review SLA needs enforcement

**Estimated Effort**: 4-5 weeks

---

## Rationale

**Option 3 selected** because post-mortems inherently retrospective (triggered 30-365 days after decision). No reason to block pipeline for analysis of old decisions.

Key factors:

- **Async nature**: Post-mortems analyze outcomes known months later, non-blocking correct approach
- **Human efficiency**: Batch reviews (5 concurrent max) better than immediate interruptions
- **Learning quality**: Structured process with failure taxonomy and human questions captures deep insights
- **Integration**: Works with Gate 6 (patterns quarantined until validated) and existing checkpoint system
- **Scalability**: Queue limits (5 concurrent) prevent human overload at scale

Tradeoffs accepted:

- Lesson application delay mitigated by Gate 6 quarantine (unvalidated patterns not used)
- Infrastructure complexity justified by learning quality improvement

---

## Consequences

### Positive Impacts

- **Root cause understanding**: Systematic investigation reveals WHY failures occurred
- **Human expertise captured**: Structured questions extract qualitative insights ("what did we miss?")
- **Success validation**: Distinguishes luck from skill, prevents false positive learning
- **Lesson broadcasting**: Failure insights shared across agents, prevents repetition
- **Audit trail**: Complete failure investigation history for pattern re-evaluation
- **Continuous improvement**: Learning from mistakes, not just successes

### Negative Impacts / Tradeoffs

- **Implementation complexity**: FailurePostMortem, SuccessValidator, LessonBroadcaster components
- **Human burden**: 48hr review SLA for post-mortems (mitigated by 5 concurrent limit)
- **Queue management**: Need prioritization logic (deviation severity)
- **Lesson delay**: Insights applied retroactively (acceptable for retrospective analysis)

### Affected Components

- **OutcomeTracker**: Triggers post-mortems on >30% deviation at checkpoints
- **NegativeFeedbackManager** (NEW): Orchestrates post-mortem workflow, manages queue
- **Human Interface**: Post-mortem review dashboard with structured questions
- **Knowledge Base Agent**: Stores post-mortem reports, lessons learned library
- **Learning Engine**: Applies lessons to patterns, agent policies
- **All Specialist Agents**: Consume lessons, update checklists/bias corrections
- **Gate 6**: Validates pattern revisions from post-mortem insights

---

## Implementation Notes

### Trigger Conditions

Post-mortem triggered at checkpoint (30/90/180/365 days) if:

```text
abs(actual_outcome - predicted_outcome) / predicted_outcome > 0.30
```

Applies to both failures (negative outcomes) and missed opportunities (passed, stock outperformed).

### Failure Taxonomy

6 categories for root cause classification:

1. **Data quality**: Missing/incorrect data, stale information
2. **Model assumptions**: DCF inputs wrong, growth rates off
3. **Missing factors**: Unconsidered variables (competitive threat, regulatory change)
4. **Timing**: Thesis correct but too early/late
5. **Regime change**: Market conditions shifted (multiple compression, rate changes)
6. **Black swan**: Unforeseeable events (pandemic, war, fraud)

### Human Interface Questions

Structured review (48hr SLA):

1. Primary reason for unexpected outcome? (6 categories + other)
2. Specific factors missed/underweighted? (free text)
3. Warning signs should have caught? (free text)
4. What to do differently in similar situations? (free text)
5. Which patterns need revision? (free text)
6. Foreseeability rating (1-5 scale)

### Success Validation Logic

For positive outcomes, validate:

- **Thesis decomposition**: Did our predicted drivers actually occur?
- **Baseline comparison**: Performance vs market/sector (alpha calculation)
- **Luck vs skill**: Attribution (market contribution, sector contribution, stock-specific)
- **Skill ratio**: `stock_specific_contribution × thesis_score`

Classification:

- `skill_ratio > 0.6` + thesis correct → Genuine Success (reinforce)
- `0.4 < skill_ratio ≤ 0.6` + beat market → Partial Success (partial credit)
- `skill_ratio ≤ 0.4` → Lucky Success (do not reinforce)

### Queue Management

- **Max concurrent**: 5 post-mortems
- **Priority**: By deviation severity (largest deviations reviewed first)
- **Timeout**: 48 hours for human response
- **Overflow**: Queue additional post-mortems, process sequentially

### Lesson Broadcasting

When post-mortem completed:

1. Extract actionable lessons (AI analysis + human insights)
2. Update affected agents (add to checklists, bias corrections)
3. Revise patterns (propose changes for Gate 6 validation)
4. Add to screening filters (if screening-related lesson)
5. Store in lesson library (searchable by category/agent/pattern)
6. Notify human (summary of changes applied)

### Integration Points

- **OutcomeTracker** → triggers post-mortem
- **NegativeFeedbackManager** → orchestrates workflow
- **Human Interface** → collects structured review
- **Knowledge Base Agent** → stores reports/lessons
- **Learning Engine** → applies lessons to patterns (via Gate 6)
- **CentralKnowledgeGraph** → provides historical context for similar failures

**Testing Requirements**:

1. Post-mortem trigger on >30% deviation
2. Queue management (5 concurrent limit, priority by severity)
3. Human interface (structured questions, 48hr SLA)
4. Success validation (luck vs skill decomposition)
5. Lesson extraction (AI + human synthesis)
6. Lesson broadcasting (updates to agents/patterns/checklists)
7. Integration with Gate 6 (pattern revision proposals)

**Rollback Strategy**: Disable post-mortem triggers, revert to basic outcome tracking only.

**Estimated Implementation Effort**: 4-5 weeks (Phase 4: Optimization)

**Dependencies**:

- Gate 6 operational (DD-001) - validates pattern revisions from post-mortems
- Pattern validation system (DD-007) - provides context on affected patterns
- Checkpoint review system - triggers post-mortems
- Human interface - post-mortem dashboard

---

## Open Questions

None - all design parameters specified.

**Blocking**: No

---

## References

- [Flaw #9: Negative Feedback Mechanism](../design-flaws/resolved/09-negative-feedback.md) - Original problem analysis
- [DD-001: Gate 6 Learning Validation](DD-001_GATE_6_LEARNING_VALIDATION.md) - Pattern validation dependency
- [DD-007: Pattern Validation Architecture](DD-007_PATTERN_VALIDATION_ARCHITECTURE.md) - Pattern context
- [Learning Systems](../learning/01-learning-systems.md) - Checkpoint review system
- [Feedback Loops](../learning/02-feedback-loops.md) - Agent error correction

---

## Status History

| Date       | Status   | Notes                                |
| ---------- | -------- | ------------------------------------ |
| 2025-11-17 | Proposed | Initial design from Flaw #9 analysis |
| 2025-11-17 | Approved | Approved by system architect         |

---

## Notes

**Async vs blocking rationale**: Post-mortems analyze outcomes discovered 30-365 days after original decision. Blocking pipeline for retrospective analysis illogical. Async queue allows systematic investigation without pipeline delays.

**5 concurrent limit**: Conservative capacity planning. Human gates max 3 concurrent (real-time, urgent). Post-mortems less urgent (retrospective), 5 concurrent manageable. Can adjust based on empirical data.

**Success validation critical**: Prevents "false positive" learning where stock goes up for wrong reasons (market rally, sector strength) and system incorrectly reinforces bad analysis. Luck vs skill decomposition ensures only genuine insights reinforced.

**Lesson broadcasting mechanism**: Post-mortem insights must propagate to prevent recurrence. Affected agents get checklist updates, patterns flagged for Gate 6 revision, lessons stored in searchable library. Without broadcasting, post-mortems generate reports but don't prevent future mistakes.

**Future enhancement**: Dashboard showing "lessons learned from failures" - categorized by failure type, most impactful insights, blind spots identified, pattern revisions triggered. Demonstrates continuous improvement to human user.
