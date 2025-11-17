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
  "escalation_timer": 3600
}
```

### Response Requirements

1. **Acknowledge within 15 minutes**

   - Confirm receipt of challenge
   - Commit to response timeline
   - Request clarification if needed

2. **Provide evidence within 1 hour**

   - Address challenge directly
   - Present supporting evidence
   - Acknowledge limitations
   - Revise position if warranted

3. **Escalate to human if unresolved**

   - Document disagreement
   - Present both positions
   - Highlight decision impact
   - Request arbitration

4. **Document resolution**
   - Final agreed position
   - Evidence considered
   - Confidence level
   - Impact on analysis

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

### Pre-Debate Memory Loading

Before structured debates, the system:

- Loads relevant historical debates
- Identifies similar disagreements and resolutions
- Weights agent credibility by track record
- Surfaces applicable precedents

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

---

## Related Documentation

- [System Overview](./01-system-overview.md) - Overall architecture
- [Memory System](./02-memory-system.md) - Knowledge graph supporting collaboration
- [Coordination Agents](./05-agents-coordination.md) - Debate facilitation
- [Specialist Agents](./03-agents-specialist.md) - Primary participants in collaboration
