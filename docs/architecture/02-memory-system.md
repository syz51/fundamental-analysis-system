# Memory Architecture

## Hybrid Memory Model

The system implements a three-tier hybrid memory architecture combining centralized knowledge with distributed agent-specific memories:

```text
┌─────────────────────────────────────────────┐
│      Central Knowledge Graph (Neo4j)         │
│  Companies | Patterns | Decisions | Outcomes │
└─────────────────────────────────────────────┘
                    ▲ ▼ Sync
┌──────────────┬──────────────┬───────────────┐
│   L2 Cache   │   L2 Cache   │   L2 Cache    │
│ Specialized  │ Specialized  │ Specialized   │
├──────────────┼──────────────┼───────────────┤
│  Financial   │   Strategy   │   Valuation   │
│    Agent     │    Agent     │     Agent     │
│ L1: Working  │ L1: Working  │  L1: Working  │
└──────────────┴──────────────┴───────────────┘
```

---

## Memory Hierarchy

### L1: Agent Working Memory (RAM)

- **Purpose**: Immediate context for current analysis
- **Contents**: Active calculations, current company data, debate context
- **Size**: ~100 items per agent
- **TTL**: Hours
- **Access Time**: <10ms

### L2: Agent Specialized Cache (Local Database)

- **Purpose**: Domain-specific patterns and frequently accessed data
- **Contents**:
  - Financial Agent: Ratio patterns, peer comparisons, accounting rules
  - Strategy Agent: Management patterns, capital allocation histories
  - Valuation Agent: Model templates, multiple histories, sector norms
- **Size**: ~10,000 items per agent
- **TTL**: Weeks (with refresh)
- **Access Time**: <100ms

### L3: Central Knowledge Graph (Graph Database)

- **Purpose**: Permanent institutional knowledge
- **Contents**: All analyses, decisions, outcomes, patterns, relationships
- **Size**: Unlimited
- **TTL**: Permanent
- **Access Time**: <1s

---

## Knowledge Graph Schema

```yaml
Nodes:
  Company:
    - ticker: string
    - sector: string
    - analyzed_count: integer
    - last_analysis: datetime

  Analysis:
    - id: string
    - date: datetime
    - recommendation: enum
    - confidence: float
    - outcome: float

  Pattern:
    - name: string
    - category: string
    - success_rate: float
    - occurrence_count: integer

  Decision:
    - id: string
    - type: string
    - agents_involved: array
    - outcome: enum

  Agent:
    - name: string
    - specialization: string
    - accuracy_scores: object
    - total_decisions: integer

Relationships:
  - Company -[HAS_ANALYSIS]-> Analysis
  - Analysis -[IDENTIFIED_PATTERN]-> Pattern
  - Analysis -[LED_TO]-> Decision
  - Decision -[HAS_OUTCOME]-> Outcome
  - Agent -[PERFORMED]-> Analysis
  - Agent -[MADE]-> Decision
  - Pattern -[SIMILAR_TO]-> Pattern
  - Company -[PEER_OF]-> Company
```

### Debate-Specific Knowledge Graph Extensions

To support the tiered debate resolution system, the knowledge graph includes specialized nodes and relationships for tracking debate patterns and agent credibility:

```yaml
Additional Nodes for Debate Resolution:
  Debate:
    - id: string
    - topic: string
    - challenger_agent: string
    - challenged_agent: string
    - disputed_finding: string
    - challenge_basis: string
    - resolution_level: enum [1_agent, 2_facilitator, 3_human, 4_fallback, 5_gate_review]
    - resolution_method: enum [consensus, credibility_weighted, human_binding, conservative_default, override]
    - final_position: string
    - timestamp: datetime
    - priority: enum [critical_path, valuation, supporting]
    - provisional: boolean
    - override_window_closed: datetime

  DebateResolution:
    - id: string
    - debate_id: string
    - winning_position: string
    - winning_agent: string
    - credibility_differential: float
    - resolution_time_seconds: integer
    - human_override: boolean
    - override_rationale: string
    - downstream_impact: array
    - accuracy_tracked: boolean
    - outcome_correctness: float (populated later)

  AgentCredibility:
    - agent_id: string
    - domain: string (e.g., "tech_margins", "management_evaluation")
    - overall_score: float
    - sample_size: integer
    - recent_accuracy: float (last 10 decisions)
    - time_weighted_score: float
    - bias_corrections: object
    - last_updated: datetime

Additional Relationships for Debate Resolution:
  - Debate -[RESOLVED_BY]-> Agent (facilitator or human)
  - Debate -[WINNING_POSITION]-> Agent
  - Debate -[HAS_RESOLUTION]-> DebateResolution
  - DebateResolution -[IMPACTED_ANALYSIS]-> Analysis
  - Agent -[HAS_CREDIBILITY_IN]-> Domain
  - Debate -[SIMILAR_TO]-> Debate (pattern matching)
  - Pattern -[SUPPORTS_POSITION]-> Debate (historical evidence)
  - Human -[OVERRODE]-> DebateResolution
```

**Debate Pattern Storage**:

The system stores complete debate histories including:

- Debate topics and agent positions
- Resolution methods and outcomes
- Credibility scores at time of debate
- Time to resolution at each level
- Provisional vs binding resolutions
- Human override patterns
- Accuracy of fallback resolutions (tracked post-outcome)

**Query Capabilities**:

```cypher
# Find similar past debates
MATCH (d1:Debate)-[:SIMILAR_TO]-(d2:Debate)
WHERE d1.topic CONTAINS "margin_sustainability"
  AND d2.resolution_level IN [3_human, 4_fallback]
RETURN d2, d2.final_position, d2.outcome_correctness
ORDER BY d2.timestamp DESC
LIMIT 5

# Retrieve agent credibility in specific domain
MATCH (a:Agent)-[r:HAS_CREDIBILITY_IN]->(domain)
WHERE a.name = "financial_analyst"
  AND domain.name = "retail_margins"
RETURN r.overall_score, r.sample_size, r.recent_accuracy

# Find debates where conservative default was applied
MATCH (d:Debate)-[:HAS_RESOLUTION]->(dr:DebateResolution)
WHERE d.resolution_level = '4_fallback'
  AND dr.human_override = true
RETURN d.topic, d.final_position, dr.override_rationale, dr.outcome_correctness

# Calculate facilitator auto-resolution success rate
MATCH (d:Debate)-[:HAS_RESOLUTION]->(dr:DebateResolution)
WHERE d.resolution_level = '2_facilitator'
  AND dr.accuracy_tracked = true
RETURN AVG(dr.outcome_correctness) as success_rate,
       COUNT(*) as total_auto_resolutions
```

**Agent Credibility Tracking**:

The system maintains dynamic credibility scores for each agent in specific domains:

**Credibility Calculation**:

```text
credibility_score = (
  0.4 * historical_accuracy_in_domain +
  0.3 * recent_performance_last_10 +
  0.2 * time_weighted_accuracy +
  0.1 * evidence_quality_score
)
```

**Credibility Updates**:

- After each analysis outcome is known (6-12 months post-decision)
- Weighted toward recent performance (exponential decay)
- Domain-specific (agent may have high credibility in one area, lower in another)
- Requires minimum 5 data points before use in auto-resolution

**Bias Correction Storage**:

- Systematic over/under-estimation patterns
- Sector-specific biases
- Market regime dependencies
- Recommended adjustments for future analyses

**Similar Debate Precedent Retrieval**:

When a new debate initiates, the system retrieves relevant historical debates:

**Similarity Matching Criteria**:

1. **Topic similarity**: NLP-based semantic matching on debate topics
2. **Agent pairing**: Same agents involved in past debates
3. **Domain overlap**: Similar analytical domains (margins, growth, ROIC, etc.)
4. **Pattern involvement**: Same patterns cited as evidence
5. **Company characteristics**: Similar sector, size, maturity

**Precedent Presentation**:

```yaml
Historical Precedent Context:

Similar Debates (3 found):
  1. Topic: "Tech margin sustainability in competitive markets"
     Date: 2024-06-15
     Agents: Financial Analyst vs Strategy Analyst
     Resolution: Human arbitration → Financial Analyst position
     Outcome: Correct (margins held, accuracy: 0.92)
     Lesson: Financial analyst credibility higher in margin defense

  2. Topic: "Operating leverage assumptions"
     Date: 2024-08-22
     Agents: Financial Analyst vs Valuation Agent
     Resolution: Credibility-weighted → Valuation Agent (diff: 0.31)
     Outcome: Correct (accuracy: 0.88)

  3. Topic: "Gross margin expansion potential"
     Date: 2024-03-10
     Resolution: Conservative default (human unavailable)
     Outcome: Conservative position correct (accuracy: 1.0)
     Lesson: Conservative defaults effective for margin debates

Pattern Success Rates:
  - "Margin compression in competitive markets": 0.73 (12 occurrences)
  - "Operating leverage benefits": 0.68 (8 occurrences)

Agent Track Records in This Domain (retail margins):
  - Financial Analyst: 0.82 (15 decisions)
  - Strategy Analyst: 0.71 (12 decisions)
  - Credibility differential: 0.11 (below auto-resolution threshold)
```

This precedent context enables:

- Data-driven debate facilitation
- Informed credibility weighting
- Pattern-based argument validation
- Learning from past resolution effectiveness

---

## Memory Synchronization Protocol

**Note**: Code samples referenced here have been omitted from architecture docs. See `/examples/` directory for implementation examples.

### Event-Driven Priority Sync Architecture

The Memory Sync Manager uses an event-driven approach with three priority tiers to ensure timely synchronization while minimizing overhead.

**Sync Priority Levels**:

| Priority     | Trigger Events                            | Latency     | Use Cases                                           |
| ------------ | ----------------------------------------- | ----------- | --------------------------------------------------- |
| **Critical** | Debates, challenges, human gates          | <2 seconds  | Ensures consistency during high-stakes interactions |
| **High**     | Important findings, alerts, confirmations | <10 seconds | Fast propagation of significant discoveries         |
| **Normal**   | Routine updates, batch operations         | 5 minutes   | Background sync for non-urgent updates              |

### Synchronization Process

**Push Operations** (Local → Central):

- Critical: Immediate push when debate initiated or human gate approaching
- High: Fast push for important discoveries (importance > 0.7)
- Normal: Scheduled push every 5 minutes for routine updates

**Pull Operations** (Central → Local):

- Critical: Force immediate pull before debates/challenges
- High: Fast pull when relevant high-priority updates available
- Normal: Periodic pull of cross-domain insights

**Event-Triggered Sync**:

The system automatically triggers critical sync when:

- **Debate/Challenge Initiated**: Both challenger and challenged agents force-synced
- **Human Gate Approaching**: All agents synced 30 minutes before gate
- **Alert Messages**: Sending and receiving agents high-priority synced
- **Finding with Precedent**: High-priority sync to ensure historical context available

### Memory Snapshot for Debates

During debates, the system creates a point-in-time memory snapshot:

1. **Force sync all participants** - ensures consistent starting state
2. **Create locked snapshot** - prevents mid-debate inconsistencies
3. **All agents reference snapshot** - uniform view of evidence
4. **Sync after resolution** - propagate debate outcomes

### Relevance Determination

The system determines which agents need immediate notification based on:

- Agent specialization overlap
- Current active analyses
- Historical usage patterns
- Insight importance and urgency
- Message type and priority

---

## Related Documentation

- [System Overview](./01-system-overview.md) - High-level architecture
- [Specialist Agents](./03-agents-specialist.md) - Agents using memory systems
- [Knowledge Base Agent](./04-agents-support.md#knowledge-base-agent) - Memory management agent
- [Collaboration Protocols](./07-collaboration-protocols.md) - Memory-enhanced communication
