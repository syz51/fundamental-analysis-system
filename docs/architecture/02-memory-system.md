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

---

## Memory Synchronization Protocol

**Note**: Code samples referenced here have been omitted from architecture docs. See `/examples/` directory for implementation examples.

### Synchronization Process

The Memory Sync Manager handles bidirectional synchronization between agent local memories and the central knowledge base:

**Push Operations** (Local → Central):

- Important local discoveries (importance > 0.7)
- New insights from agent analysis
- Broadcast to relevant agents

**Pull Operations** (Central → Local):

- Relevant updates since last sync
- Cross-domain insights applicable to agent's specialization
- Pattern updates affecting agent's domain

**Sync Frequency**: Every 5 minutes for active agents

### Relevance Determination

The system determines which agents need immediate notification of insights based on:

- Agent specialization overlap
- Current active analyses
- Historical usage patterns
- Insight importance and urgency

---

## Related Documentation

- [System Overview](./01-system-overview.md) - High-level architecture
- [Specialist Agents](./03-agents-specialist.md) - Agents using memory systems
- [Knowledge Base Agent](./04-agents-support.md#knowledge-base-agent) - Memory management agent
- [Collaboration Protocols](./07-collaboration-protocols.md) - Memory-enhanced communication
