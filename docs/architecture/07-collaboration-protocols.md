# Collaborative Intelligence Protocols

## Overview

This document defines the communication and collaboration protocols that enable agents to work together effectively, share knowledge, and collectively arrive at better decisions than any single agent could achieve alone.

---

## Basic Inter-Agent Messaging

### Message Structure

```json
{
  "from_agent": "financial_analyst",
  "to_agent": "valuation_agent",
  "message_type": "finding",
  "priority": "high",
  "content": {
    "finding": "Abnormal capex increase",
    "confidence": 0.85,
    "evidence": ["10-K page 45", "CFO commentary"],
    "impact": "Adjust FCF projections"
  },
  "timestamp": "2025-11-16T10:30:00Z",
  "requires_response": true
}
```

### Message Types

**Finding**: Share analytical results

- Discovery from analysis
- Confidence level
- Supporting evidence
- Implications for other agents

**Request**: Ask for specific analysis

- Targeted query
- Scope and parameters
- Priority and deadline
- Context and rationale

**Challenge**: Dispute another agent's conclusion

- Disagreement with finding
- Basis for challenge
- Counter-evidence
- Request for clarification

**Confirmation**: Validate information

- Verify finding or data
- Cross-check assumption
- Seek agreement
- Build consensus

**Alert**: Urgent attention needed

- Material development
- Immediate action required
- Risk notification
- Deadline warning

---

## Debate Protocol

### Challenge Format

```json
{
  "challenge_id": "CH-001",
  "challenger": "strategy_analyst",
  "challenged": "financial_analyst",
  "disputed_finding": "Management effectiveness",
  "challenge_basis": "ROI declining despite claims",
  "required_evidence": ["Historical ROI data", "Peer comparison"],
  "escalation_timer": 3600,
  "priority": "critical-path",
  "provisional_resolution": null
}
```

### 5-Level Tiered Escalation System

The debate protocol uses a tiered escalation approach with timeouts and fallback mechanisms to prevent pipeline deadlocks when humans are unavailable.

#### Level 1: Agent Direct Resolution (15min timeout)

**Process**:

1. Challenged agent acknowledges within 15 minutes
2. Agent provides evidence addressing challenge
3. Challenger evaluates response
4. If accepted → resolved, end debate
5. If rejected → escalate to Level 2

**Actions**:

- Confirm receipt of challenge
- Commit to response timeline
- Request clarification if needed
- Address challenge directly with evidence
- Acknowledge limitations
- Revise position if warranted

#### Level 2: Debate Facilitator Mediation (1hr timeout)

**Process**:

1. Debate Facilitator reviews both positions
2. Applies credibility scoring based on agent track records
3. If credibility differential >0.25 → auto-resolve to higher credibility position
4. If credibility differential <0.25 → escalate to Level 3
5. Documents reasoning and evidence considered

**Auto-Resolution Criteria**:

- Credibility gap threshold: 0.25
- Based on agent historical accuracy in similar contexts
- Requires minimum 5 historical data points per agent
- Falls back to escalation if insufficient data

#### Level 3: Human Arbitration - Gate 4 (6hr timeout)

**Process**:

1. Debate added to human queue with priority classification
2. Queue managed (max 3 concurrent per expert)
3. Human receives both positions with credibility scores and precedents
4. If human responds within 6 hours → binding resolution
5. If timeout → escalate to Level 4

**Priority Classification** (determines queue order):

- **Critical-path blocking**: Debates preventing immediate pipeline progress (highest)
- **Valuation impact**: Debates affecting DCF assumptions, price targets (medium)
- **Supporting analysis**: Background research disagreements (lowest)

**Queue Management**:

- Max concurrent debates per expert: 3
- Overflow handling: Auto-escalate to Level 4 or defer to next gate
- Load indicator displayed in dashboard

#### Level 4: Fallback Resolution (24hr timeout)

**Process**:

1. Conservative default logic applied automatically
2. Resolution marked as "provisional decision"
3. Pipeline continues (non-blocking)
4. Override window opens: Until next gate
5. Human can review and override at subsequent gates

**Conservative Default Logic**:

1. Identify most cautious position:
   - Lowest price target
   - Highest risk assessment
   - Most conservative assumptions
   - Most skeptical interpretation
2. Apply that position as provisional resolution
3. Document rationale in decision log
4. Flag for mandatory review at next gate

**Override Window**:

- Opens when fallback applied
- Closes at next human decision gate
- Human sees "X provisional decisions require review" at gate
- Actions: Confirm, Override (with rationale), Request re-debate

#### Level 5: Gate Review (at next decision point)

**Process**:

1. Next gate displays all provisional decisions requiring review
2. Human reviews fallback reasoning and agent positions
3. Options:
   - **Confirm**: Accept conservative default, becomes final
   - **Override**: Apply different resolution, check downstream impact
   - **Re-debate**: Trigger new debate with additional context
4. Final resolution propagated to all agents

**Downstream Impact Check**:

- If override changes key assumptions, flag dependent analyses
- Re-run affected calculations if needed
- Update confidence scores if cascading changes occur

### Escalation Timeouts Summary

| Level             | Timeout                     | Action if Exceeded                 |
| ----------------- | --------------------------- | ---------------------------------- |
| 1: Agent Direct   | 15min (ack), 1hr (evidence) | Escalate to Level 2                |
| 2: Facilitator    | 1hr                         | Escalate to Level 3                |
| 3: Human (Gate 4) | 6hr                         | Escalate to Level 4                |
| 4: Fallback       | 24hr (provisional)          | Continue with conservative default |
| 5: Gate Review    | Until next gate             | Override window closes             |

### Priority-Based Queue Management

**Queue Limits**:

- Single expert: Max 3 concurrent debates
- Overflow: Auto-resolve or defer based on priority

**Routing Logic**:

1. Critical-path debates → immediate attention (skip queue if <3)
2. Valuation debates → queue position based on arrival time
3. Supporting debates → defer to next gate if queue full

**Load Balancing** (future multi-expert):

- Round-robin assignment
- Expertise-based routing
- Workload-aware distribution

### Documentation Requirements

**For All Resolutions** (regardless of level):

- Final agreed/applied position
- Evidence considered
- Resolution level and method
- Confidence level
- Impact on analysis
- If provisional: Override window status

**Additional for Provisional Resolutions**:

- Conservative default rationale
- Alternative positions considered
- Review deadline (next gate)
- Downstream dependencies

---

## Memory-Enhanced Communication

### Enhanced Message Structure with Historical Context

```json
{
  "from_agent": "financial_analyst",
  "to_agent": "valuation_agent",
  "message_type": "finding_with_precedent",
  "priority": "high",
  "content": {
    "finding": "Abnormal capex increase",
    "confidence": 0.85,
    "evidence": ["10-K page 45", "CFO commentary"],
    "historical_context": {
      "similar_patterns": [
        {
          "company": "MSFT",
          "year": 2016,
          "outcome": "Cloud investment paid off"
        }
      ],
      "pattern_success_rate": 0.72,
      "my_accuracy_on_pattern": 0.81
    },
    "impact": "Adjust FCF projections with growth bias"
  },
  "timestamp": "2025-11-16T10:30:00Z",
  "requires_response": true
}
```

### Historical Context Fields

**Similar Patterns**:

- Past occurrences of same pattern
- Companies and timeframes
- Outcomes (positive/negative)
- Success rates

**Pattern Metadata**:

- Overall pattern success rate
- Agent's accuracy on this pattern
- Number of observations
- Confidence intervals

**Agent Credibility**:

- Track record in similar contexts
- Historical accuracy scores
- Domain expertise relevance
- Learning trajectory

---

## Real-Time Collaborative Memory Building

**Note**: Code samples referenced here have been omitted from architecture docs. See `/examples/` directory for implementation examples.

### Collaborative Session Mechanics

**Shared Context Management**:

- Maintain common understanding across agents
- Track emerging insights in real-time
- Identify pattern candidates during analysis
- Alert agents to important cross-domain findings

**Cross-Validation**:

- Check findings against other agents' discoveries
- Strengthen patterns with multiple confirmations
- Identify contradictions early
- Build consensus incrementally

**Importance Filtering**:

- Broadcast high-importance findings (>0.8)
- Buffer medium-importance locally
- Discard low-value noise
- Adaptive thresholds based on context

**Synthesis Checkpoints**:

- Periodic consolidation of learnings
- Identify emerging patterns
- Surface contradictions for resolution
- Store intermediate insights

---

## Decision Meeting with Full Memory Context

### Decision Package Components

**Note**: Code samples referenced here have been omitted from architecture docs. See `/examples/` directory for implementation examples.

A complete decision package includes:

**Current Analysis**:

- All agent findings
- Confidence scores
- Supporting evidence
- Areas of uncertainty

**Historical Context**:

- Similar past decisions
- Success rates in this context
- Cautionary examples
- Lessons learned

**Agent Credibility**:

- Track record summaries
- Accuracy in similar situations
- Domain expertise weights
- Learning improvements

**Pattern Matches**:

- Relevant historical patterns
- Success/failure rates
- Applicability conditions
- Risk indicators

**Confidence Calibration**:

- Adjust scores for historical accuracy
- Apply learned bias corrections
- Quantify uncertainty
- Risk-adjusted recommendations

### Memory-Informed Recommendation

The system synthesizes:

- Credibility-weighted agent positions
- Historical precedent guidance
- Pattern match probabilities
- Risk factors from memory
- Confidence intervals with track record basis

---

## Debate Enhancement with Memory

### Pre-Debate Memory Synchronization

Before structured debates begin, the system ensures memory consistency:

**Critical Sync Protocol**:

1. **Force sync all participants** (<2 seconds)

   - Both challenger and challenged agents
   - All related agents in same analysis stream
   - Ensures no stale local cache data

2. **Create memory snapshot**

   - Point-in-time view of all relevant knowledge
   - Locked state prevents mid-debate inconsistencies
   - All participants work from identical evidence base

3. **Load historical context**
   - Relevant historical debates
   - Similar disagreements and resolutions
   - Agent credibility by track record
   - Applicable precedents

**Why Critical Sync Matters**: Without forced synchronization, debates could proceed with agents having different views of evidence, leading to contradictory positions and degraded debate quality.

### Challenge with Historical Evidence

Challenges are strengthened by:

- Historical counter-examples
- Pattern accuracy rates
- Agent track records on topic
- Success rates of competing positions

### Resolution with Precedent

Conflict resolution considers:

- Similar historical conflicts
- Which position proved correct historically
- Agent credibility weighting
- Statistical likelihood based on patterns

### Post-Debate Synchronization

After debate resolution:

- Outcomes immediately synced to central knowledge graph
- All agents receive debate conclusions (high-priority sync)
- Updated credibility scores propagated
- Lessons learned added to institutional knowledge

---

## Related Documentation

- [System Overview](./01-system-overview.md) - Overall architecture
- [Memory System](./02-memory-system.md) - Knowledge graph supporting collaboration
- [Coordination Agents](./05-agents-coordination.md) - Debate facilitation
- [Specialist Agents](./03-agents-specialist.md) - Primary participants in collaboration
